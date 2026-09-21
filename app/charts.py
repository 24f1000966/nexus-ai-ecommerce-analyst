"""
Matplotlib chart styling shared across the app — thin marks, recessive
gridlines, direct value labels, and the validated categorical/status palette
from the dataviz skill, so every chart in the demo reads as one system.
"""
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"
SERIES_1 = "#2a78d6"   # blue
SERIES_2 = "#eb6834"   # orange
STATUS_CRITICAL = "#d03b3b"
STATUS_GOOD = "#0ca30c"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "text.color": INK_PRIMARY,
    "axes.edgecolor": BASELINE,
    "axes.labelcolor": INK_SECONDARY,
    "xtick.color": INK_MUTED,
    "ytick.color": INK_MUTED,
})


def _clean_axes(ax, hide_y=False):
    ax.set_facecolor(SURFACE)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.spines["bottom"].set_linewidth(1)
    ax.yaxis.grid(True, color=GRIDLINE, linewidth=1, zorder=0)
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)
    if hide_y:
        ax.set_yticks([])


def bar_chart(df, x, y, title=None, highlight_negative=False, value_fmt="{:,.0f}"):
    fig, ax = plt.subplots(figsize=(8, 3.6), facecolor=SURFACE)
    _clean_axes(ax)

    values = df[y]
    colors = [STATUS_CRITICAL if (highlight_negative and v < 0) else SERIES_1 for v in values]
    bars = ax.bar(df[x].astype(str), values, color=colors, width=0.6, zorder=3)

    for bar, v in zip(bars, values):
        ax.annotate(value_fmt.format(v),
                    (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    ha="center", va="bottom" if v >= 0 else "top",
                    fontsize=8.5, color=INK_SECONDARY, xytext=(0, 3),
                    textcoords="offset points")

    ax.set_xlabel("")
    ax.set_ylabel(y.replace("_", " ").title())
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    plt.xticks(rotation=25, ha="right")
    if title:
        ax.set_title(title, fontsize=12, color=INK_PRIMARY, loc="left", pad=10)
    fig.tight_layout()
    return fig


def line_chart(df, x, y, title=None, value_fmt="{:,.0f}"):
    fig, ax = plt.subplots(figsize=(8, 3.6), facecolor=SURFACE)
    _clean_axes(ax)

    ax.plot(df[x].astype(str), df[y], color=SERIES_1, linewidth=2,
            marker="o", markersize=8, markerfacecolor=SERIES_1,
            markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=3)

    last_x, last_y = df[x].iloc[-1], df[y].iloc[-1]
    ax.annotate(value_fmt.format(last_y), (str(last_x), last_y),
                xytext=(6, 6), textcoords="offset points",
                fontsize=9, color=INK_PRIMARY, fontweight="bold")

    ax.set_xlabel("")
    ax.set_ylabel(y.replace("_", " ").title())
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    plt.xticks(rotation=25, ha="right")
    if title:
        ax.set_title(title, fontsize=12, color=INK_PRIMARY, loc="left", pad=10)
    fig.tight_layout()
    return fig
