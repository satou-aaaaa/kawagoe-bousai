#!/usr/bin/env python3
# index.html を作る（src/ と data/places.js を1つのファイルにまとめる）。標準ライブラリだけで動く。
# 1つのファイルにするのは、保存したファイルを AirDrop などで人に渡しても、それだけで開けるようにするため。
#   使い方: python3 tools/build.py   （データを取り直したら先に tools/build-data.py）
from pathlib import Path
R = Path(__file__).resolve().parent.parent
s = (R / "src/index.src.html").read_text(encoding="utf-8")
for mark, f in [("/*STYLE*/", "src/style.css"), ("/*PLACES*/", "data/places.js"), ("/*I18N*/", "src/i18n.js"), ("/*APP*/", "src/app.js")]:
    body = (R / f).read_text(encoding="utf-8")
    assert "</script" not in body.lower(), f
    s = s.replace(mark, body.rstrip("\n"), 1)
s = s.replace("<!doctype html>\n", "<!doctype html>\n<!-- 自動で作るファイル（tools/build.py）。直すのは src/ -->\n", 1)
(R / "index.html").write_text(s, encoding="utf-8")
print("index.html", len(s.encode()), "bytes")
