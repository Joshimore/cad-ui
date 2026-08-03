# Board / Orchestra Roles (full reference)

The board does not exist to produce a pretty answer. It exists to leave a **trace**: hypotheses, arguments, disagreements between roles, sources, claims, risks, test, and conclusion.

## Roles → agents
| Role | Agent | Function | Output |
|------|-------|----------|--------|
| Generator | `generator` | Primary approach | Initial hypothesis (L0) |
| Alternative | `alternative` | Independent competing approach | Alternative hypothesis (L0) |
| Skeptic | `skeptic` | Weaknesses, risks, stale data, version mismatch | Severity-ranked objections |
| Source Auditor | `source-auditor` | Source quality + L0–L5 + version applicability | Trust levels |
| Test Designer | `test-designer` | Claim → reproducible test | Test protocol |
| (Test Runner) | `test-runner` | Executes auto tests | Test results |
| Synthesizer | `synthesizer` | Whole picture, disagreements preserved | Honest summary + recommendation |
| Researcher | `researcher` | Gathers evidence | Sourced findings |
| Reporter | `reporter` | Documents the session | Session report + KB cards |
| Human Reviewer | (the user) | Final decision | Decision status |

## Two mechanisms

### Default: adversarial subagent pipeline
You (the orchestrator) spawn the roles in sequence/parallel and assemble their trace files. They run as isolated subagents under one model; communication is one-directional (each reports back to you). Cheap and portable — ships inside this folder.

Typical Standard-tier order: `generator` + `alternative` → `researcher` → `source-auditor` → `skeptic` → `test-designer` → (test executed) → `synthesizer` → `reporter`.

### On demand: Agent Team (the "real" board)
A Claude Code **Agent Team** runs the roles as separate full sessions that message each other and can genuinely challenge each other's findings — the closest thing to a live consilium. It is experimental, must be enabled by the user at the user level, and uses significantly more tokens.

## Hybrid promotion trigger
Promote from pipeline to Agent Team when **any** of these holds:
1. The user explicitly asks for a "Board" / deep validation.
2. After one pipeline round, `skeptic` and `generator`/`alternative` have **not converged** on a claim.
3. A claim is being promoted to **L4 → L5**.

When a trigger fires, **recommend** the promotion to the user, stating the reason and the cost ("Agent Teams use significantly more tokens"). Do not auto-spin one up. If the user's environment doesn't have Agent Teams enabled, continue with the subagent pipeline and note that the deep-board option requires the user-level flag.

## The multi-model seam (optional, for genuine L1)
Internal agent agreement is not independent corroboration. If you want real L1 from model diversity, connect an MCP that can query *other* models (e.g. GPT, Gemini) and have `researcher`/`source-auditor` treat those as independent voices. This is an optional extension point, not a dependency — without it, L1 must come from independent human-authored sources.

### Wiring the multi-model seam
Configure the connector as an MCP server in your **own (user-level)** Claude Code settings — it is **not** shipped in the project, and any API keys stay personal. Plug it in at the **board / source-rating** stage so other models act as independent voices for L1 — not at the test stage (a test-judging model is not independent corroboration).
