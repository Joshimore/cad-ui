"""Link graph over the workspace.

Nodes are the same markdown/text files the index sees (scanner.iter_text_files);
node classification reuses tagger. Edges come from three sources:
  - markdown inline links   `[text](relative/path.md)`   -> kind "link"
  - wiki links              `[[Target]]` / `[[Target|x]]` -> kind "wiki"
  - agent -> skill          an agent's `skills:` frontmatter -> kind "uses"

The graph is built on demand and rendered client-side (vanilla SVG); this module
only produces a JSON-serialisable dict. Bounded by GRAPH_MAX_NODES.
"""
from __future__ import annotations

import posixpath
import re
from collections import Counter

from . import tagger
from .config import MARKDOWN_EXTENSIONS, WorkspaceConfig
from .index import _read              # reuse the one frontmatter + size-capped reader
from .markdown import _is_external    # reuse the one external-href test
from .scanner import iter_text_files

GRAPH_MAX_NODES = 800

# `[text](target "title")` — group 1 is a leading `!` (image embed, skipped),
# group 2 the target. The full bracket pair avoids matching bare `](` fragments.
_MD_LINK_RE = re.compile(r"(!?)\[[^\]]*\]\(\s*<?([^)>\s]+)>?")
# `[[Target]]` or `[[Target|alias]]` — capture Target.
_WIKI_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
# Fenced / inline code — stripped before scanning so code samples don't yield edges.
_FENCE_RE = re.compile(r"```.*?```", re.S)
_INLINE_CODE_RE = re.compile(r"`[^`]*`")


def _to_posix(rel: str) -> str:
    return rel.replace("\\", "/")


def _strip_code(body: str) -> str:
    """Drop fenced and inline code so links inside code samples aren't turned into edges."""
    return _INLINE_CODE_RE.sub(" ", _FENCE_RE.sub(" ", body))


def _keep_min(m: dict, key: str, nid: str) -> None:
    """Collision resolution that does not depend on filesystem walk order: keep the
    lexicographically smallest id, so a shared name/stem resolves the same everywhere."""
    if key and (key not in m or nid < m[key]):
        m[key] = nid


def _resolve_rel(href: str, base_dir: str) -> str | None:
    """Resolve a document-relative href to a workspace-relative POSIX path, or None
    if it is empty or points outside the workspace."""
    href = href.split("#", 1)[0].split("?", 1)[0].strip()
    if not href:
        return None
    joined = posixpath.join(base_dir, href) if base_dir else href
    joined = posixpath.normpath(joined)
    if joined.startswith("..") or joined.startswith("/"):
        return None
    return joined


def build_graph(cfg: WorkspaceConfig) -> dict:
    nodes: dict[str, dict] = {}
    raw_refs: dict[str, dict] = {}
    stem_map: dict[str, str] = {}    # basename stem (lower) -> id
    name_map: dict[str, str] = {}    # frontmatter name (lower) -> id
    skill_map: dict[str, str] = {}   # skill name (lower) -> id, skill nodes only
    truncated = False

    for rel, abs_path, _mtime, _kind in iter_text_files(cfg):
        if len(nodes) >= GRAPH_MAX_NODES:
            truncated = True
            break
        nid = _to_posix(rel)
        is_md = abs_path.suffix.lower() in MARKDOWN_EXTENSIONS
        # Only markdown bodies feed link/wiki/skill extraction; don't read the rest.
        meta, body = _read(abs_path, "markdown") if is_md else ({}, "")
        tags = tagger.extract_tags(nid, meta, body)
        nodes[nid] = {
            "id": nid,
            "label": str(meta.get("name") or abs_path.name),
            "type": tags["type"],
            "subsystem": tags["subsystem"],
            "project": tags["project"],
            "degree": 0,
        }
        _keep_min(stem_map, posixpath.splitext(abs_path.name)[0].lower(), nid)
        if meta.get("name"):
            name = str(meta["name"]).strip().lower()
            _keep_min(name_map, name, nid)
            if tags["type"] == "skill":
                _keep_min(skill_map, name, nid)

        refs: dict[str, list] = {"md": [], "wiki": [], "skills": []}
        if is_md:
            scan = _strip_code(body)
            base_dir = posixpath.dirname(nid)
            refs["md"] = [(m.group(2), base_dir) for m in _MD_LINK_RE.finditer(scan)
                          if m.group(1) != "!"]
            refs["wiki"] = [m.group(1).strip() for m in _WIKI_RE.finditer(scan)]
            if tags["type"] == "agent":
                sk = meta.get("skills")
                if isinstance(sk, str):
                    refs["skills"] = [s.strip() for s in sk.replace(",", " ").split()]
                elif isinstance(sk, (list, tuple)):
                    refs["skills"] = [str(s).strip() for s in sk]
        raw_refs[nid] = refs

    # Case-insensitive id lookup: a link's case need not match the file's on disk.
    nodes_ci = {nid.lower(): nid for nid in nodes}

    edges: list[dict] = []
    seen: set[tuple] = set()

    def add_edge(src: str, tgt: str | None, kind: str) -> None:
        if tgt and tgt in nodes and tgt != src and (src, tgt, kind) not in seen:
            seen.add((src, tgt, kind))
            edges.append({"source": src, "target": tgt, "kind": kind})

    def resolve_link(tgt: str | None) -> str | None:
        if not tgt or tgt in nodes:
            return tgt
        if (tgt + ".md") in nodes:
            return tgt + ".md"                        # link omitting the .md extension
        return nodes_ci.get(tgt.lower()) or nodes_ci.get((tgt + ".md").lower())

    def resolve_skill(name: str) -> str | None:
        tgt = skill_map.get(name.lower())             # match skill nodes only, not any doc
        if tgt:
            return tgt
        guess = f".claude/skills/{name}/SKILL.md"     # fall back to the canonical path
        return guess if guess in nodes else None

    for nid, refs in raw_refs.items():
        for href, base_dir in refs["md"]:
            if _is_external(href):
                continue
            add_edge(nid, resolve_link(_resolve_rel(href, base_dir)), "link")
        for w in refs["wiki"]:
            wl = w.lower()
            tgt = name_map.get(wl) or stem_map.get(wl) or stem_map.get(posixpath.splitext(wl)[0])
            add_edge(nid, tgt, "wiki")
        for s in refs["skills"]:
            add_edge(nid, resolve_skill(s), "uses")

    for e in edges:
        nodes[e["source"]]["degree"] += 1
        nodes[e["target"]]["degree"] += 1

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "types": dict(Counter(n["type"] for n in nodes.values())),
        "truncated": truncated,
    }
