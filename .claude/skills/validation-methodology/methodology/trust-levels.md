# Trust Levels L0–L5 (full reference)

Confidence is always explicit. A level is a claim about how much verification has happened — not how confident the model feels.

| Level | Meaning | How to use it |
|-------|---------|---------------|
| **L0** | One model said so. | Starting hypothesis only. |
| **L1** | Independent corroboration — multiple *independent* sources, or genuinely different models, agree. | Strengthened hypothesis, still not proof. |
| **L2** | Confirmed in sources that **apply to the target version**. | You may design a test. |
| **L3** | An internal test was conducted. | Limited conclusion allowed. |
| **L4** | Result reproduced (several examples / another person). | Working internal practice. |
| **L5** | Ready for a production pipeline. | Can be standardized and scaled. |

## Promotion rules
- **Version gate (to reach L2+):** the supporting sources must demonstrably apply to the target version. A source about another version does not raise the level.
- **Independence (to reach L1):** internal agreement between this system's agents/models is the same engine talking to itself and stays at **L0+**. L1 needs independent *external* corroboration. Source **diversity** matters more than source count.
- **Test required (to reach L3):** an actual test must be run — by `test-runner` (auto domains) or by the human (manual domains). A test *plan* alone does not grant L3.
- **Reproduction (to reach L4):** the result must hold on more than one example or when run by another person.
- **Production (to reach L5):** L4 plus the operational readiness to standardize.

## Critical reminder
Agreement among several models is at most **L1**. Real value appears only after sources, a test, reproduction, and documentation. Do not let a confident-sounding L0 masquerade as anything higher.

## Terminal states
- **Promoted** to a level, with evidence on disk.
- **UNVERIFIABLE** — insufficient evidence or research unavailable; capped at L0/L1 and labeled as such.
- **Rejected** — a BLOCKING objection (often a version mismatch) held.

## Decision rule (the auditor's rubric)
Promotion is mechanical, not a feeling. Promote a claim to a level **iff**:
- the sources support it, **AND**
- the version matches the target (Version Gate), **AND**
- no **BLOCKING** objection from the `skeptic` stands.

**MAJOR** objections cap the level or narrow the scope of the claim. **MINOR** objections are recorded but do not block. A BLOCKING objection — most often a version mismatch — caps or rejects regardless of how strong the sources look.

## Anti-patterns and the terminal states
- **REJECTED** claims (a BLOCKING objection held, or a test failed) become version-stamped **anti-patterns** — one file each under `knowledge-base/anti-patterns/`, format in `contracts/knowledge-base.md`. A future match to an anti-pattern **flags and triggers a re-check against the current version — it never auto-rejects.**
- **UNVERIFIABLE** is NOT an anti-pattern. "Could not verify" is not "verified false"; recording it as a negative pattern would poison the anti-pattern base with false negatives.
