# 0013. Yahoo Finance の取得は yfinance を使う

- ステータス: Accepted
- 日付: 2026-10-25
- 見直し対象: 0010 の「yfinance パッケージは使わない」

## 背景

0010・0012 では、Yahoo Finance の chart API（`query1.finance.yahoo.com/v8/finance/chart/...`）を `urllib` で直接叩いていた。GitHub Actions の実行では、TOPIX・SOX・ETF 200A のすべてが毎回 `HTTP 429 Too Many Requests` で失敗していた。1 日 3 回しか呼んでいないので、本当の回数超過ではない。

Yahoo はボットらしいアクセスを 429 で弾いている。GitHub Actions はデータセンターの IP から接続し、`urllib` の TLS の挨拶の仕方（指紋）はブラウザと違う。User-Agent をブラウザにしても見抜かれる。

## 決定

- 取得は yfinance（`yfinance>=1.7,<2`）経由にする。yfinance は curl_cffi で Chrome の TLS の指紋を真似て接続し、cookie と crumb も自前で取る
- `history(period="3y", interval="1d", auto_adjust=False, raise_errors=True)` の終値を使う。日付は取引所の現地時間の日付にする
- 429 は待っても解けないので、リトライしない。以前は 5 秒・10 秒待って再試行していて、1 銘柄あたり約 15 秒を無駄にしていた

## 選ばなかった選択肢

- **ホストや User-Agent を変える（`query2` など）**: 一時的に通ることはあっても、すぐまた弾かれやすい
- **取得元を Yahoo 以外にする（Nasdaq の API、stooq など）**: どれもクラウドの IP を弾くことがあり、今より確実とは言えない。ETF 200A は代わりの取得元が見つかりにくい

## 影響

- 依存が増える（pandas・curl_cffi ほか）。`pip install` は Actions のキャッシュが効くので、実行時間への影響は小さい
- yfinance も非公式で、Yahoo 側の対策しだいで再び弾かれうる。その場合も、失敗した銘柄だけを省いて残りは送る（0010・0012 と同じ）
