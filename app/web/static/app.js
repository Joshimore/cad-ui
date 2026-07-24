/* CAD UI — vanilla JS: lazy tree, SPA-style navigation, favorites. */
(function () {
  "use strict";

  /* ---------- lazy tree ---------- */
  async function loadChildren(li) {
    const ul = li.querySelector(":scope > ul.children");
    if (!ul || ul.dataset.loaded) return;
    ul.dataset.loaded = "1";
    const resp = await fetch("/api/tree?path=" + encodeURIComponent(li.dataset.path));
    if (resp.ok) ul.innerHTML = await resp.text();
  }

  async function initRoot() {
    const root = document.querySelector("ul.children.root");
    if (!root || root.dataset.loaded) return;
    root.dataset.loaded = "1";
    const resp = await fetch("/api/tree?path=");
    if (resp.ok) root.innerHTML = await resp.text();
  }

  document.addEventListener("click", function (e) {
    const label = e.target.closest(".dir-label");
    if (label) {
      const li = label.closest("li.dir");
      if (li.classList.contains("excluded")) return;
      li.classList.toggle("open");
      const ul = li.querySelector(":scope > ul.children");
      if (ul) {
        ul.hidden = !li.classList.contains("open");
        loadChildren(li);
      }
      return;
    }

    /* ---------- SPA navigation for .nav links ---------- */
    const link = e.target.closest("a.nav");
    if (link) {
      e.preventDefault();
      navigate(link.getAttribute("href"), true);
      return;
    }

    /* ---------- favorite toggle ---------- */
    const fav = e.target.closest(".fav-btn");
    if (fav) {
      apiPost("/api/favorite?path=" + encodeURIComponent(fav.dataset.path))
        .then((r) => r.json())
        .then((data) => fav.classList.toggle("on", data.favorite));
      return;
    }

    /* ---------- Claude Launch ---------- */
    const cl = e.target.closest("#claude-launch");
    if (cl) {
      cl.disabled = true;  /* disabled buttons emit no clicks, so no double-launch */
      apiPost("/api/claude-launch")
        .then(async (r) => {
          if (r.ok) {
            flashBtn(cl, "ok", ">_ запущен");
          } else {
            const data = await r.json().catch(() => ({}));
            flashBtn(cl, "err", "ошибка");
            if (data.detail) alert(data.detail);
          }
        })
        .catch(() => flashBtn(cl, "err", "ошибка"));
      return;
    }

    /* ---------- reindex ---------- */
    const ri = e.target.closest("#reindex");
    if (ri) {
      ri.disabled = true;
      flashBtn(ri, "ok", "⟳ индексирую…");
      apiPost("/api/reindex")
        .then((r) => r.json())
        .then(() => navigate(location.pathname + location.search, false))
        .catch(() => {})
        .finally(() => { ri.disabled = false; });
      return;
    }

    /* ---------- create-form toggles ---------- */
    const tgl = e.target.closest("#new-project-toggle, #new-task-toggle");
    if (tgl) {
      const form = tgl.parentElement.querySelector(".create-form");
      if (form) {
        form.hidden = !form.hidden;
        if (!form.hidden) { const f = form.querySelector("input, textarea"); if (f) f.focus(); }
      }
      return;
    }

    /* ---------- project status change ---------- */
    const so = e.target.closest(".status-opt");
    if (so && !so.classList.contains("on")) {
      const seg = so.closest(".status-seg");
      apiPost("/api/project/status", { slug: seg.dataset.slug, status: so.dataset.status })
        .then((r) => { if (r.ok) navigate(location.pathname + location.search, false); });
    }
  });

  /* ---------- project colour picker ---------- */
  document.addEventListener("change", function (e) {
    const ci = e.target.closest("#project-color");
    if (!ci) return;
    apiPost("/api/project/color", { slug: ci.dataset.slug, color: ci.value })
      .then((r) => { if (r.ok) navigate(location.pathname + location.search, false); });
  });

  /* ---------- forms → SPA / create actions ---------- */
  document.addEventListener("submit", function (e) {
    const search = e.target.closest("#search-form");
    if (search) {
      e.preventDefault();
      const q = (search.querySelector('input[name="q"]').value || "").trim();
      navigate("/search?q=" + encodeURIComponent(q), true);
      return;
    }

    const proj = e.target.closest("#new-project-form");
    if (proj) {
      e.preventDefault();
      submitCreate(proj, "/api/project/create", {
        name: proj.name.value, description: proj.description.value,
      }, (data) => "/project?slug=" + encodeURIComponent(data.slug));
      return;
    }

    const task = e.target.closest("#new-task-form");
    if (task) {
      e.preventDefault();
      submitCreate(task, "/api/task/create", {
        project: task.dataset.project, name: task.name.value,
        goal: task.goal.value, steps: task.steps.value,
        started: task.started.value, due: task.due.value,
      }, () => "/project?slug=" + encodeURIComponent(task.dataset.project));
      return;
    }
  });

  async function submitCreate(form, url, body, nextUrl) {
    const btn = form.querySelector('button[type="submit"]');
    if (btn) btn.disabled = true;
    try {
      const r = await apiPost(url, body);
      const data = await r.json().catch(() => ({}));
      if (r.ok) {
        navigate(nextUrl(data), true);
      } else {
        alert(data.detail || "Не удалось создать.");
      }
    } catch (_) {
      alert("Ошибка сети.");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function apiPost(url, body) {
    const opts = { method: "POST", headers: { "X-Requested-With": "cad-ui" } };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(url, opts);
  }

  function flashBtn(btn, cls, text) {
    if (!btn.dataset.label) btn.dataset.label = btn.textContent;
    clearTimeout(btn._flashTimer);
    btn.classList.remove("ok", "err");
    btn.classList.add(cls);
    btn.textContent = text;
    btn._flashTimer = setTimeout(() => {
      btn.classList.remove(cls);
      btn.textContent = btn.dataset.label;
      btn.disabled = false;
    }, 2000);
  }

  /* Swap strategy: if both the current page and the response contain #doc-view
     (Документы), swap only the viewer pane so the tree keeps its state.
     Otherwise swap the whole #content area and header. */
  async function navigate(url, push) {
    const resp = await fetch(url);
    if (!resp.ok) {
      const target = document.getElementById("doc-view") || document.getElementById("content");
      target.innerHTML = '<p class="empty">Ошибка ' + resp.status + "</p>";
      return;
    }
    const html = await resp.text();
    const doc = new DOMParser().parseFromString(html, "text/html");

    const curView = document.getElementById("doc-view");
    const newView = doc.getElementById("doc-view");
    if (curView && newView) {
      curView.replaceWith(newView);
      syncChrome(doc);
    } else {
      const curContent = document.getElementById("content");
      const newContent = doc.getElementById("content");
      if (!newContent) { location.href = url; return; }
      curContent.replaceWith(newContent);
      syncChrome(doc);
      initRoot();
    }
    if (push) history.pushState({}, "", url);
    document.title = doc.title;
    const scrollTarget = document.getElementById("doc-view") || document.getElementById("content");
    scrollTarget.scrollTop = 0;
  }

  function syncChrome(doc) {
    /* Replace whole nodes (the click listener is delegated on document, so this
       is safe) — this keeps nav in sync even when the «Реестр» section appears
       or disappears mid-session, which index-based pairing could not. */
    const curBar = document.querySelector(".topbar-title");
    const newBar = doc.querySelector(".topbar-title");
    if (curBar && newBar) curBar.replaceWith(newBar);
    const curNav = document.querySelector(".nav-rail");
    const newNav = doc.querySelector(".nav-rail");
    if (curNav && newNav) curNav.replaceWith(newNav);
  }

  window.addEventListener("popstate", function () {
    navigate(location.pathname + location.search, false);
  });

  initRoot();
})();
