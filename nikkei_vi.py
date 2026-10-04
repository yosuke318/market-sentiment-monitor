"""日経平均ボラティリティー・インデックス（日経平均VI）の日次終値を取得する。

日経の指数公式サイトが公開している CSV（直近 3 年分の日次）を使う。
CSV は日経の著作物なので、リポジトリには保存しない。
"""

from __future__ import annotations

import csv
import io
import time
import urllib.request
from datetime import date, datetime, timedelta

CSV_URL = "https://indexes.nikkei.co.jp/nkave/historical/nikkei_stock_average_vi_daily_jp.csv"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)

# 前営業日以外は「その日以前で最も近い営業日」と比べる
COMPARISONS = [
    ("1週間前比", timedelta(days=7)),
    ("1ヶ月前比", timedelta(days=30)),
    ("1年前比", timedelta(days=365)),
]


def fetch(retries: int = 3) -> list[tuple[date, float]]:
    """古い順の (日付, 終値) を返す。"""
    req = urllib.request.Request(CSV_URL, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=20) as res:
                return parse(res.read().decode("cp932"))
        except Exception:
            if attempt == retries:
                raise
            time.sleep(5 * attempt)
    raise AssertionError("unreachable")


def parse(text: str) -> list[tuple[date, float]]:
    rows = []
    # 1 行目はヘッダー、最終行は著作権表示なので日付として読めない行は飛ばす
    for row in csv.reader(io.StringIO(text)):
        try:
            rows.append((datetime.strptime(row[0], "%Y/%m/%d").date(), float(row[1])))
        except (ValueError, IndexError):
            continue
    if not rows:
        raise ValueError("日経平均VIの CSV にデータ行がありません")
    return sorted(rows)


def on_or_before(rows: list[tuple[date, float]], target: date) -> tuple[date, float] | None:
    candidates = [r for r in rows if r[0] <= target]
    return candidates[-1] if candidates else None


def build_message(rows: list[tuple[date, float]]) -> str:
    latest_date, latest = rows[-1]
    compared = [("前日比", rows[-2] if len(rows) >= 2 else None)]
    compared += [(name, on_or_before(rows, latest_date - delta)) for name, delta in COMPARISONS]
    lines = [f"📊 日経平均VI: {latest:.2f}（{latest_date:%Y-%m-%d} 終値）", ""]
    lines += [
        f"{name}: {latest - row[1]:+.2f}（{row[1]:.2f}）"
        for name, row in compared
        if row
    ]
    return "\n".join(lines)
