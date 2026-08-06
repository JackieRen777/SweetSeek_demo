"""Data curation flowchart — clean single-column layout."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "results"

TEAL  = '#2A9D6A'
BLUE  = '#2D7DC4'
AMBER = '#D48A0A'
RED   = '#C0392B'
WHITE = '#FFFFFF'

def rounded_box(ax, cx, cy, w, h, text, fc, ec, fs=10):
    p = mpatches.FancyBboxPatch((cx-w/2, cy-h/2), w, h,
        boxstyle='round,pad=0.025', facecolor=fc, edgecolor=ec,
        linewidth=2, zorder=3)
    ax.add_patch(p)
    ax.text(cx, cy, text, ha='center', va='center',
            fontsize=fs, color='#1a1a1a', zorder=4, linespacing=1.5)

def vert_arrow(ax, cx, y_top, y_bot):
    ax.annotate('', xy=(cx, y_bot+0.005), xytext=(cx, y_top-0.005),
        arrowprops=dict(arrowstyle='->', color='#555555', lw=1.6), zorder=2)

def drop_note(ax, cx, cy, text):
    ax.text(cx + 0.36, cy, text, ha='left', va='center',
            fontsize=8, color=RED,
            bbox=dict(boxstyle='round,pad=0.2', fc='#FDECEA', ec=RED, lw=0.8))

fig, ax = plt.subplots(figsize=(7, 13))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis('off')

W = 0.62   # box width
CX = 0.42  # center x

# ── Step 0: two sources side by side ─────────────────────────────────────────
# Left source
p1 = mpatches.FancyBboxPatch((0.04, 0.91), 0.28, 0.07,
    boxstyle='round,pad=0.025', facecolor='#D4EDDA', edgecolor=TEAL,
    linewidth=2, zorder=3)
ax.add_patch(p1)
ax.text(0.18, 0.945, 'ChemTastesDB\n2,930 molecules',
        ha='center', va='center', fontsize=9.5, color='#1a1a1a',
        fontweight='bold', linespacing=1.4)

# Right source
p2 = mpatches.FancyBboxPatch((0.38, 0.91), 0.28, 0.07,
    boxstyle='round,pad=0.025', facecolor='#D0E4F5', edgecolor=BLUE,
    linewidth=2, zorder=3)
ax.add_patch(p2)
ax.text(0.52, 0.945, 'BitterDB\n2,228 molecules',
        ha='center', va='center', fontsize=9.5, color='#1a1a1a',
        fontweight='bold', linespacing=1.4)

# Converging arrows into step 1
ax.annotate('', xy=(CX-0.05, 0.865), xytext=(0.18, 0.91),
    arrowprops=dict(arrowstyle='->', color='#555555', lw=1.4))
ax.annotate('', xy=(CX+0.05, 0.865), xytext=(0.52, 0.91),
    arrowprops=dict(arrowstyle='->', color='#555555', lw=1.4))

# ── Steps ────────────────────────────────────────────────────────────────────
steps = [
    # (cy, text, fc, ec, drop_text)
    (0.81, 'SMILES Standardization\n(canonical form, InChIKey, MW)\n→ CTD: 2,913  |  BDB: 2,206',
     '#EBF5FB', BLUE, '−17 CTD  / −22 BDB\n(no SMILES / disallowed atoms)'),

    (0.65, 'Within-source Deduplication\n(by InChIKey, keep first)\n→ CTD: 2,683  |  BDB: 2,128',
     '#EBF5FB', BLUE, '−230 CTD  / −78 BDB\n(duplicate structures)'),

    (0.49, 'Cross-source Merge\n(ChemTastesDB priority on overlap)\nOverlap removed: 650  →  Union: 4,161',
     '#FEF9E7', AMBER, '−650 BDB duplicates\n(already in CTD)'),

    (0.335, 'Label Mapping  (V1 binary)\nSweet → 1    Non-Sweet → 0\n→ 3,862 labeled',
     '#FEF9E7', AMBER, '−299 dropped\n(multitaste / umami / sour / salt)'),

    (0.18, 'Quality Filter\nMolecular weight: 50–2,000 Da\n→ 3,846 molecules',
     '#FEF9E7', AMBER, '−16 dropped\n(MW out of range)'),
]

BOX_H = 0.11
prev_cy = 0.865

for cy, text, fc, ec, drop in steps:
    vert_arrow(ax, CX, prev_cy, cy + BOX_H/2)
    rounded_box(ax, CX, cy, W, BOX_H, text, fc, ec, fs=9.5)
    drop_note(ax, CX, cy, drop)
    prev_cy = cy - BOX_H/2

# ── Final dataset ─────────────────────────────────────────────────────────────
vert_arrow(ax, CX, prev_cy, 0.065)
p_final = mpatches.FancyBboxPatch((CX - W/2, 0.01), W, 0.10,
    boxstyle='round,pad=0.025', facecolor='#D4EDDA', edgecolor=TEAL,
    linewidth=2.5, zorder=3)
ax.add_patch(p_final)
ax.text(CX, 0.06,
        'Final Dataset:  3,846 molecules\n'
        'Sweet: 881 (22.9%)    Non-Sweet: 2,965 (77.1%)\n'
        'ChemTastesDB: 2,381    BitterDB: 1,465',
        ha='center', va='center', fontsize=10,
        color='#1a1a1a', fontweight='bold', linespacing=1.5, zorder=4)

ax.set_title('Data Curation Pipeline', fontsize=13, fontweight='bold',
             pad=12, color='#1a1a1a', y=0.995)

fig.tight_layout()
fig.savefig(OUT / 'fig7_data_curation.png', dpi=300, bbox_inches='tight')
print('Saved: results/fig7_data_curation.png')
