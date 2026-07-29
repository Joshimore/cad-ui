---
name: status
description: Compose and post Russian work-status messages to Discord for the CAD UI workspace. Day bookends (Начало/Конец дня) and presence (отошёл/на месте/отхожу) go to the Status channel; per-task "Трек" updates, assignment Старт/Итог, and branded PDFs go to each project's own channel. Use whenever the user wants to post a status, track a task, announce stepping away/returning, or report a task result. Asks the type, drafts in Russian, posts only after approval.
---

# Status — Russian status updates to Discord (per-project)

Posts short **Russian** status messages via Discord webhooks. **Approve-first**: always
show a compact preview of the exact text and wait for an explicit "send" — even for
tests. (The only auto-sending path is the day bookends, handled by Task Scheduler via
`post_bookend.py`, NOT by this skill.) At 22:00, right after the (unchanged) Конец дня
message, `post_bookend.py` **stages** a per-project **daily summary** as
`_summary_draft.md` and pops a notification — it is **not** auto-sent. You approve & send
it to the dedicated summary channel via `/status` (see «Сводка дня» below). Days with no
real tracked work stage nothing.

**Configuration is not part of this skill's runtime** — a teammate configures the Discord
webhooks once by following `.claude/skills/status/SETUP.md`. Never post until the config
is filled.

Paths (all relative to the workspace/repo root; the `>_ Claude` terminal opens there):
- Sender:  `.claude/skills/status/send_status.py`
- Config:  repo-root `workspace.config.json` → the **`status`** object (`status_webhook`,
  `summary_webhook`, `username`, `summary_username`, and a `projects` map). **Git-ignored**
  — secrets live only here. Never echo webhook URLs.
- Runtime state (git-ignored, `.cad-ui/status/`): outbox `_message.txt`, active-project
  `active.json`, sent-id trail `_sent.json`, staged summary `_summary_draft.md`.
- Tick:    `.claude/skills/status/track_tick.py` · Notifier: `.claude/skills/status/notify.ps1`
- Scheduler setup: `.claude/skills/status/register_tasks.ps1` (Windows-only).

Per-project track files live **inside each project** under `Working directory/`, not centrally
(this is exactly what the cad-ui «Проекты» panel reads, so posted tasks show up in the UI):
- Task file: `Working directory/<project>/track/<slug>.md` · Active slug: `…/track/current.txt`
- Pending auto-draft: `…/track/_draft.md` · Reports: `…/track/reports/`

Run commands from the repo root; prefer the venv interpreter, fall back to `python`:
`\.venv\Scripts\python .claude\skills\status\send_status.py …`  (or `python .claude\skills\status\send_status.py …`)

Style: на «ты», по-дружески; light emoji; no sign-off. All posted text in **Russian**
(translate if the user dictates in another language). Discord markdown: `##` header,
`**bold**`, `-` bullets, `-#` subtext.

## Channels (routing)
- **Status channel** — `--channel status` (default): День (Начало/Конец) and Присутствие.
- **Project channel** — `--channel <project-key>`: Задание (Старт/Трек/Итог) and PDFs.

Resolve the project key by matching the **current working directory** against each
`projects[*].path` in the `status` config (paths may be workspace-relative, e.g.
`Working directory/<key>`). If none matches and the user is **starting a new
assignment**, register the project (Старт задания, below). Otherwise list the configured
project keys and ask the user to pick (AskUserQuestion).

## Auto-draft (the 3-hour tick)
While a task is active, `track_tick.py` runs on a schedule (work hours: 12/15/18/21) and,
for the project named in `.cad-ui/status/active.json`, writes a Russian Трек **draft** to
`Working directory/<project>/track/_draft.md`, logs it to the journal, and pops a Windows
"Черновик трека готов" balloon. **It never posts to Discord.** You review and send the
pending draft via `/status → Задание → Трек` (see below). When no task is active it does nothing.

## Сводка дня (end-of-day summary — approve-first)
At 22:00 `post_bookend.py` stages an «Итоги дня» draft to `.cad-ui/status/_summary_draft.md`
(it is the full ready message) and pops a "Сводка дня готова" balloon — it does **not** post.
**At the start of `/status`, check whether `.cad-ui/status/_summary_draft.md` exists; if it
does, offer to review and send it first.** On approval, show the exact text, then send to the
**summary** channel and delete the draft:
`\.venv\Scripts\python .claude\skills\status\send_status.py --channel summary --file .cad-ui\status\_summary_draft.md`
On `Sent.`, delete `.cad-ui/status/_summary_draft.md`. If the user edits, update the file and
re-show before sending. (No journal entry — the summary is a digest of journals, not a task event.)

## Step 1 — Ask the type (two-level)
AskUserQuestion caps at 4 options, so ask the **category** first (header "Категория"):
**День** / **Задание** / **Присутствие** / (Other = Своё). Then ask the **sub-type**:
- День → Начало дня / Конец дня
- Задание → Старт задания / Трек / Итог задания
- Присутствие → Отошёл от ПК / Снова на месте / Отхожу

## Step 2 — Build the draft (Russian)
Get local date/time with PowerShell `Get-Date` (date `yyyy-MM-dd`, time `HH:mm`).

**День (→ status channel)** — normally auto-sent at 09:00/22:00; use this for a manual or
richer one, or if a scheduled run was missed:
- Начало дня (time always **09:00** AM): `## 🟢 [YYYY-MM-DD] Начало рабочего дня (09:00).`
  + optional `**В планах на сегодня:**` bullets (ask the user).
- Конец дня (time = now): `## 🔴 Конец рабочего дня (HH:MM).` + optional `**Итоги дня:**`
  bullets (from today's task journals) + `**Завтра:**`.

**Присутствие (→ status channel)** — **send immediately on selection; skip Step 3 (no review).**
- Отошёл (🟡): `🟡 **Отошёл от компьютера** — временно недоступен. Как вернусь, отпишусь.`
- Снова на месте (🔵): `🔵 **Снова на месте** — за компьютером, продолжаю работу.`
- Отхожу (🚶): ask куда/насколько first (needed to build the text), then send right away →
  `🚶 **Отхожу** — <куда>, вернусь ~<время>. Пишите, если срочно.`

**Задание (→ project channel)** — needs a resolved project:
- Старт задания (once per task): ask name + goal + track steps. **Resolve/register the
  project:** match cwd to a `projects[*].path`; if it's a new project, pick a short
  `<key>`, ask the user for that project's Discord webhook URL, and add
  `projects[<key>] = {name, path, webhook}` to the `status` object in `workspace.config.json`
  (never echo the URL back). Create `Working directory/<project>/track/` and
  `…/track/<slug>.md` — frontmatter (`name`, `project: <key>`, `goal`, `started: today`,
  `state: active`) + `## Трек (план)` (the steps) + `## Журнал`. Write the slug into
  `…/track/current.txt`. Set `.cad-ui/status/active.json` to `{"project": "<key>"}`.
  **Do NOT post yet** — first build the kick-off PDF (Step 5a), then send the start text
  **and** the PDF as a **single combined message** (text + `--attach`), shown for approval
  first. See Step 5a.
- Трек (routine update): **first check for a pending `Working directory/<project>/track/_draft.md`**
  (made by the 3-h tick). If it exists, show *that* as the draft for approval — don't
  re-draft. If not, draft fresh: read the task file, gather recent activity
  (`git log --oneline -10`, `git status -s`, files modified today), build
  `## 📌 Трек — <name> (HH:MM)` + `**Сделано:** …` + `**Где на треке:** …` + `**Дальше:** …`.
  On approval (Step 4), post to the project channel, append a timestamped entry to the
  task's `## Журнал`, and **delete `_draft.md`** if it was used.
- Итог задания (done): draft `## ✅ Итог задания: <name>` + `**Результат:** …` from the
  journal + activity; append a final journal entry, set `state: done`, reset
  `.cad-ui/status/active.json` to `{}`, and delete any leftover `_draft.md`. Then do
  Step 5b (results PDF).

**Своё (Other):** render the user's text as a clean Russian message; ask which channel
(status or a project) if it isn't clear.

## Step 3 — Approve
Show the **exact** final message in a fenced code block; ask **send / edit / cancel**.
Don't proceed without an explicit "send". If they edit, update and re-show.
**Exception:** Присутствие messages skip this step — send immediately on selection (see Step 2).

## Step 4 — Send
1. Write the approved text to `.cad-ui/status/_message.txt` (UTF-8).
2. Run with the resolved channel:
   `\.venv\Scripts\python .claude\skills\status\send_status.py --channel <status|project-key> --file .cad-ui\status\_message.txt`
3. On `Sent.` confirm. On error, report it.

## Step 5a — Kick-off PDF + single combined start message (every Старт задания)
At the start of a **new** assignment, build a **branded** kick-off PDF by delegating to the
**cvd-docs agent** (Agent tool, `subagent_type: cvd-docs`): pass the task's name, goal/
context, and the `## Трек (план)` steps, and ask for a polished PDF titled
"План задания — <name>" that describes the task and lays out the plan as a **checklist**
(checkbox list of the steps). Save to `Working directory/<project>/track/reports/<slug>-plan.pdf`.

Then compose **one** message (do **not** send the start text separately):
`## 🎯 Старт задания: <name>` + `**Цель:** …` + `**Трек (план):**` bullets + a short
`📄 В PDF:` line describing what the attached PDF contains. **Show this exact message for
approval (Step 3)**, and only on "send" post it as a **single Discord message** with the
PDF attached:
`\.venv\Scripts\python .claude\skills\status\send_status.py --channel <project-key> --file .cad-ui\status\_message.txt --attach "Working directory\<project>\track\reports\<slug>-plan.pdf"`

## Step 5b — Results PDF (Итог задания, or on request)
Build a **branded** "track + results" PDF via the **cvd-docs agent**: pass the task's name,
goal, `## Трек (план)`, and `## Журнал`, and ask for a polished PDF titled
"Трек и результаты — <name>" saved to `Working directory/<project>/track/reports/<slug>.pdf`.
Then post it:
`\.venv\Scripts\python .claude\skills\status\send_status.py --channel <project-key> --attach "Working directory\<project>\track\reports\<slug>.pdf"`
(optionally a short `--file` caption — preview it first).

Never print or expose webhook URLs. If a webhook is missing, the sender fails with a clear
message — point the user to `.claude/skills/status/SETUP.md`, do not guess a URL.
