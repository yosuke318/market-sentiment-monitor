"""CNN Fear & Greed Index を取得して Webhook に通知する。

前回値は state.json に保存し、区分（Extreme Fear〜Extreme Greed）が変わったら
変化を知らせる文面を先頭に付ける。標準ライブラリのみで動く。
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

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
                return json.load(res)["fear_and_greed"]
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
        f"🔔 *区分が変化しました* {arrow}\n"
        f"{label(prev)} → *{label(curr)}*\n"
        f"{direction}動きました。{ENTER_COMMENT[curr]}"
    )


def build_message(data: dict, prev_rating: str | None) -> str:
    rating = data["rating"]
    score = data["score"]
    emoji = LABELS[rating][2]
    as_of = datetime.fromisoformat(data["timestamp"]).astimezone(JST)

    def diff(key: str) -> str:
        return f"{score - data[key]:+.1f}"

    lines = []
    if prev_rating and prev_rating != rating:
        lines += [change_message(prev_rating, rating), ""]
    lines += [
        f"{emoji} Fear & Greed Index: *{score:.0f}* — {label(rating)}",
        f"前日比 {diff('previous_close')} / 1週間前比 {diff('previous_1_week')}"
        f" / 1ヶ月前比 {diff('previous_1_month')} / 1年前比 {diff('previous_1_year')}",
        f"（{as_of:%Y-%m-%d %H:%M} JST 時点）",
    ]
    return "\n".join(lines)


def notify(webhook_url: str, text: str) -> None:
    # Discord は content、Slack は text を受け取る
    host = urlparse(webhook_url).hostname or ""
    is_discord = host.endswith("discord.com") or host.endswith("discordapp.com")
    payload = {"content": text} if is_discord else {"text": text}
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=20).close()


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}


def save_state(data: dict) -> None:
    STATE_PATH.parent.mkdir(exist_ok=True)
    state = {k: data[k] for k in ("rating", "score", "timestamp")}
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")


def main() -> int:
    data = fetch()
    state = load_state()

    # 週末・祝日は前回と同じデータが返るので通知しない
    if state.get("timestamp") == data["timestamp"]:
        print(f"No new data since {data['timestamp']}; skipped.")
        return 0

    text = build_message(data, state.get("rating"))
    print(text)

    webhook_url = os.environ.get("WEBHOOK_URL")
    if webhook_url:
        notify(webhook_url, text)
    else:
        print("WEBHOOK_URL is not set; notification skipped.", file=sys.stderr)

    save_state(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
