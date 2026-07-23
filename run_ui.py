"""CAD UI entry point.

Usage:
    python run_ui.py <path-to-workspace> [--port 8145] [--no-browser]
"""
from __future__ import annotations

import argparse
import sys
import threading
import webbrowser
from pathlib import Path

import uvicorn

from app.main import create_app


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cad-ui",
        description="CAD UI — локальная веб-обёртка над рабочей папкой.",
    )
    parser.add_argument("workspace", nargs="?",
                        help="путь к рабочей папке (по умолчанию — папка самого cad-ui)")
    parser.add_argument("--port", type=int, default=8145)
    parser.add_argument("--no-browser", action="store_true", help="не открывать браузер")
    args = parser.parse_args()

    root = Path(args.workspace).expanduser() if args.workspace else Path(__file__).resolve().parent
    if not root.is_dir():
        print(f"Ошибка: папка не найдена: {root}")
        return 2

    app = create_app(root)
    url = f"http://127.0.0.1:{args.port}"
    print(f"CAD UI: {root.resolve()}")
    print(f"Открой в браузере: {url}")

    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
