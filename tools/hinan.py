# build.py と build-print.py が使う共通の部品（データの読み込み・距離と方角・近い順・QR の SVG）。
# 近さの計算は src/app.js と同じ（qa/run.mjs が画面と紙の答えが同じかを見る）。
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


