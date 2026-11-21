// 川越 避難ガイドの動き。外へは何も送らない（現在地もこの端末の中だけで使う）。
(function () {
  "use strict";
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
        return `<li><span class="no">${i + 1}</span>${arrow(x.b)}<div class="pl"><b>${esc(p.n)}</b><span class="dd">${esc(dirName(x.b))} ${esc(dist(x.d))}</span><span class="ad">${esc(p.a)}</span>${tags.join("")}${p.note ? `<span class="nt">${esc(p.note)}</span>` : ""}<a href="${map}" target="_blank" rel="noopener">${esc(t("openMap"))}</a></div></li>`;
      }).join("") + `</ol>`;
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
      <h2>${esc(t("shareT"))}</h2><p class="row"><button type="button" class="sub" id="share">${esc(t("share"))}</button><button type="button" class="sub" id="savefile">${esc(t("saveFile"))}</button></p><p><a href="./print.html">${esc(t("qrSheet"))}</a></p>
      <h2>${esc(t("linksT"))}</h2><ul class="links">
        <li><a href="https://www.city.kawagoe.saitama.jp/kurashi/anshin/1001545/1001581/1001583.html" target="_blank" rel="noopener">${esc(t("lnCity"))}</a></li>
        <li><a href="https://www.city.kawagoe.saitama.jp/shisei/shisetsu/hinanjyo/1013361.html" target="_blank" rel="noopener">${esc(t("lnHinan"))}</a></li>
        <li><a href="https://www.jma.go.jp/bosai/" target="_blank" rel="noopener">${esc(t("lnJma"))}</a></li>
        <li><a href="https://www.jnto.go.jp/safety-tips/" target="_blank" rel="noopener">${esc(t("lnSafety"))}</a></li></ul>
      <h2>${esc(t("aboutT"))}</h2><p>${esc(t("about1"))}</p><p>${esc(t("about2"))}</p><p>${esc(t("about3"))}</p>${st.lang === "ja" ? "" : `<p class="warn">${esc(t("about4"))}</p>`}
      <p class="hint">${esc(fmt(t("dataDate"), PLACES_META))}</p>`;
  }

  function render() {
    document.documentElement.lang = st.lang === "easy" ? "ja" : st.lang === "zh" ? "zh-Hans" : st.lang;
    document.title = t("title");
    $("#title").textContent = t("title");
    $("#sub").textContent = t("sub");
    $("#lang-label").textContent = t("lang");
    $("#lang").value = st.lang;
    for (const b of document.querySelectorAll("[data-tab]")) { b.textContent = t("tab" + b.dataset.tab[0].toUpperCase() + b.dataset.tab.slice(1)); b.setAttribute("aria-selected", String(b.dataset.tab === st.tab)); }
    const v = $("#view");
    v.innerHTML = st.tab === "near" ? nearHTML() : st.tab === "do" ? doHTML() : st.tab === "talk" ? talkHTML() : infoHTML();
    v.setAttribute("aria-labelledby", "tab-" + st.tab);
    status();
  }
  function status() {
    const el = $("#status");
    const saved = LS("kb-saved") === "1";
    el.className = "status " + (navigator.onLine ? (saved ? "ok" : "warn") : "off");
    el.textContent = navigator.onLine ? (saved ? t("saved") : t("notSaved")) : t("offline");
  }

  function useGps() {
    const s = $("#gps-state");
    if (!navigator.geolocation) { s.textContent = t("gpsFail"); return; }
    s.textContent = t("gpsWait");
    navigator.geolocation.getCurrentPosition(
      (pos) => { st.here = { lat: pos.coords.latitude, lon: pos.coords.longitude }; render(); },
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
  async function saveFile() {
    try {
      const html = await (await fetch("./index.html")).text();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([html], { type: "text/html" }));
      a.download = "kawagoe-bousai.html";
      document.body.appendChild(a); a.click(); a.remove();
    } catch (e) { /* 保存できない端末では何もしない */ }
  }

  document.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    if (b.dataset.tab) { st.tab = b.dataset.tab; render(); $("#view").focus(); return; }
    if (b.dataset.hz) { st.hz = b.dataset.hz; render(); return; }
    if (b.dataset.spot) { const s = SPOTS.find((x) => x.id === b.dataset.spot); st.here = { lat: s.lat, lon: s.lon, id: s.id, label: s.name[st.lang] || s.name.en }; render(); return; }
    if (b.id === "gps") return useGps();
    if (b.id === "compass") return compass();
    if (b.id === "share") { if (navigator.share) navigator.share({ title: t("title"), url: location.href.split("?")[0] }).catch(() => {}); return; }
    if (b.id === "savefile") return saveFile();
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
