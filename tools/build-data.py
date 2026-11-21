#!/usr/bin/env python3
# 避難場所のデータ（data/places.js）を作る。標準ライブラリだけで動く。
#   使い方: python3 tools/build-data.py
# 入力（どれも公式の一次資料。取り直したら日付も直す）:
#   data/gsi-hinanbasho.csv  国土地理院「指定緊急避難場所データ」川越市 11201_2（座標・災害の種類ごとの指定）
#   data/gsi-hinanjo.csv     国土地理院「指定避難所データ」川越市 11201_1
#   data/city-list.json      川越市「指定避難所・指定緊急避難場所一覧」の表（洪水・内水で「2階以上」「3階以上」の注記）
import csv, json, re, sys, unicodedata
from pathlib import Path
R = Path(__file__).resolve().parent.parent
GSI_DATE = "2026-08-31"   # 国土地理院の掲載の最終更新（一覧の表示）
CITY_DATE = "2026-06-22"  # 川越市のページの更新日

def norm(s):
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"[\s・･（）()]", "", s).replace("ヶ", "ケ")

def rows(p):
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

places = rows(R / "data/gsi-hinanbasho.csv")
shelters = {norm(r["施設・場所名"]) for r in rows(R / "data/gsi-hinanjo.csv")}
city = {norm(c["name"]): c for c in json.loads((R / "data/city-list.json").read_text(encoding="utf-8"))}

def floor(v):
    m = re.match(r"([23])階以上", v or "")
    return int(m.group(1)) if m else 0

out, unmatched = [], []
for r in places:
    name = r["施設・場所名"].strip()
    k = norm(name)
    c = city.get(k)
    if c is None: unmatched.append(name)
    h = {key: r[col].strip() == "1" for key, col in [("flood", "洪水"), ("slope", "崖崩れ、土石流及び地滑り"), ("quake", "地震"), ("fire", "大規模な火事"), ("inland", "内水氾濫")]}
    p = {
        "n": name,
        "a": r["住所"].replace("埼玉県川越市", "").strip(),
        "lat": round(float(r["緯度"]), 6),
        "lon": round(float(r["経度"]), 6),
        "h": [key for key, v in h.items() if v],
        "s": k in shelters,
    }
    f = max(floor(c["flood"]), floor(c["inland"])) if c else 0
    if f and (h["flood"] or h["inland"]): p["f"] = f
    if c and c.get("note"): p["note"] = c["note"]
    out.append(p)

body = "// 自動で作るファイル（tools/build-data.py）。手で直さない。\n"
body += "// 出典: 国土地理院「指定緊急避難場所・指定避難所データ」（" + GSI_DATE + " 更新分）・川越市「指定避難所・指定緊急避難場所一覧」（" + CITY_DATE + " 更新）\n"
body += "window.PLACES_META = " + json.dumps({"gsi": GSI_DATE, "city": CITY_DATE, "count": len(out)}, ensure_ascii=False) + ";\n"
body += "window.PLACES = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n"
(R / "data/places.js").write_text(body, encoding="utf-8")
print(f"{len(out)} 件。市の一覧と名前が合わないもの {len(unmatched)} 件:", "、".join(unmatched[:40]), file=sys.stderr)
