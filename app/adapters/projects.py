"""Adapter: team work — projects and their tasks under 'Working directory/'.

Structure (all optional metadata via frontmatter):
    Working directory/<project>/project.md            name, description, status, created, due
    Working directory/<project>/track/<task>.md        name, goal, state, started, due
    Working directory/<project>/track/current.txt       active task slug
    Working directory/<project>/track/_draft.md         unsent draft (flag only)

Panel is shown whenever 'Working directory/' exists (even empty) so the first
project can be created from the UI.
"""
from __future__ import annotations

import datetime
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter

from ..core import state
from ..core.config import WorkspaceConfig

WORKDIR_NAME = "Working directory"
# Archived projects move here; the name is already in DEFAULT_EXCLUDED_DIRS, so the
# contents drop out of the tree, search and graph automatically.
ARCHIVE_DIRNAME = "_archive"
SOON_DAYS = 3
PROJECT_STATUSES = ("active", "done", "frozen")

# Default per-project colours (data, not app theme) — customizable per project.
PALETTE = ["#d9822b", "#3b82f6", "#16a34a", "#a855f7",
           "#e0507e", "#0d9488", "#ca8a04", "#7c6cff"]
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def default_color(slug: str) -> str:
    return PALETTE[sum(slug.encode("utf-8")) % len(PALETTE)]

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    "і": "i", "ї": "yi", "є": "ye", "ґ": "g",
}


@dataclass
class Task:
    slug: str
    project_slug: str
    project_name: str
    name: str
    goal: str
    state: str
    started: str
    due: str
    rel_md: str
    is_active: bool = False
    has_draft: bool = False

    def urgency(self, today: datetime.date) -> str:
        """done / overdue / soon / ok / none — derived from state + due."""
        if self.state == "done":
            return "done"
        d = _parse_date(self.due)
        if not d:
            return "none"
        if d < today:
            return "overdue"
        if (d - today).days <= SOON_DAYS:
            return "soon"
        return "ok"


@dataclass
class Project:
    slug: str
    name: str
    description: str
    status: str
    created: str
    due: str
    rel_md: str
    color: str = ""
    task_count: int = 0
    active_count: int = 0
    overdue_count: int = 0


def _workdir(cfg: WorkspaceConfig) -> Path:
    return cfg.root / WORKDIR_NAME


def detect(cfg: WorkspaceConfig) -> bool:
    return _workdir(cfg).is_dir()


def _parse_date(value: str):
    m = re.search(r"(20\d{2}-\d{2}-\d{2})", str(value or ""))
    if not m:
        return None
    try:
        return datetime.date.fromisoformat(m.group(1))
    except ValueError:
        return None


def _load_meta(path: Path) -> dict:
    try:
        return frontmatter.loads(path.read_text(encoding="utf-8", errors="replace")).metadata
    except Exception:
        return {}


def slugify(name: str, taken: set[str] | None = None) -> str:
    s = "".join(_TRANSLIT.get(ch, ch) for ch in name.lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    s = s or "item"
    if taken:
        base, i = s, 2
        while s in taken:
            s = f"{base}-{i}"
            i += 1
    return s


# ---------- reading ----------

def list_projects(cfg: WorkspaceConfig) -> list[Project]:
    wd = _workdir(cfg)
    if not wd.is_dir():
        return []
    today = datetime.date.today()
    projects: list[Project] = []
    for child in sorted(wd.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue
        if child.name == ARCHIVE_DIRNAME:
            continue  # archived projects are hidden, and the folder itself is not a project
        md = child / "project.md"
        meta = _load_meta(md) if md.is_file() else {}
        tasks = list_tasks(cfg, child.name)
        color = str(meta.get("color", "")).strip()
        if not _HEX_RE.match(color):
            color = default_color(child.name)
        projects.append(Project(
            slug=child.name,
            name=str(meta.get("name", child.name)),
            description=str(meta.get("description", "")),
            status=str(meta.get("status", "active")),
            created=str(meta.get("created", "")),
            due=str(meta.get("due", "")),
            rel_md=str(md.relative_to(cfg.root)) if md.is_file() else "",
            color=color,
            task_count=len(tasks),
            active_count=sum(1 for t in tasks if t.state != "done"),
            overdue_count=sum(1 for t in tasks if t.urgency(today) == "overdue"),
        ))
    return projects


def list_tasks(cfg: WorkspaceConfig, project_slug: str) -> list[Task]:
    track = _workdir(cfg) / project_slug / "track"
    if not track.is_dir():
        return []
    project_md = _workdir(cfg) / project_slug / "project.md"
    project_name = str(_load_meta(project_md).get("name", project_slug)) if project_md.is_file() else project_slug
    active_slug = ""
    current = track / "current.txt"
    if current.is_file():
        try:
            active_slug = current.read_text(encoding="utf-8").strip()
        except OSError:
            active_slug = ""
    has_draft = (track / "_draft.md").is_file()
    tasks: list[Task] = []
    for md in sorted(track.glob("*.md"), key=lambda p: p.name.lower()):
        if md.name == "_draft.md":
            continue
        meta = _load_meta(md)
        slug = md.stem
        tasks.append(Task(
            slug=slug,
            project_slug=project_slug,
            project_name=project_name,
            name=str(meta.get("name", slug)),
            goal=str(meta.get("goal", "")),
            state=str(meta.get("state", "active")),
            started=str(meta.get("started", "")),
            due=str(meta.get("due", "")),
            rel_md=str(md.relative_to(cfg.root)),
            is_active=(slug == active_slug),
            has_draft=has_draft,
        ))
    return tasks


def all_tasks(cfg: WorkspaceConfig) -> list[Task]:
    out: list[Task] = []
    for p in list_projects(cfg):
        out.extend(list_tasks(cfg, p.slug))
    return out


def work_stats(cfg: WorkspaceConfig) -> dict:
    projects = list_projects(cfg)
    tasks = all_tasks(cfg)
    return {
        "projects": len(projects),
        "tasks": len(tasks),
        "active": sum(1 for t in tasks if t.state != "done"),
        "done": sum(1 for t in tasks if t.state == "done"),
    }


# ---------- creating ----------

class WorkError(Exception):
    pass


def _existing_project_slugs(cfg: WorkspaceConfig) -> set[str]:
    wd = _workdir(cfg)
    return {c.name for c in wd.iterdir() if c.is_dir()} if wd.is_dir() else set()


def create_project(cfg: WorkspaceConfig, name: str, description: str) -> str:
    name = (name or "").strip()
    if not name:
        raise WorkError("Название проекта не может быть пустым.")
    wd = _workdir(cfg)
    wd.mkdir(exist_ok=True)
    slug = slugify(name, _existing_project_slugs(cfg))
    proj = wd / slug
    proj.mkdir()
    today = datetime.date.today().isoformat()
    post = frontmatter.Post(
        "",
        name=name,
        description=(description or "").strip(),
        status="active",
        created=today,
    )
    (proj / "project.md").write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
    return slug


def create_task(cfg: WorkspaceConfig, project_slug: str, name: str, goal: str,
                steps: str, due: str, started: str = "") -> str:
    if project_slug not in _existing_project_slugs(cfg):
        raise WorkError("Проект не найден.")
    name = (name or "").strip()
    if not name:
        raise WorkError("Название задачи не может быть пустым.")
    track = _workdir(cfg) / project_slug / "track"
    track.mkdir(exist_ok=True)
    taken = {p.stem for p in track.glob("*.md")}
    slug = slugify(name, taken)
    due_clean = ""
    d = _parse_date(due)
    if due and not d:
        raise WorkError("Дедлайн должен быть датой в формате ГГГГ-ММ-ДД.")
    if d:
        due_clean = d.isoformat()
    started_date = _parse_date(started) or datetime.date.today()
    today = datetime.date.today().isoformat()
    step_lines = [s.strip() for s in (steps or "").splitlines() if s.strip()]
    plan = "\n".join(f"- [ ] {s}" for s in step_lines) or "- [ ] (шаги не заданы)"
    meta = {"name": name, "goal": (goal or "").strip(), "state": "active",
            "started": started_date.isoformat()}
    if due_clean:
        meta["due"] = due_clean
    body = f"## Трек (план)\n\n{plan}\n\n## Журнал\n\n- {today} — задача создана.\n"
    post = frontmatter.Post(body, **meta)
    (track / f"{slug}.md").write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
    (track / "current.txt").write_text(slug, encoding="utf-8")
    return slug


def set_project_status(cfg: WorkspaceConfig, slug: str, status: str) -> None:
    if status not in PROJECT_STATUSES:
        raise WorkError("Недопустимый статус проекта.")
    if slug not in _existing_project_slugs(cfg):
        raise WorkError("Проект не найден.")
    md = _workdir(cfg) / slug / "project.md"
    if md.is_file():
        post = frontmatter.loads(md.read_text(encoding="utf-8", errors="replace"))
    else:
        post = frontmatter.Post("", name=slug, created=datetime.date.today().isoformat())
    post["status"] = status
    md.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")


def _require_project(cfg: WorkspaceConfig, slug: str) -> Path:
    """Validate a client-supplied slug and return the project folder.

    Membership in _existing_project_slugs (iterdir names) implicitly rejects '..',
    slashes and absolute paths — the same guard the other mutators rely on.
    """
    if slug == ARCHIVE_DIRNAME or slug not in _existing_project_slugs(cfg):
        raise WorkError("Проект не найден.")
    return _workdir(cfg) / slug


def archive_project(cfg: WorkspaceConfig, slug: str) -> None:
    """Move a project to 'Working directory/_archive/<slug>/' (recoverable by hand)."""
    proj = _require_project(cfg, slug)
    archive = _workdir(cfg) / ARCHIVE_DIRNAME
    archive.mkdir(exist_ok=True)
    dest = archive / slug
    n = 2
    while dest.exists():  # same dedup idea as slugify: -2, -3, …
        dest = archive / f"{slug}-{n}"
        n += 1
    shutil.move(str(proj), str(dest))
    state.prune_favorites(cfg, f"{WORKDIR_NAME}/{slug}/")


def delete_project(cfg: WorkspaceConfig, slug: str) -> None:
    """Permanently delete a project folder. Unrecoverable: contents are git-ignored."""
    proj = _require_project(cfg, slug)
    shutil.rmtree(proj)
    state.prune_favorites(cfg, f"{WORKDIR_NAME}/{slug}/")


def set_project_color(cfg: WorkspaceConfig, slug: str, color: str) -> None:
    if not _HEX_RE.match(color or ""):
        raise WorkError("Цвет должен быть в формате #RRGGBB.")
    if slug not in _existing_project_slugs(cfg):
        raise WorkError("Проект не найден.")
    md = _workdir(cfg) / slug / "project.md"
    if md.is_file():
        post = frontmatter.loads(md.read_text(encoding="utf-8", errors="replace"))
    else:
        post = frontmatter.Post("", name=slug, created=datetime.date.today().isoformat())
    post["color"] = color.lower()
    md.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")


# ---------- timeline ----------

@dataclass
class TimelineBar:
    task: Task
    left: float
    width: float
    urgency: str
    color: str = ""


_MONTHS_RU = ["", "янв", "фев", "мар", "апр", "май", "июн",
              "июл", "авг", "сен", "окт", "ноя", "дек"]


@dataclass
class Timeline:
    rows: list[TimelineBar] = field(default_factory=list)
    days: list[dict] = field(default_factory=list)   # [{left,width,num,is_weekend,is_today,month}]
    legend: list[dict] = field(default_factory=list)  # [{name,color}] projects shown on the chart
    today_left: float = -1.0
    has_data: bool = False


def timeline(cfg: WorkspaceConfig, today: datetime.date | None = None,
             max_days: int = 56) -> Timeline:
    today = today or datetime.date.today()
    project_color = {p.slug: p.color for p in list_projects(cfg)}
    tasks = [t for t in all_tasks(cfg) if _parse_date(t.due)]
    tl = Timeline()
    if not tasks:
        return tl

    def start_of(t: Task) -> datetime.date:
        d = _parse_date(t.started)
        due = _parse_date(t.due)
        return d if d and d <= due else (due - datetime.timedelta(days=SOON_DAYS))

    starts = [start_of(t) for t in tasks]
    dues = [_parse_date(t.due) for t in tasks]
    # Day-column window anchored on today, capped so columns stay readable.
    win_start = max(min(min(starts), today), today - datetime.timedelta(days=14))
    win_end = max(max(dues), today + datetime.timedelta(days=7))
    total_days = (win_end - win_start).days + 1
    if total_days > max_days:
        total_days = max_days
        win_end = win_start + datetime.timedelta(days=total_days - 1)
    day_w = round(100 / total_days, 4)

    def pct(d: datetime.date) -> float:
        clamped = min(max(d, win_start), win_end + datetime.timedelta(days=1))
        return round((clamped - win_start).days / total_days * 100, 3)

    for i in range(total_days):
        d = win_start + datetime.timedelta(days=i)
        tl.days.append({
            "left": round(i * day_w, 3),
            "width": day_w,
            "num": d.day,
            "is_weekend": d.weekday() >= 5,
            "is_today": d == today,
            "month": _MONTHS_RU[d.month] if (i == 0 or d.day == 1) else "",
        })

    seen: dict[str, str] = {}
    for t in sorted(tasks, key=lambda t: _parse_date(t.due)):
        s, e = start_of(t), _parse_date(t.due)
        left = pct(s)
        # bar spans inclusive of the due day
        width = max(pct(e + datetime.timedelta(days=1)) - left, day_w)
        color = project_color.get(t.project_slug) or default_color(t.project_slug)
        tl.rows.append(TimelineBar(t, left, width, t.urgency(today), color))
        if t.project_slug not in seen:
            seen[t.project_slug] = t.project_name
            tl.legend.append({"name": t.project_name, "color": color})

    tl.today_left = pct(today)
    tl.has_data = True
    return tl
