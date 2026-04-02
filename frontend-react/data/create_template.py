import pandas as pd
import os

data = [
    {
        "Title": "Interaction mechanism between zein and β-lactoglobulin: Insights from multi-spectroscopy and molecular dynamics simulation methods.",
        "Authors": "Chengzhi Liu†, Nan Lv†, Lijuan Dong, Min Huang (黄敏)*, Qing Shen, Gerui Ren, Ruibo Wu, Binju Wang, Zexing Cao, Hujun Xie (谢湖均)*.",
        "Journal": "Food Hydrocolloids",
        "Year": 2023,
        "Volume": "135",
        "Pages": "108226",
        "IF": 11,
        "IsESI": "Yes",
        "Rank": "前1%"
    },
    {
        "Title": "Highly biologically active and pH-sensitive collagen hydrolysate-chitosan film loaded with red cabbage extracts realizing dynamic visualization and preservation of shrimp freshness.",
        "Authors": "Gerui Ren, Ying He, Junfei Lv, Ying Zhu, Zhengfang Xue, Yujing Zhan, Yufan Sun, Xin Luo, Ting Li, Yuling Song, Fuge Niu, Min Huang, Sheng Fang, Linglin Fu, Hujun Xie (谢湖均)*.",
        "Journal": "International Journal of Biological Macromolecules",
        "Year": 2023,
        "Volume": "233",
        "Pages": "123414",
        "IF": 9,
        "IsESI": "Yes",
        "Rank": "前1%"
    }
]

df = pd.DataFrame(data)

# Ensure the directory exists
os.makedirs('/Users/jackieren/Desktop/FCN_SweetSeek/frontend-react/data', exist_ok=True)

# Save to Excel
df.to_excel('/Users/jackieren/Desktop/FCN_SweetSeek/frontend-react/data/references_template.xlsx', index=False)
print("Template created successfully!")
