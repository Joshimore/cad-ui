#!/usr/bin/env python3
"""Generate a Russian "Трек" draft for the active project, then pop a "draft ready" balloon.

Run by Task Scheduler during work hours (12/15/18/21). This script does NOT post to
Discord — it writes a pending draft to ``<project>\\track\\_draft.md`` and notifies the
user, who reviews and sends it via ``/status`` (Задание -> Трек).

Flow:
  1. Read .cad-ui/status/active.json -> active project key. If none, exit silently.
  2. Resolve project from workspace.config.json (path, name). Read its track\\current.txt ->
     slug, then track\\<slug>.md (goal, plan, journal tail).
  3. Gather recent activity in Python (files modified in the last few hours; git log/
     status if the project is a git repo).
  4. Ask ``claude -p`` (text in via stdin -> text out) to synthesize the draft.
  5. Write the draft to track\\_draft.md and append a journal line to <slug>.md.
  6. Pop notify.ps1 -Text "...".

Use --dry-run to print the prompt and the draft without writing or notifying.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from send_status import load_config, STATE_DIR, WORKSPACE_ROOT  # same folder; script dir on sys.path

HERE = Path(__file__).resolve().parent
ACTIVE = STATE_DIR / "active.json"   # git-ignored runtime state (.cad-ui/status/)
NOTIFY = HERE / "notify.ps1"         # committed skill code stays in the skill dir

# How far back to look for "что сделано". Ticks are ~3 h apart; a little slack helps.
WINDOW = timedelta(hours=3, minutes=30)
# Directories we never descend into when scanning for recent edits.
SKIP_DIRS = {"track", ".git", "node_modules", "__pycache__", ".venv", "venv",
             "output", "models", ".idea", ".vscode", "dist", "build"}
MAX_FILES = 40


def _configured_claude():
    """Top-level 'claude_command' from workspace.config.json (NOT the 'status' object)."""
    cfg_path = WORKSPACE_ROOT / "workspace.config.json"
    if not cfg_path.exists():
        return ""
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
    except (ValueError, OSError):
        return ""
    cmd = data.get("claude_command")
    return cmd.strip() if isinstance(cmd, str) and cmd.strip() else ""


def claude_bin():
    """Full path to the claude CLI launcher, resolved robustly for Task Scheduler."""
    configured = _configured_claude()          # reuse cad-ui's own claude_command first
    if configured:
        return configured
    appdata = os.environ.get("APPDATA", "")
    cand = Path(appdata) / "npm" / "claude.cmd"
    if cand.exists():
        return str(cand)
    from shutil import which
    return which("claude") or "claude"


def read_active_project():
    if not ACTIVE.exists():
        return None
    try:
        data = json.loads(ACTIVE.read_text(encoding="utf-8-sig") or "{}")
    except json.JSONDecodeError:
        return None
    key = (data or {}).get("project")
    return key or None


def resolve_project_root(proj):
    """Absolute project root; workspace-relative paths resolve against the repo root
    (so scheduled runs, which have no reliable cwd, still find the project)."""
    p = Path(proj["path"])
    return (p if p.is_absolute() else (WORKSPACE_ROOT / p)).resolve()


def recent_files(root: Path):
    cutoff = (datetime.now() - WINDOW).timestamp()
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            fp = Path(dirpath) / fn
            try:
                mt = fp.stat().st_mtime
            except OSError:
                continue
            if mt >= cutoff:
                hits.append((mt, fp.relative_to(root).as_posix()))
    hits.sort(reverse=True)
    return [rel for _, rel in hits[:MAX_FILES]]


def git_activity(root: Path):
    if not (root / ".git").exists():
        return ""
    out = []
    for label, cmd in (("git log", ["git", "-C", str(root), "log", "--oneline", "-10"]),
                       ("git status", ["git", "-C", str(root), "status", "-s"])):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                               timeout=20)
            if r.stdout.strip():
                out.append(f"{label}:\n{r.stdout.strip()}")
        except Exception:
            pass
    return "\n\n".join(out)


def build_prompt(name, goal, plan, journal_tail, files, git_text, hhmm):
    files_block = "\n".join(f"- {f}" for f in files) if files else "(нет изменённых файлов за последние ~3 часа)"
    git_block = git_text if git_text else "(не git-репозиторий или нет коммитов)"
    return f"""Ты ведёшь рабочий трек проекта и пишешь короткое статус-сообщение для Discord на русском языке, на «ты», по-дружески, без подписи.

Проект: {name}
Цель задания: {goal}

План (трек):
{plan}

Последние записи журнала:
{journal_tail}

Изменённые файлы за последние ~3 часа:
{files_block}

Активность git:
{git_block}

Составь сообщение СТРОГО в таком формате (Discord markdown):

## 📌 Трек — {name} ({hhmm})
**Сделано:** <1–3 коротких пункта или фразы о том, что сделано, на основе активности выше>
**Где на треке:** <на каком шаге плана сейчас>
**Дальше:** <что планируется следующим шагом>

Требования:
- Пиши только по-русски, на «ты», по-дружески, лёгкие эмодзи допустимы.
- Опирайся на активность выше; если активности почти нет — честно отметь, что заметного прогресса за интервал немного.
- Выведи ТОЛЬКО текст сообщения. Без пояснений, без вступления, без markdown-кодблоков (```)."""


def run_claude(prompt):
    cmd = ["cmd", "/c", claude_bin(), "-p"]
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                       encoding="utf-8", timeout=300)
    return (r.stdout or "").strip()


def append_journal(task_file: Path, hhmm):
    line = f"\n- {hhmm} — черновик трека сгенерирован\n"
    with task_file.open("a", encoding="utf-8") as f:
        f.write(line)


def notify(text):
    subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden",
                    "-ExecutionPolicy", "Bypass", "-File", str(NOTIFY), "-Text", text],
                   check=False)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true",
                   help="print the prompt and draft; write nothing, notify nothing")
    args = p.parse_args()

    key = read_active_project()
    if not key:
        return  # no active task — nothing to track

    cfg = load_config()
    proj = (cfg.get("projects") or {}).get(key)
    if not proj or not proj.get("path"):
        sys.exit(f"Active project '{key}' is not in workspace.config.json ('status' block).")
    root = resolve_project_root(proj)
    name = proj.get("name", key)

    track = root / "track"
    current = track / "current.txt"
    if not current.exists():
        return  # no active slug for this project
    slug = current.read_text(encoding="utf-8-sig").strip()
    task_file = track / f"{slug}.md"
    if not task_file.exists():
        return
    task_md = task_file.read_text(encoding="utf-8-sig")

    # Pull goal / plan / journal tail out of the task file (best-effort, plain text).
    goal = ""
    for ln in task_md.splitlines():
        if ln.lower().startswith("goal:"):
            goal = ln.split(":", 1)[1].strip()
            break
    plan = _section(task_md, "## Трек (план)") or "(план не указан)"
    journal = _section(task_md, "## Журнал") or ""
    journal_tail = "\n".join(journal.strip().splitlines()[-12:]) or "(журнал пуст)"

    hhmm = datetime.now().strftime("%H:%M")
    prompt = build_prompt(name, goal or "(цель не указана)", plan, journal_tail,
                          recent_files(root), git_activity(root), hhmm)

    if args.dry_run:
        print("===== PROMPT =====\n" + prompt + "\n")
        print("===== DRAFT =====\n" + run_claude(prompt))
        return

    draft = run_claude(prompt)
    if not draft:
        sys.exit("claude returned no draft.")

    (track / "_draft.md").write_text(draft + "\n", encoding="utf-8")
    append_journal(task_file, hhmm)
    notify(f"Черновик трека для {name} готов — /status, чтобы отправить.")
    print("Draft ready.")


def _section(md, header):
    """Return the text under a '## Header' up to the next '## ' (exclusive)."""
    lines = md.splitlines()
    out, grabbing = [], False
    for ln in lines:
        if ln.strip() == header:
            grabbing = True
            continue
        if grabbing and ln.startswith("## "):
            break
        if grabbing:
            out.append(ln)
    return "\n".join(out).strip()


if __name__ == "__main__":
    main()
