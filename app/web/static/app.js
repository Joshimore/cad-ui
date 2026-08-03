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

    /* ---------- theme toggle ---------- */
    if (e.target.closest("#theme-toggle")) { toggleTheme(); return; }

    /* ---------- first-run onboarding overlay ---------- */
    if (e.target.closest("#onboard-never")) { hideOnboard(true); return; }
    if (e.target.closest("#onboard-close")) { hideOnboard(false); return; }
    if (e.target.closest("#onboard-open")) {
      hideOnboard(false);
      navigate("/view?path=INSTRUCTION.md", true);
      return;
    }
    if (e.target.id === "onboard") { hideOnboard(false); return; }  // click on the backdrop

    /* ---------- knowledge-base trust-level filter ---------- */
    const kf = e.target.closest(".kb-filter");
    if (kf) { kf.classList.toggle("on"); applyKbFilters(); return; }

    /* ---------- open document editor ---------- */
    const ed = e.target.closest("#doc-edit");
    if (ed) { openEditor(ed); return; }

    /* ---------- project status change ---------- */
    const so = e.target.closest(".status-opt");
    if (so && !so.classList.contains("on")) {
      const seg = so.closest(".status-seg");
      apiPost("/api/project/status", { slug: seg.dataset.slug, status: so.dataset.status })
        .then((r) => { if (r.ok) navigate(location.pathname + location.search, false); });
      return;
    }

    /* ---------- project archive / delete ---------- */
    const arch = e.target.closest("#project-archive");
    if (arch) {
      arch.disabled = true;
      projectRemove("/api/project/archive", arch);
      return;
    }
    const del = e.target.closest("#project-delete");
    if (del) {
      if (!del.classList.contains("armed")) {
        // First click arms the button; a click elsewhere or a timeout disarms it.
        del.classList.add("armed");
        if (!del.dataset.label) del.dataset.label = del.textContent;
        del.textContent = "Точно удалить навсегда?";
        del._armTimer = setTimeout(() => disarmDelete(del), 4000);
      } else {
        clearTimeout(del._armTimer);
        del.disabled = true;
        projectRemove("/api/project/delete", del);
      }
      return;
    }
    const armed = document.querySelector("#project-delete.armed");
    if (armed) disarmDelete(armed);  // any other click disarms
  });

  function disarmDelete(btn) {
    clearTimeout(btn._armTimer);
    btn.classList.remove("armed");
    if (btn.dataset.label) btn.textContent = btn.dataset.label;
  }

  async function projectRemove(url, btn) {
    try {
      const r = await apiPost(url, { slug: btn.dataset.slug });
      if (r.ok) { navigate("/projects", true); return; }  // the old URL would 404
      const data = await r.json().catch(() => ({}));
      alert(data.detail || "Не получилось.");
    } catch (_) {
      alert("Ошибка сети.");
    }
    btn.disabled = false;
    if (btn.id === "project-delete") disarmDelete(btn);
  }

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

  /* ---------- document editor ---------- */
  async function openEditor(btn) {
    const path = btn.dataset.path;
    const pane = document.querySelector(".md-content, .text-content");
    if (!pane) return;
    let raw;
    try {
      const r = await fetch("/raw?path=" + encodeURIComponent(path));
      if (!r.ok) throw 0;
      raw = await r.text();
    } catch (_) {
      alert("Не удалось открыть файл для правки.");
      return;
    }
    btn.disabled = true;

    const wrap = document.createElement("div");
    wrap.className = "editor-wrap";
    const bar = document.createElement("div");
    bar.className = "editor-bar";
    const saveBtn = document.createElement("button");
    saveBtn.className = "btn btn-primary";
    saveBtn.textContent = "Сохранить";
    const cancelBtn = document.createElement("button");
    cancelBtn.className = "btn btn-ghost";
    cancelBtn.textContent = "Отмена";
    const hint = document.createElement("span");
    hint.className = "editor-hint";
    hint.textContent = "Ctrl+S — сохранить · Esc — отмена";
    bar.append(saveBtn, cancelBtn, hint);
    const ta = document.createElement("textarea");
    ta.className = "md-editor";
    ta.value = raw;
    ta.spellcheck = false;
    wrap.append(bar, ta);
    pane.replaceWith(wrap);
    ta.focus();

    const reload = () => navigate(location.pathname + location.search, false);
    const save = async () => {
      saveBtn.disabled = true;
      try {
        const r = await apiPost("/api/file/save", { path: path, content: ta.value });
        const data = await r.json().catch(() => ({}));
        if (r.ok) reload();
        else { alert(data.detail || "Не удалось сохранить."); saveBtn.disabled = false; }
      } catch (_) {
        alert("Ошибка сети.");
        saveBtn.disabled = false;
      }
    };
    saveBtn.addEventListener("click", save);
    cancelBtn.addEventListener("click", reload);
    ta.addEventListener("keydown", (ev) => {
      if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "s") { ev.preventDefault(); save(); }
      else if (ev.key === "Escape") { ev.preventDefault(); reload(); }
    });
  }

  /* ---------- theme ---------- */
  function toggleTheme() {
    const root = document.documentElement;
    const next = root.dataset.theme === "dark" ? "light" : "dark";
    root.classList.add("theme-anim");           // enable the cross-fade for the switch
    root.dataset.theme = next;
    try { localStorage.setItem("cadui-theme", next); } catch (_) {}
    updateThemeToggle(next);
    setTimeout(() => root.classList.remove("theme-anim"), 360);
  }
  function updateThemeToggle(theme) {
    const btn = document.getElementById("theme-toggle");
    if (!btn) return;
    btn.textContent = theme === "dark" ? "☀" : "☾";
    btn.title = theme === "dark" ? "Светлая тема" : "Тёмная тема";
  }
  updateThemeToggle(document.documentElement.dataset.theme || "light");

  /* ---------- first-run onboarding overlay ---------- */
  function showOnboard() {
    const ov = document.getElementById("onboard");
    if (!ov) return;
    ov.hidden = false;
    const btn = document.getElementById("claude-launch");
    if (btn) btn.classList.add("pulse");  // draw the eye to the real button
  }
  function hideOnboard(permanent) {
    const ov = document.getElementById("onboard");
    if (ov) ov.hidden = true;
    const btn = document.getElementById("claude-launch");
    if (btn) btn.classList.remove("pulse");
    if (permanent) { try { localStorage.setItem("cadui-onboarded", "1"); } catch (_) {} }
  }
  function maybeShowOnboard() {
    let done = "0";
    try { done = localStorage.getItem("cadui-onboarded") || "0"; } catch (_) {}
    if (done !== "1") showOnboard();  // shows on every full load until dismissed for good
  }

  /* ---------- knowledge-base filter: hide cards whose trust level is toggled off ---------- */
  function applyKbFilters() {
    const off = new Set();
    document.querySelectorAll(".kb-filter:not(.on)").forEach((b) => off.add(b.dataset.trust));
    let shown = 0;
    document.querySelectorAll(".kb-card").forEach((c) => {
      const hide = off.has(c.dataset.trust);   // cards with no trust level are never hidden
      c.hidden = hide;
      if (!hide) shown++;
    });
    const empty = document.getElementById("kb-empty");
    if (empty) empty.hidden = shown > 0;
  }

  window.addEventListener("popstate", function () {
    navigate(location.pathname + location.search, false);
  });

  initRoot();
  maybeShowOnboard();
})();
