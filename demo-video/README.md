# 3枚目デモ動画の素材

同じ日銀の声明文を、左：LLM（OpenAI `gpt-6-luna` の Chat API）／右：Decision Model（ローカルで動かした Kev-4B）に、**ブラウザの「実行」ボタンで実際に同時に呼び出す**画面。結果の再生ではなく、押した瞬間から本物の通信と時間を見せる。画面には、実行ログ（実行開始からの経過秒・リクエスト・ステータス）と、右の応答 JSON そのものが出る。

## 録画のしかた（ライブ版 `live.html`）

1. Kev のサーバーを起動する（下の「Kev のサーバー」）。別のターミナルを開いたままにする。
2. ライブ用サーバーを起動する。`OPENAI_API_KEY`（環境変数、またはこのフォルダの `.env`）が要る。

   ```powershell
   cd demo-video
   python serve_live.py
   ```

3. Chrome / Edge で `http://127.0.0.1:8765/` を開き、F11 で全画面にする。「準備完了」のログが出て、右上のボタンが「▶ 実行」になるまで待つ。
4. 画面録画を始める（Windows なら `Win + Alt + R`、または OBS）。
5. 「▶ 実行」を押す（または Space）。左が文章を書いている間に、右が先に確率を返し、最後に「◯秒 対 ◯秒」が出る。そこまで撮って録画を止める。
6. mp4 にして `../assets/demo_llm_vs_decision.mp4` に置く。スライドは、ファイルがあれば自動で表示する（ミュート・ループ再生）。
7. **画面に出た数字を、スライド3枚目の2か所と、発表者ノートの「約◯秒」に書き写す。** 実行のたびに数字は変わる（LLM は2.4〜4.7秒、Decision Model は0.3〜0.55秒ほどの揺れを確認済み。まれに LLM が8秒台に跳ねることもあった）。

撮影は `python record_live.py` で自動化してある（Edge を操作して、ページを開き、「実行」を押し、`../assets/demo_llm_vs_decision.mp4` に保存する。画面に出た数字は `rec_numbers.json` に残る）。

- 「もう一度」を押すと撮り直せる。毎回、実行前に自動で Kev のキャッシュを入れ替える（下の注意）。
- ライブ用サーバーは自分のマシン内（127.0.0.1）だけで待ち受け、配るのは `live.html` だけ。API キーはサーバー側にだけあり、ブラウザには出ない。撮り終わったら Ctrl+C で止める。

## 予備：再生版（`demo.html`）

通信しない再生版。`measure.py` が記録した実測を、そのままの時刻で再生する。ネットワークや GPU が使えない日の予備用で、「実際に呼んでいる」画面ではない（スライドで見せるならライブ版を使う）。ダブルクリックで開ける。

## Kev のサーバー（ライブ版でも、計測し直しでも要る）

右側の Kev は、ローカルの Linux 環境（WSL2 など）に `jev-local`（Kev-4B を動かす API サーバー、モデル約9GB）を入れて動かしている。

```powershell
# 1) Kev のサーバーを起動（別のターミナルで開いたままにする。GPU メモリを約10GB使う）
# jev-local のフォルダで（ポート 8008）
HF_HUB_OFFLINE=1 .venv/bin/python -m app.server --host 127.0.0.1 --port 8008

# 2)（再生版や、5回計測の記録を作り直すときだけ）計測と、画面用データの作り直し
python measure.py 5
python build_demo.py
```

- サーバーの起動には数十秒かかる。`http://127.0.0.1:8008/v1/models` が返れば準備完了。
- Kev はサーバー側に先頭キャッシュ（4件）があり、**同じ文章を繰り返すと約0.08秒に縮む**（キャッシュ命中）。`measure.py` は毎回、別の短い文章を5回送って声明文を押し出してから測るので、数字はキャッシュなし（約0.3秒）。最初の1回は GPU 初期化で遅い（約1.3秒）ため、これも計測の外で済ませている。

## ファイル

| ファイル | 役割 |
|---|---|
| `live.html` / `serve_live.py` | ライブ版の画面と、API を中継するローカルサーバー（キーはサーバー側だけ） |
| `record_live.py` | ライブ版を Edge で動かして録画し、mp4 にする（`playwright` と `imageio-ffmpeg` が要る） |
| `demo.html` / `demo_data.js` | 再生版の画面と、その元データ（`measure.json` から生成） |
| `measure.py` | Kev（ローカル）・OpenAI Decisions API（参考）・LLM を同時に呼んで実測し、`measure.json` に保存 |
| `build_demo.py` | LLM 所要時間が中央値の回を選んで `demo_data.js` を作る |
| `statement.txt` | 日本銀行 2026-09-18「金融市場調節方針の変更について」の4・5段落（原文のまま） |
| `probe_kev.py` | ローカルの Kev に1つ投げて、確率と時間を見る |
| `probe_decisions.py` / `oai.py` | OpenAI Decisions API の疎通確認と共通部品 |

## 注意

- `measure.py` を動かすには、環境変数 `OPENAI_API_KEY` か、このフォルダの `.env`（`OPENAI_API_KEY=...`）が要る。`.env` は `.gitignore` 済み。クラウド同期フォルダの下に置くと同期されるので、置き場所に注意し、不要になったら消す。
- **条件は左右で同じではない。** 左は OpenAI への通信を含み、右はローカルの GPU で通信なし。時間の比較は「API 越しの LLM」対「ローカルの Decision Model」になる。
- Kev の確率は タカ派 96.8%・中立 2.0%・ハト派 0.2%・判断困難 1.0%。参考に同時に測っている OpenAI Decisions API は 100%／0%／0%／0% と極端だった（`measure.json` の `openai_decision`）。明確な文書だったため。迷う文書ではばらける。
- OpenAI Decisions API は 2026-10-07 時点で限定プレビューかつ公式のスキーマ未公開。`/v1/decisions` の形（`input` と `questions[]`、選択肢は `choices:[{value}]`）はエラーメッセージから特定したもので、変わる可能性がある。
- 画面には「Decision Model（ローカル実行）」とだけ出し、モデル名・GPU 名・接続先は出していない。何を使ったかを聞かれたときの答え（Kev-4B、VRAM 12GB のローカル GPU）は、スライド3枚目の発表者ノートにある。
