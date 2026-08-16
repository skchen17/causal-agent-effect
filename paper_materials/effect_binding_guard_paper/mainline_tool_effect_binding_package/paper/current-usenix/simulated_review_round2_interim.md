# USENIX Security 2027 模拟审稿：第二轮（中期证据版）

审稿日期：2026-08-09

审稿对象：`paper/current-usenix/main.pdf`

证据边界：本轮只采用已经冻结并完成的结果。Qwen3-32B、current-profile AgentLAB、current-C1f four-view、bounded-adaptive 和 raw-field attribution 仍在运行或排队，因此只作为缺失证据，不预判其结果。

## 结论与评分

**当前建议：Weak Reject，接近 Borderline。**

论文提出了一个合理的系统安全问题：如果监控器的表示合并了授权上应作不同决定的工具执行，那么后续分类器或策略无法恢复已经丢失的区别。论文进一步用源码执行反事实来验证 effect representation，并展示一个确定性的 pre-commit mediation 实例。问题、理论边界和负面结果总体表述诚实。

当前拒稿风险主要来自因果归因，而不是概念不成立。AgentDojo registry 保留了全部 67 个字段，因此 C1f 的安全结果尚不能证明收益来自最小 atom 表示，而不是 generic structured-field provenance checking。DeepSeek 上 Spotlighting 同样达到零次观察到的攻击成功，且效用更高；重复良性实验的非劣效门槛也略微失败。尚未完成的 second-model、迁移和闭环消融将直接决定最终判断。

| 维度 | 评分（1--5） | 判断 |
|---|---:|---|
| Originality | 3 | effect-side representation obligation 有区分度，但碰撞定理本身直接，创新主要依赖 source-executed registration 与系统证据。 |
| Technical Quality | 3 | 有真实源码状态差分、冻结协议和审计链；关键闭环归因与第二模型尚缺。 |
| Correctness | 4 | 条件和有限域边界写得较准确，负面结果没有被隐藏。 |
| Significance | 3 | 问题对 agent harness 有意义，但当前仅证明有限工具域和受限 provenance-origin policy。 |
| Clarity | 4 | 主线清楚，经典 complete mediation 与本文贡献区分明确。 |
| Reproducibility | 3 | 固定证据和脚本较完整；最终四个 required artifacts 与统一账本尚未完成。 |
| Reviewer Confidence | 4 | 主要判断可由源码、冻结 JSON、表格和审计产物直接核对。 |

## 主要优点

1. **问题定义具体。** 日历邀请等复合效果示例清楚展示了 tool name 或 coarse summary 为什么不足。
2. **表示问题与授权策略分离。** 论文没有把 C1f 写成完整 ACL、委托或通用 authority 系统。
3. **反事实验证基于执行结果。** source oracle 比让 LLM 自评 atom 是否合理更可信，且区分 committed-state change、output-only change 和 invalid intervention。
4. **理论范围克制。** representation collision、finite refinement 和 conditional confinement 的前提均被显式列出。
5. **负面结果透明。** `67/67` 字段保留、`38/75` 干预覆盖、308 次 invalid/unresolved、Spotlighting parity 和历史迁移效用下降均被保留。
6. **运行时可审计。** C1f 不调用额外 guard LLM，并将 pre-commit decision 与实际执行签名对账。

## 主要问题

### 1. Atom 表示的独立运行时贡献仍未建立

当前 registry 将 67/67 字段全部视为 security-relevant。这说明系统实现了一个保守字段级 provenance monitor，但没有从 AgentDojo 注册实验中得到稀疏或明显更小的 effect representation。现有 321-case atom-field/whole-call 结果来自 selection-conditioned subset，只能作为定向机制证据。

**需要的证据：** current-C1f four-view 闭环实验必须同时报告 no guard、whole-call provenance、effect-only 和 registered-field C1f 的 ASR、任务效用、触发范围和完整 mediation audit。另需在相同 321 个案例上加入 raw-field taint：它检查所有具体参数但删除 effect-label expansion。若该对照与 C1f 在相同调用上的决策及闭环结果没有可复现差异，运行时收益不能归因于 atom 语义；运行时部分应继续定位为 case study，atom 的独立贡献主要由 source-oracle collision 和 counterfactual registration 支撑。

### 2. 当前 PDF 尚未采用最终效用口径

Table 6 仍混合四次 no-guard 均值与其他方法的单次 pre-freeze 值。冻结的重复实验已经完成：no guard、Spotlighting、C1f 分别为 `301/388`、`305/388` 和 `297/388`。C1f 与 no guard 的均值差只有约一个百分点，但 task-clustered 单侧 95% 下界为 `-0.054`，没有通过预注册的 `-0.05` 非劣效门槛。

**需要的修订：** 最终表格必须替换旧口径，并写明“平均效用接近，但本实验未建立 5% margin 下的非劣效性”。不能使用“utility-preserving”或等价表述。

### 3. Runtime 防御尚未显示强于简单基线

DeepSeek 官方攻击中 no guard 仅成功 6 次，Spotlighting 与 C1f 都为 0。冻结 held-out 320-case 中 no guard 为 4/320，另外两种方法均为 0，但 C1f 任务效用 `235/320`，低于 no guard 的 `250/320` 和 Spotlighting 的 `238/320`。这些结果说明 C1f 可以阻止观察到的攻击目标，但没有证明数值优势。

**需要的证据：** Qwen3-32B matched run 必须完整覆盖每种方法的 726 个相同 key。若更易受攻击的第二模型仍显示 C1f 相对 no guard 的安全提升，并且效用代价可解释，证据会明显增强；若 Spotlighting 继续在安全与效用上不弱于 C1f，论文应强调可审计 mediation 和表示验证，而不是防御性能。

### 4. Counterfactual adequacy 仍是有限域性质

有限域中 typed effects 与 source-effect partition 一致，因此零碰撞是有意义的 sufficiency 结果，但其外推能力有限。ToolSandbox held-out 只有 32 个 context、五个工具。AgentDojo-wide 审计中仅 38/75 字段实例获得至少五种有效干预，七个字段没有有效 mutation。

**需要的说明：** 论文应进一步区分三类结论：观察到 committed-effect witness、在冻结有限域中 authorization-sufficient、以及未知域中的保守保留。不得把 invalid mutation 或 fail-closed retention 当作字段必要性的正证据。

### 5. Threat model 依赖可信 provenance 和受限 policy

C1f 只检查 untrusted observation 是否引入 authenticated task 未支持的 registered effect/value。它不判断 ACL、delegation、quota、用户自身恶意请求、output-only goals 或未标记 provenance。该边界理论上合理，但缩小了系统结果的适用范围。

**需要的证据：** current-profile AgentLAB transfer 必须证明相同 checkpoint、相同 303-key manifest、每个实际执行调用都有一致的 pre-commit allow 记录，并直接报告效用。历史 profile 的 `87/303` 效用不能作为当前实现的支持证据。

### 6. “因果”定位应继续保持克制

本文干预的是工具参数和 pre-state，并观察状态差分；它并不识别开放域因果图，也不分析模型内部因果机制。当前将方法写成 counterfactual falsification 与 CEGAR-style refinement 是合适的。

**需要的修订：** 避免将有限受控干预写成 general causal discovery。可将贡献描述为 execution-grounded causal witness 或 intervention-based validation，但不应扩大到模型推理因果性。

### 7. 最终 artifact 尚未达到投稿状态

paper-local reproduction 当前只有 167 条固定 claim rows，并明确标为 `pending_required_artifacts`。匿名包是预览版本，而不是最终可复现包。

**需要的证据：** 五个 pending artifact 完成后，fail-fast reproducer 应生成 207 条 claim rows 和 5,549 条逐案例记录；随后重新生成表格、结果段、claim map、PDF、匿名包和审稿报告。任何缺 key、错误行或协议 hash 不匹配都应阻断 finalization。

## 次要问题

1. Abstract 当前仍使用旧的 `6/608` 主结果，未体现重复效用和 held-out 结果；待最终数据生成后应重新平衡摘要中的安全与效用结论。
2. Table 2 的 custom stress 与 released checkpoint adapted-input 结果需要保持醒目标注，避免被误读为原论文 benchmark reproduction。
3. 结果部分同时出现 retrospective interceptability、selection-conditioned closed loop 和完整 benchmark，读者容易混淆。建议在每张表标题中直接标注 `retrospective`、`targeted closed-loop` 或 `full benchmark`。
4. “minimal” 最好始终带有 `policy- and intervention-relative` 限定；标题中目前没有使用 minimal，风险较低。
5. 论文正文当前结束于第 9 页，仍有空间插入最终结果，但不能用现有页数替代最终编译后的 13 页检查。

## 对作者的问题

1. 在四视图闭环实验中，registered-field C1f 相比 whole-call provenance 是否在相同 ASR 下提高任务效用或减少受影响轨迹？
2. Qwen3-32B 上 no guard 的攻击成功率是否足够高，使防御差异不再只由少数 discordant cases 决定？
3. current-profile AgentLAB 的效用是否显著高于旧 profile 的 `87/303`，同时保持完整 mediation reconciliation？
4. 对未取得 committed-effect witness 的九个字段，保留它们是因为无法验证还是已发现状态依赖？能否在附录中逐字段区分？
5. typed effect qualifier 的初始候选由谁或什么规则提出？source oracle 如何避免验证规则与表示规则共享同一错误假设？

## 从 Weak Reject 转向 Weak Accept 的条件

1. Qwen3-32B matched comparison 完整、无错误，并显示 C1f 在更有攻击信号的设置下具有安全收益，同时公开效用代价。
2. current-C1f four-view 闭环实验显示 atom/registered-field granularity 相比 whole-call 或 effect-only 至少在 selectivity、任务效用或触发范围上具有独立价值。
3. current-profile AgentLAB 完成严格的 checked/executed multiset reconciliation，且效用不再出现历史 profile 的严重下降。
4. bounded-adaptive 结果完整保留，不发生结果后修补。
5. 最终稿用冻结重复实验替换旧混合口径，并通过 13 页、引用、匿名化和 fail-fast reproduction 检查。

若第 2 项失败，即使其他运行时结果良好，最稳妥的投稿定位也应是“effect representation and validation paper with a bounded mediation case study”，而不是“new leading prompt-injection defense”。

## 最终判断

论文已经具备可投稿研究工作的主体，而不是概念性系统提案。表示碰撞、源码反事实和受限 pre-commit mediation 形成了连贯证据链。但当前还不能确认 atom granularity 是运行时收益的原因，也不能声明良性效用非劣。完成已冻结的四个实验并严格吸收负面结果，是从当前 Weak Reject 进入 Weak Accept 区间的必要条件。
