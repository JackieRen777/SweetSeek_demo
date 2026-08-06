"""Extra figures for group meeting report."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import numpy as np
import pandas as pd
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "results"
OUT.mkdir(exist_ok=True)

TEAL   = '#2E8B57'
BLUE   = '#4682B4'
GRAY   = '#AAAAAA'
RED    = '#DC143C'
LIGHT  = '#F0F7F4'

plt.rcParams.update({
    'font.family': 'Times New Roman',
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'font.size': 11,
})


# ── Fig 4: Class Distribution ─────────────────────────────────────────────────
def fig_class_dist():
    y = np.load(REPO / 'data/features/y.npy')
    sweet = int((y == 1).sum())
    nonsweet = int((y == 0).sum())

    fig, ax = plt.subplots(figsize=(5, 4))
    bars = ax.bar(['Sweet', 'Non-Sweet'], [sweet, nonsweet],
                  color=[TEAL, GRAY], width=0.5, edgecolor='white', linewidth=1.2)
    for bar, val in zip(bars, [sweet, nonsweet]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 30,
                f'{val}\n({val/len(y)*100:.1f}%)',
                ha='center', va='bottom', fontsize=10)

    ax.set_ylabel('Number of Molecules')
    ax.set_title(f'Dataset Class Distribution  (Total = {len(y)})', fontsize=12)
    ax.set_ylim(0, nonsweet * 1.22)
    fig.tight_layout()
    fig.savefig(OUT / 'fig4_class_dist.png', dpi=300, bbox_inches='tight')
    plt.close()
    print('fig4_class_dist.png saved')


# ── Fig 5: Data Pipeline Flowchart ───────────────────────────────────────────
def fig_pipeline():
    steps = [
        ('ChemTastesDB\n+ BitterDB', '#D4EDDA', TEAL),
        ('SMILES\nStandardization', '#D0E8F2', BLUE),
        ('Deduplication\n& Label Merge', '#D0E8F2', BLUE),
        ('3846 Molecules\nmaster.parquet', '#D4EDDA', TEAL),
        ('Feature Engineering\nECFP4+MACCS+RDKit2D\n1407 dims', '#D0E8F2', BLUE),
        ('70/15/15 Split\n(Stratified)', '#D0E8F2', BLUE),
        ('RF + XGB\n5-fold CV', '#FFE8CC', '#E07B00'),
        ('Ensemble\nAUC = 0.976', '#D4EDDA', TEAL),
    ]

    fig, ax = plt.subplots(figsize=(10, 2.8))
    ax.set_xlim(0, len(steps))
    ax.set_ylim(0, 1)
    ax.axis('off')

    box_w, box_h = 0.82, 0.52
    y_center = 0.5

    for i, (label, facecolor, edgecolor) in enumerate(steps):
        x = i + 0.5
        rect = mpatches.FancyBboxPatch(
            (x - box_w/2, y_center - box_h/2), box_w, box_h,
            boxstyle='round,pad=0.04',
            facecolor=facecolor, edgecolor=edgecolor, linewidth=1.5
        )
        ax.add_patch(rect)
        ax.text(x, y_center, label, ha='center', va='center',
                fontsize=8.2, color='#333333')
        if i < len(steps) - 1:
            ax.annotate('', xy=(i + 1 + 0.5 - box_w/2, y_center),
                        xytext=(i + 0.5 + box_w/2, y_center),
                        arrowprops=dict(arrowstyle='->', color='#555555', lw=1.4))

    ax.set_title('Data & Modeling Pipeline', fontsize=12, pad=8)
    fig.tight_layout()
    fig.savefig(OUT / 'fig5_pipeline.png', dpi=300, bbox_inches='tight')
    plt.close()
    print('fig5_pipeline.png saved')


# ── Fig 6: Literature Comparison Table ───────────────────────────────────────
def fig_literature():
    cols = ['Metric', 'Tang 2023\n(Foods)', 'ChemSweet 2025\n(Food Chem)', 'SweetSeek\n(Ours)']
    rows = [
        ['Dataset size',       '649',        '47,087 (multi-task)',  '3,846'],
        ['Feature type',       '91 phys-chem','MOE 2D + fingerprints','ECFP4+MACCS+RDKit2D'],
        ['Feature dims',       '91',          '200+680+fingerprints', '1,407'],
        ['Best classifier AUC','0.89 (RF)',   '0.986 (Carbohydrate)', '0.976 (Ensemble)'],
        ['Regression (R²)',    '0.78',        '0.873',                'N/A (V2 planned)'],
        ['Interpretability',   'Variable imp.','SHAP (global)',       'SHAP (per-sample)'],
        ['Safety prediction',  'No',          'Yes (LD50/Ames/NOAEL)','No'],
        ['Web deployment',     'No',          'Yes',                  'Yes (sweetseek.top)'],
    ]

    fig, ax = plt.subplots(figsize=(11, 4))
    ax.axis('off')

    col_widths = [0.22, 0.20, 0.30, 0.24]
    x_pos = [sum(col_widths[:i]) for i in range(len(col_widths))]

    # Header
    for j, (col, xp) in enumerate(zip(cols, x_pos)):
        ax.text(xp + col_widths[j]/2, 1.0, col,
                ha='center', va='center', fontsize=9.5, fontweight='bold',
                color='white',
                bbox=dict(boxstyle='square,pad=0.3', facecolor=TEAL, edgecolor='none'))

    # Rows
    for i, row in enumerate(rows):
        bg = LIGHT if i % 2 == 0 else 'white'
        y = 1.0 - (i + 1) * 0.105
        for j, (cell, xp) in enumerate(zip(row, x_pos)):
            color = '#C8E6C9' if (j == 3 and i in [0, 2, 5, 7]) else bg
            ax.text(xp + col_widths[j]/2, y, cell,
                    ha='center', va='center', fontsize=8.5,
                    bbox=dict(boxstyle='square,pad=0.28', facecolor=color, edgecolor='#DDDDDD', linewidth=0.5))

    ax.set_xlim(0, 1)
    ax.set_ylim(1.0 - len(rows) * 0.105 - 0.05, 1.1)
    ax.set_title('Comparison with Related Works', fontsize=12, pad=10)
    fig.tight_layout()
    fig.savefig(OUT / 'fig6_literature.png', dpi=300, bbox_inches='tight')
    plt.close()
    print('fig6_literature.png saved')


if __name__ == '__main__':
    import os
    os.chdir(REPO)
    fig_class_dist()
    fig_pipeline()
    fig_literature()
    print('\nAll done → results/fig4–6')
