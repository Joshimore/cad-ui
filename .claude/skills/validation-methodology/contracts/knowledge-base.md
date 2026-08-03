# Contract — `knowledge-base/`

The knowledge base is one of the two folder names this module expects from its host (the
other is `sessions/`). This file is the authoritative definition of the card format; the
host's own documentation should link here rather than restate it.

## Layout

```
knowledge-base/
├─ <slug>.md                     a card: something that works, at some trust level
└─ anti-patterns/<AP-NNN>-<slug>.md   a negative pattern: something that did not
```

**One file per entry.** The host reads *a file* as a card. Several entries collected into one
document render as a single row, and the individual findings become invisible — this is the
single most common way to break the panel.

**Contents are personal.** `knowledge-base/*` is git-ignored by the host; only the empty
skeleton is shared. A validation base belongs to whoever ran the sessions — what a team shares
is the format, not the findings. Never add ignore exceptions to push cards into a shared repo.

## Required frontmatter

| Field | Value | Notes |
|---|---|---|
| `title` | quoted string | **Quote it.** A colon inside an unquoted YAML scalar aborts the whole frontmatter block, and the entry silently loses every field. |
| `type` | `card` \| `anti-pattern` | Anything else is treated as `card`. |
| `trust` | `L0`–`L5` | The level the claim **actually reached**, not a target. Unrecognised values become empty and sort last. |
| `version` | quoted string | The version stamp. The card is valid only for it. |
| `tags` | list of strings | Optional. |
| `created` | `YYYY-MM-DD` | Optional. |
| `stale` | `true` \| `false` | Manual flag: the card no longer holds for its version. A generic tool cannot know the "current" version of arbitrary software, so a human sets this. |

Trust is a **field, never a folder**. Promoting L2→L3 edits the file in place; it never moves
it. The panel ranks cards by trust and puts anti-patterns after cards.

For an anti-pattern, `trust` measures how well established the **negative** result is — a
reject backed by an executed test outranks a reasoned one.

## Do not put anything else under `knowledge-base/`

The host scans the folder **recursively** and treats every `.md` it finds as a card. An index
file, a README, a session report, a trace file — each would appear as a bogus row with no trust
and no version. There is deliberately **no aggregate index file**: the host computes the tally
from the cards themselves.

## Two rules that outlive any format detail

- A match against an anti-pattern **raises a flag and triggers a re-check against the current
  version — it never auto-rejects.** A negative result from an older version can be wrong now.
- `UNVERIFIABLE` never becomes an anti-pattern. "Could not verify" is not "verified false";
  recording it as a negative pattern poisons the base with false negatives.
