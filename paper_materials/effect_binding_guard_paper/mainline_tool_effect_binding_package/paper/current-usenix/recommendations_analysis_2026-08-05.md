# 建议文档核对与执行决策分析（recommendations_analysis）

- 日期：2026-08-05（分析时点 16:23 CST）
- 分析对象：`theory_experiment_narrative_risk_reduction_recommendations_2026-08-05.md`（下称《建议》）
- 产出：research-assistant（只读分析；未修改任何代码/数据/运行中进程）
- 纪律声明：本次核对只读取了运行进度计数（行数）、基础设施信号（server 日志 400 计数）与代码/文档；**未读取、未聚合任何变体的官方 ASR/utility 结果**（遵守《建议》§7 P0-1"不读取 partial outcome 作决策"）。

---

## 0. 结论先行

1. **《建议》§3.1 的最关键指控属实，且根因比指控更深**：V1（`opaque_whole_call`）在 `agentdojo_representation_patch.py` L163 直接调用 V3/E77 字段级比较器 `compare_call_to_plan_with_evidence`，其判决是 V3 字段约束 conjunction 的标签塌缩（含 DENY→NEEDS_REPLAN 塌缩）。这不是实现偏离协议——**冻结协议 §4 V1 原文就是这么定义的**（"全部约束合并成一个 conjunction"），协议 §15 只要求"界面保持 call-level opaque"（该点实现已满足，`checks=[]`）。因此这是**协议层设计缺陷**：V1 与 V3 的授权内容同源，比较只隔离"反馈粒度"，不隔离"表示粒度"，V1/V3 的 representation-granularity 因果声明不成立。
2. **P0 暂停建议应予采纳**：V0 继续跑完（语义有效、两种修复方案都需要它，约 08-06 00:00 自然结束）；在 V0 完整性检查通过后、V1 启动前 kill 驱动（驱动是裸 bash 循环，无内置暂停门，操作窗口在 manifest 的 `CHECK variant=tool_identity_only rc=` 行之后）。V1 未开始，暂停零数据损失。
3. **V1 修复推荐方案 A（真 whole-call 表示）**，理由与成本分析见 §2.3：A 保住 V0→V1→V2→V3 的表示粒度阶梯与 N2 叙事资格，增量成本约 1-2 人日 + ~1.5h smoke 重跑；方案 B 只是把 A 推迟而非免除（《建议》自己声明 B 需"另增真正 whole-call 条件后才能完成表示归因"）。附明确的降级规则：若 A 在 08-07 EOD 前未完成实现与验证，切 B 保日历。
4. **方案 A 必须签发新 protocol ID**（协议 Phase 1 第 5 条明文）；建议保留 V0 数据并以 protocol v1/v2 血缘注记衔接（V0 语义字节级不变、冻结输入 hash 全部不变），不建议重跑 V0。
5. **《建议》§3.3 的 merged 口径数字（2,217/83/407；1,958/749；259；455）目前不可引用**：我对 r1/r2/merged 三份 audit 的独立重算均与之不符（详见 §1.4），仓库中不存在产出这组数字的 artifact；现有 override-composition 产物还是 08-03 的 r1 部分快照（265 次，自标 preliminary）。《建议》"必须由 merged artifact 正式重生成"的要求成立，且**重生成前需先预注册计数口径**（merged audit = r2 base 2,718 行 + repair stage 追加 60 行，9 个修复案例的截断原始行仍在内，朴素计数会重复计数）。
6. **H4/H5 与 context-integrity 门禁确认未实现**（❌），但三者均可作为 finalizer/监控侧纯增量（不需要重跑任何 GPU 条件）。context-integrity 有时间压力：V0 尚未跑到 workspace suite（v17 的 9 例截断全在 workspace u35/u38；runner 使用同级 65536 窗口），**对称修复政策必须在 V0 进入 workspace 前（今晚）预注册**。当前 V0 server 日志实际 HTTP 400 计数为 0（暂安全）。
7. **时间线影响可控**：原 ETA V3 ≈ 08-08 凌晨 → 采纳 P0+方案 A 后全链完成 ≈ 08-09/08-10，stability+finalize+H1-H5 判定仍在原 W3（08-17→08-23）内，不影响 08-18 注册决策点（目标本为 Cycle 2）。
8. 既有规划融合：《建议》主叙事 = 白皮书 N1 基座的强化版，与 N1/N2/N3 决策树兼容；唯一实质修正是**决策树根节点（V0-V3）在 V1 修复前被污染**——N2（正结果叙事）分支在修复前不得被任何结果触发。8 条投稿门禁：2 条 🔴/❌（V1 语义、H1-H5 机器结论）、5 条 ⚠️ 部分达成、1 条 ❌ 未开始（第二模型，可用摘要边界句替代）。

---

## 1. 逐项核对：《建议》§2–§6 vs 当前状态

状态标记：✅ 已实现 / ⚠️ 部分实现 / ❌ 未实现 / 🔴 与当前执行冲突。

### 1.1 总表

| 《建议》条目 | 状态 | 证据（文件/行号） |
|---|---|---|
| §2.1-2.3 理论主线收窄（表示义务、四步链条、T1 改名、O6 不作 confinement 扩展、policy family 入定义） | ⚠️ 方向已具备，文本未落地 | T1/T3/O6/E2 草稿已按相近方向完成（war_plan §4.8/§4.9）；但 `t1_theorem_section.tex` 现名仍是 "Counterfactual Registration Converges"（war_plan §4.9 LaTeX 包条目），改名与符号统一未执行 |
| §2.4 理论补强 P0×3（符号统一 / T1 重写 / strict-override 分离报告） | ⚠️ | strict/effective 双字段在审计中已分离记录（e77_runtime 落盘 guard_decision/decision/strict_authorization_satisfied）；定理层分离表述与主文一套定义未完成 |
| §3.1 V1 归因有效性修复 | 🔴 问题属实，未修复，V1 全量运行在即 | 见 §1.2 详细核实 |
| §3.2-1 H4（DENY/NEEDS_REPLAN/coverage 分解、执行减少 vs 未达成分解） | ❌ 未实现 | `finalize.py` 只有 `_runtime_metrics` 聚合计数（L271-302），无配对阻断分解、无 H4 判定 |
| §3.2-2 H5（suite/strata 方向与分母） | ❌ 未实现 | `finalize.py`/`finalize-strict-attribution.py` 无任何 suite/attack_type/injection_task_id 分组输出 |
| §3.2-3 HTTP 400 / truncation / empty-assistant 门禁 | ❌ 严格归因链未实现 | runner `parse_case_log`（L458-480）只读 utility/security/error/duration；finalizer `integrity_errors`（L120-151）只查 null 纪律与 reconciliation。v17 侧有可复用检测（context-repair-v17 detect、merged finalizer 的 post_tool_empty_assistant 门） |
| §3.2-4 预注册对称 context repair | ❌ 未预注册（v17 已执行过同类流程但未覆盖本实验） | P2-b 工具链存在（detect/repair/merge），本实验无 repair 政策文档 |
| §3.2-5 冻结并验证 runner/patch/comparator/finalizer/statistics/scorer/环境/模型 SHA-256 | ✅ | runner `verify_frozen_inputs`（L191-221）+ 每行 8 类 hash；protocol.json `protocol-frozen`（frozen_at 2026-08-05T03:03:33Z）；模型 sha256 `efd97156…` 一致；47 项测试、smoke 64/64 PASS（phase_c 报告） |
| §3.3 v17/O6 merged 重审计 | ⚠️ merged 正源已冻结，口径重生成未做 | 见 §1.4 |
| §3.4 Sandwiching matched-key 配对比较 | ⚠️ 基础设施存在，v17 重算未做 | `analyze_e78_capacity_matched_statistics.py` 含 `agentdojo_live_prompt_sandwiching`（L23）、`evaluable_pairs`/exact McNemar/Holm/paired+cluster bootstrap；尚未在 v17 merged 行上运行。机制性 stress 数据集（§3.4 后半）完全未建 |
| §3.5 证据矩阵 | ⚠️ 见 §3.3 逐行评估 | — |
| §4 叙事（推荐"表示义务与可执行注册"） | ⚠️ 与 N1 基座一致，未正式采纳为主叙事 | 见 §3.1 |
| §5 论文结构 | ⚠️ 未落地（Phase D 前不冲突） | D1 骨架现有结构按 E 编号组织，需在 Phase D 改为按 claim 组织 |
| §6 风险分类表 | ✅ 各项风险与仓库事实一致 | Sandwiching 三轴占优、V1 无效、单模型等均有证据支撑（war_plan §4.9、v17_number_replacement §3.4） |
| §7 P0-P2 执行顺序 | 🔴 P0-2（暂停驱动）与当前执行直接冲突 | 见 §2 |
| §7 投稿最低门禁 8 条 | ⚠️ 见 §3.3 | — |

### 1.2 核实 (a)：V1 归因有效性（最关键）——指控属实

代码事实（`experiments/security-analysis-ablation-and-overhead/source/strict-atom-representation-attribution/agentdojo_representation_patch.py`）：

- L297：`base_compare = e77_patch.compare_call_to_plan_with_evidence` —— 即 E77/V3 的字段级比较器；
- L133-183 `_make_opaque_whole_call(base_compare)`：V1 比较器**内部调用** `base_compare(...)`（L163-170），然后把 `detailed["decision"]` 塌缩为单一 opaque 判决（ALLOW → `whole_call_within_authorized_envelope`；其余 → `whole_call_outside_authorized_envelope`，`checks=[]`）；
- L259-273 `select_variant_comparator`：V3 原样返回 `base_compare`；V2 用 raw-schema registry 替换字段集后调 `base_compare`；V1 = 上述包装。

语义后果（推理，非文档转述）：

1. V1 的授权判定内容 = V3 字段约束在 V3 字段集上的 conjunction。两变体的 ALLOW 集合差异不来自"表示"，而只来自塌缩引入的两点：(i) 反馈粒度（opaque reason vs per-field checks/repair）；(ii) DENY→NEEDS_REPLAN 的判决类别塌缩（改变后续 recovery 分支）。
2. 因此 V1 vs V3 至多隔离"解释/恢复粒度"，**无法证明 whole-call representation 不足**；协议 §1 主问题中"整调用表示 vs atom 表示"的对照不成立。
3. 协议原文背书了这一实现：冻结协议 §4 V1"将该工具的全部约束合并成一个 conjunction，最终只产生一次 call-level match/mismatch"；§15 第 2 条仅要求"verdict 可由字段约束 conjunction 产生，但界面必须保持 call-level opaque"——实现满足 §15 的界面要求（单元测试 L650-653 断言 opaque reasons），但协议对"whole-call 表示"的定义本身与"用字段约束 conjunction 产生 verdict"自相矛盾：**能计算 conjunction 的 monitor 已经持有字段级表示**。
4. 结论：《建议》§3.1 指控属实；修复是协议级变更（需新 protocol ID），不是代码 bug 修复。smoke 在当前语义下 PASS（phase_c 报告 16/16）只证明 wiring，不构成语义背书。

### 1.3 核实 (b)：H4/H5 实现状态——均未实现（但可纯增量补齐）

- `finalize.py` 现有能力：`case_metrics`（ASR/BU/AU，固定分母 629/97）、`_runtime_metrics`（n_allow/n_deny/n_abstain/n_needs_replan、decision_coverage、override_rate、strict_execution_ratio、monitor_applicability、reconciliation violations）、`paired_asr`（exact McNemar+Holm）、`paired_utility`（paired bootstrap + 非劣 -0.05 判定）。
- **缺 H4**：无"V3 阻断而对照未阻断的 attack case"的配对分解，无"攻击因执行减少被阻止 vs 已执行但未达成"的拆分，无 H4 判定输出。原始材料已在每行中（`n_executed_effectful_calls`、`n_deny`、`official_attack_success`），可纯 finalizer 增量实现，不需重跑。
- **缺 H5**：无任何按 suite（banking/slack/travel/workspace）或攻击 strata（attack_type × injection_task_id）的方向/分母输出，无"≥3 suite 且 ≥3 strata"判定。行内已有 suite/attack_type/injection_task_id 字段，同样可纯增量实现。
- **缺 H1-H3 机器判定**：统计量齐备但没有把 Holm-adjusted p、非劣 CI 下界聚合成"H1/H2/H3 pass/fail"的判定块（协议 §2.2 判定规则的机器化未完成）。协议 §2.3 解释矩阵目前是人工流程。
- 影响：不阻塞 GPU 运行；必须在 finalize 前完成（《建议》§7 P0-5 与 P1-2 一致）。

### 1.4 核实 (c)：v17/O6 merged 口径——必须重生成，且《建议》引用的数字本身暂无出处

**已冻结事实**（`p2b_execution_report_2026-08-05.md` + `protocol.json`）：

- merged 目录 `...v17-726-r2-context-repaired`：finalizer 16/16 全过（含新红旗门 `no_allow_with_expansion_findings`），`finalizer-passed.json` 2026-08-05T02:58:34Z；
- merged 指标（726 行）：ASR 11/629、BU 46/97、attack utility **272/629**（《建议》数字正确；war_plan 里的 273 是 r1 原始值）；post-tool 空 assistant 行 9→0；
- 冻结 plan cache sha256 `ea881cfc…` 与 merge_manifest 的 `merged_plan_cache_sha256` 一致。

**独立重算**（只读 python 计数，本次分析执行）——precommit_check 行上的朴素计数：

| 口径 | 行数 | effective ALLOW/DENY/NEEDS_REPLAN | strict true/false | override commits（strict 非 ALLOW→effective ALLOW） | diagnostic flag true |
|---|---|---|---|---|---|
| r1 audit | 2,729 | 2,219 / 90 / 420 | 1,951 / 778 | 268 | 445 |
| r2 audit | 2,718 | 2,218 / 89 / 411 | 1,949 / 769 | 269 | 446 |
| **merged audit（朴素）** | **2,778** | **2,275 / 91 / 412** | **2,000 / 778** | **275（全部 execution_attempted，fallback=0）** | **481** |
| 《建议》引用 | (2,707) | 2,217 / 83 / 407 | 1,958 / 749 | 259 | 455 |

发现：

1. **merged audit 是 r2 base（2,718 行）+ repair stage 追加 60 行**，9 个修复案例的截断原始行仍保留在文件内（query_hash 级计数核对：7 个 query_hash 计数增加，增量合计 60，无删减）。朴素计数对修复案例双重计行，直接引用会失真。
2. **《建议》引用的数字（合计 2,707 行）与仓库中任何 artifact 都不匹配**，也与我遇到的三种朴素口径不同（与 merged 朴素口径差 71 行）。最可能的解释是某次未落盘的 case-bound 去重分析（剔除 9 个修复案例的截断原始行）——但该口径未在仓库中预注册，其出处无法追溯。**因此这组数字在正式重生成前不得入稿，也不得作为 O6 命题参数。**
3. 现有 `results/strict-atom-representation-attribution/override-composition/` 产物（265 overrides、φ=0.000、2 行 outside_exact_plan 违例）指向 **r1 目录**、生成于 08-03（v17 完成前），自标 "preliminary / Re-run after the finalizer passes"——已过期，且其"2 行违例"在 r2（最严格优先聚合修复后）已由 merged finalizer 新红旗门确认为 0。
4. `o6_attack_release_path_analysis_2026-08-05.md`（11 案例放行路径）也做在 **r1** audit（5,625 行）上；r2+修复后 audit 行已变，需在 merged 上重跑（脚本已存在、只读可复现）。
5. 方向性一致的部分：override 均为结构化路径（fallback=0，三套口径一致）、flag true 中 strict 已 ALLOW 的占比显著（259 vs 455 的区分语义正确：`diagnostic_uncertainty_override` 在 strict-ALLOW 行也置 True，见 override_composition_measurement §3.1）。

**结论**：《建议》§3.3 要求成立且比它表述的更紧——不仅要"由 merged artifact 正式重生成"，还要**先预注册计数口径**（case-bound 绑定规则、截断原始行剔除规则、override commit 与 diagnostic flag 双口径分别报告），再生成带 snapshot hash 的正式 artifact；在此之前《建议》自己的 259/455/2,217 等数字也只是占位。

### 1.5 核实 (d)：context-integrity 门禁——未实现，且存在明确复发风险窗口

- runner 与 finalizer 均无 HTTP 400 / truncation / empty-assistant 检测（§1.1 表已列证据）。风险机制已被 v17 r1/r2 两次证实：AgentDojo `local_llm.py` 的 `except Exception` 吞掉 400 并返回空串 → case 日志无 error、`run_completed=true`、官方 scorer 照常打分 → **截断轨迹以"干净行"身份进入统计**（war_plan §4.9 更正块、pm_process_review §1.4）。
- 当前运行的直接风险：runner 用 `DEFAULT_CONTEXT=65536`（与 v17 同级窗口）；case 顺序按 `suite, user_task_id, ...` 排序 → banking→slack→travel→workspace。v17 的 9 例截断全部在 workspace u35/u38，即**每个变体的最后 ~280 case 才到达风险区**。当前 V0 在 116/726（slack 段），server 日志实际 HTTP 400 计数 = 0（"CUDA Graph id 400" 噪声 1,078 条按 P2-b 惯例排除）。
- 缓解的有利条件：风险案例集是 case 固有属性（长 context 任务），四变体共享同一模型/窗口/case 集 → 失败**跨变体对称**，配对结构基本受保护；v17 P2-b 的 detect/repair/merge 工具链可原样复用。
- 时间约束：**对称修复政策与检测口径必须在 V0 进入 workspace 前预注册**（按当前速率估算为今晚 ~22:00-24:00），否则 V0 的 workspace 行将按未预注册规则处置。检测本身可先以只读旁路监控落地（grep server 日志 + 扫描 case 日志），不打断运行。

### 1.6 核实 (e)：Sandwiching 配对比较与"三路径裁决"的衔接——一致，属同一路径的具体化

- 既有"三路径裁决"（`v17_number_replacement_impact_2026-08-05.md` §3.4）：①配对共评估口径核查 → ②比较平面扩展（披露轴）→ ③诚实降级。
- 《建议》§3.4 的 matched-key 配对比较 = 路径①的可执行形式：同 key、同模型、同任务、同攻击 + 置信区间。基础设施已存在（`analyze_e78_capacity_matched_statistics.py`：`evaluable_pairs` 按 (suite,user_task,attack,injection) key 配对、exact McNemar、Holm、paired/cluster bootstrap；方法表含 `agentdojo_live_prompt_sandwiching`），但**尚未在 v17 merged 行上重算**——当前"Sandwiching 三轴占优"是各自 evaluable 分母上的 rate 比较（1.27%/.629/.581 vs 1.75%/.474/.434），配对方向与 discordant counts 未知。
- 衔接建议：finalize 当天先出路径①结果；若配对仍被支配，进入路径②/③。《建议》额外的"机制性 stress 数据集"（同工具名、相似表面文本、effect/recipient/provenance 变化的攻击对）是新实验，不在三路径内，应单独立项预注册（见 §4 暂缓项）。
- 注意：E78 baseline traces 是 E78-era 运行的产物；baseline 侧未变（同模型/任务/攻击），配对重算只需把本方法侧换成 v17 merged 行，无需重跑 baselines（前提：key 集兼容，finalize 时核验）。

---

## 2. 关键决策点：P0"暂停 V1 前驱动"

### 2.1 当前执行状态（核对值）

- 驱动 PID 1448380（14:56:45 启动）：`run-v0v3-full-serial-driver.sh` 是裸 bash `for` 循环（V0→V1→V2→V3），每变体 `wait` 退出后跑 read-only completeness check，然后**立即**启动下一变体；无暂停门、无 gate 文件、无信号机制。
- V0（tool_identity_only）：116/726（16.0%，16:23），约 44.6 s/case → **V0 完成 ETA ≈ 08-06 00:00**；不暂停时全链（V1-V3 各 ~9.5h）完成 ≈ 08-08 凌晨至上午（与 war_plan "ETA V3 ≈ 08-08 凌晨" 一致）。
- V1-V3 目录尚未创建；V1 零进度。runner 支持 `--resume`，每变体独立调用、自带 llama.cpp server（变体间无共享状态）。
- 协议已冻结（protocol_id `bccf19ea51b13f27`，已写入 V0 每行）；冻结输入 hash（plan cache `ea881cfc…` 等）跨变体一致由 finalizer 强制。

### 2.2 逐问回答

**(a) V0 应继续跑完，不中止。**
理由：V0（tool-identity）语义在方案 A、B 下都有效且都被需要（它是唯一的身份级粗表示对照）；中止损失 ~7.5 GPU h 且丢掉基线；《建议》§3.1 也认可 V0 保留。V0 数据在两种方案下均无需重跑（语义字节级不变）。

**(b) 暂停时机：V0 完成 + completeness check 通过之后、V1 启动之前。**
驱动无内置暂停，操作配方（只 kill 进程、不改任何脚本/数据）：

1. 监控 `runs/strict-atom-representation-attribution/qwen32/_v0v3_full_driver_manifest_2026-08-05.log`；
2. 当出现 `[driver] ... CHECK variant=tool_identity_only rc=0` 行后、`LAUNCH variant=opaque_whole_call` 行出现前，`kill -TERM 1448380`（CHECK 本身需要数秒至分钟级读 726 行，操作窗口充足）；
3. 若错过窗口（manifest 已出现 `LAUNCH variant=opaque_whole_call`）：kill 驱动与 V1 runner（pid 在 manifest 中），并把 `opaque_whole_call/repeat-0/` 目录整体归档移出（旧语义的部分行绝不能与新语义混存；`--resume` 会跳过已存在 key）；
4. 恢复时不再依赖原驱动循环，直接按协议 §10 #4 逐变体调用 `run-strict-attribution.py --scope full --variant <name> --repeat-index 0 --port 18087 --resume`，维持 V1→V2→V3 顺序（与原驱动逐字相同的命令，仅执行器变化，记入 manifest）。

不推荐"立即 kill"：V0 还有 ~84% 有效工作；也不推荐"让 V1 跑完再说"：那将产出 ~10 GPU h 的语义无效数据（至多可改标为 opaque-feedback 消融），并把预注册纪律置于"先跑后改"的被动位置。

**(c) 方案 A vs B：推荐 A。**

| 维度 | 方案 A（真 whole-call） | 方案 B（改名 atom_decision_opaque_feedback） |
|---|---|---|
| 归因价值 | 恢复 V0→V1→V2→V3 表示粒度阶梯；N2 叙事资格保留 | whole-call 阶梯缺失，V0 成唯一粗对照；论文下界叙事（"粗表示合并授权不等价执行"）失去标准粗实例对照 |
| 代码工作 | 新比较器 + whole-call envelope 注册投影 + 单元测试 + 新 protocol ID + smoke 重跑 | 改名/标签 + 协议修订 + smoke 重跑（协议 §9 Phase 2 同样触发） |
| 日历成本 | 实现 ~1-2 人日；GPU 与原计划相同（V1 本就要跑 ~9.5h） | 近零，但留下证据洞 |
| 后续义务 | 无 | 《建议》明文：仍需"另增真正 whole-call 条件"——A 被推迟而非免除 |
| 风险 | whole-call authority 注册规则需设计并预注册（见 d） | 论文必须放弃 V1/V3 representation-granularity 因果声明（主张收缩幅度大） |

推荐 A 的核心逻辑：B 的"便宜"是一次性的，而它放弃的恰是本文主叙事（表示充分性）最需要的对照层级；A 的增量成本主要是 1-2 天工程且与 GPU 链并行。附降级规则（事先承诺，防沉没成本）：**若 A 的实现+测试+smoke 在 08-07 EOD 前未完成，切 B，并把 A 列为投稿前补充条件（V1′）**。

**(d) 方案 A 的工作项与协议版本处理：**

1. **whole-call authority 注册（核心设计点）**：建议采用冻结 plan cache 的确定性投影——对每个 planned call，其 whole-call envelope = 经同一 totalization/canonicalization 管线序列化后的整调用串，比较规则 = 精确匹配（envelope exact-match）；不匹配 → NEEDS_REPLAN（opaque 反馈）。权威性来源与所有变体相同（同一 `frozen-common-plan-cache.json`），保持协议 §3.3"同一初始 authority"不变量。投影规则 + envelope registry 必须作为新冻结 artifact 预注册并写入新 protocol.json 的 hash 表。需向用户披露的科学后果：exact-match envelope 非常严格（参数值替换即不匹配），V1 可能表现为高 NEEDS_REPLAN/低执行覆盖——这正是"whole-call 表示授权盲目性"的预期刻画，属合法科学结果，但 H4 分解必须同时报告该机制。
2. **代码**：`agentdojo_representation_patch.py` 新增真 whole-call 比较器（不调用 `base_compare`、不产生 per-field repair）；envelope 投影脚本；单元测试按协议 §11.1 模式补：planned tool + 参数替换 → V0 ALLOW、V1 非 ALLOW；匹配整调用 → V1 ALLOW；V1 恰产生一个 aggregate check。
3. **协议版本**：协议 Phase 1 第 5 条明文"此后任何协议改动必须产生新 protocol ID"。V1 语义变更 → **签发 protocol v2**（新 md + 新 protocol.json，status=protocol-frozen，输入 hash 表不变、新增 envelope registry hash、附变更记录：仅 V1 定义变更，V0/V2/V3 逐字不变）。V0 行保留 protocol_id `bccf19ea51b13f27`：finalizer 的 hash 一致性门禁只校验冻结输入 hash（不校验 protocol_id），配对不受影响；在协议 v2 与最终报告中记录血缘（"V0 executed under v1; V1-V3 under v2; frozen inputs identical"）。**不建议为统一 ID 重跑 V0**（+9.5 GPU h 无语义收益）。
4. **smoke 必须重跑**：协议 §9 Phase 2"若发现代码错误，修复后四个条件全部重跑 smoke"——虽然这是语义修订而非 bug 修复，同一纪律适用；4×16 ≈ 1-1.5 GPU h。原 smoke 产物已归档（phase_c 报告），新 smoke 产物独立目录。
5. V2/V3 不受影响，不需要重跑；finalize/statistics 逻辑不受影响。

**(e) 时间线影响：**

| 节点 | 原计划 | 采纳 P0+A 后 |
|---|---|---|
| V0 完成 | ~08-06 00:00 | 不变 |
| 暂停 + V1 重构（代码/测试/protocol v2/envelope 冻结）+ 重跑 smoke | — | 08-06 → 08-07 |
| V1 全量（726） | 08-06→08-07 | 08-07 → 08-08 |
| V2 / V3 全量 | 08-07 / 08-08 凌晨 | 08-08 / 08-09 → **全链完成 ≈ 08-09~08-10** |
| stability（160×4×2≈16h GPU）+ finalize + H1-H5 判定 | W3（08-17→08-23） | 08-10→08-14，仍落在 W3 内 |
| 08-18 注册决策点 / Cycle 2 目标 | 不受影响 | 不受影响（净延迟 ~1.5-2 天，W6 缓冲未动） |

---

## 3. 与既有规划的融合

### 3.1 主叙事 vs N1/N2/N3 决策树——一致，加一道前置闸

- 《建议》主叙事"表示义务与可执行反事实注册" ≡ 白皮书 N1 基座（表示义务 + 反事实 witness 方法论 + 条件性 mediation）的强化版，并吸收了 T1（有限域单调终止）、T3（novelty boundary）、E2（policy-family relative）的既有产出方向。**结论：融合为"N1 为无条件基座，N2/N3 为结果分支"，与 accept_path §4 决策树结构兼容。**
- 唯一实质修正：**决策树根节点在 V1 修复前被污染**。现行树的"正（V3 显著优于 V0/V1/V2 + H4 + H5）→ N2"分支，其 V1 比较项在当前语义下无效；在修复落地前，任何中途结果都不得触发 N2 写作，也不得用于论证"方案 B 足够"。这与协议 §2.2"不根据中途结果修改 variant"纪律一致。
- 《建议》§2.3 的理论收窄与既有草稿的相容性：T1 草稿已是有限域表述（轨迹检查 9/9），改名为 "Finite-Domain Registered Refinement..." 低成本；T2/O6 草稿已按 window 决策书 §2b 重述为"排除式保证 + 证据隔离"（与《建议》"O6 不证明 affirmative authority membership"一致）；T3 已是构造性 novelty-boundary 命题（与《建议》P2 项一致）。需要新做的主要是：T1 标题/前提改写、主文单套符号统一、strict/override 在定理-图表-结果三处的分离报告。

### 3.2 《建议》P0-P2 vs 决策书/作战计划——冲突点与调整

| 冲突点 | 既有规划 | 《建议》 | 裁决建议 |
|---|---|---|---|
| V0→V3 一气呵成 vs V1 前暂停 | war_plan §4.10 Phase C："每变体完成 CHECK PASS → 全部完成后 finalize"；驱动无暂停 | P0-2 暂停串行驱动 | **《建议》优先**（归因有效性 > 日历；延迟可被 W2-W3 余量吸收，当前进度本就超前于 window 决策书的 W2 排期） |
| 协议冻结不可动 vs V1 语义变更 | protocol.json 已 frozen；协议 §2.2 中途不得改 variant | P0-3 修正 V1 语义并更新协议版本 | 两者可调和：按协议 Phase 1 第 5 条签发 **protocol v2**（变更留痕、输入 hash 不变、V0 血缘注记）；这不是"中途改阈值"，是预注册体系的版本化修订，须在 V1 任何 case 运行前完成 |
| finalize 后直接 H1-H5 vs 先补 H4/H5 实现 | war_plan："全部完成后 finalize → H1-H5 判定" | P0-5 先实现 H4/H5 finalizer + 单测 | 无实质冲突：H4/H5 是 finalize 的前置代码，插入 GPU 空窗期（暂停期）完成，反而利用等待时间 |
| v17 数字落地流程 | v17_number_replacement §5 门禁：finalizer gate（已过）→ O6 红旗处置（r2 已过新门）→ 统计重算 | §3.3 增加：merged 口径正式重生成 + 259/455 不得混用 + 结果表三分（strict ALLOW / override / blocked） | 并入既有门禁清单，作为 Phase D 数字回填的硬前置（CPU 工作，不占 GPU） |
| Sandwiching 裁决 | v17_number_replacement §3.4 三路径（finalize 后） | §3.4 matched-key 配对 + CI；另加机制性 stress | 三路径保留为主裁决流程；机制性 stress 数据集单独立项、P2 优先级（见 §4 暂缓） |
| context repair | 仅 v17 有 P2-b 闭环；本实验无政策 | §3.2-4 预注册对称修复 | **立即补**：复用 context-repair-v17 工具链，政策文档在 V0 进入 workspace 前（今晚）落盘 |

### 3.3 投稿最低门禁 8 条达成度

| # | 门禁 | 达成度 | 依据 |
|---|---|---|---|
| 1 | 正文数字映射唯一 finalizer-passed artifact | ⚠️ | v17 merged 已 finalizer-passed；但 O6/override 数字未重生成（§1.4）、严格归因结果未产生、PDF 仍是 E78 旧数字（war_plan §4.9 确认） |
| 2 | V1/V2/V3 语义与论文标签一致 | 🔴 | V1 现语义≠whole-call（§1.2）；修复前不满足 |
| 3 | H1-H5 均有机器生成结论 | ❌ | H4/H5 未实现；H1-H3 有统计量无判定块（§1.3） |
| 4 | context failure 为零或有预注册对称可审计 repair | ⚠️ | v17 侧满足（P2-b 9/9，overlay+manifest）；严格归因侧门禁与政策均未建（§1.5） |
| 5 | strict 与 override execution 分开，定理不覆盖后者 | ⚠️ | 审计字段已分离（guard_decision/decision/strict_authorization_satisfied）；O6 草稿已按排除式表述；但 merged 口径未重生成、主文三分表未写 |
| 6 | 强基线同 key/模型/任务/scorer | ⚠️ | E78 capacity-matched + 配对脚本已具备同 key 能力；v17 重算未执行 |
| 7 | Abstract/Intro/Conclusion 无过强声明 | ⚠️ | claim boundary 纪律与占位符体系在位；但 W 骨架 §3.2 "vs Sandwiching ASR 高于我方"句在 v17 下为假（v17_number_replacement §3.4-4），须修订；Pareto 句失效风险未裁决 |
| 8 | 第二模型/独立域证据，或摘要明示单模型边界 | ❌ | E1 未启动（既有计划列 W4）；limitations 已有单模型披露，摘要边界句为合规替代项 |

---

## 4. 采纳 / 暂缓 / 拒绝清单与调整后执行顺序

### 4.1 清单

**采纳（立即/本周）：**
1. V0 跑完后暂停驱动（§2.2(b) 操作配方）；
2. V1 按方案 A 重构（§2.2(d)），附 08-07 EOD 降级到 B 的事先规则；
3. 签发 protocol v2 + envelope registry 冻结 + 四变体 smoke 重跑；
4. context-integrity：只读旁路监控现在就位；对称 context-repair 政策今晚（V0 进 workspace 前）预注册；runner/finalizer 的门禁集成在暂停期完成；
5. H4/H5 + H1-H3 判定块 finalizer 实现 + 单元测试（暂停期 CPU 工作）；
6. merged artifact 口径重生成：先预注册计数口径（case-bound 绑定 + 截断原始行剔除 + override commit/flag 双口径），再重跑 override-composition 与 11 案例放行路径分析；
7. 主叙事采纳"表示义务与可执行注册"（N1 基座强化版）；理论收窄三项（T1 改名/符号统一/strict-override 分离）纳入 Phase D 前置；
8. Sandwiching matched-key 配对重算排入 finalize 当天（三路径裁决路径①）。

**暂缓（预注册设计先行，执行延后）：**
1. 机制性 stress 数据集（《建议》§3.4 后半）：先写预注册设计（攻击对构造规则、所有基线同跑），主结果出来后再执行——避免在 V0-V3 未定时增加 GPU 分支；
2. 第二模型 E1：维持 window 决策书排期（W4、finalize 后），不提前占用 GPU；
3. 321-case / AgentLAB / bounded adaptive 三项 v17-runtime 依赖重跑：维持 v17_number_replacement §5 的 finalize 当天裁决；
4. 《建议》§5 论文结构重排：Phase D 执行，不提前动正文。

**拒绝/修正：**
1. 拒绝"立即 kill V0"（损失有效基线数据）；
2. 拒绝重跑 V0 以统一 protocol ID（以 v1/v2 血缘注记替代，省 ~9.5 GPU h）；
3. 修正《建议》§3.3：其引用的 merged 数字（2,217/83/407；1,958/749；259；455）**在重生成完成前不得被任何文档当作既成事实引用**——仓库中无产出该数字的 artifact，我的三套独立重算（r1/r2/merged 朴素）均不一致（§1.4）。方向性结论（override 全结构化、fallback=0、commit≠flag）成立，具体数值以重生成 artifact 为准。

### 4.2 调整后的执行顺序（周粒度）

**08-05（今日剩余，GPU 不中断）**
- V0 继续（ETA ~08-06 00:00）；
- CPU 并行：① context-integrity 旁路监控上线（server 日志 400 计数 + case 日志空 assistant 扫描，只读）；② 对称 context-repair 政策文档落盘（案例集判定规则、窗口阶梯 73728→81920→122880、四变体同案同策、overlay manifest 要求）——**硬截止：V0 进入 workspace 前**；③ 开始 V1 方案 A 实现（比较器/envelope 投影/测试）。

**08-06（暂停日）**
- V0 completeness check 通过后 kill 驱动（§2.2(b)）；记录 V0 运行与源码快照 hash（《建议》P0-1 的未竟部分：当前冻结记录只含输入 hash，建议补代码树快照 hash 入档案）；
- 完成方案 A 实现 + 单测；protocol v2 + envelope registry 冻结；
- CPU 并行：merged 口径预注册 + override-composition/11 案例分析重生成；H4/H5 finalizer 实现开始。

**08-07**
- smoke 四变体重跑（~1-1.5 GPU h）→ 通过后启动 V1 全量；
- **EOD 检查点**：若方案 A 尚未通过 smoke → 触发降级规则，切 B（改名+协议修订+smoke），A 转为投稿前补充条件。

**08-08 → 08-09**
- V2 全量、V3 全量（各 ~9.5h）；期间完成 H4/H5 + H1-H3 判定块 + 单测；context-integrity 监控持续（workspace 段重点）。

**08-10 → 08-14（原 W3 前段）**
- stability repeats（160×4×2 ≈ 16 GPU h）→ fail-fast finalize（--require-complete --require-paired）→ H1-H5 机器判定 → 按协议 §2.3 矩阵分支决策（N1/N2/N3）；
- 同期：v17 配对统计重算（含 vs Sandwiching matched-key 方向）、pathway audit 重跑裁决。

**08-15 → 08-18**
- 分支写作启动（Phase D 顺序：Evaluation→Results→Abstract）；08-18 注册决策点：以"H1-H5 判定 + 门禁 1-8 状态"为依据向用户提交轮次建议（默认 Cycle 2 不变）。

### 4.3 需要用户拍板的决策项

| # | 决策项 | 建议 | 截止 |
|---|---|---|---|
| D1 | V1 方案 A（真 whole-call）vs B（改名+放弃因果声明） | A，附 08-07 EOD 降级规则 | 08-06 暂停时 |
| D2 | 暂停时机与方式（V0 自然结束后 kill 驱动；错过窗口则连 V1 runner 一起 kill 并归档目录） | 按 §2.2(b) 配方 | 08-06 ~00:00 |
| D3 | protocol v2 签发 + V0 保留 v1 血缘注记（不重跑 V0） | 采纳 | 08-06 |
| D4 | 方案 A 的 whole-call authority 注册规则（frozen plan cache 的 exact-match envelope 投影） | 采纳并预注册 hash | 08-06 |
| D5 | 严格归因实验的对称 context-repair 政策（复用 P2-b 工具链） | 今晚前批准落盘 | 08-05 晚 |
| D6 | merged 口径预注册：case-bound 绑定、截断原始行剔除、override commit/flag 双口径分报 | 采纳后执行重生成 | 08-06 |
| D7 | 接受全链完成 ETA 从 08-08 后移至 08-09/08-10 | 建议接受 | 08-06 |

---

## 5. 证据索引（可追溯）

| 事实 | 来源 |
|---|---|
| V1 内部调用 V3 比较器 | `agentdojo_representation_patch.py` L133-183、L259-273、L297（本次通读） |
| 协议 V1 原文/§15 审查条款/新 protocol ID 规则 | `strict_atom_representation_attribution_protocol_2026-08-03.md` §4、§15、Phase 1-5、§2.2、§9 Phase 2 |
| 驱动无暂停机制 | `run-v0v3-full-serial-driver.sh` L27-46；manifest 日志（PID 1448380，14:56:45 启动） |
| V0 进度 116/726、~44.6s/case、server 400=0 | 运行目录 paired-case-results.jsonl 行数 + server 日志 grep（16:23 只读计数） |
| H4/H5 未实现、无 suite/strata 分组 | `finalize.py` L99-302（通读）；`finalize-strict-attribution.py`（通读） |
| context 门禁缺失 | `run-strict-attribution.py` `parse_case_log` L458-480；`finalize.py` `integrity_errors` L120-151 |
| protocol.json 冻结、protocol_id bccf19ea51b13f27 | `evaluation/strict-atom-representation-attribution/protocol.json` + V0 首行 + sha256sum 核对 |
| merged finalizer 16/16、ASR 11/629、BU 46/97、AU 272/629 | `p2b_execution_report_2026-08-05.md` §4、§6.1 |
| r1/r2/merged audit 重算数字 | 本次只读 python 计数（§1.4 表）；merged=base 2,718+追加 60 行经 query_hash 差分核实 |
| override-composition 产物过期（r1、08-03、265） | `results/strict-atom-representation-attribution/override-composition/override-composition.{json,md}` |
| 11 案例分析基于 r1 | `o6_attack_release_path_analysis_2026-08-05.md` §1 |
| Sandwiching 三轴占优点估计、三路径裁决 | `v17_number_replacement_impact_2026-08-05.md` §0-3、§3.4 |
| 配对统计基础设施含 sandwiching | `scripts/analyze_e78_capacity_matched_statistics.py` L23、L105-141 |
| 47 项测试、smoke 64/64 PASS | `test_strict_atom_representation_attribution.py`（47 个 test_ 函数）；`phase_c_smoke_and_launch_2026-08-05.md` |
| 时间线/轮次/既有排期 | `submission_war_plan_2026-08-03.md` §2、§4.10；`window_execution_decision_2026-08-04.md` §3 |

*本报告全部结论基于上述可读文件与只读计数；未对任何文件做写操作（本报告落盘除外），未触碰运行中进程，未读取变体结果指标。*
