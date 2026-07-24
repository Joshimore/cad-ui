/* CAD UI — link graph: vanilla SVG force-directed layout, no external libs.
   Fetches /api/graph, lays out with a small Fruchterman-Reingold simulation,
   renders to SVG, and wires drag / zoom / pan / hover / filters. */
(function () {
  "use strict";
  const SVGNS = "http://www.w3.org/2000/svg";

  /* node type -> colour class + which filter layer it belongs to */
  const TYPE_LAYER = {
    agent: "agents", skill: "agents",
    card: "knowledge", report: "knowledge", protocol: "knowledge", doc: "knowledge",
    track: "projects",
    script: "code", config: "code",
  };
  const LAYERS = [
    { key: "agents", label: "Агенты" },
    { key: "knowledge", label: "Знания" },
    { key: "projects", label: "Проекты" },
    { key: "code", label: "Код" },
  ];
  const layerOf = (t) => TYPE_LAYER[t] || "knowledge";

  const svg = document.getElementById("graph-canvas");
  const stage = svg.parentElement;
  const tip = document.getElementById("graph-tip");
  const statsEl = document.getElementById("graph-stats");
  const emptyEl = document.getElementById("graph-empty");
  const layersEl = document.getElementById("graph-layers");
  const subsEl = document.getElementById("graph-subs");
  const legendEl = document.getElementById("graph-legend");
  const isoBox = document.getElementById("show-isolated");

  let nodes = [], edges = [], byId = new Map();
  let view = { x: 0, y: 0, w: 1000, h: 700 };   // SVG viewBox (world coords)
  const active = { layers: new Set(), subs: new Set() };
  let hovered = null, dragNode = null, alpha = 0, raf = 0, data_truncated = false;

  fetch("/api/graph").then((r) => r.json()).then(init).catch(() => {
    statsEl.textContent = "не удалось загрузить граф";
  });

  function init(data) {
    data_truncated = !!data.truncated;
    nodes = data.nodes || [];
    edges = (data.edges || []).map((e) => ({
      kind: e.kind, source: e.source, target: e.target,
    }));
    byId = new Map(nodes.map((n) => [n.id, n]));
    /* keep only edges whose both ends exist as nodes */
    edges = edges.filter((e) => byId.has(e.source) && byId.has(e.target));

    /* deterministic spiral seed so layout is stable across reloads */
    const R = 26 * Math.sqrt(nodes.length || 1);
    nodes.forEach((n, i) => {
      const a = i * 2.399963, r = R * Math.sqrt(i + 1) / Math.sqrt(nodes.length || 1) + 8;
      n.x = Math.cos(a) * r; n.y = Math.sin(a) * r;
      n.vx = 0; n.vy = 0; n.pin = false;
      n.rad = 5 + Math.min(9, (n.degree || 0) * 1.4);
      n.neighbors = new Set();
    });
    edges.forEach((e) => {
      byId.get(e.source).neighbors.add(e.target);
      byId.get(e.target).neighbors.add(e.source);
    });

    LAYERS.forEach((l) => active.layers.add(l.key));
    [...new Set(nodes.map((n) => n.subsystem))].sort().forEach((s) => active.subs.add(s));

    buildControls(data);
    buildScene();
    layout(300);
    applyFilters();
    render();
    fit();
  }

  /* ---------- controls: layer toggles, subsystem chips, legend ---------- */
  function buildControls(data) {
    const counts = {};
    nodes.forEach((n) => { const k = layerOf(n.type); counts[k] = (counts[k] || 0) + 1; });
    layersEl.innerHTML = "";
    LAYERS.forEach((l) => {
      if (!counts[l.key]) return;
      const b = chip(l.label + " " + counts[l.key], "layer-" + l.key, true);
      b.onclick = () => { toggle(active.layers, l.key, b); applyFilters(); };
      layersEl.appendChild(b);
    });

    subsEl.innerHTML = "";
    [...active.subs].forEach((s) => {
      const b = chip(s, "sub", true);
      b.onclick = () => { toggle(active.subs, s, b); applyFilters(); };
      subsEl.appendChild(b);
    });

    const types = data.types || {};
    legendEl.innerHTML = "";
    Object.keys(types).sort((a, b) => types[b] - types[a]).forEach((t) => {
      const item = document.createElement("span");
      item.className = "glegend-item";
      item.innerHTML = '<span class="glegend-dot t-' + t + '"></span>' + t + " · " + types[t];
      legendEl.appendChild(item);
    });

    isoBox.checked = false;
    isoBox.onchange = applyFilters;
    document.getElementById("graph-refit").onclick = fit;
  }

  function chip(text, cls, on) {
    const b = document.createElement("button");
    b.className = "gchip " + cls + (on ? " on" : "");
    b.textContent = text;
    return b;
  }
  function toggle(set, key, el) {
    if (set.has(key)) { set.delete(key); el.classList.remove("on"); }
    else { set.add(key); el.classList.add("on"); }
  }

  /* ---------- build SVG scene ---------- */
  let gEdges, gNodes;
  function buildScene() {
    svg.innerHTML = "";
    gEdges = document.createElementNS(SVGNS, "g");
    gNodes = document.createElementNS(SVGNS, "g");
    svg.appendChild(gEdges);
    svg.appendChild(gNodes);

    edges.forEach((e) => {
      const ln = document.createElementNS(SVGNS, "line");
      ln.setAttribute("class", "gedge k-" + e.kind);
      e.el = ln;
      gEdges.appendChild(ln);
    });

    nodes.forEach((n) => {
      const g = document.createElementNS(SVGNS, "g");
      g.setAttribute("class", "gnode t-" + n.type);
      const c = document.createElementNS(SVGNS, "circle");
      c.setAttribute("r", n.rad);
      const label = document.createElementNS(SVGNS, "text");
      label.setAttribute("class", "gnode-label");
      label.setAttribute("x", n.rad + 3);
      label.setAttribute("y", 3);
      label.textContent = n.label;
      g.appendChild(c);
      g.appendChild(label);
      n.el = g;
      g.addEventListener("pointerenter", () => setHover(n));
      g.addEventListener("pointerleave", () => setHover(null));
      g.addEventListener("pointerdown", (ev) => startDrag(ev, n));
      g.addEventListener("click", (ev) => {
        if (n._moved) { n._moved = false; return; }  // ignore click after a drag
        ev.preventDefault();
        location.href = "/view?path=" + encodeURIComponent(n.id);
      });
      gNodes.appendChild(g);
    });
  }

  /* ---------- filtering (layer + subsystem + isolated) ---------- */
  function visibleByFacet(n) {
    return active.layers.has(layerOf(n.type)) && active.subs.has(n.subsystem);
  }
  function applyFilters() {
    const showIso = isoBox.checked;
    const facet = new Map();
    nodes.forEach((n) => facet.set(n.id, visibleByFacet(n)));
    /* an edge shows only if both ends pass the facet filter */
    const vdeg = new Map(nodes.map((n) => [n.id, 0]));
    edges.forEach((e) => {
      const ok = facet.get(e.source) && facet.get(e.target);
      e._vis = ok;
      if (ok) { vdeg.set(e.source, vdeg.get(e.source) + 1); vdeg.set(e.target, vdeg.get(e.target) + 1); }
    });
    let shownN = 0, shownE = 0;
    nodes.forEach((n) => {
      const vis = facet.get(n.id) && (showIso || vdeg.get(n.id) > 0);
      n._vis = vis;
      n.el.classList.toggle("hidden", !vis);
      if (vis) shownN++;
    });
    edges.forEach((e) => {
      const vis = e._vis && byId.get(e.source)._vis && byId.get(e.target)._vis;
      e.el.classList.toggle("hidden", !vis);
      if (vis) shownE++;
    });
    statsEl.textContent = shownN + " узлов · " + shownE + " связей"
      + (data_truncated ? " · показаны первые " + nodes.length : "");
    emptyEl.hidden = shownN > 0;
  }

  /* ---------- Fruchterman-Reingold simulation ---------- */
  let simK = 1, simSide = 1;
  function computeScale() {
    const n = nodes.length || 1;
    simSide = 40 * Math.sqrt(n) + 240;
    simK = simSide / Math.sqrt(n);
  }
  function step(temp) {
    const n = nodes.length;
    for (let i = 0; i < n; i++) { nodes[i].fx = 0; nodes[i].fy = 0; }
    /* repulsion between all pairs */
    for (let i = 0; i < n; i++) {
      const a = nodes[i];
      for (let j = i + 1; j < n; j++) {
        const b = nodes[j];
        let dx = a.x - b.x, dy = a.y - b.y;
        let d2 = dx * dx + dy * dy;
        if (d2 < 0.01) { dx = (i - j) * 0.1 + 0.05; dy = 0.05; d2 = dx * dx + dy * dy; }
        const d = Math.sqrt(d2);
        const f = (simK * simK) / d;
        const ux = dx / d, uy = dy / d;
        a.fx += ux * f; a.fy += uy * f;
        b.fx -= ux * f; b.fy -= uy * f;
      }
    }
    /* attraction along edges */
    for (const e of edges) {
      const a = byId.get(e.source), b = byId.get(e.target);
      let dx = a.x - b.x, dy = a.y - b.y;
      const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
      const f = (d * d) / simK;
      const ux = dx / d, uy = dy / d;
      a.fx -= ux * f; a.fy -= uy * f;
      b.fx += ux * f; b.fy += uy * f;
    }
    /* integrate with temperature cap + weak centering */
    for (let i = 0; i < n; i++) {
      const p = nodes[i];
      if (p === dragNode || p.pin) continue;
      p.fx += -p.x * 0.012; p.fy += -p.y * 0.012;
      const disp = Math.sqrt(p.fx * p.fx + p.fy * p.fy) || 1;
      const lim = Math.min(disp, temp);
      p.x += (p.fx / disp) * lim;
      p.y += (p.fy / disp) * lim;
    }
  }
  /* Initial layout runs synchronously so the graph is positioned on first paint
     even when requestAnimationFrame is throttled (hidden/background tab). */
  function layout(iters) {
    computeScale();
    for (let s = 0; s < iters; s++) step(simSide * 0.10 * (1 - s / iters) + 0.5);
  }
  function heat(a) {
    computeScale();
    alpha = a;
    if (!raf) raf = requestAnimationFrame(tick);
  }
  function tick() {
    raf = 0;
    if (!nodes.length) return;
    step(alpha * simSide * 0.10);
    render();
    alpha *= 0.94;
    if (alpha > 0.03) raf = requestAnimationFrame(tick);
  }

  function render() {
    for (const e of edges) {
      if (e.el.classList.contains("hidden")) continue;
      const a = byId.get(e.source), b = byId.get(e.target);
      e.el.setAttribute("x1", a.x); e.el.setAttribute("y1", a.y);
      e.el.setAttribute("x2", b.x); e.el.setAttribute("y2", b.y);
    }
    for (const nd of nodes) {
      if (!nd._vis) continue;
      nd.el.setAttribute("transform", "translate(" + nd.x + "," + nd.y + ")");
    }
  }

  /* ---------- hover highlight ---------- */
  function setHover(n) {
    hovered = n;
    if (!n) { svg.classList.remove("has-hover"); tip.hidden = true; return; }
    svg.classList.add("has-hover");
    nodes.forEach((m) => {
      const near = m === n || n.neighbors.has(m.id);
      m.el.classList.toggle("near", near);
      m.el.classList.toggle("dim", !near);
    });
    edges.forEach((e) => {
      const inc = e.source === n.id || e.target === n.id;
      e.el.classList.toggle("near", inc);
      e.el.classList.toggle("dim", !inc);
    });
    tip.hidden = false;
    tip.innerHTML = "<b>" + esc(n.label) + "</b><span>" + n.type
      + (n.subsystem ? " · " + esc(n.subsystem) : "") + "</span><span class='gtip-path'>"
      + esc(n.id) + "</span>";
  }
  stage.addEventListener("pointermove", (ev) => {
    if (tip.hidden) return;
    const r = stage.getBoundingClientRect();
    tip.style.left = (ev.clientX - r.left + 14) + "px";
    tip.style.top = (ev.clientY - r.top + 14) + "px";
  });

  /* ---------- drag node ---------- */
  function clientToWorld(ev) {
    const r = svg.getBoundingClientRect();
    return {
      x: view.x + ((ev.clientX - r.left) / r.width) * view.w,
      y: view.y + ((ev.clientY - r.top) / r.height) * view.h,
    };
  }
  function startDrag(ev, n) {
    ev.stopPropagation();
    dragNode = n; n._moved = false;
    n.el.setPointerCapture(ev.pointerId);
    const move = (e) => {
      const w = clientToWorld(e);
      n.x = w.x; n.y = w.y; n.pin = true; n._moved = true;
      render(); heat(0.35);
    };
    const up = (e) => {
      n.el.releasePointerCapture(ev.pointerId);
      n.el.removeEventListener("pointermove", move);
      n.el.removeEventListener("pointerup", up);
      dragNode = null;
    };
    n.el.addEventListener("pointermove", move);
    n.el.addEventListener("pointerup", up);
  }

  /* ---------- pan + zoom on the background ---------- */
  svg.addEventListener("pointerdown", (ev) => {
    if (ev.target.closest(".gnode")) return;
    const start = { x: ev.clientX, y: ev.clientY, vx: view.x, vy: view.y };
    const r = svg.getBoundingClientRect();
    const move = (e) => {
      view.x = start.vx - (e.clientX - start.x) / r.width * view.w;
      view.y = start.vy - (e.clientY - start.y) / r.height * view.h;
      applyView();
    };
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  });
  svg.addEventListener("wheel", (ev) => {
    ev.preventDefault();
    const w = clientToWorld(ev);
    const f = ev.deltaY > 0 ? 1.1 : 0.9;
    view.x = w.x - (w.x - view.x) * f;
    view.y = w.y - (w.y - view.y) * f;
    view.w *= f; view.h *= f;
    applyView();
  }, { passive: false });

  function applyView() {
    svg.setAttribute("viewBox", view.x + " " + view.y + " " + view.w + " " + view.h);
  }
  function fit() {
    const vis = nodes.filter((n) => n._vis);
    const pts = vis.length ? vis : nodes;
    if (!pts.length) { applyView(); return; }
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    pts.forEach((n) => {
      minX = Math.min(minX, n.x); minY = Math.min(minY, n.y);
      maxX = Math.max(maxX, n.x); maxY = Math.max(maxY, n.y);
    });
    const pad = 60;
    const w = Math.max(maxX - minX, 200) + pad * 2;
    const h = Math.max(maxY - minY, 200) + pad * 2;
    const cw = stage.clientWidth, ch = stage.clientHeight;
    const ar = (cw > 0 && ch > 0) ? cw / ch : 1.4;   // never Infinity/NaN
    let vw = w, vh = h;
    if (vw / vh < ar) vw = vh * ar; else vh = vw / ar;
    view = { x: (minX + maxX) / 2 - vw / 2, y: (minY + maxY) / 2 - vh / 2, w: vw, h: vh };
    applyView();
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }
})();
