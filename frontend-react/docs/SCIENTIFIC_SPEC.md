# Scientific Specification & Design Document
## 1. 论文深度解析与需求清单 (Paper Analysis)

### 1.1 核心研究问题
建立氯代蔗糖衍生物的**相对结合自由能 ($\Delta\Delta G$)** 与 **相对甜度 ($Sw$)** 之间的定量关系，验证 "自由能-感知强度" 的跨尺度关联。

### 1.2 关键数据模型
*   **输入变量**: $\Delta\Delta G$ (Relative Binding Free Energy, kcal/mol)
*   **输出变量**: $Sw$ (Relative Sweetness vs Sucrose)
*   **核心方程 (Eq 1)**: 
    $$ \Delta\Delta G = 10.13 \cdot \log_{10}(Sw) - 20.72 $$
    *   *注：此方程基于论文图表数据 (Table 1 & Fig 2) 提取，与部分文本描述的斜率符号差异以图表数据为准（Table 1 显示 $\Delta\Delta G$ 与 $\log Sw$ 正相关）。*
*   **转换方程**:
    $$ \log_{10}(Sw) = \frac{\Delta\Delta G + 20.72}{10.13} $$
    $$ Sw = 10^{\frac{\Delta\Delta G + 20.72}{10.13}} $$
*   **统计参数**: $R^2 = 0.8615$, 95% 置信区间斜率 [8.78, 11.49]。

### 1.3 实验数据 (Table 1 Reference)
| Compound | $\log_{10} Sw$ | $\Delta\Delta G$ (kcal/mol) |
| :--- | :--- | :--- |
| 4-Cl-sucrose | 0.70 | -17.47 |
| 1p-Cl-sucrose | 1.30 | -8.28 |
| ... | ... | ... |
| 4-1p-6p-4Cl-sucrose | 3.32 | 8.68 |

## 2. 网页信息架构 (Information Architecture)

### 2.1 布局结构
*   **Header**: 论文标题、版本号、导出/引用工具。
*   **Main Stage (Split View)**:
    *   **Left (Control Panel)**: 
        *   $\Delta\Delta G$ 输入 (Slider + Input, Range: -20 to +15).
        *   Model Parameters Display ($a=10.13, b=-20.72$).
    *   **Center (Visualization)**:
        *   3D Oral Cavity (Contextual).
        *   Dynamic Molecule/Receptor Interaction.
    *   **Right (Analysis)**:
        *   Regression Plot ($\Delta\Delta G$ vs $\log Sw$).
        *   Data Table (Comparison with Reference Compounds).

## 3. 科学可行性验证 (Scientific Validation)

| 验证项目 | 论文要求 | 网页实现方案 | 技术路径 |
| :--- | :--- | :--- | :--- |
| **计算精度** | 保留2位小数 | JavaScript `Number` (双精度浮点) | 前端实时计算 |
| **数据边界** | $\Delta\Delta G \in [-18, 10]$ | Input Range Restriction | React State Validation |
| **实时性** | 毫秒级响应 | React `useMemo` / RAF | Client-side Computing |
| **理论模型** | Boltzmann/Stevens | 代码复现 Eq 2-15 推导逻辑 | TypeScript Logic |

## 4. 交互规格 (Interaction Specs)

*   **Slider**: 
    *   Default: $\Delta\Delta G = 0$ (Sucrose baseline approx).
    *   Step: 0.1 kcal/mol.
    *   Feedback: 实时更新图表上的 "Current Prediction" 点。
*   **Charts**:
    *   显示 Reference Points (Table 1 数据) 作为散点背景。
    *   显示 Regression Line (Eq 1)。
    *   显示 95% Confidence Interval (Shaded Area).

## 5. 可访问性 (Accessibility)
*   **ARIA**: `aria-label`, `role="slider"`, `aria-valuetext`.
*   **Color**: High contrast charts (Blue/Orange), Colorblind friendly palette.
*   **Keyboard**: Tab navigation support for sliders and buttons.
