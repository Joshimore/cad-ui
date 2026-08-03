---
name: validation-methodology
description: The end-to-end method for validating AI/technical claims — the question→hypotheses→board→sources→claims→test→decision cycle, the L0–L5 trust scale, tiered validation depth, and the trace-to-disk discipline. Use this whenever validating, fact-checking, or trust-rating any technical claim, evaluating an AI suggestion, deciding whether a technique/setting/feature is reliable, or whenever the user asks "is this true / will this work / should we use this." Apply it even when the user does not say the word "validate."
---

# Validation Methodology

This skill governs HOW the system validates anything. Depth detail lives in `methodology/`; read the file named below when you need it.

## The cycle
`question → hypotheses → board → sources → claims → test → decision`
Full walkthrough: `methodology/validation-cycle.md`.

## Trust scale (L0–L5)
Confidence is always explicit. Read `methodology/trust-levels.md` for full definitions and the promotion rules. Two rules to remember always:
- A claim cannot exceed **L2** without confirming it applies to the **target version**.
- A claim cannot reach **L1** on internal agent agreement alone — that needs independent external corroboration.

## Tiered depth — match process to stakes
Do not run the full board for trivial checks. Choose:
- **Fast lane (L0–L2):** orchestrator + `researcher` + `source-auditor` + version check. For simple existence/syntax/version lookups.
- **Standard (L2–L3):** add `generator` + `alternative`, then `skeptic`, then `test-designer` + execution.
- **Deep/Board (L3→L5 or conflict):** full roster; consider promoting to an Agent Team.
Always run the version gate. State your chosen tier in one line and proceed.

## Trace-to-disk
Every spawned agent writes its own file to `sessions/<session>/trace/<NN>-<role>.md`. The reporter builds the report from these files. The orchestrator's memory is not the trace. This is what makes results reproducible by a teammate.

## The version gate
Non-negotiable and first. See `methodology/version-discipline.md`. If a claim fails because of a version mismatch, all other work on it is wasted — establish the version before validating.

## Board mechanics & promotion
Subagent pipeline by default; Agent Team on demand (user request, unresolved conflict, or L4→L5). See `methodology/board-roles.md`.

## Terminal states
Every claim ends as one of: promoted to a level with evidence; `UNVERIFIABLE` (insufficient evidence — capped at L0/L1); or rejected (a blocking objection held). Never let an unsupported claim pass silently.

---

# Session protocol — how to actually run one

The sections above are the method. This section is the operating procedure. Follow it in
order; it is what makes a session reproducible instead of merely well-reasoned.
Module boundary, environment contract and invariants: `MODULE.md`.

## 1. Bootstrap — before any work
Ask two questions up front (use `AskUserQuestion`):
1. **Working language** — EN / RU / UK, default **UK**. It governs conversation and output
   documents only; this file, agent prompts and field labels stay English.
2. **Session type** — **Validation** or **Other**. "Other" skips everything below: help
   directly, still bound by the honesty rules.

For a Validation session, then **establish the target version** — software + version/patch,
plugins/custom nodes, hardware where it matters. Do not start validating against an unknown
version; ask if the user has not stated it. This is the version gate and it is first.

## 2. Create the session folder
`sessions/<YYYY-MM-DD>-<short-slug>/` containing `trace/` and `telemetry/`. The report lands
in the session root. Announce the chosen tier in one line, then proceed.

## 3. Spawn agents with the trace path
Every agent you spawn must be told its **session trace path** and required to write its own
file to `sessions/<session>/trace/<NN>-<role>.md` (`NN` = two-digit order). Subagents *can*
write trace files and test protocols — the harness only blocks report files. An agent that
returns findings without writing its trace has not finished its job.

## 4. Load the domain pack
Check `domains/` for a pack matching the task. If one applies, load its `knowledge.md` and
`sources.md`, and read `test_execution` (`human` | `auto`) from `pack.md` — that decides
whether `test-runner` executes the test or the human does. Tell `test-designer` which mode
applies **and** whether the test operator is non-technical (that is what triggers the plain
protocol). If no pack fits, say so and fall back to the core — never block on a missing pack.

## 5. Maintain telemetry — you, not the agents
Fill `sessions/<session>/telemetry/telemetry.md` from `templates/session-telemetry-template.md`
using each agent's return fields (`subagent_tokens`, `tool_uses`, `duration_ms`). Scale the
detail to the tier: on Deep/Board append a row per agent as it returns; on Fast lane and
Standard a single summary row is enough. Bookkeeping must never compete with the validation.

## 6. Persist the outputs — the reporter cannot
`reporter` has Read/Glob/Grep only and returns the finished document **as text**, because the
harness refuses report-file writes from subagents. This is by design; do not work around it
with a different filename. **You** then write to disk:
- `sessions/<session>/REPORT.md` — verbatim, do not re-summarise it;
- knowledge cards into `knowledge-base/` (see `contracts/knowledge-base.md` for the required
  frontmatter — a card without it is invisible to the UI);
- anti-patterns as **one file each** into `knowledge-base/anti-patterns/`, version-stamped;
- one row appended to `sessions/LOG.md`.

Bulky deliverables (PDFs, datasets, image sets) do **not** go in the session folder — put
them under `Working directory/<project>/output/` and link them from the report.

## 7. Honesty rules — enforced, not aspirational
- **Internal agreement is not corroboration.** Agents agreeing with each other is one model
  talking to itself; it stays at L0+. L1 needs independent external sources. Reward source
  *diversity*, not count.
- **Document both outcomes.** Successes become cards; rejected claims and failed tests become
  version-stamped anti-patterns plus an Error/Hallucination Log entry. An undocumented failure
  teaches nothing.
- **`UNVERIFIABLE` never becomes an anti-pattern.** "Could not verify" is not "verified false";
  recording it as a negative pattern poisons the base with false negatives.
- **An anti-pattern match flags, it never auto-rejects.** Re-check against the current version —
  a negative result from an old version can be wrong now.
- **Record where it does NOT work**, what was not tested, and what is unsafe to apply.
- **Non-conformism.** Disagree when there is a real reason, propose alternatives, defend your
  reasoning, never be a yes-man — but substantively. Manufactured objections drown the signal.

## 8. Output language
Prose in the session language (default UK). Technical terms, tool names, version identifiers,
file and parameter names, UI paths and quoted source claims stay **English**. Template field
labels stay English.

## Definition of done
A teammate can reproduce **at least the test** from the documents alone, with no verbal
explanation, and the decision — including limitations and "do not apply to" notes — is
explicit. The recommendation is the system's; the decision is the human's.
