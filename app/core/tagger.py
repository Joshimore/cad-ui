"""Heuristic auto-tagging: derive tags from a file's path, frontmatter and content.

Domain-agnostic on purpose — this tool runs on any workspace, so tags come from
generic conventions (top-level folder, filename patterns, frontmatter), never from
one team's specific layout.
"""
from __future__ import annotations

import re
from pathlib import PurePosixPath

DATE_RE = re.compile(r"(20\d{2}-\d{2}-\d{2})")


def _norm(rel_path: str) -> PurePosixPath:
    return PurePosixPath(rel_path.replace("\\", "/"))


def _subsystem(p: PurePosixPath) -> str:
    """Top-level folder, or '(root)' for files directly in the workspace."""
    parts = p.parts
    return parts[0] if len(parts) > 1 else "(root)"


def _type(p: PurePosixPath, meta: dict) -> str:
    """Generic document type by frontmatter, then filename/path conventions."""
    ft = str(meta.get("type", "")).strip().lower()
    if ft:
        return ft
    name = p.name.lower()
    ext = p.suffix.lower()
    parts = [seg.lower() for seg in p.parts]
    if name in ("readme.md", "claude.md") or name.endswith(".readme.md"):
        return "doc"
    if name == "skill.md":
        return "skill"
    if "agents" in parts and ext == ".md":
        return "agent"
    if name.startswith("report") or name == "report.md":
        return "report"
    if "track" in parts:
        return "track"
    if "knowledge-base" in parts or "knowledge_base" in parts:
        return "card"
    if "protocol" in name:
        return "protocol"
    if ext in (".py", ".js", ".ts", ".sh", ".bat", ".ps1"):
        return "script"
    if ext in (".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".xml"):
        return "config"
    return "doc"


def _project(p: PurePosixPath) -> str:
    """Project label from a PROJECTS/<bucket>/<project>/... path, else ''."""
    parts = p.parts
    for i, seg in enumerate(parts):
        if seg.lower() == "projects" and i + 2 < len(parts):
            return parts[i + 2]
    return ""


def extract_tags(rel_path: str, meta: dict, content: str) -> dict:
    """Return the tag fields for one file. `meta` is parsed frontmatter (may be {})."""
    p = _norm(rel_path)
    tags: dict[str, str] = {
        "subsystem": _subsystem(p),
        "type": _type(p, meta),
        "project": _project(p),
    }

    # date: filename prefix first, then frontmatter, then any date in the name
    date = ""
    m = DATE_RE.match(p.name)
    if m:
        date = m.group(1)
    elif meta.get("date"):
        dm = DATE_RE.search(str(meta["date"]))
        date = dm.group(1) if dm else ""
    tags["date"] = date

    # free-form keywords for the FTS 'tags' column: frontmatter name/tags + values
    keywords: list[str] = [tags["subsystem"], tags["type"]]
    if tags["project"]:
        keywords.append(tags["project"])
    if meta.get("name"):
        keywords.append(str(meta["name"]))
    ft = meta.get("tags")
    if isinstance(ft, str):
        keywords.extend(ft.replace(",", " ").split())
    elif isinstance(ft, (list, tuple)):
        keywords.extend(str(t) for t in ft)
    tags["keywords"] = " ".join(dict.fromkeys(k for k in keywords if k))
    return tags
