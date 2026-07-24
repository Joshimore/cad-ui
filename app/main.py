"""CAD UI — FastAPI application. Strictly local: binds 127.0.0.1, no external calls."""
from __future__ import annotations

import datetime
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from fastapi import Body

from . import __version__
from .adapters import agents_skills
from .adapters import projects
from .core import graph
from .core import index
from .core import state as state_mod
from .services import launcher
from .core.config import WorkspaceConfig, load_config
from .core.markdown import render_markdown
from .core.scanner import (
    Entry,
    PathOutsideWorkspace,
    file_kind,
    list_dir,
    recent_files,
    resolve_safe,
)

APP_DIR = Path(__file__).parent
MAX_TEXT_BYTES = 2 * 1024 * 1024  # refuse to render text files above 2 MB
ALLOWED_HOSTS = {"127.0.0.1", "localhost"}  # reject other Host headers (DNS rebinding)


def create_app(workspace_root: Path) -> FastAPI:
    cfg: WorkspaceConfig = load_config(workspace_root)
    app = FastAPI(title="CAD UI", docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=APP_DIR / "web" / "static"), name="static")
    templates = Jinja2Templates(directory=APP_DIR / "web" / "templates")

    @app.middleware("http")
    async def security_guard(request: Request, call_next):
        # Block DNS-rebinding: a remote page keeps its own hostname in Host.
        host = (request.headers.get("host") or "").split(":")[0]
        if host and host not in ALLOWED_HOSTS:
            return JSONResponse({"detail": "Host not allowed"}, status_code=403)
        # Block cross-origin CSRF on state-changing endpoints: cross-site forms
        # and no-cors fetches cannot set a custom request header.
        if request.method == "POST" and request.url.path.startswith("/api/"):
            if request.headers.get("x-requested-with") != "cad-ui":
                return JSONResponse({"detail": "CSRF check failed"}, status_code=403)
        return await call_next(request)

    # Ensure the team working directory exists so its panel and create buttons work.
    (cfg.root / projects.WORKDIR_NAME).mkdir(exist_ok=True)

    # Build the search index in the background so startup is not blocked.
    threading.Thread(target=index.build, args=(cfg,), daemon=True).start()

    def guard(rel_path: str) -> Path:
        try:
            return resolve_safe(cfg, rel_path)
        except PathOutsideWorkspace:
            raise HTTPException(status_code=403, detail="Path outside workspace")

    def fmt_mtime(ts: float) -> str:
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

    def base_ctx(nav: str) -> dict:
        return {
            "workspace": str(cfg.root),
            "workspace_name": cfg.root.name,
            "has_agents_panel": agents_skills.detect(cfg),
            "has_work_panel": projects.detect(cfg),
            "nav": nav,
            "fav_count": len(state_mod.load_favorites(cfg)),
            "version": __version__,
        }

    def filelist_items(entries_with_mtime) -> list[dict]:
        return [{"entry": e, "mtime": fmt_mtime(m)} for e, m in entries_with_mtime]

    # ---------- pages ----------

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        agents = agents_skills.list_agents(cfg)
        skills = agents_skills.list_skills(cfg)
        recents = filelist_items(recent_files(cfg)[:8])
        return templates.TemplateResponse(request, "home.html", {
            **base_ctx("home"),
            "recents": recents,
            "agent_count": len(agents),
            "skill_count": len(skills),
            "recent_count": len(recents),
            "work": projects.work_stats(cfg),
            "timeline": projects.timeline(cfg),
        })

    @app.get("/docs", response_class=HTMLResponse)
    def docs(request: Request):
        return templates.TemplateResponse(request, "docs.html", {
            **base_ctx("docs"),
            "file": None,
        })

    @app.get("/view", response_class=HTMLResponse)
    def view(request: Request, path: str = Query(...)):
        target = guard(path)
        if target.is_dir():
            raise HTTPException(status_code=400, detail="Is a directory")
        if not target.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        kind = file_kind(target)
        file_ctx = {
            "rel_path": path.replace("\\", "/"),
            "name": target.name,
            "kind": kind,
            "mtime": fmt_mtime(target.stat().st_mtime),
            "is_favorite": state_mod.is_favorite(cfg, path),
        }
        if kind == "markdown":
            raw = _read_text(target)
            meta, html = render_markdown(raw, path)
            file_ctx.update(meta=meta, content_html=html)
        elif kind == "text":
            file_ctx.update(text=_read_text(target))
        elif kind == "image":
            pass  # template shows <img src=/raw>
        else:
            size_mb = target.stat().st_size / (1024 * 1024)
            file_ctx.update(size_mb=f"{size_mb:.1f}")
        return templates.TemplateResponse(request, "docs.html", {
            **base_ctx("docs"),
            "file": file_ctx,
        })

    @app.get("/search", response_class=HTMLResponse)
    def search_page(request: Request, q: str = Query(default=""),
                    subsystem: str = Query(default=""), type: str = Query(default="")):
        index.sync(cfg)  # cheap incremental refresh (throttled)
        q = q.strip()
        hits = index.search(cfg, q, subsystem=subsystem, ftype=type) if q else []
        return templates.TemplateResponse(request, "search.html", {
            **base_ctx("search"),
            "q": q,
            "hits": [{"hit": h, "mtime": fmt_mtime(h.mtime)} for h in hits],
            "facets": index.facets(cfg),
            "active_subsystem": subsystem,
            "active_type": type,
        })

    @app.post("/api/reindex")
    def reindex():
        index.build(cfg)
        return JSONResponse({"ok": True, "total": index.facets(cfg)["total"]})

    @app.get("/api/graph")
    def graph_data():
        return JSONResponse(graph.build_graph(cfg))

    @app.get("/recent", response_class=HTMLResponse)
    def recent_page(request: Request):
        return templates.TemplateResponse(request, "filelist_page.html", {
            **base_ctx("recent"),
            "page_title": "Недавние",
            "page_sub": "Последние изменённые документы рабочего пространства",
            "items": filelist_items(recent_files(cfg)),
            "empty_text": "Нет недавних файлов",
        })

    @app.get("/favorites", response_class=HTMLResponse)
    def favorites_page(request: Request):
        items = []
        for rel in state_mod.load_favorites(cfg):
            target = cfg.root / rel
            if target.is_file():
                entry = Entry(target.name, rel, False, kind=file_kind(target))
                items.append({"entry": entry, "mtime": fmt_mtime(target.stat().st_mtime)})
        return templates.TemplateResponse(request, "filelist_page.html", {
            **base_ctx("favorites"),
            "page_title": "Избранное",
            "page_sub": "Закреплённые документы",
            "items": items,
            "empty_text": "Избранного пока нет — открой файл и нажми ★",
        })

    @app.get("/graph", response_class=HTMLResponse)
    def graph_page(request: Request):
        return templates.TemplateResponse(request, "graph.html", base_ctx("graph"))

    @app.get("/agents", response_class=HTMLResponse)
    def agents_page(request: Request):
        return templates.TemplateResponse(request, "registry.html", {
            **base_ctx("agents"),
            "page_title": "Агенты",
            "page_sub": "Автономные роли из .claude/agents",
            "items": agents_skills.list_agents(cfg),
            "empty_text": "В .claude/agents пока пусто",
        })

    @app.get("/skills", response_class=HTMLResponse)
    def skills_page(request: Request):
        return templates.TemplateResponse(request, "registry.html", {
            **base_ctx("skills"),
            "page_title": "Навыки",
            "page_sub": "Skills из .claude/skills",
            "items": agents_skills.list_skills(cfg),
            "empty_text": "В .claude/skills пока пусто",
        })

    @app.get("/projects", response_class=HTMLResponse)
    def projects_page(request: Request):
        return templates.TemplateResponse(request, "projects.html", {
            **base_ctx("projects"),
            "projects": projects.list_projects(cfg),
        })

    @app.get("/project", response_class=HTMLResponse)
    def project_page(request: Request, slug: str = Query(...)):
        items = projects.list_projects(cfg)
        proj = next((p for p in items if p.slug == slug), None)
        if proj is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return templates.TemplateResponse(request, "project.html", {
            **base_ctx("projects"),
            "project": proj,
            "tasks": projects.list_tasks(cfg, slug),
            "today": datetime.date.today().isoformat(),
            "statuses": projects.PROJECT_STATUSES,
        })

    @app.post("/api/project/create")
    def project_create(payload: dict = Body(...)):
        try:
            slug = projects.create_project(cfg, payload.get("name", ""),
                                           payload.get("description", ""))
        except projects.WorkError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return JSONResponse({"ok": True, "slug": slug})

    @app.post("/api/task/create")
    def task_create(payload: dict = Body(...)):
        try:
            slug = projects.create_task(
                cfg, payload.get("project", ""), payload.get("name", ""),
                payload.get("goal", ""), payload.get("steps", ""),
                payload.get("due", ""), payload.get("started", ""))
        except projects.WorkError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return JSONResponse({"ok": True, "slug": slug})

    @app.post("/api/project/status")
    def project_status(payload: dict = Body(...)):
        try:
            projects.set_project_status(cfg, payload.get("slug", ""), payload.get("status", ""))
        except projects.WorkError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return JSONResponse({"ok": True})

    @app.post("/api/project/color")
    def project_color(payload: dict = Body(...)):
        try:
            projects.set_project_color(cfg, payload.get("slug", ""), payload.get("color", ""))
        except projects.WorkError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return JSONResponse({"ok": True})

    # ---------- api ----------

    @app.get("/api/tree", response_class=HTMLResponse)
    def tree(request: Request, path: str = Query(default="")):
        directory = guard(path)
        if not directory.is_dir():
            raise HTTPException(status_code=404, detail="Not a directory")
        entries = list_dir(cfg, path)
        return templates.TemplateResponse(request, "_tree.html", {"entries": entries})

    @app.post("/api/claude-launch")
    def claude_launch():
        # Reload config so an edited claude_command applies without a restart.
        try:
            launcher.launch_claude(load_config(cfg.root))
        except launcher.LaunchError as exc:
            raise HTTPException(status_code=500, detail=str(exc))
        return JSONResponse({"ok": True})

    @app.post("/api/favorite")
    def favorite_toggle(path: str = Query(...)):
        guard(path)
        now = state_mod.toggle_favorite(cfg, path)
        return JSONResponse({"favorite": now})

    @app.get("/raw")
    def raw(path: str = Query(...)):
        target = guard(path)
        if not target.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(target)

    def _read_text(target: Path) -> str:
        if target.stat().st_size > MAX_TEXT_BYTES:
            raise HTTPException(status_code=413, detail="File too large to render")
        return target.read_text(encoding="utf-8", errors="replace")

    return app
