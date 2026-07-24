"""Workspace configuration: default exclusions + optional workspace.config.json."""
from __future__ import annotations

import fnmatch
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Directory names (or fnmatch patterns) that are never scanned or expanded.
DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".cad-ui",
    "_archive",
    "*_portable",
    ".idea",
    ".vscode",
    "dist",
    "build",
    "*.egg-info",
}

# File extensions treated as binary/heavy: shown in the tree but not viewable as text.
DEFAULT_EXCLUDED_EXTENSIONS = {
    ".safetensors", ".ckpt", ".pt", ".pth", ".onnx", ".gguf", ".bin",
    ".zip", ".7z", ".rar", ".tar", ".gz",
    ".exe", ".dll", ".msi", ".iso",
    ".mp4", ".mov", ".avi", ".mkv", ".webm",
    ".psd", ".blend", ".fbx", ".obj", ".glb", ".gltf",
    ".db", ".sqlite",
}

# Extensions rendered as markdown.
MARKDOWN_EXTENSIONS = {".md", ".markdown"}

# Extensions viewable as plain text.
TEXT_EXTENSIONS = {
    ".txt", ".py", ".js", ".ts", ".json", ".yaml", ".yml", ".toml", ".ini",
    ".cfg", ".css", ".html", ".xml", ".csv", ".bat", ".ps1", ".sh", ".log",
}

# Extensions served inline as images in the viewer.
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}

CONFIG_FILENAME = "workspace.config.json"
STATE_DIRNAME = ".cad-ui"


@dataclass
class WorkspaceConfig:
    root: Path
    excluded_dirs: set[str] = field(default_factory=lambda: set(DEFAULT_EXCLUDED_DIRS))
    excluded_extensions: set[str] = field(default_factory=lambda: set(DEFAULT_EXCLUDED_EXTENSIONS))
    claude_command: str = "claude"

    def is_dir_excluded(self, name: str) -> bool:
        for pattern in self.excluded_dirs:
            if "*" in pattern or "?" in pattern:
                if fnmatch.fnmatch(name.lower(), pattern.lower()):
                    return True
            elif name.lower() == pattern.lower():
                return True
        return False

    def is_file_excluded(self, name: str) -> bool:
        return Path(name).suffix.lower() in self.excluded_extensions

    @property
    def state_dir(self) -> Path:
        return self.root / STATE_DIRNAME


# The cad-ui repository root (this file is app/core/config.py).
REPO_ROOT = Path(__file__).resolve().parents[2]


def load_config(root: Path) -> WorkspaceConfig:
    """Build config for a workspace root, merging workspace.config.json if present."""
    cfg = WorkspaceConfig(root=root.resolve())
    config_path = cfg.root / CONFIG_FILENAME
    if config_path.is_file():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            # A broken config must not prevent startup, but the user must know
            # their settings were ignored rather than silently applied.
            print(f"[CAD UI] WARNING: ignoring {config_path}: {exc}", file=sys.stderr)
            return cfg
        for name in data.get("exclude_dirs", []):
            cfg.excluded_dirs.add(str(name))
        for ext in data.get("exclude_extensions", []):
            ext = str(ext).lower()
            cfg.excluded_extensions.add(ext if ext.startswith(".") else f".{ext}")
        # claude_command is executed in a terminal, so it is trusted ONLY when it
        # comes from the cad-ui repo's own config (isolated mode). A config file
        # inside an arbitrary opened workspace is untrusted data — ignore its
        # command and keep the default so a hostile workspace cannot run code.
        if cfg.root == REPO_ROOT:
            if isinstance(data.get("claude_command"), str) and data["claude_command"].strip():
                cfg.claude_command = data["claude_command"].strip()
        elif data.get("claude_command"):
            print(
                "[CAD UI] WARNING: ignoring 'claude_command' from a non-repo "
                f"workspace config ({config_path}) for security.",
                file=sys.stderr,
            )
    return cfg
