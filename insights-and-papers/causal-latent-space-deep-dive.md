# 因果潜空间表征：方法、进展与 CAR 应用

## 一、核心问题

如何让机器学习系统在不依赖显式因果图的情况下，在其潜空间中编码因果结构？这个问题的答案决定了 CAR 能否从"手工 do-calculus"跃迁到"学习因果表征 + 因果语言解释"的混合架构。

---

## 二、理论基础：可识别性

### 2.1 什么是可识别性

在因果表征学习中，可识别性问的是：

> 从观测数据中学到的潜变量 $z$ 是否真正对应了真实世界中的因果变量？

没有可识别性保证，你无法区分"模型学到了因果"和"模型学到了某个方便但不因果的表征"。这是因果表征学习区别于普通表征学习的本质。

### 2.2 2025-2026 年的关键理论进展

#### 最简条件：只需要很少的干预

**Varici et al. (JMLR 2025)** 建立了目前最实用的可识别性框架——基于**得分函数**（score function，即 $\nabla \log p(x)$）的因果表征学习：

| 场景 | 所需干预数量 | 附加条件 |
|------|------------|---------|
| 线性混合 | 每个节点 1 次硬干预 | 无 faithfulness 假设 |
| 非线性（一般）混合 | 每个节点 2 次硬干预 | 不需要知道哪对环境的干预节点相同 |
| 软干预 + 充分非线性 | 每个节点 1 次 | 部分可识别（可识别到父节点混合） |

**核心洞见**: 每个真实因果变量只需要 **1-2 次干预**（即改变该变量的外部操作）就可以在潜空间中被识别。对于 CAR 来说，每次工具调用就是一次对某个"状态变量集合"的干预。

#### 最简数据：跨环境变异性就够了

**Montagna et al. (CLeaR 2025)** 和 **Montagna et al. (ICLR 2026)** 进一步放松了条件：

- 只需要 **2 个环境**（环境间噪声统计不同），即可识别完全的非线性因果图
- 得分函数在潜变量因果发现中可以替代条件独立性检验
- 非线性假设不是必要的——加性噪声模型可以更弱

**对 CAR 的关键意义**: CAR 天然拥有多个"环境"——每次 tool call 就是一个新环境（不同工具产生不同机制变化）。这意味着理论条件可以被满足。

#### 不需要辅助变量：几何方法

**DICA / J-VolMax (NeurIPS 2025)**: 提出**雅可比体积最大化**——一个完全不需要辅助变量、独立性假设或稀疏性假设的可识别性准则。只需要潜变量对观测特征的"影响方向足够多样"（support diversity）。

**意义**: 这意味着我们不需要为 CAR 设计复杂的辅助变量方案——工具的多样性天然提供了足够的 support diversity。

#### 有限样本保证

**Lee, Jin, Aragam (Mar 2026)** 首次从"可识别性理想"走向"有限样本可实现":
- 只需要 **对数数量** 的未知多节点干预——干预目标不需要预先指定
- 同时保证恢复：(a) 潜因果图，(b) 混合矩阵和表征，(c) 未知干预目标

### 2.3 可识别性理论的实用总结

要保证潜空间中的因果表征可识别，需要满足：

1. **最低条件**: 每个因果变量至少有 1-2 次干预（CAR: ✅ 每次 tool call 都是干预）
2. **跨环境变异性**: 不同环境下数据分布有差异（CAR: ✅ 不同工具产生不同效果分布）
3. **充分数据量**: 对数级别的干预足以在有限样本下恢复因果结构（CAR: ✅ 执行历史持续积累）

**结论: CAR 的运行时环境在理论上满足因果表征学习的可识别性条件。** 这不是假设——这是可以从当前架构中导出的结论。

---

## 三、核心架构范式

2025-2026 年涌现了四种主要的因果表征学习架构范式。

### 3.1 VAE 范式：隐式因果潜变量模型

**代表工作**: MOSAIC (May 2026), CausalVAE (Apr 2026), IS-DGM (2025)

**核心思想**: 用 VAE 的编码器将观测映射到潜空间，同时在潜空间中施加因果约束。

```
x (观测) → Encoder → z (潜变量)
                       ↓
              [因果约束: DAG + 干预]
                       ↓
z → Decoder → x̂ (重建)
```

**CausalVAE 的关键创新**: 作为**即插即用模块**——可以附加到任何 encoder-transition 骨干网络上。在物理基准上，反事实命中率 (CF-H@1) 提升 102.5%（平均 8 个基线），在一个 GNN 设置中从 11.0 跳到 41.0（+272.7%）。

**对 CAR 的适用性**: CausalVAE 的"即插即用"特性意味着我们可以保留 CAR 现有的 SQLite CausalMemory 作为训练数据源，在其上附加一个轻量 VAE 来做潜空间因果表征学习。

**关键限制**: VAE 的潜空间维度需要预先指定——对于动态增长的 agent 状态空间，需要支持增量扩展。

### 3.2 得分函数范式：通过梯度学习因果

**代表工作**: Varici et al. (JMLR 2025), Montagna et al. (CLeaR 2025)

**核心思想**: 得分函数 $\nabla_z \log p(z)$（对数概率密度的梯度）在不同干预下会有不同的变化模式。通过学习一个从观测 $x$ 到潜变量 $z$ 的变换，使得 $z$ 的得分函数在跨环境中呈现特定的变化模式，就可以恢复因果结构。

```python
# 得分函数 CRL 的核心损失
loss = reconstruction_loss +
       score_matching_loss +      # 得分函数匹配
       intervention_sparsity_loss  # 干预稀疏性正则化
```

**关键优势**: 
- 理论保证最强（JMLR 2025 给出了完整的可识别性证明）
- 不需要知道哪些环境共享同一个干预节点
- 非参数——不对潜因果模型的函数形式做假设

**对 CAR 的适用性**: 得分函数方法需要估计 $\nabla \log p(x)$——这通常需要训练一个得分网络（如扩散模型中的 denoiser）。计算成本比 VAE 高，但理论保证更强。

### 3.3 Transformer / 注意力范式：因果从架构中涌现

**代表工作**: ECAM (2026), Mask2Cause (May 2026), Arrow (May 2026)

**核心思想**: 因果不是被优化出来的，而是从架构的归纳偏置中涌现的。

**ECAM (Endogenous Causal Attention Mechanism)**: 在 transformer 的自注意力中插入可学习的因果图调制：

```
标准注意力:  softmax(QK^T / √d) V
ECAM 注意力: softmax(QK^T / √d ⊙ M_causal) V

其中 M_causal 是从局部因果图中学习的门控矩阵
```

**Mask2Cause**: 可学习的邻接矩阵直接门控自注意力——在学习时间序列预测的同时学习因果图：

```
Attention_with_causal_gate = Attention ⊙ σ(A_learned)
```

**Arrow**: 将因果发现问题分解为无向骨架 + 拓扑排序——用 transformer 一次前向传播预测完整 DAG。在 1 亿+合成因果发现任务上预训练，零样本匹配专用算法。

**"Transformer Is Inherently a Causal Learner" (NeurIPS 2025)**: 最激进的主张——自回归训练的 decoder-only transformer **本身就是**因果学习者，不需要任何特殊的因果架构。梯度对过去输入的敏感度直接恢复因果图。

**对 CAR 的适用性**: CAR 已经有一个 transformer（LLM）在回路中。问题不是"要不要加一个因果 transformer"，而是"如何从已有的 LLM 表征中提取因果信号"（类似 Do-PFN 的思路）。

### 3.4 JEPA 范式：通过预测学习因果

**代表工作**: Causal-JEPA (Feb 2026), HCLSM (Mar 2026)

**核心思想**: 通过**掩码预测**（masked prediction）施加因果归纳偏置。当模型被迫从其他对象预测一个被掩码对象的潜状态时，它必须学习对象间的交互动态——这天然是因果的。

**Causal-JEPA 的关键机制**:

```
输入场景 → Object Slot Attention → 对象级潜表征
                                        ↓
                        [掩码整个对象, 而非空间块]
                                        ↓
                        从剩余对象预测被掩码对象的潜状态
                                        ↓
                    预测误差 → 迫使模型学习对象间因果交互
```

**核心结果**:
- 反事实推理提升 ~20%（相对于无对象掩码的相同架构）
- 仅需基于 patch 的世界模型 1% 的潜特征即可达到同等控制性能
- 对象掩码被形式化证明为"潜空间中的干预操作"

**HCLSM (Hierarchical Causal Latent State Machines)**: 在此基础上增加了三级时间层次——连续物理（选择性 SSM）→ 离散事件（稀疏 Transformer）→ 抽象目标（压缩 Transformer）——并用 GNN 学习对象间的因果交互。

**对 CAR 的适用性**: Causal-JEPA 的对象掩码思想可以直接转化为 CAR 中的"工具掩码"——遮蔽某个工具，让模型从其他工具的执行模式预测被遮蔽工具的效果。这在结构上等价于学习"如果用了工具 A 会怎样 vs 如果用了工具 B 会怎样"的因果对比。

---

## 四、CAR-CRL：具体架构设计

基于以上四种范式的分析，为 CAR 设计一个混合架构。

### 4.1 设计原则

1. **利用已有的 LLM**: LLM 的表征已经包含因果信号（Do-PFN 的发现），不需要从零训练编码器
2. **干预天然的可用性**: CAR 的每次 tool call = 一次干预，满足可识别性的最低条件
3. **轻量化**: 不能显著增加工具调用的延迟
4. **可审计性**: 潜空间表征需要能映射回人类可理解的因果语言

### 4.2 架构概览

```
┌──────────────────────────────────────────────────────────┐
│                    CAR-CRL 混合架构                        │
│                                                          │
│  工具调用 ──→ [LLM 嵌入层] ──→ z_llm (冻结或微调)        │
│       │                                                   │
│       ├──→ [状态编码器] ──→ z_state                       │
│       │         │                                         │
│       │    [因果交叉注意力] ← 受 ECAM 和 Causal-JEPA 启发   │
│       │         │                                         │
│       │    z_causal = CrossAttn(                          │
│       │      query=z_tool,                                │
│       │      key=z_state ⊙ M_causal,    ← 可学习因果门控   │
│       │      value=z_state                                │
│       │    )                                              │
│       │         │                                         │
│       └──→ [融合层] ──→ z_joint                           │
│                 │                                         │
│            [效果预测头] ──→ P(effect | tool, state)        │
│            [不确定性头] ──→ Var(effect | tool, state)      │
│            [因果归因头] ──→ attention_weights (可审计)      │
│                                                          │
│  ─────────────── 解释层 (Pearl 侧) ───────────────        │
│                                                          │
│  因果归因权重 ──→ ProofObject.causal_attribution           │
│  效果预测 ──→ ProofObject.predicted_effects               │
│  不确定性 ──→ ProofObject.evidence_quality                │
└──────────────────────────────────────────────────────────┘
```

### 4.3 关键组件

#### 组件 1: LLM 嵌入提取器

```python
class LLMEmbeddingExtractor:
    """从 LLM 的隐藏状态中提取因果相关表征

    依据: Do-PFN (2025) 证明预训练模型的冻结 embedding 已包含因果信号
    """
    def __init__(self, llm_backend):
        self.llm = llm_backend
        # 不对 LLM 做微调——使用冻结权重
        # 只训练一个轻量投影头

    def extract(self, tool_name, args, state):
        # 构造上下文
        context = self._format_context(tool_name, args, state)

        # 提取 LLM 的多层隐藏状态
        hidden_states = self.llm.get_hidden_states(
            context,
            layers=[-1, -4, -8]  # 最后 3 层的不同抽象级别
        )

        # 投影到统一维度
        z_llm = self.projection(torch.cat(hidden_states, dim=-1))
        return z_llm
```

**关键决策**: 使用 LLM 的**冻结** embedding（不微调），只训练投影头。理由：
- Do-PFN 证明冻结 embedding 中已有因果信号
- 微调 LLM 的计算成本太高
- 冻结保证了表征的稳定性和可复现性

#### 组件 2: 因果交叉注意力

这是最核心的创新——借鉴 ECAM 和 Causal-JEPA 的思想，设计一个因果门控的交叉注意力层。

```python
class CausalCrossAttention(nn.Module):
    """因果交叉注意力 —— 工具如何因果地关注状态的不同维度"""

    def __init__(self, d_model, num_tools, num_state_dims):
        super().__init__()
        # 可学习的因果邻接矩阵
        # A[i,j] = 工具 i 对状态维度 j 的因果效应强度（先验）
        self.causal_adjacency = nn.Parameter(
            torch.zeros(num_tools, num_state_dims)
        )

        # LLM 先验偏置（从 LLM embedding 中提取的因果方向）
        self.llm_prior_proj = nn.Linear(d_model, num_state_dims)

        # 交叉注意力
        self.cross_attn = nn.MultiheadAttention(
            d_model, num_heads=4, batch_first=True
        )

    def forward(self, z_tool, z_state, z_llm_prior):
        # Step 1: 构造因果门控矩阵
        llm_prior = torch.sigmoid(self.llm_prior_proj(z_llm_prior))
        causal_gate = torch.sigmoid(self.causal_adjacency) * llm_prior

        # Step 2: 因果门控调制状态表征
        z_state_gated = z_state * causal_gate.unsqueeze(-1)

        # Step 3: 因果交叉注意力
        z_causal, attn_weights = self.cross_attn(
            query=z_tool.unsqueeze(1),
            key=z_state_gated,
            value=z_state_gated
        )

        return z_causal.squeeze(1), attn_weights, causal_gate
```

**因果门控的语义**:
- `causal_adjacency[i,j]` 在训练中学习"工具 i 对状态维度 j 有因果效应"的强度
- `llm_prior[j]` 是 LLM 对"状态维度 j 是否是因果相关的"的语义判断
- 两者相乘：经验证据 × 语义先验 → 因果门控
- 注意力权重可以直接提取到 ProofObject 中作为审计证据

#### 组件 3: 效果预测与不确定性

```python
class CausalEffectPredictor(nn.Module):
    """从潜空间表征预测工具效果 + 不确定性"""

    def __init__(self, d_model, num_effects, num_risks):
        super().__init__()
        # 效果预测
        self.effect_head = nn.Sequential(
            nn.Linear(d_model, 128),
            nn.LayerNorm(128),
            nn.GELU(),
            nn.Linear(128, num_effects)
        )

        # 风险预测
        self.risk_head = nn.Sequential(
            nn.Linear(d_model, 64),
            nn.GELU(),
            nn.Linear(64, num_risks)
        )

        # 认知不确定性 (epistemic) —— 来自模型参数的不确定性
        self.epistemic_head = nn.Sequential(
            nn.Linear(d_model, 64),
            nn.GELU(),
            nn.Linear(64, num_effects)
        )

        # 偶然不确定性 (aleatoric) —— 来自数据本身的不确定性
        self.aleatoric_head = nn.Sequential(
            nn.Linear(d_model, 64),
            nn.GELU(),
            nn.Linear(64, num_effects)
        )

    def forward(self, z_causal):
        effect_logits = self.effect_head(z_causal)
        risk_logits = self.risk_head(z_causal)

        # 使用 MC Dropout 估计认知不确定性
        epistemic_var = self._mc_dropout_forward(z_causal)

        # 偶然不确定性通过对数方差估计
        aleatoric_logvar = self.aleatoric_head(z_causal)

        total_uncertainty = epistemic_var + torch.exp(aleatoric_logvar)

        return effect_logits, risk_logits, total_uncertainty
```

### 4.4 训练策略

```python
class CARCRLTrainer:
    """CAR-CRL 的在线学习训练器"""

    def __init__(self, model, memory, llm_backend):
        self.model = model
        self.memory = memory  # 现有的 SQLite CausalMemory
        self.llm = llm_backend

    def online_update(self, tool_name, before_state, after_state, success):
        """每次工具调用后的增量更新"""
        # Step 1: 计算实际效果（ground truth）
        actual_effects = _diff_state(before_state, after_state)

        # Step 2: 获取 LLM embedding（缓存友好的批量处理）
        z_llm = self.llm_extractor.extract_cached(tool_name, before_state)

        # Step 3: 前向传播 → 预测
        with torch.no_grad():
            # 先做无梯度的预测（用于对比）
            pred_effects, pred_risks, uncertainty = self.model.predict(
                tool_name, before_state, z_llm
            )

        # Step 4: 计算多维损失
        loss = (
            self._effect_loss(pred_effects, actual_effects) +
            0.1 * self._uncertainty_calibration_loss(uncertainty, actual_effects, pred_effects) +
            0.01 * self._causal_sparsity_loss(self.model.causal_adjacency) +
            0.05 * self._consistency_loss(pred_effects, self.memory.predict(tool_name, before_state))
            # ↑ 与 SQLite 记忆中的频率统计保持一致的正则化
        )

        # Step 5: 单步梯度更新（在线学习，不重训全量）
        loss.backward()
        self.optimizer.step()
        self.optimizer.zero_grad()

        # Step 6: 更新 SQLite 记忆（保持双轨——CRL + 频率统计）
        self.memory.update(
            action_name=tool_name,
            before_state=before_state,
            after_state=after_state,
            success=success,
            effects=actual_effects,
            risks=[],
        )
```

### 4.5 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| LLM 权重 | 冻结 | Do-PFN 证明冻结 embedding 有因果信号；微调成本过高 |
| 训练方式 | 在线增量 | CAR 的数据是流式的——不需要离线批量重训 |
| 双轨架构 | CRL + SQLite 并行 | CRL 做预测，SQLite 做校准和审计 |
| 可审计性 | 注意力权重 → ProofObject | 交叉注意力的权重直接编码了"哪个状态维度驱动了哪个效果预测" |
| 因果门控 | 可学习 + LLM 先验 | 经验数据 + 语义知识 = 因果门控 |

---

## 五、与竞争方法的对比

### 5.1 因果潜空间表征方法对比

| 方法 | 范式 | 理论保证 | 需要干预 | 计算成本 | CAR 适用性 |
|------|------|---------|---------|---------|-----------|
| CausalVAE (Apr 2026) | VAE | 中 | 是 | 低 | ⭐⭐⭐⭐ 即插即用 |
| Score-based CRL (JMLR 2025) | 得分函数 | **强** | 1-2/节点 | 中-高 | ⭐⭐⭐ 理论最优但成本高 |
| ECAM (2026) | Transformer | 弱 | 否 | 低 | ⭐⭐⭐⭐⭐ 最适配 CAR |
| Causal-JEPA (Feb 2026) | JEPA | 中 | 潜干预 | 低 | ⭐⭐⭐⭐ 掩码机制可迁移 |
| Arrow (May 2026) | Foundation | 中 | 否 | 极低(推理) | ⭐⭐ 通用模型不专门化 |
| Do-PFN (2025) | PFN | 中 | 否 | 低 | ⭐⭐⭐ 利用已有 embedding |

### 5.2 为什么 ECAM 范式最适合 CAR

1. **注意力机制天然适配**: CAR 的工具-状态-效果三元组可以被自然地表达为注意力计算
2. **LLM 已在回路中**: ECAM 不需要额外的编码器——可以直接复用 LLM 的隐藏状态
3. **可审计性**: 注意力权重是天然的解释——"哪个状态维度驱动了决策"
4. **增量学习**: 因果邻接矩阵可以在线更新，不需要全量重训
5. **因果门控**: 可学习的因果门控 + LLM 先验 = "从经验中学习 + 从知识中引导"的组合

---

## 六、开放挑战

### 6.1 理论挑战

1. **可识别性的 gap**: 理论说 1-2 次干预/节点足够，但 CAR 的"干预"（工具调用）不是随机的——用户选择工具的方式存在强烈的选择偏倚。非随机的干预可能不满足可识别性条件。

2. **非稳态因果图**: CAR 的工具集会随时间变化（新增/禁用工具），因果图本身是动态的。现有的可识别性理论假设因果图在一段时间内不变。

3. **隐混杂**: 工具效果可能受到未观测变量的影响（用户意图、外部环境变化）。潜空间表征可能学到虚假关联而非因果。

### 6.2 工程挑战

1. **延迟约束**: 每次工具调用前都需要 CRL 模型做一次前向传播。如果在 LLM 推理之外增加了显著的延迟，用户体验会受影响。

2. **冷启动**: CRL 模型需要训练数据——刚开始时没有足够的执行历史。需要依赖 LLM 先验（类似贝叶斯先验方案）度过冷启动期。

3. **灾难性遗忘**: 在线增量学习可能导致模型忘记旧的因果模式。需要 replay buffer 或 elastic weight consolidation。

4. **LLM 嵌入的稳定性**: 如果 LLM 后端切换（从 GPT-4 到 Claude），其 embedding 空间会发生显著变化。需要重新校准投影头。

### 6.3 审计挑战

1. **注意力 ≠ 因果**: 注意力权重高不等于因果效应强——可能只是相关性。需要验证注意力归因的有效性。

2. **潜空间的不透明性**: 即使有注意力权重，潜空间的维度不一定对应人类可理解的概念。需要额外的"潜空间→因果语言"的映射层。

---

## 七、实施路线

```
阶段 1 (1-2 月): 最小可行性原型
  ├── 冻结 LLM embedding 提取器
  ├── 简单因果交叉注意力（不含 LLM 先验）
  ├── 多标签效果分类
  └── 与 SQLite CausalMemory 并行运行（不替代）

阶段 2 (2-4 月): 因果门控 + 不确定性
  ├── 加入可学习因果邻接矩阵
  ├── 加入 LLM 先验调制
  ├── 认知/偶然不确定性分解
  └── 离线评估：CRL vs SQLite 的预测精度

阶段 3 (4-8 月): 在线学习 + 审计集成
  ├── 在线增量训练
  ├── 注意力权重 → ProofObject 的因果归因字段
  ├── 在真实 Hermes 使用中收集数据
  └── 实验：对比 CRL vs 频率统计 vs SafetyDrift

阶段 4 (8-12 月): 论文撰写
  ├── 核心 claim: "第一个在 agent 安全中使用因果表征学习"
  ├── 关键实验：可识别性验证 + 审计完整性的消融
  └── 开源：CAR-CRL 作为 Hermes 的独立插件
```
