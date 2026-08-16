# T2 O6 命题草稿（重述版：override trail 完整性）

日期：2026-08-04
产出：research-assistant，供 PM 审阅；**本草稿不修改 main.tex / sections/ 任何内容**。
依据：
- 决策书 `window_execution_decision_2026-08-04.md` §2b（T2 前置核实结论与两个必要条件）
- 审稿人校准 `reviewer_perspective_improvement_evaluation_2026-08-04.md` §4 攻击点 2
- 代码证据：`experiments/intent-bound-runtime-guard/source/effect-difference-runtime-guard/e77_runtime.py`
  （`apply_uncertainty_policy` L162-235；`AUTHORIZED_FIELD_STATUSES` L44-51）、
  `agentdojo_e77_runtime_patch.py`（审计落盘 L669-696；证据回写条件 L723）
- 配套测量：`override_composition_measurement_2026-08-04.md`（同日期，本目录）

## 0. 结论先行

1. O6 的**条件可支撑性成立**：resolver-fill 侧六态（`AUTHORIZED_FIELD_STATUSES`，e77_runtime.py L44-51）
   均经 registered projection / 授权证据核验；审计同时落盘 strict 与 effective 双判决
   （patch L676/L678/L690），满足"排除式保证"所需的 trail 结构。
2. 命题**必须**按决策书 §2b 重述为"**排除式保证 + 证据隔离**"，并显式声明**非肯定性成员证明**性质；
   本草稿全文避免 "established" 措辞（替代词：recorded / excluded / isolated / witnessed-as-absent）。
3. **新增红旗发现（必须上报 PM）**：初步测量在 v17 部分审计中发现 2 行 override 的最终
   reasons/checks 携带 `outside_exact_plan`（审计行 1097/1106），机制为
   `field_decisions` 按字段名 dict 赋值时同字段后续 authorized check 覆盖先前 BLOCK
   （e77_runtime.py L188-212，多值字段场景）。这与决策书 §2b 第 2 条"五类扩权发现在结构化路径硬阻断"
   的既有核实结论**不完全一致**。在处置（修复+重跑，或限定+披露）之前，O6 在论文层面零承诺
   （与决策书 §4 风险③红线一致）。详见 §4.3。

## 1. 记号（沿用 security_analysis.tex §Conditional Effect Confinement）

- commit \(i\)：一次对外有效果的调用提交；\(u_i\) 为该调用，\(\mu(u_i)\) 为其真实效果多重集；
- \(A_i\)：contract \(K_i\) 产生的 atom-instance 序列；\(\gamma(a)\) 为 atom 出现 \(a\) 代表的
  具体效果多重集，\(\gamma(A)=\biguplus_{a\in A}\gamma(a)\)；
- \(\Gamma_i\)：runtime envelope（对 atom 出现的谓词）；
  调用局部具体闭包 \(\mathsf{Cl}_i(\Gamma_i,A_i)=\biguplus_{a\in A_i,\ \Gamma_i(a)=\mathrm{true}}\gamma(a)\)；
- \(B^{(\eta(i))}\)：认证授权 epoch \(\eta(i)\) 提供的具体界（bound）；任务级界记作 \(B_q\)；
- 六态集合 \(\mathcal{S}_{\mathrm{auth}}=\{\)matched_exact, matched_runtime_default,
  resolved_from_registered_projection, resolved_from_original_task,
  resolved_from_authorized_read, resolved_from_authorized_effect_result\(\}\)
  （e77_runtime.py L44-51）；resolver 态 \(\rho=\) resolver_fill_requires_replan。

**Override 事件**（协议 §7.2 override rate 的分子口径）：pre-commit 记录满足
strict 判决 \(d_s=\) `guard_decision` \(\notin\{\text{ALLOW}\}\) 而 effective 判决
\(d_e=\) `decision` \(=\) ALLOW，策略为 `allow_with_trail`（patch L669-696 落盘
`guard_decision`/`decision`/`diagnostic_uncertainty_override`/`strict_authorization_satisfied`）。

**结构化 / fallback 两路**（e77_runtime.py L162-235）：
- 结构化路径（L187-212）：存在逐字段 checks；每字段判定三值
  \(\{\text{ALLOW},\ \text{ALLOW\_WITH\_TRAIL},\ \text{BLOCK}\}\)，当且仅当无 BLOCK 字段时
  \(d_e=\) ALLOW（L209-211），并落盘 `field_decisions`（L212）；
- fallback 路径（L213-234）：无结构化 checks；当且仅当所有 reason 含 \(\rho\) 且不含五类
  扩权 token（L220-226）时 \(d_e=\) ALLOW（L232-234）。

## 2. O6 陈述（重述版）

> **O6（Override-trail integrity，排除式保证 + 证据隔离）.**
> 设 commit \(i\) 的执行由一次 override 事件放行（\(d_s\neq\) ALLOW，\(d_e=\) ALLOW，
> policy = `allow_with_trail`），其审计 trail 为 \(T_i\)。则：
>
> **(O6-a 排除式保证)** \(T_i\) 逐字段（结构化路径）或逐 reason（fallback 路径）记录了
> 比较状态，并且满足排除性质：
> \[
> \forall \text{field } f:\ \mathrm{status}_i(f)\in \mathcal{S}_{\mathrm{auth}}\cup\{\rho\},
> \]
> 即五类扩权发现
> \(\mathcal{D}=\{\)forbidden_field_used, outside_exact_plan, tool_not_in,
> missing_e77, revision_binding_invalid\(\}\) 中的任何状态/reason 均**未**出现在
> 被放行的比较记录中。等价地：override 放行的必要条件是
> \(\mathcal{D}\cap \mathrm{findings}(T_i)=\varnothing\)。
>
> **(O6-b 非肯定性成员证明声明)** 对状态为 \(\rho\) 的字段，trail 记录的是
> "该字段值由 resolver 填充且被放行"这一事实；\(T_i\) **不构成**被覆盖效果值属于
> \(B_q\)（或 \(B^{(\eta(i))}\)）的肯定性成员证明。本义务不声称
> \(\mu(u_i)\preceq B^{(\eta(i))}\) 对 override 放行的字段成立；该方向的不等式
> 不在 O6 的结论集内。
>
> **(O6-c 证据隔离)** 设 \(E_i\) 为 commit \(i\) 之后写入 resolver 证据库的条目集合。
> 若 commit \(i\) 是 override 放行且 side-effectful，则其结果不进入证据库：
> 证据回写条件为 `not side_effectful or strict_decision == ALLOW`
> （agentdojo_e77_runtime_patch.py L723），即
> \[
> \text{side-effectful}(u_i)\ \wedge\ d_s\neq\text{ALLOW}
> \ \Longrightarrow\ E_i=\varnothing .
> \]
>
> **(O6-d 不扩充后续授权依据，推论)** 由 (O6-c)，后续 commit \(j>i\) 的比较中，
> 状态 resolved_from_authorized_effect_result / resolved_from_authorized_read
> 所能引用的证据不含任何 override 放行的副作用结果；因此 override 不扩充
> 后续调用的授权依据集合。
>
> **范围条件（scope）**：
> (S1) 本义务就现有 trail schema 定理化（协议冻结前不改 runtime 代码，决策书 §2b 红线）；
> trail 无"填充值事后复验"字段，故 (O6-b) 的否定性表述不可升级为肯定性表述。
> (S2) 设 \(\phi\) 为 fallback 路径 override 占全部 override 的比例；若 \(\phi>20\%\)，
> O6 限定于结构化路径并随文披露 \(\phi\)（决策书 §2b 必要条件 2）。
> (S3) (O6-a) 对"同一字段产生多条 check"的多值字段成立的前提是逐字段判定按
> **最严格优先**聚合；当前实现的聚合行为见 §4.3 红旗发现，处置前 (O6-a) 对多值字段
> 不声明成立。

**措辞约束（防审稿攻击点 2，reviewer_perspective §4.2）**：O6 的正文陈述与证明
显式写明"非肯定性成员证明"；禁用 "established"；推荐措辞集合：
"the trail records…"、"expansion findings are excluded"、"the result is isolated
from the evidence ledger"、"no membership witness is claimed"。

## 3. 支撑引理与代码证据

**引理 1（五类扩权发现的策略层硬阻断）.** 在 `allow_with_trail` 下，
\(\mathcal{D}\) 中的发现不能由不确定性策略直接翻转为 ALLOW：

- 结构化路径：状态 \(\notin \mathcal{S}_{\mathrm{auth}}\cup\{\rho\}\) 的字段判 BLOCK
  （e77_runtime.py L199-200）；存在 BLOCK 字段时保留 strict 判决、仅把 reasons
  收窄到被阻字段（L201-208），不发生 override。五类扩权状态均属 BLOCK 类。
- fallback 路径：`disqualifying` 元组恰为 \(\mathcal{D}\) 的五 token
  （L220-226，子串匹配）；任一 reason 含 token 则 `is_resolver_only` 为假
  （L227-231），不发生 override（L232-234）。

**引理 2（证据隔离）.** 副作用调用的结果进入证据库当且仅当 strict 判决为 ALLOW：
patch L720-752，条件在 L723（`if not descriptor.get("side_effectful") or
strict_comparison["decision"] == "ALLOW"`）。override 事件的 strict 判决非 ALLOW，
故其副作用结果不落证据库；后续比较中 `resolved_from_authorized_effect_result`
与 `resolved_from_authorized_read` 两态（六态之二，L49-50）的供给集因此不含
override 产物。审计侧对应事件为 `authorized_read_evidence`（patch L737-752），
可用于事后核对隔离性（协议 §5 schema `n_uncertainty_override` 与逐 case 计数，
协议 §6）。

**引理 3（双判决可审计性）.** 每次 pre-commit 均落盘
`decision`（effective）、`guard_decision`（strict）、`initial_decision`/`initial_reasons`
（recovery 前）、`diagnostic_uncertainty_override`、`atom_checks`（逐字段
`check_result`）、`strict_authorization_satisfied`、`execution_attempted`
（patch L669-696，字段位于 L676/L678/L679-680/L682/L687/L690/L694）。
这给出 O6 的 witness 载体 \(T_i\)，也是协议 §7.2 override rate 与
reconciliation violations（目标 0）的度量基础。

## 4. 边界条件与红旗发现

### 4.1 trail 的已知局限（决策书 §2b 必要条件 1）

trail 记录 resolver_fill 字段的**放行事实与来源类别**，但不记录填充值的
事后复验（无 post-hoc membership re-check 字段）。这是 (O6-b) 采用否定性
表述的结构性原因：若写成"被覆盖效果在 \(B_q\) 内的肯定性成员证明"，则 witness
不存在，命题反噬（决策书 §4 风险③）。

### 4.2 fallback 路径的 trail 差异

fallback 路径无逐字段 trail，只有 call-level reasons（e77_runtime.py L213-234）。
其占比 \(\phi\) 必须由 v17 审计实测（决策书 §2b 必要条件 2）。
**初步测量结果**（v17 未完成，部分审计快照）：\(\phi = 0/265 = 0.000\)，
远低于 20% 阈值；finalize 后须用同一脚本复测（见 override_composition_measurement
文档）。注意：\(\phi\) 低**不能**替代 §4.3 的处置。

### 4.3 红旗发现：多值字段的逐字段判定覆盖（PM 决策项）

**现象**：初步测量发现 2 行 override（审计行 1097/1106，均为 `send_email`，
`recovery_state=CALL_REVISION_REQUIRED`）的**最终** reasons 与 `atom_checks`
携带 `outside_exact_plan`。两行的 checks 均为同一模式：
字段 `attachments` 产生两条 check，先 `outside_exact_plan`（值 'file'），
后 `matched_exact`（值 '19'），其余字段为 resolver_fill / matched_exact。

**机制（代码定位）**：结构化分支的 `field_decisions` 是以字段名为键的 dict
（e77_runtime.py L188：`field_decisions: dict[str, str] = {}`；L192-200 循环内
`field_decisions[field] = ...`）。同一字段的多条 check（list target 展开）
按 check 顺序**后值覆盖前值**：后来的 `matched_exact` 覆盖了先前的 BLOCK，
`blocked` 集为空（L201），于是 L209-211 放行并置 override 标志。
即：**多值字段中只要存在一条 authorized check 且排序在后，同字段的被阻值即被放行**。

**与既有核实结论的关系**：决策书 §2b 第 2 条"五类扩权发现在结构化与 fallback
两路均硬阻断"在单 check 字段上成立（引理 1 的推导无误），但未覆盖多 check 字段
的聚合行为。此发现不推翻 O6 的可支撑性判断，但 (O6-a) 在当前代码下对多值字段
不成立，必须先处置。

**处置选项（供 PM 决策；本任务包红线禁止修改 runtime 源文件，故此处只列选项）**：
1. **修复后重跑**：将聚合改为"最严格优先"（字段一旦 BLOCK 则保持 BLOCK），
   属协议 §2.2 允许的代码 bug 修复，但所有受影响条件必须从头重跑——
   v17 与后续 V0-V3 均使用同一 runtime，重跑成本按决策书 §4 风险①吸收
   （+3-5 天，W6 缓冲）。修复后 (O6-a) 无多值字段例外，O6 可按 §2 全文陈述。
2. **限定 + 披露**：O6 限定于"每字段至多一条 check"的调用子集，随文披露
   例外行数与机制。成本最低但给审稿人留下实现性弱点攻击面，且与
   "hard-block" 措辞冲突，不推荐单独采用。
3. **混合**：先修复，在修复版重跑前，论文表述采用选项 2 的限定语；
   finalize 复测后按选项 1 放开。

**测量口径**：配套脚本（schema `override-composition/2`）已将
"final 材料中的 token"（违例候选）与"仅 initial_reasons 中的 token"
（PLANNER_REPLAN_APPLIED 恢复路径先解决再重验，非策略层越权）分开计数；
当前快照 43 行属后者、2 行属前者。finalize 后复测即得最终裁决。

## 5. O6 与 O1-O5 的相容性论证要点

1. **与 O5（fail-closed uncertainty）相容**：O6 不放宽 O5 的排除集——
   缺 contract、未解析的 effect-bearing 默认值/身份、矛盾授权、不可用 provenance
   仍不能产生 ALLOW；override 仅作用于状态恰为 \(\rho\) 的字段
   （e77_runtime.py L197-198）或 reason 全为 \(\rho\) 的调用（L227-231），
   属 O5 排除集之外的已枚举情形。O6 是 O5 在 `allow_with_trail` 实验策略下的
   精化（refinement），不是例外条款。
2. **与 O3（complete mediation）相容**：override 事件仍是"先判决、后执行"——
   \(d_e\) 在执行前产生且完整落盘（patch L669-696 先于 L717 执行）；
   `execution_attempted` 与 `decision` 的一致性由 reconciliation 检查监督
   （协议 §7.2 reconciliation violations 目标 0；初步测量为 0）。
3. **与 O4（check-use integrity）相容**：执行器使用的是经 totalization 的
   checked call；override 只改变判决标签，不替换被执行的参数对象
   （patch L477-478 totalize 后比较、L717 执行同一 `call.args`）。
4. **与 O2（envelope soundness）的边界**：O2 声称对 accepted plan/revision 有
   \(\mathsf{Cl}_i(\Gamma_i,A_i)\preceq B^{(\eta(i))}\)。O6 明确**不**把该包含链
   延伸到 override 放行的 \(\rho\) 字段——这正是 (O6-b) 的作用：O6 给出的是
   "扩权发现缺席 + 结果不入证据库"，而不是 envelope 包含。两个义务在
   \(\rho\) 字段上互补而不重叠。注意：planner replan 恢复路径
   （patch L499-567，`PLANNER_REPLAN_APPLIED`）会改写 plan 并重验调用，其授权侧
   正确性属 O2 对 revised plan 的核验范畴，不在 O6 内；trail 用
   `initial_reasons` 与 `recovery_state` 将两者分离（§4.3 测量口径即依赖该分离）。
5. **与 O1（causal-abstraction soundness）无关涉**：O6 不改动 \(\mu\) 与
   \(\gamma\) 的关系，仅约束判决层与证据层。
6. **对 Theorem single-commit confinement 的影响**：O1-O5 下的包含链
   \(\mu(u_i)\preceq\mathsf{Cl}_i\preceq B^{(\eta(i))}\) 对 strict-ALLOW 提交不变；
   对 override 提交，可证的替代结论是 (O6-a)/(O6-c)/(O6-d)：
   扩权发现缺席、效果不入证据库、后续授权依据不扩充。由 (O6-d)，轨迹级归纳
   （Corollary trajectory-prefix）中"后续比较的证据供给"这一前提不因 override
   而被污染，故 override 不破坏**后续**提交的包含链前提。这是"override 不扩充
   后续授权依据"的定理化价值所在。

## 6. 与初步测量的映射与 finalize 后更新流程

| O6 成分 | 测量脚本输出键 | 初步值（v17 部分快照，非最终） |
|---|---|---|
| override 总量（协议 §7.2 分子） | `overrides.total` | 265（2661 pre-commit 中） |
| fallback 占比 \(\phi\)（S2 阈值 20%） | `overrides.fallback_share_of_overrides` | 0.000 |
| 五类硬阻断（final 材料违例，要求 0） | `five_class_hard_block.o6_hard_block_violations_final` | **2（红旗，§4.3）** |
| 恢复路径已解决（非违例） | `overrides_with_token_in_initial_reasons_only` | 43（均 PLANNER_REPLAN_APPLIED） |
| reconciliation violations（要求 0） | `integrity.reconciliation_violation_count` | 0 |

finalize 后流程：重跑 `override-composition-measurement.py` →
若 \(\phi>20\%\) 则按 (S2) 限定结构化路径并披露；若违例计数 \(>0\) 则按 §4.3
处置结论更新 O6 范围条件；随后才允许进入论文写作（B 线顺序，决策书 §2e）。

## 7. Table e80_obligations 建议行（草稿，供后续入表）

| Obligation | Evidence | Status |
|---|---|---|
| O6 override-trail integrity | 双判决审计（strict/effective 逐行落盘）；五类扩权发现在两路策略的排除性检查（finalize 后复测）；override 副作用结果不入证据库的回写条件审计 | Partial pending §4.3 disposition（禁止写 Scoped pass，直至违例计数在 finalize 审计中为 0 且多值字段问题处置完毕） |

## 8. 写作禁则清单（本草稿已遵守）

1. 禁写"被覆盖效果在 \(B_q\) 内的肯定性成员证明"；
2. 禁词 "established"（指称 O6 结论时）；
3. 禁在 finalize 复测前把初步测量数字写入论文正文；
4. 禁在 §4.3 处置前声称"五类发现硬阻断"无条件成立；
5. O6 不得引用 V0-V3 任何结果（未运行）。
