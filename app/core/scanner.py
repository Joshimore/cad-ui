"""Lazy directory listing, bounded recent-files walk, path safety guard."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .config import (
    IMAGE_EXTENSIONS,
    MARKDOWN_EXTENSIONS,
    TEXT_EXTENSIONS,
    WorkspaceConfig,
)

RECENT_LIMIT = 30
RECENT_MAX_DIRS = 2000  # hard cap on directories visited per recent-files request
INDEX_MAX_DIRS = 20000  # runaway guard for a full index walk


class PathOutsideWorkspace(Exception):
    pass


def resolve_safe(cfg: WorkspaceConfig, rel_path: str) -> Path:
    """Resolve a workspace-relative path, refusing anything outside the root."""
    candidate = (cfg.root / rel_path).resolve() if rel_path else cfg.root
    if candidate != cfg.root and not candidate.is_relative_to(cfg.root):
        raise PathOutsideWorkspace(rel_path)
    return candidate


def file_kind(path: Path) -> str:
    """Classify a file for the UI: markdown / text / image / binary."""
    ext = path.suffix.lower()
    if ext in MARKDOWN_EXTENSIONS:
        return "markdown"
    if ext in TEXT_EXTENSIONS:
        return "text"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    return "binary"


@dataclass
class Entry:
    name: str
    rel_path: str
    is_dir: bool
    kind: str = ""       # for files: markdown/text/image/binary
    excluded: bool = False  # shown greyed-out, not expandable/viewable


def list_dir(cfg: WorkspaceConfig, rel_path: str) -> list[Entry]:
    """One directory level: dirs first, then files, alphabetical; excluded items flagged."""
    directory = resolve_safe(cfg, rel_path)
    if not directory.is_dir():
        return []
    dirs: list[Entry] = []
    files: list[Entry] = []
    try:
        with os.scandir(directory) as it:
            for de in it:
                rel = str(Path(rel_path) / de.name) if rel_path else de.name
                if de.is_dir(follow_symlinks=False):
                    dirs.append(Entry(de.name, rel, True, excluded=cfg.is_dir_excluded(de.name)))
                elif de.is_file(follow_symlinks=False):
                    kind = file_kind(Path(de.name))
                    files.append(Entry(de.name, rel, False, kind=kind,
                                       excluded=cfg.is_file_excluded(de.name)))
    except OSError:
        return []
    key = lambda e: e.name.lower()
    return sorted(dirs, key=key) + sorted(files, key=key)


def iter_text_files(cfg: WorkspaceConfig):
    """Yield (rel_path, abs_path, mtime, kind) for every indexable markdown/text
    file, skipping excluded dirs/files. Bounded by INDEX_MAX_DIRS."""
    stack: list[Path] = [cfg.root]
    visited = 0
    while stack and visited < INDEX_MAX_DIRS:
        current = stack.pop()
        visited += 1
        try:
            with os.scandir(current) as it:
                for de in it:
                    if de.is_dir(follow_symlinks=False):
                        if not cfg.is_dir_excluded(de.name):
                            stack.append(Path(de.path))
                    elif de.is_file(follow_symlinks=False):
                        kind = file_kind(Path(de.name))
                        if kind in ("markdown", "text") and not cfg.is_file_excluded(de.name):
                            try:
                                mtime = de.stat(follow_symlinks=False).st_mtime
                            except OSError:
                                continue
                            rel = str(Path(de.path).relative_to(cfg.root))
                            yield rel, Path(de.path), mtime, kind
        except OSError:
            continue


def recent_files(cfg: WorkspaceConfig) -> list[tuple[Entry, float]]:
    """Top markdown/text files by mtime. Bounded walk: excluded dirs skipped,
    at most RECENT_MAX_DIRS directories visited."""
    results: list[tuple[Entry, float]] = []
    stack: list[Path] = [cfg.root]
    visited = 0
    while stack and visited < RECENT_MAX_DIRS:
        current = stack.pop()
        visited += 1
        try:
            with os.scandir(current) as it:
                for de in it:
                    if de.is_dir(follow_symlinks=False):
                        if not cfg.is_dir_excluded(de.name):
                            stack.append(Path(de.path))
                    elif de.is_file(follow_symlinks=False):
                        kind = file_kind(Path(de.name))
                        if kind in ("markdown", "text") and not cfg.is_file_excluded(de.name):
                            rel = str(Path(de.path).relative_to(cfg.root))
                            try:
                                mtime = de.stat(follow_symlinks=False).st_mtime
                            except OSError:
                                continue
                            results.append((Entry(de.name, rel, False, kind=kind), mtime))
        except OSError:
            continue
    results.sort(key=lambda pair: pair[1], reverse=True)
    return results[:RECENT_LIMIT]
