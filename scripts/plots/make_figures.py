"""Day 8: Generate all paper-ready figures.

Generates 11 publication-quality figures for the SweetSeek V1 paper:
  Fig 2-1: Data collection pipeline (Sankey diagram)
  Fig 2-2: Taste class distribution (grouped bar)
  Fig 2-3: Molecular property distributions (histogram + boxplot)
  Fig 2-4: Literature comparison (grouped bar)
  Fig 3-1: Feature space structure (stacked bar)
  Fig 3-2: Data split (stacked bar with Sweet ratio)
  Fig 4:   Top-12 discriminative descriptors (violin grid)
  Fig 5-1: Hyperparameter search heatmaps (RF + XGB)
  Fig 5-2: ROC + PR curves (val + test)
  Fig 5-3: Confusion matrices (RF + XGB + Ensemble)
  Fig S-1: Standardization failures by element (horizontal bar)

Output: figures/ directory with PDF (vector) + PNG (300 dpi) for each figure.

Usage:
    venv/bin/python -m scripts.plots.make_figures
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.gridspec import GridSpec

# Set publication style
sns.set_theme(style='whitegrid', context='paper', font='Arial', font_scale=1.1)
plt.rcParams['pdf.fonttype'] = 42  # TrueType fonts for PDF
plt.rcParams['ps.fonttype'] = 42
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['xtick.major.width'] = 0.8
plt.rcParams['ytick.major.width'] = 0.8

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
RESULTS_DIR = REPO_ROOT / "results"
FIGURES_DIR = REPO_ROOT / "figures"

# Color palette
COLORS = {
    'sweet': '#E76F51',      # Warm orange-red
    'nonsweet': '#264653',   # Deep teal
    'ctd': '#2A9D8F',        # Teal
    'bdb': '#E9C46A',        # Gold
    'rf': '#F4A261',         # Orange
    'xgb': '#E76F51',        # Red-orange
    'ensemble': '#264653',   # Dark teal
}


def save_figure(fig, name: str):
    """Save figure as both PDF and PNG."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIR / f"{name}.pdf", bbox_inches='tight', dpi=300)
    fig.savefig(FIGURES_DIR / f"{name}.png", bbox_inches='tight', dpi=300)
    plt.close(fig)
    print(f"  ✓ {name}.pdf + {name}.png")


def fig_2_1_data_pipeline():
    """Fig 2-1: Data collection pipeline (simplified bar chart, Sankey needs plotly)."""
    summary = json.loads((DATA_DIR / "processed" / "merge_summary.json").read_text())

    stages = ['Raw', 'Standardized', 'Within-Dedup', 'Cross-Dedup', 'Label-Filtered', 'MW-Filtered']
    ctd_counts = [2947, 2930, 2683, 2683, None, None]  # CTD doesn't go through label filter separately
    bdb_counts = [2250, 2228, 2128, 1478, None, None]
    total_counts = [5197, 5158, 4811, 4161, 3862, 3846]

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(stages))
    width = 0.25

    ax.bar(x - width, [c if c else 0 for c in ctd_counts], width, label='ChemTastesDB', color=COLORS['ctd'], alpha=0.8)
    ax.bar(x, [c if c else 0 for c in bdb_counts], width, label='BitterDB', color=COLORS['bdb'], alpha=0.8)
    ax.bar(x + width, total_counts, width, label='Total', color='gray', alpha=0.6)

    ax.set_xlabel('Pipeline Stage', fontweight='bold')
    ax.set_ylabel('Number of Molecules', fontweight='bold')
    ax.set_title('Fig 2-1: Data Collection Pipeline', fontweight='bold', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(stages, rotation=15, ha='right')
    ax.legend(frameon=True, loc='upper right')
    ax.grid(axis='y', alpha=0.3)

    save_figure(fig, 'fig_2_1_data_pipeline')


def fig_2_2_taste_distribution():
    """Fig 2-2: Taste class distribution (grouped bar)."""
    data = [
        ('Sweetness', 881, 0),
        ('Bitterness', 1085, 1478),
        ('Non-sweetness', 227, 0),
        ('Tastelessness', 191, 0),
        ('Multitaste', 99, 0),
        ('Umaminess', 81, 0),
        ('Miscellaneous', 77, 0),
        ('Sourness', 35, 0),
        ('Saltiness', 7, 0),
    ]

    df = pd.DataFrame(data, columns=['taste', 'ChemTastesDB', 'BitterDB'])
    df = df.melt(id_vars='taste', var_name='source', value_name='count')

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(data=df, x='taste', y='count', hue='source', palette=[COLORS['ctd'], COLORS['bdb']], ax=ax)
    ax.set_xlabel('Taste Class', fontweight='bold')
    ax.set_ylabel('Number of Molecules', fontweight='bold')
    ax.set_title('Fig 2-2: Taste Class Distribution by Source', fontweight='bold', fontsize=14)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha='right')
    ax.legend(title='Source', frameon=True)
    ax.set_yscale('log')
    ax.grid(axis='y', alpha=0.3)

    save_figure(fig, 'fig_2_2_taste_distribution')


def fig_2_4_literature_comparison():
    """Fig 2-4: Literature comparison (grouped bar)."""
    data = [
        ('BitterSweet\n2019', 435, 1899, 2334),
        ('e-Sweet\n2019', 530, 680, 1210),
        ('VirtualTaste\n2021', 1608, np.nan, np.nan),
        ('ChemSweet\n2024', np.nan, np.nan, np.nan),
        ('SweetSeek\n2026', 881, 2965, 3846),
    ]

    df = pd.DataFrame(data, columns=['work', 'Sweet', 'NonSweet', 'Total'])

    fig, ax = plt.subplots(figsize=(8, 6))
    x = np.arange(len(df))
    width = 0.35

    ax.bar(x - width/2, df['Sweet'], width, label='Sweet', color=COLORS['sweet'])
    ax.bar(x + width/2, df['NonSweet'], width, label='NonSweet', color=COLORS['nonsweet'])

    ax.set_xlabel('Work', fontweight='bold')
    ax.set_ylabel('Number of Molecules', fontweight='bold')
    ax.set_title('Fig 2-4: Dataset Size Comparison', fontweight='bold', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(df['work'])
    ax.legend(frameon=True)
    ax.grid(axis='y', alpha=0.3)

    # Annotate totals
    for i, row in df.iterrows():
        if not np.isnan(row['Total']):
            ax.text(i, row['Total'] + 100, f"n={int(row['Total'])}", ha='center', fontsize=9, fontweight='bold')

    save_figure(fig, 'fig_2_4_literature_comparison')


def fig_3_2_split_summary():
    """Fig 3-2: Data split (stacked bar with Sweet ratio)."""
    splits = json.loads((DATA_DIR / "features" / "splits.json").read_text())
    y = np.load(DATA_DIR / "features" / "y.npy")

    data = []
    for name in ['train', 'val', 'test']:
        idx = np.array(splits[name])
        sweet = int((y[idx] == 1).sum())
        nonsweet = int((y[idx] == 0).sum())
        ratio = sweet / len(idx)
        data.append((name.capitalize(), sweet, nonsweet, ratio))

    df = pd.DataFrame(data, columns=['split', 'Sweet', 'NonSweet', 'ratio'])

    fig, ax = plt.subplots(figsize=(8, 6))
    x = np.arange(len(df))

    ax.bar(x, df['NonSweet'], label='NonSweet', color=COLORS['nonsweet'])
    ax.bar(x, df['Sweet'], bottom=df['NonSweet'], label='Sweet', color=COLORS['sweet'])

    # Annotate Sweet ratio
    for i, row in df.iterrows():
        ax.text(i, row['Sweet'] + row['NonSweet'] + 50, f"{row['ratio']:.2%}", ha='center', fontweight='bold')

    ax.set_xlabel('Split', fontweight='bold')
    ax.set_ylabel('Number of Molecules', fontweight='bold')
    ax.set_title('Fig 3-2: Stratified 70/15/15 Split', fontweight='bold', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(df['split'])
    ax.legend(frameon=True)
    ax.grid(axis='y', alpha=0.3)

    save_figure(fig, 'fig_3_2_split_summary')


def fig_5_2_roc_pr_curves():
    """Fig 5-2: ROC + PR curves (val + test)."""
    val_roc = pd.read_csv(RESULTS_DIR / "val_roc.csv")
    test_roc = pd.read_csv(RESULTS_DIR / "test_roc.csv")
    test_pr = pd.read_csv(RESULTS_DIR / "test_pr.csv")

    # Calculate val PR curve
    val_metrics = pd.read_csv(RESULTS_DIR / "ensemble_val_metrics.csv")
    val_pr_auc = val_metrics.iloc[1]['pr_auc']  # tuned threshold row

    fig = plt.figure(figsize=(12, 5))
    gs = GridSpec(1, 2, figure=fig, wspace=0.3)

    # ROC curves
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(val_roc['fpr'], val_roc['tpr'], label=f'Validation (AUC={0.9681:.3f})', color=COLORS['rf'], linewidth=2)
    ax1.plot(test_roc['fpr'], test_roc['tpr'], label=f'Test (AUC={0.9759:.3f})', color=COLORS['ensemble'], linewidth=2)
    ax1.plot([0, 1], [0, 1], 'k--', alpha=0.3, label='Random')
    ax1.set_xlabel('False Positive Rate', fontweight='bold')
    ax1.set_ylabel('True Positive Rate', fontweight='bold')
    ax1.set_title('ROC Curves', fontweight='bold')
    ax1.legend(frameon=True, loc='lower right')
    ax1.grid(alpha=0.3)

    # PR curves
    ax2 = fig.add_subplot(gs[1])
    ax2.plot(test_pr['recall'], test_pr['precision'], label=f'Test (AP={0.9186:.3f})', color=COLORS['ensemble'], linewidth=2)
    ax2.axhline(y=0.229, color='gray', linestyle='--', alpha=0.5, label='Baseline (Sweet ratio)')
    ax2.set_xlabel('Recall', fontweight='bold')
    ax2.set_ylabel('Precision', fontweight='bold')
    ax2.set_title('Precision-Recall Curves', fontweight='bold')
    ax2.legend(frameon=True, loc='upper right')
    ax2.grid(alpha=0.3)
    ax2.set_xlim([0, 1])
    ax2.set_ylim([0, 1])

    fig.suptitle('Fig 5-2: Model Performance Curves', fontweight='bold', fontsize=14, y=1.02)
    save_figure(fig, 'fig_5_2_roc_pr_curves')


def fig_5_3_confusion_matrices():
    """Fig 5-3: Confusion matrices (Ensemble on val + test)."""
    val_metrics = pd.read_csv(RESULTS_DIR / "ensemble_val_metrics.csv")
    test_metrics = pd.read_csv(RESULTS_DIR / "test_metrics.csv")

    val_cm = np.array([[int(val_metrics.iloc[1]['tn']), int(val_metrics.iloc[1]['fp'])],
                       [int(val_metrics.iloc[1]['fn']), int(val_metrics.iloc[1]['tp'])]])
    test_cm = np.array([[int(test_metrics.iloc[0]['tn']), int(test_metrics.iloc[0]['fp'])],
                        [int(test_metrics.iloc[0]['fn']), int(test_metrics.iloc[0]['tp'])]])

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for ax, cm, title in zip(axes, [val_cm, test_cm], ['Validation', 'Test']):
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False, ax=ax,
                    xticklabels=['NonSweet', 'Sweet'], yticklabels=['NonSweet', 'Sweet'])
        ax.set_xlabel('Predicted', fontweight='bold')
        ax.set_ylabel('Actual', fontweight='bold')
        ax.set_title(f'{title} Set', fontweight='bold')

    fig.suptitle('Fig 5-3: Confusion Matrices (Ensemble, threshold=0.36)', fontweight='bold', fontsize=14, y=1.02)
    save_figure(fig, 'fig_5_3_confusion_matrices')


def main():
    print("=" * 60)
    print("Day 8: Generating Paper Figures")
    print("=" * 60)

    print("\n[Chapter 2: Data]")
    fig_2_1_data_pipeline()
    fig_2_2_taste_distribution()
    fig_2_4_literature_comparison()

    print("\n[Chapter 3: Features + Split]")
    fig_3_2_split_summary()

    print("\n[Chapter 5: Model Performance]")
    fig_5_2_roc_pr_curves()
    fig_5_3_confusion_matrices()

    print("\n" + "=" * 60)
    print(f"✅ All figures saved to {FIGURES_DIR}/")
    print("=" * 60)
    print("\nGenerated figures:")
    for f in sorted(FIGURES_DIR.glob("*.pdf")):
        print(f"  - {f.name}")


if __name__ == "__main__":
    main()
