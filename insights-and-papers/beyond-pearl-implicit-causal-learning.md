# 超越 Pearl：隐式因果学习能替代显式因果建模吗？

## 问题的本质

用户提出了一个比"如何改进 CAR 的因果推理"更根本的问题：

> 是否需要硬数学建模（Pearl 的 do-calculus + 因果图）？还是可以像 LLM 学会语言一样，让机器通过潜空间 embedding 隐式学到因果信息？

这个问题恰好命中了 2025-2026 年因果推理领域最深层的分裂。

---

## 一、两条路线的根本分歧

```
路线 P (Pearl 传统):
  因果图 → do-calculus → 因果效应
  "没有图就没有因果"

路线 E (Emergent/连接主义):
  足够的数据 + 正确的架构 → 因果结构在潜空间中涌现
  "因果是可以学到的，就像语法是可以学到的一样"
```

### 1.1 Pearl 路线的逻辑

Pearl 的基本论证是：关联 ≠ 因果，要从观测数据中得到因果结论，必须要有因果假设（因果图）。do-calculus 的作用是在给定的因果图假设下，判断一个因果效应是否可以从观测数据中识别，如果可以，怎么算。

这条路线的力量在于**保证**——如果图是对的，效应估计就是无偏的。弱点在于**图通常不是已知的**。

### 1.2 Emergent 路线的逻辑

Emergent 路线的基本论证是：因果结构本身是可以从数据中学到的——不是作为离散的图搜索，而是作为潜空间中的连续几何结构。就像 LLM 从文本中学会了语法而不需要显式的句法树，模型可以从干预/时间序列/多环境数据中学会因果而不需要显式的因果图。

这条路线的力量在于**可扩展性**——不需要领域专家画图。弱点在于**缺乏保证**——你不知道模型学到的"因果"是不是真的因果。

---

## 二、2025-2026 年的关键证据

### 2.1 最震撼的发现：Transformer 本身就是因果学习者

**NeurIPS 2025**: *"Transformer Is Inherently a Causal Learner"* (Wang, Wang, Huang)

**核心发现**: 用自回归目标训练的 decoder-only transformer **在其学习到的表征中自然地编码了时滞因果结构**——不需要任何显式的因果目标、结构约束或 do-calculus。

具体来说：
- 输出的梯度对过去输入的敏感度直接恢复了底层的因果图
- 因果准确率随数据量增加呈现**缩放法则**——传统因果发现方法没有这个性质
- 这意味着自回归预训练本身就施加了因果归纳偏置

**对 CAR 的启示**: 如果自回归 transformer 天然学会了因果，那么 CAR 中与 LLM 交互的过程本身可能已经在隐式地利用这一点。LLM 选择调用哪个工具、用什么参数，都在其自回归推理中编码了因果推理——只是我们没有显式地提取和利用它。

### 2.2 因果基础模型的崛起

**Arrow** (May 2026, UTS/CSIRO): 一个在 1 亿+合成因果发现任务上预训练的 transformer。不需要 do-calculus——DAG 被分解为无向骨架 + 拓扑排序，一次前向传播预测因果图。在零样本场景下匹配或超越专用因果发现算法。

**Mask2Cause** (May 2026, IISc): 在时间序列预测的前向传播中**同时**学习邻接矩阵和预测权重——可学习的邻接矩阵门控自注意力。因果图不是后处理提取的，而是和前向传播一同优化的。

**CausalFM** (June 2025, updated Feb 2026): 用 Prior-Data Fitted Networks (PFNs) 做贝叶斯因果推断。模型在上下文中学习后门/前门/工具变量调整——不需要显式的 do-calculus。

**Causal-JEPA** (Feb 2026): 对象级别的 masking 在联合嵌入预测架构中**诱导出反事实式效果**——约 20% 的绝对提升来自于架构设计本身，而非任何因果损失函数。

### 2.3 Schölkopf 路线：算法因果性 + 压缩

**CLeaR 2025**: Schölkopf 和 Wendong 提出"算法因果性"——当传统因果可识别性假设失败时，因果结构可以通过跨多个环境的**压缩**来涌现。核心论证：

> 因果结构 = 在多环境中实现最短描述长度的表征

这与 LLM 的训练直接相关——LLM 在预训练中做了大量的压缩（下一个 token 预测 → 学习最小充分统计量）。如果因果结构是最可压缩的（能够最好地泛化到新环境），那么有效的压缩自然会倾向于学到因果结构。

**ICLR 2025**: Schölkopf 团队的 IEM（可识别可交换机制）框架将因果发现、ICA 和因果表征学习统一在单一概率图模型下——不再区分"发现"和"学习"，而是将它们视为同一潜变量推断问题的不同侧面。

### 2.4 隐式因果表征学习的关键进展

**Do-PFN / TabPFN** (2025): 从预训练 PFN 的**冻结 embedding** 中提取因果信号。因果知识已经存在于 embedding 中——PFN 从未被训练做因果推理，但它的内部表征编码了因果信息。这是"因果知识可以在没有显式因果训练的情况下涌现"的直接证据。

**ECAM** (2026): 一个即插即用的注意力模块——将 SCM 直接集成到 transformer 注意力计算中。从数据或专家先验学习局部因果图，调节注意力分数。使得模型可以在内部做干预和反事实推理，而不需要外部的 do-calculus 引擎。

**IEM** (ICLR 2025, Schölkopf et al.): 统一了因果发现和表征学习——通过 exchangeability 假设和机制变异性条件，在潜空间中同时识别因果变量和因果结构。

---

## 三、对 CAR 的深刻启示

### 3.1 当前路线的根本问题

CAR 当前的理论改进路线（后门调整、do-calculus）是在 Pearl 框架内修补——这是**在正确的方向上用了错误的工具**。

理由：
1. CAR 面对的不是一个已知因果图 + 需要估计效应的场景，而是一个**因果图根本不知道且不断变化的场景**
2. CAR 拥有的是一个 LLM（自回归 transformer）+ 执行历史流。根据 NeurIPS 2025 的发现，这两者都天然编码了因果信息——只是没有被提取
3. 强迫一个在潜空间中已经隐式拥有因果知识的系统去使用显式的 do-calculus，是在用 1990 年代的工具解决 2026 年的问题

### 3.2 替代路线：CAR-CRL (Causal Representation Learning for CAR)

**核心思想**: 不是给 CAR 加一个 do-calculus 引擎，而是设计一个小型神经组件，从 CAR 的执行流中**学习因果转移的潜空间表征**。

```
当前 CAR:
  工具调用 → _state_pattern (手工离散化) → 频率表 → Laplace 平滑 → 置信度

CAR-CRL:
  工具调用 → 编码器(小型 transformer/MLP) → 潜空间表征 z
         ↓
  因果注意力层 → 对每个候选效果给出 P(effect | 潜空间上下文)
         ↓
  解码器 → 结构化输出 (效果 + 置信度 + 不确定性的完整分布)
```

### 3.3 具体的架构设计

```python
class CausalTransitionEncoder(nn.Module):
    """学习工具→效果转移的因果潜空间表征"""

    def __init__(self, state_dim, tool_dim, latent_dim=128):
        # 状态编码器
        self.state_encoder = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.LayerNorm(256),
            nn.GELU(),
            nn.Linear(256, latent_dim)
        )

        # 工具嵌入
        self.tool_embedding = nn.Embedding(num_tools, latent_dim)

        # 因果注意力 —— 借鉴 ECAM 的思路
        # 不是计算 "所有状态特征之间的注意力"
        # 而是计算 "工具嵌入 × 状态特征之间的因果注意力"
        self.causal_attention = CausalCrossAttention(
            latent_dim,
            num_heads=4,
            # 关键：注意力掩码由因果先验（时间顺序 + LLM 提供的方向性）调制
            causal_mask_provider=self.llm_causal_prior
        )

        # 效果预测头 —— 多标签分类 + 不确定性估计
        self.effect_predictor = nn.Sequential(
            nn.Linear(latent_dim * 2, 128),  # 状态 ⊕ 工具
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(128, num_effects)  # 每个效果一个 logit
        )

        # 置信度估计 —— 每个预测附带的不确定性
        self.uncertainty_head = nn.Sequential(
            nn.Linear(latent_dim * 2, 64),
            nn.GELU(),
            nn.Linear(64, num_effects)  # 每个效果的对数方差
        )

    def forward(self, state, tool_idx):
        # 编码状态到潜空间
        z_state = self.state_encoder(state)

        # 工具嵌入
        z_tool = self.tool_embedding(tool_idx)

        # 因果交叉注意力 —— 工具如何在潜空间中"关注"状态的不同维度
        z_causal = self.causal_attention(
            query=z_tool.unsqueeze(1),      # 工具作为 query
            key=z_state.unsqueeze(1),       # 状态作为 key
            value=z_state.unsqueeze(1)      # 状态作为 value
        )

        # 融合表征 → 效果预测 + 不确定性
        z_joint = torch.cat([z_state, z_causal.squeeze(1)], dim=-1)
        effect_logits = self.effect_predictor(z_joint)
        effect_uncertainty = self.uncertainty_head(z_joint)

        return effect_logits, torch.exp(effect_uncertainty)  # 方差


class CausalCrossAttention(nn.Module):
    """因果交叉注意力 —— 受 ECAM 和 Mask2Cause 启发"""

    def __init__(self, dim, num_heads, causal_mask_provider):
        super().__init__()
        self.attention = nn.MultiheadAttention(
            dim, num_heads, batch_first=True
        )
        self.causal_mask_provider = causal_mask_provider
        # 可学习的因果偏置矩阵
        # B[i,j] = 工具 i 对状态维度 j 的因果注意力偏置
        self.causal_bias = nn.Parameter(
            torch.zeros(num_tools, state_dim)
        )

    def forward(self, query, key, value):
        # 获取 LLM 提供的因果先验作为注意力偏置
        llm_prior = self.causal_mask_provider.get_prior_mask()

        # 可学习的偏置 + LLM 先验 → 因果门控
        causal_gate = torch.sigmoid(self.causal_bias + llm_prior)

        # 在因果门控调制后的 key/value 上做注意力
        key_gated = key * causal_gate.unsqueeze(0)
        value_gated = value * causal_gate.unsqueeze(0)

        output, attn_weights = self.attention(query, key_gated, value_gated)
        return output
```

### 3.4 这个设计的理论基础

1. **"Transformer is inherently a causal learner"** —— 自回归目标施加因果偏置。我们不需要重新发明因果学习，只需要提供正确的架构偏置（时间顺序 + 工具-效果的注意力门控）。

2. **Schölkopf 的"算法因果性"** —— 跨多环境（不同的工具、不同的状态）压缩执行数据 = 学习因果。CAR 的 CausalMemory 已经是在做压缩（从 raw before/after 快照压缩到转移统计），只是压缩算法太原始（桶离散化 + 计数）。

3. **ECAM / Mask2Cause** —— 因果注意力可以被实现为可学习的邻接矩阵门控自注意力。这给了我们一个具体的工程模板。

4. **Do-PFN** —— 因果信号已经存在于预训练模型的 embedding 中。如果我们用一个预训练的 encoder（如微调过的 RoBERTa 或小型 transformer）来编码状态，它可能已经在 embedding 中携带了因果信息。

---

## 四、两条路线的对比

| 维度 | Pearl 路线 (do-calculus) | Emergent 路线 (CRL) |
|------|-------------------------|---------------------|
| **理论基础** | SCM + 后门准则 | 因果表征学习 + 算法因果性 |
| **所需假设** | 已知因果图结构 + 无未观测混杂 | 多环境数据 + 机制变异性 |
| **对 CAR 的适配度** | 低——CAR 的因果图未知且动态变化 | 高——CAR 天然有多环境（不同工具调用）和时滞结构 |
| **工程复杂度** | 中（需实现后门调整 + 混杂识别） | 中-高（需训练小型神经网络） |
| **可解释性** | 高——每步都可以追溯到公式 | 低——潜空间不可直接解释 |
| **可审计性** | 高——决策逻辑透明 | 中——可以提取注意力权重作为审计证据 |
| **泛化能力** | 低——只能在预设的变量空间中推理 | 高——潜空间可以编码未预设的因果结构 |
| **冷启动** | 需要 LLM 提供因果图先验 | 需要预训练或在线学习 |
| **学术叙事** | "第一个在 agent 安全中实现 do-calculus" | "让 agent 安全系统像 LLM 学会语言一样学会因果" |
| **评审风险** | Causal ML 评审会 scrutinize 因果图的质量 | ML 评审可能质疑"你学到了因果还是只是相关" |

---

## 五、综合判断

### 5.1 哪个路线在学术上更强？

**目前是 Pearl 路线。** 因为：
- do-calculus 被充分验证，有明确的正确性标准
- 评审知道如何评价一个后门调整做得好不好
- "第一个在 agent 安全中实现 do-calculus" 是一个干净、可验证的 claim

**但 2027 年可能是 Emergent 路线。** 因为：
- "Transformer is inherently a causal learner" (NeurIPS 2025) 已经为隐式因果学习提供了理论基础
- Arrow, Mask2Cause, Causal-JEPA 在快速推动因果基础模型的成熟
- Schölkopf 的"算法因果性"正在建立一个不同于 Pearl 的理论框架

### 5.2 哪个路线对 CAR 更实际？

**混合路线——Pearl 的解释层 + Emergent 的学习层。**

```
学习层 (Emergent):
  小型 CRL 模型从执行流中学习因果转移的潜空间表征
  → 产出: P(effect | tool, state) + 不确定性

解释层 (Pearl):
  ProofObject 用因果语言 (do-calculus 术语) 解释预测
  → 产出: "为什么是这个决策" + 因果证据链
```

学习层解决了 Pearl 路线在 CAR 中最本质的问题——因果图未知且动态变化。解释层解决了 Emergent 路线最本质的问题——潜空间不透明、难以审计。

具体分工：
- CRL 模型负责**预测**（在潜空间中隐式学到因果转移结构）
- ProofObject + do-calculus 框架负责**解释**（把预测映射到可审计的因果语言）
- CausalMemory (SQLite) 仍然存在——作为 CRL 模型的训练数据源和 ProofObject 的证据来源

### 5.3 推荐的实施策略

```
短期 (1-2 月): 贝叶斯先验 (Pearl 路线, 已验证可行)
  └─ 产出可发表的改进 + 积累更多执行数据

中期 (3-6 月): 探索 CRL 原型 (Emergent 路线)
  ├─ 用 CausalMemory 的数据训练一个小型 CausalTransitionEncoder
  ├─ 与贝叶斯先验版本做对比实验
  └─ 决定长期走哪条路

长期 (6-12 月): 混合架构
  ├─ CRL 学习层 + Pearl 解释层
  └─ 产出第二篇论文: "Learning Causal Transition Models for Agent Safety"
```

---

## 六、对论文叙事的最终建议

不要选边站。**把"Pearl vs Emergent"变成论文的 tension 而非立场。**

论文可以这样叙事：

1. 我们首先尝试了 Pearl 路线——用 do-calculus 实现 agent 安全中的因果推理。我们发现了 X, Y, Z 问题（因果图未知、数据稀疏、隐变量）。

2. 这些问题的根源在于：agent 安全的因果结构是**动态的**（新工具、新状态变量不断出现），而 Pearl 框架假设因果图是静态且已知的。

3. 受到 2025-2026 年因果表征学习进展的启发（"Transformer is inherently a causal learner", Causal-JEPA, Schölkopf 的算法因果性），我们提出了一个替代视角：也许 agent 安全系统不需要显式的因果图，而是可以从执行流中学习因果转移的潜空间表征。

4. 我们提出了混合架构——Emergent 学习 + Pearl 解释——并展示了初步证据。

这种叙事同时尊重了两条路线，避免了选边站的风险，并且把 CAR 定位为**第一个在 agent 安全中面对"Pearl vs Emergent"张力的系统**——这个定位本身就是学术贡献。
