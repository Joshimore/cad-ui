# Version Discipline — the flagship rule (full reference)

**Correspondence between information and the exact software version in use is the single most important factor. If something fails because of a version mismatch, every other effort spent on it is wasted resources.**

This is not one rule among many. It gates the entire cycle.

## What "establish the version" means
Before validating anything, pin down the target:
- The software and its **version/patch** (e.g. an engine build, a tool release, a pinned patch identifier).
- **Plugins / custom nodes / extensions** and their versions.
- **Hardware** where it materially affects behavior.
Record these in the session report's structured form. If any are unknown and matter, resolve them before proceeding.

## How the gate acts at each layer
- **Sources:** a source raises a claim to **L2+ only if it applies to the target version.** A source about another version, or with no stated version, does not raise the level — record the mismatch (see `trust-levels.md`, `source-trust` skill).
- **Skeptic:** version mismatch is attack vector #1 and is always a **BLOCKING** objection until resolved.
- **Claims:** a claim true for a different version is **FAILED**, never "partially true."
- **Tests:** the fixed test environment must record exact versions; a test run on a different version does not validate the claim.

## The knowledge base is not exempt
A card verified for one version becomes wrong for another. Therefore:
- Every Knowledge Card carries a **version stamp** (`knowledge-card-template.md`).
- At session bootstrap, compare the current target version with the versions on relevant KB cards. Cards whose version differs are flagged **`needs re-validation`** — they are not silently trusted.
- A flagged card drops to "hypothesis" status until re-validated against the current version.

## Why this is the flagship
In this domain, the most common, most confident, and most expensive AI failure is asserting something that was true for a different version. Catching that early is worth more than any other check — hence: establish the version first, and treat every version mismatch as blocking.
