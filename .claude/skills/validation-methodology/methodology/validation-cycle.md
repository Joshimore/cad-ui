# The Validation Cycle (full reference)

`question → hypotheses → board → sources → claims → test → decision`

Every stage leaves a trace file on disk. This is the universal cycle; it is independent of any specific tool.

## 1. Question
Frame the technical question so the answer is **checkable**, not generic. Bad: "is this AI good for textures?" Good: "in `<software> <version>`, does `<feature>` produce a valid texture set under the `<platform>` budget of N MB?" Record the target version here — the cycle does not proceed without it.

## 2. Hypotheses
`generator` proposes a primary approach; `alternative` proposes an independent competing one. Each is a falsifiable hypothesis at **L0**. On the fast lane this stage is skipped.

## 3. Board
The roles examine the hypotheses. By default this is the adversarial **subagent pipeline**; for L4→L5 or unresolved conflict it may be promoted to an **Agent Team** (see `board-roles.md`). The board must leave a trace: hypotheses, arguments, disagreements between roles, sources, claims, risks, test, conclusion — not just a tidy answer.

## 4. Sources
`researcher` gathers evidence with provenance; `source-auditor` assigns L0–L5 and checks version applicability. Internal agreement does not count as corroboration (see `trust-levels.md`).

## 5. Claims
Turn model/source statements into concrete claims — test the **claim**, not the prose. Each claim carries its own trust level and version applicability.

## 6. Test
`test-designer` builds a reproducible protocol + capture template once a claim is at L2. Execution: `test-runner` for `auto` domains, the human for `manual` domains. A claim reaches **L3** only after a test is actually run (by machine or human).

## 7. Decision
`synthesizer` assembles the honest picture (disagreements preserved); `reporter` documents it; the **human** decides: use / don't use / test further / use only with limits. The recommendation is the system's; the decision is the human's.

## Definition of done
The cycle is complete when a teammate can **reproduce at least the test from the documentation alone**, with no verbal explanation, and the decision (including limitations and "do not apply to" notes) is explicit.

## Documenting outcomes (every claim, not only successes)
Both successful and failed claims run through `synthesizer → reporter`. Successes become Knowledge Cards; **REJECTED** claims and failed tests become version-stamped anti-patterns (`knowledge-base/ANTI-PATTERNS.md`) plus Error Log entries; **UNVERIFIABLE** claims are recorded as such and are never turned into anti-patterns.
