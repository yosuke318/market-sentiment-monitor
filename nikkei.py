"""日経平均VI（ボラティリティー・インデックス）と日経平均株価の日次終値を取得する。

日経の指数公式サイトが公開している CSV（直近 3 年分の日次）を使う。
CSV は日経の著作物なので、リポジトリには保存しない。
"""

from __future__ import annotations

import csv
import io
import time
import urllib.request
from datetime import date, datetime, timedelta

CSV_BASE = "https://indexes.nikkei.co.jp/nkave/historical/"
VI_CSV = "nikkei_stock_average_vi_daily_jp.csv"
AVERAGE_CSV = "nikkei_stock_average_daily_jp.csv"
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


# メール本文に添える見方。Fear & Greed とは向きが逆なのでそこを先に書く
VI_GUIDE = """💡 日経平均VIの見方
・Fear & Greed とは向きが逆で、高いほど不安が強い
・日経平均オプションの価格から、今後1ヶ月に日経平均がどれだけ動くと市場が見込んでいるかを年率%で表したもの
・目安: 20前後は平常、30を超えると警戒、40超は急落時のパニック水準
・日経平均が急落すると跳ね上がり、落ち着くとゆっくり下がる傾向がある"""


def fetch(csv_name: str, retries: int = 3) -> list[tuple[date, float]]:
    """古い順の (日付, 終値) を返す。"""
    req = urllib.request.Request(CSV_BASE + csv_name, headers={"User-Agent": USER_AGENT})
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
        raise ValueError("CSV にデータ行がありません")
    return sorted(rows)


def on_or_before(rows: list[tuple[date, float]], target: date) -> tuple[date, float] | None:
    candidates = [r for r in rows if r[0] <= target]
    return candidates[-1] if candidates else None


def compare(rows: list[tuple[date, float]]) -> list[tuple[str, tuple[date, float]]]:
    """前日比・1週間前比… の比較相手。データがない期間は省く。"""
    latest_date = rows[-1][0]
    compared = [("前日比", rows[-2] if len(rows) >= 2 else None)]
    compared += [(name, on_or_before(rows, latest_date - delta)) for name, delta in COMPARISONS]
    return [(name, row) for name, row in compared if row]


def build_vi_message(rows: list[tuple[date, float]]) -> str:
    latest_date, latest = rows[-1]
    lines = [f"📊 日経平均VI: {latest:.2f}（{latest_date:%Y-%m-%d} 終値）", ""]
    lines += [f"{name}: {latest - v:+.2f}（{v:.2f}）" for name, (_, v) in compare(rows)]
    return "\n".join(lines)


def build_average_message(rows: list[tuple[date, float]]) -> str:
    latest_date, latest = rows[-1]
    lines = [f"🗾 日経平均株価: {latest:,.0f}円（{latest_date:%Y-%m-%d} 終値）", ""]
    lines += [
        f"{name}: {(latest / v - 1) * 100:+.1f}%（{v:,.0f}円）"
        for name, (_, v) in compare(rows)
    ]
    return "\n".join(lines)
