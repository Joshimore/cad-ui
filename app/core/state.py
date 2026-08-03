"""Per-workspace UI state (favorites) stored in <workspace>/.cad-ui/state.json."""
from __future__ import annotations

import json
from pathlib import Path

from .config import WorkspaceConfig

STATE_FILENAME = "state.json"


def _state_path(cfg: WorkspaceConfig) -> Path:
    return cfg.state_dir / STATE_FILENAME


def load_favorites(cfg: WorkspaceConfig) -> list[str]:
    path = _state_path(cfg)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        favs = data.get("favorites", [])
        return [str(f) for f in favs if isinstance(f, str)]
    except (json.JSONDecodeError, OSError):
        return []


def toggle_favorite(cfg: WorkspaceConfig, rel_path: str) -> bool:
    """Add/remove a favorite. Returns True if it is a favorite after the call."""
    favorites = load_favorites(cfg)
    normalized = rel_path.replace("\\", "/")
    favorites_norm = [f.replace("\\", "/") for f in favorites]
    if normalized in favorites_norm:
        favorites = [f for f in favorites if f.replace("\\", "/") != normalized]
        now_favorite = False
    else:
        favorites.append(normalized)
        now_favorite = True
    cfg.state_dir.mkdir(exist_ok=True)
    _state_path(cfg).write_text(
        json.dumps({"favorites": favorites}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return now_favorite


def is_favorite(cfg: WorkspaceConfig, rel_path: str) -> bool:
    return rel_path.replace("\\", "/") in [f.replace("\\", "/") for f in load_favorites(cfg)]


def prune_favorites(cfg: WorkspaceConfig, rel_prefix: str) -> None:
    """Drop favorites under a removed/moved folder so fav_count stays honest."""
    favorites = load_favorites(cfg)
    prefix = rel_prefix.replace("\\", "/")
    kept = [f for f in favorites if not f.replace("\\", "/").startswith(prefix)]
    if len(kept) == len(favorites):
        return
    cfg.state_dir.mkdir(exist_ok=True)
    _state_path(cfg).write_text(
        json.dumps({"favorites": kept}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
