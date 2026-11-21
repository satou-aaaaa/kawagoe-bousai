#!/usr/bin/env python3
# print.html の QR を読み取り、中身が下に印刷した文と同じかを確かめる（文字化け・欠けの見張り）。
#   使い方: pip install qrcode==8.2 zxing-cpp pillow && python3 tools/check-qr.py
import re, html, sys
from pathlib import Path
from PIL import Image, ImageDraw
import zxingcpp
R = Path(__file__).resolve().parent.parent
s = (R / "print.html").read_text(encoding="utf-8")
bad = 0
for card in re.findall(r'<section class="card" data-spot="\w+">.*?</section>', s, re.S):
    svg = re.search(r'viewBox="0 0 (\d+) \1".*?d="([^"]+)"', card)
    n, d = int(svg[1]), svg[2]
    k = 6; img = Image.new("L", (n * k, n * k), 255); dr = ImageDraw.Draw(img)
    for x, y, w in re.findall(r"M(\d+) (\d+)h(\d+)", d):
        x, y, w = int(x), int(y), int(w); dr.rectangle([x * k, y * k, (x + w) * k - 1, (y + 1) * k - 1], fill=0)
    got = zxingcpp.read_barcodes(img)
    want = html.unescape(re.search(r'<pre class="tx">(.*?)</pre>', card, re.S)[1])
    ok = len(got) == 1 and got[0].text == want
    print("OK " if ok else "NG ", want.splitlines()[0]); bad += not ok
sys.exit(1 if bad else 0)
