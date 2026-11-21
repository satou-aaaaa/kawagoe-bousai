#!/usr/bin/env python3
# print.html を作る：決まった場所ごとに、近い避難場所を「文字そのまま」入れた QR コードと、同じ文を印刷する紙。
# QR の中身はリンクではなく文章なので、読み取ればインターネットが無くても文字が出る。
#   使い方: pip install qrcode==8.2 && python3 tools/build-print.py
# 近さの計算は src/app.js と同じ（qa/run.mjs が画面の答えと紙の答えが同じかを見る）。
import json, math, re, html
from pathlib import Path
import qrcode
R = Path(__file__).resolve().parent.parent
APP_URL = "https://satou-aaaaa.github.io/kawagoe-bousai/"

def js_value(path, name):
    s = (R / path).read_text(encoding="utf-8")
    m = re.search(r"window\." + name + r" = (.*?);\n", s, re.S)
    return json.loads(m.group(1))

PLACES = js_value("data/places.js", "PLACES")
META = js_value("data/places.js", "PLACES_META")
spots_src = (R / "src/i18n.js").read_text(encoding="utf-8")
SPOTS = []
for m in re.finditer(r'\{ id: "(\w+)", lat: ([\d.]+), lon: ([\d.]+), name: \{ ja: "([^"]+)", easy: "[^"]+", en: "([^"]+)"', spots_src):
    SPOTS.append(dict(id=m[1], lat=float(m[2]), lon=float(m[3]), ja=m[4], en=m[5]))
assert len(SPOTS) >= 5, SPOTS

def geo(a, b):
    r = math.pi / 180
    p1, p2 = a["lat"] * r, b["lat"] * r
    dp, dl = (b["lat"] - a["lat"]) * r, (b["lon"] - a["lon"]) * r
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    d = 2 * 6371000 * math.asin(math.sqrt(h))
    y = math.sin(dl) * math.cos(p2); x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return d, (math.degrees(math.atan2(y, x)) + 360) % 360

DJA = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
DEN = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
def dist(m): return f"{round(m / 10) * 10}m" if m < 1000 else f"{m / 1000:.1f}km"
def near(s, flood, n=3):
    ok = [p for p in PLACES if (("flood" in p["h"] or "inland" in p["h"]) if flood else "quake" in p["h"])]
    rows = sorted(((geo(s, p), p) for p in ok), key=lambda x: x[0][0])[:n]
    return [(p, d, b) for (d, b), p in rows]

def text(s):
    L = [f"川越 避難ガイド｜{s['ja']}", f"Kawagoe Evacuation Guide | {s['en']}", "【地震 Earthquake】"]
    for i, (p, d, b) in enumerate(near(s, False), 1):
        k = round(b / 45) % 8
        L.append(f"{i} {p['n']} {DJA[k]}{dist(d)} / {DEN[k]} {dist(d)}")
    L.append("【大雨・洪水 Heavy rain/Flood】")
    for i, (p, d, b) in enumerate(near(s, True), 1):
        k = round(b / 45) % 8
        up = f" {p['f']}階以上/{p['f']}F+" if p.get("f") else ""
        L.append(f"{i} {p['n']}{up} {DJA[k]}{dist(d)} / {DEN[k]} {dist(d)}")
    L += ["119 火事・救急 Fire/Ambulance", "110 警察 Police", "171 災害用伝言 Disaster message",
          "無料Wi-Fi 00000JAPAN (災害時 in disasters)",
          "最新は川越市で確認 Check latest with Kawagoe City",
          f"国土地理院データ GSI data {META['gsi']}", APP_URL]
    return "\n".join(L)

def svg(data):
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4)
    q.add_data(data.encode("utf-8"), optimize=0); q.make(fit=True)
    m = q.get_matrix(); n = len(m); d = []
    for y, row in enumerate(m):   # 横に続く黒を1本の長方形にして小さくする
        x = 0
        while x < n:
            if row[x]:
                x0 = x
                while x < n and row[x]: x += 1
                d.append(f"M{x0} {y}h{x - x0}v1h-{x - x0}z")
            else: x += 1
    return q.version, f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" shape-rendering="crispEdges" role="img" aria-label="QR"><rect width="{n}" height="{n}" fill="#fff"/><path fill="#000" d="{"".join(d)}"/></svg>'

cards = []
for s in SPOTS:
    tx = text(s)
    v, code = svg(tx)
    cards.append(f'<section class="card" data-spot="{s["id"]}"><h2>{html.escape(s["ja"])} / {html.escape(s["en"])}</h2>'
                 f'<div class="qr" data-version="{v}">{code}</div><pre class="tx">{html.escape(tx)}</pre></section>')
_, appqr = svg(APP_URL)
page = f"""<!doctype html>
<!-- 自動で作るファイル（tools/build-print.py）。手で直さない -->
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>川越 避難ガイド 印刷用QR</title>
<style>
:root{{--bg:#fff;--fg:#111;--mut:#555;--line:#ccc}}
@media (prefers-color-scheme:dark){{:root:not([data-print]){{--bg:#121212;--fg:#eee;--mut:#bbb;--line:#444}}}}
body{{margin:0 auto;max-width:900px;padding:16px;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,"Hiragino Sans","Noto Sans JP",sans-serif}}
h1{{font-size:1.3rem}}p{{color:var(--mut)}}
.card{{border:2px solid var(--line);border-radius:10px;padding:12px;margin:16px 0;break-inside:avoid;page-break-inside:avoid;display:grid;grid-template-columns:minmax(0,260px) 1fr;gap:12px;align-items:start}}
.card h2{{grid-column:1/-1;margin:0;font-size:1.1rem}}
.qr svg{{width:100%;height:auto;background:#fff}}
.tx{{white-space:pre-wrap;word-break:break-all;margin:0;font:13px/1.45 system-ui,"Hiragino Sans","Noto Sans JP",sans-serif}}
.app{{display:flex;gap:12px;align-items:center}}.app svg{{width:120px;height:auto;background:#fff}}
@media (max-width:560px){{.card{{grid-template-columns:1fr}}}}
@media print{{body{{max-width:none}}.noprint{{display:none}}}}
</style></head><body>
<h1>川越 避難ガイド 印刷用QR / Printable QR codes</h1>
<p>QRの中身は文章そのものです。読み取ると、インターネットが無くても文字が出ます（機種によって出方が違います）。お店や駅に貼る場合は、持ち主・管理者の許可を取ってください。</p>
<p>The QR codes contain the text itself, so it shows even without internet.</p>
<p class="noprint"><a href="./">← アプリに戻る / Back to the app</a></p>
{''.join(cards)}
<section class="card"><h2>アプリ（電波があるときに一度開くと保存されます） / The app</h2><div class="app">{appqr}<span>{APP_URL}</span></div></section>
<p>出典：国土地理院「指定緊急避難場所・指定避難所データ」（{META['gsi']} 更新分）・川越市「指定避難所・指定緊急避難場所一覧」（{META['city']} 更新）。避難場所は災害の種類ごとに指定されています。最新の状況は川越市で確認してください。</p>
</body></html>
"""
(R / "print.html").write_text(page, encoding="utf-8")
print("print.html", len(page.encode()), "bytes; QR versions:", [re.search(r'data-version="(\d+)"', c)[1] for c in cards])
