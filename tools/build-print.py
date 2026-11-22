#!/usr/bin/env python3
# print.html を作る：決まった場所ごとの掲示用ポスター（A4）。上が北の簡単な地図・近い避難場所（地震・洪水）・電話・アプリの QR（URL）。
# 紙なので電気も電波も要らない（2026-11-21 satou さん「文字の QR は微妙」を受けて、文字だけQRから替えた）。
#   使い方: pip install qrcode==8.2 && python3 tools/build-print.py
# 近さの計算は src/app.js と同じ（qa/run.mjs が画面の答えと紙の答えが同じかを見る）。
from hinan import *

DZH = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
DKO = ["북", "북동", "동", "남동", "남", "남서", "서", "북서"]

def mapsvg(s, rows):
    # 上が北の道の地図。黒丸が「いまここ」、線が危ない所を避けた歩く道（地震=赤の線と丸数字・洪水=青の点線と四角の英字）
    S = 340
    pts = [(s["lat"], s["lon"])] + [pt for r in rows for pt in r["route"]["pts"]] + [(r["p"]["lat"], r["p"]["lon"]) for r in rows]
    la0, la1 = min(p[0] for p in pts), max(p[0] for p in pts); lo0, lo1 = min(p[1] for p in pts), max(p[1] for p in pts)
    cy, cx = (la0 + la1) / 2, (lo0 + lo1) / 2
    hw = max((lo1 - lo0) * M_LON / 2, (la1 - la0) * M_LAT / 2, 250) * 1.12
    k = S / 2 / hw
    X = lambda lo: S / 2 + (lo - cx) * M_LON * k
    Y = lambda la: S / 2 - (la - cy) * M_LAT * k
    path = lambda ps: "M" + "L".join(f"{X(lo):.1f} {Y(la):.1f}" for la, lo in ps)
    G = road_graph(); inb = lambda i: abs(G["lon"][i] / 1e5 - cx) * M_LON < hw and abs(G["lat"][i] / 1e5 - cy) * M_LAT < hw
    bg = []
    for e in G["e"]:
        if not (inb(e[0]) or inb(e[1])): continue
        x, y = G["lon"][e[0]], G["lat"][e[0]]; ps = [(y / 1e5, x / 1e5)]
        for j in range(4, len(e), 2):
            x += e[j]; y += e[j + 1]; ps.append((y / 1e5, x / 1e5))
        ps.append((G["lat"][e[1]] / 1e5, G["lon"][e[1]] / 1e5)); bg.append(path(ps))
    o = [f'<svg viewBox="0 0 {S} {S}" role="img" aria-label="地図 map">', f'<rect width="{S}" height="{S}" fill="#fff"/>',
         f'<path d="{"".join(bg)}" fill="none" stroke="#ccc" stroke-width="0.8"/>']
    for r in rows:   # 洪水の道を先に、地震の道を上に描く
        if r["kind"] == "f": o.append(f'<path d="{path([(s["lat"], s["lon"])] + r["route"]["pts"] + [(r["p"]["lat"], r["p"]["lon"])])}" fill="none" stroke="#1565c0" stroke-width="3" stroke-dasharray="7 4" stroke-linejoin="round"/>')
    for r in rows:
        if r["kind"] == "q": o.append(f'<path d="{path([(s["lat"], s["lon"])] + r["route"]["pts"] + [(r["p"]["lat"], r["p"]["lon"])])}" fill="none" stroke="#b3261e" stroke-width="3" stroke-linejoin="round" opacity=".85"/>')
    # 縮尺
    bar = 500 if hw > 600 else 200
    o.append(f'<path d="M12 {S - 14}h{bar * k:.1f}" stroke="#111" stroke-width="3"/><text x="12" y="{S - 20}" font-size="11">{dist(bar)}</text>')
    o.append(f'<text x="{S / 2}" y="16" font-size="15" font-weight="bold" text-anchor="middle" fill="#b3261e">▲ N 北</text>')
    o.append(f'<circle cx="{X(s["lon"]):.1f}" cy="{Y(s["lat"]):.1f}" r="9" fill="#111" stroke="#fff" stroke-width="2"/><text x="{X(s["lon"]):.1f}" y="{Y(s["lat"]) + 24:.1f}" font-size="13" font-weight="bold" text-anchor="middle" stroke="#fff" stroke-width="3" paint-order="stroke">いまここ / You</text>')
    qn = {r["p"]["n"] for r in rows if r["kind"] == "q"}
    for r in rows:
        x, y = X(r["p"]["lon"]), Y(r["p"]["lat"])
        if r["kind"] == "f" and r["p"]["n"] in qn: x, y = x + 18, y - 18   # 地震と同じ場所は、四角を右上にずらして両方見えるように
        if r["kind"] == "q":
            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="#b3261e" stroke="#fff" stroke-width="2"/><text x="{x:.1f}" y="{y + 5:.1f}" font-size="14" font-weight="bold" fill="#fff" text-anchor="middle">{r["i"]}</text>')
        else:
            o.append(f'<rect x="{x - 12:.1f}" y="{y - 12:.1f}" width="24" height="24" fill="#1565c0" stroke="#fff" stroke-width="2"/><text x="{x:.1f}" y="{y + 5:.1f}" font-size="14" font-weight="bold" fill="#fff" text-anchor="middle">{chr(64 + r["i"])}</text>')
    o.append("</svg>")
    return "".join(o)

def li(mark, p, d, b, flood, r):
    k = round(b / 45) % 8
    w = r["len"]
    up = f'<span class="up">{p["f"]}階以上 / {p["f"]}F+</span>' if flood and p.get("f") else ""
    return (f'<li><span class="mk {"f" if flood else "q"}">{mark}</span><span class="ar" style="transform:rotate({b:.0f}deg)" aria-hidden="true">↑</span>'
            f'<span><b class="nm">{html.escape(p["n"])}</b>{up}<br><span class="dd">{DJA[k]}・{DEN[k]}・{DZH[k]}・{DKO[k]}　<b class="wk">🚶 {dist(w)} {walk_min(w)}分/min</b></span></span></li>')

def poster(s, appqr):
    q, f = near(s, False), near(s, True)
    rows = [dict(kind="q", i=i, p=p, route=route(s, p, "quake")) for i, (p, d, b) in enumerate(q, 1)] + [dict(kind="f", i=i, p=p, route=route(s, p, "flood")) for i, (p, d, b) in enumerate(f, 1)]
    ql = "".join(li(str(i), p, d, b, False, rows[i - 1]["route"]) for i, (p, d, b) in enumerate(q, 1))
    fl = "".join(li(chr(64 + i), p, d, b, True, rows[len(q) + i - 1]["route"]) for i, (p, d, b) in enumerate(f, 1))
    return f"""<section class="poster" data-spot="{s['id']}">
<h2>避難場所 Evacuation Sites 避难场所 대피 장소</h2><p class="here">いまここ / You are here: <b>{html.escape(s['ja'])}</b> {html.escape(s['en'])}</p>
<div class="body"><div class="map">{mapsvg(s, rows)}<p class="cap">上が北。線は危ない所をなるべく避けた歩く道 / North is up. Lines: walking routes avoiding hazards</p></div>
<div class="lists"><h3 class="q">● 地震 Earthquake 地震 지진</h3><ol class="lq">{ql}</ol>
<h3 class="f">■ 大雨・洪水 Flood 洪水 홍수</h3><p class="note">川に近づかない。外が危ないときは近くの丈夫な建物の上の階へ。<br>Stay away from rivers. If outside is dangerous, go upstairs in a sturdy building.</p><ol class="lf">{fl}</ol></div></div>
<div class="foot"><div class="calls"><b>119</b> 火事・救急 Fire/Ambulance 火警・急救 화재・구급<br><b>110</b> 警察 Police 警察 경찰<br><b>171</b> 災害用伝言ダイヤル Disaster message dial<br>無料Wi-Fi <b>00000JAPAN</b>（大きな災害のとき / in major disasters）</div>
<div class="qr">{appqr}<span>アプリ App 应用 앱<br>電波があるうちに一度開くと保存され、電波がなくても使えます。<br>Open once while online; then it works offline.</span></div></div>
<p class="src">出典：国土地理院「指定緊急避難場所データ」（{META['gsi']} 更新分）・川越市「指定避難所・指定緊急避難場所一覧」（{META['city']} 更新）。避難場所は災害の種類ごとに指定されています。最新の状況は川越市で確認してください。道と距離は、国土地理院の道路と国土数値情報（浸水・土砂の想定）から、地震は細い道や崖を、洪水は浸水想定・川のそば・地下道を避けて計算。区域は想定で、いまの通行止めは分かりません。非公式。</p>
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
.dd{{font-size:.85rem;color:#333}}.wk{{color:#111}}.up{{margin-left:6px;font-size:.8rem;border:1px solid #1565c0;color:#1565c0;padding:0 4px;border-radius:4px;font-weight:bold}}
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
