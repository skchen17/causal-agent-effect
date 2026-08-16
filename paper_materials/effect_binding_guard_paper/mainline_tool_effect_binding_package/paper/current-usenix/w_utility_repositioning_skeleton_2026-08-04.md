# W Utility 重定位叙事骨架（数字占位版）

日期：2026-08-04
产出：research-assistant。依据决策书 `window_execution_decision_2026-08-04.md` §2e（W 骨架规格）与 §2f、
审稿人评估 `reviewer_perspective_improvement_evaluation_2026-08-04.md` §2（W 行：可感知性中，
"33/97 原数仍在，重定位可能被读作 spin"）与 §4 攻击点 4。

**硬约束（与决策书 §2e、D1 骨架纪律一致）**：
1. 本文档是独立草稿，**不修改 sections/ 任何文件、不修改 claim_to_source_map.md**；
   入稿在 Phase D 按 B 线顺序（Evaluation→Results→Abstract）由写作负责人移植。
2. 叙事正文（可移植英文句）中的**数字一律占位符**；v17 落地后回填。
   已冻结数字不手写进可移植文本，而是经 §1 占位符映射表指向真源——移植时从真源抄录，
   防止转录漂移；尚未产生的数字（V0-V3、E4）保持占位、禁止预填（R1 overclaim 触发器）。
3. 措辞防 spin：不删除、不弱化 33/97（D1 不变式 3）；归因 ≠ 豁免——pathway audit
   只定位损失来源，不改官方标签、不改 headline；E4 证据不入 headline，
   禁用 "utility problem is solved / resolved"（reviewer_perspective §4.4）。

---

## 1. 占位符约定与数值状态

| 前缀 | 含义 | 回填时机 |
|---|---|---|
| `[V17-*]` | v17 finalizer/freeze 后复锚定的 headline 口径值 | Phase D（v17 落地后） |
| `[V0V3-*]` | V0-V3 主实验结果 | Phase D（finalize + H1-H5 判定后） |
| `[E4-*]` | E4 预注册 pilot 结果 | E4 pilot 落地后（决策书 §3 W4-W5） |
| `[PENDING-FINALIZE]` | 通用待定占位（与 D1 骨架约定一致） | 同上 |

**FROZEN 标记**：占位符映射表中标注 FROZEN 的数字，其值锁定于所列真源文件；
这些数字已存在于当前论文（results.tex / additional_results.tex / limitations.tex / abstract.tex），
移植时逐字取自真源，不允许凭记忆重录。标注 PENDING 的数字在产生前任何文本不得填入。

与分支的关系：本骨架服务 N1 基座（无论 V0-V3 正负都成立）；§6 给出 N2/N3/混合分支下的
叠加与收缩规则。混合/正分支下与 V0-V3 效用数字的一致性检查使用 `[V0V3-*]` 占位。

---

## 2. 段落一：归因式辩护段（Attribution Defense）

**移植位置**：`sections/results.tex` §Common-Checkpoint AgentDojo Comparison
（L147-153 现有 pathway audit 段的扩展重写位）；解剖细节保持在
`appendix/additional_results.tex` L45-59 "Headline benign-utility pathway audit" 段。

### 2.1 主题句（英文草稿，可移植）

> A deterministic pathway audit decomposes the benign-utility losses by observed
> runtime pathway. Of [PA-LOSSES] no-defense-success/guard-failure transitions,
> [PA-FEEDBACK-LOSSES] contain explicit runtime replan feedback, and the losses
> concentrate in three named interfaces—initial-plan construction, field
> binding/evidence admission, and resolver value recovery—rather than being
> distributed as a uniform cost of effect decomposition. We read this as an
> attribution to the current implementation interfaces, not as a demonstration
> that the loss is avoidable; the audit is post-hoc, and the official utility
> labels are unchanged.

### 2.2 论证链（bullet）

1. **损失总量与方向**：97 个 capacity-matched benign 配对中，no-defense 成功→guard 失败
   的转移共 [PA-LOSSES] 例（反向转移 [PA-GAINS] 例）；headline 净值 63/97→33/97。
2. **feedback 分层是归因的第一级**：[PA-FEEDBACK-LOSSES]/[PA-LOSSES] 的损失含显式
   runtime replan feedback；含 feedback 的 [PA-FB-TASKS] 个任务成功数 35→4（净 −31），
   不含 feedback 的 [PA-NOFB-TASKS] 个任务 28→29（净 +1）——损失几乎全部集中于
   feedback 层，说明损失经由可命名的运行路径发生，而非均匀分布在所有任务上。
3. **层内构成是归因的第二级**（三类接口，类别在 [PA-OVERLAP] 例上重叠）：
   - plan 接口：[PA-PLAN]/[PA-FEEDBACK-LOSSES] 含 initial-plan 构造/覆盖发现
     （非互斥理由计数：`task_permission_plan_parse_failed` = [PA-PARSE]、
     `tool_not_in_initial_permission_plan` = [PA-NOTTOOL]）；
   - binding/evidence 接口：[PA-BINDING]/[PA-FEEDBACK-LOSSES] 含 field-binding 或
     evidence 发现（`forbidden_field_used` = [PA-FORBID]、
     `outside_exact_plan` = [PA-OUTPLAN]）；
   - resolver 接口：[PA-RESOLVER-REPLAN] 例 `resolver_fill_requires_replan`；
     [PA-PROBE-CHECKS] 个被拒 resolver-field 检查中 [PA-LITERAL-VALUES] 个值字面出现于
     更早的 benign 工具结果，跨 [PA-LITERAL-CASES] 个损失 case——被拒的值并非"不存在"，
     而是恢复/信任接口未能在证据已在场时接纳它。
4. **接口缺陷清单**（由 2/3 直接汇总，每条对应一个可修接口而非方法本身）：
   - D-plan：任务权限计划解析失败与工具不在初始计划内 → plan 构造/覆盖接口缺陷；
   - D-bind：字段绑定与证据接纳规则把已在场证据挡在授权之外 → evidence 接口缺陷；
   - D-resolver：具体运行值无法被已批准的 resolver 证成 → trusted-evidence
     恢复接口缺陷（与 abstain root-cause 的机制解释一致，见段落三）；
   - D-manifest：[FB-MANIFEST]/[FB-ABSTAIN] 个 abstention 无 authority manifest
     → O2/interface-coverage 缺陷（接口面未覆盖，非拒绝过严）。
5. **修复路线图方向**（只写方向与衔接，不承诺数字）：上述四类缺陷即 E4 预注册 pilot
   的设计目标域——registered relation/projection 的按需接入（evidence 侧）与
   manifest 覆盖扩展（authority 侧）。衔接纪律：E4 设计稿先行（决策书 §3 W4，
   "E4 设计先行，守住'禁止事后加 parser'"）；本段不得引用任何未经预注册的恢复实验
   （claim map "Pending Claims Excluded From The PDF" 中 pilot 谱系行的排除理由不变）。
6. **post-hoc 免责声明（逐字保留，不得弱化）**：no-guard 与 guarded 轨迹是独立的
   随机运行，层间差异不是随机化因果效应；literal presence 只是诊断，不证明语义关联、
   可信性或授权；官方 utility 标签未被改变。

### 2.3 占位符位置与映射

| 占位符 | 数值状态 | 真源（移植时逐字抄录） |
|---|---|---|
| `[PA-LOSSES]` / `[PA-GAINS]` | FROZEN | `experiments/security-analysis-ablation-and-overhead/results/headline-benign-utility-pathway-audit/headline-benign-utility-pathway-audit.md` §Paired Decomposition（37 / 7）；`appendix/additional_results.tex` L47-48 |
| `[PA-FEEDBACK-LOSSES]` | FROZEN | 同上 §Paired Decomposition（32/37）；claim map L35 行 |
| `[PA-FB-TASKS]` / `[PA-NOFB-TASKS]` | FROZEN | 同上（47 / 50；成功 35→4、28→29）；`results.tex` L148-149 |
| `[PA-PLAN]` / `[PA-BINDING]` / `[PA-OVERLAP]` | FROZEN | 同上 §Runtime-Feedback Loss Anatomy（16/32、22/32、重叠 6）；claim map L36 行；`appendix/additional_results.tex` L51-54 |
| `[PA-PARSE]` / `[PA-NOTTOOL]` / `[PA-FORBID]` / `[PA-OUTPLAN]` / `[PA-RESOLVER-REPLAN]` | FROZEN | 同上非互斥理由计数（6 / 10 / 5 / 7 / 17） |
| `[PA-PROBE-CHECKS]` / `[PA-LITERAL-VALUES]` / `[PA-LITERAL-CASES]` | FROZEN | 同上（85 / 38 / 12）；`appendix/additional_results.tex` L54-56 |
| `[E4-DESIGN-STATUS]` | PENDING | E4 预注册设计稿（决策书 §3 W4 产出，当前未产生；产生前本句只允许"设计目标域"级表述） |

### 2.4 数据来源引用

- 真源 JSON：`experiments/security-analysis-ablation-and-overhead/results/headline-benign-utility-pathway-audit/headline-benign-utility-pathway-audit.json`；
  摘要 md：同目录 `headline-benign-utility-pathway-audit.md`（其 Claim Boundary 段即免责声明底本）。
- 生成代码/测试：`source/headline-benign-utility-pathway-audit/run_audit.py`、
  `test_headline_benign_utility_pathway_audit.py`（claim map L35-36 行已登记）。
- 论文现址：`sections/results.tex` L147-153；`appendix/additional_results.tex` L45-59；
  `sections/limitations.tex` L21-23（post-hoc 与 literal-presence 边界句）。
- claim map 对应行：L35（32/37、feedback 分层）、L36（16/32、22/32、12 例）、L37（机制 probe）。

### 2.5 禁止措辞（防 spin 自查）

- 禁："the utility loss is an artifact / not real"；"utility is solved by the repair roadmap"；
  "the losses would disappear after fixes"（均为未经实验的承诺）。
- 允许："concentrate in / are attributable to named interfaces"、"post-hoc pathway audit"、
  "does not establish that the loss is avoidable"。

---

## 3. 段落二：前沿定位段（Frontier Positioning）

**移植位置**：`sections/results.tex` §Common-Checkpoint AgentDojo Comparison
L138-145 现有 utility/baseline 段的重写位（保持段内顺序：先代价、后前沿、再 disclaimer）。

### 3.1 主题句（英文草稿，可移植）

> Read on the joint security–utility plane, the result is a point on the
> competitive frontier, not a dominance statement. Each comparison system
> occupies a different region: [BL-PA] reaches lower attack success than \sys{}
> at lower benign and attack-side utility; [BL-PS] retains substantially more
> utility at higher attack success; [BL-MELON] and [BL-SPOT] retain utility near
> the no-defense level without materially reducing attack success. \sys{} is
> neither dominated by nor dominating any of these points; we report positions,
> not superiority.

### 3.2 论证链（bullet）

1. **平面定义先行**：比较平面 = (ASR, benign utility, attack-side utility)，
   外加披露维度（不可评估行保留、all-key bounds、abstention 构成）。先给平面再给位置，
   避免"单维更好"式读法。
2. **逐点不可比性**（每对至少一轴我方程更差、至少一轴我方更好，故无 Pareto 支配关系）：
   - vs [BL-PA]：对方 ASR [V17-PA-ASR]（分母 629）低于我方 [V17-E78-ASR]，
     但 BU [V17-PA-BU] 低于我方 [V17-E78-BU]、UA [V17-PA-UA] 低于我方 [V17-E78-UA]
     → 安全更高、效用更低的区域；
   - vs [BL-PS]：对方 BU [V17-PS-BU] 高于我方，但 ASR [V17-PS-ASR]（8/627）高于我方
     → 效用更高、安全更弱的区域；
   - vs [BL-MELON]/[BL-SPOT]：效用接近 no-defense，ASR 与 no-defense 同量级
     → 效用保留但安全无实质增益的区域。
3. **措辞规则（任务硬要求）**：全文使用 "position / region / tradeoff / not dominated"，
   禁用 "better than / outperforms / superior"；结论句固定为
   "competitive security–utility tradeoff, not Pareto dominance"
   （与 `results.tex` L143-144 现文及 claim map L33 行 Boundary 完全一致）。
4. **分母与口径披露随段给出**：ASR 分母 627（No defense/MELON/Sandwiching/Spotlighting）
   vs 629（PromptArmor/\sys{}）；MELON BU 用 96 行、其余 97 行；九个不可评估 baseline
   行保留不折算（`tables/table_e78_qwen32_baselines.tex` caption L4）。
5. **adapter disclaimer 逐字保留**：adapter 行是 common-input 本地实现，不是原论文复现
   （`results.tex` L144-145）。

### 3.3 占位符位置与映射

| 占位符 | 数值状态 | 真源 |
|---|---|---|
| `[V17-E78-ASR]` / `[V17-E78-BU]` / `[V17-E78-UA]` | FROZEN | `tables/table_e78_qwen32_baselines.tex` L15（.005 / .340 / .329）；`analysis/results/e78_capacity_matched_statistics.json`（claim map L33 行） |
| `[V17-PA-ASR]` / `[V17-PA-BU]` / `[V17-PA-UA]` | FROZEN | 同上 L13（.002 / .278 / .219） |
| `[V17-PS-ASR]` / `[V17-PS-BU]` / `[V17-PS-UA]` | FROZEN | 同上 L12（.013 / .629 / .581） |
| `[V17-ND-*]` | FROZEN | 同上 L10（no defense：.086 / .649 / .550） |
| `[BL-PA]` / `[BL-PS]` / `[BL-MELON]` / `[BL-SPOT]` | 引用占位 | 见 §3.5 引用警示 |

### 3.4 数据来源引用

- 主表：`paper/current-usenix/tables/table_e78_qwen32_baselines.tex`（L4 caption、L9-16 行值）。
- 统计真源：`analysis/results/e78_capacity_matched_statistics.json`、
  `analysis/results/e78_capacity_matched_comparison.json`（claim map L32-34 行）；
  配对 ASR 差 −0.083、row-bootstrap CI [−0.105,−0.061]、user-task-cluster CI [−0.107,−0.060]
  （claim map L33 Boundary 列）。
- 论文现址：`sections/results.tex` L138-145。

### 3.5 引用警示（移植前置检查）

- 现状核验（2026-08-04）：`references.bib`（33 条目）与 `main.bbl` 中**均未检索到**
  PromptArmor / Prompt Sandwiching / MELON / Spotlighting 的文献条目；正文与表 caption
  仅以方法名 + adapter 行形式提及。**移植本段前必须补齐四个 baseline 的 bib 条目与
  引用键**；在补齐前只能保留"adapter rows … not original-paper reproductions"的现有表述。
  本骨架不虚构引用键。

---

## 4. 段落三：覆盖归一化段（Coverage Normalization）

**移植位置**：`sections/results.tex` §Authority, Mechanism, and Cost Diagnostics
（L183-188 现有 26-task/abstention 叙述的扩展位）；根因细节保持在
`appendix/additional_results.tex` 与 `full-benign-abstain-root-cause.md`。

### 4.1 主题句（英文草稿，可移植）

> The full-benign utility figure mixes security behavior with authority-interface
> coverage, and the two are separable in the audit data. Of [FB-CHECKS] pre-commit
> checks, [FB-ABSTAIN] are abstentions; [FB-MANIFEST] abstentions lack an authority
> manifest and [FB-RESOLVER] lack resolver proof. On the 26 tasks whose manifests
> do compile, the same guard changes attack success from [E84-ASR-0] to [E84-ASR-1]
> and benign utility from [E84-BU-0] to [E84-BU-1]: the compiled subset is a
> measurable proxy for authority-interface quality, not a random sample, and the
> full-set gate failure is reported unchanged.

### 4.2 论证链（bullet）

1. **全量可分解**：97 个 benign 任务、[FB-CHECKS] 次 pre-commit 检查中，
   ALLOW [FB-ALLOW] / ABSTAIN [FB-ABSTAIN] / DENY [FB-DENY]；
   abstention 根因：[FB-MANIFEST] 缺 manifest、[FB-RESOLVER] 缺 resolver proof、
   [FB-OEA] outside exact authority、[FB-TOOB] 工具在 bounded plan 之外。
   主导项（缺 manifest）被根因审计的机制解释定位为
   "O2/interface-coverage limitation"（接口未覆盖→ fail closed），
   而非安全拒绝过严——这是"覆盖归一化"的第一层含义：
   全量 utility 数字 = 安全行为 + 接口覆盖缺口，两者可分。
2. **26-task 编译子集 = 接口质量的可测代理**：44/97 manifest 通过审阅、26 个编译进
   runtime（claim map L54 行）；在该子集上同一 reviewed authority 把 ASR 从
   [E84-ASR-0] 降到 [E84-ASR-1]，BU 从 [E84-BU-0] 到 [E84-BU-1]（攻击差非显著），
   attack utility 从 [E84-UA-0] 到 [E84-UA-1]。子集的选择条件是"接口完整"，
   因此它是 authority 接口质量的代理测量，**不是基准效用的无偏估计**——
   该限定句必须随数字同段出现。
3. **子集内损失的性质披露**：七个 reviewed-authority benign label discordance
   全部为只读调用、无一含 runtime denial/abstention；visible-answer 敏感性把净差从
   [DISC-GAP-0] 缩到 [DISC-GAP-1]（claim map L44 行；appendix L30-43）——
   即子集内的 utility 差不是"拒绝计数"，防止读者把 [E84-BU-0]→[E84-BU-1] 读作假拒绝成本。
4. **refinement 的效用价值（同切片证据）**：E81 将已验证 registry 换成未精炼
   schema-description 划分后 attack utility 从 [E81-UA-1] 降到 [E81-UA-0]
   （配对 bootstrap CI [E81-CI]）——在接口完整的切片上，refinement 与效用正相关
   （claim map L48 行；results.tex L188-191）。
5. **披露结构不豁免门槛**：全量运行**仍然失败于预声明的 50-task utility gate**
   （claim map L47 Boundary）；107/152 与 43 的披露是归一化的输入，不是对门槛失败的
   辩解。limitations 既有句（L13-14）保留。

### 4.3 占位符位置与映射

| 占位符 | 数值状态 | 真源 |
|---|---|---|
| `[FB-CHECKS]` / `[FB-ALLOW]` / `[FB-ABSTAIN]` / `[FB-DENY]` | FROZEN | `experiments/human-authority-and-causal-validation/results/full-benign-runtime-guard-validation/full-benign-abstain-root-cause.json`（`decision_counts`：426 / 270 / 152 / 4；`precommit_checks`=426） |
| `[FB-MANIFEST]` / `[FB-RESOLVER]` / `[FB-OEA]` / `[FB-TOOB]` | FROZEN | 同上 `check_category_counts`（107 / 43 / 4 / 2）；claim map L47 行；`results.tex` L187-188；`limitations.tex` L13-14 |
| `[E84-ASR-0]` / `[E84-ASR-1]` / `[E84-BU-0]` / `[E84-BU-1]` / `[E84-UA-0]` / `[E84-UA-1]` | FROZEN | `experiments/security-analysis-ablation-and-overhead/results/runtime-mechanism-ablation/e84-qwen32-reviewed-authority-strong-baselines-full-results.json`（claim map L42 行；`results.tex` L183-186：5/169→1/169、20/26→15/26、121/169→124/169） |
| `[DISC-GAP-0]` / `[DISC-GAP-1]` | FROZEN | `experiments/security-analysis-ablation-and-overhead/results/benign-utility-causal-audit/benign-utility-causal-audit.json`（claim map L44 行；appendix L36-40：5→3） |
| `[E81-UA-1]` / `[E81-UA-0]` / `[E81-CI]` | FROZEN | `experiments/security-analysis-ablation-and-overhead/results/runtime-mechanism-ablation/e81-qwen32-runtime-ablation-full-results.json`（claim map L48 行：124/169→107/169、CI [−0.154,−0.053]） |
| `[FB-44]` / `[FB-26]`（44/97、26/97） | FROZEN | claim map L54 行；`experimental_setup.tex` L44-46 |

### 4.4 数据来源引用

- abstention 根因：`full-benign-abstain-root-cause.json` / `.md`（`mechanism_interpretation`
  字段给出逐类别机制解释，本段论证链 bullet 1 的定位即取自该字段）；
  主报告：同目录 `full-benign-report.json` / `.md`。
- 26-task：E84 结果 JSON（上表）+ `tables/table_e84_reviewed_authority.tex`。
- 生成代码/测试：full-benign finalizer 与 abstain root-cause analyzer、E84 runner/finalizer
  （claim map L42/L47/L54 行 Generating code/test 列）。
- 论文现址：`sections/results.tex` L183-198；`appendix/additional_results.tex` L12-43；
  `sections/limitations.tex` L13-14。

---

## 5. 段落四：诚实收尾句（Abstract 末句的保持与强化）

**现状**（`sections/abstract.tex` L31-33，逐字引用）：
> "The results support effect-level mediation, but contract coverage and utility
> remain barriers to deployment."

### 5.1 处理决定

- **保持**："remain barriers to deployment" 的自认结构保留——它是防 spin 的锚点，
  任何重定位都不允许把它弱化成 "are being addressed"。
- **强化方向**（Phase D 可选移植，二选一或不用）：在自认句内嵌入归因指针，
  使读者从 Abstract 即可看到"障碍已被定位、修复被预注册"，而不声称障碍已消除。

### 5.2 候选改写（英文草稿，占位版）

**候选 A（最小改动，推荐默认）**：保持原句，仅在其后追加归因指针从句：

> The results support effect-level mediation, but contract coverage and utility
> remain barriers to deployment; a post-hoc pathway audit locates the observed
> utility losses in named plan, evidence, and resolver interfaces, which we treat
> as targets of pre-registered follow-up rather than as removed costs.

**候选 B（仅当 V0-V3 正分支成立且 H2/H3 通过时可用，需与 §6 一致性检查同时满足）**：

> The results support effect-level mediation, but contract coverage and utility
> remain barriers to deployment: on [V0V3-KEYS] keys the representation-level
> comparison yields [V0V3-BU-DIRECTION] benign utility under lower attack success
> [V0V3-ASR-SUMMARY], while the interface-coverage abstentions identified by the
> audit remain open engineering work.

### 5.3 规则

1. E4 的任何数字**不得**进入 Abstract（E4 定位为归因证据 + 外推边界句，
   reviewer_perspective §4.4；其 pilot 证据在 claim map 中仍属
   "excluded from the current PDF" 谱系，L38-40 行的排除状态不因本骨架改变）。
2. 候选 B 的启用条件写死在此：H2∧H3 非劣通过（协议 §2.1/§2.3 行 3）；
   若走混合/零负分支，Abstract 只用候选 A 或原句。
3. 占位符：`[V0V3-KEYS]`、`[V0V3-BU-DIRECTION]`、`[V0V3-ASR-SUMMARY]` 均为 PENDING，
   finalize 前禁止以任何形式填入（含方向性词汇如 "higher"——方向本身也是结果）。

### 5.4 数据来源引用

- 现句真源：`sections/abstract.tex` L31-33。
- 候选 A 的归因从句锚定段落一真源（§2.4 所列）；候选 B 锚定
  `strict_atom_representation_attribution_protocol_2026-08-03.md` §2.1 H2/H3 与
  §2.3 行 3 的允许结论措辞。

---

## 6. 与 V0-V3 分支（N1/N2/N3）的叠加规则

| 分支（D1 §0） | W 骨架处置 |
|---|---|
| N1 基座（现状） | §2-§5 全部可用，占位符只取 FROZEN 值 |
| N2 全量（正，行 3） | §2-§4 保留；§5 可启用候选 B（H2∧H3 通过为前提）；新增一致性要求：段落三的 [E84-BU-*] 与 V0-V3 benign utility 方向若矛盾，按 defensive_writing_drafts C.1 的裁决规则处理（收缩主张，禁止事后调和分母），一致性句占位 `[V0V3-CONSISTENCY-NOTE]` |
| N2 变体（行 2，ASR 同、效用更高） | §2 归因段保留；段落二前沿定位不变；§5 只用候选 A |
| 混合（行 1/4/5） | §2-§4 保留但禁一切 trade-off 优势措辞；§5 只用候选 A 或原句 |
| N3 全量（零/负，行 6） | §2 归因段成为 "where the cost is" 叙事的组成部分（与 D1 R.N.2 瓶颈定位并列呈现）；§3 前沿定位保留（负结果不改变 E78 前沿位置）；§5 保持原句 |

---

## 7. 防 spin 自查清单（移植前逐项勾选）

1. [ ] 33/97（及其分母 97、配对口径）在 Results 与 Abstract 中原样存在，未被移走或改写；
2. [ ] 段落一保留逐字 post-hoc 免责声明（独立随机运行、非因果、官方标签不变）；
3. [ ] 段落二无 "better than / outperforms / superior / dominates" 字样；
4. [ ] 段落三明写 "fails the predeclared 50-task utility gate"（或其等价引用）；
5. [ ] 段落四未出现 E4 数字；无 "utility problem is solved/resolved"；
6. [ ] 所有 PENDING 占位符仍为占位符（无预填数字、无预填方向）；
7. [ ] 所有 FROZEN 值与 §2.3/§3.3/§4.3 映射表所列真源逐字一致；
8. [ ] baseline 引用已补齐（§3.5）或保留 adapter-only 表述。

---

## 附：与真源表的登记关系（不预更新声明）

本骨架涉及的新叙事（归因式辩护、前沿平面定位、覆盖归一化）**不新增任何 claim map 行**；
其全部数字锚点均指向 claim map 已登记行（L33/L35/L36/L37/L42/L44/L47/L48/L54）。
若 Phase D 移植时写作负责人认为需要新增或修改 claim map 行，按
`claim_map_branch_templates_2026-08-04.md` 的分支模板与更新纪律执行，
本文档不替代该流程。
