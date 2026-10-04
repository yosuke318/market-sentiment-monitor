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


def render_dual_axis(
    left: tuple[str, list[tuple[datetime, float]], str],
    right: tuple[str, list[tuple[datetime, float]], str],
    days: int,
    *,
    right_zones: list[tuple] | None = None,
) -> bytes:
    """2 つの指標を 1 つの枠に重ね、左右それぞれの y 軸で描く。

    left / right は (凡例名, 点列, 値の書式)。左右の目盛りの範囲しだいで線の重なり方は
    いくらでも変わって見えるので、範囲は手で合わせず各データの最小〜最大から自動で取る。
    right_zones を渡すと、右軸はその範囲に固定して背景に区分の帯を敷く（Fear & Greed 用）。
    帯と同系色にならないよう、そのとき右の線は黒にして塗りつぶさない。
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    fig, ax_left = plt.subplots(figsize=(8, 4.2), dpi=150)
    ax_right = ax_left.twinx()
    fig.patch.set_facecolor(SURFACE)
    ax_left.set_facecolor(SURFACE)

    # 右（VI）を奥に、左（株価）を手前に描く
    ax_right.set_zorder(1)
    ax_left.set_zorder(2)
    ax_left.patch.set_visible(False)

    handles = []
    last_x = None
    if right_zones:
        for low, high, zone_name, zone_color, alpha in right_zones:
            # 左軸の線の背景にもなるので、単独グラフより薄くする
            ax_right.axhspan(low, high, color=zone_color, alpha=alpha * 0.5, linewidth=0)
            ax_right.text(
                1.09, (low + high) / 2, zone_name, transform=ax_right.get_yaxis_transform(),
                va="center", ha="left", fontsize=7, color=MUTED,
            )
        ax_right.set_ylim(right_zones[0][0], right_zones[-1][1])
        ax_right.set_yticks(sorted({z[0] for z in right_zones} | {right_zones[-1][1]}))

    for ax, (name, points, value_format), color, fill in (
        (ax_left, left, SERIES_COLORS[1], False),
        (ax_right, right, INK if right_zones else SERIES_COLORS[0], not right_zones),
    ):
        points = [(t, y) for t, y in points if t >= since]
        xs = [t for t, _ in points]
        ys = [y for _, y in points]
        last_x = max(last_x or xs[-1], xs[-1])
        (line,) = ax.plot(xs, ys, color=color, linewidth=1.4, solid_capstyle="round", label=name)
        if fill:
            ax.fill_between(xs, ys, min(ys), color=color, alpha=0.08, linewidth=0)
        ax.scatter([xs[-1]], [ys[-1]], s=24, color=color, edgecolors=SURFACE, linewidths=1.5, zorder=3)
        ax.annotate(
            value_format.format(ys[-1]), (xs[-1], ys[-1]), xytext=(6, 0), textcoords="offset points",
            ha="left", va="center", fontsize=9, fontweight="bold", color=INK,
        )
        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
        ax.tick_params(colors=MUTED, labelsize=8, length=0)
        for side in ax.spines:
            ax.spines[side].set_visible(False)
        handles.append(line)

    # 目盛りの数値だけでは左右どちらの軸か分からないので、軸名を付ける
    ax_left.set_ylabel(f"{left[0]}  (left)", color=MUTED, fontsize=8)
    ax_right.set_ylabel(f"{right[0]}  (right)", color=MUTED, fontsize=8)
    # 区分の帯があるときは横の基準線を帯だけにし、左軸の横グリッドと混ざらないようにする
    ax_left.grid(axis="x" if right_zones else "both", color=GRID, linewidth=0.6)
    ax_left.spines["bottom"].set_visible(True)
    ax_left.spines["bottom"].set_color(BASELINE)
    ax_left.legend(
        handles=handles, loc="upper left", frameon=False, fontsize=9, labelcolor=INK,
        bbox_to_anchor=(0, 1.12), ncol=2,
    )

    ax_left.set_xlim(since, last_x + timedelta(days=days // 15))
    ax_left.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax_left.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    fig.tight_layout()
    buf = io.BytesIO()
    # 枠の外に置いた区分名が切れないよう、余白を含めて書き出す
    fig.savefig(buf, format="png", facecolor=SURFACE, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    return buf.getvalue()
