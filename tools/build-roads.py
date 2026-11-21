#!/usr/bin/env python3
# 歩ける道のつながり（data/roads.js）を作る。アプリはこれを使い、端末の中だけで「危ない所を避けた道順」を探す。
#
# 使うデータ（どれも取り直せる。大きいので リポジトリには入れない）
#   道路・川   国土地理院 ベクトルタイル（experimental_bvmap）ズーム16。地理院タイル利用規約（出典を書けば使える）
#              https://cyberjapandata.gsi.go.jp/xyz/experimental_bvmap/16/{x}/{y}.pbf   x=58141..58174, y=25739..25768
#   浸水の深さ 国土数値情報 洪水浸水想定区域（A31a 2024・埼玉 11）想定最大規模（20）と家屋倒壊等氾濫想定区域（41 氾濫流・42 河岸侵食）。CC BY 4.0
#              https://nlftp.mlit.go.jp/ksj/gml/data/A31a/A31a-24/A31a-24_11_10.zip ・ A31a-24_11_20.zip を展開
#   土砂災害   国土数値情報 土砂災害警戒区域（A33 2024・埼玉 11）。埼玉県は商用・再配信可のオープンデータ
#              https://nlftp.mlit.go.jp/ksj/gml/data/A33/A33-24/A33-24_11_GML.zip を展開
#   ※ gsi.go.jp と nlftp.mlit.go.jp は古い TLS の再ネゴシエーションが要ることがある（OPENSSL_CONF で許す）。
#
# 使い方: pip install mapbox-vector-tile==2.1.0 shapely==2.0.6
#         python3 tools/build-roads.py <タイルのフォルダ> <A31a を展開したフォルダ> <A33-24_11.xml>
#
# 道の印（flags のビット）。アプリの app.js の ROUTE_W と同じ並び
#   1 橋  2 トンネル・地下道  4 石段  8 細い道（幅3m未満）  16 川・水路のそば
#   32 浸水0.5〜3m  64 浸水3m以上  128 家屋倒壊等氾濫想定区域  256 土砂災害警戒区域
import glob, json, math, os, re, sys
from collections import defaultdict
import mapbox_vector_tile as mvt
from shapely import STRtree, points, box, LineString, Polygon, MultiLineString
from shapely import transform as _tf, MultiPoint

def transform(f, g):
    return _tf(g, lambda a: __import__("numpy").array([f(x, y) for x, y in a]))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hinan import R, PLACES

TILES, A31, A33 = sys.argv[1:4]
Z, EXT = 16, 4096
S, N_, W, E_ = 35.85, 35.98, 139.38, 139.56  # 川越市とそのまわり
BRIDGE, TUNNEL, STAIRS, NARROW, RIVER, F1, F2, COLLAPSE, SLOPE = 1, 2, 4, 8, 16, 32, 64, 128, 256

def ll(tx, ty, px, py):
    n = 2 ** Z
    lon = (tx + px / EXT) / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (ty + py / EXT) / n))))
    return lon, lat

def lines(g):
    return list(g.geoms) if hasattr(g, "geoms") else [g]

# 1) タイルから 道・川 を読む（タイルの枠で切って、となりのタイルと重ならないようにする）
roads, rivers, ditches, waters = [], [], [], []
frame = box(0, 0, EXT, EXT)
for f in sorted(glob.glob(os.path.join(TILES, "*_*.pbf"))):
    tx, ty = map(int, os.path.basename(f)[:-4].split("_"))
    d = mvt.decode(open(f, "rb").read(), default_options={"y_coord_down": True})
    to_ll = lambda x, y, z=None: ll(tx, ty, x, y)
    for ft in d.get("road", {}).get("features", []):
        p = ft["properties"]; c = p.get("ftCode", 0)
        if not 2701 <= c <= 2734: continue  # 27xx が道の中心線（22xx は道の縁なので使わない）
        if p.get("motorway") == 1 or p.get("rdCtg") == 3: continue  # 高速道路は歩けない
        kind = c % 10  # 1 通常 2 雪覆い 3 橋・高架 4 トンネル
        fl = (BRIDGE if kind == 3 else 0) | (TUNNEL if kind == 4 else 0) | (STAIRS if 2731 <= c <= 2734 else 0) | (NARROW if p.get("rnkWidth") == 0 else 0)
        g = ft["geometry"]
        geom = LineString(g["coordinates"]) if g["type"] == "LineString" else MultiLineString(g["coordinates"])
        for part in lines(geom.intersection(frame)):
            if part.geom_type == "LineString" and part.length > 0:
                roads.append((transform(to_ll, part), fl))
    for ft in d.get("river", {}).get("features", []):
        g = ft["geometry"]; small = ft["properties"].get("ftCode") != 5201
        geom = LineString(g["coordinates"]) if g["type"] == "LineString" else MultiLineString(g["coordinates"])
        (ditches if small else rivers).extend(transform(to_ll, x) for x in lines(geom.intersection(frame)) if x.geom_type == "LineString")
    for ft in d.get("waterarea", {}).get("features", []):
        g = ft["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for pc in polys:
            try:
                pg = Polygon(pc[0], pc[1:]).buffer(0).intersection(frame)
            except Exception:
                continue
            if not pg.is_empty: waters.append(transform(to_ll, pg))
print("roads", len(roads), "rivers", len(rivers), "waters", len(waters))

# 2) 道を短い区間に分け、区間ごとに危なさの印をつける（区間の真ん中の点で調べる）
M_LAT = 111320.0
M_LON = 111320.0 * math.cos(math.radians(35.9))
def meters(a, b):
    return math.hypot((a[0] - b[0]) * M_LON, (a[1] - b[1]) * M_LAT)

area = MultiPoint([(p["lon"], p["lat"]) for p in PLACES]).convex_hull.buffer(1500 / M_LAT)
roads = [(g, fl) for g, fl in roads if area.intersects(g)]
segs = []  # (a, b, flags)
for g, fl in roads:
    cs = list(g.coords)
    for a, b in zip(cs, cs[1:]):
        L = meters(a, b)
        k = max(1, math.ceil(L / 25))  # 長い区間は 25m 以下に刻む（区域の出入りを見落とさない）
        pts = [(a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k) for i in range(k + 1)]
        segs += [(p, q, fl) for p, q in zip(pts, pts[1:]) if p != q]
mid = points([((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b, _ in segs])
flags = [fl for _, _, fl in segs]

def mark(polys, bit, dist=0.0):
    if not polys: return 0
    tree = STRtree(polys)
    if dist:
        idx = tree.query(mid, predicate="dwithin", distance=dist)[0]
    else:
        idx = tree.query(mid, predicate="intersects")[0]
    for i in set(idx.tolist()): flags[i] |= bit
    return len(set(idx.tolist()))

# 川のそば：川の線から約10m・水面から約15m・細い流れ（水路）から約5m（緯度経度の度で近い値にする）
print("river", mark(rivers, RIVER, 10 / M_LAT), mark(waters, RIVER, 15 / M_LAT), mark(ditches, RIVER, 5 / M_LAT))

# 川を橋でない所で渡っていないか（水面の中にある、橋でない道）。道の線と水面の線は少しずれるので、多すぎないことだけ見る
wet = set(STRtree(waters).query(mid, predicate="within")[0].tolist()) if waters else set()
wet_m = sum(meters(segs[i][0], segs[i][1]) for i in wet if not segs[i][2] & BRIDGE)
print("not-bridge in water (m)", round(wet_m))
for i in wet:
    if not segs[i][2] & BRIDGE: flags[i] |= RIVER

bb = box(W, S, E_, N_)
def a31(kind):
    out = defaultdict(list)
    for f in glob.glob(os.path.join(A31, "*", "*", f"{kind}_*", "*.geojson")):
        for ft in json.load(open(f, encoding="utf-8"))["features"]:
            g = ft["geometry"]
            if g["type"] != "Polygon": continue
            xs = [c[0] for c in g["coordinates"][0]]; ys = [c[1] for c in g["coordinates"][0]]
            if max(xs) < W or min(xs) > E_ or max(ys) < S or min(ys) > N_: continue
            rank = next((v for k, v in ft["properties"].items() if k.endswith("05")), 1)
            out[rank].append(Polygon(g["coordinates"][0], g["coordinates"][1:]))
    return out
depth = a31("20")  # 想定最大規模。ランク 1 0.5m未満 2 0.5〜3m 3 3〜5m 4 5〜10m 5 10〜20m 6 20m以上
print("flood 0.5-3m", mark(depth.get(2, []), F1), "3m+", mark(sum((depth.get(r, []) for r in (3, 4, 5, 6)), []), F2))
col = a31("41"); col42 = a31("42")
print("collapse", mark(sum(col.values(), []) + sum(col42.values(), []), COLLAPSE))

slopes = []
xml = open(A33, encoding="utf-8").read()
for m in re.finditer(r"<gml:posList>(.*?)</gml:posList>", xml, re.S):
    v = list(map(float, m.group(1).split()))
    ring = [(v[i + 1], v[i]) for i in range(0, len(v), 2)]  # 緯度 経度 の順で入っている
    if len(ring) >= 4 and any(W <= x <= E_ and S <= y <= N_ for x, y in ring):
        pg = Polygon(ring).buffer(0)
        if not pg.is_empty: slopes.append(pg)
print("slope", len(slopes), mark(slopes, SLOPE))

# 3) 点をつないでグラフにする（約1m で丸めて同じ点にする。タイルの境目の切れ目は 1.5m 以内ならつなぐ）
Q = 1e5
key = lambda p: (round(p[0] * Q), round(p[1] * Q))
adj = defaultdict(dict)  # node -> {node: flags}
for (a, b, _), fl in zip(segs, flags):
    ka, kb = key(a), key(b)
    if ka != kb: adj[ka][kb] = adj[kb][ka] = fl
parent = {}
def find(k):
    while parent.get(k, k) != k: k = parent[k]
    return k
ends = [k for k, v in adj.items() if len(v) == 1]
grid = defaultdict(list)
for k in adj: grid[(k[0] // 2, k[1] // 2)].append(k)
for k in ends:
    best = None
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for o in grid[(k[0] // 2 + dx, k[1] // 2 + dy)]:
                if o == k or o in adj[k]: continue
                d = meters((k[0] / Q, k[1] / Q), (o[0] / Q, o[1] / Q))
                if d <= 1.5 and (best is None or d < best[0]): best = (d, o)
    if best: parent[find(k)] = find(best[1])
if parent:
    nadj = defaultdict(dict)
    for k, v in adj.items():
        for o, fl in v.items():
            a, b = find(k), find(o)
            if a != b: nadj[a][b] = fl
    adj = nadj

# いちばん大きいつながりだけ残す（離れ小島の道に案内しない）
seen, best = set(), []
for s0 in adj:
    if s0 in seen: continue
    comp, stack = [], [s0]; seen.add(s0)
    while stack:
        u = stack.pop(); comp.append(u)
        for v in adj[u]:
            if v not in seen: seen.add(v); stack.append(v)
    if len(comp) > len(best): best = comp
keep = set(best)
adj = {k: {o: f for o, f in v.items() if o in keep} for k, v in adj.items() if k in keep}
print("nodes(all)", len(adj))

# 4) 枝分かれの無い点を省いて「交差点から交差点まで」の道にまとめる（印が変わる所では切る）
junction = {k for k, v in adj.items() if len(v) != 2 or len(set(v.values())) > 1}
edges, done = [], set()
for s0 in junction:
    for nb, fl in adj[s0].items():
        if (s0, nb) in done: continue
        path = [s0, nb]; done.add((s0, nb)); done.add((nb, s0))
        while path[-1] not in junction:
            u = path[-1]; nxt = next(o for o in adj[u] if o != path[-2])
            path.append(nxt); done.add((u, nxt)); done.add((nxt, u))
        edges.append((path, fl))
# 輪だけでできた道（交差点の無い輪）は省く
def rdp(pts, eps):
    if len(pts) < 3: return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    L = math.hypot((x2 - x1) * M_LON, (y2 - y1) * M_LAT) or 1e-9
    dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        x, y = pts[i]
        d = abs((x2 - x1) * M_LON * (y1 - y) * M_LAT - (x1 - x) * M_LON * (y2 - y1) * M_LAT) / L
        if d > dmax: dmax, idx = d, i
    if dmax <= eps: return [pts[0], pts[-1]]
    return rdp(pts[: idx + 1], eps)[:-1] + rdp(pts[idx:], eps)

nodes = sorted({p for path, _ in edges for p in (path[0], path[-1])})
nid = {k: i for i, k in enumerate(nodes)}
out_n = []
px, py = 0, 0
for k in nodes:  # 経度・緯度（1e-5 度）を ひとつ前との差で書く
    out_n += [k[0] - px, k[1] - py]; px, py = k
out_e = []
for path, fl in edges:
    L = sum(meters((a[0] / Q, a[1] / Q), (b[0] / Q, b[1] / Q)) for a, b in zip(path, path[1:]))
    geo = rdp([(k[0] / Q, k[1] / Q) for k in path], 4.0)[1:-1]
    row = [nid[path[0]], nid[path[-1]], max(1, round(L)), fl]
    x, y = path[0]
    for gx, gy in geo:
        gx, gy = round(gx * Q), round(gy * Q)
        row += [gx - x, gy - y]; x, y = gx, gy
    out_e.append(row)

meta = {"roads": "国土地理院 ベクトルタイル（道路・河川）", "flood": "国土数値情報 洪水浸水想定区域 A31a 2024（想定最大規模）・家屋倒壊等氾濫想定区域", "slope": "国土数値情報 土砂災害警戒区域 A33 2024",
        "made": __import__("datetime").date.today().isoformat(), "nodes": len(nodes), "edges": len(out_e)}
js = ("// 自動で作るファイル（tools/build-roads.py）。歩ける道のつながりと、道ごとの危なさの印。\n"
      "// 出典：" + "・".join(meta[k] for k in ("roads", "flood", "slope")) + "。浸水・土砂の区域は想定で、いまの通行止めではない。\n"
      "window.ROADS = " + json.dumps({"meta": meta, "n": out_n, "e": out_e}, ensure_ascii=False, separators=(",", ":")) + ";\n")
(R / "data/roads.js").write_text(js, encoding="utf-8")
bits = defaultdict(int)
for row in out_e:
    for b in range(9):
        if row[3] >> b & 1: bits[1 << b] += row[2]
print("nodes", len(nodes), "edges", len(out_e), "bytes", len(js.encode()), {k: round(v / 1000, 1) for k, v in sorted(bits.items())}, "km")
