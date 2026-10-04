# market-sentiment-monitor

CNN の [Fear & Greed Index](https://edition.cnn.com/markets/fear-and-greed) を毎日取得して Gmail からメールで通知する。
区分（Extreme Fear / Fear / Neutral / Greed / Extreme Greed）が前回から変わった日は、変化を知らせる文面を先頭に付ける。

```
件名: 【区分変化】Extreme Fear → Fear（Fear & Greed 31）

🔔 区分が変化しました 📈
Extreme Fear（極度の恐怖） → Fear（恐怖）
楽観方向へ1段階動きました。市場心理は悲観寄りです。

😨 Fear & Greed Index: 31 — Fear（恐怖）
前日比 +7.2 / 1週間前比 -5.8 / 1ヶ月前比 -14.9 / 1年前比 -23.4
（2026-10-03 08:59 JST 時点）
```

## 仕組み

- GitHub Actions が毎日 09:30 JST に `fear_greed.py` を実行（`.github/workflows/notify.yml`）
- 前回の区分・スコア・データ時刻を `state/state.json` に保存し、Actions がコミットする
- データ時刻が前回と同じ（週末・米国祝日）なら通知しない

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

```sh
python3 fear_greed.py   # MAIL_USER / MAIL_APP_PASSWORD 未設定なら標準出力のみ
MAIL_USER=you@gmail.com MAIL_APP_PASSWORD=xxxx python3 fear_greed.py
python3 -m unittest discover -s tests -t .
```

ローカルで実行すると `state/state.json` が作られる。Actions 側の状態とずれるのでコミットしないこと。

## 設計判断

[docs/adr/](docs/adr/README.md)
