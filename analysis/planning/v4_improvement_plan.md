# v4 审查改进方案

> 2026-05-13 | 基于审查意见 v4

## v4 判断

Workshop 已经很有竞争力。主会需要补：统计报告、更多 baseline、pIIA 指标增强。

## 10 个问题分类

### 快修（6 个，表述/表格/简单计算，< 1 小时）

| # | 问题 | 方案 |
|:---:|------|------|
| 1 | 定义 7 desc(a) 残留 | ✅ 已修 |
| 2 | ToolProxyGap 与 FNR-Gap 重复 | 加 `FNR-Gap = max_{A,B} ToolProxyGap(A,B)` |
| 3 | Frag vs ToolProxyGap 桥接 | 加"Frag 是理论表征距离; ToolProxyGap 是安全任务 proxy" |
| 5 | LOTO 表缺 source-FNR + heldout-tool | 补四列: Source FNR, Heldout FNR, FNR-Gap, Heldout Tool |
| 7 | 部署 FNR≈0 需样本量+CI | 加 per-effect per-tool 样本数, rule-of-three CI |
| 9 | 命题 1 同家族 vs 跨家族需 CI | 加 95% CI + bootstrap, 注明 156 对非独立 |

### 需要分析（2 个，不用新实验）

| # | 问题 | 方案 |
|:---:|------|------|
| 6 | tool-conditioned 为什么不起作用 | LOTO 下 heldout 工具 ID 未在训练中出现,one-hot 退化为全零。相当于 pooled。需要实验中明确写这个机制 |
| 8 | pIIA-FNR "统计关系"→"趋势关系" | 已修。保持 ρ=0.77 p=0.072 的克制表述 |

### 需要新实验（2 个）

| # | 问题 | 方案 |
|:---:|------|------|
| 4 | pIIA 需 threshold/margin | 从 LOTO 数据用 within-FNR/heldout-FNR 直接作为 pIIA-threshold 的近似（pIIA-within threshold ≈ 1-within_FNR, pIIA-cross threshold ≈ 1-heldout_FNR） |
| 10(审查#8) | Group DRO baseline | 实现 worst-group importance weighting: 在 pooled 训练中给稀有工具更高权重 |

## 执行顺序

```
快修 1-9 (30 分钟)
  → pIIA-threshold 近似 (15 分钟)
  → Group DRO (30 分钟)
  → 更新 formalization.md
```

## Group DRO 实现方案

标准 Group DRO (Sagawa et al., ICLR 2020) 需要分组并优化 worst-group loss。简化版：

```
for each tool T:
  w_T = 1 / n_T  (inverse frequency weight)
train pooled LogisticRegression with sample_weight = w_{tool}
```

这等价于给稀有工具的样本更高权重。与 balanced pooling（固定采样数）不同，weighted 使用所有数据但改变每个样本的损失权重。

预期：比 balanced 更稳定（不用丢弃数据），但同样不能解决跨工具表征碎片化——因为问题在于特征空间分离，不在于损失权重。
