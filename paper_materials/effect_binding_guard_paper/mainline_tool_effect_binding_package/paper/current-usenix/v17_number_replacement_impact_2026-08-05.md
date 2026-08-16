# v17 数字替换影响评估（E78 headline 口径）

日期：2026-08-05
产出：research-assistant（W2 交付，任务 B）。
输入：
- E78 现用数字（已入稿，frozen）：ASR 2/627（配对）、3/629（全 key）、BU 33/97、UA 207/627；
- v17 实测参考（**未冻结**）：ASR 11/629、BU 46/97、attack utility 273/629；
- 冻结状态证据：`v17_finalizer_watch.log`（2026-08-04 02:21 finalizer exit=1，`command_protocol_clean=false`，"finalizer failed; not freezing"）。

**红线声明（全文有效）**：
1. v17 数字在本文档中仅作**影响评估**引用，一律标注"参考值/未冻结"；在 finalize 门禁（协议 §11）通过前，**禁止**写入任何 LaTeX 正文、表、abstract、claim map。
2. 本文档不修改任何现有文件；所有替换句一律使用 `[V17-*]` 占位符（与 W 骨架 §1 占位符约定一致）。
3. 数字回填顺序仍按 B 线：Evaluation protocol → Results 表 → failure analysis → Abstract/Introduction → claim-to-source map（D1 骨架 §4 规则 2）。

---

## 0. 结论先行

1. **方向摘要**：v17 相对 E78 现用口径呈"效用回升 + 安全小幅回退"形态：BU 33→46（+13 任务，+13.4pp），UA 207→273（+66 任务，+10.4pp），ASR 2/627→11/629（0.32%→1.75%，+9 例成功攻击）。这与 recovery/override 策略（`allow_with_trail` + planner replan）的权衡预期一致。
2. **安全主张仍然成立但量级收缩**：相对 no-defense 8.61%（54/627），v17 的 1.75% 仍是约 79.7% 的相对降幅（此前口径为 96.3%）；"missingness 不能反转结论"的论证仍成立（11 < 54）。
3. **最大叙事风险（新发现，必须上报）**：v17 口径下 Prompt Sandwiching（ASR 8/627=1.27%、BU .629、UA .581）在三条 headline 轴上**同时优于** \sys{}（1.75% / .474 / .434）。现文"competitive security–utility tradeoff, not Pareto dominance"的说法在 headline 三轴上不再成立，除非（i）配对共评估口径统计给出不同方向，或（ii）把比较平面扩到披露轴（不可评估行、abstention 构成、override trail）。**这是替换前必须解决的头号问题**。
4. **utility gate 仍失败**：46/97 = 46 任务 < 预声明 50-task gate（claim map L47），效用改善不改变门槛失败状态；W 骨架防 spin 句（"full-set gate failure is reported unchanged"）继续适用。
5. **前置条件**：finalizer 门禁当前失败（`command_protocol_clean=false`），在修复并通过全部 gate 之前，本评估中的所有替换均为"预案"，不得执行。

---

## 1. 数字对比与派生指标

| 指标 | E78 现用（frozen） | v17 参考（未冻结） | 变化 | 备注 |
|---|---|---|---|---|
| ASR（配对共评估） | 2/627 = 0.32% | [V17-PAIR-SUCC-SYS]/627 未知 | — | v17 参考只给了全 key 口径；配对值待 finalize 统计 |
| ASR（全 key） | 3/629 = 0.48% | 11/629 = 1.75% | +8 例，+1.27pp | 分母同为 629，可比 |
| no-defense ASR | 54/627 = 8.61%（全 key 界 54/629–56/629） | 不变 | — | baseline 侧不受 v17 影响 |
| 相对 no-defense 的降幅 | 96.3%（相对）/ −8.29pp | 79.7%（相对）/ −6.86pp | 收缩 16.6pp（相对口径） | 按全 key rate 计算 |
| BU | 33/97 = 34.0% | 46/97 = 47.4% | +13 任务，+13.4pp | no-defense 63/97=64.9%；仍低 17 任务 |
| 守卫引入的 BU 损失回收率 | — | 13/30 = 43.3% | — | 63→33 损失 30，33→46 回收 13 |
| UA | 207/627 = 33.0%（正文）/ .329（表，按 629 口径） | 273/629 = 43.4% | +66 任务，+10.4pp | 注意现文存在 627/629 双分母表述（见 §2.3 分母纪律） |
| 守卫引入的 UA 损失回收率 | — | 66/138 = 47.8% | — | 345→207 损失 138；ND 基数 345 按 627 分母，跨分母比较需标注 |
| 50-task utility gate | 失败（33 < 50） | 仍失败（46 < 50） | 不变 | claim map L47 Boundary |

派生计算说明：相对降幅 = 1 − (ASR_sys / ASR_nd)，rate 口径（11/629)/(54/627)=0.2031 → 79.7%；(2/627)/(54/627)=0.0370 → 96.3%。所有派生值在 finalize 后以冻结统计脚本输出为准，本文数字仅用于量级评估。

---

## 2. 需要改动的正文位置清单

记号：`现状句`（逐字引自现有文件）→ `替换句`（占位符版）→ `叙事调整建议`。

### 2.1 Abstract（sections/abstract.tex L26-28）

**现状句**：
> "Under a capacity-matched Qwen3-32B comparison, the guard reduces AgentDojo attack success from 54/627 to 2/627 on jointly evaluable keys, while benign utility falls from 63/97 to 33/97."

**替换句**：
> "Under a capacity-matched Qwen3-32B comparison, the guard reduces AgentDojo attack success from 54/627 to [V17-PAIR-SUCC-SYS]/[V17-PAIR-N] on jointly evaluable keys ([V17-ASR-ALLKEY]/629 across all evaluable guard keys), while benign utility falls from 63/97 to [V17-BU]/97."

**叙事调整建议**：
- 保持"falls"框架：63→46 仍是下降，abstract 不得把 recovery 写成收益（防 spin，W 骨架硬约束 3）。与旧版冻结构建（33/97）的对比只在 Results 出现，不进 abstract。
- 末句 "contract coverage and utility remain barriers to deployment" 原样保留（46/97 仍支持该自认）。
- 同段 L28-29 "On 303 fixed saved AgentLAB attacks, success falls from 95 to zero"：**连带风险项**——v17 改变 override/recovery 策略后，AgentLAB 保存-转移实验（含 1,439 executed calls 匹配、87/303 user tasks）可能需要重跑；在重跑裁决前该句标注 `[RECHECK-V17-AGENTLAB]`，不得默认保留。

### 2.2 Introduction（sections/introduction.tex L82-85）【任务清单外新增，必须同步】

**现状句**：
> "the runtime reduces official AgentDojo attack success from 54/627 to 2/627 on jointly evaluable keys, but benign utility falls from 63/97 to 33/97."

**替换句**：与 abstract 同构（同占位符）。

**叙事调整建议**：L90-91 "These sandboxes consistently show lower attack success, but utility and the authority interface remain unsolved." 保留（v17 下仍真：1.75% < 8.61%，utility 未解决）。

### 2.3 Results E78 主表段（sections/results.tex §Common-Checkpoint，L127-136）

**现状句 A**（L130-133）：
> "On the 627 attack keys evaluable for both no defense and \sys{}, attack success changes from 54 to 2, a difference of $-0.083$ (paired bootstrap 95\% CI $[-0.105,-0.061]$; Holm-adjusted exact McNemar $p=7.3\times10^{-14}$)."

**替换句 A**：
> "On the [V17-PAIR-N] attack keys evaluable for both no defense and \sys{}, attack success changes from [V17-PAIR-SUCC-ND] to [V17-PAIR-SUCC-SYS], a difference of [V17-DIFF] (paired bootstrap 95\% CI [V17-CI-ROW]; Holm-adjusted exact McNemar $p=$[V17-P-MCNEMAR])."

**现状句 B**（L133-134）：
> "A user-task-cluster bootstrap gives $[-0.107,-0.060]$."

**替换句 B**：
> "A user-task-cluster bootstrap gives [V17-CI-CLUSTER]."

**现状句 C**（L134-136）：
> "Across all 629 evaluable \sys{} keys, attack success is 3/629; the no-defense all-key interval is 54/629--56/629, so missingness cannot reverse the conclusion."

**替换句 C**：
> "Across all 629 evaluable \sys{} keys, attack success is [V17-ASR-ALLKEY]/629; the no-defense all-key interval is 54/629--56/629, so missingness cannot reverse the conclusion."

**叙事调整建议**：
- 全部配对统计量（差值、双 CI、p）必须由 `analyze_e78_capacity_matched_statistics.py` 在 v17 artifact 上重算，禁止手填；预期方向：差值仍显著为负（1.75% vs 8.61%），但幅度收缩（约 −0.069 vs 现 −0.083，以脚本输出为准）。
- **分母纪律（现文既有问题，替换时一并修复）**：现文正文 UA 写 207/627，而表 caption 声明 \sys{} 攻击分母为 629（表值 .329=207/629）。替换时统一规则：正文同时给出"配对共评估口径 + 全 key 口径"两处数字并写明分母，不允许单一分母混用。
- missingness 论证保留，但语气校准：11 与 54 的距离仍大，论证结构不变。

### 2.4 Results utility/frontier 段（L138-145）——含最高风险改动

**现状句 A**（L138-139）：
> "The reduction is not free. On matched keys, benign utility changes from 63/97 to 33/97 and attack-side utility from 345/627 to 207/627."

**替换句 A**：
> "The reduction is not free. On matched keys, benign utility changes from 63/97 to [V17-BU]/97 and attack-side utility from 345/627 to [V17-UA]/[V17-UA-DENOM]."

**现状句 B**（L139-142）：
> "PromptArmor-style attains 1/629 attack success but lower utility than \sys{}; Prompt Sandwiching retains substantially more utility at 8/627 attacks."

**替换句 B**（v17 口径下 Sandwiching 的 ASR 1.27% 低于 \sys{} 1.75%，原句的对比逻辑反转）：
> "PromptArmor-style attains 1/629 attack success but lower utility than \sys{}; Prompt Sandwiching retains substantially more utility at 8/627 attacks, an attack rate [V17-COMPARE-DIRECTION: lower than / comparable to] the \sys{} rate under the finalized counts."

**现状句 C**（L142-145）：
> "MELON-style and Spotlighting retain utility near no defense but do not materially reduce attack success. Thus the result establishes a competitive security--utility tradeoff, not Pareto dominance."

**替换句 C**：
> "MELON-style and Spotlighting retain utility near no defense but do not materially reduce attack success. [V17-FRONTIER-SENTENCE: 依 §3.4 裁决结果三选一]."

**叙事调整建议**：见 §3.4（Pareto 风险裁决）。"The reduction is not free" 段首句保留——v17 下效用仍低于 no-defense，该句仍真；但段内应增加一句 recovery 来源披露（override/recovery 策略是效用回升的机制，数字占位 `[V17-OVERRIDE-COUNT]`，与 O6 披露段联动）。

### 2.5 Results pathway audit 段（L147-153）——全部数字需重算

**现状句**：
> "A deterministic pathway audit finds runtime replan feedback in 32/37 benign losses. The 47 feedback-bearing tasks change from 35 to four successes; the other 50 change from 28 to 29. Initial-plan findings occur in 16/32 direct losses, binding/evidence findings in 22/32, and 12 loss cases reject a resolver value already present in an earlier benign tool result."

**替换句**：全段数字占位 `[PA-*]`（W 骨架 §2 段落一的占位符族），并在 v17 冻结日志上**重跑** `run_audit.py`：
> "A deterministic pathway audit finds runtime replan feedback in [PA-FEEDBACK-LOSSES]/[PA-LOSSES] benign-loss transitions ... [PENDING-V17-RECOMPUTE]."

**叙事调整建议**：
- v17 的 BU 从 33 升到 46，意味着损失-转移结构（37 losses / 7 gains）必然改变，且出现**净回收**（+13 任务）：现有审计脚本按"损失分解"设计，需评估是否对称增加"回收分解"（哪些接口贡献了 +13）。若新增，该分解必须在写入前预注册口径（防事后归因，D1 规则）。
- post-hoc 免责声明逐字保留（独立随机运行、非因果、官方标签不变）。
- claim map L35/L36 两行随重算结果做 diff。

### 2.6 Results 321-case 段（L159-165）——重跑裁决项

**现状句**：
> "the whole-call view permits 3/273 attack goals versus none for atom fields; benign utility is identical and attack-side utility is 49/273 versus 57/273."

**处置选项（二选一，PM 决策）**：
- 选项 1（推荐）：在 v17 runtime 上重跑 321-case 归因 → 数字全部占位 `[V17-321-*]`；理由：v17 改变了 recovery/override 策略，而该实验"holding ... recovery ... fixed"的前提已失效，沿用旧数字会构成 runtime 版本错配。
- 选项 2：保留冻结工件数字，但随段披露 runtime 版本（"measured on the pre-recovery runtime; the v17 recovery policy is not applied in this attribution"）；代价：审稿人可攻击"归因结论是否随 recovery 变化"。
- 连带项：Panel (b) AgentLAB（95→0、180→87、1,439）与 bounded adaptive（4/40→1/40，L176-179）同属 v17 runtime 依赖项，裁决规则相同，占位 `[RECHECK-V17-AGENTLAB]` / `[RECHECK-V17-ADAPTIVE]`。

### 2.7 tables/table_e78_qwen32_baselines.tex（L15 \sys{} 行）

**现状**：`\sys{} & .340 & .329 & .005 \\`
**替换**：`\sys{} & [V17-BU] & [V17-UA] & [V17-ASR] \\`（参考值 .474 / .434 / .017，finalize 前禁止写入）。
**叙事调整**：caption 的分母声明（627 vs 629、MELON BU 96 行）若 v17 改变分母需同步修订；"Nine non-evaluable baseline rows" 属 baseline 侧，预计不变，finalize 核对。

### 2.8 Conclusion（sections/conclusion.tex）

**现状句**（L15-18）：
> "At runtime, effect mediation sharply reduces AgentDojo attack success, and targeted whole-call and 303 saved-AgentLAB comparisons test granularity and multi-step transfer. These are bounded results: utility loss remains substantial, only 26/97 authority manifests compile, ..."

**替换句**：无需数字替换（本段未写 E78 具体数字）。
**叙事调整建议**：
- "sharply reduces" 在 8.61%→1.75% 下仍成立，保留；若 PM 认为 1.75% 不足以支撑 "sharply"，可降为 "substantially reduces"——finalize 后定稿。
- "utility loss remains substantial" 保留（47.4% vs 64.9% 仍是 substantial）。
- 可选新增半句（与 O6 联动）："...with an audited recovery path whose override trail is disclosed rather than certified"——仅在 O6 finalize 处置完成后启用。
- 321/AgentLAB 两句随 §2.6 裁决结果核对（若走选项 1 重跑且结果变化，"test granularity and multi-step transfer" 的支撑数字在 results 侧更新即可，本段措辞不变）。

### 2.9 Limitations（sections/limitations.tex）

**现状相关句**（L14-16）：
> "The main comparison uses one Qwen3-32B model and leaves nine baseline traces non-evaluable."

**替换句**：保留原句；**新增一句（占位）**：
> "The v17 headline numbers reflect an experimental recovery policy (\texttt{allow\_with\_trail} overrides and planner replan); the override trail is audited under obligation O6 with [V17-O6-VIOLATION-COUNT] violations in final materials, and override-released fields carry no affirmative membership proof."

**叙事调整建议**：
- ASR 上升（2→11）的机制披露放在 limitations 是正确位置：一句话说明"安全数字包含 recovery 策略的权衡代价"，与 results 的 recovery 披露呼应。
- "The E78 pathway audit is post-hoc" 句保留；若 §2.5 重算，引用数字同步。

---

## 3. 叙事影响分析

### 3.1 benign 33→46：效用利好如何写

**事实结构**：+13 任务（+13.4pp）；回收了守卫引入损失（30 任务）的 43.3%；距 no-defense（63）仍差 17 任务；50-task gate 仍失败（46<50）。

**写法建议**（按防 spin 纪律）：
1. 表述为"loss partially recovered"，不表述为"utility improved/solved"；参照系固定为 no-defense 63/97，不以旧构建 33/97 为参照系声称"提升"（否则触发 W 骨架 §2 所指"33/97 原数仍在，重定位被读作 spin"的变体——现在是 46/97 原数必须仍在）。
2. 机制归因指向 recovery/override 接口（resolver-fill 放行 + planner replan），用 pathway audit 重算结果支撑；归因 ≠ 豁免，post-hoc 免责声明保留。
3. gate 失败句必须与利好句同段或相邻出现（W 骨架 §4.2 bullet 5 纪律）："The full-set run still fails the predeclared 50-task utility gate."
4. 禁止措辞：~~"utility problem resolved"~~、~~"recovery removes the cost"~~、~~"comparable to no defense"~~。

### 3.2 ASR 2→11：上升如何解释

**（a）recovery 策略的权衡框架**：v17 的效用回收机制（`allow_with_trail` override、planner replan recovery）本质上是把此前 DENY/ABSTAIN 的一部分提交改为放行；放行集同时包含 benign（+13 任务）与 attack（+9 例成功）案例。因此 ASR 上升应表述为**同一机制的两个方向**，而非防御失效："the recovery path that returns benign utility also admits a small number of attack commits that the strict policy withheld"。支撑数字：override 总量与构成（finalize 后复测，占位 `[V17-OVERRIDE-COUNT]`）。

**（b）与 no_guard 8.6% 的对比**：绝对降幅仍有 6.86pp（8.61%→1.75%），相对降幅 79.7%。headline 建议保留"相对 no-defense"锚点，避免与自身旧版本（0.32%）对比形成"安全恶化"框架——正确参照系是 no-defense 与 baseline 族，不是历史构建。

**（c）H4 非拒绝驱动预判**：预注册的 H4 分解（字段检查阻止 / 工具未注册阻止 / authority-evidence abstain / 模型未尝试）刻画的是**ASR 下降的来源**；v17 下需对 **11 例成功的来源**做互补分解（新增维度：strict-ALLOW 放行 vs override 放行）。预判与检查点：
- 若 11 例集中于 override 放行且均为 resolver-fill（ρ 态）字段 → 与"recovery 权衡"叙事一致，可表述为机制性代价；
- 若任何一例的 override trail 携带五类扩权 finding（关联 O6 §4.3 红旗：多值字段聚合缺陷曾使 `outside_exact_plan` 被后续 check 覆盖）→ **这不是叙事问题而是安全问题**，必须先处置（修复+重跑）再谈替换；O6 处置结论是 v17 数字入稿的硬前置条件之一。
- H4 的正面读法仍可用：v17 的 ASR 降幅是在**更少的拒绝/abstain**（效用回收的副产品）下取得的，"非拒绝驱动"的成色反而提高——但此主张以对 11 例的逐例 pathway 审计为前提。

**（d）统计层面**：配对 McNemar、双 bootstrap CI、Holm 校正全部重算；预期 vs no-defense 仍显著，vs Sandwiching 的配对对比**方向反转**（见 §3.4）。

### 3.3 attack utility 207→273

**事实结构**：+66 任务（+10.4pp，全 key 629 分母）；回收守卫引入损失（138）的 47.8%；仍低于 no-defense（约 345/627≈55.0%）。

**写法建议**：
- 与 BU 同框架："attack-side utility partially recovered; still below no defense"；
- 注意 UA 的语义：attack key 上的用户任务完成度，其回升同样来自 recovery 策略，不与 ASR 上升分开解释（同一机制）；
- 分母纪律：现文 207/627（正文）与 .329=207/629（表）并存；替换时明确 v17 UA 的分母（273/629）并在正文与表之间保持一致。

### 3.4 Frontier/Pareto 风险（最高优先级）

**问题**：以 rate 口径比较，v17 下 Sandwiching（ASR 1.27%、BU .629、UA .581）在三条 headline 轴上全部优于 \sys{}（1.75%、.474、.434）。现文结论句 "competitive security–utility tradeoff, not Pareto dominance"（results L143-144；claim map L33 Boundary；W 骨架 §3 措辞规则）在当前论文中依赖"\sys{} ASR 低于 Sandwiching"这一轴；该轴反转后，**headline 三轴上 \sys{} 被 Sandwiching 支配**。

**裁决路径（按优先级）**：
1. **配对共评估口径核查**：现表是各行各自 evaluable 分母上的 rate；627/629 共评估子集上的配对比较可能给出不同的相对位置（Sandwiching 的 8 例成功与 \sys{} 的 11 例是否同 key 分布未知）。finalize 统计必须输出 \sys{} vs Sandwiching 的配对方向与 discordant counts，作为第一裁决证据。
2. **比较平面扩展**：若 rate 口径确认被支配，把比较平面从 (ASR, BU, UA) 扩到已披露轴——不可评估行保留策略、all-key bounds、abstention 构成、override trail 可审计性——并逐轴说明差异；这是 W 骨架 §3.2"逐点不可比性"论证的延续，但必须基于事实而非措辞。
3. **诚实降级**：若两路径都无法恢复"非支配"结论，则 results/conclusion 必须改为如实表述（"Sandwiching dominates on the three headline rates in this configuration; \sys{}'s distinguishing properties are [audited override trail / effect-level attribution / ...]"），claim map L33 Boundary 同步改写。禁止用措辞维持已不成立的结论（R1 overclaim 触发器）。
4. W 骨架 §3.2 中 "vs [BL-PS]：对方 ASR（8/627）高于我方" 的句子在 v17 下**直接为假**，属必须修订的骨架文本（见 §4）。

### 3.5 统计重算清单（finalize 后一次性执行）

| 统计量 | 现值（E78） | v17 状态 |
|---|---|---|
| 配对 ASR 差 + row-bootstrap CI | −0.083，[−0.105,−0.061] | 重算，占位 [V17-DIFF]/[V17-CI-ROW] |
| user-task-cluster CI | [−0.107,−0.060] | 重算，占位 [V17-CI-CLUSTER] |
| Holm-McNemar p（全族对比） | 7.3e−14 | 重算，占位 [V17-P-*]；注意 vs Sandwiching 方向反转 |
| 全 key ASR | 3/629 | 11/629（参考值） |
| BU / UA 点估计 | 33/97、207/627 | 46/97、273/629（参考值） |

---

## 4. 与 W 骨架 / D1 骨架 / claim map 的联动

### 4.1 W utility 重定位骨架（w_utility_repositioning_skeleton_2026-08-04.md）

| 骨架位置 | 现状态 | v17 影响 | 动作 |
|---|---|---|---|
| §2.2 bullet 1 "headline 净值 63/97→33/97" | FROZEN 表述 | 数字过时 | 改为 "63/97→[V17-BU]/97" |
| §2.3 全部 `[PA-*]`（标注 FROZEN） | 指向 E78-era pathway audit | v17 轨迹改变 → 全部失效 | 状态改标 PENDING-V17-RECOMPUTE；真源列指向重算后的新报告 |
| §3.2 bullet 2 "vs [BL-PS]：...ASR（8/627）高于我方" | FROZEN 断言 | **v17 下为假** | 强制改写（依 §3.4 裁决结果） |
| §3.3 `[V17-E78-ASR/BU/UA]` | 映射表 L15 .005/.340/.329 | 表值将变 | finalize 后更新映射真源 |
| §5 候选 A | 无数字依赖 | 不受影响 | 保留 |
| §7 自查清单 item 1 "33/97 原样存在" | — | 对象更换 | 改为 "[V17-BU]/97 原样存在" |
| §3.5 baseline 引用缺失（4 篇） | 未解决 | 不受影响但仍欠账 | 列入 §5 待办 |

### 4.2 D1 results 分支骨架（d1_results_branch_skeleton_2026-08-04.md）

- **R.6（E78 小节）**：段 1-3 主题句不含数字（占位纪律已生效），可直接复用；段 2 "安全收益有代价"与段 4 frontier 定位受 §3.4 裁决约束。
- **R.7（321-case）**：依 §2.6 裁决（重跑 vs 版本披露）。
- **R.9（O6 披露位）**：override 构成测量数字（总量、fallback 占比、违例计数）全部来自 v17 审计 → 在 finalize 复测前只允许"测量已预注册"级中性表述（D1 §4 规则 3 不变）。
- **§0 分支判定表**：H1-H5 判定输入全部用 v17 重算值；分支逻辑本身不变，但 H4 分解新增"放行路径"维度（§3.2c）需在 finalize 前补进协议口径（否则属于事后新增分解维度，违反预注册纪律——注意：该维度是**对成功案例的来源审计**，与"对 ASR 差异的事后切片"性质不同，但仍应书面预登记）。

### 4.3 claim map（claim_to_source_map.md）——diff 清单（不预更新）

| 行 | 内容 | 动作 |
|---|---|---|
| L32 | capacity-matched 726 keys 保留 | 核对 v17 finalizer gate 通过后重锚定 |
| L33 | 627 配对 ASR 54→2、63→33、−0.083、CI、p；Boundary "strong trade-off, not Pareto dominance" | 全量替换；Boundary 措辞依 §3.4 裁决（可能不再是 "not Pareto dominance"） |
| L34 | 全 key 3/629 + no-defense 界 | [V17-ASR-ALLKEY] 替换；界不变 |
| L35/L36 | pathway audit（32/37、16/32、22/32、12 例） | 重算后全量替换 |
| L57 | strict E77 audit（2,930 checks、738 revision calls、32 replan→allow） | 核对 v17 下是否变化 |
| 新增 | O6 义务行（obligation-to-evidence mapping） | 由 o6_obligation.tex 落地时按 claim_map_branch_templates 流程新增 |

纪律：所有 diff 在 finalize 当天按 `claim_map_branch_templates_2026-08-04.md` 模板执行，本评估不预改 claim map（决策书 §2f 第 1 条）。

---

## 5. 执行前置条件（门禁）

1. **v17 finalizer gate**：当前失败（`command_protocol_clean=false`，watch log 2026-08-04 02:21）。修复该 gate 并全项通过前，**零替换**。
2. **O6 红旗处置**：多值字段聚合缺陷（t2_o6 §4.3，2 行 `outside_exact_plan` 进入 final 材料）必须先处置（修复+重跑 或 限定+披露）；该缺陷与"11 例攻击成功的放行路径审计"直接耦合（§3.2c）。
3. **统计重算**：§3.5 清单全部由冻结脚本产出，禁止手填。
4. **重跑裁决**：321-case / AgentLAB / bounded adaptive 三项 v17-runtime 依赖实验的重跑与否，在 finalize 当天与 H1-H5 判定一并裁决。
5. **baseline 引用欠账**：PromptArmor / Sandwiching / MELON / Spotlighting 四篇 bib 条目（W 骨架 §3.5）在 frontier 段移植前补齐；§3.4 裁决使 Sandwiching 对比句成为焦点，引用欠账的风险等级随之上调。

## 6. 待办清单（汇总）

- [ ] 修复 `command_protocol_clean` gate → v17 finalize 冻结
- [ ] finalize 后复测 override 构成（总量/φ/违例计数），回填 O6 (S2)(S3)
- [ ] 重算配对统计（差值/双 CI/Holm-McNemar 全族），输出 vs Sandwiching 配对方向
- [ ] pathway audit 在 v17 日志上重跑（含是否新增对称"回收分解"的预注册决定）
- [ ] 321-case / AgentLAB / adaptive 三项重跑裁决
- [ ] §3.4 Pareto 风险裁决（三路径），确定 results L142-145 与 claim map L33 Boundary 的最终措辞
- [ ] 补齐 4 篇 baseline bib 条目（[CITE] 欠账，关联 W 骨架 §3.5）
- [ ] 按 §2 清单执行数字回填（B 线顺序：Evaluation→Results→Abstract→Intro→claim map）
- [ ] limitations 新增 override/recovery 披露句（依赖 O6 处置结论）
