# Anti-Pattern

<!-- A negative pattern: something that did NOT work, was rejected, or fooled the system.
     Captured so future runs avoid the same dead end. MUST carry a version stamp.
     A match against this anti-pattern RAISES A FLAG — it does NOT auto-reject.
     Re-check against the current version before treating it as binding. -->

- **Title:** <short name of the anti-pattern>
- **Domain:** <your-domain (kebab-case, matches a domains/<name>/ pack) | none>
- **The claim/approach that failed:** <what looked plausible but did not hold>
- **Why it failed:** <root cause: doesn't exist, wrong version, non-reproducible, bad source, etc.>
- **Category:** <version-mismatch | invented-feature | stale-info | non-reproducible | bad-source | other>
- **How it was caught:** <source | test | skeptic | human review | version comparison>
- **Software versions (VERSION STAMP):** <software + version, plugins, custom nodes, hardware>
- **Scope of the negative result:** <does it fail only in this version? broadly? under what conditions?>
- **Action on future match:** flag for re-check (NOT auto-reject). Re-validate against the current version.
- **Re-validation status:** <current | needs re-validation (version changed)>
- **Source session / trace:** <link to the session where it was found>
