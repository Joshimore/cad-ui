#!/usr/bin/env python3
"""Post a status message (and optional file) to a Discord channel webhook.

Usage:
    python send_status.py --file message.txt
    python send_status.py --channel <project-key> --file message.txt
    python send_status.py --channel <key> --file message.txt --attach report.pdf
    python send_status.py "inline text"
    python send_status.py --channel <key> --delete-last
    python send_status.py --channel <key> --delete <message_id>

Channels are resolved from the workspace config (repo-root workspace.config.json,
"status" object):
  - "status" (default) -> status["status_webhook"]
  - "summary"          -> status["summary_webhook"]
  - <project-key>      -> status["projects"][key]["webhook"]

Sends use ?wait=true so Discord returns the created message; its id is recorded
per channel in .cad-ui/status/_sent.json, which lets --delete-last remove the
message we just posted (webhooks can only delete their own messages).

Config + secrets live in the git-ignored workspace.config.json; runtime state
lives in the git-ignored .cad-ui/status/ dir. Neither is committed. Configure via
.claude/skills/status/SETUP.md.
"""
import argparse
import json
import mimetypes
import sys
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

# Windows consoles default to a legacy codepage (e.g. cp1251 on Russian Windows) that
# can't encode emoji/Cyrillic — printing a draft/message would crash. Force UTF-8 stdout.
# (Discord payloads are always UTF-8 regardless; under pythonw there is no console, so guard.)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
# .claude/skills/status/send_status.py -> parents[3] is the workspace/repo root.
WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
CONFIG = WORKSPACE_ROOT / "workspace.config.json"
STATE_DIR = WORKSPACE_ROOT / ".cad-ui" / "status"  # git-ignored (.cad-ui/)
SENT = STATE_DIR / "_sent.json"
UA = "StatusAgent/1.0 (+https://localhost)"  # Discord/Cloudflare rejects urllib's default UA


def state_dir():
    """Ensure the git-ignored runtime-state dir exists, return it."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR


def load_config():
    """Return the 'status' object from the repo-root workspace.config.json."""
    if not CONFIG.exists():
        sys.exit(
            f"workspace.config.json not found at {CONFIG}. Copy config.example.json to the "
            f"repo root and fill the 'status' block (see .claude/skills/status/SETUP.md)."
        )
    data = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
    status = data.get("status")
    if not isinstance(status, dict):
        sys.exit(
            "workspace.config.json has no 'status' object. See config.example.json and "
            ".claude/skills/status/SETUP.md."
        )
    return status


def resolve_webhook(cfg, channel):
    if channel == "status":
        url = (cfg.get("status_webhook") or "").strip()
        if not url or "REPLACE" in url:
            sys.exit("status_webhook is not set in workspace.config.json ('status' block).")
        return url
    if channel == "summary":
        url = (cfg.get("summary_webhook") or "").strip()
        if not url or "REPLACE" in url:
            sys.exit("summary_webhook is not set in workspace.config.json ('status' block).")
        return url
    projects = cfg.get("projects") or {}
    proj = projects.get(channel)
    if not proj:
        known = ", ".join(["status", "summary"] + list(projects.keys()))
        sys.exit(f"Unknown channel/project '{channel}'. Known: {known}")
    url = (proj.get("webhook") or "").strip()
    if not url or "REPLACE" in url:
        sys.exit(f"webhook for project '{channel}' is not set in workspace.config.json.")
    return url


def _with_wait(url):
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}wait=true"


def _read_response(resp):
    if resp.status not in (200, 204):
        sys.exit(f"Discord returned HTTP {resp.status}")
    body = resp.read()
    return json.loads(body) if body else None


def _send_json(url, content, username):
    payload = json.dumps({"content": content, "username": username}).encode("utf-8")
    req = urllib.request.Request(
        _with_wait(url), data=payload,
        headers={"Content-Type": "application/json", "User-Agent": UA}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return _read_response(resp)


def _send_multipart(url, content, username, attaches):
    """attaches: list of Path -> one Discord message with files[0..n] (Discord allows up to 10)."""
    crlf = "\r\n"
    boundary = uuid.uuid4().hex
    payload_json = json.dumps({"content": content, "username": username})
    buf = bytearray()
    buf.extend((f"--{boundary}{crlf}"
                f'Content-Disposition: form-data; name="payload_json"{crlf}'
                f"Content-Type: application/json{crlf}{crlf}{payload_json}").encode("utf-8"))
    for i, attach in enumerate(attaches):
        ctype = mimetypes.guess_type(attach.name)[0] or "application/octet-stream"
        buf.extend((f"{crlf}--{boundary}{crlf}"
                    f'Content-Disposition: form-data; name="files[{i}]"; '
                    f'filename="{attach.name}"{crlf}'
                    f"Content-Type: {ctype}{crlf}{crlf}").encode("utf-8"))
        buf.extend(attach.read_bytes())
    buf.extend(f"{crlf}--{boundary}--{crlf}".encode("utf-8"))
    req = urllib.request.Request(
        _with_wait(url), data=bytes(buf),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                 "User-Agent": UA}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return _read_response(resp)


def _record_sent(channel, msg):
    if not msg or "id" not in msg:
        return
    data = {}
    if SENT.exists():
        try:
            data = json.loads(SENT.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            data = {}
    history = data.get(channel, [])
    history.append({"id": str(msg["id"]), "ts": datetime.now().isoformat(timespec="seconds")})
    data[channel] = history[-20:]  # keep a short trail per channel
    state_dir()
    SENT.write_text(json.dumps(data, indent=2), encoding="utf-8")


def post(channel, text, attach=None):
    """Reusable: post text (and optional file) to the named channel. Returns the message id (or None)."""
    cfg = load_config()
    url = resolve_webhook(cfg, channel)
    username = cfg.get("username", "Статус")
    if channel == "summary":
        username = cfg.get("summary_username") or username
    elif channel != "status":
        proj = (cfg.get("projects") or {}).get(channel) or {}
        username = proj.get("username") or username
    if attach:
        files = attach if isinstance(attach, (list, tuple)) else [attach]
        msg = _send_multipart(url, text or "", username, [Path(a) for a in files])
    else:
        msg = _send_json(url, text, username)
    _record_sent(channel, msg)
    return (msg or {}).get("id")


def delete(channel, message_id):
    """Delete a message previously posted by this channel's webhook."""
    cfg = load_config()
    url = resolve_webhook(cfg, channel)
    req = urllib.request.Request(
        f"{url}/messages/{message_id}",
        headers={"User-Agent": UA}, method="DELETE")
    with urllib.request.urlopen(req, timeout=20) as resp:
        if resp.status not in (200, 204):
            sys.exit(f"Discord returned HTTP {resp.status}")
    # drop it from the recorded trail if present
    if SENT.exists():
        try:
            data = json.loads(SENT.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            data = {}
        history = [e for e in data.get(channel, []) if str(e.get("id")) != str(message_id)]
        data[channel] = history
        SENT.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _last_sent_id(channel):
    if not SENT.exists():
        return None
    try:
        data = json.loads(SENT.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    history = data.get(channel, [])
    return history[-1]["id"] if history else None


def _read_message(args):
    if args.file:
        return Path(args.file).read_text(encoding="utf-8-sig").strip()
    if args.text:
        return args.text
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return ""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("text", nargs="?", help="inline message text")
    p.add_argument("--file", help="read message text from this file")
    p.add_argument("--channel", default="status", help="'status', 'summary', or a project key")
    p.add_argument("--attach", action="append",
                   help="path to a file to upload (repeatable; e.g. a PDF or several images)")
    p.add_argument("--delete", metavar="MESSAGE_ID", help="delete a message by id from --channel")
    p.add_argument("--delete-last", action="store_true",
                   help="delete the last message this tool recorded for --channel")
    args = p.parse_args()

    if args.delete or args.delete_last:
        mid = args.delete or _last_sent_id(args.channel)
        if not mid:
            sys.exit(f"No recorded message to delete for channel '{args.channel}'.")
        delete(args.channel, mid)
        print(f"Deleted {mid}.")
        return

    message = _read_message(args)
    if not message and not args.attach:
        sys.exit("No message. Use --file, inline text, or stdin.")
    mid = post(args.channel, message, args.attach)
    print(f"Sent. id={mid}" if mid else "Sent.")


if __name__ == "__main__":
    main()
