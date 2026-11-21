#!/usr/bin/env python3
# index.html を作る（src/ と data/places.js を1つのファイルにまとめる）。
# 1つのファイルにするのは、保存したファイルを AirDrop などで人に渡しても、それだけで開けるようにするため（「みんなに配る」）。
# 受け取ったファイルをスクリプトの動かない画面（iPhone の「ファイル」のプレビューなど）で開いても読めるよう、
# 近い避難場所・全部の避難場所・電話番号を <noscript> にも書く。
#   使い方: pip install qrcode==8.2 && python3 tools/build.py   （データを取り直したら先に tools/build-data.py）
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from hinan import *

# アプリの URL の QR（言語ごと。電波がなくても画面に出せるよう、作るときに SVG にしておく）
LANG_CODES = ["ja", "easy", "en", "zh", "ko"]
qrs = {c: svg(APP_URL + ("" if c == "ja" else f"?lang={c}"))[1] for c in LANG_CODES}
qr_js = "window.APP_URL = " + json.dumps(APP_URL) + ";\nwindow.APP_QR = " + json.dumps(qrs, ensure_ascii=False) + ";"

# スクリプトが動かないときの表示
H = {"quake": "地震 Earthquake", "flood": "洪水 Flood", "inland": "内水 Inland flood", "slope": "崖崩れ Landslide"}
def row(p):
    hz = " / ".join(H[h] for h in ["quake", "flood", "inland", "slope"] if h in p["h"])
    up = f'（洪水は{p["f"]}階以上 / Flood: {p["f"]}F+）' if p.get("f") else ""
    return f'<li><b>{html.escape(p["n"])}</b> {html.escape(p["a"])} — {hz}{up}</li>'
spots = []
for s in SPOTS:
    def items(flood):
        return "".join(f'<li>{html.escape(p["n"])}：{DJA[round(b / 45) % 8]} {dist(d)} / {DEN[round(b / 45) % 8]} {dist(d)}{"（" + str(p["f"]) + "階以上 / " + str(p["f"]) + "F+）" if flood and p.get("f") else ""}</li>' for p, d, b in near(s, flood))
    spots.append(f'<h3>{html.escape(s["ja"])} / {html.escape(s["en"])}</h3><p>地震 Earthquake</p><ol>{items(False)}</ol><p>大雨・洪水 Flood</p><ol>{items(True)}</ol>')
noscript = f"""<noscript><div class="nojs">
<h2>簡易表示 / Simple view</h2>
<p>119 火事・救急 Fire/Ambulance ／ 110 警察 Police ／ 171 災害用伝言ダイヤル Disaster message dial ／ 無料Wi-Fi 00000JAPAN</p>
<h2>場所ごとの近い避難場所 / Nearest sites</h2>{''.join(spots)}
<h2>川越市の避難場所 全{len(PLACES)}か所 / All evacuation sites</h2><ul>{''.join(row(p) for p in sorted(PLACES, key=lambda p: p["a"]))}</ul>
<p>出典：国土地理院（{META['gsi']} 更新分）・川越市（{META['city']} 更新）。最新は川越市で確認。非公式。</p>
</div></noscript>"""

s = (R / "src/index.src.html").read_text(encoding="utf-8")
for mark, body in [("/*STYLE*/", (R / "src/style.css").read_text(encoding="utf-8")), ("/*PLACES*/", (R / "data/places.js").read_text(encoding="utf-8")),
                   ("/*QR*/", qr_js), ("/*I18N*/", (R / "src/i18n.js").read_text(encoding="utf-8")), ("/*APP*/", (R / "src/app.js").read_text(encoding="utf-8")),
                   ("<!--NOSCRIPT-->", noscript)]:
    assert mark in s, mark
    assert "</script" not in body.lower() or mark == "<!--NOSCRIPT-->", mark
    s = s.replace(mark, body.rstrip("\n"), 1)
s = s.replace("<!doctype html>\n", "<!doctype html>\n<!-- 自動で作るファイル（tools/build.py）。直すのは src/ -->\n", 1)
(R / "index.html").write_text(s, encoding="utf-8")
print("index.html", len(s.encode()), "bytes")
