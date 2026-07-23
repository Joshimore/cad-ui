"""Markdown rendering: CommonMark + tables/strikethrough/tasklists + link rewriting."""
from __future__ import annotations

import html as html_mod
import posixpath
from urllib.parse import quote, urlparse

import frontmatter
from markdown_it import MarkdownIt
from mdit_py_plugins.tasklists import tasklists_plugin

from .config import MARKDOWN_EXTENSIONS


def _is_external(href: str) -> bool:
    parsed = urlparse(href)
    return bool(parsed.scheme) or href.startswith("//") or href.startswith("#")


def _rewrite(href: str, base_rel_dir: str, route: str) -> str:
    """Turn a document-relative href into a viewer/raw route URL."""
    joined = posixpath.normpath(posixpath.join(base_rel_dir, href)) if base_rel_dir else posixpath.normpath(href)
    if joined.startswith(".."):
        return href  # points outside the workspace: leave as-is, the server will 403 it
    return f"{route}?path={quote(joined)}"


def _build_renderer(base_rel_dir: str) -> MarkdownIt:
    md = MarkdownIt("commonmark").enable("table").enable("strikethrough").use(tasklists_plugin)

    def link_open(tokens, idx, options, env):
        token = tokens[idx]
        href = token.attrGet("href") or ""
        if href and not _is_external(href):
            ext = posixpath.splitext(urlparse(href).path)[1].lower()
            route = "/view" if ext in MARKDOWN_EXTENSIONS or ext == "" else "/raw"
            token.attrSet("href", _rewrite(href, base_rel_dir, route))
        elif href and not href.startswith("#"):
            token.attrSet("target", "_blank")
            token.attrSet("rel", "noopener")
        return md.renderer.renderToken(tokens, idx, options, env)

    def image(tokens, idx, options, env):
        token = tokens[idx]
        src = token.attrGet("src") or ""
        if src and not _is_external(src):
            src = _rewrite(src, base_rel_dir, "/raw")
        alt = html_mod.escape(token.content or "")
        return f'<img src="{html_mod.escape(src, quote=True)}" alt="{alt}" loading="lazy">'

    md.renderer.rules["link_open"] = link_open
    md.renderer.rules["image"] = image
    return md


def render_markdown(raw_text: str, rel_path: str) -> tuple[dict, str]:
    """Split frontmatter and render body to HTML. Returns (metadata, html)."""
    try:
        post = frontmatter.loads(raw_text)
        meta = {str(k): str(v) for k, v in post.metadata.items()}
        body = post.content
    except Exception:
        meta, body = {}, raw_text  # malformed frontmatter must not kill the viewer
    base_rel_dir = posixpath.dirname(rel_path.replace("\\", "/"))
    html = _build_renderer(base_rel_dir).render(body)
    return meta, html
