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
      fetch("/api/favorite?path=" + encodeURIComponent(fav.dataset.path), { method: "POST" })
        .then((r) => r.json())
        .then((data) => fav.classList.toggle("on", data.favorite));
      return;
    }

    /* ---------- Claude Launch ---------- */
    const cl = e.target.closest("#claude-launch");
    if (cl) {
      cl.disabled = true;
      fetch("/api/claude-launch", { method: "POST" })
        .then(async (r) => {
          if (r.ok) {
            flashBtn(cl, "ok", ">_ запущен");
          } else {
            const data = await r.json().catch(() => ({}));
            flashBtn(cl, "err", "ошибка");
            if (data.detail) alert(data.detail);
          }
        })
        .catch(() => flashBtn(cl, "err", "ошибка"))
        .finally(() => { cl.disabled = false; });
    }
  });

  function flashBtn(btn, cls, text) {
    const orig = btn.textContent;
    btn.classList.add(cls);
    btn.textContent = text;
    setTimeout(() => {
      btn.classList.remove(cls);
      btn.textContent = orig;
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
    const curBar = document.querySelector(".topbar-title");
    const newBar = doc.querySelector(".topbar-title");
    if (curBar && newBar) curBar.replaceWith(newBar);
    const curNav = document.querySelector(".nav-rail");
    const newNav = doc.querySelector(".nav-rail");
    if (curNav && newNav) {
      document.querySelectorAll(".nav-item").forEach((item, i) => {
        const fresh = newNav.querySelectorAll(".nav-item")[i];
        if (fresh) item.classList.toggle("active", fresh.classList.contains("active"));
      });
    }
  }

  window.addEventListener("popstate", function () {
    navigate(location.pathname + location.search, false);
  });

  initRoot();
})();
