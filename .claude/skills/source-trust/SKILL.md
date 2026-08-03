---
name: source-trust
description: How to evaluate sources and assign L0–L5 trust levels — source-type hierarchy, recency, the version-applicability requirement, source diversity over count, and why internal model agreement does not count as corroboration. Use whenever rating evidence, deciding how much to trust a source, comparing conflicting sources, or assigning/justifying a trust level. This is the source-auditor's reference; consult it before promoting any claim above L0.
---

# Source Trust

## Source-type hierarchy (default trust, before version check)
1. **Official docs / API / release notes** — high, but always check the version and the context of use.
2. **GitHub repos / issues / maintainer comments / changelogs** — high-to-medium; valuable for new tools, still needs verification.
3. **Forums / Discord / Slack / Telegram (incl. expert/paid channels)** — useful for practice, never final truth without a test.
4. **Tutorials / YouTube / courses** — good for direction, ages quickly, often doesn't scale or applies to an old version.
5. **Internal team tests** (scene/workflow files, logs, screenshots, notes) — the most valuable source *after* reproducible verification.
6. **Model answers** (GPT, Claude, Gemini, local) — a hypothesis, not a source of truth.

## The version-applicability requirement
A source raises a claim to **L2+ only if it applies to the target version.** A source about another version, or with no stated version, does not raise the level — record the mismatch. This enforces the project's flagship version gate at the evidence layer.

## Diversity over count
Three independent origins beat three copies of the same origin. Reward genuinely independent corroboration. Note when "multiple sources" are actually one source restated.

## Internal agreement is not corroboration
Agents/models in this system are one engine with different prompts. Their agreement stays at L0+. **L1 requires independent external corroboration** (independent sources, or genuinely different models — see the multi-model seam in `methodology/board-roles.md`).

## Closed channels — ethics
Use closed/expert chats only correctly: official access, community rules respected, no unauthorized scraping of private data. If a bot is disallowed, make a manual summary and record it as an expert note with its source.

## Mapping to L0–L5
See `methodology/trust-levels.md` for the full scale and what each promotion requires.
