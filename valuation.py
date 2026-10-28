"""日経平均の PER と日本の 10 年債利回りを取得し、イールドスプレッドを出す。

- PER: 日経の指数公式サイトのヒストリカルデータ（日次投資指標）の表。CSV は配布されていないので HTML から読む
- 10 年債利回り: 財務省の国債金利情報 CSV
どちらも日経・財務省の公表値をそのまま使い、リポジトリには保存しない。
"""

from __future__ import annotations

import re
import time
import urllib.request
from datetime import date

import nikkei

PER_CURRENT_URL = "https://indexes.nikkei.co.jp/nkave/archives/data?list=per"
PER_MONTH_URL = "https://indexes.nikkei.co.jp/nkave/statistics/dataload?list=per&year={year}&month={month}"
JGB_CURRENT_URL = "https://www.mof.go.jp/jgbs/reference/interest_rate/jgbcm.csv"
# 前月末までの全期間（1974 年〜）。当月分の CSV は月初に空になりうるので、こちらで補う
JGB_ALL_URL = "https://www.mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv"
# 和暦の元年の前年（S1 = 1926 年）
ERA_BASE = {"S": 1925, "H": 1988, "R": 2018}


def _get(url: str, retries: int = 3) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": nikkei.USER_AGENT})
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return res.read()
        except Exception:
            if attempt == retries:
                raise
            time.sleep(5 * attempt)
    raise AssertionError("unreachable")


def parse_per_html(html: str) -> list[tuple[date, float, float]]:
    """表の行（日付 | 加重平均(倍) | 指数ベース(倍)）を古い順の (日付, 加重平均, 指数ベース) にする。"""
    rows = []
    for tr in re.findall(r"<tr.*?</tr>", html, re.S):
        cells = [re.sub(r"<[^>]+>|\s+", "", c) for c in re.findall(r"<td.*?</td>", tr, re.S)]
        m = re.fullmatch(r"(\d{4})\.(\d{2})\.(\d{2})", cells[0]) if len(cells) >= 3 else None
        if not m:
            continue
        try:
            rows.append((date(*map(int, m.groups())), float(cells[1]), float(cells[2])))
        except ValueError:
            continue
    return sorted(rows)


def per_months(today: date) -> list[tuple[int, int]]:
    """比較（前日比〜1年前比）に要る過去の月。1年前比は月をまたぐことがあるので前後も取る。"""
    def shift(n: int) -> tuple[int, int]:
        total = today.year * 12 + today.month - 1 - n
        return total // 12, total % 12 + 1

    return [shift(n) for n in (1, 2, 12, 13)]


def fetch_per(today: date) -> list[tuple[date, float, float]]:
    """当月は必須、過去の月は取れた分だけ使う（比較の一部が欠けるだけで済むため）。"""
    rows = parse_per_html(_get(PER_CURRENT_URL).decode("utf-8"))
    for year, month in per_months(today):
        try:
            rows += parse_per_html(_get(PER_MONTH_URL.format(year=year, month=month), retries=1).decode("utf-8"))
        except Exception:
            continue
    rows = sorted(set(rows))
    if not rows:
        raise ValueError("PER の表にデータ行がありません")
    return rows


def parse_era_date(text: str) -> date | None:
    m = re.fullmatch(r"([SHR])(\d+)\.(\d+)\.(\d+)", text.strip())
    if not m:
        return None
    era, year, month, day = m.groups()
    return date(ERA_BASE[era] + int(year), int(month), int(day))


def parse_jgb_csv(text: str, maturity: str = "10年") -> list[tuple[date, float]]:
    """国債金利情報 CSV から、指定した年限の (日付, 利回り %) を古い順に返す。欠損（-）は飛ばす。"""
    rows = []
    col = None
    for line in text.splitlines():
        cells = line.split(",")
        if cells and cells[0] == "基準日":
            col = cells.index(maturity)
            continue
        d = parse_era_date(cells[0]) if cells else None
        if d is None or col is None or col >= len(cells):
            continue
        try:
            rows.append((d, float(cells[col])))
        except ValueError:
            continue
    return sorted(rows)


def fetch_jgb10() -> list[tuple[date, float]]:
    rows = dict(parse_jgb_csv(_get(JGB_ALL_URL).decode("cp932")))
    try:
        rows.update(parse_jgb_csv(_get(JGB_CURRENT_URL).decode("cp932")))
    except Exception:
        # 当月分が取れなくても、前月末までで出す
        pass
    if not rows:
        raise ValueError("国債金利 CSV にデータ行がありません")
    return sorted(rows.items())


def yield_spread(
    per_rows: list[tuple[date, float]], jgb_rows: list[tuple[date, float]]
) -> list[tuple[date, float]]:
    """株式益回り（100 ÷ PER, %）− 10 年債利回り（%）。

    利回りは PER と同じ日がなければ、その日以前で最も近い日を使う（財務省の公表が 1 日遅れるため）。
    """
    spread = []
    for d, per in per_rows:
        jgb = nikkei.on_or_before(jgb_rows, d)
        if jgb:
            spread.append((d, 100 / per - jgb[1]))
    return spread


def build_message(
    per_rows: list[tuple[date, float, float]] | None, jgb_rows: list[tuple[date, float]] | None
) -> str:
    lines = []
    if per_rows:
        weighted = [(d, w) for d, w, _ in per_rows]
        latest_date, w, ix = per_rows[-1]
        lines += [
            f"💹 日経平均PER: {w:.2f}倍（加重平均）/ {ix:.2f}倍（指数ベース）（{latest_date:%Y-%m-%d}）",
            "",
            *(f"{name}: {w - v:+.2f}（{v:.2f}）" for name, (_, v) in nikkei.compare(weighted)),
        ]
    else:
        lines.append("⚠️ 日経平均のPERは取得に失敗しました。")
    lines.append("")
    if jgb_rows:
        jgb_date, jgb = jgb_rows[-1]
        lines += [
            f"🏦 日本10年債利回り: {jgb:.3f}%（{jgb_date:%Y-%m-%d}）",
            "",
            *(f"{name}: {jgb - v:+.3f}pt（{v:.3f}%）" for name, (_, v) in nikkei.compare(jgb_rows)),
        ]
    else:
        lines.append("⚠️ 日本10年債利回りは取得に失敗しました。")
    if per_rows and jgb_rows:
        spread = yield_spread([(d, w) for d, w, _ in per_rows], jgb_rows)
        index_spread = yield_spread([(d, ix) for d, _, ix in per_rows], jgb_rows)
        if spread:
            s_date, s = spread[-1]
            used_jgb = nikkei.on_or_before(jgb_rows, s_date)
            lines += [
                "",
                f"📐 イールドスプレッド（株式益回り−10年債利回り）: {s:+.2f}pt"
                f"（PER {s_date:%m/%d}・利回り {used_jgb[0]:%m/%d}）",
                "",
                *(f"{name}: {s - v:+.2f}pt（{v:+.2f}）" for name, (_, v) in nikkei.compare(spread)),
                "",
                f"株式益回りは加重平均PERから（指数ベースPERでは {index_spread[-1][1]:+.2f}pt）。"
                "大きいほど株が債券より割安で、縮むほど割高。",
            ]
    return "\n".join(lines)
