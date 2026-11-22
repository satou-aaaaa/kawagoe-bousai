// 川越 避難ガイドの動き。外へは何も送らない（現在地もこの端末の中だけで使う）。
(function () {
  "use strict";
  // 人に渡すファイルの中身。描く前の形を、動き出したときに写しておく（電波もサーバーも無しで渡せるように）
  const SOURCE = "<!doctype html>\n" + document.documentElement.outerHTML;
  const FILE_MODE = location.protocol === "file:";
  const $ = (s, r = document) => r.querySelector(s);
  const LS = (k, v) => { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } };
  const codes = LANGS.map((l) => l[0]);
  const guess = () => { const n = (navigator.language || "ja").toLowerCase(); return n.startsWith("ja") ? "ja" : n.startsWith("zh") ? "zh" : n.startsWith("ko") ? "ko" : "en"; };
  const urlLang = new URLSearchParams(location.search).get("lang");
  const st = {
    lang: codes.includes(urlLang) ? urlLang : codes.includes(LS("kb-lang")) ? LS("kb-lang") : guess(),
    hz: "quake",
    here: null, // { lat, lon, label }
    heading: null,
    tab: "near",
    route: null, // 道順を出している一覧の番号
  };
  const t = (k) => (T[st.lang] && T[st.lang][k] !== undefined ? T[st.lang][k] : T.ja[k]);
  const fmt = (s, o) => String(s).replace(/\{(\w+)\}/g, (_, k) => o[k]);
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // 距離（m）と方角（度。北=0、時計回り）
  function geo(a, b) {
    const R = 6371000, r = Math.PI / 180;
    const p1 = a.lat * r, p2 = b.lat * r, dp = (b.lat - a.lat) * r, dl = (b.lon - a.lon) * r;
    const h = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
    const d = 2 * R * Math.asin(Math.sqrt(h));
    const y = Math.sin(dl) * Math.cos(p2), x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl);
    return { d, b: ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360 };
  }
  const DIRS = ["dirN", "dirNE", "dirE", "dirSE", "dirS", "dirSW", "dirW", "dirNW"];
  const dirName = (b) => t(DIRS[Math.round(b / 45) % 8]);
  const dist = (m) => (m < 1000 ? Math.round(m / 10) * 10 + t("meters") : (m / 1000).toFixed(1) + t("km"));
  // 災害の種類 → 使える場所
  function fits(p) {
    if (st.hz === "flood") return p.h.includes("flood") || p.h.includes("inland");
    return p.h.includes("quake"); // 地震。火事は指定が無いので地震用の広い場所を出す
  }
  function nearest(n) {
    if (!st.here) return [];
    return PLACES.filter(fits).map((p) => Object.assign({ p }, geo(st.here, p))).sort((a, b) => a.d - b.d).slice(0, n);
  }
  window.KB = { geo, nearest: (here, hz, n) => { st.here = here; st.hz = hz; return nearest(n); } }; // 検査用

  function arrow(b) {
    const rot = st.heading == null ? b : b - st.heading;
    return `<svg class="arrow" data-b="${b.toFixed(0)}" viewBox="0 0 24 24" aria-hidden="true" style="transform:rotate(${rot.toFixed(0)}deg)"><path d="M12 2 19 20 12 16 5 20Z"/></svg>`;
  }
  function miniMap(list) {
    if (!list.length) return "";
    const max = Math.max(500, ...list.map((x) => x.d)) * 1.15, S = 150;
    const pt = (x) => { const r = (x.d / max) * (S - 14), a = (x.b * Math.PI) / 180; return [S + r * Math.sin(a), S - r * Math.cos(a)]; };
    const ring = (m) => (m < max ? `<circle cx="${S}" cy="${S}" r="${((m / max) * (S - 14)).toFixed(1)}" class="ring"/><text x="${S + 3}" y="${(S - (m / max) * (S - 14) + 12).toFixed(1)}" class="rl">${dist(m)}</text>` : "");
    const dots = list.map((x, i) => { const [cx, cy] = pt(x); return `<circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="11" class="dot"/><text x="${cx.toFixed(1)}" y="${(cy + 4).toFixed(1)}" class="dn">${i + 1}</text>`; }).join("");
    return `<figure class="mini"><svg viewBox="0 0 300 300" role="img" aria-label="${esc(t("mapNote"))}">${ring(500)}${ring(1000)}${ring(2000)}<text x="${S}" y="14" class="north">N ▲</text><circle cx="${S}" cy="${S}" r="7" class="me"/>${dots}</svg><figcaption>${esc(t("mapNote"))}</figcaption></figure>`;
  }
  function nearHTML() {
    const hzBtn = (k, label) => `<button type="button" class="chip" data-hz="${k}" aria-pressed="${st.hz === k}">${esc(t(label))}</button>`;
    const spots = SPOTS.map((s) => `<button type="button" class="chip" data-spot="${s.id}" aria-pressed="${!!(st.here && st.here.id === s.id)}">${esc(s.name[st.lang] || s.name.en)}</button>`).join("");
    let body = "";
    if (st.here) {
      const list = nearest(5);
      body += `<p class="hint" id="gps-msg">${esc(st.here.id ? st.here.label : t("gpsOk"))}</p>`;
      if (st.hz === "fire") body += `<p class="warn">${esc(t("noFireSite"))}</p>`;
      if (st.hz === "flood") body += `<p class="warn">${esc(t("floodNote"))}</p>`;
      body += `<ol class="places">` + list.map((x, i) => {
        const p = x.p, tags = [];
        if (st.hz === "flood" && p.f) tags.push(`<span class="tag up">${esc(fmt(t("floorUp"), { n: p.f }))}</span>`);
        if (p.s) tags.push(`<span class="tag">${esc(t("shelterMark"))}</span>`);
        const map = `https://www.google.com/maps/search/?api=1&query=${p.lat},${p.lon}`;
        return `<li><span class="no">${i + 1}</span>${arrow(x.b)}<div class="pl"><b>${esc(p.n)}</b><span class="dd">${esc(dirName(x.b))} ${esc(dist(x.d))}</span><span class="ad">${esc(p.a)}</span>${tags.join("")}${p.note ? `<span class="nt">${esc(p.note)}</span>` : ""}<span class="rw" data-rw="${i}"></span><button type="button" class="sub rbtn" data-route="${i}" aria-pressed="${st.route === i}">🚶 ${esc(t("routeBtn"))}</button><a href="${map}" target="_blank" rel="noopener">${esc(t("openMap"))}</a></div></li>`;
      }).join("") + `</ol>`;
      body += `<section id="route" aria-live="polite"></section>`;
      body += miniMap(list);
      body += `<p><button type="button" class="sub" id="compass">${esc(t("compass"))}</button> <span class="hint" id="compass-msg"></span></p>`;
    }
    return `<h2>${esc(t("whatHappen"))}</h2><div class="row">${hzBtn("quake", "hzQuake")}${hzBtn("flood", "hzFlood")}${hzBtn("fire", "hzFire")}</div>
      <h2>${esc(t("whereAreYou"))}</h2><button type="button" class="main" id="gps">📍 ${esc(t("useGps"))}</button><p class="hint" id="gps-state" aria-live="polite"></p>
      <p class="hint">${esc(t("orPick"))}</p><div class="row">${spots}</div><div id="result">${body}</div>`;
  }
  const steps = (k) => `<h2>${esc(t(k + "T"))}</h2><ol class="steps">${t(k).map((s) => `<li>${esc(s)}</li>`).join("")}</ol>`;
  const doHTML = () => steps("doQuake") + steps("doFlood") + steps("doFire");
  function talkHTML() {
    const ja = T.ja.talk, mine = t("talk");
    return `<p class="hint">${esc(t("talkHint"))}</p><ul class="talk">` + ja.map((row, i) => `<li><span class="big">${esc(row[0])}</span>${st.lang === "ja" ? "" : `<span class="tr" lang="${st.lang === "easy" ? "ja" : st.lang}">${esc(mine[i][0])}</span>`}</li>`).join("") + `</ul>`;
  }
  function infoHTML() {
    const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
    return `<h2>${esc(t("callT"))}</h2><ul class="calls"><li><a href="tel:119">${esc(t("call119"))}</a></li><li><a href="tel:110">${esc(t("call110"))}</a></li><li><a href="tel:171">${esc(t("call171"))}</a></li></ul>
      <h2>${esc(t("wifiT"))}</h2><p>${esc(t("wifi"))}</p>
      <h2>${esc(t("keepT"))}</h2><p>${esc(ios ? t("keepIos") : t("keepAndroid"))}</p><p class="hint">${esc(ios ? t("keepAndroid") : t("keepIos"))}</p>
      <h2>${esc(t("shareT"))}</h2><p><button type="button" class="sub" data-tab="share">${esc(t("give"))}</button></p><p><a href="${FILE_MODE ? APP_URL : "./"}print.html${st.lang === "ja" ? "" : "?lang=" + st.lang}">${esc(t("qrSheet"))}</a></p>
      <h2>${esc(t("linksT"))}</h2><ul class="links">
        <li><a href="https://www.city.kawagoe.saitama.jp/kurashi/anshin/1001545/1001581/1001583.html" target="_blank" rel="noopener">${esc(t("lnCity"))}</a></li>
        <li><a href="https://www.city.kawagoe.saitama.jp/shisei/shisetsu/hinanjyo/1013361.html" target="_blank" rel="noopener">${esc(t("lnHinan"))}</a></li>
        <li><a href="https://www.jma.go.jp/bosai/" target="_blank" rel="noopener">${esc(t("lnJma"))}</a></li>
        <li><a href="https://www.jnto.go.jp/safety-tips/" target="_blank" rel="noopener">${esc(t("lnSafety"))}</a></li></ul>
      <h2>${esc(t("aboutT"))}</h2><p>${esc(t("about1"))}</p><p>${esc(t("about2"))}</p><p>${esc(t("about3"))}</p>${st.lang === "ja" ? "" : `<p class="warn">${esc(t("about4"))}</p>`}
      <p class="hint">${esc(fmt(t("dataDate"), PLACES_META))}</p>`;
  }

  function shareHTML() {
    const n = Number(LS("kb-shared") || 0);
    return `<p>${esc(t("shareLead"))}</p>
      <h2>${esc(t("shareOnlineT"))}</h2><p>${esc(t("shareOnline"))}</p>
      <div class="qrbox" id="qr">${APP_QR[st.lang] || APP_QR.ja}</div><p class="url">${esc(APP_URL + (st.lang === "ja" ? "" : "?lang=" + st.lang))}</p>
      <h2>${esc(t("shareOfflineT"))}</h2><p>${esc(t("shareOffline"))}</p>
      <button type="button" class="main" id="givefile">📲 ${esc(t("shareFileBtn"))}</button><p class="hint" id="give-msg" aria-live="polite"></p>
      ${n ? `<p class="count" id="give-count">${esc(fmt(t("shareCount"), { n }))}</p>` : ""}
      <h2>${esc(t("recvT"))}</h2><div class="recv"><p>${esc(t("recvIos"))}</p><p>${esc(t("recvAndroid"))}</p><p class="hint">${esc(t("recvNoJs"))}</p></div>`;
  }

  function render() {
    document.documentElement.lang = st.lang === "easy" ? "ja" : st.lang === "zh" ? "zh-Hans" : st.lang;
    document.title = t("title");
    $("#title").textContent = t("title");
    $("#sub").textContent = t("sub");
    $("#lang-label").textContent = t("lang");
    $("#lang").value = st.lang;
    for (const b of document.querySelectorAll("nav [data-tab]")) { b.textContent = t("tab" + b.dataset.tab[0].toUpperCase() + b.dataset.tab.slice(1)); b.setAttribute("aria-selected", String(b.dataset.tab === st.tab)); }
    const v = $("#view");
    $("#give").textContent = t("give");
    $("#give").hidden = st.tab === "share";
    v.innerHTML = st.tab === "near" ? nearHTML() : st.tab === "do" ? doHTML() : st.tab === "talk" ? talkHTML() : st.tab === "share" ? shareHTML() : infoHTML();
    v.setAttribute("aria-labelledby", "tab-" + st.tab);
    status();
    if (st.tab === "near" && st.here) fillRoutes();
    if (st.tab === "share") ROUTE.load().catch(() => {}); // 渡すファイルに道のデータも入れるので、先に読んでおく（押してから待たせない）
  }

  // 道順（src/route.js）。道のデータは大きいので、場所が決まってから読む
  let rc = { key: "", res: null };
  const walk = (m) => fmt(t("routeWalk"), { d: dist(m), min: Math.max(1, Math.ceil(m / 60)) }); // 災害のときは分速60mで見る
  function fillRoutes() {
    const list = nearest(5), key = [st.here.lat, st.here.lon, st.hz].join();
    const box = $("#route");
    if (st.route != null && box && !ROUTE.ready()) box.innerHTML = `<p class="hint">${esc(t("routeLoading"))}</p>`;
    ROUTE.load().then(() => {
      if (rc.key !== key) rc = { key, res: ROUTE.routes(st.here, list.map((x) => x.p), st.hz === "fire" ? "fire" : st.hz) };
      if (!$("#route")) return;
      rc.res.forEach((r, i) => { const el = document.querySelector(`[data-rw="${i}"]`); if (el && r) el.textContent = walk(r.len); });
      if (st.route != null) { $("#route").innerHTML = routeHTML(list[st.route], rc.res[st.route]); if (follow.last) onPos(follow.last[0], follow.last[1]); }
    }, () => {
      const b = $("#route");
      if (b && st.route != null) b.innerHTML = `<p class="warn">${esc(t("routeNone"))}</p>`;
    });
  }
  // 歩きながら見る：現在地を道順の地図に出し、残りの距離と、道からはずれたことを知らせる（位置は端末の中だけ）
  const follow = { id: null, last: null };
  function stopFollow() { if (follow.id != null) navigator.geolocation.clearWatch(follow.id); follow.id = null; follow.last = null; }
  function onPos(lat, lon) {
    follow.last = [lat, lon];
    const r = rc.res && st.route != null ? rc.res[st.route] : null, msg = $("#follow-msg");
    if (!r || !msg) return;
    ROUTE.showMe(lat, lon);
    const g = ROUTE.progress(r, lat, lon);
    msg.textContent = g.left < 30 ? t("followArrive") : g.off > 60 ? fmt(t("followOff"), { d: dist(g.off) }) : fmt(t("followLeft"), { d: dist(g.left), min: Math.max(1, Math.ceil(g.left / 60)) });
    msg.className = g.off > 60 && g.left >= 30 ? "warn" : "dd";
  }
  function startFollow() {
    if (!navigator.geolocation) { $("#follow-msg").textContent = t("gpsFail"); return; }
    follow.id = navigator.geolocation.watchPosition((p) => onPos(p.coords.latitude, p.coords.longitude), () => { const m = $("#follow-msg"); if (m) m.textContent = t("gpsFail"); }, { enableHighAccuracy: true, maximumAge: 5000, timeout: 30000 });
    const b = $("#follow"); b.textContent = "📍 " + t("followStop"); b.setAttribute("aria-pressed", "true");
    $("#follow-msg").textContent = t("gpsWait");
  }
  window.KB.pos = onPos; // 検査用（GPS の動きをまねる）
  function routeHTML(x, r) {
    if (!x || !r) return `<p class="warn">${esc(t("routeNone"))}</p>`;
    const hz = st.hz === "fire" ? "fire" : st.hz, w = ROUTE.W[hz];
    const avoid = ROUTE.BITS.filter(([b]) => (w[b] || 1) >= 2), still = avoid.filter(([b]) => r.by[b] > 0);
    const name = (k) => t(k);
    const turn = (s) => s.turn === "end" ? fmt(t("stepEnd"), { d: dist(s.d) }) : fmt(t("stepTurn"), { d: dist(s.d), turn: t(s.turn === "R" ? "turnR" : "turnL") });
    let h = `<h2>${esc(fmt(t("routeT"), { name: x.p.n }))}</h2><p class="dd">${esc(walk(r.len))}</p>`;
    if (r.startGap > 300) h += `<p class="warn">${esc(fmt(t("routeFar"), { d: dist(r.startGap) }))}</p>`;
    h += `<figure class="rmap">${ROUTE.svg(r, hz, esc(t("routeMapNote")))}<figcaption>${esc(t("routeMapNote"))}</figcaption></figure>`;
    h += `<p class="hint">${esc(fmt(t("routeAvoid"), { list: avoid.map(([, k]) => name(k)).join("・") }))}</p>`;
    if (still.length) h += `<p class="warn" id="route-still">${esc(fmt(t("routeStill"), { list: still.map(([b, k]) => name(k) + " " + dist(r.by[b])).join("・") }))}</p>`;
    h += `<p><button type="button" class="main" id="follow" aria-pressed="${follow.id != null}">📍 ${esc(t(follow.id != null ? "followStop" : "follow"))}</button></p><p class="dd" id="follow-msg" aria-live="polite"></p>`;
    h += `<ol class="rsteps">${ROUTE.steps(r).map((s) => `<li>${esc(turn(s))}</li>`).join("")}</ol>`;
    h += `<p class="warn">${esc(t("routeNote"))}</p><p class="hint">${esc(t("routeSrc"))}</p>`;
    return h;
  }
  function status() {
    const el = $("#status");
    const saved = LS("kb-saved") === "1";
    if (FILE_MODE) { el.className = "status ok"; el.textContent = t("fileMode"); return; }
    el.className = "status " + (navigator.onLine ? (saved ? "ok" : "warn") : "off");
    el.textContent = navigator.onLine ? (saved ? t("saved") : t("notSaved")) : t("offline");
  }

  function useGps() {
    const s = $("#gps-state");
    if (!navigator.geolocation) { s.textContent = t("gpsFail"); return; }
    s.textContent = t("gpsWait");
    navigator.geolocation.getCurrentPosition(
      (pos) => { st.here = { lat: pos.coords.latitude, lon: pos.coords.longitude }; st.route = null; render(); },
      () => { $("#gps-state").textContent = t("gpsFail"); },
      { enableHighAccuracy: true, timeout: 20000, maximumAge: 120000 },
    );
  }
  function compass() {
    const msg = $("#compass-msg");
    const on = (e) => {
      const h = typeof e.webkitCompassHeading === "number" ? e.webkitCompassHeading : e.absolute && e.alpha != null ? 360 - e.alpha : null;
      if (h == null) return;
      st.heading = h;
      for (const a of document.querySelectorAll(".places .arrow")) a.style.transform = `rotate(${(Number(a.dataset.b) - h).toFixed(0)}deg)`;
    };
    const start = () => { window.addEventListener("deviceorientationabsolute", on); window.addEventListener("deviceorientation", on); msg.textContent = t("compassOn"); };
    if (typeof DeviceOrientationEvent === "undefined") { msg.textContent = t("compassNo"); return; }
    if (typeof DeviceOrientationEvent.requestPermission === "function") DeviceOrientationEvent.requestPermission().then((r) => (r === "granted" ? start() : (msg.textContent = t("compassNo"))), () => (msg.textContent = t("compassNo")));
    else start();
  }
  // ファイルで渡す。共有の画面（AirDrop・クイック共有）を開き、使えない端末ではファイルを保存する
  const ROADS_MARK = 'id="roads' + '-data"'; // 本文にこの文字をそのまま書かない（app.js 自身が入った写しで見まちがえないように）
  async function fileSource() {
    if (SOURCE.includes("<script " + ROADS_MARK)) return SOURCE;
    try { await ROUTE.load(); } catch (e) { return SOURCE; }
    const data = "<script " + ROADS_MARK + ">window.ROADS = " + JSON.stringify(window.ROADS) + ";</" + "script>\n";
    const at = SOURCE.lastIndexOf("</body>");
    return SOURCE.slice(0, at) + data + SOURCE.slice(at);
  }
  async function giveFile() {
    const msg = $("#give-msg");
    const file = new File([await fileSource()], "kawagoe-bousai.html", { type: "text/html" });
    const counted = () => { LS("kb-shared", String(Number(LS("kb-shared") || 0) + 1)); };
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      try { await navigator.share({ files: [file], title: t("title") }); counted(); render(); return; }
      catch (e) { if (e && e.name === "AbortError") return; }
    }
    const a = document.createElement("a");
    a.href = URL.createObjectURL(file);
    a.download = file.name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 10000);
    counted();
    msg.textContent = t("shareFileSaved");
  }
  window.KB.source = () => SOURCE; // 検査用
  window.KB.fileSource = fileSource;

  document.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    if (b.dataset.tab) { st.tab = b.dataset.tab; render(); $("#view").focus({ preventScroll: true }); window.scrollTo(0, 0); return; }
    if (b.dataset.hz) { st.hz = b.dataset.hz; render(); return; }
    if (b.id === "follow") { if (follow.id != null) { stopFollow(); render(); } else startFollow(); return; }
    if (b.dataset.route) { const i = Number(b.dataset.route); st.route = st.route === i ? null : i; if (st.route == null) stopFollow(); render(); const r = $("#route"); if (r && st.route != null) r.scrollIntoView({ block: "start" }); return; }
    if (b.dataset.spot) { st.route = null; stopFollow(); const s = SPOTS.find((x) => x.id === b.dataset.spot); st.here = { lat: s.lat, lon: s.lon, id: s.id, label: s.name[st.lang] || s.name.en }; render(); return; }
    if (b.id === "gps") return useGps();
    if (b.id === "compass") return compass();
    if (b.id === "give") { st.tab = "share"; render(); $("#view").focus({ preventScroll: true }); window.scrollTo(0, 0); return; }
    if (b.id === "givefile") return giveFile();
  });
  $("#lang").addEventListener("change", (e) => { st.lang = e.target.value; LS("kb-lang", st.lang); if (st.here && st.here.id) { const s = SPOTS.find((x) => x.id === st.here.id); st.here.label = s.name[st.lang] || s.name.en; } render(); });
  window.addEventListener("online", status);
  window.addEventListener("offline", status);
  $("#lang").innerHTML = LANGS.map(([c, n]) => `<option value="${c}">${n}</option>`).join("");
  render();
  if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
    navigator.serviceWorker.register("./sw.js").then(() => navigator.serviceWorker.ready).then(() => { LS("kb-saved", "1"); status(); }).catch(() => {});
  }
})();
