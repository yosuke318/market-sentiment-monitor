# market-sentiment-monitor

CNN の [Fear & Greed Index](https://edition.cnn.com/markets/fear-and-greed) ・[日経平均VI](https://indexes.nikkei.co.jp/nkave/index/profile?idx=nk225vi)・日経平均株価を毎日取得して、1 通のメールにまとめて Gmail から通知する。
区分（Extreme Fear / Fear / Neutral / Greed / Extreme Greed）が前回から変わった日は、変化を知らせる文面を先頭に付ける。

```
件名: 【区分変化】Extreme Fear → Fear（Fear & Greed 31）

🔔 区分が変化しました 📈
Extreme Fear（極度の恐怖） → Fear（恐怖）
楽観方向へ1段階動きました。市場心理は悲観寄りです。

😨 Fear & Greed Index: 31 — Fear（恐怖）

前日比: +3.1（28）
1週間前比: -5.8（37）
1ヶ月前比: -14.9（46）
1年前比: -23.4（55）

（2026-10-03 08:59 JST 時点）

────────────────

📊 日経平均VI: 22.58（2026-10-02 終値）

前日比: -0.34（22.92）
1週間前比: +2.28（20.30）
1ヶ月前比: -2.97（25.55）
1年前比: -2.71（25.29）

🗾 日経平均株価: 68,309円（2026-10-02 終値）

前日比: -0.9%（68,957円）
1週間前比: +2.9%（66,364円）
1ヶ月前比: +6.2%（64,326円）
1年前比: +52.0%（44,937円）

💡 日経平均VIの見方
・Fear & Greed とは向きが逆で、高いほど不安が強い
・…

[Fear & Greed の過去6ヶ月の推移グラフ]
[日経平均株価（左軸）と日経平均VI（右軸）を重ねた過去2年半の推移グラフ]
```

括弧内は比較対象の時点の値。日経平均VI・日経平均株価の 1週間前・1ヶ月前・1年前は、その日以前で最も近い営業日と比べる。グラフは PNG で本文に埋め込む（`chart.py`）。描画や日経のデータの取得に失敗した場合も、残りの内容で送る。メール 1 通は 200KB 程度（Gmail の上限は 25MB）。

## 仕組み

- GitHub Actions が毎日 09:30 JST に `fear_greed.py` を実行（`.github/workflows/notify.yml`）
- 前回の区分・スコア・データ時刻を `state/state.json` に保存し、Actions がコミットする
- Fear & Greed・日経のデータのどちらも前回と同じデータ（週末・日米ともに休場）なら通知しない。手動実行時に `force` にチェックを入れると、同じデータでも送る

## セットアップ

1. 送信元の Google アカウントで 2 段階認証を有効にし、[アプリ パスワード](https://myaccount.google.com/apppasswords)を発行する
2. リポジトリの Settings → Secrets and variables → Actions に以下を登録する

   | Secret | 値 |
   |---|---|
   | `MAIL_USER` | 送信元の Gmail アドレス |
   | `MAIL_APP_PASSWORD` | 発行したアプリ パスワード（16 文字、スペースなし） |
   | `MAIL_TO` | 送り先アドレス（省略すると `MAIL_USER` 宛て） |

3. Actions タブから `Fear & Greed notify` を手動実行（Run workflow）して届くか確認する

## ローカル実行

グラフ描画に matplotlib を使う（`requirements.txt`）。

```sh
pip install -r requirements.txt
python3 fear_greed.py   # MAIL_USER / MAIL_APP_PASSWORD 未設定なら標準出力のみ
MAIL_USER=you@gmail.com MAIL_APP_PASSWORD=xxxx python3 fear_greed.py
python3 -m unittest discover -s tests -t .
```

ローカルで実行すると `state/state.json` が作られる。Actions 側の状態とずれるのでコミットしないこと。

## 設計判断

[docs/adr/](docs/adr/README.md)
