# 项目演进史：从实验设计到 Path A 论文

> 日期：2026-05-22  
> 范围：2026-05-12 项目启动 — 2026-05-22 Path A 路线确认

---

## 总览

本项目从一个简单的线性可编码性扫描实验开始，在 10 天内经历了四个主要阶段：

| 阶段 | 时间 | 核心问题 | 关键转折 |
|------|------|----------|----------|
| Phase 1: 诊断发现 | 5/12–5/14 | 线性探针能否检测因果效果？ | 发现 surface-form fragmentation |
| Phase 2: 证据加固 | 5/14–5/15 | 碎片化是真实的还是 artifacts？ | 完成 lexical control + pIIA + mainconf v2 |
| Phase 3: Auth-SafeInv 补强 | 5/17–5/22 | 碎片化如何影响授权安全？ | T38-T73: 从诊断到框架，三个 gate failure |
| Phase 4: 路线收敛 | 5/22 | 当前证据能支撑什么类型的论文？ | Path A: evaluation/diagnostic paper |

---

## Phase 0: 项目奠基（5/12）

### 原始研究计划

项目以 **EXPERIMENT_PLAN.md** 为蓝本启动，最初的实验设计是：

> "在 agent 安全场景中，LLM 的内部表征是否以线性可编码的方式编码了工具调用的因果效果？"

这是一个相对简单的问题：训练线性探针 → 检测因果效果 → 报告 R²/F1/AUC。

**初始设定**：
- 11 个因果效果（command_executed, file_written, file_deleted, content_fetched, network_egress 等）
- 9 个工具（terminal, write_file, read_file, delete_file, send_message, web_fetch, web_search, delegate, memory）
- 3 种数据源：规则模板（N=1000）+ LLM 合成（N=500）+ 真实执行数据（N=待定）
- 3 种模型：MiniLM (384d), Qwen2.5-7B (3584d), Qwen3-8B (4096d)

### 初始基础设施建立

```
data/              → 场景数据集 (JSONL)
embeddings/        → LLM 嵌入 (npy + meta.json)
train_probes.py    → 线性+非线性探针
analysis/          → 实验结果
```

**第一天产出的文件**（文件时间戳追踪）：
- `generate_data.py` → 900 条规则模板数据
- `generate_counterfactual_data.py` → 284 条反事实 + LLM 合成数据
- `generate_targeted_data.py` → 175 条定向低频效果数据
- `merge_data.py` → 459 条合并主数据集
- `extract_embeddings.py` → MiniLM 嵌入
- `extract_embeddings_qwen.py` → Qwen2.5-7B 嵌入
- `train_probes.py` → 线性探针训练与 Δ 分析

**关键设计决策**：打破 tool→effect 的确定性映射。同一工具在不同上下文中产生不同效果，同一效果可以通过不同工具产生。这是后续发现 surface-form fragmentation 的必要前提。

---

## Phase 1: 诊断发现（5/12–5/14）

### 从"可编码性扫描"到"碎片化发现"

最初的实验按 EXPERIMENT_PLAN.md 执行：训练探针、报告 F1/AUC。但随着实验深入，发现了一个远超预期的问题。

**核心发现**：
- 线性探针在训练覆盖的工具上能很好检测效果
- 但在 leave-one-tool-out (LOTO) 测试中，同一效果的检测能力急剧下降
- 最高 held-out FNR 达到 **0.97**（file_written/write_file）

这个现象被命名为 **surface-form fragmentation**（表面形式碎片化）：LLM 表征中，同一因果效果的信息按工具表面形式碎片化编码，而不是按因果语义统一编码。

### 实验链建立

**Delta 分析**：非线性探针（MLP 64-128 hidden units）对比线性探针无系统改进（|Δ| ≤ 0.02 for 5/11 effects），满足 Sutter et al. 的线性约束。

**跨工具泛化**：LOTO FNR 是核心诊断指标。定义了 ToolProxyGap = [ΔFNR]₊（held-out FNR - within-form FNR 的非负 clamp）。

**pIIA**：probe-mediated interchange intervention，在 Qwen3-8B 的 L24/36 进行基于 hook 的激活干预。pIIA-Drop = pIIA_within − pIIA_cross。发现了从 tool_error（语义统一，pIIA-Drop=0.052）到 network_egress（表征碎片化，pIIA-Drop=0.366）的连续谱。

**Baseline 比较**：Pooled, Balanced, Tool-Conditioned, Group Reweight, Procrustes Alignment — 无方法消除 worst-form FNR。

**第一轮论文**：`paper/main.tex` 初稿完成，标题为 "Authorization-Conditioned Causal Task Consistency in LLM Tool Use"。

### 概念的逐步精确化

| 概念 | 定义 | 提出时间 |
|------|------|----------|
| MultiMech (D1) | P(E=1\|T) per tool，多工具可实现同一效果 | 5/12 |
| Frag (D2) | 同效果跨工具表征的分布距离 | 5/12 |
| SafeInv (D3-4) | 跨表面形式的 FNR bounded | 5/13 |
| ToolProxyGap (D5) | [ΔFNR]₊，跨工具检测退化 | 5/13 |
| pIIA (D6) | 激活级跨形式效果方向可迁移性 | 5/14 |
| Theorem 1 | [β−α]₊ 安全下界 | 5/14 |

---

## Phase 2: 证据加固（5/14–5/15）

### 为什么这一阶段是必要的

Phase 1 发现了 surface-form fragmentation，但有多个替代解释需要排除：
1. 碎片化是否是**词汇捷径**（探针依赖工具名/keyword）？
2. pIIA 是否只是 **probe calibration artifact**？
3. 关键 cells 的**样本量是否足够**？
4. 真实 agent 工具是否与合成工具有**语义对应**？
5. 严格 held-out 设置下的 **mitigation 是否有效**？

### 排除替代解释

**Lexical control**（T8/T10）：
- 将所有 tool names → [TOOL]，inline code → [CMD]，URLs → [URL]
- 重新提取 Qwen3-8B 嵌入，重跑 LOTO
- 结果：整体 FNR 仅从 0.378 → 0.382（Δ=+0.004）
- **结论**：碎片化不是简单的词汇表面特征

**pIIA controls**（T43/T48）：
- Random direction control
- Matched-norm control
- Same-effect wrong-form control
- Different-effect same-form negative control
- Layer sweep (L24/36)
- Token aggregation ablation
- Confirmatory scale-up: 864 raw hook rows, 6 effects
- **结论**：pIIA-Drop 与 max heldout FNR 的 Spearman = 0.53，不是纯 probe artifact

**Real-tool calibration**（T14）：
- 从 `real-agent-tools/` Hermes 工具注册中抽取 schema 和 effect semantics
- 构造 real_tool_scenarios_v2.jsonl (459 rows) 作为 proxy validation
- Schema/flow/semantic conflicts 均为 0
- **结论**：合成场景在 schema 层面与真实工具有效对应

### Mainconf v2: 数据规模扩充

**统计审计**（T27）暴露了关键问题：原始 459 数据中，44 个 positive effect-tool cells 中有 36 个 N+ < 30；LOTO 20 行中 15 行 N+ < 30。

**修复链**（T28/T29/T37）：
1. 选择 7 个 P0 key effect-tool cells 作为 target
2. 生成 408 条 incremental rows（含 tool_call 和 call_flow 字段）
3. 生成 65 条 static replay traces（含 schema/call-flow metadata）
4. 合并为 **932-row scenarios_mainconf_v2**
5. 7 个 P0 cells 全部达到 N+ ≥ 50

**Mainconf v2 实验结果**：
- LOTO max held-out FNR: 0.8036 (file_content_read/read_file)
- Strict LOPO: 68 tool-case evaluations, 33 improved, mean ΔFNR=0.1044
- Full-training multiseed: max mean post-FNR=0.034（observed-pair upper bound）

### Causal-chain diagnostic

**P2**（T22/T23）：测试因果链文本是否能改变表征组织。

- 构造 2290 个 chain-conditioned 样本（5 种条件：raw, tool-only, effect-chain, task-causal-chain, wrong-chain）
- Wrong-chain 分为 153 effect omissions, 152 effect flips, 153 authorization flips
- **结果**：部分效果（network_egress, tool_error）在 task-causal-chain 下改善，但 content_fetched/file_written 不改善，且 wrong-chain 可以误导
- **结论**：causal-chain conditioning 是机制诊断工具，不是可靠 mitigation

### 论文口径收敛

**P0**（T2/T3）：将论文从"多个指标 + 一个解法"重写为"causal task consistency 主线"。
- Deploy/LOTO/pIIA 三类量不再混用
- Contrastive theory 改为 conditional bounds
- pIIA 降级为 probe-mediated diagnostic

**P1**（T4/T8-T12）：数字可追溯。
- 新增 `generate_paper_table_audit.py`
- 修复 0.22 vs 0.25 口径不一致
- 修复 LOTO 定义从单源工具换到 all-but-heldout
- pIIA raw outcomes 全量落盘 + bootstrap CI

---

## Phase 3: Auth-SafeInv 理论补强（5/17–5/22）

### 为什么需要 Phase 3

Phase 2 加固了 surface-form fragmentation 的证据，但存在两个根本问题：
1. SafeInv (effect detection invariance) 与 authorization-conditioned safety 之间的概念鸿沟
2. Pure representation repair (contrastive projection) 在 strict held-out 条件下是否真的有效

**5/17 决策**：用户确认"按原来理论和论断进行补强"的路线。不是为了降级为 diagnostic paper，而是保留 causal task consistency 强主张，但引入：
- 授权条件形式化 (A(c), Ω(a,S), U(c,a,S))
- 执行级效果验证 (execution-level effect verifier)
- 严格泛化评估 (Auth-SafeInv 指标)

### T38-T45: 理论与数据基础

**T38**：Auth-SafeInv 形式化改造。
- 在 `formalization.md` 和 `paper/main.tex` 中统一 authorization-conditioned risk accounting
- 新增：Authorized Effect Envelope, Unauthorized Effect Set, Auth-SafeInv, AuthToolProxyGap
- 清理旧口径（Safety Theorems/E_critical/Theorem 1）

**T39**：Authorization counterfactual dataset v1。
- 1184 rows，含 task context, authorized effects, verified effects, unauthorized effects
- 四类 counterfactual：same task tool swap, same tool auth flip, same effect semantic reframing, same task effect substitution
- Qwen3-8B embeddings: 1184×4096

**T40/T49**：Execution traces。
- v1: 68 traces (56 sandbox_simulated + 12 static_replay)
- v2: 138 traces (70 controlled observed_execution + 56 sandbox + 12 static)
- 都是 controlled local sandbox，不是 deployed-agent traffic

**T41/T54**：Auth-SafeInv evaluation。
- Group-aware 5-seed random/LOTO/family-holdout
- CI 和 AuthToolProxyGap 指标

**T42**：Surface graph alignment。
- 分析 unauthorized effect graph 的连通性
- 解释为什么 two-form effects 在 strict LOPO 下不可识别

**T43/T48**：pIIA controls 补全。
- Hook-based matched-norm random intervention
- Wrong-form/wrong-effect controls
- Layer sweep + token aggregation ablation
- Confirmatory scale-up: 864 raw hook rows

**T44/T47**：Strong baselines。
- Split-matched pilot: 678 method rows across 10 baselines
- Confirmatory sweep: 504 fixed rows + 9408 threshold-curve rows
- Seeds 0/1/2, hidden dims 64/128
- 包含 domain-adversarial, supervised contrastive, IRM-linear, calibrated abstention, open-set, reweighting

### T51-T56: 三个 Gate Failure

这是 Phase 3 最关键的转折点。

**T51 (Gate 1)**：Contrastive projection vs baselines 集成比较。
- Observed-pair projection 是强 upper-bound repair（FPR≤0.1 时有效）
- 但 strict train-only projection 在 LOTO 仅覆盖 **4/14 cells**
- **Gate FAILED**：不能作为主方法

**T53/T54 (Gate 1 续)**：v2 surface-graph expansion + strict mitigation rerun。
- v2 将 strict train-only LOTO coverage 提升到 21/21 cells
- 但 FPR≤0.1 下 strict contrastive FNR=**0.2804**，弱于 best supervised_contrastive baseline 0.1835
- **Gate 仍 FAILED**：修复 coverage 后方法仍不足

**T55 (Gate 2)**：Pair-free effect-schema conditioned mitigation。
- 35136 schema-conditioned candidate-effect rows
- Qwen3-8B embeddings + monitor evaluation
- Best full-tool-chain LOTO FNR=**0.4516**，远弱于 T54 baseline 0.1835
- **Gate FAILED**：naive schema conditioning 不足

**T56 (Gate 3)**：Decomposed verifier mitigation。
- 将任务分解为 effect-present verifier + authorization monitor
- Pure frozen-embedding 版本：LOTO FNR=**0.3547**，仍弱于 baseline 0.1835
- **Gate FAILED**：纯表征分解不够
- **但** verifier-present upper-bound 很强：oracle present label → LOTO FNR=**0.0042**, family FNR=**0.0745** at FPR=0

**三个 gate failure 的战略意义**：
- 它们不是"null results"——每个方法做了一个不同的结构假设（transitive alignment, schema-visible effects, frozen-embedding separability），每个假设都被证伪
- 它们排除了"纯表征修复"作为当前解决方案的可能性
- Verifier-present upper-bound（T56）指出了唯一的正向出路：需要外部执行证据，不能只靠 LLM 表征

### T57-T65: Verifier-Assisted Framework

**T57**：从 oracle present label 到 deterministic static verifier。
- 用 trace-calibrated tool-call 规则替换 T56 oracle label
- Full-tool-chain LOTO FNR=**0.0262**/FPR=0.073
- 首次在同 cell 严格比较中超越 T54 strong baseline
- 但 verifier 仍是 deterministic static rules，不是 live execution logs

**T58**：Execution-level verifier hardening。
- 1104 trace candidate-effect rows（从 138 controlled traces 构造）
- Qwen3-8B trace embeddings
- Schema-trained authorization monitor + execution-trace present verification
- Schema-to-trace-all FNR=**0.0429**/FPR=0.0
- 但 traces 仍是 controlled observed/sandbox/static

**T59**：Real-agent-tools external-validity stress test。
- 静态审计 Hermes `real-agent-tools` 注册：74 个工具，58 个 external/API candidates
- Direct import 被缺 `agent`/`hermes_constants` 阻塞
- 只安全执行 read_file/write_file/terminal local adapters：48 traces, 384 candidate rows
- Schema-to-real-agent-local-trace FNR=**0.25**/FPR=0.0
- **关键负信号**：真实工具语义迁移仍有漏检，verifier-assisted success 不应被高估

**T60/T61**：DeepSeek provider API traces。
- T60: 8 traces pilot → T61: 120 traces expansion
- 960 candidate-effect rows, Qwen3-8B embeddings
- Execution verifier FNR=0/FPR=0, static verifiers FNR=**1.0**
- **关键证据**：static rules 对 provider/API effects 完全失效，execution evidence 不可或缺
- 但是单 provider surface

**T62**：Validation-selected threshold calibration。
- 在 validation trace groups 选阈值，held-out trace groups 测试
- T58 controlled: exec FNR/FPR=**0.0/0.0**
- T59 real-agent local: exec FNR/FPR=**0.1765/0.0**
- T61 provider API: exec FNR/FPR=**0.0/0.0**
- 修复了 ex-post-threshold 风险

**T63**：Broader web/search/browser/messaging local adapters。
- 300 traces, 2400 candidate-effect rows
- Validation-selected exec verifier test FNR=**0.0351**/FPR=0.0
- Static verifiers FNR=**0.614**/FPR=0.0132
- Controlled local adapters, 不是 live external services

**T64**：Key-free live/protocol external-validity traces。
- 150 条真实 outbound HTTPS + 150 条本地 webhook protocol
- 2400 candidate-effect rows
- Validation-selected exec verifier test FNR/FPR=**0.0/0.0** (N+=197, N-=1170)
- Static verifiers FNR/FPR=**0.6294/0.0462**
- 2026-05-22 补 full-precision Qwen3-8B rerun
- 强于 T63 local adapters，但不是 provider-backed search/SaaS messaging

**T65**：File-backed headless Chrome browser-runtime traces。
- 120 条真实 headless Chrome DOM/JS traces（file-backed pages）
- 960 candidate-effect rows
- Validation-selected exec verifier test FNR/FPR=**0.0/0.0** (N+=62, N-=411)
- Static verifier FNR/FPR=**1.0/0.0**
- 真实浏览器 runtime 证据，但不是 HTTP browser networking

### T66-T73: 论文方法与评估闭环

**外部审稿意见 v1**（5/21）触发了一系列补充实验和论文修改：

**T66**：Related Work difference matrix（AgentDojo, ToolEmu, AgentHarm, ASB, AttriGuard, CausalArmor, ClawGuard, ARGUS）。

**T67**：EffectVerif-AuthMonitor 方法接口定义（输入、trace schema、effect taxonomy、failure modes、伪代码）。

**T68**：Action-level Auth-SafeInv metrics。
- 按 trace/action 聚合 T62 candidate-effect predictions
- 执行 verifier unauthorized-action allow / authorized-action false-denial:
  - T58: **0.0/0.1591**, T59: **0.2/0.3571**, T61: **0.0/1.0**, T63: **0.05/0.21**, T65: **0.0/1.0**, T64: **0.0/0.0**
- **关键发现**：row-level 0/0 FNR/FPR 可以与 action-level FDeny=1.0 共存

**T69**：Trace-view verifier independence ablation。
- Full-label → label-hidden raw → minimal-evidence
- FNR: **0.0353 → 0.1162 → 0.1465**（3.3×–4.2× 退化）
- 最大退化在 browser-runtime traces

**T70**：Existing-defense proxy comparison。
- Pre-action rule-only: FNR=**0.5700**
- Provenance-only: FNR=**0.2873**
- EffectVerif label-hidden: FNR=**0.1162**
- Raw-status boundary: FNR=**0.1113**, FDeny=**0.0265**
- **关键发现**：raw-status boundary 是 competitive baseline

**T73**：Action-level threshold calibration negative diagnostic。
- Validation false-denial ≤ 0.10 约束下
- T59/T61/T63/T65 多数选择 all-allow threshold
- Held-out unauthorized-action allow=**1.0**
- **结论**：简单阈值校准不能作为部署策略

### Phase 3 论文修改

**T45**：论文两轮重写（5/21）。
- 第一轮：切换为 verifier-assisted controlled-study 主线
- 第二轮：重排实验叙事权重，contrastive 从 Solution 降为 observed-pair upper-bound

**T71**：第三轮重写（5/21-5/22）。
- 整合 T64/T65/T66-T70/T73 入主文
- Auth-SafeInv/verifier-assisted monitoring 提前为主实验小节
- Pure representation mitigation 写为 gate failed

**T50**：Reproducibility。
- `reproduce_auth_safeinv.sh` (53 步)
- `analysis/auth_result_source_appendix.{json,md}`
- all_outputs_present=True

---

## Phase 4: 路线收敛（5/22）

### 新一轮评审与 Path A 决策

**5/22**：用户收到新一轮总体评审结论（Weak Reject / Borderline Reject）。项目到了决定性分叉点。

**外部文献搜索**：发现 2026 年 4-5 月 provenance/effect-trace monitoring 方向密集出现：
- PACT (2605.11039)：argument-level provenance + capability contracts
- Alignment Contracts (2605.00081)：formal effect-trace semantics + Lean 4 proofs
- ARM (2604.04035)：causality laundering detection
- AgentTrust (2605.04785)：runtime interception 95-96.7% accuracy
- Parallax (2604.12986)：cognitive-executive separation, 98.9% attack block
- ECA (2605.19192)：evidence-carrying certificates

**核心判断**：继续作为 verifier-assisted method paper 投稿，novelty 会被这些工作严重稀释。

**Path A 决策**（用户确认）：
- 走 evaluation/diagnostic paper 路线
- 不引入新方法（CEG-Auth 保留为 future work）
- 论文定位：**Auth-SafeInv evaluation target + three-layer over-optimism diagnosis + constructive framework with honest limits**

### Path A 论文重构

**v1**（5/22 下午）：
- 标题改为 "How Safe Are Agent Safety Monitors?"
- 四贡献结构：eval target + fragmentation diagnosis + three-layer evidence + constructive framework
- Experiments 按三层结构重组
- Contrastive/causal-chain 移到 appendix
- 18 页主文 + 5 页附录，编译通过

**外部审稿意见分析**（5/22）：
- 14 条批评逐条分析
- 确认 #3 (Auth-SafeInv vs SafeInv 混淆), #9 (verifier-generator 同源), #14 (贡献边界摇摆) 为致命问题

**v2**（5/22 晚）：
- 四贡献 → 两贡献结构（更紧密的因果链）
- Layer 1 明确标注为 SafeInv failure，Layer 2-3 为 Auth-SafeInv
- 新增两阶段 sandbox 执行模型声明
- 诚实承认 verifier-generator 同源问题
- 补充 row-action aggregation pipeline 解释
- 主表加 CI 标注
- 标题改为 "Auth-SafeInv: An Evaluation Target for Authorization-Conditioned Effect Monitoring with Three-Layer Over-Optimism Diagnosis"
- 编译通过，零 undefined reference

### 项目整理

**5/22 最后阶段**：
- analysis/ 226 个文件重组为 8 个子目录
- src/ 47 个脚本按功能重组为 8 个子目录
- 所有 shell entry scripts 更新为新路径
- 66 处 Path(__file__) 引用修复
- PROJECT_SUMMARY.md 写入完整项目综述

---

## 项目关键数字演进

| 指标 | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|------|---------|---------|---------|---------|
| 数据集规模 | 459 scenarios | 932 scenarios (mainconf v2) | +1464 auth counterfactuals, +35,136 schema rows, +8,988 trace rows | 不变 |
| 探针模型 | MiniLM, Qwen2.5 | +Qwen3-8B (primary) | 不变 | 不变 |
| 最大 LOTO FNR | 0.97 | 0.80 (mainconf v2) | 不变 | 不变 |
| Gate failures | — | — | 3 (T54/T55/T56) | 不变 |
| Trace families | 0 | 65 static replay | +6 families (controlled, local, API, broader, live, browser) | 不变 |
| 执行 verifier test FNR/FPR | — | — | 0.0/0.0 on best cases (T64/T65) | 不变 |
| Action FDeny | — | — | 1.0 on worst cases (T61/T65) | 不变 |
| 论文页数 | ~15 | ~15 | ~15 | 18+5 |
| 论文贡献数 | 4 (混排) | 4 | 4 | 2 (紧耦合) |
| 论文定位 | diagnostic study | diagnostic study | verifier-assisted method | evaluation/diagnostic paper |
| 审稿判断 | — | Weak Reject | Borderline Reject | (待投稿) |

---

## 关键经验教训

1. **从简单问题出发可以发现深层问题**：最初的"线性可编码性扫描"意外揭示了 surface-form fragmentation，这不是计划内的发现，而是实验设计（打破 tool→effect 映射）自然暴露的。

2. **严格的 held-out 评估是方法试金石**：三个 gate failure (T54/T55/T56) 在 full-training 或 pooled evaluation 下可能被掩盖。只有 strict held-out protocol 才能区分"observed-pair repair"和"real generalization"。

3. **外部文献格局决定论文定位**：如果 2026 年 4-5 月没有密集出现 provenance/effect-trace monitoring 工作，verifier-assisted method paper 可能是可行路线。但面对 PACT/Alignment Contracts/ARM/AgentTrust/Parallax/ECA 的同时出现，evaluation/diagnostic paper 是唯一有足够 novelty 边界的选择。

4. **负结果是强贡献**：三个 gate failure 不是"失败"——它们排除了简单的解决方案路径，为后续研究指明了真实的难度水平。审稿人会重视这种诚实。

5. **指标的结构性脱节需要明确定义**：row-level 0/0 FNR/FPR 与 action-level FDeny=1.0 的"矛盾"不是 bug——它是 candidate-effect aggregation rule 的结构性结果。但这需要（a）明确的 aggregation pipeline 解释和（b）具体的反例才能让审稿人接受。
