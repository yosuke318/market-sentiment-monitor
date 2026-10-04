"""CNN Fear & Greed Index と日経平均VI・日経平均株価を取得してメールで通知する。

前回値は state.json に保存し、Fear & Greed の区分（Extreme Fear〜Extreme Greed）が
変わったら変化を知らせる文面を先頭に付ける。推移グラフを PNG でメールに埋め込む。
"""

from __future__ import annotations

import html
import json
import os
import smtplib
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path

import nikkei

API_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
# ヘッダーなしだと 418 (I'm a teapot) が返るため、ブラウザからのアクセスに見せる
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://edition.cnn.com/",
    "Origin": "https://edition.cnn.com",
}
STATE_PATH = Path(__file__).parent / "state" / "state.json"
JST = timezone(timedelta(hours=9))

# 悲観 → 楽観の順。インデックスの差で変化の方向と段数を出す
RATINGS = ["extreme fear", "fear", "neutral", "greed", "extreme greed"]
LABELS = {
    "extreme fear": ("Extreme Fear", "極度の恐怖", "😱"),
    "fear": ("Fear", "恐怖", "😨"),
    "neutral": ("Neutral", "中立", "😐"),
    "greed": ("Greed", "強欲", "😏"),
    "extreme greed": ("Extreme Greed", "極度の強欲", "🤑"),
}
COMPARISONS = [
    ("前日比", "previous_close"),
    ("1週間前比", "previous_1_week"),
    ("1ヶ月前比", "previous_1_month"),
    ("1年前比", "previous_1_year"),
]
# 変化先の区分ごとの一言
ENTER_COMMENT = {
    "extreme fear": "市場は極度の悲観状態に入りました。",
    "fear": "市場心理は悲観寄りです。",
    "neutral": "市場心理は中立圏に戻りました。",
    "greed": "市場心理は楽観寄りです。",
    "extreme greed": "市場は極度の楽観（過熱）状態に入りました。",
}


def fetch(retries: int = 3) -> dict:
    req = urllib.request.Request(API_URL, headers=HEADERS)
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=20) as res:
                return json.load(res)
        except Exception:
            if attempt == retries:
                raise
            time.sleep(5 * attempt)
    raise AssertionError("unreachable")


def label(rating: str) -> str:
    en, ja, _ = LABELS[rating]
    return f"{en}（{ja}）"


def change_message(prev: str, curr: str) -> str:
    steps = RATINGS.index(curr) - RATINGS.index(prev)
    if steps > 0:
        arrow, direction = "📈", f"楽観方向へ{steps}段階"
    else:
        arrow, direction = "📉", f"悲観方向へ{-steps}段階"
    return (
        f"🔔 区分が変化しました {arrow}\n"
        f"{label(prev)} → {label(curr)}\n"
        f"{direction}動きました。{ENTER_COMMENT[curr]}"
    )


def build_message(data: dict, prev_rating: str | None) -> str:
    rating = data["rating"]
    score = data["score"]
    emoji = LABELS[rating][2]
    as_of = datetime.fromisoformat(data["timestamp"]).astimezone(JST)

    lines = []
    if prev_rating and prev_rating != rating:
        lines += [change_message(prev_rating, rating), ""]
    lines += [
        f"{emoji} Fear & Greed Index: {score:.0f} — {label(rating)}",
        "",
        *(
            f"{name}: {score - data[key]:+.1f}（{data[key]:.0f}）"
            for name, key in COMPARISONS
        ),
        "",
        f"（{as_of:%Y-%m-%d %H:%M} JST 時点）",
    ]
    return "\n".join(lines)


def build_subject(data: dict, prev_rating: str | None) -> str:
    rating = data["rating"]
    score = f"{data['score']:.0f}"
    if prev_rating and prev_rating != rating:
        return f"【区分変化】{LABELS[prev_rating][0]} → {LABELS[rating][0]}（Fear & Greed {score}）"
    return f"Fear & Greed {score}: {LABELS[rating][0]}"


def send_mail(
    user: str, app_password: str, to: str, subject: str, body: str,
    charts: list[tuple[str, str, bytes]],
) -> None:
    """charts は (Content-ID, 代替テキスト, PNG) のリスト。"""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to
    msg.set_content(body)
    if charts:
        # HTML 版に本文と同じテキスト＋グラフを入れ、画像は Content-ID で本文に埋め込む
        msg.add_alternative(
            '<div style="font-family:sans-serif;font-size:14px;line-height:1.6;white-space:pre-line">'
            f"{html.escape(body)}</div>"
            + "".join(
                f'<img src="cid:{cid}" alt="{html.escape(alt)}" width="640"'
                ' style="max-width:100%;height:auto;margin-top:12px;display:block">'
                for cid, alt, _ in charts
            ),
            subtype="html",
        )
        related = msg.get_payload()[1]
        for cid, _, png in charts:
            related.add_related(png, "image", "png", cid=f"<{cid}>")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as smtp:
        smtp.login(user, app_password)
        smtp.send_message(msg)


def render_charts(
    raw: dict, vi_rows: list | None, average_rows: list | None
) -> list[tuple[str, str, bytes]]:
    # グラフが描けなくても数値のメールは送る
    try:
        import chart
    except Exception as e:
        print(f"Chart skipped: {e!r}", file=sys.stderr)
        return []

    jobs = [(
        "fear-greed", "Fear & Greed Index の推移（過去6ヶ月）",
        lambda: chart.render(
            [
                (datetime.fromtimestamp(p["x"] / 1000, timezone.utc), p["y"])
                for p in raw["fear_and_greed_historical"]["data"]
            ],
            zones=chart.FEAR_GREED_ZONES,
        ),
    )]
    def to_points(rows: list) -> list:
        return [(datetime.combine(d, datetime.min.time(), timezone.utc), v) for d, v in rows]

    panels = []
    if vi_rows:
        panels.append(("Nikkei VI", to_points(vi_rows), "{:.2f}"))
    if average_rows:
        panels.append(("Nikkei 225", to_points(average_rows), "{:,.0f}"))
    if len(panels) == 2:
        jobs.append((
            "nikkei", "日経平均VI（上）と日経平均株価（下）の推移（過去6ヶ月）",
            lambda: chart.render_panels(panels),
        ))
    elif panels:
        title, points, value_format = panels[0]
        jobs.append((
            "nikkei", f"{title} の推移（過去6ヶ月）",
            lambda: chart.render(points, value_format=value_format),
        ))
    charts = []
    for cid, alt, draw in jobs:
        try:
            charts.append((cid, alt, draw()))
        except Exception as e:
            print(f"Chart {cid} skipped: {e!r}", file=sys.stderr)
    return charts


def fetch_nikkei(csv_name: str) -> list | None:
    try:
        return nikkei.fetch(csv_name)
    except Exception as e:
        print(f"Nikkei fetch failed ({csv_name}): {e!r}", file=sys.stderr)
        return None


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}


def save_state(data: dict, vi_date: str | None) -> None:
    STATE_PATH.parent.mkdir(exist_ok=True)
    state = {k: data[k] for k in ("rating", "score", "timestamp")}
    state["nikkei_vi_date"] = vi_date
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")


def main() -> int:
    raw = fetch()
    data = raw["fear_and_greed"]
    state = load_state()

    # 日経のデータが取れなくても Fear & Greed は送る
    vi_rows = fetch_nikkei(nikkei.VI_CSV)
    average_rows = fetch_nikkei(nikkei.AVERAGE_CSV)
    vi_date = vi_rows[-1][0].isoformat() if vi_rows else state.get("nikkei_vi_date")

    # 週末・祝日はどちらも前回と同じデータなので通知しない（FORCE=1 で手動テスト時は送る）
    is_new = state.get("timestamp") != data["timestamp"] or state.get("nikkei_vi_date") != vi_date
    if not is_new and os.environ.get("FORCE") != "1":
        print(f"No new data since {data['timestamp']} / Nikkei VI {vi_date}; skipped.")
        return 0

    subject = build_subject(data, state.get("rating"))
    body = build_message(data, state.get("rating")) + "\n\n" + "─" * 16 + "\n\n"
    if vi_rows:
        subject += f" / 日経VI {vi_rows[-1][1]:.1f}"
        body += nikkei.build_vi_message(vi_rows)
    else:
        body += "⚠️ 日経平均VIは取得に失敗しました。"
    body += "\n\n"
    if average_rows:
        body += nikkei.build_average_message(average_rows)
    else:
        body += "⚠️ 日経平均株価は取得に失敗しました。"
    body += "\n\n" + nikkei.VI_GUIDE
    print(subject, body, sep="\n\n")

    user = os.environ.get("MAIL_USER", "").strip()
    # Google の画面からコピーすると区切りの空白（NBSP を含む）が混ざるので除く
    app_password = "".join(os.environ.get("MAIL_APP_PASSWORD", "").split())
    if user and app_password:
        # 送り先の指定がなければ自分宛て
        send_mail(
            user, app_password, os.environ.get("MAIL_TO") or user, subject, body,
            render_charts(raw, vi_rows, average_rows),
        )
    else:
        print("MAIL_USER / MAIL_APP_PASSWORD are not set; mail skipped.", file=sys.stderr)

    save_state(data, vi_date)
    return 0


if __name__ == "__main__":
    sys.exit(main())
