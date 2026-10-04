"""指標の推移グラフを PNG で描く。"""

from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402

DAYS = 180

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
# 2 系列を色で見分けるときの順番（青 → オレンジ）
SERIES_COLORS = ["#2a78d6", "#eb6834"]

# Fear & Greed の区分。悲観 = 赤、楽観 = 青、中立 = グレーの diverging 配色。帯は背景なので薄く敷く
FEAR_GREED_ZONES = [
    (0, 25, "Extreme Fear", "#e34948", 0.22),
    (25, 45, "Fear", "#e34948", 0.10),
    (45, 55, "Neutral", "#f0efec", 1.0),
    (55, 75, "Greed", "#2a78d6", 0.10),
    (75, 100, "Extreme Greed", "#2a78d6", 0.22),
]


def render(
    points: list[tuple[datetime, float]],
    *,
    zones: list[tuple] | None = None,
    value_format: str = "{:.0f}",
) -> bytes:
    """points は (UTC の日時, 値)。zones を渡すと y 軸はその範囲に固定し、背景に帯を敷く。"""
    since = datetime.now(timezone.utc) - timedelta(days=DAYS)
    points = [(t, y) for t, y in points if t >= since]
    xs = [t for t, _ in points]
    ys = [y for _, y in points]

    fig, ax = plt.subplots(figsize=(8, 3.6), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    if zones:
        for low, high, name, color, alpha in zones:
            ax.axhspan(low, high, color=color, alpha=alpha, linewidth=0)
            ax.text(
                1.01, (low + high) / 2, name, transform=ax.get_yaxis_transform(),
                va="center", ha="left", fontsize=8, color=MUTED,
            )
        ax.set_ylim(zones[0][0], zones[-1][1])
        ax.set_yticks(sorted({z[0] for z in zones} | {zones[-1][1]}))
    else:
        ax.grid(axis="y", color=GRID, linewidth=0.6)

    ax.plot(xs, ys, color=INK, linewidth=1.6, solid_capstyle="round")
    ax.scatter([xs[-1]], [ys[-1]], s=28, color=INK, edgecolors=SURFACE, linewidths=1.5, zorder=3)
    ax.annotate(
        value_format.format(ys[-1]), (xs[-1], ys[-1]), xytext=(6, 0), textcoords="offset points",
        ha="left", va="center", fontsize=10, fontweight="bold", color=INK,
    )

    # 最新の点と値ラベルが右端で切れないよう余白を取る
    ax.set_xlim(xs[0], xs[-1] + timedelta(days=12))
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


def render_panels(panels: list[tuple[str, list[tuple[datetime, float]], str]]) -> bytes:
    """同じ期間の複数指標を、x 軸を共有した上下の段に描く。

    panels は (見出し, 点列, 値の書式)。単位も桁も違う指標を 1 つの枠に左右 2 軸で
    重ねると、軸の取り方しだいで相関があるように見えてしまうので、段を分ける。
    """
    since = datetime.now(timezone.utc) - timedelta(days=DAYS)
    fig, axes = plt.subplots(
        len(panels), 1, sharex=True, figsize=(8, 2.4 * len(panels) + 0.4), dpi=150,
    )
    fig.patch.set_facecolor(SURFACE)
    last_x = None
    for ax, (title, points, value_format), color in zip(axes, panels, SERIES_COLORS):
        points = [(t, y) for t, y in points if t >= since]
        xs = [t for t, _ in points]
        ys = [y for _, y in points]
        last_x = max(last_x or xs[-1], xs[-1])
        ax.set_facecolor(SURFACE)
        ax.plot(xs, ys, color=color, linewidth=1.6, solid_capstyle="round")
        ax.scatter([xs[-1]], [ys[-1]], s=28, color=color, edgecolors=SURFACE, linewidths=1.5, zorder=3)
        ax.annotate(
            value_format.format(ys[-1]), (xs[-1], ys[-1]), xytext=(6, 0), textcoords="offset points",
            ha="left", va="center", fontsize=10, fontweight="bold", color=INK,
        )
        # 見出しの色見本で、どの線がどの指標かを色だけに頼らず示す
        ax.text(0, 1.04, "\u25AC ", transform=ax.transAxes, color=color, fontsize=10, va="bottom")
        ax.text(0.035, 1.04, title, transform=ax.transAxes, color=INK, fontsize=10, va="bottom")
        ax.grid(axis="both", color=GRID, linewidth=0.6)
        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
        ax.tick_params(colors=MUTED, labelsize=8, length=0)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(BASELINE)

    axes[-1].set_xlim(since, last_x + timedelta(days=16))
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator())
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=SURFACE)
    plt.close(fig)
    return buf.getvalue()
