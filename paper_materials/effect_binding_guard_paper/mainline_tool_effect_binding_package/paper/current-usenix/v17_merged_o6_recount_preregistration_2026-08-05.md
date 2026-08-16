# v17 merged 口径预注册（O6 recount 前置，先于任何重算执行）

- 预注册时间：2026-08-05T10:27:00Z（本地 18:27+08:00）
- 预注册人：experimental-researcher（D6，approved per recommendations_analysis §4.3 D6）
- 纪律声明：本文件在任何 v17 merged 重算数字产生之前写定并哈希固化。重算脚本只能实现
  本文定义的口径；若实现中发现口径歧义，必须停止、修订本文件（新时间戳、新哈希、
  新修订记录）后重跑，**严禁**按已见数字回填式调整口径。
- 本文件只使用**既有文档中的已知事实**（P2-b 报告的 9 案例集合、finalizer 通过时间、
  recommendations_analysis §1.4 的朴素计数表）设计口径；未读取任何待重算的统计结果。

## 1. 正源（唯一数据来源）

- merged 目录（protocol-frozen、finalizer 16/16 通过）：
  `experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/recovery-normalization-qwen32-full-allow-with-trail-v17-726-r2-context-repaired/`
  （finalizer-passed.json finalized_at 2026-08-05T02:58:34Z；merge_manifest plan_hash
  `6dff8183ad3cd1d2eba009225b1835b8313b00d85af8dd257318473059b5adaf`；
  merged_plan_cache_sha256 `ea881cfc…28d`，与冻结协议 frozen-common-plan-cache 一致）。
- base 目录与各 repair stage 目录由 merge_manifest 的 `base_run_root` / `stage_roots` 解析；
  三者均只读。
- 审计文件：各目录下的 `runtime_audit.jsonl`；案例日志：merged 目录
  `agentdojo_logs/local-ours_e77_effect_diff_runtime/`。

## 2. 口径 C1：case-bound 绑定（unified_case_id）

1. **unified_case_id 定义**：官方案例键
   `case_key = suite:user_task_id:attack_type:injection_task_id`（benign 案例 attack_type 与
   injection 均为 `none`）。全宇宙 U = merged agentdojo_logs 中满足官方行过滤
   （context-repair-v17.py::is_official_case_payload 语义：四官方 suite；benign 或
   important_instructions；排除 `injection_task_*` 命名的辅助 injection-utility 日志）的
   恰好 726 个案例。
2. **审计行绑定**（audit 行本身只携带 user-task 级 query_hash，不携带 injection 信息，
   因此绑定必须经由"区段 + 段 + 执行序"三级完成）：
   - **区段（section）**：merged `runtime_audit.jsonl` 必须与
     `base 审计 + stage1 审计 + stage2 审计 + stage3 审计` 的按序字节拼接完全一致
     （脚本逐字节验证；失败即整体作废）。区段按拼接顺序编号 S0(base)/S1/S2/S3。
   - **段（segment）**：区段内每个 `task_plan` 事件开启一个新段；段携带该区段内其后继的
     全部事件行直到下一个 `task_plan`。区段首个 `task_plan` 之前的行（若有）为孤儿行，
     单列报告、不计入任何统计。
   - **段 → 案例绑定**：
     - query_hash 映射：对 U 中每个案例日志重算 query_hash = sha256(首条 user 消息文本)
       （override-composition-measurement.py::build_suite_map 的同一构造）。
     - S0（base）：同一 query_hash 的段按审计内出现顺序，绑定到该 query_hash 对应的案例
       集合按案例日志 `evaluation_timestamp` 升序的序列；**要求时间戳严格递增且段数与案例
       文件数相等**，否则该 query_hash 组 fail-closed（不出统计、报告错误）。
     - S1–S3（stage）：**先将段按 query_hash 归属分类**——query_hash 不属于 U 中任何
       案例的段为辅助段（non_official），从绑定序列中移除；剩余官方段的期望执行序 =
       该 stage `protocol_manifest.json` 的 `rerun_groups` 列表顺序 ×（attack 组内按列出
       的 injection_task 顺序；benign 组单案例），逐段按序绑定并要求 query_hash 与对应
       案例一致；官方段数与期望序不等即 fail-closed。辅助段的数量与 query_hash 只报告、
       不计数、不参与任何绑定。
     - query_hash 不属于 U 中任何案例的段（辅助 injection-utility 评估）标为
       `non_official`，永不计数，只报告。**结构性依据（修订 A1）**：runtime patch
       （agentdojo_e77_runtime_patch.py L417-442）在每次 pipeline 评估的首个 tool call
       时（state 无 plan_initialized）恰发射一个 task_plan 事件；AgentDojo 对 attack 案例
       另触发独立的 injection-utility 评估（query 为 injection 文本），其 task_plan 的
       query_hash 与任何官方案例的首条 user 消息哈希均不同，故辅助段可按 query_hash
       成员关系无歧义识别。base 区段同一机制成立（726 官方案例评估 + 若干辅助评估，
       每评估恰一个 task_plan 段）。
   - 绑定正确性只需对**含截断案例的 query_hash 组**（workspace u35、u38）强制成立；
     其余组若段数与案例数不一致仅记警告（其全部 base 行无论归属均保留，不影响计数）。

## 3. 口径 C2：截断原始行剔除（repair 行替代）

1. 截断案例集 T = merge_manifest `selected_rows` 的 9 个 case_key（P2-b detect 枚举、
   与本政策同源的检测规则；T 的成员与逐案例 stage/window/KV 选择**全部取自
   merge_manifest**，重算不再自行判定）。
2. 保留集规则（对 precommit_check 行）：
   - 案例 c ∉ T：保留 S0 中绑定到 c 的全部行；
   - 案例 c ∈ T：仅保留 c 的**选定 stage**（selected_rows 的 stage_root）区段中绑定到 c
     的段的全部行；c 在 S0 的段标 `excluded_original_truncated`（取证保留在文件内，不计数）；
     c 在非选定 stage 的段标 `excluded_superseded_stage`（仍截断/被取代的中间尝试，不计数）。
   - `non_official` 段与孤儿行永不计数。
3. 完整性核对（必须全过，否则不出统计）：
   - 保留行数 = S0 precommit 总数 − Σ(T 案例 S0 段行数) − Σ(辅助段 precommit 行数)
     + Σ(stage precommit 行数) − Σ(非选定 stage 段行数) − Σ(stage 辅助段 precommit 行数)
     （两侧独立计算互验；辅助段 = non_official 段，见 C1.2 修订 A1）；
   - 每个 c ∈ T 恰有一个保留段；U 中每个案例的保留行来自唯一区段；
   - 保留行中 effective=ALLOW 与 execution_attempted 的 reconciliation 违例为 0
     （沿用 override-composition 脚本的两类 reconciliation 定义）。

## 4. 口径 C3：override commit 与 diagnostic flag 双口径（不得混用）

对保留的每一条 precommit_check 行（字段语义同 e77_runtime.py apply_uncertainty_policy 与
override-composition-measurement.py）：

1. **effective decision** := `decision`；**strict decision** := `guard_decision`；
   strict 布尔 := `strict_authorization_satisfied`（必须与 guard_decision=="ALLOW" 一致，
   违例计数必须为 0）。
2. **override commit（259 类口径）**：`decision=="ALLOW" 且 guard_decision!="ALLOW"`。
   其中"实际执行"子集 := 再加 `execution_attempted==true`。主文引用的
   "strict-non-ALLOW→ALLOW 实际 override" 数字 = **该执行子集**；两个数（commit 总数、
   执行子集）分开报告。
3. **diagnostic flag 口径**：`diagnostic_uncertainty_override==true` 的行数，另分
   guard==ALLOW（flag 但 strict 未变）与 guard!=ALLOW 两个子计数。
   flag 口径与 commit 口径**分别报告，永不互换或合并**（flag 在 strict-ALLOW 行也会置
   True，语义不同，见 override_composition_measurement §3.1）。
4. **override 结构分解**：commit 行中 `atom_checks` 非空 = structured，空 = fallback；
   五类权限扩张 token（forbidden_field_used / outside_exact_plan / tool_not_in /
   missing_e77 / revision_binding_invalid）出现在 commit 行 FINAL 证据（reasons +
   atom_checks.check_result）中的计数必须为 0（merged finalizer 新红旗门的独立复核）。
5. **三分层（执行分层表）**：
   - strict execution := guard_decision=="ALLOW" 且 execution_attempted==true；
   - override execution := override commit 且 execution_attempted==true；
   - blocked / no execution := execution_attempted==false 的其余行。
   三者必须构成保留行的一个划分（和 = 保留总数），并报告
   effective=ALLOW 但 execution_attempted=false 的行数（若存在须解释，不得静默）。

## 5. 报告指标清单（重算脚本必须输出的完整集合）

- 保留 precommit 总数、 excluded 各类计数（original_truncated / superseded_stage /
  non_official / orphan）与逐案例明细（T 的 9 案例）；
- effective decision 分布（ALLOW/DENY/NEEDS_REPLAN/其他）；
- guard decision 分布；strict_authorization_satisfied true/false；strict×effective 交叉表；
- override commit 总数与执行子集、structured/fallback、按 guard decision 分解；
- diagnostic flag 三计数；五类 token 违例计数；reconciliation 违例计数；
- 三分层计数与划分核对；
- 与《建议》§3.3（2,217/83/407；1,958/749；259；455）及 recommendations_analysis §1.4
  merged 朴素计数（2,778；2,275/91/412；2,000/778；275；481）的逐项差异表
  （差异仅作解释，不作口径回调依据）；
- 全部输入文件 sha256（merged/base/stage 审计、merge_manifest、finalizer-passed）与本
  预注册文件 sha256。

## 6. 产物与弃用

- 重算产物：`experiments/security-analysis-ablation-and-overhead/results/strict-atom-representation-attribution/merged-o6-recount/`
  下 JSON + MD；报告：`paper/current-usenix/v17_merged_o6_recount_2026-08-05.md`。
- 弃用：`results/strict-atom-representation-attribution/override-composition/override-composition.{json,md}`
  （2026-08-03、基于 r1 部分快照、265 overrides、自标 preliminary）自本报告起不得被正文引用；
  其"2 行 outside_exact_plan 违例"已由 merged finalizer 新红旗门确认为 0。
  旧产物文件本体不做任何改动（以本报告为弃用凭据）。

## 7. 修订记录

### 修订 A1（2026-08-05T13:05:00Z，本地 21:05+08:00）

- **动机**：重算脚本首次运行在 stage1 绑定处 fail-closed（14 段 vs 期望 9 案例）。
  结构排查（只读，不涉及任何统计结果）确认：`task_plan` 事件由 runtime patch 在每次
  pipeline 评估（state 无 `plan_initialized`）时恰发射一次；AgentDojo 对 attack 案例
  额外触发独立 injection-utility 评估，这些评估也发射 `task_plan`，其 query_hash 为
  injection 文本的哈希，不属于任何官方案例。三个 stage 审计的 task_plan 数分别为
  14/5/2，其中官方段恰为 9/3/1（与各自 rerun_groups 完全一致），辅助段 5/2/1。
  原 C1.2 条文在"stage 绑定段数核对前是否先移除辅助段"上存在歧义（实现按全段数
  核对执行），现予以澄清。
- **变更前文本**（C1.2 stage 子条）：
  > S1–S3（stage）：段的期望执行序 = 该 stage `protocol_manifest.json` 的
  > `rerun_groups` 列表顺序 ×（attack 组内按列出的 injection_task 顺序；benign 组
  > 单案例），逐段按序绑定并要求 query_hash 与对应案例一致；段数不等即 fail-closed。
- **变更内容**：stage 绑定先按 query_hash 成员关系将辅助段（non_official）移出绑定
  序列，再对官方段做"段数相等 + 顺序 + query_hash 一致"三重核对；辅助段只报告。
  口径的统计含义不变（辅助段在任何版本下均不计数），仅消除绑定的歧义。
- **作废声明**：本修订前重算脚本曾于 stage1 绑定处 fail-closed，未产生任何统计
  数字，无需作废产物。
- **修订后文件 sha256**：见下方固化行。



### 修订 A2（2026-08-05T13:30:00Z，本地 21:30+08:00）

- **动机**：A1 修订后重算在保留算术互验处 fail（2,746 expected vs 2,657 retained，
  差 89）。结构排查（只读）确认差额 = base 辅助段 precommit 行数 75 + stage 辅助段
  precommit 行数 14（stage1/2/3 分别 9/3/2）。原 C2.3 保留算术公式未显式扣除辅助段
  行数，与"non_official 段永不计数"（C1.2/C2.2）不自洽，现修正公式。
- **变更前文本**（C2.3 第一条）：
  > 保留行数 = S0 precommit 总数 − Σ(T 案例 S0 段行数) + Σ(stage precommit 行数) −
  > Σ(非选定 stage 段行数)（两侧独立计算互验）；
- **变更内容**：公式两侧各扣除辅助段（non_official）precommit 行数；统计含义不变
  （辅助段在 A1 口径下本就不计数，本修订仅使互验公式与口径自洽）。
- **作废声明**：A2 之前脚本因互验失败未输出任何统计数字（无产物），无需作废。


<!-- pinned sha256 after amendment A2: 2046eebe313dc0b9f32d2dddde8feb59379d4ae1262238f928c082b548439886 -->
