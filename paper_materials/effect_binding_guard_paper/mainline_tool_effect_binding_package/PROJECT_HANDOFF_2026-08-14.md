# Tool-Effect Binding 项目交接文档

更新时间：2026-08-14（Asia/Shanghai）

工作区根目录：

<code>/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package</code>

本文档是给后续研究者或 AI 的首要入口。它描述当前论文主张、证据、运行队列、文件结构和接手顺序。逐文件可检索清单见根目录的 <code>PROJECT_FILE_CONTENT_MAP.csv</code>。该 CSV 覆盖物理工作区中的全部文件和顶层兼容符号链接，并给出所属实验、文件类型、用途、相关性、大小和更新时间。

## 1. 一页状态

| 项目 | 当前状态 |
|---|---|
| 投稿目标 | USENIX Security 2027 Cycle 2 |
| 活动论文 | <code>paper/current-usenix/main.tex</code> |
| 最新 PDF | <code>paper/current-usenix/main.pdf</code> |
| 论文标题 | *Binding Agent Tool Calls to Effects: Counterfactually Validated Atoms for Pre-Commit Mediation* |
| 投稿判断 | **Conditional no-go**：等待五方法 Qwen3-32B 同协议结果及最终再生成 |
| 当前篇幅 | 总 PDF 15 页；技术正文 11/13 页 |
| 构建状态 | 通过；无 undefined citation/reference、fatal error 或 overfull box |
| 引用状态 | 当前 PDF 使用 35 个 citation keys；引用审计通过 |
| 主复现状态 | <code>pending_required_artifacts</code>；固定证据 232 行已核对，缺五方法最终 JSON |
| 正在运行 | Qwen3-32B 五方法 AgentDojo 同协议比较 |
| 排队任务 | 强基线完成后运行论文 finalizer；finalizer 完成后运行 atom-vs-field semantic attribution |
| 必须人工完成 | 最终作者核对、作者/ORCID/COI 元数据、匿名 artifact URL、最终匿名性检查 |

注意：<code>paper/current-usenix/submission_readiness_report.md</code> 中“技术正文第 9 页结束”是较早快照。当前可信值来自 <code>paper/current-usenix/reproduction/check_page_budget.py</code> 和 <code>page_budget_report.json</code>：**11/13 页**。

## 2. 项目目标

项目研究的问题是：一次 agent 工具调用可能提交多个彼此独立授权的效果，但工具名、整次调用、通用参数元组或表面文本可能把授权不等价的效果合并到同一个监控视图中。此时任何只看该粗粒度视图的确定性 monitor 都必须在 unsafe allow 与 withheld authorized work 之间出错。

目标系统分为两个阶段：

1. **离线注册。** 开发者或 LLM 提出候选 tool descriptor。系统在复制的 sandbox 中执行基础调用和字段干预，比较实际提交的状态变化，并用冻结的授权策略族寻找 policy-separating counterexample。反例用于细化 descriptor；通过有限门禁后才冻结。
2. **在线中介。** 不可信 agent 只提出精确工具调用。确定性 pre-commit monitor 使用冻结 descriptor 实例化 effects/atoms，把它们与独立提供的 authority 比较，再决定 ALLOW、DENY 或 ABSTAIN。运行时不调用 descriptor proposer，也不允许 planner 自行扩大 authority。

当前 AgentDojo 实现是一个受限的 **provenance-origin monitor**，不是完整 ACL、delegation、quota 或通用权限系统。

## 3. 核心贡献与严格边界

### 3.1 当前支持的贡献

1. **表示碰撞下界。** 若 monitor view 合并授权不等价的已提交效果，则它不可能同时保持 soundness 和 permissiveness。
2. **反事实注册。** 源码执行的 counterfactual intervention 可发现并逐步消除冻结有限域中的授权分离碰撞；无效或未决干预不会被当作字段无关证据。
3. **有限域 concrete-atom realization。** 在冻结 ToolSandbox 域和授权关系上，typed concrete atoms 能实现目标决策关系。
4. **受限运行时实例。** 冻结 descriptor 可以驱动可审计的 pre-commit provenance-origin mediation，且执行调用与 allow record 可对账。

### 3.2 不得写入论文的强声明

- 不得声称全局唯一或开放域最小 atom schema。
- 不得声称完整授权系统、production safety 或 deployed-system guarantee。
- 不得把 saved replay 写成真实部署轨迹。
- 不得把 adapted baseline 写成外部论文原协议复现。
- 不得把 planner 或 LLM 输出当作 authority 来源。
- 不得把 67/67 字段保留解释为自动发现了稀疏最小字段集。
- 不得把运行时 ASR 下降单独解释为 atom 优于 generic field taint；必须结合 source-oracle collision 与 raw-field control。

## 4. 理论主线

理论位于 <code>paper/current-usenix/sections/security_analysis.tex</code>，完整证明位于 <code>paper/current-usenix/appendix/formal_proofs.tex</code>。

| 理论对象 | 内容 | 证据边界 |
|---|---|---|
| Authorization sufficiency | 表示必须区分策略会作出不同授权决定的 executions | 相对于给定 effect domain 与 policy family |
| Representation collision theorem | 粗视图合并授权不等价效果时，monitor 必须产生 unsafe allow 或 false deny | 一般离散决策结论 |
| Counterfactual witness proposition | 一个 policy-separating intervention 可证伪当前表示充分性 | 反例只证明不足，不证明完整性 |
| Finite refinement theorem | 每个有效反例细化有限分区，因此在有限 intervention domain 上终止 | 不外推到开放工具域 |
| Conditional atom-level mediation | descriptor soundness、独立 authority、complete mediation 和 check-use consistency 成立时，每个 committed effect 满足策略 | 条件性结论 |
| Provenance-origin confinement instance | 当前 C1f 在可信 provenance 和冻结 registry 下实现有限来源约束 | 不是通用 ACL/delegation |

## 5. 当前主要证据

以下数字已经进入当前 PDF 或 claim ledger。引用时必须保留右侧边界。

| 证据 | 当前结果 | 可支持的结论 |
|---|---|---|
| AgentDojo effect prevalence | 97 个良性 reference trajectories 中 339 个调用；100 个具有归一化状态/外部交互效果，17 个为 compound，13 个为 heterogeneous/cross-subsystem | benchmark 中确实存在复合效果；不是整个 agent 生态的 prevalence |
| 56-call source finite domain | tool-name/effect-only 视图分别产生 564/548 个 authorization-separating pairs；reviewed typed effects 为 0 | 粗表示在冻结域中发生碰撞 |
| ToolSandbox held-out | 32 个 contexts；common fields 有 41 个 separating pairs，typed effects 为 0；8 个 invalid contexts 保留 | 外部来源有限域迁移，不是开放域完备性 |
| Concrete atom authorizer | 32 contexts、232 ordered queries；typed atoms 为 0/150 unsafe pre-allows 和 0/82 false denials | 在冻结策略关系上的 concrete realization |
| AgentDojo registration audit | 25 tools、67/67 unique fields retained；66/75 suite-field instances 有 committed-effect witness；38/75 有至少 5 类有效干预 | conservative coverage 与部分 necessity evidence；不是 sparse discovery |
| DeepSeek official AgentDojo | no guard 6/629 attack successes，C1f 0/629；Spotlighting 也为 0/629 | 受限 runtime case study；不能证明 atom-specific dominance |
| DeepSeek repeated benign | no guard 301/388，Spotlighting 305/388，C1f 297/388；C1f 均值差 -1.0 pp，但单侧 95% 下界 -5.4 pp，未通过 -5 pp 非劣效门禁 | 保留负面边界：未证明 benign non-inferiority |
| Frozen held-out 320 | no guard 4/320，Spotlighting/C1f 均 0/320；utility 分别 250/320、238/320、235/320 | 冻结公开攻击族上的安全改善伴随 utility 下降 |
| AgentLAB saved transfer | no guard 95/303 attack successes、185/303 utility；C1f 1/303、132/303；1,334 guarded calls 完整对账 | 跨环境 saved replay 有安全收益和显著效用代价 |
| Raw-field attribution | 同一 321-case subset 上 raw-field 为 10/273、C1f 为 7/273 attack successes；raw-field utility 更高 | effect semantics 改变决策并略严，但未证明 selectivity 优势 |
| Bounded 40-key diagnostic | no guard 4/40，C1f 2/40 | 有界公开生成器诊断，不是 unrestricted adaptation |

机器可审计的主张映射：<code>paper/current-usenix/claim_to_source.md</code>。  
行级账本：<code>paper/current-usenix/reproduction/main_claims.{json,csv,md}</code>。

## 6. 正在运行与排队任务

### 6.1 当前五方法强基线

入口：<code>shared/compatibility/scripts/run_current_c1f_qwen32_strong_baseline_rerun.py</code>

冻结协议：<code>experiments/unified-agent-security-baselines/results/current-c1f-strong-baseline-rerun/protocol.json</code>

状态：<code>experiments/unified-agent-security-baselines/results/current-c1f-strong-baseline-rerun/run-status.json</code>

最终结果应生成：<code>experiments/unified-agent-security-baselines/results/current-c1f-strong-baseline-rerun/results.json</code>

协议为同一个 Qwen3-32B checkpoint、65,536 context、AgentDojo v1.1.2、97 个良性 keys 和 629 个攻击 keys。方法顺序固定为：

1. no guard；
2. Spotlighting；
3. Prompt Sandwiching；
4. PromptArmor-style local adapter；
5. current C1f。

截至本文档生成快照：

- no guard：良性与攻击全部完成；
- Spotlighting：良性与攻击全部完成；
- Prompt Sandwiching：97 个良性完成，629 个攻击正在运行；
- PromptArmor-style：尚未开始；
- C1f：尚未开始。

任何中间行都不得写入论文。只有 <code>results.json.status == "passed"</code>、每方法正好 726 个 keys、无 error/incomplete 且 C1f audit gates 通过后，才能引用。

### 6.2 自动 finalizer

入口：<code>paper/current-usenix/reproduction/finalize_after_frozen_runs.py</code>

它等待强基线进程结束，然后依次：

1. 重跑有限 concrete-atom authorizer；
2. 生成 path-free fixed support；
3. 导出最终 case outcomes；
4. 生成最终结果段；
5. 重建主 claim ledger；
6. 生成 readiness 与模拟审稿；
7. 编译 PDF；
8. 检查页限、引用、匿名化、PaperSpine 与测试；
9. 重建匿名 artifact。

<code>paper/current-usenix/reproduction/finalization_report.json</code> 当前显示的是一次较早失败记录，不能解释为本次等待队列已经失败。旧失败所缺的 raw-field artifact 目前已存在；本次 finalizer 尚未真正开始，结束后会覆盖该文件。

### 6.3 Atom-vs-field semantic attribution

排队入口：<code>shared/compatibility/scripts/queue_atom_vs_field_semantic_attribution.py</code>

状态：<code>experiments/security-analysis-ablation-and-overhead/results/atom-vs-field-semantic-attribution/queue-status.json</code>

该任务等待 finalizer 完成，再运行测试与完整 attribution。它用于进一步判断 observed runtime difference 来自 effect semantics 还是 generic structured-field provenance。结果无论正负都必须保留。

## 7. 活动论文结构与逐文件映射

### 7.1 构建入口

| 文件 | 内容与用途 | 当前状态 |
|---|---|---|
| <code>paper/current-usenix/main.tex</code> | 唯一活动论文入口；定义标题、宏、include graph 与附录顺序 | 活动 |
| <code>paper/current-usenix/usenix.sty</code> | 当前 USENIX 双栏样式 | 活动 |
| <code>paper/current-usenix/references.bib</code> | 当前 35 个引用 keys 的 BibTeX 数据 | 活动、审计通过 |
| <code>paper/current-usenix/main.pdf</code> | 最新编译稿 | 15 页总长，技术正文 11 页 |
| <code>paper/current-usenix/main.*</code> 中除 tex/pdf 外文件 | LaTeX 生成文件 | 生成物，不作为证据源 |

### 7.2 正文章节

| 文件 | 论文功能 |
|---|---|
| <code>sections/abstract.tex</code> | 问题、方法、三个 headline evidence 与安全/效用边界 |
| <code>sections/introduction.tex</code> | 日历复合效果案例、表示碰撞动机、反事实注册、贡献与证据链 |
| <code>sections/related_work.tex</code> | 按 intervention location、authorization view、effect specification、representation validation 比较相关工作 |
| <code>sections/threat_model.tex</code> | 系统边界、攻击者、目标、trusted inputs 与 scope |
| <code>sections/method.tex</code> | effect atom、policy view、离线反事实注册、运行时接口、provenance-origin monitor |
| <code>sections/security_analysis.tex</code> | collision、counterfactual witness、finite refinement 和 conditional mediation 的正文陈述与 proof sketches |
| <code>sections/evaluation.tex</code> | RQ1-RQ4、数据集、oracle 区分、指标和完整性门禁 |
| <code>sections/results.tex</code> | prevalence、representation/registration、finite authorizer、runtime mediation 结果 |
| <code>sections/generated_final_validation_results.tex</code> | 自动生成的重复效用与 held-out 结果段；finalizer 会覆盖 |
| <code>sections/limitations.tex</code> | 注册覆盖、可信接口、安全-效用边界 |
| <code>sections/conclusion.tex</code> | 有限主张总结 |
| <code>sections/experimental_setup.tex</code> | 较早的独立 Experimental Setup 草稿；未被 main.tex 包含 |

### 7.3 附录

| 文件 | 内容 |
|---|---|
| <code>appendix/ethics.tex</code> | sandbox、无真实外部副作用、伦理边界 |
| <code>appendix/open_science.tex</code> | artifact、manifest、hash 与复现说明 |
| <code>appendix/additional_results.tex</code> | exact representation、DeepSeek、旧 controlled stress、注册失败和开销 |
| <code>appendix/formal_proofs.tex</code> | 三项核心理论的完整定义、证明和边界 |

### 7.4 图

| 文件 | 图号与内容 |
|---|---|
| <code>figures/tikz_style.tex</code> | 全部原创 TikZ 图标和灰度可辨配色 |
| <code>figures/representation_collision.tex</code> | Figure 1：calendar compound effect、coarse view collision 与 atom separation |
| <code>figures/system_overview.tex</code> | Figure 2：message-oriented 离线 registry 与在线 pre-commit mediation |
| <code>figures/representation_results.tex</code> | Figure 3：AgentDojo/ToolSandbox separating-pair 水平柱状图 |
| <code>figures/security_utility_tradeoff.tex</code> | Figure 4：DeepSeek official/held-out 安全-效用散点图 |
| <code>figures/handdrawn/*</code> | 早期手绘 PNG/SVG 备选；未进入当前 PDF |

### 7.5 表

| 文件 | 内容 | 当前 PDF |
|---|---|---|
| <code>tables/table_agentdojo_effect_prevalence.tex</code> | AgentDojo effect prevalence | 主文 |
| <code>tables/table_registration_sufficiency.tex</code> | 67-field conservative registration audit | 主文 |
| <code>tables/table_concrete_atom_authorizer.tex</code> | 232-query finite authorizer | 主文 |
| <code>tables/table_granularity_and_transfer.tex</code> | granularity attribution 与 AgentLAB transfer | 主文 |
| <code>tables/table_representation_collisions.tex</code> | 56-call exact collisions | 附录 |
| <code>tables/table_toolsandbox_heldout.tex</code> | 32-context exact held-out collisions | 附录 |
| <code>tables/table_deepseek_runtime.tex</code> | DeepSeek exact runtime counts | 附录 |
| <code>tables/table_binding_problem_characterization.tex</code> | 旧 E47/E50 controlled stress | 附录 |
| <code>tables/table_e78_qwen32_baselines.tex</code> | 较早 Qwen baseline 表 | 未包含，不能替代当前 fresh run |
| <code>tables/table_e80_obligations.tex</code> | obligations 表草稿 | 未包含 |
| <code>tables/table_e81_runtime_ablation.tex</code> | runtime ablation 表草稿 | 未包含 |
| <code>tables/table_e83_kernel_overhead.tex</code> | overhead 表草稿 | 未包含 |
| <code>tables/table_e84_authority_burden.tex</code> | authority burden 表草稿 | 未包含 |
| <code>tables/table_e84_reviewed_authority.tex</code> | reviewed authority 表草稿 | 未包含 |

### 7.6 复现与审计

| 文件 | 用途 |
|---|---|
| <code>reproduction/reproduce_main_claims.py</code> | 当前主张 fail-fast 复现入口 |
| <code>reproduction/build_current_evidence.py</code> | 构建当前 evidence bank |
| <code>reproduction/extract_sanitized_fixed_support.py</code> | 从含机器路径的旧报告提取匿名固定数字 |
| <code>reproduction/export_final_case_outcomes.py</code> | 导出最终逐 case 结果 |
| <code>reproduction/generate_final_result_section.py</code> | 将通过门禁的最终结果写入生成章节 |
| <code>reproduction/render_final_tables.py</code> | 生成最终表格 |
| <code>reproduction/generate_final_readiness_and_review.py</code> | 更新 readiness 与模拟审稿 |
| <code>reproduction/check_page_budget.py</code> | 测量技术正文页数 |
| <code>reproduction/audit_references.py</code> | 核对 BibTeX 和引用 |
| <code>reproduction/audit_submission_sources.py</code> | 检查 include graph、引用、匿名化和 PDF 文本 |
| <code>reproduction/finalize_after_frozen_runs.py</code> | 强基线完成后的统一 finalizer |
| <code>reproduction/main_claims.{json,csv,md}</code> | 当前 232 行 claim ledger |
| <code>reproduction/reproduction_status.json</code> | 当前 pending_required_artifacts 状态 |
| <code>reproduction/sanitized_fixed_support.json</code> | 绑定旧 raw reports 的路径无关数字与 hash |
| <code>reproduction/finalization_report.json</code> | finalizer 最近一次执行报告；当前为旧失败快照 |

### 7.7 当前状态文档的可信顺序

| 优先级 | 文件 | 使用方式 |
|---:|---|---|
| 1 | <code>PROJECT_HANDOFF_2026-08-14.md</code> | 当前整体交接入口 |
| 2 | <code>paper/current-usenix/remaining_issues_to_fix.md</code> | 当前唯一问题总表 |
| 3 | <code>paper/current-usenix/writing_report.md</code> | 当前论文、证据与图表状态 |
| 4 | <code>paper/current-usenix/claim_to_source.md</code> | 主张到结果/代码映射 |
| 5 | <code>paper/current-usenix/reproduction/reproduction_status.json</code> | 机器门禁状态 |
| 6 | <code>paper/current-usenix/submission_readiness_report.md</code> | 总体判断可用，但页数行部分过时 |
| 历史 | 其他带日期 handoff/review/plan 文档 | 仅用于理解决策演化，不覆盖当前文件 |

## 8. 实验族映射

实验目录按研究问题命名。历史 E 编号只存在于 artifact 内容和兼容代码中。

| 实验族 | 研究作用 | 关键文件/结果 | 当前论文角色 |
|---|---|---|---|
| <code>experiments/binding-failure-and-granularity/</code> | 证明 joint-binding failure 与资源/授权瓶颈 | <code>results/authorization-separating-collision-audit/</code>、<code>results/cross-method-binding-stress/</code> | 问题证据；旧 controlled stress 已移附录 |
| <code>experiments/precommit-authorization-and-audit/</code> | E55-v2 strict local authorization 与 E56/E57 审计 | 该族 <code>results/</code> | 历史 feasibility/audit，非当前 headline |
| <code>experiments/independent-contracts-and-realistic-traces/</code> | independent specified contract、realistic replay、decomposition、burden | <code>evaluation/</code>、<code>reports/</code>、<code>paper-tables/</code> | 补充材料；不得写 independently authored，除非真实人审通过 |
| <code>experiments/counterfactual-descriptor-onboarding/</code> | LLM/规则 descriptor proposal、反事实反馈与注册原型 | <code>source/</code>、<code>results/</code> | 机制探索；当前论文不声称 automatic synthesis |
| <code>experiments/real-model-and-checkpoint-evidence/</code> | real LLM judge/extractor 与 released checkpoint adapter | <code>evaluation/</code>、<code>baselines/</code>、<code>reports/</code> | 附加证据；adapted comparison，不是原协议复现 |
| <code>experiments/intent-bound-runtime-guard/</code> | task envelope、replanning、effect-diff runtime、C1f registry | <code>evaluation/counterfactual-atom-envelope-guard/</code>、<code>results/counterfactual-atom-envelope-guard/</code>、<code>results/effect-difference-runtime-guard/</code> | 当前 C1f 主要实现与结果来源 |
| <code>experiments/unified-agent-security-baselines/</code> | AgentDojo no-guard 与统一强基线 | <code>results/current-c1f-strong-baseline-rerun/</code>、<code>runs/current-c1f-strong-baseline-rerun/</code> | 当前唯一 P0 实验 |
| <code>experiments/long-horizon-transfer/</code> | AgentLAB/ToolSandbox-style saved transfer | <code>results/long-horizon-cross-environment-transfer/</code> 与兼容结果 | 迁移 case study，utility cost 必须保留 |
| <code>experiments/security-analysis-ablation-and-overhead/</code> | 理论义务、消融、attribution、自适应攻击、开销 | <code>results/refinement-monotonicity-check/</code>、<code>results/c1f-raw-field-attribution/</code>、<code>results/runtime-policy-view-ablation/</code>、<code>results/runtime-overhead-measurement/</code> | 理论和机制归因核心支持 |
| <code>experiments/human-authority-and-causal-validation/</code> | source-executed effect validation、ToolSandbox、authority review | <code>results/finite-domain-effect-binding-validation/</code>、<code>results/heldout-toolsandbox-effect-binding-validation/</code>、<code>results/concrete-atom-authorizer-mechanism/</code> | 当前 atom 表示价值的最强证据 |
| <code>experiments/adaptive-injection-benchmark/</code> | held-out/public-family 与 bounded attack generation | <code>evaluation/usenix-heldout-public-families/</code>、<code>results/usenix-heldout-public-families/</code>、<code>results/bounded-public-family-search-current-c1f/</code> | 冻结 held-out 与 bounded diagnostic |

每个实验族中的目录含义固定：

| 子目录 | 含义 |
|---|---|
| <code>source/</code> | 实验实现 |
| <code>scripts/</code> | 运行、汇总和审计入口 |
| <code>tests/</code> | 单元/集成测试 |
| <code>evaluation/</code> | 冻结输入、manifest、review packet、schema 和 preregistration |
| <code>results/</code> | JSON/JSONL/CSV 结果及 Markdown 报告 |
| <code>reports/</code> | 跨 artifact 的人工可读总结 |
| <code>paper-tables/</code> | 实验生成的候选 LaTeX 表 |
| <code>runs/</code> | 原始逐 case logs、cache、第三方环境和中间输出；不应直接作为 headline evidence |

## 9. 其他顶层目录与兼容路径

| 路径 | 内容 |
|---|---|
| <code>paper/</code> | 当前稿、历史稿、PaperSpine 工作区和论文材料 |
| <code>experiments/</code> | 11 个按研究问题组织的物理实验族 |
| <code>shared/compatibility/</code> | 旧根目录的物理目标，仍被部分 active runners 使用；迁移完成前不可删除 |
| <code>shared/workspace-management/</code> | 工作区迁移、匿名打包和文件映射工具 |
| <code>analysis</code>、<code>code</code>、<code>scripts</code>、<code>results</code>、<code>runs</code>、<code>tests</code> 等顶层路径 | 指向 <code>shared/compatibility/*</code> 的符号链接，用于保持历史 imports/artifact paths |
| <code>.agents/</code>、<code>.codex/</code>、<code>.qoder/</code> | AI 工具配置；不是论文证据 |
| cache 目录 | 可重建，不作为证据 |
| <code>v*_watch*.log/.sh</code> | 历史后台 watcher；当前队列以实际进程和 status JSON 为准 |

不要在活跃强基线运行期间移动 <code>runs/</code>、<code>code/</code>、<code>scripts/</code> 或其 symlink targets。

## 10. 完整逐文件映射

<code>PROJECT_FILE_CONTENT_MAP.csv</code> 是完整索引，列定义如下：

| 列 | 含义 |
|---|---|
| <code>path</code> | 相对工作区的精确路径 |
| <code>physical_root</code> | paper、experiments、shared 或根目录 |
| <code>family</code> | 实验族或论文子树 |
| <code>area</code> | source/results/evaluation/runs 等 |
| <code>file_type</code> | Python、LaTeX、JSON、JSONL、CSV、PDF、日志、图片等 |
| <code>content_role</code> | 活动 PDF 源、结果、运行记录、外部依赖、缓存等 |
| <code>relevance</code> | active/evidence/history/generated/external 等 |
| <code>size_bytes</code> | 文件大小 |
| <code>modified_time</code> | 最近修改时间 |
| <code>symlink_target</code> | 符号链接目标 |
| <code>description</code> | 内容用途说明 |

生成器：<code>shared/workspace-management/generate_project_file_map.py</code>

重新生成：

    python shared/workspace-management/generate_project_file_map.py

该映射不遍历 <code>.git</code>；缓存和第三方环境仍列出并明确标记，顶层 symlink 作为单独行记录但不重复遍历。

## 11. 接手后的正确执行顺序

1. 阅读本文件、<code>remaining_issues_to_fix.md</code>、<code>writing_report.md</code> 和 <code>claim_to_source.md</code>。
2. 检查当前进程与 <code>run-status.json</code>，不要启动第二个相同强基线任务。
3. 等待五方法 <code>results.json</code> 生成，并核对 status、keys、error 和 C1f check-use audit。
4. 观察等待中的 finalizer 是否完成。若失败，只修复生成/路径/审计问题；不得改冻结 protocol 或删除不利 cases。
5. 等待 atom-vs-field attribution 完成，诚实更新独立归因结论。
6. 运行当前复现、页限、引用、匿名化和测试门禁。
7. 更新 Abstract、Introduction、Results、Limitations、Conclusion 中依赖最终强基线的句子。
8. 重新做两轮模拟审稿：先 correctness/contribution/evaluation，再 originality/rigor/clarity/systems fit。
9. 重建匿名 artifact，最后交给作者完成人工元数据与匿名 URL。

## 12. 常用验证命令

在工作区根目录运行：

    cd paper/current-usenix
    latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
    python reproduction/check_page_budget.py
    python reproduction/audit_references.py
    python reproduction/audit_submission_sources.py

主 claim ledger：

    python scripts/reproduce_usenix_main.py --allow-pending

最终强基线完成前，strict 模式应当因缺失 <code>results.json</code> 而失败；这是预期的 fail-closed 行为。

## 13. 已知风险

1. **强基线尚未完成。** 当前投稿结论不能升级为 go。
2. **效用非劣效未建立。** 不得把 -1.0 pp 平均差写成已通过非劣效；下界是 -5.4 pp。
3. **atom 独立归因仍有限。** 67/67 字段全部保留；raw-field control utility 更高。source-oracle collision 是目前最干净的 atom 价值证据。
4. **finalizer 状态文件是旧失败快照。** 必须等待本次队列覆盖，不能误判当前队列已失败。
5. **历史材料很多。** archive、旧 E 编号表、flat/compact copies 和 dated notes 不得覆盖活动稿。
6. **运行目录巨大。** headline 数字应来自 strict summary JSON，不应手数文件得出最终结论。
7. **page-report 漂移。** 以脚本输出为准；当前为 11/13。
8. **图表已重画但需最终复检。** 当前四图无重叠；最终表插入后仍需逐页视觉检查。
9. **API 凭证。** 不把任何密钥写入脚本、日志、论文或交接文档；只通过环境变量注入。
10. **工作树很脏。** 上级仓库含大量用户与历史修改；不得 reset、checkout 或删除与本任务无关的文件。

## 14. 作者必须完成的事项

1. 对所有 AI 辅助文字、数字、图和引用逐项负责并人工确认。
2. 提供作者名单、ORCID、topics、funding/acknowledgments 和 conflicts。
3. 将最终匿名 artifact 上传到稳定匿名地址，并在 Open Science appendix 中填入 URL。
4. 做最终匿名审查，包含 PDF、文件名、manifest、压缩包 metadata 和 URL。

旧 authority-manifest 的独立人工审查不是当前 provenance-origin 论文边界的阻塞项。只有重新主张 independently human-authored authority contracts 时才需要恢复该门禁。
