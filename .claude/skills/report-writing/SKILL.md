---
name: report-writing
description: How to produce the single self-contained session report and the Gold-KB cards — what goes in the report, how to fill the template from the on-disk trace, the output-language rules, and how/when to promote a knowledge card. Use whenever writing up a validation session, producing the session document, filling the report template, or updating the knowledge base. This is the reporter's reference.
---

# Report Writing

## One report per session, self-contained
Fill `templates/session-report-template.md` into `sessions/<session>/REPORT.md`. It contains, in order: the session narrative, the structured form (with versions), the Knowledge Cards produced this session, the Error/Hallucination Log entries, and the decision-ready brief. No separate documents.

## Who writes the file: reporter produces, orchestrator persists
The `reporter` is read-only: it returns the finished report body + explicit KB deltas **as text**, and the **orchestrator** persists `REPORT.md` verbatim, creates the L4+ Knowledge Cards, appends anti-patterns, and applies the `INDEX.md` metrics deltas. The full rationale (the harness deliberately blocks subagents from writing report files) lives in its canonical home, **`CLAUDE.md` §6** — don't restate it here, and don't try to evade the guard by renaming the file.

## Build it from disk, not memory
Read the entire `sessions/<session>/trace/` folder and assemble the report from those files. The trace is the source of truth; the orchestrator's recollection is not.

## Output-language rules
- Prose in the working language chosen at session start (default **UK**).
- Keep in **English**: technical terminology, tool/library names, version identifiers (e.g. `0.5.0b`), file/parameter names, and any directly quoted source claims.
- Template field labels stay in English.

## The decision-ready brief
For each claim give the human: trust level, version status, the key dissent (if any), and the recommendation (use / don't use / test further / use only with limits). Keep it tight enough to decide from at a glance.

## Knowledge Cards → Gold KB
Use `templates/knowledge-card-template.md`. Every card is **version-stamped**. Promote a card to `knowledge-base/<domain>/` (one subfolder per domain, mirroring `domains/`) only when it reached **L4+** — the trust level is a card field/INDEX column, never a folder. On promotion, update `knowledge-base/INDEX.md` and increment the running metrics (hallucinations caught, claims promoted/rejected, version mismatches caught).

## Error/Hallucination Log
Use `templates/error-hallucination-log-template.md` for every model/source/workflow error caught — especially version hallucinations. These entries are the system's main signal that it is working.
