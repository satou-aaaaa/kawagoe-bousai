# AGENTS.md

川越市限定の防災ページ（PWA）。インストール不要・5言語・一度開けば電波なしで使える。場所ごとの掲示用ポスター（print.html、A4）も作る。GitHub Pages で公開（main の /）。

## 準備（最初に一度）

```bash
bash scripts/setup.sh                       # 検査の道具（Playwright）
pip install qrcode==8.2    # index.html・print.html を作り直すとき（QR を作る）
```

## 作り方（index.html・print.html は自動で作るファイル。手で直さない）

```bash
python3 tools/build-data.py    # data/*.csv・city-list.json → data/places.js（データを取り直したとき）
python3 tools/build.py         # src/ + data/places.js → index.html（1つのファイルにまとめる。「みんなに配る」でそのまま人に渡すため。<noscript> の簡易表示も作る）
python3 tools/build-print.py   # print.html（場所ごとの掲示用ポスター）
```

## push する前の確認

```bash
node qa/run.mjs
```

## 決まり

- 外へ通信する部品を足さない（CSP の connect-src は 'self' だけ）。現在地は端末の中だけで使う。
- 避難場所の一次資料は国土地理院「指定緊急避難場所・指定避難所データ」（川越市 11201）と川越市の一覧。取り直したら tools/build-data.py の日付も直す。利用上の注意（最新は市に確認・災害種別ごとの指定・第三者に正しく伝える）を画面に出し続ける。
- 日本語以外は AI の訳で人の確認がまだ。確認したら「このページについて」の注意を外す。
- 決まった場所（SPOTS）の座標は国土地理院の住所検索で求めたもの。足すときも同じやり方で。
- 言葉を足すときは5言語すべてに足す（qa/run.mjs が抜けを見る）。

## 共通のきまり

- PR の作り方・マージの仕方は satou-aaaaa/shared-workflows の `routines/pr.md`、全体のきまりは `routines/common.md` に従う。
- Claude 以外の AI・人が作業するときは、shared-workflows の `routines/tool-map.md` と `routines/without-claude.md` を読む。
