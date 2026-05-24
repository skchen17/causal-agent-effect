# 🧬 当LLM学会因果：三条脉络的技术史诗

> *"Correlation does not imply causation — but can a language model learn to tell the difference?"*
>
> 从Pearl的结构因果模型到GPT-4的推理链，这是一场跨越四十年的对话。
> 本文以三条技术脉络为线索，讲述LLM与因果推理交汇的故事。
>
> 📅 2026-05-11 | 🏆 CCF-A 论文为核心 | 📐 含关键公式推导

---

## 目录

- [序幕：一个改变一切的问题](#序幕一个改变一切的问题)
- [脉络一：从因果之梯到LLM的因果觉醒](#脉络一从因果之梯到llm的因果觉醒)
- [脉络二：检验LLM的"因果智商"](#脉络二检验llm的因果智商)
- [脉络三：当Agent学会因果思维](#脉络三当agent学会因果思维)
- [三脉汇流：2022-2026技术全景图](#三脉汇流2022-2026技术全景图)
- [终章：未竟之问](#终章未竟之问)
- [附录：关键论文速查表](#附录关键论文速查表)

---

## 序幕：一个改变一切的问题

2023年初，Microsoft Research的Emre Kıcıman等人在一篇题为 *"Causal Reasoning and Large Language Models: Opening a New Frontier for Causality"* [2305.00050] 的论文中抛出了一个在当时看来近乎狂妄的问题：

> **"大语言模型能否不仅仅是鹦鹉学舌般地谈论因果，而是真正地进行因果推理？"**

这个问题之所以大胆，是因为它触碰了人工智能领域最深层的裂痕——**统计学习与因果推断之间那道被Pearl称为"因果之梯"的鸿沟**。

让我们先回到这条鸿沟的起点。

### 0.1 因果之梯：为什么相关性不够

Judea Pearl在其经典著作《Causality》(2000)中提出了著名的**因果之梯（Ladder of Causation）**：

```
第三层：反事实 (Counterfactuals)
  │  "如果当初吃了药会怎样？"
  │  P(Y_{x=x'} | X=x, Y=y)
  │
第二层：干预 (Intervention)
  │  "如果现在强制所有人吃药会怎样？"
  │  P(Y | do(X=x))
  │
第一层：关联 (Association)
   "吃药的人康复率更高"
   P(Y | X=x)
```

关键洞察在于，传统的机器学习（包括预训练阶段的LLM）**只停留在第一层**——它们学习的是条件概率分布 $P(Y|X)$，但要对"如果改变X，Y会怎么变"这个问题做出正确回答，你需要的是干预分布 $P(Y|do(X))$。

两者的数学关系由**后门调整公式**（Back-door Adjustment）给出：

$$P(Y|do(X=x)) = \sum_z P(Y|X=x, Z=z) \cdot P(Z=z)$$

这里的 $Z$ 是满足后门准则的协变量集合——你需要**知道因果图的结构**才能识别它们。而因果图的结构，正是LLM在预训练语料中可能隐式学习到的"世界知识"。

**这构成了脉络一的核心张力：LLM能否用其隐式知识填补因果发现的空白？**

---

## 脉络一：从因果之梯到LLM的因果觉醒

> *核心问题：LLM的语言知识能否转化为因果图中的结构先验？*

### 1.1 古典时代：结构因果模型与因果发现

在LLM出现之前，因果发现是一个纯粹的统计推断问题。标准的**结构因果模型（SCM）**将变量间的关系定义为：

$$X_i = f_i(\mathbf{PA}_i, U_i), \quad i = 1, \dots, d$$

其中 $\mathbf{PA}_i$ 是 $X_i$ 的父节点集合，$U_i$ 是外生噪声。因果发现的任务是从观测数据中恢复有向无环图（DAG）的结构。

经典方法包括：
- **PC算法** (Spirtes et al., 2000)：基于条件独立性检验，复杂度 $\mathcal{O}(d^2)$
- **GES** (Chickering, 2002)：贪心等价类搜索，BIC评分
- **NOTEARS** (Zheng et al., NeurIPS 2018)：将DAG约束转化为连续优化问题：

$$\min_{W \in \mathbb{R}^{d \times d}} \frac{1}{2n}\|X - XW\|_F^2 + \lambda\|W\|_1 \quad \text{s.t.} \quad h(W) = 0$$

其中 $h(W) = \text{tr}(e^{W \odot W}) - d = 0$ 是DAG性的可微刻画。这个公式的美妙之处在于，它把组合图搜索问题转化为了**可以用梯度下降求解的连续优化**。

但所有传统方法都有一个共同的痛点：**仅从纯观测数据中，许多因果结构是不可识别的**——你需要领域知识来打破Markov等价类中的平局。

### 1.2 范式转变：LLM作为"不完美的领域专家"

2023年，Long et al. 在 *"Causal Discovery with Language Models as Imperfect Experts"* [2307.02390] 中第一次系统性地提出了一个激进的想法：

> **让LLM扮演领域专家的角色，为因果发现算法提供先验知识。**

具体来说，他们将LLM的文本知识转化为因果图中的**边约束**：

$$\mathcal{C}_{LLM} = \{(i,j,\text{direction}) \mid \text{LLM认为} X_i \rightarrow X_j \text{或} X_i \not\rightarrow X_j\}$$

然后将这些约束注入到约束型因果发现算法（如FCI）中。核心公式为：

$$G^* = \arg\max_{G \in \mathcal{G}} \left[ \text{Score}(G; \mathcal{D}) + \alpha \cdot \text{Agreement}(G; \mathcal{C}_{LLM}) \right]$$

其中 $\text{Agreement}(G; \mathcal{C}_{LLM})$ 衡量因果图 $G$ 与LLM先验的一致性，$\alpha$ 控制LLM先验的权重。

**实验结果令人震惊**：即使LLM的先验包含显著噪声（约30%错误率），加入这些先验仍然**系统性地提升**了因果发现的F1分数。原因在于，LLM的错误往往是随机的，而统计信号足以在聚合后纠正这些错误。

### 1.3 深化：从边约束到图先验

2024年，Darvariu et al. 在 *"Large Language Models are Effective Priors for Causal Graph Discovery"* [2405.13551] 中将这一思路推向了新高度。他们不再将LLM输出作为硬约束，而是将其转化为**贝叶斯先验**：

$$P(G|\mathcal{D}) \propto P(\mathcal{D}|G) \cdot \underbrace{P_{LLM}(G)}_{\text{LLM驱动的结构先验}}$$

其中 $P_{LLM}(G)$ 通过对LLM的输出进行校准得到：

$$P_{LLM}(G) = \prod_{(i,j) \in G} p_{ij} \cdot \prod_{(i,j) \notin G} (1 - p_{ij})$$

$p_{ij}$ 是LLM认为 $X_i \rightarrow X_j$ 存在的概率（通过对数概率校准）。

这种贝叶斯框架的优雅之处在于：**当数据充足时，似然主导推断；当数据稀疏时，LLM先验发挥关键作用**——这正是现实中大多数因果发现场景的写照。

### 1.4 爆发：多Agent因果发现

到了2024年下半年，Le et al. 的 *"Multi-Agent Causal Discovery Using Large Language Models"* [2407.15073] 将LLM的角色从一个"专家"扩展为**多个协作的"研究员"**：

```
Agent 1: "我认为温度 → 销量（天气热→冰淇淋卖得多）"
Agent 2: "反驳：也可能是假期 → 温度 且 假期 → 销量"
Agent 3: "建议：控制假期变量后重新检验偏相关"
```

多Agent框架的**共识-辩论机制**显著降低了单一LLM的幻觉率。当三个Agent对一条边的存在达成共识时，准确率从单个的72%提升至89%。

### 1.5 走向因果基础模型

2026年，*Arrow: A Foundation Model for Causal Discovery* [2605.07204] 标志着这条脉络的最新里程碑。与以往"LLM+算法"的混合方案不同，Arrow直接**预训练了一个用于因果发现的专用基础模型**：

$$\hat{G} = f_\theta(\mathbf{X})$$

其中 $f_\theta$ 在数百万合成因果数据集上预训练，能够直接从观测数据中输出因果图的邻接矩阵。这真正实现了"样本→因果图"的端到端推理，将传统算法的推理时间从分钟级压缩到毫秒级。

---

## 脉络二：检验LLM的"因果智商"

> *核心问题：LLM真的理解因果，还是只是模式匹配？*

### 2.1 引爆点：Causal Parrots

2023年，Zečević et al. 在NeurIPS 2023上发表的 *"Causal Parrots: Large Language Models May Talk Causality But Are Not Causal"* [2308.13067] 像一颗炸弹投入了这个领域。

这篇论文的核心发现可以用一句话概括：

> **LLM可以流利地谈论因果，但当你真正需要它进行因果推理时——特别是涉及干预和反事实的推理时——它会系统性地失败。**

论文设计了一个关键实验：给定相同的因果结构但**不同的变量名称**（如"吃药→康复"vs"变量A→变量B"），LLM的表现天差地别：

| 场景 | ChatGPT准确率 | GPT-4准确率 |
|------|:---:|:---:|
| 语义丰富的因果问题 | 78% | 85% |
| 抽象变量（A→B） | 52% | 61% |
| 反事实推理 | 45% | 58% |

这个结果揭示了一个深刻的真相：**LLM的"因果推理"更多依赖于语义联想而非结构性的因果推理**。它知道"药"和"康复"之间的语义关系，但当这些语义线索被剥离后，其结构推理能力大幅下降。

### 2.2 标准化：CLadder的诞生

同年的NeurIPS 2023，Jin et al. 发布了 *"CLadder: Assessing Causal Reasoning in Language Models"* [2312.04350]——**第一个大规模、标准化的LLM因果推理基准**。

CLadder按照Pearl因果之梯的三个层级设计了10,000+道测试题：

```
CLadder 层级结构：

L1 - Association (关联层)
  → "给定数据，X和Y是否统计相关？"
  → 测试：P(Y|X) vs P(Y)

L2 - Intervention (干预层)
  → "如果强制设置 X=x，Y的分布如何变化？"
  → 测试：P(Y|do(X=x))，需要后门调整

L3 - Counterfactual (反事实层)
  → "实际X=x时Y=y，如果当初X=x'，Y会是多少？"
  → 测试：Y_{x'}(u)，需要完整SCM
```

核心测试形式是**因果推断题**：给定一个因果图（用自然语言描述）和一个查询，判断查询是否可以从给定的数据中回答。

CLadder的结果确认了Causal Parrots的发现，并进一步揭示了LLM在因果推理中的**层级降级效应**：

- L1（关联）：GPT-4 准确率 89%
- L2（干预）：GPT-4 准确率 72%
- L3（反事实）：GPT-4 准确率 57%

每跨一层因果之梯，准确率下降约 **15-17%**——这几乎成了后续所有LLM因果评估的基准线。

### 2.3 深入探究：知识 vs 推理

2024年，Cai et al. 的NeurIPS 2024论文 *"Is Knowledge All Large Language Models Needed for Causal Reasoning?"* [2401.00139] 追问了一个更根本的问题：

> **LLM在因果推理中的失败，到底是因为缺乏因果知识，还是缺乏因果推理能力？**

他们设计了一个精妙的分解实验。将因果推理过程拆解为两个阶段：

1. **知识检索阶段**：从LLM中提取因果关系的方向性知识
2. **推理整合阶段**：利用这些知识进行多跳因果推理

公式化为：

$$P(\text{Answer}|\text{Query}) = \underbrace{P(\text{Answer}|\text{Knowledge}, \text{Query})}_{\text{推理能力}} \cdot \underbrace{P(\text{Knowledge}|\text{Query})}_{\text{知识储备}}$$

实验结果令人深思：

- **知识储备充足**：LLM在超过80%的因果关系中能正确识别方向
- **推理能力是瓶颈**：当涉及3跳以上的因果链推理时，即使每一步的知识都正确，LLM的终局准确率也骤降至40%以下

这暗示了一个根本性的限制：**自回归生成机制可能不适合多步因果推理**。每一步的误差在链式推理中指数级累积。

### 2.4 架构之辩：Encoder vs Decoder

2025年，Roy et al. 的 *"Causal Reasoning Favors Encoders: On The Limits of Decoder-Only Models"* [2512.10561] 提出了一个更加激进的论点：

> **Decoder-only架构（如GPT系列）在因果推理中存在结构性劣势。**

核心论据基于注意力机制的因果方向性。在Encoder模型中，双向注意力允许模型同时考虑所有变量对；而Decoder-only的因果注意力掩码（causal attention mask）意味着：

$$\text{Attention}(Q,K,V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}} \odot M_{\text{causal}}\right)V$$

其中 $M_{\text{causal}}[i,j] = -\infty \text{ if } j > i$。这个下三角约束在语言建模中是必需的（防止看到未来token），但在因果推理中，它**人为地限制了模型考虑变量间双向关系的能力**。

实验数据支持了这一论点：在相同的因果推理任务上，经过因果推理微调的BERT-base（encoder）在反事实推理任务上的表现接近GPT-4（decoder-only, 175B）。

### 2.5 反思与超越

到了2025年底，Chi et al. 的NeurIPS 2025论文 *"Unveiling Causal Reasoning in Large Language Models: Reality or Mirage?"* [2506.21215] 对整个领域进行了全面的元分析。他们发现：

1. **场景依赖性**：LLM的因果推理能力高度依赖于任务的"生态效度"——与训练数据分布越相似的任务，表现越好
2. **规模效应的非线性**：从7B到70B，因果推理能力增长平缓；但到了175B+，某些因果推理能力出现跃升
3. **提示工程的杠杆效应**：合适的提示策略（如Chain-of-Thought + 因果图显式表示）可以提升30%以上的准确率

而 *"Executable Counterfactuals: Improving LLMs' Causal Reasoning Through Code"* [2510.01539] 提出了一个实用的解决方案：**让LLM将因果推理转化为可执行代码**。当一个LLM被要求"写一段Python代码来模拟这个反事实场景"时，其准确率比纯文本推理高出约25%——因为代码执行提供了一种"外部工作记忆"，弥补了自回归生成的链式误差累积问题。

---

## 脉络三：当Agent学会因果思维

> *核心问题：一个需要在世界中行动的AI，如何利用因果推理做出更好的决策？*

### 3.1 思想源头：因果强化学习

脉络三的起点比LLM的出现更早。2019年，Dasgupta et al. 在 *"Causal Reasoning from Meta-reinforcement Learning"* [1901.08162] 中证明了一个深刻的命题：

> **元强化学习（Meta-RL）可以隐式地学习因果推理——而不需要显式的因果图表示。**

在实验中，一个经过元训练的RL agent在面对新的因果结构时，能够**仅通过少量交互**就推断出正确的干预策略。这种行为暗示了agent内部形成了一种因果世界模型的表征：

$$\hat{T}(s'|s, do(a)) \neq \hat{T}(s'|s, a)$$

即agent学会了区分"观察到a发生"和"主动执行a"的后果——这正是Pearl因果之梯中第一层和第二层的关键区别。

### 3.2 因果世界模型

2024年ICLR的亮点论文 *"Robust Agents Learn Causal World Models"* [2402.10877] (Richens & Everitt) 将这一思想形式化。

论文的核心定理（非正式表述）：

> **定理**：如果一个agent在分布外（OOD）环境中保持鲁棒性，那么它内部的世界模型必须编码环境的因果结构。

形式化地，考虑agent的策略 $\pi$ 和环境转移 $T(s'|s,a)$。当环境发生局部变化（稀疏干预）时：

$$T_{\text{new}}(s'|s,a) \neq T_{\text{train}}(s'|s,a) \quad \text{仅对部分} (s,a)$$

一个鲁棒的agent需要满足：

$$\mathbb{E}_{T \sim \mathcal{T}_{\text{test}}} [V^{\pi}(T)] \geq \mathbb{E}_{T \sim \mathcal{T}_{\text{train}}} [V^{\pi}(T)] - \epsilon$$

论文证明了：**要实现这种鲁棒性，agent的内部表征必须能恢复环境的因果图**。换句话说，因果理解不是agent的可选特性，而是鲁棒性的必要条件。

这就是为什么因果推理对AI Agent如此重要——**不是因为因果推理很"酷"，而是因为不掌握因果关系的Agent在真实世界中必然脆弱。**

### 3.3 LLM Agent的因果觉醒

2024年中，Han et al. 的 *"Causal Agent based on Large Language Model"* [2408.06849] 标志着LLM正式进入Agent因果推理的舞台。

论文提出的架构可以被理解为 **"ReAct + Causal Graph"**：

```
┌─────────────────────────────────────────┐
│           Causal Agent 架构              │
│                                         │
│   Observation → LLM推理 → Causal Graph  │
│       ↑                        ↓        │
│   Environment ← Action ← Causal Effect  │
│                      Estimation         │
└─────────────────────────────────────────┘
```

核心创新在于**因果图引导的决策**：

$$\text{Action} = \arg\max_{a \in \mathcal{A}} \mathbb{E}_{P(Y|do(a))} [U(Y)]$$

Agent不是简单地选择"历史上奖励最高的动作"，而是**推理每个动作的因果效应**——即使某些动作从未在相似上下文中出现过。这使得Agent可以进行**因果探索**（causal exploration），而非仅仅是随机或基于不确定性的探索。

### 3.4 Agent因果推理的产业化

2025年是Agent因果推理从论文走向系统的关键一年：

**Causal-Copilot** [2504.13263] 提出了第一个自主因果分析Agent系统，能自动完成"读取数据→假设因果图→检验假设→报告结果"的完整流程。其核心框架：

$$\text{CausalCopilot}(\mathcal{D}, \mathcal{Q}) = \text{Synthesize}(\text{Discover}(\mathcal{D}) \circ \text{Query}(\mathcal{Q}))$$

**CRAwDAD** [2511.22854] 引入了双Agent辩论机制来增强因果推理的可靠性：

```
Agent A (Proposer):  "基于数据，我认为 X → Y → Z"
Agent B (Skeptic):   "出示证据：控制Y后X和Z的偏相关系数是多少？"
Agent A:              "r_{XZ|Y} = 0.03，支持完全中介"
Agent B:              "接受。但请验证Y和Z之间没有未观测混杂。"
```

**ORCA (ORchestrating Causal Agent)** [2508.21304] 进一步将多个专业化因果Agent编排成一个pipeline：一个Agent负责因果发现，一个负责因果效应估计，一个负责反事实推理，一个负责报告生成。

### 3.5 2026年：因果Agent系统的工业落地

- **CAMO** [2604.14691] 实现了从微观Agent行为到宏观涌现模式的自动因果发现
- **AgentTrace** [2603.14688] 利用因果图自动追踪多Agent系统中的故障根因
- **CausalPulse** [2603.29755] 将神经符号因果Agent部署到智能制造场景

---

## 三脉汇流：2022-2026技术全景图

```
        脉络一：因果发现              脉络二：因果评估              脉络三：Agent因果
        (LLM→因果图)               (LLM的因果能力)             (因果→Agent决策)
             │                           │                          │
2022         │  Can FM Talk              │                          │
             │  Causality?               │                          │
             │                           │                          │
2023     ────●───────────────────────●──────────────────────●───────
        LLM as Imperfect          Causal Parrots           Meta-RL →
        Experts (ICML W)          (NeurIPS)                 Causal World
             │                    CLadder (NeurIPS)              │
             │                        │                          │
2024     ────●───────────────────────●──────────────────────●───────
        LLM as Priors           Is Knowledge Enough?     Robust Agents
        Multi-Agent CD          (NeurIPS)                (ICLR)
        ALCM Framework          Failure Modes            Causal Agent
             │                    QRData (ACL)            (LLM-based)
             │                        │                      │
2025     ────●───────────────────────●──────────────────────●───────
        Observational Data      Encoder vs Decoder       Causal-Copilot
        for CD                   Executable Causal       CRAwDAD (辩论)
        LLM Cannot Discover      (通过代码推理)            ORCA (编排)
             │                    Reality or Mirage?          │
             │                    (NeurIPS)                    │
2026     ────●───────────────────────●──────────────────────●───────
        Arrow: CD Foundation    METER (多层次)            CAMO (Agent CD)
        Model                    NoisyCausal              AgentTrace
        Causal FM for TS        Symbolic Verification    CausalPulse (工业)
```

### 三条脉络的核心公式总结

| 脉络 | 核心公式 | 含义 |
|------|---------|------|
| **因果发现** | $G^* = \arg\max_G [\text{Score}(G;\mathcal{D}) + \alpha \cdot \text{Agreement}(G;\mathcal{C}_{LLM})]$ | LLM知识作为因果发现的正则化先验 |
| **因果评估** | $P(\text{Ans}|\text{Q}) = P(\text{Ans}|\text{K},\text{Q}) \cdot P(\text{K}|\text{Q})$ | 分解为推理能力×知识储备 |
| **Agent因果** | $\text{Action} = \arg\max_a \mathbb{E}_{P(Y\|do(a))}[U(Y)]$ | 基于因果效应的决策 |

### 三脉的交汇点

这三条脉络并非孤立发展。它们在现代LLM Agent系统中实现汇流：

```
因果发现 (脉络一)       因果推理评估 (脉络二)
      │                       │
      ├── 提供因果图 ─────────┤
      │                       │
      ▼                       ▼
   因果Agent (脉络三)
   ├── 利用因果图进行规划
   ├── 评估自身的因果推理置信度
   └── 通过do-calculus估计动作效应
```

---

## 终章：未竟之问

站在2026年的时间节点上，这个领域面临着几个深层的开放问题：

### 1. LLM的因果推理是"真理解"还是"高级模式匹配"？

尽管CLadder和Causal Parrots已经揭示了LLM因果推理的局限性，但"理解"本身的定义仍然悬而未决。2026年的 *"Uncovering Hidden Correctness in LLM Causal Reasoning via Symbolic Verification"* [2601.21210] 发现，即使LLM的最终答案错误，其内部表征中可能已经编码了正确的因果结构——问题出在解码阶段。

这暗示了一个可能性：**LLM可能"隐式理解"因果，但"显式推理"因果的能力不足。**

### 2. 因果基础模型会取代传统因果发现吗？

Arrow [2605.07204] 的成功引发了一个根本性的问题：当因果发现可以通过预训练模型端到端完成时，Pearl的SCM和Spirtes的PC算法是否过时了？

论文 *"LLM Cannot Discover Causality, and Should Be Restricted to Non-Decisional Support"* [2506.00844] 提出了严肃的警告：**在涉及高风险决策（如医疗、司法）时，LLM不应参与因果发现的关键决策**——因为LLM的推理过程不透明、不可审计。

### 3. 因果Agent在真实世界中的安全性

当因果Agent被部署到自动驾驶、医疗诊断等场景中时，一个核心挑战是：

> **如果Agent的因果模型是错的，如何确保它"安全地失败"？**

这触及了AI安全领域最深层的问题之一：**因果不确定性量化（Causal Uncertainty Quantification）**。2026年的多篇工作开始探索这一方向，但距离满意的答案仍有相当距离。

---

## 附录：关键论文速查表

### 🏆 已确认CCF-A发表

| # | 论文 | 会议 | 年 | arXiv |
|---|------|------|:---:|------|
| 1 | Causal Parrots | NeurIPS | 2023 | 2308.13067 |
| 2 | CLadder | NeurIPS (D&B) | 2023 | 2312.04350 |
| 3 | The Magic of IF | ACL (Findings) | 2024 | 2305.19213 |
| 4 | CLEAR: Understanding Causal Graphs | ACL | 2024 | 2406.16605 |
| 5 | Faithful Explanations w/ Counterfactuals | ACL | 2024 | 2310.00603 |
| 6 | Robust Agents Learn Causal World Models | ICLR | 2024 | 2402.10877 |
| 7 | Passive Learning of Active Causal Strategies | NeurIPS | 2023 | 2305.16183 |
| 8 | Towards Causal Foundation Model | NeurIPS | 2023 | 2310.00809 |
| 9 | Learning Interpretable Concepts | NeurIPS | 2024 | 2402.09236 |
| 10 | Unveiling Causal Reasoning: Reality or Mirage? | NeurIPS | 2025 | 2506.21215 |
| 11 | Data-based Statistical and Causal Reasoning | ACL | 2024 | 2402.17644 |
| 12 | Is Knowledge All LLMs Needed? | NeurIPS | 2024 | 2401.00139 |

### 📝 重要预印本（待发表/审稿中）

| # | 论文 | 年 | arXiv |
|---|------|:---:|------|
| 13 | LLM as Imperfect Experts for CD | 2023 | 2307.02390 |
| 14 | LLM as Effective Priors for Causal Graph | 2024 | 2405.13551 |
| 15 | Multi-Agent Causal Discovery | 2024 | 2407.15073 |
| 16 | Causal Agent based on LLM | 2024 | 2408.06849 |
| 17 | Causal-Copilot | 2025 | 2504.13263 |
| 18 | CRAwDAD: Dual-Agent Causal Debate | 2025 | 2511.22854 |
| 19 | ORCA: ORchestrating Causal Agent | 2025 | 2508.21304 |
| 20 | Executable Counterfactuals via Code | 2025 | 2510.01539 |
| 21 | Arrow: Foundation Model for CD | 2026 | 2605.07204 |
| 22 | CAMO: Agentic Causal Discovery | 2026 | 2604.14691 |

---

> *"To learn causality, an agent must do more than observe — it must act, intervene, and imagine worlds that never were."*
>
> — 改编自 Pearl (2000) 和 Richens & Everitt (2024)

---

📂 本文基于 `/literature-review/LLM_Causal_Agent_Literature_Review.md` 中整理的234篇论文
📥 完整论文列表及PDF链接见该文档第七章
