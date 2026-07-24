"""Adapter: knowledge base — trust-rated, version-stamped cards from
<workspace>/knowledge-base.

Auto-detected: the panel exists only once knowledge-base/ holds at least one card
(a .md file). Each card carries a trust level (L0–L5) and the software version it
applies to. Anti-patterns (what does NOT work) live here too, flagged by `type`.
The folder itself is a shared skeleton (its `.gitkeep` is committed); the cards
stay local (git-ignored), like the team Working directory.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import frontmatter

from ..core.config import WorkspaceConfig

KB_DIRNAME = "knowledge-base"
TRUST_LEVELS = ("L0", "L1", "L2", "L3", "L4", "L5")


@dataclass
class Card:
    title: str
    trust: str                       # "L0".."L5" or "" if unset
    version: str                     # software + version the card applies to
    kind: str                        # "card" | "anti-pattern"
    rel_path: str
    tags: list[str] = field(default_factory=list)
    created: str = ""
    stale: bool = False              # manually flagged as outdated for its version


def _card_files(cfg: WorkspaceConfig) -> list[Path]:
    directory = cfg.root / KB_DIRNAME
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.rglob("*.md") if p.name.lower() != "readme.md")


def detect(cfg: WorkspaceConfig) -> bool:
    return bool(_card_files(cfg))


def _norm_trust(v) -> str:
    s = str(v).strip().upper()
    if s and not s.startswith("L"):
        s = "L" + s
    return s if s in TRUST_LEVELS else ""


def _norm_tags(v) -> list[str]:
    if isinstance(v, str):
        return [t.strip() for t in v.replace(",", " ").split() if t.strip()]
    if isinstance(v, (list, tuple)):
        return [str(t) for t in v if str(t).strip()]
    return []


def list_cards(cfg: WorkspaceConfig) -> list[Card]:
    cards: list[Card] = []
    for path in _card_files(cfg):
        try:
            meta = frontmatter.loads(path.read_text(encoding="utf-8", errors="replace")).metadata
        except Exception:
            meta = {}
        kind = str(meta.get("type", "card")).strip().lower()
        if kind not in ("card", "anti-pattern"):
            kind = "card"
        cards.append(Card(
            title=str(meta.get("title") or path.stem),
            trust=_norm_trust(meta.get("trust", "")),
            version=str(meta.get("version", "")),
            kind=kind,
            rel_path=str(path.relative_to(cfg.root)).replace("\\", "/"),
            tags=_norm_tags(meta.get("tags")),
            created=str(meta.get("created", "")),
            stale=bool(meta.get("stale", False)),
        ))
    # cards before anti-patterns; within each, highest trust first, then title
    rank = {t: i for i, t in enumerate(reversed(TRUST_LEVELS))}  # L5->0 … L0->5
    cards.sort(key=lambda c: (c.kind == "anti-pattern", rank.get(c.trust, 99), c.title.lower()))
    return cards


def stats(cfg: WorkspaceConfig) -> dict:
    cards = list_cards(cfg)
    by_trust = {t: 0 for t in TRUST_LEVELS}
    for c in cards:
        if c.trust in by_trust:
            by_trust[c.trust] += 1
    return {
        "total": len(cards),
        "cards": sum(1 for c in cards if c.kind == "card"),
        "anti": sum(1 for c in cards if c.kind == "anti-pattern"),
        "stale": sum(1 for c in cards if c.stale),
        "by_trust": by_trust,
    }
