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

内訳（構成要素ごとの区分）:
😏 株価の勢い（S&P500）: 強欲
😨 株価の強さ（新高値と新安値）: 恐怖
😐 株価の幅（値上がりと値下がり）: 中立
😱 プット/コール: 極度の恐怖
😨 ボラティリティ（VIX）: 恐怖
😏 ジャンク債需要: 強欲
🤑 安全資産需要: 極度の強欲

💾 SOX指数（米国の半導体株）: 7,358（2026-10-02 終値）

前日比: +1.8%（7,228）
1週間前比: +3.2%（7,130）
1ヶ月前比: +6.5%（6,909）
1年前比: +41.0%（5,219）

[S&P500（左軸）と Fear & Greed（右軸）を重ねた過去1年の推移グラフ]

────────────────

📊 日経平均VI: 22.58（2026-10-02 終値）

前日比: -0.34（22.92）
1週間前比: +2.28（20.30）
1ヶ月前比: -2.97（25.55）
1年前比: -2.71（25.29）

水準: 2023-10以降の749営業日で上位38%（中央値 21.50、最高 60.46、最低 14.04）

🗾 日経平均株価: 68,309円（2026-10-02 終値）

前日比: -0.9%（68,957円）
1週間前比: +2.9%（66,364円）
1ヶ月前比: +6.2%（64,326円）
1年前比: +52.0%（44,937円）

⚖️ NT倍率（日経平均÷TOPIX）: 19.07（2026-10-02 終値）

前日比: -0.02（19.09）
1週間前比: +0.10（18.97）
1ヶ月前比: +0.31（18.76）
1年前比: +1.40（17.67）

上がるほど日経平均が値がさ株に引っ張られ、下がるほど TOPIX（市場全体）が強い。

🔌 日本の半導体株（日経半導体株指数連動ETF 200A）: 2,393円（2026-10-02 終値）

前日比: +2.1%（2,344円）
1週間前比: +4.0%（2,301円）
1ヶ月前比: +8.2%（2,212円）
1年前比: +55.3%（1,541円）

指数の代わりに連動 ETF の価格で見ている（騰落率は指数とほぼ同じ）。

[日経平均株価・TOPIX（左軸）と日経平均VI（右軸）を重ねた過去2年半の推移グラフ]
```

括弧内は比較対象の時点の値。日経平均VI・日経平均株価の 1週間前・1ヶ月前・1年前は、その日以前で最も近い営業日と比べる。グラフは PNG で本文に埋め込む（`chart.py`）。TOPIX・SOX指数・日本の半導体株 ETF は Yahoo Finance から取る。TOPIX は NT 倍率とグラフ（緑の線）に使う。VI の「水準」は日経の CSV 全体（直近 3 年ほど）の中での位置、Fear & Greed の内訳は CNN の API が一緒に返す 7 つの構成要素の区分。描画や日経・Yahoo のデータの取得に失敗した場合も、残りの内容で送る。メール 1 通は 300KB 程度（Gmail の上限は 25MB）。

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
