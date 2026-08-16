# Claim Map 分支 Diff 模板（V0-V3 正 / 零负 / 混合）

日期：2026-08-04
产出：research-assistant。依据决策书 `window_execution_decision_2026-08-04.md` §2f 项 1、
协议 `strict_atom_representation_attribution_protocol_2026-08-03.md` §2.1/§2.2/§2.3/§4/§13、
`d1_results_branch_skeleton_2026-08-04.md` §0（分支切换表）与 §4（执行规则）。

**硬约束**：
1. 本文档是独立草稿。**在 v17 finalizer 通过且 H1-H5 判定释放之前，禁止对
   `claim_to_source_map.md` 做任何编辑**（R1 overclaim 触发器；决策书 §2f 项 1、
   D1 §4 规则 1）。本文档内所有数字均为占位符。
2. 模板只覆盖 V0-V3 相关的行变更；与本模板无关的行（理论、普查、有限域、held-out、
   E48/E50、E85、transfer 等）不在任何分支下被触碰。
3. 每个新增/修改行必须五列齐全（Claim | Paper location | Authoritative result |
   Generating code/test | Boundary），缺一列不得入表（§7 审查清单）。

---

## 1. claim_to_source_map.md 现状结构（阅读记录）

文件：`paper/current-usenix/claim_to_source_map.md`（96 行，2026-08-04 核读）。

### 1.1 行 schema

主表五行结构（L7 表头）：

| 列 | 内容要求 |
|---|---|
| Claim | 单句事实性陈述（含具体数字或定理名） |
| Paper location | 该 claim 出现的论文位置（Abstract/Introduction/Results/Limitations/附录等） |
| Authoritative result | 真源文件路径（frozen JSON/report）或"定理/定义"声明 |
| Generating code/test | 生成该结果的脚本与测试 |
| Boundary | 适用边界（不外推声明、选择条件、post-hoc 免责等） |

### 1.2 特殊区段

- **Status 头**（L3-5）：列出当前已对齐的 claim 族（theory, source-effect prevalence,
  collision, finite-domain, capacity-matched baseline, granularity-attribution,
  fixed-transfer, authority, mediation, cost）。分支更新时必须同步此头（见各模板）。
- **Pending Claims Excluded From The PDF**（L63-72）：6 项排除声明（adaptive 泛化、
  AgentLAB 自适应、跨模型、因果 overhead、独立人工审阅、生产保证）。
- **Retracted Claims: Citation Prohibited**（L74-95）：atom-specificity 谱系撤回声明 +
  L93-95 脚注（"321-case 闭环归因行在 strict 726-key 协议完成前仍是唯一可采纳的
  granularity-transfer 证据"）。**该区段任何分支下只增不减、永不放松。**

### 1.3 本模板涉及的行锚点（以 claim 首词+行号定位）

| 锚点 | 行号 | 内容摘要 |
|---|---|---|
| CM-HDR | L3-5 | Status 头 claim 族列表 |
| CM-E78-CAP | L32 | E78 capacity-matched 保留 726 keys / 60 reruns |
| CM-E78-U | L33 | 627 配对 ASR 54→2；97 benign utility 63→33（Boundary："strong tradeoff, not Pareto dominance"） |
| CM-E78-A | L34 | 629 evaluable 攻击键、all-key bounds |
| CM-PA-1 | L35 | pathway audit：37 损失中 32 含 runtime feedback；47/50 分层（Boundary：post-hoc、非因果、官方标签不变） |
| CM-PA-2 | L36 | 16/32 initial-plan、22/32 binding/evidence、12 例 resolver 值字面在场（Boundary：类别重叠、literal presence 非语义证明） |
| CM-PA-3 | L37 | 四格机制 probe（账单工作流） |
| CM-PL-1/2/3 | L38-40 | 三行 excluded-from-PDF pilot 行（smoke / benign pilot v8 / onboarding audit） |
| CM-GL-321 | L41 | 321-case 闭环归因（3/273→0/273，效用相同；Boundary：applicability subset, field-level feedback 选择） |
| CM-E84 | L42 | 26-task reviewed authority（ASR 5/169→1/169、BU 20/26→15/26、UA 121/169→124/169） |
| CM-DISC | L44 | 七个 discordance 全为只读、无 denial/abstention；净差 5→3 |
| CM-FB | L47 | 97 benign / 426 checks：26 成功、152 abstention（107 缺 manifest、43 缺 resolver proof）；Boundary：fail 50-task gate、mechanical correlation |
| CM-E81-REG | L48 | registry 替换使 attack utility 124/169→107/169 |
| CM-BURDEN | L54 | 44/97 manifests 通过审阅、26 编译 |
| CM-PEND | L63-72 | Pending 排除区段 |
| CM-RETR | L74-95 | Retracted 区段 + granularity 唯一证据脚注 |

---

## 2. 分支 → 模板映射（协议 §2.3 矩阵 → H1-H5 判定 → 模板选择）

判定输入（协议 §2.1）：H1 安全（配对 ASR，629 attack cases，Holm-McNemar）、
H2 benign utility 非劣（界 −0.05）、H3 attack utility 非劣（界 −0.05）、
H4 非拒绝驱动、H5 跨族一致性（≥3 suite 且 ≥3 静态攻击 strata）。

| 协议 §2.3 矩阵行 | 判定组合 | D1 分支 | 本模板 |
|---|---|---|---|
| 行 3：ASR 更低且效用非劣 | H1∧H2∧H3∧H4∧H5 | N2 全量 | **模板 P** |
| 行 2：ASR 相同但效用更高 | H1 不成立（ASR 平）且 H2/H3 方向为正 | N2 变体 | **模板 P**（仅启用 P-NEW-5，安全主张行不新增） |
| 行 1：仅优于 V0、不优于 V2 | H1 部分成立（V3>V0，V3≈V2） | N2 细分 + N3 局部 | **模板 M** |
| 行 4：ASR 更低但拒绝驱动/效用非劣失败 | H1 成立但 H2 或 H3 或 H4 失败 | N2 细分 + N3 局部 | **模板 M** |
| 行 5：差异集中单一 suite/goal | H1 成立但 H5 失败 | N1 + 机制 witness | **模板 M** |
| 行 6：无显著或无一致收益 | H1 失败或 V3≈V2 | N3 全量 | **模板 Z** |

叠加规则：N2/N3 可局部叠加（混合分支），以 D1 §0 表为唯一依据（D1 §4 规则 4）；
混合时模板 M 优先，M 中未覆盖的行变更才允许引用 P/Z。

---

## 3. 模板 P（正分支：H1-H5 全过 / 行 2 变体）

### 3.1 需要新增的 claim 行

**P-NEW-1（V0-V3 主归因行）**

- Claim：`On all 726 frozen AgentDojo v1.1.2 official keys under one common plan
  cache, scorer, and checkpoint, the validated atom-field monitor (V3) changes
  official ASR from [V0-ASR] (V0 tool_identity_only) and [V2-ASR] (V2
  raw_schema_fields) to [V3-ASR]; benign utility changes from [V2-BU] to [V3-BU]
  and attack utility from [V2-UA] to [V3-UA]; paired ASR difference [DELTA-ASR],
  Holm-adjusted McNemar p=[P-HOLM], 10,000-seed-20260803 paired bootstrap 95%
  CI [CI-ASR], with discordant counts [DISC-COUNTS]`
- Paper location：Results §Representation Attribution（D1 R.A.1）；Abstract（若 Phase D 回填）
- Authoritative result：`experiments/security-analysis-ablation-and-overhead/results/strict-atom-representation-attribution/report.json`
  `[PENDING-FINALIZE：finalize 后以实际 frozen 路径替换]`
- Generating code/test：`experiments/security-analysis-ablation-and-overhead/source/strict-atom-representation-attribution/`
  的 `run_benchmark.py` / `finalize.py` / `statistics.py` + 配对完整性测试（协议 §8 树）
- Boundary：`Same frozen plan cache and declared authority; conclusion scoped to
  the incremental role of the representation layer given identical plan-derived
  authority (protocol §3.3); not a claim about planner independence or
  completeness; all non-evaluable and error rows retained (protocol §5 error
  policy)`

**P-NEW-2（H5 strata 一致性行）**

- Claim：`The V3-V0/V2 ASR difference appears in [N-SUITES]/4 suites and
  [N-STRATA] static attack strata; per-suite and per-stratum paired differences
  are [STRATA-TABLE-REF]`
- Boundary：`Stratification dimensions (suite, attack type, injection goal) were
  pre-registered before results (protocol §2.1 H5); a difference confined to one
  injection goal is demoted to a mechanism witness (protocol §2.3 row 5)`
- Authoritative result / code：同 P-NEW-1（report.json 分层字段）

**P-NEW-3（H4 非拒绝驱动分解行）**

- Claim：`The ASR reduction decomposes into [BLOCK-BY-FIELDCHECK] field-check
  blocks, [BLOCK-BY-UNREGISTERED] unregistered-tool blocks, [BLOCK-BY-ABSTAIN]
  authority-evidence abstentions, and [BLOCK-BY-NOTATTEMPTED] cases where the
  model did not attempt the injection goal; DENY/ABSTAIN rates, monitor
  applicability, override rate, and strict execution ratio are [DECOMP-TABLE-REF]`
- Boundary：`Decomposition is the pre-registered four-category audit (protocol
  §7.2); it attributes mechanism share, not causal necessity`

**P-NEW-4（stability 行）**

- Claim：`On the pre-selected 160-case stability subset, repeat 1/2 give per-case
  flip rate [FLIP-RATE] with direction consistency [DIR-CONSIST]`
- Boundary：`Stability repeats bound run-to-run variation at temperature zero;
  they do not replace the full 726-key primary result (protocol Phase 4)`

**P-NEW-5（行 2 变体专用，仅当 ASR 持平且效用更高时启用）**

- Claim：`V3 matches V2 ASR ([ASR-FLAT]) while changing benign utility from
  [V2-BU] to [V3-BU] (bootstrap 95% CI [CI-BU]); the difference is accompanied by
  [OVERDENY-DELTA] change in over-denial on benign keys`
- Boundary：`Supports a utility contribution of counterfactual refinement
  (protocol §2.3 row 2), not a security-granularity claim`

### 3.2 需要修改的现有 claim 行

| 锚点 | 修改内容 |
|---|---|
| CM-HDR | claim 族列表追加 `strict-attribution`（"granularity-attribution" 保留，见 §3.3） |
| CM-GL-321 | Boundary 追加：`Superseded as the main attribution evidence by the strict 726-key protocol; retained as the selection-conditioned applicability-subset witness`；Claim 与 Paper location 不改（321 数字是 frozen 事实） |
| CM-RETR（L93-95 脚注） | 将 "remains the only admissible granularity-transfer evidence … until the strict 726-key protocol completes" 改写为完成态：strict 协议已完成、P-NEW-1 行为主归因证据、321 行按其 boundary 保留；**撤回谱系正文（L76-92）一字不改** |
| CM-E78-U | 不改 claim 与 boundary；仅当 Phase D 在 Results 增加交叉引用时，Paper location 列可追加 §Representation Attribution 的对照引用（数字不动） |

### 3.3 需要删除/收缩的 claim 行

- **无删除**。CM-E78-U / CM-PA-1 / CM-PA-2 / CM-FB 的效用代价行在正分支下全部保留
  （D1 不变式 3；R5 触发器防御）。
- 收缩项：无。granularity-attribution 族名在正分支下**不收缩**（全量证据成立）。
- CM-PL-1/2/3（excluded pilots）状态不变：E4 pilot 落地前有独立准入门禁，
  正分支不自动解除其排除状态。

---

## 4. 模板 Z（零/负分支：H1 失败或 V3≈V2 / 行 6）

### 4.1 需要新增的 claim 行

**Z-NEW-1（预注册零结果行）**

- Claim：`The pre-registered four-condition comparison on all 726 official keys
  produced no significant ASR difference in the H1 direction: V3 versus V2
  paired difference [DELTA-V3V2], exact McNemar p=[P-V3V2], bootstrap 95% CI
  [CI-V3V2], discordant counts [DISC-COUNTS]; all paired statistics including
  non-significant directions are reported in [TABLE-REF]`
- Paper location：Results §Where the Bottleneck Is（D1 R.N.1）
- Authoritative result / code：同 P-NEW-1 的 frozen report 路径（`[PENDING-FINALIZE]`）
- Boundary：`Pre-registered design executed without post-hoc subset search
  (protocol §2.2); the negative result is retained as a contribution
  (protocol §2.3 row 6); no re-weighting or subset restriction applied after
  observing outcomes`

**Z-NEW-2（瓶颈阶梯行）**

- Claim：`Adjacent-condition differences along V0→V1→V2→V3 are [LADDER-V01],
  [LADDER-V12], [LADDER-V23] (each with paired CI [LADDER-CIS]); the
  representation level at which the safety difference appears/disappears is
  [BOTTLENECK-LEVEL]`
- Boundary：`Ladder localizes where a difference does or does not emerge under
  the implemented conditions; absence of a V3-over-V2 gain does not negate the
  finite-domain collision results, which are representation-level facts on
  frozen domains (see collision rows)`

**Z-NEW-3（表示轴/授权轴正交行）**

- Claim：`Under the null V0-V3 outcome, the representation-axis evidence
  (collision rows, finite-domain and held-out validation) and the
  authority-axis evidence (reviewed-authority 26-task row, full-benign
  abstention audit) each stand unchanged; the null result is scoped to
  end-to-end ASR realization of the atom granularity advantage`
- Boundary：`Scope statement, not a new empirical result; cites existing frozen
  rows (collision, finite-domain, held-out, CM-E84, CM-FB)`
- Authoritative result：`Definition-level scoping statement; no new number`（按
  claim map 现有惯例，理论/范围声明可标注 "Definition, not an empirical number"
  式来源——此处类比为"现有行的范围重述"，五列中 Authoritative result 列写明
  所引用的既有行锚点）

### 4.2 需要修改的现有 claim 行

| 锚点 | 修改内容 |
|---|---|
| CM-HDR | `granularity-attribution` → `granularity-characterization (applicability subset)`：**收缩**（零负分支下 granularity 主张只保留在适用性子集上） |
| CM-GL-321 | Boundary 追加：`Remains the sole admissible granularity-attribution evidence form (mechanism witness) under the null V0-V3 outcome`；Claim 数字不改 |
| CM-RETR（L93-95 脚注） | "until the strict 726-key protocol completes" → "the strict 726-key protocol completed with a null outcome (Z-NEW-1); the 321-case row remains the sole admissible granularity-transfer evidence, under its stated selection-conditioned boundary"；撤回谱系正文不改 |
| CM-E78-U | 不改。若 Phase D 在 Results 增设零结果节并交叉引用 E78，仅 Paper location 列可追加 |

### 4.3 需要删除/收缩的 claim 行

- **删除：无**。零/负分支不删除任何既成事实行（负面结果本身入稿）。
- **收缩（措辞层，非数字层）**：
  1. CM-HDR 族名收缩（见 4.2）；
  2. CM-GL-321 的证据地位从"等待全量协议"收缩为"机制 witness 即最终形态"；
  3. Abstract/Introduction 侧的 granularity 相关表述在 Phase D 按 D1 N3 收口
     （"区分工具而非系统"）——但 claim map 中除上述两行外不产生连锁修改。
- CM-PL-1/2/3 状态不变。

---

## 5. 模板 M（混合分支：行 1 / 行 4 / 行 5）

混合分支 = D1 "N2 细分 + N3 局部" 或 "N1 + 机制 witness"。三套行模板按触发的
§2.3 矩阵行选用，可同时启用多行（以判定组合为准）。

### 5.1 需要新增的 claim 行

**M-NEW-1（行 1 触发：已验证字段 + 字段级检查）**

- Claim：`V3 exceeds V0 ([V3-ASR] vs [V0-ASR], p=[P-V3V0]) but does not exceed
  V2 ([V3-ASR] vs [V2-ASR], p=[P-V3V2], CI [CI-V3V2]); field-level checking is
  supported while post-counterfactual atom specificity shows no additional gain
  on this benchmark`
- Boundary：`Conclusion exactly per protocol §2.3 row 1; granularity claim is
  scoped to validated fields plus field-level checking; no atom-specificity
  claim is made`

**M-NEW-2（行 4 触发：保守拒绝披露）**

- Claim：`The V3 ASR reduction of [DELTA-ASR] is accompanied by DENY/ABSTAIN
  rate [V3-DENYABSTAIN] versus [V2-DENYABSTAIN] (V2), execution coverage
  [V3-COVERAGE] versus [V2-COVERAGE]; the gain may be substantially explained
  by conservative refusal`
- Boundary：`Denial/coverage figures are reported alongside ASR, not after it
  (protocol §2.3 row 4); no superior-tradeoff claim is made; this row does not
  modify the E78 frontier description`

**M-NEW-3（行 5 触发：单一 suite/goal 集中 → 机制 witness）**

- Claim：`The V0-V3 safety difference concentrates in [CONCENTRATION-SUITE/GOAL]
  ([K]/4 suites, [M] strata, [G] injection goal(s)); it is reported as a
  mechanism witness, not as a general end-to-end advantage`
- Boundary：`Demotion per protocol §2.3 row 5; the same demotion rule was stated
  before results (defensive writing consistency preamble); no post-hoc rescoping
  in the opposite direction is permitted`

### 5.2 需要修改的现有 claim 行

| 锚点 | 修改内容 |
|---|---|
| CM-HDR | `granularity-attribution` → `validated-field granularity (mixed outcome)`：**收缩**到已验证字段 + 字段级检查 |
| CM-GL-321 | 若行 5 触发：Boundary 追加 `Demoted to mechanism witness per §2.3 row 5; the 321-case row's selection-conditioned status is unchanged`；若仅行 1/4 触发：不改 |
| CM-RETR（L93-95 脚注） | 按实际启用行改写完成态（参照模板 P/Z 的同位置改法，措辞随 M-NEW-1/2/3 收缩） |

### 5.3 需要删除/收缩的 claim 行

- 删除：无。
- 收缩：
  1. granularity 主张收缩到 "validated fields + field-level checking"
     （CM-HDR + M-NEW-1 boundary 联动）；
  2. 行 4 触发时，**禁止**任何新行使用 "tradeoff improvement / competitive
     frontier improvement" 措辞——CM-E78-U 的 "strong tradeoff, not Pareto
     dominance" boundary 成为上限表述；
  3. 与 E2 的联动（D1 §0 混合分支附加动作）：若 E2 表显示混合源于 power-set
     族过强，新增的 E2 claim 行（由 E2 表注流程登记，见
     `defensive_writing_drafts_2026-08-04.md` C.2）与本模板并列，不并入本模板。
- CM-PL-1/2/3 状态不变。

---

## 6. 更新纪律

### 6.1 何时启用哪套（判定链）

1. **协议 §2.3 矩阵**（协议 L37-46，六行）定义观测结果 → 允许结论；
2. **H1-H5 判定**在 v17 finalize 后按协议 §2.1/§2.2 统计规则释放（finalize 当天，
   协议 §11 门禁通过后；D1 §4 规则 1）；
3. **分支选择**按本文档 §2 映射表 → D1 §0 分支表（两表必须一致；不一致时以
   协议 §2.3 原文为准并提请 PM 裁决）；
4. **模板启用**：P / Z / M 三选一（混合时 M 优先），模板内行按触发条件逐行启用。

### 6.2 数字落地前禁止预更新（R1）

- v17 finalizer exit=0 且 726 keys 完整性检查通过之前：**零编辑**。
- V0-V3 四条件全部完成、`finalize.py` 产出 frozen report、H1-H5 判定书面释放之前：
  **零编辑**。
- 禁止以"方向已可见"为由预写方向性词汇（higher/lower/improve）进 claim map——
  方向本身是结果（与 W 骨架 §5.3 规则 3 同一纪律）。
- 本模板文档中的所有 `[占位符]` 只存在于本文档；claim map 中出现任何未落地
  数字即构成 R1 违例，须整行回滚。

### 6.3 更新顺序（B 线，协议 §13 末段 / D1 §4 规则 2）

```
Evaluation protocol（§Representation Attribution 表与统计）
  → Results 正文（D1 N2/N3 骨架对应小节）
  → failure analysis / 附录
  → Abstract / Introduction
  → claim_to_source_map.md（本模板执行点，倒数第二步）
  → reproduction outputs
```

claim map 位于 Abstract 之后：确保登记入真源表的每个数字已在论文正文落地，
禁止"先在 claim map 抢跑、正文后补"的反向顺序。

### 6.4 执行时的 diff 审查清单（逐条勾选）

1. [ ] 每个新增行五列齐全；Authoritative result 指向 frozen 文件路径（非运行中路径）；
2. [ ] 每个新增/修改行的数字与 frozen report 逐字一致（从 report 抄录，不凭记忆）；
3. [ ] Boundary 列包含：选择条件、非外推声明、与该行触发矩阵行的措辞绑定；
4. [ ] CM-HDR Status 头已同步且与实际行集合一致；
5. [ ] CM-PEND 区段仅在有显式触发时改动（如 E4 pilot 准入另行决策），否则不动；
6. [ ] CM-RETR 区段只允许按 §3.2/§4.2/§5.2 的完成态改写，撤回正文一字未动；
7. [ ] 不变式行（§7）未被触碰；
8. [ ] 更新后全文检索 claim map：不存在 `[PENDING`、`[V0V3-`、`[V3-` 等占位残留。

---

## 7. 三分支不变式（任何模板执行后必须仍为真）

以下行在 P/Z/M 三套模板下**均不修改 claim 与 boundary**（仅允许 Paper location
列因正文结构调整而追加）：

| 锚点 | 不变理由 |
|---|---|
| CM-E78-U（L33） | E78 是冻结的 capacity-matched 全系统对照；V0-V3 任何结果不改变 63→33/97（D1 不变式 3） |
| CM-E78-A（L34） | all-key bounds 与 missingness 处理独立于分支 |
| CM-PA-1 / CM-PA-2（L35-36） | pathway audit 是 frozen 日志审计，与 V0-V3 无关；且是 utility 归因叙事的真源（W 骨架段落一） |
| CM-FB（L47） | 50-task gate 失败与 abstention 构成是既成测量，不得因分支而重述 |
| CM-BURDEN（L54） | 接口负担测量独立于分支 |
| CM-PL-1/2/3（L38-40） | excluded 状态由 E4 准入门禁单独管理 |

---

## 8. 与其他窗口期产物的接口

- **D1 骨架**（`d1_results_branch_skeleton_2026-08-04.md`）：Results 结构载体；
  本模板的行变更必须与 D1 对应小节（R.A.1-R.A.6 / R.N.1-R.N.5）同批移植，
  移植即触发本模板 §6.4 审查（D1 §4 规则 5）。
- **W 骨架**（`w_utility_repositioning_skeleton_2026-08-04.md`）：utility 重定位
  叙事不新增 claim map 行（其锚点全部指向 §1.3 既有行）；若 Phase D 决定为其
  新增行，走本模板 §6 纪律。
- **防御性写作草稿 C.1**：V0-V3 一致性 preamble 中承诺的三步审计若产生
  矛盾清单（discordance inventory），该清单作为 P-NEW-1 行 Boundary 的附件引用，
  不另立 claim 行。
