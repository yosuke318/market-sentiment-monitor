"""日経平均VI（ボラティリティー・インデックス）と日経平均株価の日次終値を取得する。

日経の指数公式サイトが公開している CSV（直近 3 年分の日次）を使う。
CSV は日経の著作物なので、リポジトリには保存しない。
"""

from __future__ import annotations

import csv
import io
import math
import statistics
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


def position_message(rows: list[tuple[date, float]]) -> str:
    """最新値が CSV 全体（直近 3 年ほど）の中でどの水準かを 1 行で返す。"""
    values = [v for _, v in rows]
    latest = values[-1]
    # 自分自身を含めて数えるので、最高値でも 0% にはならない
    top = math.ceil(sum(v >= latest for v in values) / len(values) * 100)
    return (
        f"水準: {rows[0][0]:%Y-%m}以降の{len(values)}営業日で上位{top}%"
        f"（中央値 {statistics.median(values):.2f}、最高 {max(values):.2f}、最低 {min(values):.2f}）"
    )


def build_vi_message(rows: list[tuple[date, float]]) -> str:
    latest_date, latest = rows[-1]
    lines = [f"📊 日経平均VI: {latest:.2f}（{latest_date:%Y-%m-%d} 終値）", ""]
    lines += [f"{name}: {latest - v:+.2f}（{v:.2f}）" for name, (_, v) in compare(rows)]
    lines += ["", position_message(rows)]
    return "\n".join(lines)


def build_percent_message(title: str, rows: list[tuple[date, float]], unit: str = "") -> str:
    """株価・株価指数用。比較は騰落率（%）で出す。"""
    latest_date, latest = rows[-1]
    lines = [f"{title}: {latest:,.0f}{unit}（{latest_date:%Y-%m-%d} 終値）", ""]
    lines += [
        f"{name}: {(latest / v - 1) * 100:+.1f}%（{v:,.0f}{unit}）"
        for name, (_, v) in compare(rows)
    ]
    return "\n".join(lines)


def build_average_message(rows: list[tuple[date, float]]) -> str:
    return build_percent_message("🗾 日経平均株価", rows, "円")


def build_sox_message(rows: list[tuple[date, float]]) -> str:
    return build_percent_message("💾 SOX指数（米国の半導体株）", rows)


def build_jp_semiconductor_message(rows: list[tuple[date, float]]) -> str:
    return (
        build_percent_message("🔌 日本の半導体株（日経半導体株指数連動ETF 200A）", rows, "円")
        + "\n\n指数の代わりに連動 ETF の価格で見ている（騰落率は指数とほぼ同じ）。"
    )


def nt_ratio(
    average_rows: list[tuple[date, float]], topix_rows: list[tuple[date, float]]
) -> list[tuple[date, float]]:
    """日経平均 ÷ TOPIX。両方に終値がある日だけ数える（休場日がずれる日があるため）。"""
    topix = dict(topix_rows)
    return [(d, v / topix[d]) for d, v in average_rows if d in topix]


def build_nt_ratio_message(rows: list[tuple[date, float]]) -> str:
    latest_date, latest = rows[-1]
    lines = [f"⚖️ NT倍率（日経平均÷TOPIX）: {latest:.2f}（{latest_date:%Y-%m-%d} 終値）", ""]
    lines += [f"{name}: {latest - v:+.2f}（{v:.2f}）" for name, (_, v) in compare(rows)]
    lines += ["", "上がるほど日経平均が値がさ株に引っ張られ、下がるほど TOPIX（市場全体）が強い。"]
    return "\n".join(lines)
