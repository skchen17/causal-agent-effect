# 文献对比分析：CAR 自改进安全 vs 最新相关工作

## 搜索范围

2025–2026 年顶会/顶刊，关键词覆盖 agent safety、runtime policy learning、causal effect prediction、transition statistics、adaptive permission systems。

---

## 核心发现：这个方向非常热，且竞争激烈

到 2026 年 5 月，至少有 **8–10 篇顶会论文**在探索同一核心思想——从 agent 执行历史中学习安全策略。CAR 的"自改进安全"不是孤立的 idea，而是一个正在被多个组用不同方法追逐的方向。

---

## 最直接相关的竞争工作（按威胁等级排序）

### 🔴 高威胁：直接竞争

#### 1. SafetyDrift (arXiv, Mar 2026)
**方法**: 吸收马尔可夫链建模 agent 安全轨迹。三个状态维度（数据暴露、工具升级、可逆性）在马尔可夫链上转移，预测"何时越界"。
**结果**: 94.7% 检出率，3.7 步提前预警。"每个 agent 如果不被监控，最终都会违反安全——吸收概率 = 1.0。"
**与 CAR 的关系**: 直接撞车。同样是从执行历史中学习状态转移来预测安全违规。不同的是 SafetyDrift 用正式马尔可夫链 + 吸收态分析，CAR 用 Laplace 平滑的频率表。SafetyDrift 的数学更扎实。
**CAR 的差异化可能**: SafetyDrift 是纯预测（predict when violations occur），不做干预决策。CAR 包含 PolicyEngine → 决策 + ProofObject → 审计的完整闭环。

#### 2. Pro2Guard / ProbGuard (arXiv, Aug 2025)
**方法**: 离散时间马尔可夫链（DTMC）+ 概率可达性分析。从执行轨迹学习转移概率，计算到达不安全状态的概率，触发干预。
**结果**: PAC 式正确性保证。自动驾驶中 100% 预测交通违规（提前 38.66 秒）。具身 agent 中减少 65.37% 不安全行为。
**与 CAR 的关系**: 更形式化的 CAR。DTMC 学习 = CAR 的 CausalMemory 但要严格得多。概率可达性 = CAR 的 predict() 但有理论保证。
**CAR 的差异化可能**: Pro2Guard 的 DTMC 状态空间是手工定义的，不是学出来的。CAR 的状态模式提取（`_state_pattern`）自动发现特征 + 动态发现布尔标志。但这个差异化偏弱。

#### 3. SafePred (arXiv, Feb 2026)
**方法**: World model 预测短期和长期风险。Risk-to-decision loop 将预测风险与当前决策对齐。
**结果**: >97.6% 安全性能，比 reactive baseline 高出 21.4% 任务效用。
**与 CAR 的关系**: 同样做预测性安全，但用 world model 而非频率统计。world model 可以泛化到未见过的状态组合，CAR 的离散化 bucket 不能。
**CAR 的差异化可能**: SafePred 需要训练 world model，CAR 不需要训练——SQLite 增量更新，部署即学习。

#### 4. GuardAgent (ICML 2025)
**方法**: Guardrail agent 用 LLM + 经验记忆模块存储过去的任务执行，动态检查目标 agent 动作是否符合安全策略。生成 guardrail 代码做确定性执行。
**结果**: 医疗/网页 agent 基准上 98%+ 准确率。
**与 CAR 的关系**: 记忆模块的核心思想非常相似——存储过去执行经验，用于当前决策。但 GuardAgent 记忆的是自然语言经验，CAR 记忆的是结构化转移统计。GuardAgent 依赖 LLM 做推理，CAR 用简单频率统计。
**CAR 的差异化可能**: CAR 不依赖 LLM 做安全决策（轻量、低延迟、可审计），GuardAgent 每次安全判断都要调 LLM。CAR 的审计链更完整。

---

### 🟡 中威胁：邻域竞争

#### 5. Firewalled Agentic Networks (Microsoft Research, 2025)
从先前对话中自动推导任务安全规则。防火墙设计（数据/轨迹/输入三层）。与 CAR 共享"从执行中学习规则"的核心 idea，但架构不同。

#### 6. TBAC + LLM Judge — 不确定性感知的访问控制 (Oct 2025)
LLM 作为风险感知裁判，计算复合风险分数 + 模型不确定性，高风险/高不确定性升级给人类。与 CAR 的置信度→决策映射有结构相似性。

#### 7. ALTK-Evolve (IBM, Apr 2026)
将原始 agent 轨迹转换为可复用指南（原则而非转录）。+14.2% 在困难多步任务上。与 CAR 的"从执行中学习"共享动机，但 ALTK-Evolve 学习的是操作指南而非安全策略。

#### 8. RiskGate / Agent Viability Framework (Apr 2026)
基于 Aubin 生存理论的运行时治理。KL 散度 + z 检验 + 序列模式匹配。引入标量生存指数 VI(t)。数学上比 CAR 强得多，但抽象度更高，工程落地距离更远。

#### 9. Causal Influence Prompting (ACL 2025 Findings)
因果关系图（CID）建模 agent 决策中的因果关系。从任务规格初始化，从观察中迭代更新。与 CAR 的"因果"宣称有重叠但方法完全不同——CID 是 LLM prompt，CAR 是频率统计。

#### 10. Safactory (May 2026)
闭环流水线：平行仿真→可信数据→自主进化。与 CAR 共享"封闭学习循环"理念，但规模完全不同——Safactory 是训练基础设施，CAR 是轻量运行时安全。

---

## 诊断：CAR 的位置在哪里？

### CAR 的真实优势

| 维度 | CAR | 竞争工作 |
|------|-----|---------|
| **部署开销** | 零训练，SQLite 增量更新 | SafetyDrift/Pro2Guard 需离线训练马尔可夫链 |
| **审计完整性** | ProofObject 三层对比（预测/决策/实际） | 多数只记录决策，不记录因果证据 |
| **决策可解释性** | 每个 block 可追溯到具体 transition + 置信度 | GuardAgent 依赖 LLM 推理，难审计 |
| **集成深度** | 已集成到 Hermes agent 的 pre/post tool hook | 多数是研究原型 |
| **冷启动处理** | bootstrap 保守策略 → 渐进学习 | 多数假设已有训练数据 |

### CAR 的真实劣势

| 维度 | CAR | 竞争工作 |
|------|-----|---------|
| **理论深度** | Laplace 平滑 + 桶离散化 | SafetyDrift 用吸收马尔可夫链，Pro2Guard 用 PAC 理论 |
| **形式保证** | 无 | Pro2Guard 有 PAC 保证，Conformal Policy Learning 有限样本保证 |
| **状态泛化** | 离散 bucket，未见组合无法处理 | SafePred 的 world model 可泛化 |
| **实验规模** | 无公开基准评估 | SafetyDrift 在多个 agent 任务上评估，GuardAgent 在医疗/网页基准上评估 |
| **安全收敛证明** | 无 | SafetyDrift 证明了吸收概率 = 1.0 |

### CAR 最致命的 gap

**Laplace 平滑太弱了。** 在 SafetyDrift 用吸收马尔可夫链给出收敛性证明、Pro2Guard 用 DTMC 给出 PAC 理论保证的竞争环境中，CAR 的频率表 + Laplace 平滑在理论上处于明显的劣势。如果投 NeurIPS/ICML，评审 100% 会指出这一点。

---

## 重新评估 5 个论点的竞争前景

| 论点 | 原评估 | 文献对比后修正 | 理由 |
|------|--------|---------------|------|
| #3 自改进安全 | ⭐⭐⭐ | ⭐⭐ | SafetyDrift/Pro2Guard 已经用更强的数学做了相同的事 |
| #1 因果预测 | ⭐⭐ | ⭐ | Causal Influence Prompting 的 CID 比 CAR 的关联频率更接近"因果" |
| #2 f(效果,置信度,上下文) | ⭐⭐ | ⭐⭐ | TBAC+LLM Judge 也在做类似的事，但用 LLM 而非规则引擎 |
| #4 可审计 | ⭐ | ⭐⭐⭐↑ | 文献对比后，这恰恰是 CAR 最大的差异化优势！没有竞争对手做了三层对比审计 |
| #5 冷热一致性 | — | — | 不变 |

**重要修正**: 可审计性从最弱论点变成了最强差异化优势。因为几乎所有竞争工作在安全决策的可解释性和可审计性上都远弱于 CAR。SafetyDrift 告诉你 violation 会发生但不告诉你为什么，GuardAgent 告诉你结果但不留下可追溯的证据链。CAR 的 ProofObject 三层对比（预测→决策→实际）是独特的。

---

## 重新评估 3 个论文方向

### 方向 A: AI Safety — 仍然可行，但需重新定位

**原定位**: "自改进安全"  
**修正定位**: "**可审计的自改进安全**"——强调不只能自改进，而且每一步改进都有可追溯的证据链

竞争论文的核心弱点正好是 CAR 的强项：
- SafetyDrift 预测了但没解释
- Pro2Guard 保证了但没审计
- GuardAgent 决策了但没留痕

CAR 提供了三者都缺的东西：**完整的因果审计链**。这是唯一一个把 safety decision provenance 作为一等公民的系统。

论文角度可以改为：*Safety is not just about blocking violations — it's about being able to explain, after the fact, why each decision was made, and that explanation must cite empirical evidence, not model internals.*

### 方向 B: Agent 系统 — 机会上升

系统论文可以这样定位：**第一个在真实 agent 系统中部署的、带审计功能的自改进安全引擎**。竞争工作都是研究原型，CAR 已经集成在 Hermes 中。

### 方向 C: 因果推断 — 仍然不建议

文献搜索确认了诊断：真正的因果推断工作（Causal Influence Prompting）用因果图 + 迭代更新，与 CAR 的统计关联不在同一层面。放弃这个方向是正确的。

---

## 关键建议

### 1. 不要和 SafetyDrift/Pro2Guard 拼数学

Laplace 平滑拼不过吸收马尔可夫链和 PAC 理论。不要尝试在数学深度上竞争——那是追不上的（且方向不对）。

### 2. 把可审计性推成核心贡献

这是 CAR 真正独特的地方。所有竞争工作都忽略了审计。把 ProofObject 从辅助模块升级为核心卖点：

```
不是: "我们学到了一个更好的安全预测模型"
而是: "我们展示了安全决策的可审计证据链，并且这个证据链随执行次数增长而变得更可靠"
```

### 3. 做实验时要包含审计维度

除了传统的 precision/recall/F1，增加一个独有的指标维度：
- **可追溯率**: 多少个安全决策可以追溯到具体 causal evidence
- **证据充分度**: 平均每个决策背后有多少条观测支持
- **覆盖增长曲线**: 随执行次数增加，有多少比例的工具调用被因果记忆覆盖（从 bootstrap 迁移到 evidence-based）

### 4. 考虑安全领域的定位

投稿时不要把 CAR 定位为"另一种 agent 安全方法"——那会让它进入和 SafetyDrift/Pro2Guard 的直接比较。定位为：

> **Provenance-first agent safety**: an approach where every safety decision carries a verifiable evidence chain, enabling post-hoc audit that is impossible with statistical-only or LLM-based approaches.

这个 niche 在当前文献中是空的。
