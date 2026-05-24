---
name: agent-causal-safety-research
description: Agent 安全因果可解释性研究项目 — 从 CAR 架构探索到因果抽象理论的完整研究议程
type: project
originSessionId: f876b3bb-0ab5-4944-84f3-c1dd51705ce0
---
# Agent 安全因果可解释性研究

## 项目起源

用户拥有 HERMES CAR (Causal Agent Runtime) 项目 (`/home/administrator/hermes-car/`)——一个基于因果效应预测的 agent 安全引擎。核心思想是"Decision = f(predicted_effects, confidence, state_context)"而非传统的"Decision = f(tool_name, static_list)"。

但 CAR 是一个**未验证的空架子**——约 500 行 Python 设计文档，没有部署，没有执行数据，ProofObject 审计日志是空目录。不能直接依赖 CAR 做实验。

## 探讨过程

### 阶段 1: CAR 架构提炼 (2026-05-11)
- 提炼了 5 个核心论点和 3 个论文定位方向
- 文档: `insights-and-papers/car-policy-engine-core-thesis.md`
- 文档: `insights-and-papers/core-arguments-potential-evaluation.md`

### 阶段 2: 文献对比分析
- 搜索了 2025-2026 年最相关的 agent 安全论文
- 关键发现: SafetyDrift (吸收马尔可夫链), ProbGuard (DTMC+PAC), GuardAgent (ICML 2025) 等都在做类似的事
- 诊断: CAR 的"自改进"核心论点在理论上落后（Laplace 平滑 vs 马尔可夫链/PAC 保证）
- 转折发现: **所有竞争工作都忽略了可审计性**——这是 CAR 差异化优势
- 文档: `insights-and-papers/literature-comparison-analysis.md`
- 文档: `insights-and-papers/related-literature-details.md`

### 阶段 3: 因果推理深度探索
- 研究了 Pearl 路线 (do-calculus) vs Emergent 路线 (隐式因果表征学习)
- 阅读了关键文献: Causal-JEPA, Arrow, ECAM, Mask2Cause, Schölkopf 的算法因果性
- 提出混合路线: CRL 学习层 + Pearl 解释层
- 文档: `insights-and-papers/theoretical-improvement-proposals.md`
- 文档: `insights-and-papers/causal-reasoning-feasibility-analysis.md`
- 文档: `insights-and-papers/beyond-pearl-implicit-causal-learning.md`

### 阶段 4: 因果潜空间表征深度研究
- 研究了可识别性理论 (Varici et al., JMLR 2025; Lee et al., 2026)
- 四种范式: VAE, 得分函数, Transformer/注意力, JEPA
- 提出 CAR-CRL 混合架构设计
- 文档: `insights-and-papers/causal-latent-space-deep-dive.md`

### 阶段 5: 因果可解释性机理深化 (关键转折)
- 用户指出"不想做 A+B 拼凑研究"
- 发现 NeurIPS 2025 Spotlight: "非线性表征困境"——不加线性约束的因果抽象在数学上是空洞的
- 建立三条研究路径:
  - **路径一 (因果抽象+线性约束)**: 用 interchange intervention 验证 agent 安全表征是否真正编码了因果效果 ← **选定**
  - 路径二 (层析因果一致性): 数学门槛最高，长期储备
  - 路径三 (因果区分概念): Tatsat & Shater (May 2026) 已占据 SAE+agent 位置，差异化难度高
- 文档: `insights-and-papers/causal-interpretability-mechanism.md`
- 文档: `insights-and-papers/honest-assessment-and-gaps.md`

### 阶段 6: 五篇学习文档
- 用户要求按学习路线创建五篇结构化文档，包含论文翻译和解析:
  1. `learning-doc-1-causal-abstraction-foundations.md` — 因果抽象定义 + IIT
  2. `learning-doc-2-distributed-alignment-search.md` — DAS 方法
  3. `learning-doc-3-nonlinear-representation-dilemma.md` — 非线性困境
  4. `learning-doc-4-linear-representation-hypothesis.md` — LRH
  5. `learning-doc-5-car-application-framework.md` — CAR 应用框架 + 实验设计

### 阶段 7: 独立研究项目 (2026-05-12)
- 用户决定在根目录创建独立项目，不与 CAR 或 Hermes 耦合
- 项目路径: `/home/administrator/causal-agent-safety-research/`
- 第一个实验: **哪些 agent 工具调用的因果效果被 LLM 表征线性编码？**
- 项目文档: `causal-agent-safety-research/EXPERIMENT_PLAN.md`

## 当前状态 (2026-05-12)

### 研究问题
在 agent 安全场景中，LLM 内部表征是否以线性可编码的方式编码了工具调用的因果效果？

### 核心假设
- H1: 高频因果效果被线性编码（线性探针 F1 > 0.7）
- H2: 低频因果效果不被线性编码
- H3: 安全关键效果（HIGH tier）的线性编码质量影响安全决策的可靠性

### 已创建的研究基础设施
- `causal-agent-safety-research/generate_data.py` — 模板数据生成（900 条场景，11 个效果，9 个工具）✓ 已运行
- `causal-agent-safety-research/extract_embeddings.py` — LLM 嵌入提取（sentence-transformers）
- `causal-agent-safety-research/train_probes.py` — 线性探针训练 + F1/AUC 排名 + 可视化
- 依赖正在安装中 (sentence-transformers, sklearn, matplotlib)

### 下一步
1. 跑通 `run_all.sh` 全流程，获取第一批线性可编码性测量结果
2. 如果模板数据效果不错，扩展数据源（LLM 合成数据、真实执行数据）
3. 对比线性 τ vs 非线性 τ（实验 3）验证非线性困境在 agent 安全中的表现
4. 如果存在 Δ≈0 的因果效果 → 线性约束的因果抽象在 agent 安全中是可行的
5. 准备论文: "Provenance-first agent safety: verifying causal representations through linear abstraction"

## 关键文献

### 核心理论基石
- Geiger et al. (NeurIPS 2021) — Causal Abstractions of Neural Networks (arXiv: 2106.02997)
- Geiger et al. (ICML 2022) — Inducing Causal Structure / IIT (arXiv: 2112.00826)
- Geiger et al. (JMLR 2025) — Causal Abstraction: Theoretical Foundation (arXiv: 2301.04709)
- Sutter et al. (NeurIPS 2025 Spotlight) — Non-Linear Representation Dilemma (arXiv: 2507.08802)

### 竞争文献
- SafetyDrift (Mar 2026) — Absorbing Markov chains for agent safety prediction (arXiv: 2603.27148)
- ProbGuard (Aug 2025) — DTMC + PAC guarantees for agent runtime safety (arXiv: 2508.00500)
- GuardAgent (ICML 2025) — LLM guardrail with experience memory

### 因果表征学习
- Varici et al. (JMLR 2025) — Score-based CRL: 1-2 interventions per node sufficient
- CausalVAE (Apr 2026) — Plug-in causal module for world models (arXiv: 2604.07712)
- Causal-JEPA (Feb 2026) — Object-level masking induces causal bias (arXiv: 2602.11389)
- ECAM (2026) — Endogenous causal attention mechanism
- Arrow (May 2026) — Foundation model for causal discovery (arXiv: 2605.07204)
- "Transformer Is Inherently a Causal Learner" (NeurIPS 2025)

### 因果抽象与可解释性
- CAN: Networks of Causal Abstractions (arXiv: 2509.25236v3) — 层析因果一致性
- "Causal Differentiating Concepts" (NeurIPS 2025) — 稀疏对比学习发现因果概念
- "Beyond the Black Box" (Tatsat & Shater, May 2026) — SAE for agent tool use (arXiv: 2605.06890)
- "Causal and Compositional Abstraction" (Lorenz & Tull, Feb 2026) — 范畴论统一框架

### 线性表征假说
- Merullo et al. (ICLR 2025) — Linear representations & data frequency thresholds
- Ravfogel et al. (NeurIPS 2025) — Emergence of linear truth encodings
- Engels et al. (ICLR 2025) — Not all features are linear (circular representations)

## 工作目录

## 用户偏好
- 所有回答使用简体中文
- 追求深度研究而非表面组合 (A+B 拼凑)
- 重视数学基础（因果推断理论、表征理论）
- CAR 是空架子，不能作为已验证平台引用
