"""中文版建模流程图 — fig5_pipeline_zh.png"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import font_manager
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "results"
OUT.mkdir(exist_ok=True)

# 选一个 macOS 自带且支持中文的字体
for cand in ['PingFang SC', 'Heiti SC', 'STHeiti', 'Songti SC', 'Hiragino Sans GB', 'Arial Unicode MS']:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams['font.family'] = cand
        break
plt.rcParams['axes.unicode_minus'] = False

TEAL  = '#2E8B57'
BLUE  = '#4682B4'
ORANGE = '#E07B00'

steps = [
    ('ChemTastesDB\n+ BitterDB',                     '#D4EDDA', TEAL),
    ('SMILES\n标准化',                                '#D0E8F2', BLUE),
    ('去重\n+ 标签合并',                              '#D0E8F2', BLUE),
    ('3846 个分子\nmaster.parquet',                   '#D4EDDA', TEAL),
    ('特征工程\nECFP4+MACCS+RDKit2D\n共 1407 维',     '#D0E8F2', BLUE),
    ('70/15/15 划分\n（分层抽样）',                   '#D0E8F2', BLUE),
    ('RF + XGB\n5 折交叉验证',                        '#FFE8CC', ORANGE),
    ('集成模型\nAUC = 0.976',                         '#D4EDDA', TEAL),
]

fig, ax = plt.subplots(figsize=(11, 3.0))
ax.set_xlim(0, len(steps))
ax.set_ylim(0, 1)
ax.axis('off')

box_w, box_h = 0.86, 0.62
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
            fontsize=8.6, color='#1a1a1a', linespacing=1.4)
    if i < len(steps) - 1:
        ax.annotate('', xy=(i + 1 + 0.5 - box_w/2, y_center),
                    xytext=(i + 0.5 + box_w/2, y_center),
                    arrowprops=dict(arrowstyle='->', color='#555555', lw=1.5))

ax.set_title('数据与建模流程', fontsize=14, pad=10, color='#1a1a1a')
fig.tight_layout()
out_path = OUT / 'fig5_pipeline_zh.png'
fig.savefig(out_path, dpi=300, bbox_inches='tight')
plt.close()
print(f'Saved: {out_path}')
