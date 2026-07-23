"""Claude Launch: open a terminal running the user's CLI agent in the workspace root.

The command comes ONLY from the local workspace config (claude_command, default
"claude") — never from the HTTP request. Claude Code reads the workspace CLAUDE.md
on session start by itself, so the launched agent understands the system immediately.
"""
from __future__ import annotations

import shutil
import subprocess
import sys

from ..core.config import WorkspaceConfig


class LaunchError(Exception):
    pass


def launch_claude(cfg: WorkspaceConfig) -> None:
    cmd = cfg.claude_command.strip() or "claude"
    binary = cmd.split()[0]
    if shutil.which(binary) is None:
        raise LaunchError(
            f"Команда '{binary}' не найдена в PATH. Установи Claude Code "
            f"или укажи свою команду в workspace.config.json → claude_command."
        )
    try:
        if sys.platform == "win32":
            subprocess.Popen(
                f'start "Claude — CAD UI" cmd /k "{cmd}"',
                shell=True,
                cwd=cfg.root,
            )
        elif sys.platform == "darwin":
            script = f'tell application "Terminal" to do script "cd {cfg.root} && {cmd}"'
            subprocess.Popen(["osascript", "-e", script])
        else:
            for term in ("x-terminal-emulator", "gnome-terminal", "konsole", "xterm"):
                if shutil.which(term):
                    subprocess.Popen([term, "-e", cmd], cwd=cfg.root)
                    break
            else:
                raise LaunchError("Не найден эмулятор терминала (x-terminal-emulator/gnome-terminal/konsole/xterm).")
    except LaunchError:
        raise
    except OSError as exc:
        raise LaunchError(f"Не удалось открыть терминал: {exc}") from exc
