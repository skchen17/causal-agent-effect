# 相关文献详细内容

## 一、直接竞争（与 CAR 核心 idea 最接近）

### 1. SafetyDrift — "Predicting When AI Agents Cross the Line" (Mar 2026)

**作者**: Aditya Dhodapkar, Farhaan Pishori  
**投稿**: COLM 会议

**核心方法**: 将 agent 安全轨迹建模为**吸收马尔可夫链**（absorbing Markov chains），在三个单调状态维度上做转移分析：
- 数据暴露程度
- 工具升级程度
- 操作可逆性

因为状态空间设计为单调的（安全只能恶化，不会自动恢复），所以导出一个理论结果：**每个不被监控的 agent 最终都会违反安全策略——吸收概率 = 1.0**。这改变了问题的框架：不是问 agent "会不会"违规，而是"什么时候"会违规。

**关键结果**:
- 94.7% 违规检出率（对比 LLM 逐步骤评审 52.6%、关键词匹配 44.7%）
- 平均提前 3.7 步预警
- 比 LLM 评审快 60000 倍
- 通信类任务中，到达轻危状态的 agent 有 85% 概率在 5 步内违规
- 评估规模：357 条轨迹，40 个真实任务

**与 CAR 的结构对比**:
SafetyDrift 转移矩阵 ≈ CAR CausalMemory 的 (action, state_pattern) → effects 映射
SafetyDrift 吸收概率 ≈ CAR predict() 的 confidence 输出
差异：SafetyDrift 用正式马尔可夫链 + 吸收态分析，CAR 用频率表 + Laplace 平滑。SafetyDrift 的数学更严谨（有收敛性证明），但 SafetyDrift 是纯预测系统——不做干预决策，不产生审计记录。它的回答是"这个 agent 将在 3.7 步后违规"，但不告诉 agent 应该怎么做。

---

### 2. ProbGuard — "Probabilistic Runtime Monitoring for LLM Agent Safety" (Aug 2025, 修改 Mar 2026)

**作者**: Haoyu Wang, Christopher M. Poskitt, Jiali Wei, Jun Sun  
**开源**: 已集成到 LangChain

**核心方法**: 三步流水线——
1. **符号状态抽象**: 将 agent 执行抽象为离散符号状态
2. **DTMC 学习**: 从执行轨迹中学习离散时间马尔可夫链
3. **概率可达性分析**: 在运行时计算未来到达不安全状态的概率

当预测风险超过用户定义的阈值时，触发干预。

**理论保证**: PAC（Probably Approximately Correct）边界——在标准假设下对学习到的 DTMC 的保真度给出了统计置信度。

**关键结果**:
- 自动驾驶：100% 预测交通违规和碰撞，提前 38.66 秒预警
- 具身家庭 agent：减少 65.37% 不安全行为，同时保持 80.4% 任务完成率
- 引入了最小的运行时开销

**与 CAR 的结构对比**:
ProbGuard DTMC 学习 ≈ CAR CausalMemory.update()
ProbGuard 概率可达性分析 ≈ CAR predict()
核心差异在于**理论深度**: ProbGuard 提供了 PAC 保证——"我们学到的转移概率在概率近似正确的意义上是对的"。CAR 的 Laplace 平滑没有任何保证。ProbGuard 是 CAR 在数学上的"加强版"。

但 ProbGuard 同样缺乏审计链。它告诉你 P(违规) = 0.83，但不记录"为什么是 0.83，哪些历史观测支撑了这个估计，预测和实际结果是否一致"。

---

### 3. GuardAgent — ICML 2025

**作者**: Zhen Xiang et al. (UC Berkeley / UIUC / Stanford 等联合)  
**发表**: PMLR Vol. 267, pp 68316–68342

**核心方法**: 两阶段 pipeline——
1. **任务计划生成**: 分析安全需求 → 生成任务计划
2. **代码映射和执行**: 将计划转换为 guardrail 代码 → 确定性执行安全检查

关键是**记忆模块**: 存储从先前任务中获得的经验。当新的安全检查需求到达时，从记忆中检索相关 past experience 作为 in-context demonstration，提升 LLM 推理质量。

也就是说，GuardAgent 的"学习"不是统计转移，而是用自然语言经验做 in-context learning。

**关键结果**:
- 医疗访问控制基准（EICU-AC）：98%+ 准确率
- 网页 agent 安全基准（Mind2Web-SC）：83% 准确率

**与 CAR 的对比**:
GuardAgent 的记忆模块 ≈ CausalMemory 的思想起点：从历史中学习。但实现路径完全不同：
- GuardAgent: 自然语言经验 → LLM in-context reasoning → 生成代码 → 确定性检查
- CAR: 结构化转移统计 → 频率表 → 置信度计算 → 规则引擎决策

GuardAgent 的优势是灵活（自然语言可以表达复杂的、novel 的安全需求），劣势是每次判断需要调 LLM（延迟、成本、不可审计）。CAR 的优势是轻量、确定性和可审计，劣势是表达能力受限于预定义的效果分类和 bucket 特征。

---

## 二、邻域工作（不同方法，相似动机）

### 4. MOSAIC — "Learning When to Act or Refuse" (Mar 2026)

**作者**: Aradhye Agarwal et al. (Microsoft Research)

**核心方法**: 后训练框架，将 agent 安全决策变为 **plan → check → act or refuse** 循环。安全推理和拒绝对话被设为"一等动作"（first-class actions），让模型在训练中学习何时拒绝。

用**基于偏好的强化学习**，做配对轨迹比较（而非标量奖励）来捕捉安全差异。

**关键结果**:
- 有害行为减少最高 50%
- 注入攻击拒绝率提升 20%+
- 零样本泛化到 Qwen2.5-7B / Qwen3-4B-Thinking / Phi-4

**与 CAR 的区别**: MOSAIC 是训练时的对齐方案（需要 RL 后训练），CAR 是运行时的安全引擎（不需要训练）。两者解决不同层面：MOSAIC 让模型本身更安全，CAR 给模型行为加了一层运行时的因果审计防火墙。

---

### 5. EPO-Safe — "Discovering Safety from 1-Bit Danger Signals" (2025–2026)

**作者**: Vic Galle et al.

**核心方法**: **4 阶段经验循环**:
1. Agent 生成动作计划
2. 收到稀疏二进制危险信号（1 bit/timestep）
3. 反思这些信号
4. 进化自然语言安全规范

关键约束：没有梯度、不知道奖励函数、只能通过自然语言反思来学习安全。所有学到的安全知识编码在自然语言规范中，使其**完全可审计**。

**关键发现**:
- 1–2 轮（5–15 episode）内发现安全行为
- **仅基于奖励的反思会加速 reward hacking**——反思必须有独立的安全通道
- 跨模型复现（Claude Sonnet, Gemini Flash）
- 在 50% 误报噪声下，平均安全性能仅下降 15%

**与 CAR 的关系**: EPO-Safe 的"可审计安全规范"和 CAR 的 ProofObject 共享对审计的关注。差异在于 EPO-Safe 的规范是自然语言（灵活但不精确），CAR 的证据链是结构化的转移统计（精确但表达能力受限）。

---

### 6. RiskGate / Agent Viability Framework (Apr 2026)

**作者**: German Marin, Jatin Chaudhary

**核心方法**: 基于 Aubin 生存理论的运行时治理。定义三个"个别必要且共同充分"的性质来覆盖已知的故障模式：
- P1 监控（观察 agent 状态）
- P2 预测（预测未来不安全状态）
- P3 单调约束（渐进收紧限制）

**RiskGate** 是实现：KL 散度 + segment-vs-rest z 检验 + 序列模式匹配。引入标量**生存指数** VI(t) ∈ [-1,+1]，将治理从被动转为预测式。

**与 CAR 的对比**: RiskGate 的 VI(t) 和 CAR 的 predict().confidence 在概念上相似——都是一个标量分数来表示"现在多安全"。但 RiskGate 用的是统计假设检验（KL 散度、z 检验），CAR 用的是频率统计 + Laplace 平滑。RiskGate 在数学上更复杂，但目前**没有定量实验**（论文明确说定量评估是后续工作）。

---

## 三、关键对比矩阵

| 维度 | CAR | SafetyDrift | ProbGuard | GuardAgent | MOSAIC | EPO-Safe | RiskGate |
|------|-----|-------------|-----------|------------|--------|----------|----------|
| **学习方法** | 频率+Laplace平滑 | 吸收马尔可夫链 | DTMC | LLM+经验检索 | 偏好RL | 自然语言反思 | 统计假设检验 |
| **理论保证** | 无 | 吸收态收敛 | PAC边界 | 无 | RL收敛(隐式) | 无 | 生存分析 |
| **干预方式** | 阻断/确认/放行 | 检测+预警 | 阈值触发干预 | 代码生成确定执行 | 训练后拒绝 | 规范指导行为 | 自动驾驶仪+kill-switch |
| **审计** | ✅ 三层对比 | ❌ | ❌ | ❌ | ❌ | ✅ 规范文本 | ❌ |
| **训练需求** | 零 | 离线拟合 | 离线学习 | 无(LLM推理) | 后训练RL | 无(LLM反思) | 无 |
| **部署形态** | 代理运行时hook | 分析工具 | LangChain插件 | Guardrail代理 | 模型权重 | 对话代理 | 运行时框架 |
| **实验规模** | 无 | 357轨迹 | 2领域 | 2基准 | 3模型/4基准 | 5Gridworld | 无定量 |
