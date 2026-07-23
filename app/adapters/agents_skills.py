"""Adapter: agents & skills registry from <workspace>/.claude.

Auto-detected: the panel exists only if .claude/agents/*.md or
.claude/skills/*/SKILL.md are present in the workspace.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import frontmatter

from ..core.config import WorkspaceConfig

AGENTS_SUBDIR = Path(".claude") / "agents"
SKILLS_SUBDIR = Path(".claude") / "skills"


@dataclass
class RegistryItem:
    name: str
    description: str
    rel_path: str        # workspace-relative path to the source .md
    tools: str = ""      # agents only


def detect(cfg: WorkspaceConfig) -> bool:
    return bool(_agent_files(cfg) or _skill_files(cfg))


def _agent_files(cfg: WorkspaceConfig) -> list[Path]:
    directory = cfg.root / AGENTS_SUBDIR
    return sorted(directory.glob("*.md")) if directory.is_dir() else []


def _skill_files(cfg: WorkspaceConfig) -> list[Path]:
    directory = cfg.root / SKILLS_SUBDIR
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*/SKILL.md"))


def _load_meta(path: Path) -> dict:
    try:
        return frontmatter.loads(path.read_text(encoding="utf-8", errors="replace")).metadata
    except Exception:
        return {}


def list_agents(cfg: WorkspaceConfig) -> list[RegistryItem]:
    items = []
    for path in _agent_files(cfg):
        meta = _load_meta(path)
        tools = meta.get("tools", "")
        if isinstance(tools, list):
            tools = ", ".join(str(t) for t in tools)
        items.append(RegistryItem(
            name=str(meta.get("name", path.stem)),
            description=str(meta.get("description", "")),
            rel_path=str(path.relative_to(cfg.root)),
            tools=str(tools),
        ))
    return items


def list_skills(cfg: WorkspaceConfig) -> list[RegistryItem]:
    items = []
    for path in _skill_files(cfg):
        meta = _load_meta(path)
        items.append(RegistryItem(
            name=str(meta.get("name", path.parent.name)),
            description=str(meta.get("description", "")),
            rel_path=str(path.relative_to(cfg.root)),
        ))
    return items
