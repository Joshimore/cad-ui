# Contract — `sessions/`

The second of the two folder names this module expects from its host (the other is
`knowledge-base/`). It holds the **process record**: what was actually done, by which agent,
in what order.

The folder does not ship with the repository. Create it on the first validation session,
together with `LOG.md`, from the layout below.

## Layout

```
sessions/
├─ LOG.md                            local index, newest first, one row per finished session
└─ <YYYY-MM-DD>-<short-slug>/
   ├─ trace/<NN>-<role>.md           one file per agent, NN = order of execution
   ├─ telemetry/telemetry.md         tokens, tool calls, duration
   ├─ test-protocol-technical.md     for a human-run test
   ├─ test-protocol-plain.md         only when the test operator is non-technical
   └─ REPORT.md                      the single self-contained session report
```

`LOG.md` table columns: `Date | Session | Type | Outcome | Report | Project`.

## Who writes what

| Artefact | Written by |
|---|---|
| `trace/<NN>-<role>.md` | the agent itself — subagents may write trace files and test protocols |
| `test-protocol-*.md` | `test-designer` |
| `telemetry/telemetry.md` | the orchestrator, from each agent's return fields |
| `REPORT.md` | the **orchestrator** — `reporter` is read-only and returns text |
| the `LOG.md` row | the orchestrator, when the session finishes |

## Contents are personal

`sessions/` is git-ignored by the host, like `knowledge-base/`. A trace records what *you*
investigated, on which project, and what was rejected along the way — it is not team material by
default.

Sharing is **deliberate, not automatic**: when a result should reach the team, copy the finished
`REPORT.md` (or a generated document) to `Working directory/<project>/output/` as a deliverable.
That keeps the raw process private while making the conclusion sharable on purpose.

## Why the trace exists at all

A subagent returns only its final message; its working reasoning is lost from the orchestrator's
context. If the trail lived only in that context, "reproducible" would be a false claim. An agent
that returns findings without writing its trace file has not finished its job.

The bar: a teammate handed these documents can reproduce **at least the test** with no verbal
explanation.
