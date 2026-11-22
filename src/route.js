// 道順：危ない所をなるべく避けて歩く道を、この端末の中だけで探す（data/roads.js を使う。外へは何も送らない）。
// 道の印は tools/build-roads.py と同じビット。重みは「道の長さに掛ける数」で、大きいほど避ける。
(function () {
  "use strict";
  const BR = 1, TU = 2, ST = 4, NA = 8, RV = 16, F1 = 32, F2 = 64, CO = 128, SL = 256;
  const BITS = [[BR, "hBridge"], [TU, "hTunnel"], [ST, "hStairs"], [NA, "hNarrow"], [RV, "hRiver"], [F1, "hFlood"], [F2, "hDeep"], [CO, "hCollapse"], [SL, "hSlope"]];
  // 地震：細い道（ブロック塀・倒れた家）・崖・橋・地下道。大雨：浸水・家屋倒壊・川のそば・地下道（冠水）・橋。火事：細い道（燃え広がる・ふさがる）
  const W = {
    quake: { [BR]: 1.5, [TU]: 2, [ST]: 1.5, [NA]: 2.5, [RV]: 1.5, [SL]: 20 },
    flood: { [BR]: 4, [TU]: 30, [ST]: 1.2, [RV]: 5, [F1]: 4, [F2]: 15, [CO]: 30, [SL]: 20 },
    fire: { [BR]: 1.2, [TU]: 3, [ST]: 1.5, [NA]: 4, [SL]: 5 },
    none: {}, // 検査用：危なさを見ない、ただの近道
  };
  const Q = 1e5, M_LAT = 111320, M_LON = 111320 * Math.cos((35.9 * Math.PI) / 180), CELL = 500; // 近い点を探す升目（1e-5 度で 500 = 約 500m）
  let G = null, loading = null, proj = null;

  function build(R) {
    const nn = R.n.length / 2, lon = new Float64Array(nn), lat = new Float64Array(nn);
    let x = 0, y = 0;
    for (let i = 0; i < nn; i++) { x += R.n[2 * i]; y += R.n[2 * i + 1]; lon[i] = x; lat[i] = y; }
    const ne = R.e.length, ea = new Int32Array(ne), eb = new Int32Array(ne), el = new Float64Array(ne), ef = new Int32Array(ne), deg = new Int32Array(nn + 1);
    R.e.forEach((r, i) => { ea[i] = r[0]; eb[i] = r[1]; el[i] = r[2]; ef[i] = r[3]; deg[r[0] + 1]++; deg[r[1] + 1]++; });
    for (let i = 0; i < nn; i++) deg[i + 1] += deg[i];
    const adj = new Int32Array(2 * ne), fill = deg.slice(0, nn);
    for (let i = 0; i < ne; i++) { adj[fill[ea[i]]++] = i; adj[fill[eb[i]]++] = i; }
    const grid = new Map();
    for (let i = 0; i < nn; i++) { const k = Math.floor(lon[i] / CELL) + "," + Math.floor(lat[i] / CELL); (grid.get(k) || grid.set(k, []).get(k)).push(i); }
    return { R, nn, lon, lat, ea, eb, el, ef, deg, adj, grid };
  }
  function load() {
    if (G) return Promise.resolve(G);
    if (window.ROADS) return Promise.resolve((G = build(window.ROADS)));
    if (loading) return loading;
    loading = new Promise((ok, ng) => {
      if (location.protocol === "file:") { loading = null; return ng(new Error("no roads")); }
      const s = document.createElement("script");
      s.src = "./data/roads.js";
      s.onload = () => (window.ROADS ? ok((G = build(window.ROADS))) : ng(new Error("no roads")));
      s.onerror = () => { loading = null; s.remove(); ng(new Error("load")); };
      document.head.appendChild(s);
    });
    return loading;
  }
  const meters = (lat1, lon1, lat2, lon2) => Math.hypot((lon1 - lon2) * M_LON, (lat1 - lat2) * M_LAT);
  function snap(p) {
    const X = p.lon * Q, Y = p.lat * Q, cx = Math.floor(X / CELL), cy = Math.floor(Y / CELL);
    let best = -1, bd = Infinity;
    for (let r = 0; r <= 3 && (best < 0 || r <= 1); r++) {
      for (let dx = -r; dx <= r; dx++) for (let dy = -r; dy <= r; dy++) {
        if (Math.max(Math.abs(dx), Math.abs(dy)) !== r) continue;
        for (const i of G.grid.get(cx + dx + "," + (cy + dy)) || []) { const d = meters(Y / Q, X / Q, G.lat[i] / Q, G.lon[i] / Q); if (d < bd) { bd = d; best = i; } }
      }
    }
    return { i: best, d: bd };
  }
  function weight(f, hz) {
    const w = W[hz] || W.quake;
    if (!Object.keys(w).length) return 1;
    let k = 1;
    for (const [b] of BITS) if (f & b && w[b]) k *= w[b];
    return Math.min(k, 200);
  }
  // 出発点から、行き先の点ぜんぶまで（重みつきの）いちばん近い道を探す
  function routes(from, targets, hz) {
    const s = snap(from), goals = targets.map(snap), want = new Set(goals.map((g) => g.i));
    const dist = new Float64Array(G.nn).fill(Infinity), prev = new Int32Array(G.nn).fill(-1), done = new Uint8Array(G.nn);
    const hk = [], hv = [];
    const push = (v, k) => { let i = hk.length; hk.push(k); hv.push(v); while (i > 0) { const p = (i - 1) >> 1; if (hk[p] <= k) break; hk[i] = hk[p]; hv[i] = hv[p]; i = p; } hk[i] = k; hv[i] = v; };
    const pop = () => { const v = hv[0], lk = hk.pop(), lv = hv.pop(); if (hk.length) { let i = 0; for (;;) { let c = 2 * i + 1; if (c >= hk.length) break; if (c + 1 < hk.length && hk[c + 1] < hk[c]) c++; if (hk[c] >= lk) break; hk[i] = hk[c]; hv[i] = hv[c]; i = c; } hk[i] = lk; hv[i] = lv; } return v; };
    dist[s.i] = 0; push(s.i, 0);
    let left = want.size;
    while (hk.length && left) {
      const u = pop();
      if (done[u]) continue;
      done[u] = 1;
      if (want.has(u)) left--;
      for (let j = G.deg[u]; j < G.deg[u + 1]; j++) {
        const e = G.adj[j], v = G.ea[e] === u ? G.eb[e] : G.ea[e], nd = dist[u] + G.el[e] * weight(G.ef[e], hz);
        if (nd < dist[v]) { dist[v] = nd; prev[v] = e; push(v, nd); }
      }
    }
    return goals.map((g, gi) => {
      if (!done[g.i]) return null;
      const edges = [];
      for (let v = g.i; v !== s.i; ) { const e = prev[v]; const a = G.ea[e] === v ? G.eb[e] : G.ea[e]; edges.push([e, a]); v = a; }
      edges.reverse();
      const pts = [[G.lat[s.i] / Q, G.lon[s.i] / Q]], seg = [];
      let len = 0;
      const by = {};
      for (const [e, a] of edges) {
        const row = G.R.e[e], fwd = G.ea[e] === a;
        const mids = [];
        let x = G.lon[G.ea[e]], y = G.lat[G.ea[e]];
        for (let k = 4; k < row.length; k += 2) { x += row[k]; y += row[k + 1]; mids.push([y / Q, x / Q]); }
        if (!fwd) mids.reverse();
        const b = fwd ? G.eb[e] : G.ea[e];
        const part = mids.concat([[G.lat[b] / Q, G.lon[b] / Q]]);
        seg.push({ from: pts.length - 1, to: pts.length - 1 + part.length, f: G.ef[e], len: G.el[e] });
        pts.push(...part);
        len += G.el[e];
        for (const [bit] of BITS) if (G.ef[e] & bit) by[bit] = (by[bit] || 0) + G.el[e];
      }
      return { from: [from.lat, from.lon], to: [targets[gi].lat, targets[gi].lon], len: len + s.d + g.d, startGap: s.d, endGap: g.d, pts, seg, by, cost: dist[g.i] };
    });
  }
  // 曲がる所（35度より大きく向きが変わる所）で区切った案内
  function steps(r) {
    const brg = (a, b) => (Math.atan2((b[1] - a[1]) * M_LON, (b[0] - a[0]) * M_LAT) * 180) / Math.PI;
    const out = [];
    let run = r.startGap;
    for (let i = 1; i < r.pts.length; i++) {
      run += meters(r.pts[i - 1][0], r.pts[i - 1][1], r.pts[i][0], r.pts[i][1]);
      if (i === r.pts.length - 1) break;
      let d = brg(r.pts[i], r.pts[i + 1]) - brg(r.pts[i - 1], r.pts[i]);
      d = ((d + 540) % 360) - 180;
      if (Math.abs(d) > 35 && run >= 15) { out.push({ d: run, turn: d > 0 ? "R" : "L" }); run = 0; }
    }
    out.push({ d: run + r.endGap, turn: "end" });
    return out;
  }
  // 上が北の道の地図（SVG）。まわりの道は細い灰色、いまの災害で避けたい道は色つき、道順は太い線
  function svg(r, hz, label) {
    const ps = [r.from].concat(r.pts, [r.to]); // 道に出るまで・道から入口までも線でつなぐ
    let s = Infinity, n = -Infinity, w = Infinity, e = -Infinity;
    for (const [la, lo] of ps) { s = Math.min(s, la); n = Math.max(n, la); w = Math.min(w, lo); e = Math.max(e, lo); }
    const cy = (s + n) / 2, cx = (w + e) / 2;
    let hw = Math.max(((e - w) * M_LON) / 2, ((n - s) * M_LAT) / 2, 200) * 1.15; // 半分の幅（m）
    const S = 300, k = S / 2 / hw;
    proj = { cx, cy, k, S };
    const X = (lo) => (S / 2 + (lo - cx) * M_LON * k).toFixed(1), Y = (la) => (S / 2 - (la - cy) * M_LAT * k).toFixed(1);
    const bw = cx - hw / M_LON, be = cx + hw / M_LON, bs = cy - hw / M_LAT, bn = cy + hw / M_LAT, wt = W[hz] || W.quake;
    const inb = (i) => { const lo = G.lon[i] / Q, la = G.lat[i] / Q; return lo > bw && lo < be && la > bs && la < bn; };
    let bg = "", hzd = "";
    for (let i = 0; i < G.ea.length; i++) {
      if (!inb(G.ea[i]) && !inb(G.eb[i])) continue;
      const row = G.R.e[i];
      let x = G.lon[G.ea[i]], y = G.lat[G.ea[i]], d = "M" + X(x / Q) + " " + Y(y / Q);
      for (let j = 4; j < row.length; j += 2) { x += row[j]; y += row[j + 1]; d += "L" + X(x / Q) + " " + Y(y / Q); }
      d += "L" + X(G.lon[G.eb[i]] / Q) + " " + Y(G.lat[G.eb[i]] / Q);
      if (weight(G.ef[i], hz) >= 2.5) hzd += d; else bg += d;
    }
    const line = ps.map((p, i) => (i ? "L" : "M") + X(p[1]) + " " + Y(p[0])).join("");
    const a = ps[0], z = ps[ps.length - 1];
    return `<svg viewBox="0 0 ${S} ${S}" role="img" aria-label="${label}"><rect width="${S}" height="${S}" class="rbg"/><path d="${bg}" class="rd"/><path d="${hzd}" class="rh"/><path d="${line}" class="rt"/>` +
      `<text x="${S / 2}" y="14" class="north">N ▲</text><circle cx="${X(a[1])}" cy="${Y(a[0])}" r="7" class="me"/><rect x="${(X(z[1]) - 8).toFixed(1)}" y="${(Y(z[0]) - 8).toFixed(1)}" width="16" height="16" class="goal"/><circle id="you" r="9" cx="-99" cy="-99" class="you"/></svg>`;
  }
  // 歩いている途中：いまの場所が道順からどれだけ離れたか（off）と、着くまでの残り（left）。どちらも m
  function progress(r, lat, lon) {
    const ps = [r.from].concat(r.pts, [r.to]), P = (p) => [p[1] * M_LON, p[0] * M_LAT], me = P([lat, lon]);
    let best = { off: Infinity, i: 0, t: 0 };
    for (let i = 1; i < ps.length; i++) {
      const a = P(ps[i - 1]), b = P(ps[i]), dx = b[0] - a[0], dy = b[1] - a[1], L2 = dx * dx + dy * dy;
      const t = L2 ? Math.max(0, Math.min(1, ((me[0] - a[0]) * dx + (me[1] - a[1]) * dy) / L2)) : 0;
      const off = Math.hypot(a[0] + t * dx - me[0], a[1] + t * dy - me[1]);
      if (off < best.off) best = { off, i, t };
    }
    let left = 0;
    for (let i = best.i; i < ps.length; i++) left += meters(ps[i - 1][0], ps[i - 1][1], ps[i][0], ps[i][1]) * (i === best.i ? 1 - best.t : 1);
    return { off: best.off, left };
  }
  // 地図の上に「いまここ」を動かす（いちばん新しく描いた地図に）
  function showMe(lat, lon) {
    const el = document.getElementById("you");
    if (!el || !proj) return;
    el.setAttribute("cx", (proj.S / 2 + (lon - proj.cx) * M_LON * proj.k).toFixed(1));
    el.setAttribute("cy", (proj.S / 2 - (lat - proj.cy) * M_LAT * proj.k).toFixed(1));
  }
  window.ROUTE = { progress, showMe, load, routes, steps, svg, weight, BITS, W, ready: () => !!G };
})();
