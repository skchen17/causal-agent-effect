# Tool-Effect Binding 论文后续工作与投稿风险降低建议

- 日期：2026-08-05
- 目标会议：USENIX Security
- 依据：当前 USENIX 稿件、v17 context-repaired 正源、V0--V3 冻结协议与实现、T1/T3/O6/E2 草稿及现有实验报告
- 用途：确定理论、实验和论文叙事的后续执行顺序；不是新的实验结果报告

## 1. 总体判断

当前项目存在一个可以独立成立的研究核心：**授权安全不仅取决于 policy 和 monitor，还取决于 monitor 所观察的工具效果表示是否足以区分授权结果不同的执行。** 反事实执行的作用，是为表示不足构造可复核的碰撞见证，并在有限注册域内指导表示细化。

这个核心有理论价值，也能与现有的 complete mediation、least privilege、argument provenance 和 runtime guard 工作区分。但当前稿件不能仅依靠更换叙事达到 USENIX 投稿要求。以下问题必须通过代码或实验修复：

1. V1 当前内部调用 V3 字段级 comparator，不能作为真正的 whole-call 表示对照。
2. 严格归因 finalizer 尚未实现预注册的 H4 非拒绝驱动和 H5 跨 suite/strata 一致性。
3. 严格运行缺少 HTTP 400、context truncation 和 post-tool empty assistant 门禁。
4. v17 的 2,217 次执行中，259 次由 strict non-ALLOW 转为 effective ALLOW，不受当前 confinement 定理直接覆盖。
5. Prompt Sandwiching 在当前点估计上同时具有更低 ASR 和更高 benign/attack utility。
6. 当前论文 PDF 仍使用旧 E78 数字，T1/T3/O6/E2 尚未并入正文。

因此，后续原则应是：**先修正归因有效性和证据治理，再依据结果选择叙事；不能先选有利故事，再解释实验。**

## 2. 推荐的理论主线

### 2.1 核心对象：授权充分的效果表示

论文的核心不应写成“我们提出一个固定八/九字段 atom ontology”。更稳健的表达是：

> 对给定工具域和 admissible authorization-policy family，表示必须保留所有可能改变理想授权决策的效果差异。

atom 是实现这种表示的一个可分解载体，不是唯一真实表示。这样写有三个好处：

- 避免与 argument-level authorization/provenance 工作争夺“首次细粒度授权”；
- 允许不同工具和 policy family 使用不同字段；
- 与 authorization quotient、E2 policy-family sensitivity 和反事实碰撞直接一致。

### 2.2 理论链条应缩减为四步

1. **表示不足下界**：若两个授权结果不同的执行在 monitor view 中不可区分，则确定性 monitor 必然在其中至少一个实例上 unsafe allow 或 withholding。
2. **反事实见证**：执行干预产生 state/output/effect 不同且授权结果可分的调用对，从而证伪当前表示的充分性。
3. **有限域注册**：在有限候选域和 admissible strict refinement 条件下，表示分区单调细化并终止；collision-complete validation 只证明该有限域内充分。
4. **条件性 confinement**：在效果抽象 sound、authority bound 独立、complete mediation、check--use consistency 且 strict ALLOW 时，已提交效果包含于 authority bound。

### 2.3 必须收窄的理论表述

- 将“Counterfactual Registration Converges”改为“Finite-Domain Registered Refinement Is Monotone and Terminates under Admissible Strict Steps”。
- 不声称 atom 在逻辑上必要；T3 已说明 authorization-sufficient whole-call quotient 可以存在。
- 不把 counterfactual suite 的有限通过写成开放世界完备性。
- 不把 O6 写成 confinement 定理的扩展。O6 证明的是 override trail 的排除式审计、证据隔离和不扩充后续授权依据，不证明当前 override-released effect 已获得 affirmative authority membership。
- 把 policy family 明确放入定义。字段必要性是相对于 policy family 的，不是工具本体的绝对属性。

### 2.4 理论还需补的工作

| 优先级 | 工作 | 验收标准 | 降低的风险 |
|---|---|---|---|
| P0 | 统一 joint authorization sufficiency、quotient、atom refinement 的符号和定义 | 主文只保留一套定义；所有定理使用同一 domain/policy family | 自造概念、定义漂移 |
| P0 | 重写 T1 标题、前提和结论 | 明示有限域、admissible strict step、collision-complete suite | 过强收敛声明 |
| P0 | 分离 strict commit 与 override commit | 定理、系统图、结果表分别报告；不得用 effective ALLOW 代替 strict authorization | 理论实现不一致 |
| P1 | 给出 representation、authority、mediation 三类失败的正交反例 | 每个反例只违反一个前提 | 审稿人认为理论是常识重述 |
| P1 | 定义最小性采用“无充分 proper coarsening” | 避免用固定字段删除启发式代替最小性 | atom minimality 不严谨 |
| P2 | 将 T3 压缩为 novelty-boundary proposition | 说明本文不重新发明 least privilege/complete mediation | 与经典安全原则冲突 |

## 3. 实验建议

### 3.1 先修复 V0--V3 的归因有效性

当前 V0 可以作为 tool-identity baseline 保留。串行驱动在进入 V1 前应暂停，并完成以下处理：

#### V1 两种可接受方案

**方案 A：真正 whole-call representation。** 将 totalized call 序列化为一个不可分授权对象，只与预注册的 whole-call signatures/envelopes 比较；不调用 V3 per-field comparator，不生成字段级 repair。该方案最符合原协议，但需要明确 whole-call authority 如何注册。

**方案 B：保留代码并改名。** 将 V1 改为 `atom_decision_opaque_feedback`，明确它只消融解释/恢复粒度，不用于证明 whole-call representation 不足。另增真正 whole-call 条件后才能完成表示归因。

推荐方案 A。若实现时间不允许，使用方案 B，但论文必须放弃 V1/V3 的 representation-granularity 因果声明。

#### V2 的正确解释

V2 可以保留，但主张限定为：

> 在相同 V3-conditioned authority 和 comparator 下，比较所有 schema fields 与反事实筛选字段的增量效果。

它主要检验字段筛选是否降低 false denial/恢复成本，不是独立 schema-level 系统与 atom system 的全面比较。

### 3.2 在查看完整结果前补齐门禁

1. 实现 H4：报告 DENY、NEEDS_REPLAN、effective execution coverage、strict execution coverage；对成功阻断做“执行减少”与“已执行但攻击未达成”分解。
2. 实现 H5：按 banking/slack/travel/workspace 和冻结攻击 strata 输出方向与分母；按协议判定是否至少跨三个 suite、三个 strata。
3. 增加 HTTP 400、server log error、post-tool empty assistant、truncated conversation 检测。基础设施失败不得被记作安全成功。
4. 预注册对称 context repair：只修复枚举出的基础设施失败；四变体相同 case 使用相同窗口政策；保留原行和 overlay manifest。
5. 冻结并验证 runner、runtime patch、comparator、finalizer、statistics、AgentDojo scorer、环境锁文件和真实模型 SHA-256。

### 3.3 重新审计 v17/O6

merged 正源应统一为：

- ASR：11/629；benign utility：46/97；attack utility：272/629；
- effective decisions：ALLOW 2,217、DENY 83、NEEDS_REPLAN 407；
- strict authorization：1,958 true、749 false；
- 实际 strict-non-ALLOW override commits：259；diagnostic flag true：455；二者不得混用；
- 259 个实际 override 均有 structured checks，fallback 为 0，但必须由 merged artifact 正式重生成，不能继续引用旧 r1 override report。

结果表应将执行分为：strict ALLOW execution、override execution、blocked/no execution。主文只能对第一类引用 confinement 定理。

### 3.4 强基线的正确处置

Prompt Sandwiching 当前点估计优于本方法，不能通过更换表格口径回避。应执行同一 matched-key、同模型、同任务、同攻击的配对比较，并报告置信区间。

若配对结果仍显示 Sandwiching 占优：

- 明确承认本系统不是 benchmark Pareto frontier；
- 将其定位为 representation diagnosis 和 auditable mediation architecture；
- 增加机制性测试：同工具名、相似表面文本但 effect/resource/recipient/commit/provenance 变化的攻击对；
- 机制性数据集必须预注册并同时运行所有基线，不能只为本方法定制成功案例。

若方法只在机制性 stress 上有优势，应写成 complementary coverage，而不是普遍优越。

### 3.5 投稿前最小证据矩阵

| 论文主张 | 必须证据 | 当前状态 |
|---|---|---|
| 工具调用存在授权相关的复合效果 | 源码执行差分 + AgentDojo prevalence + 具体反例 | 基本具备 |
| 粗表示会合并授权不等价执行 | E47--E50、有限域 collision、ToolSandbox | 具备，但需统一口径 |
| 反事实注册能在有限域消除已发现碰撞 | refinement trajectory + held-out domain | 基本具备 |
| atom refinement 本身改善运行结果 | 语义有效的 V0/V1/V2/V3 配对归因 | 未完成，当前 V1 阻塞 |
| 改善不是拒绝一切造成 | H4 decomposition | 未实现 |
| 结果不是单攻击族偶然现象 | H5 suite/strata | 未实现 |
| 实际系统满足定理前提 | strict/override 分层、complete mediation、check--use audit | 部分满足 |
| 方法有可接受效用 | benign/attack utility、recovery、authority coverage | 当前偏弱 |
| 具有一定泛化性 | 第二模型或独立工具域 | 单模型，投稿风险高 |

## 4. 叙事选择

### 4.1 推荐主叙事：表示义务与可执行注册

这是最不依赖单个 benchmark 排名、也最符合当前证据的故事：

> Existing agent defenses decide whether to execute, but often assume that the monitored view preserves every authorization-relevant effect distinction. We identify this representation obligation, use counterfactual executions to falsify insufficient tool-effect contracts, and register a decomposable effect view for pre-commit mediation. The resulting guarantees are conditional on independently bounded authority and strict authorization; experiments characterize both the benefits and the remaining authority/recovery bottlenecks.

该叙事的贡献顺序应为：

1. 表示充分性问题与下界；
2. execution-grounded counterfactual registration；
3. 条件性 runtime mediation；
4. 正面结果和失败边界。

优势：即使 V0--V3 为混合或零结果，理论和 falsification methodology 仍可成立。风险：必须证明问题不只是人为构造，因此 AgentDojo prevalence、源码差分和 held-out domain 要留在主文。

### 4.2 条件叙事：counterfactually validated atoms 改善 mediation

只有在修正后的 V0--V3 同时满足以下条件时启用：

- V3 相对真正的 V1/V2 有显著安全收益；
- H2/H3 utility 非劣或损失可解释且较小；
- H4 证明收益不只是更低执行 coverage；
- H5 至少跨三个 suite 和三个 strata；
- context-integrity gates 全部通过。

这时可以把 atom-level mediation 写成主系统贡献，但仍不能声称 atom 是唯一充分表示或生产安全。

### 4.3 负结果叙事：表示并非全部，authority 是剩余瓶颈

若 V3 与 V2 相近或效用明显下降，改写为：

> Counterfactual validation can eliminate known representation collisions, but representation alone does not supply authority. In realistic trajectories, incomplete authority and resolver context dominate the residual tradeoff.

这种叙事不是失败包装，而是理论边界的实证验证。要成立，需要：

- 保留所有负结果；
- 用 E2、authority coverage、strict/override decomposition 定位瓶颈；
- 不把 v17 写成强防御系统；
- 将贡献定位为“何时 mediation 可行、何时表示不再是主瓶颈”。

它可能达到有价值的 measurement/theory paper，但系统论文的接受概率会低于正归因路径。

### 4.4 不推荐叙事

以下故事会增加投稿风险：

- “一种新的通用 agent guard，在 AgentDojo 上达到 SOTA”：当前强基线不支持。
- “atom 是安全工具调用的必要且唯一表示”：T3 和 authorization quotient 不支持。
- “反事实实验证明开放世界 contract 正确”：有限域验证不支持。
- “O6 将所有 override 纳入 confinement”：259 次 strict-non-ALLOW execution 不支持。
- “complete mediation/least privilege 是本文创新”：属于经典原则。

## 5. 论文结构建议

1. **Introduction**：用一个日历/邮件复合效果例子说明表示碰撞；第一页明确 representation obligation，不先介绍大量 O1--O6 术语。
2. **Related Work**：区分 causal attribution of tool motivation、argument provenance/authority、tool-effect learning 和本文的 committed-effect representation sufficiency。
3. **Problem and Model**：给直觉模型、policy-relative sufficiency、威胁模型和边界。
4. **Theory**：下界、quotient、counterfactual witness、有限 refinement、条件性 confinement；把长证明放附录。
5. **Design and Implementation**：注册阶段与 runtime 阶段严格分开；说明 LLM 只提出/规划，最终 strict authorization 是确定性的。
6. **Evaluation**：按 claim 组织，而不是按 E 编号组织：问题存在性、注册有效性、表示归因、系统结果、authority/override 分解、成本。
7. **Limitations**：集中披露 finite domain、single model、context repair、override theorem gap 和 authority interface，不在正文每段重复免责声明。

## 6. 投稿风险分类与处理方式

| 风险 | 能否靠叙事降低 | 正确处理 |
|---|---|---|
| 与 provenance/argument-level 工作重合 | 可以部分降低 | 聚焦 committed effects、执行差分和 representation sufficiency |
| 固定 atom ontology 显得人为 | 可以显著降低 | 改为 policy-relative sufficient representation，atom 只是载体 |
| Prompt Sandwiching 点估计占优 | 不能 | 配对重算、诚实降级、机制性补充实验 |
| V1 归因无效 | 不能 | 重构 V1 或改名并新增真正 whole-call 对照 |
| 收益可能来自拒绝更多 | 不能 | 实现 H4 |
| 单模型 | 不能完全 | 至少第二模型做关键 V3/control subset 或全量 |
| context repair 异构 | 可以部分降低 | 完整披露、对称规则、stability repeat |
| override 超出定理 | 可以部分降低 | 分层报告并缩小 theorem claim；不能称为已证明安全 |
| authority coverage 不足 | 不能仅靠写作 | E4/pilot、缺失上下文分解、接口 burden |
| 概念过多 | 可以 | 主文只保留 representation obligation、counterfactual contract、strict mediation 三个记忆点 |

## 7. 推荐执行顺序和停止条件

### P0：在 V1 开始前

1. 记录当前 V0 运行和全部源代码 hash，不读取 partial outcome 作决策。
2. 暂停串行驱动自动进入 V1。
3. 修正 V1 语义并更新协议版本；受影响条件重新 smoke。
4. 加入 context-integrity 检测和 repair protocol。
5. 实现 H4/H5 finalizer，补单元测试。

### P1：四变体完成后

1. fail-fast 完整性审计；任何 missing/error/truncated row 先处理，不能直接统计。
2. 按预注册规则生成 H1--H5 结论，不先挑有利 suite。
3. 重算 matched Prompt Sandwiching 比较。
4. 根据正/混合/负结果选择 4.2、4.1 或 4.3 叙事。

### P2：决定补实验

- 若 V3 有清晰归因收益：优先第二模型和 authority coverage，不再增加同构 synthetic stress。
- 若 V3≈V2：优先 authority/interface degradation，停止宣传 atom 优于 schema field。
- 若 V3 utility 明显更差：优先 recovery/authority coverage 根因实验；修复前不扩大系统主张。
- 若 V3 安全收益完全由低 coverage 产生：主系统叙事停止，转 measurement/theory 路径。

### 投稿最低门禁

满足以下条件后才进入最终写作冻结：

1. 所有正文数字映射到唯一通过 finalizer 的 artifact；
2. V1/V2/V3 语义和论文标签一致；
3. H1--H5 均有机器生成结论，即使结论为不通过；
4. context failure 为零或有预注册、对称、可审计 repair；
5. strict 与 override execution 分开，定理不覆盖后者；
6. 强基线比较按相同 key、模型、任务和 scorer；
7. Abstract、Introduction 和 Conclusion 不含生产安全、全局充分或 benchmark SOTA 过强声明；
8. 至少有一个独立域或第二模型证据，或在摘要中明确单模型边界。

## 8. 最终建议

推荐采用 **“表示义务与可执行反事实注册”** 作为稳定主线，而不是以 v17 防御性能作为主线。该故事与现有理论和问题证据最一致，也能在 V0--V3 出现混合或负结果时保持学术完整性。

但叙事调整只能解决定位、概念过强和与相关工作重合的问题。它不能代替真正的 whole-call 对照、H4/H5、context-integrity、强基线配对比较和 strict/override 边界。完成这些工作后，论文才具备从“有价值但证据未闭合的研究原型”转向“可由 USENIX 审稿人独立核验的条件性安全结果”的基础。
