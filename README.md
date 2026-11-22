# 川越 避難ガイド / Kawagoe Evacuation Guide

川越市にいる人（観光客・外国の人を含む）のための防災ページです（非公式）。

- **みんなに配る（目玉）**：画面の「配る」から、電波があれば QR を見せるだけ、電波がなければ AirDrop・クイック共有でファイルを送るだけで、まわりの人に渡せます。受け取った人もまた渡せます。スクリプトが動かない開き方でも、避難場所の一覧と電話番号は読めます。
- **インストール不要**：URL か QR で開くだけ。
- **電波がなくても使える**：一度開くと端末に保存されます（Service Worker）。現在地は GPS で取れるので、近い避難場所の方角と距離が出ます。
- **危ない所を避けた道順**：一覧の「道順」を押すと、端末の中だけで歩く道を探し、上が北の道の地図と「何m進んで右へ」を出します。地震は細い道（塀・倒壊）・崖、大雨は浸水想定・家屋倒壊等氾濫想定区域・川や水路のそば・地下道（冠水）・橋、火事は細い道を避けます。高速道路は通りません。区域は想定で、いまの通行止めは分かりません。道のデータ（約1.6MB）も保存されるので電波なしで使え、ファイルで渡すときにも入ります。「歩きながら見る」で地図に現在地を出し、残りの距離・道順からはずれたこと・着いたことを知らせます（位置は端末の外へ出しません）。
- **5言語**：日本語・やさしい日本語・English・中文・한국어（日本語以外は AI の訳。人の確認はまだ）。
- **掲示用ポスター**（print.html）：一番街・本川越駅・川越駅・喜多院・川越氷川神社ごとに、上が北の道の地図に、危ない所を避けた歩く道（地震=赤・洪水=青の点線）と歩く距離・近い避難場所（地震・洪水）・電話・アプリの QR を載せた A4。紙なので電気も電波も要りません。

公開：https://satou-aaaaa.github.io/kawagoe-bousai/

## 出典

- 国土地理院「指定緊急避難場所・指定避難所データ」（川越市）https://www.gsi.go.jp/bousaichiri/hinanbasho.html
- 川越市「指定避難所・指定緊急避難場所一覧」https://www.city.kawagoe.saitama.jp/shisei/shisetsu/hinanjyo/1013361.html
- 国土地理院 ベクトルタイル（道路・河川。地理院タイル利用規約）https://github.com/gsi-cyberjapan/gsimaps-vector-experiment
- 国土数値情報「洪水浸水想定区域データ」A31a 2024（埼玉・想定最大規模・家屋倒壊等氾濫想定区域。CC BY 4.0）https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A31a-2024.html
- 国土数値情報「土砂災害警戒区域データ」A33 2024（埼玉県はオープンデータ・再配信可）https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A33-2024.html
- 総務省「災害用統一SSID 00000JAPAN」https://www.soumu.go.jp/menu_seisaku/ictseisaku/public_wi-fi/freewifi_00000japan.html
- web.dev「Offline data」https://web.dev/learn/pwa/offline-data

避難場所の情報は最新でないことがあります。最新の状況は必ず川越市で確認してください。公式の情報の代わりにはなりません。

作り方・検査は [AGENTS.md](AGENTS.md)。
