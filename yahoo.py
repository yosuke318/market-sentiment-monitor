"""Yahoo Finance から日次終値を取得する。

日経の CSV に含まれない指数（TOPIX・SOX など）に使う。
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import date, datetime

# TOPIX の指数そのもの（^TOPX）は Yahoo に無い（404）ので、連動する ETF（NEXT FUNDS TOPIX 連動型）で代用する
TOPIX = "1306.T"
# フィラデルフィア半導体株指数（米国）
SOX = "^SOX"
# 日経半導体株指数は Yahoo に無いので、連動する ETF（NEXT FUNDS 日経半導体株指数連動型）で代用する
JP_SEMICONDUCTOR_ETF = "200A.T"


def fetch(symbol: str) -> list[tuple[date, float]]:
    """古い順の (日付, 終値) を返す。

    chart API を urllib で直接叩くと、GitHub Actions からは毎回 429 で弾かれた。
    yfinance はブラウザの TLS の指紋を真似て（curl_cffi）接続するので、それを使う。
    429 は待っても解けないので、ここではリトライしない。
    """
    import yfinance  # 読み込みが重く、テストでは不要なのでここで読む

    history = yfinance.Ticker(symbol).history(
        period="3y", interval="1d", auto_adjust=False, raise_errors=True
    )
    return parse(history["Close"].items())


def parse(closes: Iterable[tuple[datetime, float | None]]) -> list[tuple[date, float]]:
    """(取引所の現地時間の日時, 終値) の並びを、古い順の (日付, 終値) にする。"""
    rows = [
        (ts.date(), float(close))
        for ts, close in closes
        # 休場日などで終値が欠けている日がある
        if close is not None and not math.isnan(close)
    ]
    if not rows:
        raise ValueError("データ行がありません")
    return sorted(rows)
