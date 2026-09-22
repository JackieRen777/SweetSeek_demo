"""Plot SweetSeek classification performance on the independent test set."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import MultipleLocator, FormatStrFormatter


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "results"
FONT_PATH = Path("/System/Library/Fonts/Supplemental/Times New Roman.ttf")
FONT_BOLD_PATH = Path(
    "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf"
)


def main() -> None:
    if not FONT_PATH.exists() or not FONT_BOLD_PATH.exists():
        raise FileNotFoundError("Times New Roman is not available on this system.")

    regular = font_manager.FontProperties(fname=FONT_PATH)
    bold = font_manager.FontProperties(fname=FONT_BOLD_PATH)

    metrics = ["Accuracy", "F1 score", "ROC-AUC"]
    values = [0.915, 0.837, 0.976]
    colors = ["#3B6FA1", "#D9843B", "#3E8B75"]

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    bars = ax.bar(
        metrics,
        values,
        width=0.58,
        color=colors,
        edgecolor="#222222",
        linewidth=0.8,
        zorder=3,
    )

    ax.set_title(
        "Performance on the Independent Test Set",
        fontproperties=bold,
        fontsize=16,
        pad=14,
    )
    ax.set_ylabel("Score", fontproperties=regular, fontsize=13)
    ax.set_ylim(0, 1.08)
    ax.yaxis.set_major_locator(MultipleLocator(0.2))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))
    ax.grid(axis="y", color="#D7D7D7", linewidth=0.7, linestyle="--", zorder=0)
    ax.set_axisbelow(True)

    for tick in ax.get_xticklabels() + ax.get_yticklabels():
        tick.set_fontproperties(regular)
        tick.set_fontsize(12)

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.025,
            f"{value:.3f}",
            ha="center",
            va="bottom",
            fontproperties=bold,
            fontsize=12,
            color="#222222",
        )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.9)
    ax.spines["bottom"].set_linewidth(0.9)
    ax.tick_params(axis="both", width=0.8, length=4)

    fig.tight_layout()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        OUTPUT_DIR / "independent_test_metrics.png",
        dpi=600,
        bbox_inches="tight",
        facecolor="white",
    )
    fig.savefig(
        OUTPUT_DIR / "independent_test_metrics.pdf",
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)


if __name__ == "__main__":
    main()
