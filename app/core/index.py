"""Full-text search index over the workspace (SQLite FTS5, stdlib only).

Storage: <workspace>/.cad-ui/index.db. Built in a background thread at startup,
kept fresh by an incremental mtime-based sync (no file watcher). Search returns
snippets; facets drive the tag filter chips.
"""
from __future__ import annotations

import html
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import frontmatter

from . import tagger
from .config import STATE_DIRNAME, WorkspaceConfig
from .scanner import iter_text_files

INDEX_FILENAME = "index.db"
MAX_CONTENT_BYTES = 2 * 1024 * 1024  # files above this are indexed by path/tags only
SYNC_THROTTLE_S = 5.0

# One write lock + last-sync clock per db path (single process, single workspace).
_locks: dict[str, threading.Lock] = {}
_last_sync: dict[str, float] = {}
_status: dict[str, str] = {}  # "building" | "ready"


@dataclass
class Hit:
    rel_path: str
    name: str
    kind: str
    subsystem: str
    type: str
    mtime: float
    snippet: str


def _db_path(cfg: WorkspaceConfig) -> Path:
    return cfg.root / STATE_DIRNAME / INDEX_FILENAME


def _lock(cfg: WorkspaceConfig) -> threading.Lock:
    key = str(_db_path(cfg))
    return _locks.setdefault(key, threading.Lock())


def _connect(cfg: WorkspaceConfig) -> sqlite3.Connection:
    cfg.state_dir.mkdir(exist_ok=True)
    conn = sqlite3.connect(_db_path(cfg), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5("
        "rel_path UNINDEXED, name, tags, content, tokenize='unicode61')"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS files("
        "rel_path TEXT PRIMARY KEY, name TEXT, mtime REAL, kind TEXT, "
        "subsystem TEXT, type TEXT, project TEXT, date TEXT)"
    )


def _read(abs_path: Path, kind: str) -> tuple[dict, str]:
    """Return (frontmatter_meta, body_text) for one file."""
    try:
        if abs_path.stat().st_size > MAX_CONTENT_BYTES:
            return {}, ""
        raw = abs_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}, ""
    if kind == "markdown":
        try:
            post = frontmatter.loads(raw)
            return dict(post.metadata), post.content
        except Exception:
            return {}, raw
    return {}, raw


def _index_one(conn: sqlite3.Connection, rel_path: str, abs_path: Path,
               mtime: float, kind: str) -> None:
    meta, body = _read(abs_path, kind)
    tags = tagger.extract_tags(rel_path, meta, body)
    name = abs_path.name
    conn.execute("DELETE FROM fts WHERE rel_path = ?", (rel_path,))
    conn.execute(
        "INSERT INTO fts(rel_path, name, tags, content) VALUES(?, ?, ?, ?)",
        (rel_path, name, tags["keywords"], body),
    )
    conn.execute(
        "INSERT OR REPLACE INTO files"
        "(rel_path, name, mtime, kind, subsystem, type, project, date) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
        (rel_path, name, mtime, kind, tags["subsystem"], tags["type"],
         tags["project"], tags["date"]),
    )


def build(cfg: WorkspaceConfig) -> None:
    """Full (re)build from scratch. Safe to run in a background thread."""
    key = str(_db_path(cfg))
    _status[key] = "building"
    with _lock(cfg):
        conn = _connect(cfg)
        try:
            _ensure_schema(conn)
            conn.execute("DELETE FROM fts")
            conn.execute("DELETE FROM files")
            with conn:
                for rel, abs_path, mtime, kind in iter_text_files(cfg):
                    _index_one(conn, rel, abs_path, mtime, kind)
        finally:
            conn.close()
    _last_sync[key] = time.time()
    _status[key] = "ready"


def sync(cfg: WorkspaceConfig, force: bool = False) -> None:
    """Incremental refresh: reindex changed files, drop vanished ones. Throttled."""
    key = str(_db_path(cfg))
    if _status.get(key) == "building":
        return
    now = time.time()
    if not force and now - _last_sync.get(key, 0.0) < SYNC_THROTTLE_S:
        return
    if not _db_path(cfg).exists():
        return
    with _lock(cfg):
        conn = _connect(cfg)
        try:
            _ensure_schema(conn)
            known = {row[0]: row[1] for row in conn.execute("SELECT rel_path, mtime FROM files")}
            seen: set[str] = set()
            with conn:
                for rel, abs_path, mtime, kind in iter_text_files(cfg):
                    seen.add(rel)
                    if known.get(rel) != mtime:
                        _index_one(conn, rel, abs_path, mtime, kind)
                for rel in known.keys() - seen:
                    conn.execute("DELETE FROM fts WHERE rel_path = ?", (rel,))
                    conn.execute("DELETE FROM files WHERE rel_path = ?", (rel,))
        finally:
            conn.close()
    _last_sync[key] = now


def _fts_query(q: str) -> str:
    """Turn a raw query into a safe FTS5 prefix MATCH expression."""
    import re
    tokens = re.findall(r"\w+", q, re.UNICODE)
    return " ".join(f"{t}*" for t in tokens)


def _safe_snippet(raw: str) -> str:
    """Escape file-derived text, then restore our highlight markers as <mark>."""
    return html.escape(raw).replace("\x02", "<mark>").replace("\x03", "</mark>")


def search(cfg: WorkspaceConfig, q: str, subsystem: str = "", ftype: str = "",
           limit: int = 50) -> list[Hit]:
    if not _db_path(cfg).exists():
        return []
    match = _fts_query(q)
    if not match:
        return []
    sql = (
        "SELECT f.rel_path, f.name, f.kind, f.subsystem, f.type, f.mtime, "
        "snippet(fts, 3, char(2), char(3), '…', 12) "
        "FROM fts JOIN files f ON f.rel_path = fts.rel_path "
        "WHERE fts MATCH ?"
    )
    params: list = [match]
    if subsystem:
        sql += " AND f.subsystem = ?"
        params.append(subsystem)
    if ftype:
        sql += " AND f.type = ?"
        params.append(ftype)
    sql += " ORDER BY rank LIMIT ?"
    params.append(limit)
    conn = _connect(cfg)
    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()
    return [Hit(r[0], r[1], r[2], r[3], r[4], r[5], _safe_snippet(r[6] or "")) for r in rows]


def facets(cfg: WorkspaceConfig) -> dict:
    """Counts per subsystem and per type, for the filter chips."""
    if not _db_path(cfg).exists():
        return {"subsystem": [], "type": [], "total": 0}
    conn = _connect(cfg)
    try:
        subs = conn.execute(
            "SELECT subsystem, COUNT(*) FROM files GROUP BY subsystem ORDER BY 2 DESC"
        ).fetchall()
        types = conn.execute(
            "SELECT type, COUNT(*) FROM files GROUP BY type ORDER BY 2 DESC"
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    except sqlite3.OperationalError:
        return {"subsystem": [], "type": [], "total": 0}
    finally:
        conn.close()
    return {
        "subsystem": [(s, c) for s, c in subs],
        "type": [(t, c) for t, c in types],
        "total": total,
    }
