# v17 merged 口径重算报告（O6 recount，预注册口径 C1/C2/C3，修订 A1+A2 后执行）

- 执行时间：2026-08-05（UTC），experimental-researcher（D6）
- 预注册正本：`paper/current-usenix/v17_merged_o6_recount_preregistration_2026-08-05.md`
  - 初版 sha256 `a0e15986…f21e`（2026-08-05T10:27Z，先于任何重算）
  - 修订 A1（stage 绑定前剔除辅助段）+ A2（保留算术公式扣除辅助段）后最终
    sha256 `3e31501496a221cc4c00464cc45283ce5b014a27789c2e690354598b445d3359`
  - **顺序合规**：口径先哈希固化，脚本拒绝运行于哈希不符的预注册之上；两次修订
    均发生在任何统计数字产生之前（两次 fail 均为绑定/算术互验失败，无数字产物），
    修订只消除结构歧义、不改变计数语义（见预注册 §7 作废声明）。
- 重算脚本：`experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/v17-merged-o6-recount.py`
- 机器可读产物：`experiments/security-analysis-ablation-and-overhead/results/strict-atom-representation-attribution/merged-o6-recount/v17-merged-o6-recount.json`
- 数据正源（只读）：merged 目录
  `experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/recovery-normalization-qwen32-full-allow-with-trail-v17-726-r2-context-repaired/`
  （finalizer 16/16 通过，finalized_at 2026-08-05T02:58:34Z）

## 1. 口径定义（摘要，以预注册文件为权威）

- **C1 case-bound 绑定**：审计行经"区段（merged = base+stage1+2+3 字节拼接，逐字节
  验证通过）→ 段（每次 pipeline 评估恰一个 `task_plan` 开启一段）→ 执行序
  （base：同 query_hash 组按 evaluation_timestamp 序；stage：rerun_groups 序）"
  绑定到 726 官方案例的 unified_case_id。辅助 injection-utility 评估段
  （query_hash 不属于任何官方案例）标 `non_official`，只报告、永不计数（修订 A1）。
- **C2 截断剔除**：T = merge_manifest `selected_rows` 的 9 案例（u35×6、u38×3）。
  T 案例在 base 的段标 `excluded_original_truncated`（取证保留、不计数），仅其
  **选定 stage** 的段计入；非选定 stage 段标 `excluded_superseded_stage`。
- **C3 双口径**：override commit = `decision==ALLOW ∧ guard_decision!=ALLOW`
  （执行子集再加 `execution_attempted`）；diagnostic flag =
  `diagnostic_uncertainty_override==true`。两口径分报，永不混用。

## 2. 完整性门（全部通过才出统计）

| 门 | 结果 |
|---|---|
| merged = base+S1+S2+S3 字节拼接 | ✅ 5610+95+30+13 行 |
| 官方案例宇宙 = 726 | ✅（benign 97 + attack 629） |
| base 绑定（T 组 fail-closed 强制） | ✅ u35/u38 组段数=案例数、时间戳严格递增 |
| stage 绑定（官方段 9/3/1 = rerun_groups） | ✅ 辅助段 5/2/1 只报告 |
| 保留算术互验（修订 A2 公式） | ✅ 2718−19−75 + 60−13−14 = 2657 |
| reconciliation 违例（strict 布尔一致 / 无 ALLOW 未执行） | ✅ 0 |
| 五类权限扩张 token 违例 | ✅ 0 |
| 三分层构成保留行划分 | ✅ 1921+259+477 = 2657 |
| 孤儿行 | ✅ 0 |

剔除明细：excluded_original_truncated=19，excluded_superseded_stage=13，
non_official 段行数=89（base 75 + stage 14），orphan=0。

T 案例逐例（base 剔除行 → 选定 stage 保留行）：
u35 inj1 2→4(S1)、u35 inj2 3→2(S2)、u35 inj3 2→2(S1)、u35 inj4 2→6(S2)、
u35 inj5 2→4(S1)、u35 benign 2→5(S1)、u38 inj1 2→2(S1)、u38 inj4 2→4(S3)、
u38 inj5 2→4(S1)。每案例恰一个保留段 ✅。

## 3. 重算结果表（保留行 = 2,657 条 precommit_check）

| 指标 | 数值 |
|---|---|
| effective decision | ALLOW 2,180 / DENY 83 / NEEDS_REPLAN 394 |
| guard decision | ALLOW 1,921 / DENY 83 / NEEDS_REPLAN 653 |
| strict_authorization_satisfied | true 1,921 / false 736（与 guard==ALLOW 完全一致） |
| strict×effective 交叉 | ALLOW→ALLOW 1,921；DENY→DENY 83；NEEDS_REPLAN→ALLOW 259；NEEDS_REPLAN→NEEDS_REPLAN 394 |
| **override commit 总数** | **259**（全部 guard=NEEDS_REPLAN） |
| override commit 执行子集 | **259**（commit ⇒ 执行，无未执行 commit） |
| override 结构 | structured 259 / fallback 0 |
| 五类 token 违例 | 0 |
| **diagnostic flag** | **439**（strict-ALLOW 子计数 180 + strict-non-ALLOW 259；flag 与 commit 分报，不互换） |
| 三分层 | strict execution 1,921 / override execution 259 / blocked 477（= 2,657） |
| effective=ALLOW 且未执行 | 0 |

## 4. 与《建议》§3.3 及朴素 merged 计数的差异

| 指标 | 口径重算 | 《建议》§3.3 | Δ | 朴素 merged | Δ |
|---|---|---|---|---|---|
| precommit 总数 | 2,657 | 2,707 | −50 | 2,778 | −121 |
| effective ALLOW | 2,180 | 2,217 | −37 | 2,275 | −95 |
| effective DENY | 83 | 83 | 0 | 91 | −8 |
| effective NEEDS_REPLAN | 394 | 407 | −13 | 412 | −18 |
| strict true / false | 1,921 / 736 | 1,958 / 749 | −37 / −13 | 2,000 / 778 | −79 / −42 |
| override commit（执行） | **259** | **259** | **0** | 275 | −16 |
| diagnostic flag | 439 | 455 | −16 | 481 | −42 |

**差异解释（只读推导，非口径回调）**：
1. 朴素 2,778 → 口径重算 2,657 的全部差额 −121 = 辅助（injection-utility）段 89 +
   截断原始行 19 + 被取代 stage 行 13（与保留算术互验同源）。
2. **《建议》2,707 的口径已精确识别**：merged 审计中 query_hash ∈ 97 个官方案例
   query_hash 集合的 precommit 行恰为 2,707（独立复算验证；2,778−2,707=71 即
   query_hash 非官方的辅助评估行）。这是 v17 finalizer `official_audit` 的
   qhash 行级过滤口径：**剔除了辅助行，但未做案例绑定、未剔截断原始行与被取代
   stage 行**，且保留了 18 条"位于辅助段内但携带官方 query_hash"的行。
3. 2,707 → 2,657 的差额 −50 精确分解为：截断案例 base 原始行 19 + 被取代 stage
   行 13 + 辅助段内携带官方 qhash 的行 18（19+13+18=50，与剔除明细完全对账）。
4. **核心安全数字完全复现**：override commit 执行子集 = 259，与《建议》§3.3 完全
   一致（Δ=0），全部 guard=NEEDS_REPLAN、全部 structured、全部实际执行、零 token
   违例。《建议》的 259 正是"案例绑定 + 剔截断口径下 strict-non-ALLOW→ALLOW 实际
   override"；DENY 83 亦精确复现（Δ=0）。
5. ALLOW/NEEDS_REPLAN/strict/flag 的差额（−37/−13/−37/−13/−16）全部来自被剔除的
   50 行的分布（截断原始行与被取代行的 decision 分布 + 18 条官方 qhash 辅助行），
   方向一致、无异常符号；diagnostic flag 439 与 commit 259 的差（180）为
   strict-ALLOW 行上的置位 flag，语义不同，分报不混用。
6. 结论形态：《建议》§3.3 的 2,707/2,217/1,958/455 是 qhash 行级过滤的中间口径；
   本报告 2,657 是完整 case-bound 绑定 + 截断剔除 + 辅助段全剔除的终口径。
   **正文引用应以本报告 §3 表为准**；259 与 83 两数在两个口径下不变，可直接沿用。

## 5. 旧产物弃用

`results/strict-atom-representation-attribution/override-composition/override-composition.{json,md}`
（2026-08-03，基于 r1 部分快照，265 overrides，自标 preliminary）自本报告起**弃用**，
不得被正文引用；其"2 行 outside_exact_plan 违例"已由 merged finalizer 新红旗门与
本报告五类 token 门双重确认为 0。旧文件本体不动，以本报告与预注册 §6 为弃用凭据。

## 6. 脚本放置理由

脚本置于 `experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/`：
(1) 与同测量族的 `override-composition-measurement.py`（本脚本继承其 reconciliation
定义与 query_hash 构造）同目录；(2) 本实验树的结果目录约定在
`security-analysis-ablation-and-overhead/results/` 下；(3) `context-repair-v17` 目录
属于 intent-bound-runtime-guard 实验树的修复工具链，重算是其下游测量而非修复步骤。

## 7. 复现方式

```bash
python3 experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/v17-merged-o6-recount.py
```

脚本内置预注册哈希门（文件被改动即拒绝运行）、字节拼接验证、绑定 fail-closed、
保留算术互验；仅标准库、只读、CPU、无网络。退出码 0 且输出 `integrity_ok=true`
即所有完整性门通过。
