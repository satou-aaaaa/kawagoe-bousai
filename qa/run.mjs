// 川越 避難ガイドの検査。データ（座標が川越の中・災害の種類）・言葉のそろい・index.html が src と同じか・
// 画面（5言語・場所を選ぶ・現在地・洪水の階・火事の案内）・掲示用ポスターと画面の答えが同じか・電波なしで開けるか・スマホ幅・PWA の返事の仕方を見る。
// 使い方: node qa/run.mjs   失敗があれば終了コード 1。結果は qa-report/report.md。
import { chromium } from "playwright";
import { mkdirSync, writeFileSync, readFileSync, existsSync } from "node:fs";
import { createServer } from "node:http";
import { fileURLToPath } from "node:url";
import vm from "node:vm";
import path from "node:path";
import { checkSwStall } from "./sw-check.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const results = [];
const check = (name, ok, detail = "") => results.push({ name, ok: !!ok, detail: String(detail).slice(0, 400) });
const read = (f) => readFileSync(path.join(root, f), "utf8");

// ---- 1. ブラウザを使わない検査 ----
const ctx = { window: {} };
vm.runInNewContext(read("data/places.js") + read("src/i18n.js"), ctx);
const { PLACES, PLACES_META, T, LANGS, SPOTS } = ctx.window;
check("データ：避難場所が100件以上ある", PLACES.length >= 100, PLACES.length);
check("データ：座標が川越市のあたり（北緯35.85〜35.98・東経139.38〜139.56）", PLACES.every((p) => p.lat > 35.85 && p.lat < 35.98 && p.lon > 139.38 && p.lon < 139.56), PLACES.filter((p) => !(p.lat > 35.85 && p.lat < 35.98)).map((p) => p.n));
check("データ：どの場所にも災害の種類がある", PLACES.every((p) => p.h.length > 0));
check("データ：地震で使える場所・洪水で使える場所がそれぞれある", PLACES.some((p) => p.h.includes("quake")) && PLACES.some((p) => p.h.includes("flood")));
check("データ：階の注記（2階以上・3階以上）が付いた場所がある", PLACES.some((p) => p.f === 2) && PLACES.some((p) => p.f === 3));
check("データ：出典の日付がある", /^\d{4}-\d\d-\d\d$/.test(PLACES_META.gsi) && /^\d{4}-\d\d-\d\d$/.test(PLACES_META.city));
check("決まった場所：5つ以上・全部の言語の名前がある", SPOTS.length >= 5 && SPOTS.every((s) => LANGS.every(([c]) => s.name[c])));
{
  const keys = Object.keys(T.ja), miss = [];
  for (const [c] of LANGS) {
    for (const k of keys) {
      const a = T.ja[k], b = T[c][k];
      if (b === undefined || b === "") miss.push(`${c}.${k}`);
      else if (Array.isArray(a) && (!Array.isArray(b) || a.length !== b.length)) miss.push(`${c}.${k}（数）`);
      else if (typeof a === "string" && (a.match(/\{\w+\}/g) || []).join() !== (String(b).match(/\{\w+\}/g) || []).join()) miss.push(`${c}.${k}（{}）`);
    }
    for (const k of Object.keys(T[c])) if (!(k in T.ja)) miss.push(`${c}.${k}（余り）`);
  }
  check("言葉：5言語で同じキー・同じ数・同じ差し込み", miss.length === 0, miss.join(" "));
}
{
  // index.html が src と data から作ったものか（tools/build.py。QR は Python で作るので、中身が入っているかを見る）
  const idx = read("index.html");
  const stale = ["src/style.css", "data/places.js", "src/i18n.js", "src/app.js"].filter((f) => !idx.includes(read(f).replace(/\n+$/, "")));
  check("index.html が src/ と同じ（直したら python3 tools/build.py）", stale.length === 0, stale.join(" "));
  const kb = Buffer.byteLength(read("index.html")) / 1024;
  check("index.html が軽い（混んだ回線でも開けるよう 150KB 未満）", kb < 150, kb.toFixed(1) + "KB");
  check("index.html は外のサイトから何も読み込まない（電波なしで全部そろう）", !/<(script|link|img)[^>]+(src|href)="https?:/i.test(read("index.html")));
  check("index.html の最初の行が <!doctype html>（標準モード）", read("index.html").startsWith("<!doctype html>"));
}
{
  const sw = read("sw.js");
  const shell = JSON.parse(/const SHELL = (\[[^\]]*\])/.exec(sw)[1].replace(/'/g, '"'));
  check("PWA：保存するファイルが全部ある", shell.filter((f) => f !== "./").every((f) => existsSync(path.join(root, f))), shell.join(" "));
  const st = await checkSwStall(sw);
  check("PWA：通信が止まっても保存した画面に切り替わる（shared-workflows template/qa/sw-check.mjs）", st.ok, JSON.stringify(st));
}

// ---- 2. ブラウザで ----
const types = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".json": "application/json", ".webmanifest": "application/manifest+json", ".png": "image/png", ".css": "text/css" };
const server = createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (p.endsWith("/")) p += "index.html";
  const f = path.join(root, p);
  if (!f.startsWith(root) || !existsSync(f)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "content-type": types[path.extname(f)] || "application/octet-stream" });
  res.end(readFileSync(f));
}).listen(0);
const base = `http://127.0.0.1:${server.address().port}/`;
const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
try {
  const context = await browser.newContext({ viewport: { width: 360, height: 740 }, geolocation: { latitude: 35.923595, longitude: 139.483627 }, permissions: ["geolocation"], locale: "ja-JP" });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  await page.goto(base);
  await page.waitForFunction(() => document.querySelector("#tab-near").textContent.length > 0);
  check("開く：日本語で、5つのタブがある", (await page.locator("[role=tab]").count()) === 5 && (await page.title()) === "川越 避難ガイド");

  // 場所を選ぶ → 近い順に5つ・紙の QR の文と同じ答え
  await page.click("[data-spot=tokinokane]");
  const names = await page.locator(".places li b").allTextContents();
  check("場所を選ぶ：近い避難場所が5つ出る・方角と距離がある", names.length === 5 && (await page.locator(".places .dd").first().textContent()).match(/\d+m|km/), names.join("・"));
  const print = read("print.html");
  const card = /<section class="poster" data-spot="tokinokane">(.*?)<\/section>/s.exec(print)[1];
  const paper = (cls) => [...(new RegExp(`<ol class="${cls}">(.*?)</ol>`, "s").exec(card)[1]).matchAll(/<b class="nm">([^<]+)<\/b>/g)].map((m) => m[1]);
  const paperQuake = paper("lq");
  check("掲示用ポスター：地震の近い順が画面と同じ（一番街）", paperQuake.join() === names.slice(0, 3).join(), paperQuake.join() + " / " + names.slice(0, 3).join());
  check("小さな地図：番号の点が5つ・北の印がある", (await page.locator(".mini .dot").count()) === 5 && (await page.locator(".mini .north").count()) === 1);

  // 洪水：洪水で使える場所だけ・階の注記
  await page.click("[data-hz=flood]");
  const fnames = await page.locator(".places li b").allTextContents();
  const floodOk = fnames.every((n) => PLACES.find((p) => p.n === n).h.some((h) => h === "flood" || h === "inland"));
  check("大雨・洪水：洪水か内水で指定された場所だけ出る・川に近づかない注意がある", floodOk && (await page.locator(".warn").count()) >= 1, fnames.join("・"));
  const paperFlood = paper("lf");
  check("掲示用ポスター：洪水の近い順が画面と同じ（一番街）", paperFlood.join() === fnames.slice(0, 3).join(), paperFlood.join() + " / " + fnames.slice(0, 3).join());
  {
    await page.click("[data-spot=kawagoe]");
    const withFloor = PLACES.filter((p) => p.f).map((p) => p.n);
    const shown = await page.locator(".places li").evaluateAll((els) => els.map((e) => [e.querySelector("b").textContent, !!e.querySelector(".tag.up")]));
    check("大雨・洪水：2階以上・3階以上の場所には階の注記が出る", shown.every(([n, tag]) => tag === withFloor.includes(n)), JSON.stringify(shown));
  }
  await page.click("[data-hz=fire]");
  check("火事：指定が無いことと119番の案内が出る", /119/.test(await page.locator(".warn").first().textContent()));

  // 現在地（GPS）
  await page.click("[data-hz=quake]");
  await page.click("#gps");
  await page.waitForFunction(() => /現在地から近い順/.test((document.querySelector("#gps-msg") || {}).textContent || ""));
  const gpsNames = await page.locator(".places li b").allTextContents();
  check("現在地：時の鐘の位置で、場所を選んだときと同じ答え", gpsNames.join() === names.join(), gpsNames.join("・"));

  // 5言語
  for (const [c] of LANGS) {
    for (const tab of ["near", "do", "talk", "info", "share"]) {
      await page.selectOption("#lang", c);
      await page.click(`#tab-${tab}`);
      const txt = await page.locator("body").innerText();
      if (/undefined|NaN|\{n\}|\{gsi\}|null/.test(txt)) { check(`言葉：${c} の ${tab} に変な文字がない`, false, txt.slice(0, 200)); }
    }
  }
  check("言葉：5言語 × 5タブで undefined などが出ない", !results.some((r) => r.name.startsWith("言葉：") && r.name.includes("変な文字") && !r.ok));
  await page.selectOption("#lang", "en");
  await page.click("#tab-near");
  check("言葉：英語に切り替えると見出しも英語・html の lang も en", (await page.locator("#title").textContent()) === "Kawagoe Evacuation Guide" && (await page.evaluate(() => document.documentElement.lang)) === "en");
  await page.click("#tab-info");
  check("英語：AI が訳した注意が出る", /translated by AI/.test(await page.locator("main").innerText()));
  await page.reload();
  await page.waitForFunction(() => document.querySelector("#tab-near").textContent.length > 0);
  check("言葉：選んだ言語を覚えている", (await page.locator("#title").textContent()) === "Kawagoe Evacuation Guide");
  await page.selectOption("#lang", "ja");

  // 指さし会話：日本語と選んだ言語が並ぶ
  await page.selectOption("#lang", "zh");
  await page.click("#tab-talk");
  check("指さし会話：日本語と中国語が並ぶ", (await page.locator(".talk .big").first().textContent()) === "避難所はどこですか？" && (await page.locator(".talk .tr").first().textContent()) === "避难所在哪里？");
  await page.selectOption("#lang", "ja");

  // スマホ幅：横にはみ出さない
  for (const tab of ["near", "do", "talk", "info", "share"]) {
    await page.click(`#tab-${tab}`);
    if (tab === "near") await page.click("[data-spot=tokinokane]");
    const over = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    if (over > 0) check(`スマホ幅 360px：${tab} が横にはみ出さない`, false, over + "px");
  }
  check("スマホ幅 360px：どのタブも横にはみ出さない", !results.some((r) => r.name.startsWith("スマホ幅 360px：") && !r.ok));
  {
    const small = await page.locator("button:visible").evaluateAll((els) => els.filter((e) => Math.round(e.getBoundingClientRect().height) < 44).map((e) => e.textContent));
    check("押す所が44px以上（手袋や慌てた指でも押せる）", small.length === 0, small.join("・"));
  }

  // みんなに配る：上のボタン → 配る画面・QR・ファイルで渡す
  await page.selectOption("#lang", "ja");
  await page.click("#tab-near");
  await page.click("#give");
  check("配る：上の大きなボタンで配る画面が開く", (await page.locator("#tab-share").getAttribute("aria-selected")) === "true" && (await page.locator("#qr svg").count()) === 1);
  await page.selectOption("#lang", "en");
  check("配る：QR とアドレスが選んだ言語のもの", /\?lang=en$/.test(await page.locator(".url").textContent()));
  await page.selectOption("#lang", "ja");
  const [dl] = await Promise.all([page.waitForEvent("download"), page.click("#givefile")]);
  const filePath = path.join(root, "qa-report", "kawagoe-bousai.html");
  mkdirSync(path.join(root, "qa-report"), { recursive: true });
  await dl.saveAs(filePath);
  check("配る：共有の画面が無い端末ではファイルを保存し、そう知らせる", dl.suggestedFilename() === "kawagoe-bousai.html" && /ファイルを保存しました/.test(await page.locator("#give-msg").textContent()));
  await page.click("#tab-near"); await page.click("#tab-share");
  check("配る：配った回数を数える", /1 回/.test(await page.locator("#give-count").textContent()));
  {
    const fp = await context.newPage();
    const ferr = [];
    fp.on("pageerror", (e) => ferr.push(e.message));
    await fp.goto("file://" + filePath);
    await fp.waitForFunction(() => document.querySelector("#tab-near").textContent.length > 0);
    await fp.click("[data-spot=kawagoe]");
    check("受け取ったファイル：開くとアプリが動き、避難場所が出る", (await fp.locator(".places li").count()) === 5 && ferr.length === 0, ferr.join(" | "));
    check("受け取ったファイル：ファイルから開いていることを知らせる", /ファイルから開いています/.test(await fp.locator("#status").textContent()));
    await fp.click("#tab-share");
    const [dl2] = await Promise.all([fp.waitForEvent("download"), fp.click("#givefile")]);
    const again = path.join(root, "qa-report", "again.html");
    await dl2.saveAs(again);
    check("受け取ったファイル：そこからまた別の人へ渡せる（同じ中身）", readFileSync(again, "utf8").length > 50000 && readFileSync(again, "utf8").includes("window.PLACES"));
    await fp.close();
    const nj = await browser.newContext({ javaScriptEnabled: false });
    const np = await nj.newPage();
    await np.goto("file://" + filePath);
    const t = await np.locator(".nojs").innerText();
    check("スクリプトが動かない開き方：避難場所の一覧と119・171が読める", /119/.test(t) && /171/.test(t) && (t.match(/地震 Earthquake/g) || []).length >= PLACES.length, t.slice(0, 120));
    await nj.close();
  }

  // 電波なし：保存されたあと、オフラインで開き直しても全部出る
  await page.waitForFunction(() => navigator.serviceWorker && navigator.serviceWorker.controller !== null || localStorage.getItem("kb-saved") === "1", null, { timeout: 15000 });
  await page.reload();
  await page.waitForFunction(() => navigator.serviceWorker.controller !== null, null, { timeout: 15000 });
  check("保存：開いたあと「電波がなくても開けます」と出る", /電波がなくても開けます/.test(await page.locator("#status").textContent()));
  await context.setOffline(true);
  await page.reload();
  await page.waitForFunction(() => document.querySelector("#tab-near").textContent.length > 0, null, { timeout: 15000 });
  await page.click("#tab-near");
  await page.click("[data-spot=honkawagoe]");
  check("電波なし：開き直しても避難場所が出る", (await page.locator(".places li").count()) === 5);
  check("電波なし：電波がないことを知らせる", /電波がありません/.test(await page.locator("#status").textContent()));
  await page.click("#gps");
  await page.waitForFunction(() => /現在地から近い順/.test((document.querySelector("#gps-msg") || {}).textContent || ""));
  check("電波なし：現在地も使える", (await page.locator(".places li").count()) === 5);
  const pp = await context.newPage();
  await pp.goto(base + "print.html");
  check("電波なし：掲示用ポスターのページも開ける・場所ごとに地図とアプリの QR がある", (await pp.locator(".poster").count()) === SPOTS.length && (await pp.locator(".poster .map svg").count()) === SPOTS.length && (await pp.locator(".poster .qr svg").count()) === SPOTS.length);
  await context.setOffline(false);
  check("エラーが出ない", errors.length === 0, errors.join(" | "));
} finally {
  await browser.close();
  server.close();
}

const ng = results.filter((r) => !r.ok);
mkdirSync(path.join(root, "qa-report"), { recursive: true });
writeFileSync(path.join(root, "qa-report/report.md"), `# QA ${ng.length ? "❌" : "✅"} ${results.length - ng.length}/${results.length}\n\n` + results.map((r) => `- ${r.ok ? "✅" : "❌"} ${r.name}${r.detail && !r.ok ? `\n  - ${r.detail}` : ""}`).join("\n") + "\n");
for (const r of results) console.log(`${r.ok ? "✅" : "❌"} ${r.name}${!r.ok && r.detail ? " — " + r.detail : ""}`);
console.log(`\n${results.length - ng.length}/${results.length}`);
process.exit(ng.length ? 1 : 0);
