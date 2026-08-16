# Atom 实际作用实验的证据审计

日期：2026-08-03

## 总结判定

现有实验对 atom 的作用提供了三层不同强度的证据：

1. **较强的表示层证据**：受控碰撞、有限域和 held-out ToolSandbox 结果支持“工具名或整次调用会合并需要不同授权决定的效果，而经验证的 typed effect representation 可以分开这些情况”。
2. **窄但直接的运行时证据**：321-case AgentDojo applicability subset 中，仅把 pre-commit monitor 从 atom-field view 改为 whole-call view，ASR 从 `0/273` 变为 `3/273`，benign utility 均为 `9/48`。该结果说明字段级表示在真实闭环中可以阻止同一已计划工具上的参数扩张，但三个差异全部来自 Slack 的同一 injection goal，精确配对检验不显著（双侧 `p=0.25`），且样本按 atom monitor 已产生字段反馈来选择。
3. **模型自我治理证据为负**：仅把 atom 放入 system prompt 或工具描述，没有稳定优于 generic intent prompt 或 token-matched control。当前数据不支持“模型看到 atom 后会自行更安全地授权调用”。

因此，atom **有用，但目前被证实的作用是 authorization-relevant effect representation 和 deterministic mediation interface**，不是独立的 prompt defense，也不是模型自发安全推理能力的来源。

## 实验逐项判定

| 实验 | 核心结果 | 审计判定 | 论文用途 |
|---|---|---|---|
| E47--E50 controlled binding stress | 现有方法存在 joint binding 缺口；resource/authorization 是主要失败轴 | 可用，属于受控问题刻画 | 主文问题证据；不能估计真实失败率 |
| 有限域与 held-out ToolSandbox representation checks | common/value-role views 保留 authorization-separating pairs，typed representation 消除已枚举域内碰撞 | 可用，表示层最强证据 | 主文支撑 representation sufficiency；不能推出端到端安全 |
| 321-case closed-loop attribution | atom fields `0/273` ASR，whole call `3/273`；benign utility 同为 `9/48` | 可用但窄、未显著 | 主文保留，必须同时披露 subset selection、同一攻击目标和非显著性 |
| E81 A1 vs A9 registry ablation | refined registry 的 attack utility `124/169`，unrefined schema partition `107/169`，ASR 均 `1/169` | 有用的 utility/refinement 证据 | 主文或 appendix；仅限 26 个 reviewed tasks |
| AgentDojo 四例 self-governance pilot | validated atoms 未降低 ASR，且 benign utility `3/4 -> 2/4`；forecast parse-valid 为 0 | 有效负面结果 | Limitations/appendix；证明 descriptor visibility 不等于 task-to-effect authorization |
| 8-case explicit targeted prompt pilot | atom prompt ASR `1/8`，generic `1/8`，token control `0/8`；atom utility更低 | 有效探索性负面结果 | 不作为贡献表；可用于说明安全提示而非 atom 特异性驱动结果 |
| implicit V1/V2 | V1 no-guard ASR `0/8` 无判别力；V2 atom/shuffled 均 `2/8`，generic `0/8` | 有效负面诊断，但 V2 result-informed | appendix/failure analysis；不能作确认性结论 |
| E71 field necessity/runtime | necessity `66/70`，invariance `39/86`；runtime UPA 0 但 FDeny `20/22` | 只能作失败分析，当前 runtime 因果结论不可用 | 暂不进入主结果；修复标签回流、评分和路径后重跑 |
| atom specificity Round 1--6 | 报告声称 per-role rules 产生若干正面差异 | Round 1--5 条件接线错误，正面归因不可用；Round 6 仅为结果知情诊断 | 隔离，不引用其正面数字 |

## 关键实现问题

### 1. Round 1--5 的正确 atom 条件实际被传成 shuffled

`atom_specificity_smoke.py` 和 `atom_specificity_round2.py` 至 `round5.py` 的条件元组第五位被命名为 `is_atom`，但调用 `build_messages` 时被作为 `shuffle` 参数传入。`atom_without_rules`、`atom_with_rules` 和 `atom_shuffled_rules` 的第五位均为 `True`。例如：

- `atom_specificity_round4.py:199-204`：三个 atom 条件的第五位均为 `True`；
- `atom_specificity_round4.py:312-317`：第五位直接传给 `build_messages(..., shuffle, ...)`。

结果是 `atom_with_rules` 与 `atom_shuffled_rules` 并非“正确角色 vs 打乱角色”的有效对照；`atom_without_rules` 也使用了打乱角色。该错误恰好解释了多轮报告中两者行为高度一致。原 `atom-specificity-summary.md` 中关于正确角色、shuffled role 和 per-role 特异性的正面归因不能使用。Round 6 不复用这个参数错误，但它是在前五轮结果后选择案例和规则的修复诊断，且没有完整 matched controls。

### 2. E71 的离线标签进入了 descriptor 构造

E71 的 prompt 本身没有 gold leakage，但 artifact pipeline 并非纯 LLM 选择：

- `run_e71.py:226-242` 使用 sidecar `base_atoms` 和字段名启发式生成 `expected_atom_fields`；
- `run_e71.py:505-509` 把“任意 atom signature 改变”也计为必要性通过，未要求预期 atom 字段发生正确退化；
- `run_e71.py:600-620` 把 `expected_atom_fields` 带入 selected fields；
- `run_e71.py:647-678` 再用这些 expected labels 决定哪个参数绑定到 `resource_id`、`visibility` 和 `commit_mode`。

因此 E71 runtime descriptor 是 **LLM 输出加离线 expected-field 标签共同构造**，不能支持“LLM 通过字段必要性测试独立学会 atom binding”。此外，86 个应保持不变的输出中只有 39 个通过，说明当前 LLM atomizer 对非安全字段删除高度过敏。runtime 集合又包含 134 个 DENY、22 个 ALLOW；UPA 为零同时 FDeny 为 `20/22`，主要表现是 reject-heavy mediation。

### 3. E71 当前无法从整理后的目录直接复现

`e68_llm_counterfactual_atom_field_stress/run_e68.py:16-22` 仍寻找旧的 `evaluation/e61_realistic_trace_replay/...`，实际数据已移动到 `experiments/independent-contracts-and-realistic-traces/evaluation/realistic-agent-trace-replay/...`。相关测试出现 3 个 `FileNotFoundError`。现有 JSON 可以审计，但当前代码链在工作区重组后已断。

### 4. 321-case 结果方向正确，但效应很小且集中

whole-call comparator 的实现确实只检查工具是否在初始计划中，并忽略参数与 evidence；atom variant 使用 E77 字段比较。运行脚本固定模型、初始 plan cache、descriptor、totalization、recovery 和 sandbox。结果行数、case keys 和初始 plan material 均由 finalizer 检查。

但是：

- 307/321 cases 是因为既有 atom run 已产生字段 mismatch feedback 而入选；
- 三个安全差异全部是 Slack `injection_task_3`，分别发生在三个 user tasks；
- 配对安全变化为 `atom false -> whole-call true` 三例、反方向零例，双侧 exact McNemar `p=0.25`；
- benign utility 虽总数相同，但有 10/48 个配对发生相反方向变化；attack utility 有 52/273 个配对变化。

这是一条可信的 mechanism witness，但还不是稳定、跨攻击类型的 headline 因果效应。

## 验证状态

执行了以下测试集合：closed-loop attribution、targeted prompt、implicit prompt、self-governance 和 E71。

- `32` 项通过；
- E71 有 `3` 项因旧数据路径导致 `FileNotFoundError`；
- Round 1--6 没有针对 condition wiring 的单元测试，因而未发现上述接线错误。

## 论文建议

1. 保留主线：atom 是经反事实注册的、authorization-relevant effect representation；它为 pre-commit comparison 提供字段级接口。
2. 不写“atom prompt 提高模型安全推理”。现有 matched controls 不支持该声明。
3. 321-case 表格可以保留，但正文补充“三个差异属于同一 injection goal，结果为方向性而非显著性证据”。
4. E81 A9 可作为“反事实 refinement 有助于 utility”的辅助证据，但不要泛化到完整 benchmark。
5. 隔离 Round 1--6 原正面总结；修复 condition schema、加入 prompt-hash equality test、冻结独立案例后才能重跑。
6. E71 若继续使用，必须移除 expected labels 对 descriptor 构造的影响，将 necessity 定义改为预期字段的定向退化，并在 held-out cases 上评估生成 descriptor。

## 最终判断

这部分工作**有用**，但用途与最初期待不同：

- 它强化了论文边界，排除了“atom 作为 prompt 本身即可防注入”的错误路线；
- 它提供了一条窄但真实的字段级闭环 witness，说明 atom 能阻止已计划工具内部的参数扩张；
- 它暴露了当前最缺的证据：独立、预冻结、跨攻击类型的 whole-call vs atom-field 因果比较，以及不依赖离线标签的 descriptor registration。

在修复上述问题前，这些实验不能单独证明 atom 带来普遍的端到端安全提升，但可以与表示碰撞、有限域充分性和 E81 refinement ablation 共同支撑“atom 是有价值的安全控制接口”这一较窄、可辩护的论文主张。
