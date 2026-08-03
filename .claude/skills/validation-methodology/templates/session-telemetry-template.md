# Run Telemetry — <SESSION TITLE>

<!--
HOW TO USE: the ORCHESTRATOR fills this file at sessions/<YYYY-MM-DD>_<slug>/telemetry/telemetry.md.
One telemetry file per session. Numbers come from each subagent's return fields
(`subagent_tokens` / `tool_uses` / `duration_ms`). Context snapshots come from /context.
Detail scales to the tier: Deep/Board = the full per-agent table below; Fast lane / Standard
= a single summary/total row is enough (don't let bookkeeping compete with the work).
Field labels stay in English; notes may be in the session language.
-->

## How to read these numbers
- **subagent tokens** = output tokens spent *inside each subagent's isolated context*. They do **not** accumulate in the orchestrator's main context (only the agent's final message returns). So total subagent tokens and main-context fill (`/context`) are **different scales — do not add them**.
- **duration** = wall-clock per agent. Where agents ran **in parallel** (e.g. `generator` ⟂ `alternative`), real wall-clock = max of the pair, not the sum. The per-session total below is the arithmetic sum (upper bound), with parallel stretches flagged.

---

## Per-agent breakdown

| # | Agent | Tokens | Tool uses | Duration | Notes |
|---|-------|-------:|----------:|---------:|-------|
| 01 | <researcher> | <0> | <0> | <0 s> | <e.g. foundation pass> |
| 02 | <...> | <0> | <0> | <0 s> | |
| | **Total** | **<0>** | **<0>** | **<0 s>** | <parallel stretches noted> |

⟂ = ran in parallel (one message). Real wall-clock for the pair ≈ max(a, b), not a+b.

## Outcome
- **Tier:** <Fast lane | Standard | Deep/Board>
- **Result:** <Promoted Lx | UNVERIFIABLE | REJECTED + anti-pattern ID>
- **Most expensive agent:** <agent> (<n> tokens). **Longest:** <agent> (<n> s).

## Main-thread context (`/context`, model + window)
| Point | Tokens | % |
|-------|-------:|--:|
| <after key step> | <n>k / 1M | <n> % |

> Scale contrast: subagents spent **<n>k** in total, but main context stayed at **<n>k** — isolated agent contexts never flow into the main dialog. That is the point of trace-to-disk: heavy reasoning lives in subagents and on disk, not in the orchestrator's window.

## Notes
- <anything notable: blocked tool calls, retries, parallelism, infra issues>
