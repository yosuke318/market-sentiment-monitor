# market-sentiment-monitor

CNN の [Fear & Greed Index](https://edition.cnn.com/markets/fear-and-greed) を毎日取得して Slack / Discord に通知する。
区分（Extreme Fear / Fear / Neutral / Greed / Extreme Greed）が前回から変わった日は、変化を知らせる文面を先頭に付ける。

```
🔔 *区分が変化しました* 📈
Extreme Fear（極度の恐怖） → *Fear（恐怖）*
楽観方向へ1段階動きました。市場心理は悲観寄りです。

😨 Fear & Greed Index: *31* — Fear（恐怖）
前日比 +7.2 / 1週間前比 -5.8 / 1ヶ月前比 -14.9 / 1年前比 -23.4
（2026-10-03 08:59 JST 時点）
```

## 仕組み

- GitHub Actions が毎日 09:30 JST に `fear_greed.py` を実行（`.github/workflows/notify.yml`）
- 前回の区分・スコア・データ時刻を `state/state.json` に保存し、Actions がコミットする
- データ時刻が前回と同じ（週末・米国祝日）なら通知しない

## セットアップ

1. Slack または Discord の Incoming Webhook URL を発行する
2. リポジトリの Settings → Secrets and variables → Actions に `WEBHOOK_URL` として登録する
3. Actions タブから `Fear & Greed notify` を手動実行（Run workflow）して届くか確認する

## ローカル実行

```sh
python3 fear_greed.py                    # WEBHOOK_URL 未設定なら標準出力のみ
WEBHOOK_URL=https://... python3 fear_greed.py
python3 -m unittest discover -s tests -t .
```

ローカルで実行すると `state/state.json` が作られる。Actions 側の状態とずれるのでコミットしないこと。

## 設計判断

[docs/adr/](docs/adr/README.md)
