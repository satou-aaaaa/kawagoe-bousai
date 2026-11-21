#!/usr/bin/env python3
# print.html を作る：決まった場所ごとの掲示用ポスター（A4）。上が北の簡単な地図・近い避難場所（地震・洪水）・電話・アプリの QR（URL）。
# 紙なので電気も電波も要らない（2026-11-21 satou さん「文字の QR は微妙」を受けて、文字だけQRから替えた）。
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


DZH = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
DKO = ["북", "북동", "동", "남동", "남", "남서", "서", "북서"]

def mapsvg(rows):
    # 上が北の簡単な地図。中心が「いまここ」、番号の点が避難場所（地震=赤丸の数字・洪水=青四角の英字）
    S = 170
    mx = max(500, max(d for _, _, d, _, _ in rows)) * 1.15
    qn = {n for kind, _, _, _, n in rows if kind == "q"}
    def pt(d, b):
        r = d / mx * (S - 18); a = math.radians(b)
        return S + r * math.sin(a), S - r * math.cos(a)
    o = [f'<svg viewBox="0 0 {2 * S} {2 * S}" role="img" aria-label="地図 map">', f'<rect width="{2 * S}" height="{2 * S}" fill="#fff"/>']
    for m in (250, 500, 1000, 2000):
        if m < mx:
            r = m / mx * (S - 18)
            o.append(f'<circle cx="{S}" cy="{S}" r="{r:.1f}" fill="none" stroke="#999" stroke-dasharray="4 4"/><text x="{S + 4}" y="{S - r + 12:.1f}" font-size="11" fill="#555">{dist(m)}</text>')
    o.append(f'<text x="{S}" y="16" font-size="15" font-weight="bold" text-anchor="middle" fill="#b3261e">▲ N 北</text>')
    o.append(f'<circle cx="{S}" cy="{S}" r="9" fill="#111"/><text x="{S}" y="{S + 26}" font-size="13" font-weight="bold" text-anchor="middle">いまここ / You</text>')
    for kind, i, d, b, n in rows:
        x, y = pt(d, b)
        if kind == "f" and n in qn: x, y = x + 18, y - 18   # 地震と同じ場所は、四角を右上にずらして両方見えるように
        if kind == "q":
            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="#b3261e"/><text x="{x:.1f}" y="{y + 5:.1f}" font-size="14" font-weight="bold" fill="#fff" text-anchor="middle">{i}</text>')
        else:
            o.append(f'<rect x="{x - 12:.1f}" y="{y - 12:.1f}" width="24" height="24" fill="#1565c0"/><text x="{x:.1f}" y="{y + 5:.1f}" font-size="14" font-weight="bold" fill="#fff" text-anchor="middle">{chr(64 + i)}</text>')
    o.append("</svg>")
    return "".join(o)

def li(mark, p, d, b, flood):
    k = round(b / 45) % 8
    up = f'<span class="up">{p["f"]}階以上 / {p["f"]}F+</span>' if flood and p.get("f") else ""
    return (f'<li><span class="mk {"f" if flood else "q"}">{mark}</span><span class="ar" style="transform:rotate({b:.0f}deg)" aria-hidden="true">↑</span>'
            f'<span><b class="nm">{html.escape(p["n"])}</b>{up}<br><span class="dd">{DJA[k]} {dist(d)} ・ {DEN[k]} ・ {DZH[k]} ・ {DKO[k]}</span></span></li>')

def poster(s, appqr):
    q, f = near(s, False), near(s, True)
    rows = [("q", i, d, b, p["n"]) for i, (p, d, b) in enumerate(q, 1)] + [("f", i, d, b, p["n"]) for i, (p, d, b) in enumerate(f, 1)]
    ql = "".join(li(str(i), p, d, b, False) for i, (p, d, b) in enumerate(q, 1))
    fl = "".join(li(chr(64 + i), p, d, b, True) for i, (p, d, b) in enumerate(f, 1))
    return f"""<section class="poster" data-spot="{s['id']}">
<h2>避難場所 Evacuation Sites 避难场所 대피 장소</h2><p class="here">いまここ / You are here: <b>{html.escape(s['ja'])}</b> {html.escape(s['en'])}</p>
<div class="body"><div class="map">{mapsvg(rows)}<p class="cap">上が北 / North is up / 上方为北 / 위쪽이 북쪽</p></div>
<div class="lists"><h3 class="q">● 地震 Earthquake 地震 지진</h3><ol class="lq">{ql}</ol>
<h3 class="f">■ 大雨・洪水 Flood 洪水 홍수</h3><p class="note">川に近づかない。外が危ないときは近くの丈夫な建物の上の階へ。<br>Stay away from rivers. If outside is dangerous, go upstairs in a sturdy building.</p><ol class="lf">{fl}</ol></div></div>
<div class="foot"><div class="calls"><b>119</b> 火事・救急 Fire/Ambulance 火警・急救 화재・구급<br><b>110</b> 警察 Police 警察 경찰<br><b>171</b> 災害用伝言ダイヤル Disaster message dial<br>無料Wi-Fi <b>00000JAPAN</b>（大きな災害のとき / in major disasters）</div>
<div class="qr">{appqr}<span>アプリ App 应用 앱<br>電波があるうちに一度開くと保存され、電波がなくても使えます。<br>Open once while online; then it works offline.</span></div></div>
<p class="src">出典：国土地理院「指定緊急避難場所データ」（{META['gsi']} 更新分）・川越市「指定避難所・指定緊急避難場所一覧」（{META['city']} 更新）。避難場所は災害の種類ごとに指定されています。最新の状況は川越市で確認してください。距離は直線。非公式。</p>
</section>"""

_, APPQR = svg(APP_URL)
page = f"""<!doctype html>
<!-- 自動で作るファイル（tools/build-print.py）。手で直さない -->
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>川越 避難ガイド 掲示用ポスター</title>
<style>
@page{{size:A4;margin:10mm}}
body{{margin:0 auto;max-width:900px;padding:16px;background:#fff;color:#111;font:14px/1.45 system-ui,"Hiragino Sans","Noto Sans JP","Noto Sans SC","Noto Sans KR",sans-serif}}
.intro{{color:#444}}
.poster{{border:3px solid #b3261e;border-radius:12px;padding:14px;margin:18px 0;break-after:page;page-break-after:always}}
.poster h2{{margin:0;font-size:1.35rem;color:#b3261e}}.here{{margin:.2em 0 .6em;font-size:1.05rem}}
.body{{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.1fr);gap:14px}}
.map svg{{width:100%;height:auto;border:1px solid #ccc}}.cap{{text-align:center;margin:2px 0;font-size:.8rem;color:#444}}
h3{{margin:.2em 0;font-size:1.05rem}}h3.q{{color:#b3261e}}h3.f{{color:#1565c0}}
ol{{list-style:none;padding:0;margin:0 0 .6em}}li{{display:flex;gap:8px;align-items:center;margin:6px 0}}
.mk{{flex:none;width:26px;height:26px;display:grid;place-items:center;color:#fff;font-weight:bold}}.mk.q{{background:#b3261e;border-radius:50%}}.mk.f{{background:#1565c0}}
.ar{{flex:none;display:inline-block;font-size:1.6rem;font-weight:bold;width:28px;text-align:center}}
.dd{{font-size:.85rem;color:#333}}.up{{margin-left:6px;font-size:.8rem;border:1px solid #1565c0;color:#1565c0;padding:0 4px;border-radius:4px;font-weight:bold}}
.note{{font-size:.8rem;margin:.2em 0;color:#333}}
.foot{{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center;border-top:1px solid #ccc;margin-top:8px;padding-top:8px}}
.calls b{{font-size:1.2rem}}.qr{{display:flex;gap:8px;align-items:center;max-width:330px;font-size:.8rem}}.qr svg{{width:110px;height:auto;flex:none}}
.src{{font-size:.7rem;color:#555;margin:.6em 0 0}}
@media (max-width:640px){{.body,.foot{{grid-template-columns:1fr}}}}
@media print{{body{{max-width:none;padding:0}}.noprint{{display:none}}.poster{{margin:0;border-width:2px}}}}
</style></head><body>
<div class="noprint"><h1>掲示用ポスター（場所ごと・A4）</h1>
<p class="intro">紙なので、電気も電波も要りません。お店や駅に貼る場合は、持ち主・管理者の許可を取ってください。印刷はブラウザの「印刷」から（A4・1か所1枚）。</p>
<p><a href="./">← アプリに戻る / Back to the app</a></p></div>
{''.join(poster(s, APPQR) for s in SPOTS)}
</body></html>
"""
(R / "print.html").write_text(page, encoding="utf-8")
print("print.html", len(page.encode()), "bytes")
