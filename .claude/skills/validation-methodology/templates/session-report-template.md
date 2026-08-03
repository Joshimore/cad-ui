# Session Report — <SESSION TITLE>

<!--
HOW TO USE: copy this file to sessions/<YYYY-MM-DD>_<slug>/REPORT.md and fill it.
The reporter subagent returns this filled body as text; the orchestrator saves the file
(the harness blocks subagents from writing report files).
Field labels stay in English. Write prose in the session language (default UK).
Keep technical terms, tool names, version identifiers, file/param names, and quoted
source claims in English. Build this from the trace/ folder, not from memory.
-->

## 1. Metadata
- **Session ID:** <YYYY-MM-DD_slug>
- **Date:** <date>
- **Working language:** <EN | RU | UK>
- **Tier:** <Fast lane | Standard | Deep/Board>
- **Owner:** <who ran it>
- **Domain pack:** <your-domain | none>

## 2. Target environment (VERSION GATE)
- **Software + version:** <name + version/patch>
- **Plugins / custom nodes / extensions:** <name + version>
- **Hardware (if relevant):** <...>
- **Version established before validation?** <yes/no — if no, explain>

## 3. Question
<The framed, checkable question. Include the target version in the framing.>

## 4. How the session went (narrative)
<What was actually done, in order. Which agents ran, what the board decided, where
roles disagreed. This is the human-readable story; the granular trail is in trace/.>

## 5. Claims & trust levels
For each claim:
- **Claim:** <concrete statement tested>
- **Trust level:** <L0–L5 | UNVERIFIABLE | REJECTED>
- **Version applicability:** <applies to target version? evidence>
- **Sources:** <independent sources + diversity note>
- **Key objections (severity):** <BLOCKING / MAJOR / MINOR + resolution>
- **Test:** <designed? run by machine/human? result>

## 6. Knowledge Cards produced
<!-- Embed one block per card, using templates/knowledge-card-template.md.
     Promote to knowledge-base/ only when L4+. -->

## 7. Error / Hallucination Log
<!-- Embed entries using templates/error-hallucination-log-template.md.
     Version hallucinations especially go here. -->

## 8. Decision-ready brief (for the human)
Per claim, at a glance:
| Claim | Trust | Version status | Key dissent | Recommendation |
|-------|-------|----------------|-------------|----------------|
| <...> | <Lx>  | <ok/mismatch>  | <...>       | use / don't use / test further / use with limits |

**Human decision:** <filled by the reviewer>

## 9. Limitations & "do not apply to"
<Where it does NOT work, what was not tested, what is unsafe to apply.>

## 10. Next steps
<What to test further, reproduce, automate, or scale.>
