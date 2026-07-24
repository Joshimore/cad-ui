# CAD UI — Command & Agent Dashboard

You are working inside **CAD UI** — an isolated, self-contained agentic workspace with a local web UI on top of it. The repo is both the tool and the workspace: team members clone it, launch the UI, and do their work inside this folder. Everything is strictly local: the server binds `127.0.0.1` only, no API keys, no external calls, no CDNs.

## How the pieces interact

```
run_ui.py  ──►  app/main.py (FastAPI, port 8145)  ──►  browser UI (127.0.0.1:8145)
                    │
                    │
                    ├─ app/core/      file layer: config+exclusions, lazy tree scan,
                    │                 markdown render, favorites; search index.py
                    │                 (SQLite FTS5) + tagger.py (heuristic auto-tags)
                    ├─ app/adapters/  auto-detected panels; agents_skills.py watches
                    │                 .claude/agents/*.md and .claude/skills/*/SKILL.md
                    ├─ app/services/  actions: launcher.py (Claude Launch)
                    │  app/adapters/projects.py  team work: Working directory/,
                    │                 projects, tasks, deadlines, timeline
                    └─ app/web/       Jinja2 templates + vanilla JS (no external libs)
```

- **The UI is the eyes, the terminal is the hands.** The web UI executes no arbitrary commands — it only reads files and writes `.cad-ui/state.json` (favorites). The single fixed exception is the «>_ Claude» button in the topbar: `POST /api/claude-launch` opens a terminal in the workspace root running the command from local config (`claude_command`, default `claude`) — the command is never taken from the HTTP request. Claude Code reads this `CLAUDE.md` on session start automatically, so a session launched from the button already understands the system. All actual work (creating agents, skills, documents, code) is done by Claude Code in the terminal; the UI picks up file changes on page refresh.
- **Adapters are auto-detected.** If `.claude/agents/` or `.claude/skills/` contain valid files, the UI shows the «Реестр» section (Агенты / Навыки) automatically; if they are absent, the section is hidden. No configuration needed — creating the files IS the configuration.
- **Registry file contracts:** an agent is `.claude/agents/<name>.md` with frontmatter `name`, `description`, `tools`; a skill is `.claude/skills/<skill-name>/SKILL.md` with frontmatter `name`, `description`. The UI reads exactly these fields.
- **Work contracts (`Working directory/`):** team projects and tasks live here (created at startup if missing; committed, i.e. shared via git). A project is a folder with `project.md` (frontmatter `name`, `description`, `status`, `created`, optional `due`). A task is `<project>/track/<slug>.md` with frontmatter `name`, `goal`, `state` (active/done), `started`, optional `due`, plus `## Трек (план)` + `## Журнал`; `track/current.txt` names the active task; `track/_draft.md` flags an unsent draft. The «Новый проект»/«Новая задача» buttons write exactly this structure. Deadlines drive the dashboard timeline — `overdue`/`soon` are derived, not stored.
- **Personal vs shared:** `.claude/agents/` and `.claude/skills/` are **committed** (they are the system). `workspace.config.json` (personal exclusions, future webhooks), `.cad-ui/` (runtime state), and `.claude/settings.local.json` are **gitignored** — never commit them, never put secrets in tracked files.

## First run — what YOU must initiate

A fresh clone is empty: no venv, no agents, no skills, an almost-blank UI. When a user starts a session in this folder and the environment looks unprovisioned, proactively walk them through bootstrap (ask before each step, don't silently install):

1. **Environment check:** if `.venv/` is missing — the simplest path is `start.bat` (creates the venv, installs deps, launches). Manual equivalent: `python -m venv .venv` → `.venv\Scripts\pip install -r requirements.txt` (needs Python 3.11+ with pip; beware of PATH pythons shipped without pip, e.g. MSYS builds).
2. **Launch the UI:** `start.bat`, or `.venv\Scripts\python run_ui.py` → opens `http://127.0.0.1:8145`. Options: `--port`, `--no-browser`, or an explicit workspace path (default = this folder). To update the system later: `update.bat` (git pull + dependency sync), then restart.
3. **Seed the registry:** the repo ships a small starter roster in `.claude/agents/` (creator, repo-searcher, registrar) so «Реестр» is populated on a fresh clone — these are examples, safe to edit or delete. If a user works in a domain they don't cover, offer to scaffold a tailored agent/skill from the file contracts above. If the user clears `.claude/agents/` and `.claude/skills/`, the «Реестр» section hides itself automatically.
4. **Orient the user:** point them to the sections — Центр управления (dashboard), Документы (tree + markdown viewer), Недавние, Избранное — and explain that documents they create here appear in the UI immediately.

## Conventions for changes

- Roadmap (do not implement ahead of it without being asked): next is Discord/PDF on task start, then knowledge base + graph. Already shipped: phase 1 (file layer), Claude Launch (`>_ Claude` button), phase 2 (full-text search + auto-tagging — `app/core/index.py`), phase 3 (Working directory + projects/tasks + deadlines + dashboard timeline — `app/adapters/projects.py`).
- Keep it dependency-light: vanilla JS only, no CDN/external assets; new Python deps go to `requirements.txt` with a reason.
- New panels are adapters (`app/adapters/`, pattern: `detect() → parse data → page route + template`), never hardcoded into the core.
- UI style: "engineer's notebook" theme in `app/web/static/style.css` — light paper background, burnt-orange accent, mono labels. All colors come from the `:root` CSS variables; never hardcode theme colors in templates. Match it.
- UI text is Russian; code, comments, and this file are English.
