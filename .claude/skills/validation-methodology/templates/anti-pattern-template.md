---
title: "<AP-NNN — short name of the anti-pattern>"
type: anti-pattern
trust: L0
version: "<software + version the negative result applies to>"
tags: []
created: <YYYY-MM-DD>
stale: false
---

<!-- A negative pattern: something that did NOT work, was rejected, or fooled the system.
     Captured so future runs avoid the same dead end.

     ONE FILE PER ANTI-PATTERN. Copy to knowledge-base/anti-patterns/<AP-NNN>-<slug>.md.
     Never collect several entries in one file — the host reads a file as a single card, so
     ten anti-patterns in one file render as one row.

     The frontmatter above is REQUIRED — same rules as the knowledge card. Contract:
     ../contracts/knowledge-base.md.
       type   anti-pattern (this is what sorts it into the negative section)
       trust  how well established the NEGATIVE result is (a test-backed reject outranks a
              reasoned one) — not how bad the idea was

     A match against a recorded anti-pattern RAISES A FLAG — it does NOT auto-reject.
     Re-check against the current version before treating it as binding: a negative result
     from an older version can be wrong now. UNVERIFIABLE claims never become anti-patterns:
     "could not verify" is not "verified false". -->

- **The claim/approach that failed:** <what looked plausible but did not hold>
- **Why it failed:** <root cause: doesn't exist, wrong version, non-reproducible, bad source, …>
- **Category:** <version-mismatch | invented-feature | stale-info | non-reproducible | bad-source | wrong-lever | other>
- **How it was caught:** <source | test | skeptic | human review | version comparison>
- **Software versions (VERSION STAMP):** <software + version, plugins, custom nodes, hardware>
- **Scope of the negative result:** <fails only in this version? broadly? under what conditions?>
- **Action on future match:** flag for re-check (NOT auto-reject). Re-validate against the current version.
- **Re-validation status:** <current | needs re-validation (version changed)>
- **Source session / trace:** <link to the session where it was found>
