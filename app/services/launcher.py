"""Claude Launch: open a terminal running the user's CLI agent in the workspace root.

The command comes ONLY from the local workspace config (claude_command, default
"claude") — never from the HTTP request. Claude Code reads the workspace CLAUDE.md
on session start by itself, so the launched agent understands the system immediately.
"""
from __future__ import annotations

import shlex
import shutil
import subprocess
import sys

from ..core.config import WorkspaceConfig


class LaunchError(Exception):
    pass


def _binary(cmd: str) -> str:
    """First token of the command, honoring quotes (so quoted paths with spaces
    survive the PATH lookup)."""
    try:
        parts = shlex.split(cmd, posix=False)
    except ValueError:
        parts = cmd.split()
    return parts[0].strip('"') if parts else cmd


def launch_claude(cfg: WorkspaceConfig) -> None:
    if sys.platform != "win32":
        raise LaunchError(
            "Запуск терминала пока поддерживается только на Windows. "
            "Открой терминал в этой папке вручную и запусти Claude."
        )
    cmd = cfg.claude_command.strip() or "claude"
    if shutil.which(_binary(cmd)) is None:
        raise LaunchError(
            f"Команда '{_binary(cmd)}' не найдена в PATH. Установи Claude Code "
            f"или укажи свою команду в workspace.config.json → claude_command."
        )
    try:
        subprocess.Popen(
            f'start "Claude — CAD UI" cmd /k "{cmd}"',
            shell=True,
            cwd=cfg.root,
        )
    except OSError as exc:
        raise LaunchError(f"Не удалось открыть терминал: {exc}") from exc
