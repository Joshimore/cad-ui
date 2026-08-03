# Validation module — boundary, contract, and how to replace it

This file exists so the search-and-validation system can be identified, modified, or
swapped out **as one piece**, without reading the whole repository. CAD UI is a *wrapper*:
the engine below must work with the server stopped. Nothing here may depend on `app/`.

## What belongs to this module

| Path | Role |
|---|---|
| `.claude/skills/validation-methodology/` | the method: `SKILL.md` + `methodology/` + `templates/` + `domains/` |
| `.claude/skills/source-trust/` | deep reference: how to rate sources L0–L5 |
| `.claude/skills/report-writing/` | deep reference: how to write the session report and KB cards |
| `.claude/agents/` — the 10 validation agents | `researcher`, `source-auditor`, `generator`, `alternative`, `skeptic`, `test-designer`, `test-runner`, `synthesizer`, `reporter`, `learning-curator` |
| `knowledge-base/` — cards + `anti-patterns/` | the distilled output that outlives a session |
| `sessions/` | `LOG.md` + `<session>/{trace,telemetry,REPORT.md}` — the process record |

## What does NOT belong to it

`cvd-docs` and the `docx/pptx/pdf/xlsx` skills (document generation) · `.claude/assets/`
(brand fonts, used by `cvd-docs`) · the `status` skill · `Working directory/` (team
projects and tasks — owned by CAD UI itself) · everything under `app/`.

Deleting this module must leave all of the above working.

## Environment contract

The module expects exactly **two folder names** to exist in the workspace root:

- `knowledge-base/` — read at session bootstrap to re-check version stamps, written when a
  claim is promoted or rejected. Format: `contracts/knowledge-base.md`.
- `sessions/` — every agent writes its own trace file here; the orchestrator writes the
  report, the telemetry and the `LOG.md` row. Format: `contracts/sessions.md`.

These two names are the whole coupling to the host repository. Nothing else is assumed. Both
are git-ignored by the host: the module ships the *format*, never the findings.

## Three invariants

1. **Cross-module references go by skill name, never by path.** A path is allowed only
   inside a module's own folder, or to the two environment names above. This is what lets
   folders move without breaking 13 files.
2. **An adapter is a tolerant reader, never a gatekeeper.** It must not raise on unknown
   fields, must not reject a file, and may only show less than the module produces. The
   engine evolves faster than the UI.
3. **Headless test before every change.** Stop the server and run one validation end to
   end, from the framed question to a saved `REPORT.md`. If any step needed the UI, the
   wrapper has leaked into the engine.

## Decisions taken on port (2026-08-03)

- `sessions/` starts empty and is **git-ignored**, the same "shared skeleton, local contents"
  rule as `knowledge-base/` and `Working directory/`. A trace records what *you* investigated
  and what you rejected — it is not team material by default. Sharing a result is deliberate:
  copy the finished `REPORT.md` to `Working directory/<project>/output/` as a deliverable.
- No aggregate index file: the host computes the knowledge-base tally from the cards.
- The knowledge base holds cards at **all trust levels**, not only L4+. The origin repo's
  L4+-only rule produced zero cards in 13 sessions; an always-empty panel is worse than a
  ranked one.
- **Nothing accumulated in the origin repo is carried over** — no cards, no anti-patterns, no
  sessions. A validation base belongs to whoever ran the sessions; what the team shares is the
  folder and the format, not the findings.
- Anti-patterns follow the same rule as cards: **one file each** under
  `knowledge-base/anti-patterns/`, contents **local** (`knowledge-base/*` stays git-ignored, no
  exception). One file per entry is a hard requirement — the host reads a file as a card, so
  several anti-patterns in one file collapse into a single row.

## How to remove or replace the module

1. Delete the paths in "What belongs to this module".
2. Remove the trigger line from the root `CLAUDE.md` (the sentence that tells a session to
   invoke `validation-methodology`).
3. Delete `app/adapters/sessions.py` and its route/template if the sessions panel was built.

The «Реестр» and «База знаний» panels hide themselves automatically once their files are
gone — no configuration to unwind. To replace the system with a different one, keep the two
environment folder names and the three invariants, and the wrapper needs no changes at all.

## Port status

Done: module files in place · session protocol in `SKILL.md` · cross-module references rewritten
to skill names · the 10 agents (registry shows 11 agents, 8 skills) · both contracts written ·
template frontmatter aligned with the host and verified through its adapter · `sessions/`
git-ignored and documented · trigger line in the root `CLAUDE.md` · teammate setup note in
`INSTRUCTION.md`.

Pending: **the headless test** — one real validation run end to end with the server stopped,
which is the only proof the port works · one real domain pack (`domains/<name>/` with
`test_execution` in `pack.md`) · the sessions adapter in the host (`app/adapters/sessions.py`),
which must hide itself when `sessions/LOG.md` is absent, since the folder is git-ignored.
