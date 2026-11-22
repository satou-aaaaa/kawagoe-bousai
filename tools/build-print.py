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
    # まわりの道は言語によらず同じなので、1か所に1回だけ書いて（symbol）言語ごとの地図から使う
    sym = f'<symbol id="bg-{s["id"]}" viewBox="0 0 {S} {S}"><path d="{"".join(bg)}" fill="none" stroke="#ccc" stroke-width="0.8"/></symbol>'
    o = [f'<svg viewBox="0 0 {S} {S}" role="img" aria-label="{{MAP}}">', f'<rect width="{S}" height="{S}" fill="#fff"/>', f'<use href="#bg-{s["id"]}" width="{S}" height="{S}"/>']
    for r in rows:   # 洪水の道を先に、地震の道を上に描く
        if r["kind"] == "f": o.append(f'<path d="{path([(s["lat"], s["lon"])] + r["route"]["pts"] + [(r["p"]["lat"], r["p"]["lon"])])}" fill="none" stroke="#1565c0" stroke-width="3" stroke-dasharray="7 4" stroke-linejoin="round"/>')
    for r in rows:
        if r["kind"] == "q": o.append(f'<path d="{path([(s["lat"], s["lon"])] + r["route"]["pts"] + [(r["p"]["lat"], r["p"]["lon"])])}" fill="none" stroke="#b3261e" stroke-width="3" stroke-linejoin="round" opacity=".85"/>')
    # 縮尺
    bar = 500 if hw > 600 else 200
    o.append(f'<path d="M12 {S - 14}h{bar * k:.1f}" stroke="#111" stroke-width="3"/><text x="12" y="{S - 20}" font-size="11">{dist(bar)}</text>')
    o.append(f'<text x="{S / 2}" y="16" font-size="15" font-weight="bold" text-anchor="middle" fill="#b3261e">▲ {{N}}</text>')
    o.append(f'<circle cx="{X(s["lon"]):.1f}" cy="{Y(s["lat"]):.1f}" r="9" fill="#111" stroke="#fff" stroke-width="2"/><text x="{X(s["lon"]):.1f}" y="{Y(s["lat"]) + 24:.1f}" font-size="13" font-weight="bold" text-anchor="middle" stroke="#fff" stroke-width="3" paint-order="stroke">{{YOU}}</text>')
    qn = {r["p"]["n"] for r in rows if r["kind"] == "q"}
    for r in rows:
        x, y = X(r["p"]["lon"]), Y(r["p"]["lat"])
        if r["kind"] == "f" and r["p"]["n"] in qn: x, y = x + 18, y - 18   # 地震と同じ場所は、四角を右上にずらして両方見えるように
        if r["kind"] == "q":
            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="#b3261e" stroke="#fff" stroke-width="2"/><text x="{x:.1f}" y="{y + 5:.1f}" font-size="14" font-weight="bold" fill="#fff" text-anchor="middle">{r["i"]}</text>')
        else:
            o.append(f'<rect x="{x - 12:.1f}" y="{y - 12:.1f}" width="24" height="24" fill="#1565c0" stroke="#fff" stroke-width="2"/><text x="{x:.1f}" y="{y + 5:.1f}" font-size="14" font-weight="bold" fill="#fff" text-anchor="middle">{chr(64 + r["i"])}</text>')
    o.append("</svg>")
    return sym, "".join(o)

# 言葉（1枚に1つの言語。2026-11-22 satou さん「複数の言語が同時に出ていてわかりづらい」を受けて、言語ごとの1枚にした）
# 避難場所の名前は、現地の看板と同じ日本語のまま出す
L = {
 "ja": dict(name="日本語", h="避難場所", here="いまここ", you="いまここ", n="北", map="地図", cap="上が北。線は、危ない所をなるべく避けた歩く道。",
  q="● 地震", f="■ 大雨・洪水", note="川に近づかない。外が危ないときは、近くの丈夫な建物の上の階へ。", floor="{n}階以上", min="{n}分",
  dirs=["北", "北東", "東", "南東", "南", "南西", "西", "北西"], c119="火事・救急", c110="警察", c171="災害用伝言ダイヤル", wifi="無料Wi-Fi（大きな災害のとき）",
  app="アプリ。電波があるうちに一度開くと保存され、電波がなくても使えます。",
  src="出典：国土地理院「指定緊急避難場所データ」（{gsi} 更新分）・川越市「指定避難所・指定緊急避難場所一覧」（{city} 更新）・国土地理院の道路・国土数値情報（浸水・土砂の想定）。避難場所は災害の種類ごとに指定されています。道は、地震では細い道や崖を、洪水では浸水想定・川のそば・地下道をなるべく避けています。区域は想定で、いまの通行止めは分かりません。最新は川越市で確認してください。非公式。"),
 "easy": dict(name="やさしい にほんご", h="ひなんばしょ", here="いま ここ", you="いま ここ", n="きた", map="ちず", cap="うえが きた。せんは、あぶない ところを さけた あるく みち。",
  q="● じしん", f="■ おおあめ・こうずい", note="かわに ちかづかないで。そとが あぶない ときは、ちかくの じょうぶな たてものの うえの かいへ。", floor="{n}かい より うえ", min="{n}ふん",
  dirs=["きた", "きたひがし", "ひがし", "みなみひがし", "みなみ", "みなみにし", "にし", "きたにし"], c119="かじ・きゅうきゅう", c110="けいさつ", c171="さいがいようでんごんダイヤル", wifi="むりょう Wi-Fi（おおきな さいがいの とき）",
  app="アプリ。でんぱが ある ときに いちど ひらくと、でんぱが なくても つかえます。",
  src="しゅってん：こくどちりいん・かわごえし（{city}）・こくどすうちじょうほう。あたらしい じょうほうは かわごえしで たしかめて ください。こうしきでは ありません。"),
 "en": dict(name="English", h="Evacuation Sites", here="You are here", you="You", n="N", map="Map", cap="North is up. Lines: walking routes that avoid hazards where possible.",
  q="● Earthquake", f="■ Heavy rain / Flood", note="Stay away from rivers. If going outside is dangerous, go to an upper floor of a nearby sturdy building.", floor="{n}F or higher", min="{n} min",
  dirs=["N", "NE", "E", "SE", "S", "SW", "W", "NW"], c119="Fire / Ambulance", c110="Police", c171="Disaster message dial", wifi="Free Wi-Fi (in major disasters)",
  app="App. Open it once while online; then it works offline.",
  src="Sources: GSI Japan evacuation site data ({gsi}), Kawagoe City list ({city}), GSI roads, National Land Numerical Information (flood and landslide forecasts). Sites are designated per disaster type. Routes avoid narrow roads and slopes (earthquake) or flood areas, riversides and underpasses (flood). Areas are forecasts; current closures are unknown. Check Kawagoe City for the latest. Unofficial. Place names are in Japanese, as on local signs."),
 "zh": dict(name="中文", h="避难场所", here="你在这里", you="你在这里", n="北", map="地图", cap="上方为北。线为尽量避开危险地点的步行路线。",
  q="● 地震", f="■ 暴雨・洪水", note="不要靠近河流。外出危险时，请到附近坚固建筑物的高层。", floor="{n}楼以上", min="{n}分钟",
  dirs=["北", "东北", "东", "东南", "南", "西南", "西", "西北"], c119="火警・急救", c110="警察", c171="灾害留言电话", wifi="免费Wi-Fi（大规模灾害时）",
  app="应用。有信号时打开一次即可保存，没有信号也能使用。",
  src="出处：日本国土地理院 避难场所数据（{gsi}）、川越市 避难场所一览（{city}）、国土地理院 道路、国土数值信息（浸水・土石流预测）。避难场所按灾害种类指定。路线在地震时避开窄路和陡坡，在洪水时避开预计浸水区、河边和地下通道。区域为预测，无法得知当前封路情况。最新信息请向川越市确认。非官方。地名与当地标牌一致，使用日语。"),
 "ko": dict(name="한국어", h="대피 장소", here="현재 위치", you="현재 위치", n="북", map="지도", cap="위쪽이 북쪽. 선은 위험한 곳을 가능한 한 피한 걷는 길.",
  q="● 지진", f="■ 폭우・홍수", note="강에 가까이 가지 마세요. 밖이 위험하면 가까운 튼튼한 건물의 높은 층으로.", floor="{n}층 이상", min="{n}분",
  dirs=["북", "북동", "동", "남동", "남", "남서", "서", "북서"], c119="화재・구급", c110="경찰", c171="재해용 전언 다이얼", wifi="무료 Wi-Fi(대규모 재해 시)",
  app="앱. 신호가 있을 때 한 번 열면 저장되어 신호가 없어도 쓸 수 있습니다.",
  src="출처: 일본 국토지리원 대피 장소 데이터({gsi}), 가와고에시 대피 장소 목록({city}), 국토지리원 도로, 국토수치정보(침수・토사 예측). 대피 장소는 재해 종류별로 지정됩니다. 길은 지진 때 좁은 길과 비탈을, 홍수 때 침수 예상 구역・강가・지하도를 피합니다. 구역은 예측이며 현재 통행금지는 알 수 없습니다. 최신 정보는 가와고에시에서 확인하세요. 비공식. 지명은 현지 표지판과 같은 일본어."),
}
SPOT_NAMES = {m[1]: m[2] for m in re.finditer(r'id: "(\w+)".*?name: (\{[^}]*\})', spots_src)}
def spot_name(s, lang):
    return re.search(lang + r': "([^"]+)"', SPOT_NAMES[s["id"]]).group(1)

def lang_of(T): return next(c for c, v in L.items() if v is T)

def li(mark, p, b, flood, r, T):
    k = round(b / 45) % 8
    w = r["len"]
    up = f'<span class="up">{html.escape(T["floor"].format(n=p["f"]))}</span>' if flood and p.get("f") else ""
    return (f'<li><span class="mk {"f" if flood else "q"}">{mark}</span><span class="ar" style="transform:rotate({b:.0f}deg)" aria-hidden="true">↑</span>'
            f'<span><b class="nm">{html.escape(p["n"])}</b>{up}<br><span class="dd">{T["dirs"][k]}　<b class="wk">🚶 {dist(w)}{(" ({})" if lang_of(T) in ("en", "ko") else "（{}）").format(T["min"].format(n=walk_min(w)))}</b></span></span></li>')

SYMS = []
def posters(s):
    q, f = near(s, False), near(s, True)
    rows = [dict(kind="q", i=i, p=p, route=route(s, p, "quake")) for i, (p, d, b) in enumerate(q, 1)] + [dict(kind="f", i=i, p=p, route=route(s, p, "flood")) for i, (p, d, b) in enumerate(f, 1)]
    sym, msvg = mapsvg(s, rows)
    SYMS.append(sym)
    out = []
    for lang, T in L.items():
        ql = "".join(li(str(i), p, b, False, rows[i - 1]["route"], T) for i, (p, d, b) in enumerate(q, 1))
        fl = "".join(li(chr(64 + i), p, b, True, rows[len(q) + i - 1]["route"], T) for i, (p, d, b) in enumerate(f, 1))
        m = msvg.replace("{MAP}", T["map"]).replace("{N}", T["n"]).replace("{YOU}", html.escape(T["you"]))
        qr = svg(APP_URL + ("" if lang == "ja" else f"?lang={lang}"))[1]
        out.append(f"""<section class="poster" data-spot="{s['id']}" data-lang="{lang}" lang="{'ja' if lang == 'easy' else 'zh-Hans' if lang == 'zh' else lang}">
<h2>{T['h']}</h2><p class="here">{T['here']}: <b>{html.escape(spot_name(s, lang))}</b></p>
<div class="body"><div class="map">{m}<p class="cap">{T['cap']}</p></div>
<div class="lists"><h3 class="q">{T['q']}</h3><ol class="lq">{ql}</ol>
<h3 class="f">{T['f']}</h3><p class="note">{T['note']}</p><ol class="lf">{fl}</ol></div></div>
<div class="foot"><div class="calls"><b>119</b> {T['c119']}<br><b>110</b> {T['c110']}<br><b>171</b> {T['c171']}<br>{T['wifi']} <b>00000JAPAN</b></div>
<div class="qr">{qr}<span>{T['app']}</span></div></div>
<p class="src">{html.escape(T['src'].format(gsi=META['gsi'], city=META['city']))}</p>
</section>""")
    return "".join(out)

BODY = "".join(posters(s) for s in SPOTS)
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
.poster{{display:none}}{''.join(f'body[data-lang={c}] .poster[data-lang={c}]{{display:block}}' for c in L)}
.langs{{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0}}.langs button{{min-height:44px;padding:6px 14px;font-size:1rem;border:2px solid #b3261e;border-radius:22px;background:#fff;color:#b3261e;cursor:pointer}}
.langs button[aria-pressed=true]{{background:#b3261e;color:#fff;font-weight:bold}}
</style></head><body data-lang="ja">
<div class="noprint"><h1>掲示用ポスター（場所ごと・A4）</h1>
<p class="intro">紙なので、電気も電波も要りません。お店や駅に貼る場合は、持ち主・管理者の許可を取ってください。印刷はブラウザの「印刷」から（A4・1か所1枚）。</p>
<div class="langs" role="group" aria-label="言語 Language">{''.join(f'<button type="button" data-pick="{c}" aria-pressed="{str(c == "ja").lower()}">{T["name"]}</button>' for c, T in L.items())}</div>
<p><a href="./">← アプリに戻る / Back to the app</a></p></div>
<svg width="0" height="0" style="position:absolute" aria-hidden="true">{''.join(SYMS)}</svg>
{BODY}
<script>
// 言語を切り替える（電波なしで動く。選んだ言語は覚える。?lang=en などでも開ける）
(function () {{
  var codes = {json.dumps(list(L))}, q = new URLSearchParams(location.search).get("lang"), saved = null;
  try {{ saved = localStorage.getItem("kb-lang"); }} catch (e) {{}}
  function set(c) {{
    document.body.dataset.lang = c;
    document.documentElement.lang = c === "easy" ? "ja" : c === "zh" ? "zh-Hans" : c;
    document.querySelectorAll("[data-pick]").forEach(function (b) {{ b.setAttribute("aria-pressed", String(b.dataset.pick === c)); }});
    try {{ localStorage.setItem("kb-lang", c); }} catch (e) {{}}
  }}
  document.querySelectorAll("[data-pick]").forEach(function (b) {{ b.addEventListener("click", function () {{ set(b.dataset.pick); }}); }});
  set(codes.indexOf(q) >= 0 ? q : codes.indexOf(saved) >= 0 ? saved : "ja");
}})();
</script>
</body></html>
"""
(R / "print.html").write_text(page, encoding="utf-8")
print("print.html", len(page.encode()), "bytes")
