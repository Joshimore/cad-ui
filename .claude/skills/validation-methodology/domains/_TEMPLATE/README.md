# How to add a domain pack

The project core is domain-agnostic on purpose. Your domain specifics go in a pack here, so the shared core never bloats and the project stays portable.

## Rules
1. **Copy this `_TEMPLATE/` folder** and rename it in **kebab-case** (e.g. `my-domain`, `maya-fx`, `web-backend`). No spaces, no capitals, no underscores.
2. **Fill `pack.md`** — `pack_name`, `description`, `test_execution`, `version_pins`. If a field is missing the orchestrator just notes it and falls back to the core; it does not block.
3. **Set `test_execution` honestly:** `human` if a person must run the test (e.g. open the software and check output), `auto` if Claude Code can run it (e.g. code/scripts) — that decides whether `test-runner` is used or the human runs it.
4. **Fill `sources.md`** with your domain's trusted sources and **version pins**, and `knowledge.md` with the domain reference. Do not put methodology here.
5. **Pack-specific agents** (optional) go in this pack's `agents/` folder and listed under `custom_agents` in `pack.md`.
6. **Keep it self-contained.** A pack must not depend on anything outside the project folder.

## What stays out of packs
The validation cycle, the L0–L5 scale, the board roles, the version gate, and the templates are all core and shared. Packs only add domain knowledge, sources, version pins, and optional domain agents.
