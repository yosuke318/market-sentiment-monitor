"""Fear & Greed Index の推移グラフを PNG で描く。"""

from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

DAYS = 180

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"

# 悲観 = 赤、楽観 = 青、中立 = グレーの diverging 配色。帯は背景なので薄く敷く
ZONES = [
    (0, 25, "Extreme Fear", "#e34948", 0.22),
    (25, 45, "Fear", "#e34948", 0.10),
    (45, 55, "Neutral", "#f0efec", 1.0),
    (55, 75, "Greed", "#2a78d6", 0.10),
    (75, 100, "Extreme Greed", "#2a78d6", 0.22),
]


def render(historical: list[dict]) -> bytes:
    """historical は API の fear_and_greed_historical.data（x はミリ秒の UNIX 時刻）"""
    since = datetime.now(timezone.utc) - timedelta(days=DAYS)
    points = [
        (datetime.fromtimestamp(p["x"] / 1000, timezone.utc), p["y"])
        for p in historical
    ]
    points = [(t, y) for t, y in points if t >= since]
    xs = [t for t, _ in points]
    ys = [y for _, y in points]

    fig, ax = plt.subplots(figsize=(8, 3.6), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    for low, high, name, color, alpha in ZONES:
        ax.axhspan(low, high, color=color, alpha=alpha, linewidth=0)
        ax.text(
            1.01, (low + high) / 2, name, transform=ax.get_yaxis_transform(),
            va="center", ha="left", fontsize=8, color=MUTED,
        )

    ax.plot(xs, ys, color=INK, linewidth=1.6, solid_capstyle="round")
    ax.scatter([xs[-1]], [ys[-1]], s=28, color=INK, edgecolors=SURFACE, linewidths=1.5, zorder=3)
    ax.annotate(
        f"{ys[-1]:.0f}", (xs[-1], ys[-1]), xytext=(6, 0), textcoords="offset points",
        ha="left", va="center", fontsize=10, fontweight="bold", color=INK,
    )

    ax.set_ylim(0, 100)
    # 最新の点と値ラベルが右端で切れないよう余白を取る
    ax.set_xlim(xs[0], xs[-1] + timedelta(days=9))
    ax.set_yticks([0, 25, 45, 55, 75, 100])
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.tick_params(colors=MUTED, labelsize=8, length=0)
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=SURFACE)
    plt.close(fig)
    return buf.getvalue()
