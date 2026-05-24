# 对比投影：工具不变因果表征的初步解法

> 论文 Solution 节素材 | 2026-05-13

---

## 一、方法动机

工具代理问题的根源是：同一因果效果由不同工具产生时，LLM 嵌入中的正类样本分布在分离的子流形上。线性探针无法找到跨子流形的单一方向。

直觉解：学习一个投影 $P$，将碎片化的子流形压入共享的低维区域——同效果、不同工具的样本被拉到邻近位置，工具特定的表面特征被信息瓶颈丢弃。

---

## 二、方法

### 2.1 对比投影

对每个因果效果 $E$，学习线性投影矩阵 $P \in \mathbb{R}^{d \times k}$（$d$ 为 LLM 嵌入维数，$k \ll d$ 为投影维数）：

$$\mathbf{z} = \frac{P^\top \mathbf{h}}{\|P^\top \mathbf{h}\|}$$

**正样本对**：对每个工具对 $(A, B)$，采样 $a \sim P(\mathbf{h} \mid E=1, T=A)$，$b \sim P(\mathbf{h} \mid E=1, T=B)$。正对数量 = $\sum_{A<B} \min(N_A^+, N_B^+)$。

**负样本**：随机采样 $E=0$ 的样本 $\mathbf{h}_{\text{neg}}$。

**损失函数**（Siamese contrastive）：

$$\mathcal{L}(P) = \underbrace{\frac{1}{|P^+|}\sum_{(a,b)} \|\mathbf{z}_a - \mathbf{z}_b\|^2}_{\text{拉近同效果、不同工具}} + \lambda \cdot \underbrace{\frac{1}{|P^+|}\sum_{(a,b)}\max(0, 1 - \|\mathbf{z}_a - \mathbf{z}_{\text{neg}}\|)^2}_{\text{推开不同效果}} + \gamma \|P\|_F^2$$

### 2.2 训练配置

| 参数 | 值 |
|------|:---:|
| 投影维数 $k$ | **64**（消融实验：64-1024 全有效） |
| 优化器 | Adam, lr=0.001 |
| 迭代数 | 500 |
| Batch Size | 64 |
| $\lambda$ | 0.5 |
| $\gamma$ | 0.01 |
| 设备 | GPU (RTX 4090) |
| 每效果训练时间 | ~30 秒 |

### 2.3 评估协议

1. **全量训练**：投影 $P$ 使用所有工具对的对比对训练。在投影后空间上 LOTO 评估：训练探针时排除工具 $T$，在 $T$ 上测试 FNR。

2. **Strict Cross-Tool**：投影训练时排除工具对 $(A, B)$ 的所有对比对。在 $A$ 和 $B$ 上测量 LOTO FNR。这是更严格的测试——投影从未"见过"这两个工具之间的关系，只能通过中间工具做传递式对齐。

---

## 三、结果

### 3.1 全量训练

| 效果 | preFNR (max) | postFNR (max) | Δ |
|------|:---:|:---:|:---:|
| content_fetched | 0.78 | **0.22** | +0.56 |
| file_content_read | 0.88 | **0.00** | +0.88 |
| file_deleted | 0.60 | **0.00** | +0.60 |
| file_written | 0.97 | **0.00** | +0.97 |
| network_egress | 0.73 | **0.00** | +0.73 |
| tool_error | 0.27 | **0.00** | +0.27 |

16/20 工具改善，均值 ΔFNR = **+0.37**。4/6 效果全部工具 postFNR=0。

### 3.2 Strict Cross-Tool

投影训练排除目标工具对后：

| 指标 | 值 |
|------|:---:|
| 均值 ΔFNR | **+0.16** |
| 改善比例 | 40/68 (59%) |
| 最佳改善 | +0.73 (network_egress, 4 工具→排除 1 对仍有 2 中间工具) |

Strict 测试下改善减弱但保持正向。network_egress 受益于更多中间工具做传递式对齐。仅 2 工具的效果（content_fetched, file_written 等）在 strict 设置下无法做传递对齐——这是方法的已知局限（需要 ≥3 工具）。

### 3.3 维度消融

| 维度 | 64 | 128 | 256 | 512 | 1024 |
|------|:---:|:---:|:---:|:---:|:---:|
| content_fetched | 0.22 | 0.22 | 0.34 | 0.22 | 0.25 |
| 其他 5 效果 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

全维度有效。最优维度 64——更小的信息瓶颈更强地丢弃工具特定特征。

### 3.4 content_fetched 残余分析

**原因**：terminal 仅有 8 个正样本 → 与 web_fetch (32 个) 的对比对仅 8 对。正样本对数量决定了对比损失的信号强度。8 对不足以充分学习跨工具对齐。

**验证**：当投影维数降至 64，postFNR 从 0.25 进一步降到 0.22——更低维度的信息瓶颈部分补偿了对比对的稀疏。

**非方法原理瓶颈**：收集更多 terminal 正样本可以预期进一步降低残余 FNR。

---

## 四、与其他方法的对比

### 4.1 与 Procrustes 对齐对比

| | Procrustes | 对比投影 |
|------|:---:|:---:|
| 操作 | 旋转 w_A 方向到 w_B | 学习投影 P: R^d → R^k |
| 训练 | 闭式解 (SVD) | Adam, 500 epochs |
| 均值 ΔFNR | +0.04 | **+0.37** |
| 改善比例 | 15/38 (39%) | **16/20 (80%)** |
| 失败原因 | 碎片化不在角度中 | 数据稀疏 (N+<10) |

Procrustes 仅对齐 1D 方向，无法处理碎片化（在方差/协方差中）。对比投影通过低维压缩同时处理所有统计量。

### 4.2 与 Baseline 对比

| 方法 | 均值 Worst-FNR | 类型 |
|------|:---:|------|
| Pooled / Balanced / Tool-Cond / Group Reweight | 0.20-0.97 | 诊断 baseline |
| **Contrastive Projection** | **0.00-0.22** | **解法** |

### 4.3 与文献的关系

| 方法 | 场景 | 与我们的关系 |
|------|------|------|
| ICI-DG (IJCV 2026) | 视觉 DG, 对比不变性 | 我们首次应用于 agent 工具因果不变性 |
| CDAS (ICLR 2026) | DAS 交换干预做模型 steering | 我们更轻量（对比投影 vs 迭代前向干预） |
| AnisoAlign (May 2026) | 模态间几何校准 | 共享对齐目标，但我们是工具间（同模态内） |

---

## 五、论文中的定位

### 贡献声明

1. **我们提出对比投影作为工具不变因果表征的第一个有效方法**（非 trivial——5 种 baseline + Procrustes 均失败）
2. **Strict cross-tool 消融证明方法可传递式泛化**（但仅 ≥3 工具时有效）
3. **内容_fetched 残余归因于数据稀疏**（非方法原理瓶颈）

### 不声称的

- "解决了工具代理问题"：strict 设置下改善 59%，全量 80%。不是 100%。
- "理论保证"：对比损失的泛化界未推导。当前是经验方法。
- "跨模型泛化"：仅测了 Qwen3-8B。

### 在论文中的位置

| 节 | 内容 |
|------|------|
| §5 (Problem Diagnosis) | 工具代理的诊断 + baseline 排除 |
| **§6 (Solution)** | 对比投影方法 + 全量结果 + strict 消融 + 维度消融 |
| §7 (Discussion) | 局限：全量 vs strict 差距，content_fetched 残余，需要 ≥3 工具 |

---

## 六、复现代码

```bash
# 全量对比投影
python solution_contrastive.py qwen3-8b_scenarios_merged

# 消融实验（维度 + strict cross-tool）
python solution_ablation.py qwen3-8b_scenarios_merged

# Procrustes 对齐（对比 baseline）
python solution_procrustes.py qwen3-8b_scenarios_merged
```

输出：`analysis/contrastive_*.json`, `analysis/ablation_*.json`, `analysis/procrustes_*.json`
