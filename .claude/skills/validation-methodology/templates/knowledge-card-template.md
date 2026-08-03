---
title: "<name of the finding>"
type: card
trust: L0
version: "<software + version the card applies to>"
tags: []
created: <YYYY-MM-DD>
stale: false
---

<!-- Use for a single validated finding. Copy to knowledge-base/<slug>.md and fill.

     The frontmatter above is REQUIRED — the host reads it to render the card and to rank
     the panel. A card without it is invisible. Contract: ../contracts/knowledge-base.md.
       title    quote it; a colon inside an unquoted YAML scalar breaks the whole block
       type     card
       trust    L0–L5, the level the claim ACTUALLY reached — not a target
       version  the version stamp, quoted; the card expires when this changes
       stale    set true by hand once the card no longer holds for its version

     Write the card at whatever level it reached. The trust level is a field, never a
     folder — an L2→L3 promotion edits this file, it never moves it. -->

- **Original question:** <...>
- **Hypothesis / Claim:** <the statement validated>
- **Sources:** <independent sources used + diversity note>
- **Software versions (VERSION STAMP):** <software + version, plugins, custom nodes, hardware>
- **Test procedure:** <reproducible steps, or link to the trace>
- **Actual result:** <what actually happened>
- **What worked / failed:** <...>
- **Limitations:** <unknown zones, edge cases>
- **Can be used for:** <where it applies>
- **Do NOT use for:** <where it does not apply>
- **Re-validation status:** <current | needs re-validation (version changed)>
- **Owner / next step:** <who is responsible, what to do next>
