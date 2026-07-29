#!/usr/bin/env python3
"""Auto-send the day-start / day-end message to the Status channel (no approval).

Run by Task Scheduler: 09:00 -> --type start, 22:00 -> --type end.
Cyrillic lives in this UTF-8 source (Python 3 reads source as UTF-8), so there are
no PowerShell encoding pitfalls. Use --dry-run to print without sending.

At day end, AFTER the (unchanged) end message is posted to the Status channel, this
script STAGES a per-project daily summary as ``.cad-ui/status/_summary_draft.md`` and
pops a notification — it is NOT auto-sent. You review and send it to the summary channel
via ``/status``. The summary covers what was done today, which projects were worked on,
and the channel where each project's track lives. Days with no real tracked work stage nothing.
"""
import argparse
import re
from datetime import datetime
from pathlib import Path

from send_status import post, load_config, STATE_DIR  # same folder; script dir on sys.path
from track_tick import _section, run_claude, notify, resolve_project_root

SUMMARY_DRAFT = STATE_DIR / "_summary_draft.md"  # git-ignored runtime state (.cad-ui/status/)

START = "## 🟢 [{date}] Начало рабочего дня (09:00).\n\nДоброе утро! Приступаю к работе."
END = "## 🔴 Конец рабочего дня ({time}).\n\nРабочий день завершён. До завтра!"


def build(kind):
    now = datetime.now()
    if kind == "start":
        return START.format(date=now.strftime("%Y-%m-%d"))
    return END.format(time=now.strftime("%H:%M"))


# ---------------------------------------------------------------------------
# Daily summary (end of day) — posted to the dedicated "summary" channel
# ---------------------------------------------------------------------------
def gather_today_by_project(cfg, today):
    """Projects whose current task journal has >=1 real entry dated `today`.

    Real entries are prefixed with a full YYYY-MM-DD date; auto-tick noise lines have
    only HH:MM and say "черновик трека сгенерирован" — those are excluded.
    Returns a list of {key, name, entries[]} (entries in journal/chronological order).
    """
    out = []
    for key, proj in (cfg.get("projects") or {}).items():
        if not proj.get("path"):
            continue
        track = resolve_project_root(proj) / "track"
        current = track / "current.txt"
        if not current.exists():
            continue
        try:
            slug = current.read_text(encoding="utf-8-sig").strip()
        except OSError:
            continue
        task_file = track / f"{slug}.md"
        if not task_file.exists():
            continue
        journal = _section(task_file.read_text(encoding="utf-8-sig"), "## Журнал") or ""
        entries = []
        for ln in journal.splitlines():
            s = ln.lstrip("-").strip()
            if s.startswith(today) and "черновик трека сгенерирован" not in s:
                entries.append(s)
        if entries:
            out.append({"key": key, "name": proj.get("name", key), "entries": entries})
    return out


def _build_prompt(projects_today):
    parts = []
    for p in projects_today:
        entries = "\n".join(f"- {e}" for e in p["entries"])
        parts.append(f'Проект: {p["name"]}  (трек в канале «{p["name"]}»)\n'
                     f'Записи журнала за сегодня:\n{entries}')
    blocks = "\n\n".join(parts)
    return f"""Ты пишешь короткие «Итоги дня» для Discord на русском, на «ты», по-дружески, без подписи.
Сегодня работа шла по этим проектам (используй ТОЛЬКО эти данные, ничего не выдумывай):

{blocks}

Формат вывода (Discord markdown), по одному блоку на проект:
**<Название проекта>** — <1–2 коротких предложения: что сделано сегодня по этому проекту>.
-# трек: канал «<Название проекта>»

Требования: только по-русски; опирайся строго на записи выше; без вступления и без
markdown-кодблоков; выведи ТОЛЬКО блоки проектов, без общего заголовка и без подписи."""


def _strip_fences(body):
    """Drop accidental ```-fence wrapping if the model added it."""
    if not body.startswith("```"):
        return body
    lines = body.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _clean_entry(text):
    """Strip the 'YYYY-MM-DD HH:MM — ' prefix and **bold** markers from a journal line."""
    t = re.sub(r"^\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}\s*—\s*", "", text)
    return t.replace("**", "").strip()


def _fallback_body(projects_today):
    """Deterministic per-project block used when the claude call returns nothing."""
    lines = []
    for p in projects_today:
        recap = _clean_entry(p["entries"][-1])
        if len(recap) > 160:
            recap = recap[:157].rstrip() + "…"
        lines.append(f'**{p["name"]}** — {recap}')
        lines.append(f'-# трек: канал «{p["name"]}»')
    return "\n".join(lines)


def build_daily_summary():
    """Full «Итоги дня» message, or None when no project had real work today."""
    cfg = load_config()
    today = datetime.now().strftime("%Y-%m-%d")
    projects_today = gather_today_by_project(cfg, today)
    if not projects_today:
        return None
    body = ""
    try:
        body = _strip_fences(run_claude(_build_prompt(projects_today)).strip())
    except Exception:
        body = ""
    if not body:
        body = _fallback_body(projects_today)
    return f"## 🗂️ Итоги дня — {today}\n\n{body}\n\nХорошего вечера!"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--type", choices=["start", "end"], required=True)
    p.add_argument("--dry-run", action="store_true", help="print the message, do not send")
    args = p.parse_args()
    msg = build(args.type)

    if args.dry_run:
        print(msg)
        if args.type == "end":
            print("\n----- summary -----")
            try:
                summary = build_daily_summary()
            except Exception as e:
                summary = None
                print(f"(summary error: {e})")
            print(summary if summary else "(no work today — summary skipped)")
        return

    post("status", msg)
    print("Sent.")
    # End of day: STAGE the daily summary for approval (don't send). A headless 22:00 job
    # can't ask, so we write a pending draft + notify; you send it via /status. Wrapped so a
    # summary failure can never block the (already sent) bookend.
    if args.type == "end":
        try:
            summary = build_daily_summary()
            if summary:
                STATE_DIR.mkdir(parents=True, exist_ok=True)
                SUMMARY_DRAFT.write_text(summary + "\n", encoding="utf-8")
                notify("Сводка дня готова — /status, чтобы отправить в «Итоги дня».")
                print("Summary draft ready.")
            else:
                print("Summary skipped (no work today).")
        except Exception as e:
            print(f"summary skipped: {e}")


if __name__ == "__main__":
    main()
