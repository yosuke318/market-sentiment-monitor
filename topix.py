"""TOPIX の日次終値を取得する。

日経の CSV には TOPIX が含まれないので、Yahoo Finance の chart API（ティッカー ^TOPX）を使う。
"""

from __future__ import annotations

import json
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone

API_URL = "https://query1.finance.yahoo.com/v8/finance/chart/%5ETOPX?range=3y&interval=1d"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)


def fetch(retries: int = 3) -> list[tuple[date, float]]:
    """古い順の (日付, 終値) を返す。"""
    req = urllib.request.Request(API_URL, headers={"User-Agent": USER_AGENT})
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
        raise ValueError("TOPIX のデータ行がありません")
    return sorted(rows)
