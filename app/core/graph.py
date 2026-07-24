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
from pathlib import Path
from urllib.parse import urlparse

import frontmatter

from . import tagger
from .config import MARKDOWN_EXTENSIONS, WorkspaceConfig
from .scanner import iter_text_files

GRAPH_MAX_NODES = 800
MAX_CONTENT_BYTES = 2 * 1024 * 1024

# `](target "title")` — capture the target up to whitespace or the closing paren.
_MD_LINK_RE = re.compile(r"\]\(\s*<?([^)>\s]+)>?")
# `[[Target]]` or `[[Target|alias]]` — capture Target.
_WIKI_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def _to_posix(rel: str) -> str:
    return rel.replace("\\", "/")


def _is_external(href: str) -> bool:
    return bool(urlparse(href).scheme) or href.startswith("//") or href.startswith("#")


def _read(abs_path: Path, is_md: bool) -> tuple[dict, str]:
    try:
        if abs_path.stat().st_size > MAX_CONTENT_BYTES:
            return {}, ""
        raw = abs_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}, ""
    if is_md:
        try:
            post = frontmatter.loads(raw)
            return dict(post.metadata), post.content
        except Exception:
            return {}, raw
    return {}, raw


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
    stem_map: dict[str, str] = {}   # 'foo' -> 'a/b/foo.md'  (first wins on collision)
    name_map: dict[str, str] = {}   # frontmatter name (lower) -> id
    truncated = False

    for rel, abs_path, _mtime, _kind in iter_text_files(cfg):
        if len(nodes) >= GRAPH_MAX_NODES:
            truncated = True
            break
        nid = _to_posix(rel)
        is_md = abs_path.suffix.lower() in MARKDOWN_EXTENSIONS
        meta, body = _read(abs_path, is_md)
        tags = tagger.extract_tags(nid, meta, body)
        nodes[nid] = {
            "id": nid,
            "label": str(meta.get("name") or abs_path.name),
            "type": tags["type"],
            "subsystem": tags["subsystem"],
            "project": tags["project"],
            "degree": 0,
        }
        stem_map.setdefault(posixpath.splitext(abs_path.name)[0].lower(), nid)
        if meta.get("name"):
            name_map.setdefault(str(meta["name"]).strip().lower(), nid)

        refs: dict[str, list] = {"md": [], "wiki": [], "skills": []}
        if is_md:
            base_dir = posixpath.dirname(nid)
            refs["md"] = [(m.group(1), base_dir) for m in _MD_LINK_RE.finditer(body)]
            refs["wiki"] = [m.group(1).strip() for m in _WIKI_RE.finditer(body)]
            if tags["type"] == "agent":
                sk = meta.get("skills")
                if isinstance(sk, str):
                    refs["skills"] = [s.strip() for s in sk.replace(",", " ").split()]
                elif isinstance(sk, (list, tuple)):
                    refs["skills"] = [str(s).strip() for s in sk]
        raw_refs[nid] = refs

    edges: list[dict] = []
    seen: set[tuple] = set()

    def add_edge(src: str, tgt: str | None, kind: str) -> None:
        if tgt and tgt in nodes and tgt != src and (src, tgt, kind) not in seen:
            seen.add((src, tgt, kind))
            edges.append({"source": src, "target": tgt, "kind": kind})

    def resolve_skill(name: str) -> str | None:
        tgt = name_map.get(name.lower())
        if tgt:
            return tgt
        guess = f".claude/skills/{name}/SKILL.md"
        return guess if guess in nodes else None

    for nid, refs in raw_refs.items():
        for href, base_dir in refs["md"]:
            if _is_external(href):
                continue
            tgt = _resolve_rel(href, base_dir)
            if tgt and tgt not in nodes and (tgt + ".md") in nodes:
                tgt = tgt + ".md"      # link omitting the .md extension
            add_edge(nid, tgt, "link")
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
