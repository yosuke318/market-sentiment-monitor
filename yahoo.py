"""Yahoo Finance の chart API から日次終値を取得する。

日経の CSV に含まれない指数（TOPIX・SOX など）に使う。
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

API_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{}?range=3y&interval=1d"
TOPIX = "^TOPX"
# フィラデルフィア半導体株指数（米国）
SOX = "^SOX"
# 日経半導体株指数は Yahoo に無いので、連動する ETF（NEXT FUNDS 日経半導体株指数連動型）で代用する
JP_SEMICONDUCTOR_ETF = "200A.T"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)


def fetch(symbol: str, retries: int = 3) -> list[tuple[date, float]]:
    """古い順の (日付, 終値) を返す。"""
    url = API_URL.format(urllib.parse.quote(symbol))
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=20) as res:
                return parse(json.load(res))
        except Exception:
            if attempt == retries:
                raise
            time.sleep(5 * attempt)
    raise AssertionError("unreachable")


def parse(payload: dict) -> list[tuple[date, float]]:
    result = payload["chart"]["result"][0]
    # 取引所の現地時間での日付にする（東証の始値の時刻は UTC では前日にならないが、ずれに備える）
    offset = timedelta(seconds=result["meta"].get("gmtoffset", 0))
    closes = result["indicators"]["quote"][0]["close"]
    rows = []
    for ts, close in zip(result["timestamp"], closes):
        # 休場日などで終値が null の日がある
        if close is None:
            continue
        rows.append(((datetime.fromtimestamp(ts, timezone.utc) + offset).date(), float(close)))
    if not rows:
        raise ValueError("データ行がありません")
    return sorted(rows)
