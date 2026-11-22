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




# ---- 道順（src/route.js と同じ計算。qa/run.mjs が紙と画面の歩く距離が同じかを見る） ----
import heapq
M_LAT = 111320.0
M_LON = 111320.0 * math.cos(math.radians(35.9))
_RJ = (R / "src/route.js").read_text(encoding="utf-8")
_BIT = dict(re.findall(r"\b([A-Z][A-Z0-9]) = (\d+)", _RJ.split("\n")[4]))
def _w(name):
    body = re.search(name + r": \{(.*?)\}", _RJ).group(1)
    return {int(_BIT[k]): float(v) for k, v in re.findall(r"\[([A-Z][A-Z0-9])\]: ([\d.]+)", body)}
ROUTE_W = {k: _w(k) for k in ("quake", "flood", "fire")}
assert len(_BIT) == 9 and 32 in ROUTE_W["flood"] and 8 in ROUTE_W["quake"], ROUTE_W  # route.js の書き方が変わったら気づくように
_G = None
def road_graph():
    global _G
    if _G: return _G
    s = (R / "data/roads.js").read_text(encoding="utf-8")
    d = json.loads(s[s.index("window.ROADS = ") + 15: s.rindex(";")])
    lon, lat, x, y = [], [], 0, 0
    for i in range(0, len(d["n"]), 2):
        x += d["n"][i]; y += d["n"][i + 1]; lon.append(x); lat.append(y)
    adj = [[] for _ in lon]
    for i, e in enumerate(d["e"]):
        adj[e[0]].append(i); adj[e[1]].append(i)
    _G = dict(lon=lon, lat=lat, e=d["e"], adj=adj)
    return _G
def _meters(la1, lo1, la2, lo2): return math.hypot((lo1 - lo2) * M_LON, (la1 - la2) * M_LAT)
def _snap(p):
    G = road_graph()
    best = min(range(len(G["lon"])), key=lambda i: (G["lon"][i] / 1e5 - p["lon"]) ** 2 * M_LON ** 2 + (G["lat"][i] / 1e5 - p["lat"]) ** 2 * M_LAT ** 2)
    return best, _meters(p["lat"], p["lon"], G["lat"][best] / 1e5, G["lon"][best] / 1e5)
def _weight(f, hz):
    k = 1.0
    for b, w in ROUTE_W[hz].items():
        if f & b: k *= w
    return min(k, 200)
def route(a, b, hz):
    """a から b まで歩く道。{len: m, pts: [(lat, lon), ...]}"""
    G = road_graph(); s, sg = _snap(a); t, tg = _snap(b)
    dist, prev, done, h = {s: 0.0}, {}, set(), [(0.0, s)]
    while h:
        d, u = heapq.heappop(h)
        if u in done: continue
        done.add(u)
        if u == t: break
        for ei in G["adj"][u]:
            e = G["e"][ei]; v = e[1] if e[0] == u else e[0]
            nd = d + e[2] * _weight(e[3], hz)
            if nd < dist.get(v, 1e18): dist[v] = nd; prev[v] = ei; heapq.heappush(h, (nd, v))
    pts, L, v = [], 0, t
    chain = []
    while v != s:
        ei = prev[v]; e = G["e"][ei]; u = e[1] if e[0] == v else e[0]
        chain.append((ei, u)); v = u
    chain.reverse()
    pts = [(G["lat"][s] / 1e5, G["lon"][s] / 1e5)]
    for ei, u in chain:
        e = G["e"][ei]; x, y = G["lon"][e[0]], G["lat"][e[0]]; mids = []
        for k in range(4, len(e), 2):
            x += e[k]; y += e[k + 1]; mids.append((y / 1e5, x / 1e5))
        fwd = e[0] == u
        if not fwd: mids.reverse()
        end = e[1] if fwd else e[0]
        pts += mids + [(G["lat"][end] / 1e5, G["lon"][end] / 1e5)]
        L += e[2]
    return dict(len=L + sg + tg, pts=pts)
def walk_min(m): return max(1, math.ceil(m / 60))
