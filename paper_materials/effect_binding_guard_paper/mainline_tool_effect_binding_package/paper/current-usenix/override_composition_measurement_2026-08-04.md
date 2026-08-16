# Override 构成测量（T2/O6 前置，初步结果）

日期：2026-08-04
产出：research-assistant。配套 T2 O6 命题草稿（`t2_o6_proposition_draft_2026-08-04.md`）
与决策书 `window_execution_decision_2026-08-04.md` §2b 必要条件 2。

## 1. 结论先行

1. **fallback 占比初步测量：0.000**（部分 v17 快照：265 次 override 全部走结构化路径，
   fallback 0 次）。低于决策书 §2b 的 20% 阈值——条件 (S2) 目前**不**要求把 O6
   限定于结构化路径。此为初步值：v17 未完成，finalize 后必须用同一脚本复测。
2. **红旗发现**：2 行 override 的最终 reasons/checks 携带扩权发现
   `outside_exact_plan`（审计行 1097/1106），机制为 `field_decisions` 多值字段
   后值覆盖（e77_runtime.py L188-212）。在处置前，O6 的 (O6-a) 对多值字段不成立。
   详细机制与处置选项见 O6 草稿 §4.3。
3. 五类扩权发现的其余阻断行为在快照内符合预期：`forbidden_field_used` 72 行
   全部止于 DENY/NEEDS_REPLAN；`tool_not_in` 的 43 个最终 ALLOW 全部属
   PLANNER_REPLAN_APPLIED 恢复路径（发现已被 plan 修订解决并重验，非策略层放行）。
4. reconciliation violations = 0；`strict_authorization_satisfied` 与
   `guard_decision` 无矛盾行。

## 2. 脚本位置与理由

脚本：`experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/override-composition-measurement.py`

选址理由：
- 该测量是 V0-V3 协议（§7.2 override rate、§6 `n_uncertainty_override`、
  §13 输出第 4 条）与 T2/O6 前置核实共用的度量，协议 §8 已把
  `scripts/strict-atom-representation-attribution/` 定为该协议脚本目录
  （`build-protocol.py` 已在其中）；
- 替代选址 `experiments/intent-bound-runtime-guard/scripts/effect-difference-runtime-guard/`
  更靠近数据，但该目录存放的是运行器（会写运行产物），把只读分析脚本与协议侧
  归档在一起更符合"测量服务于 O6 定理化与协议分流"的用途；
- 脚本为纯标准库、只读输入、输出写入独立 results 目录，不 import 任何 runtime
  模块，满足"不修改 runtime 源文件"红线。

输出：`experiments/security-analysis-ablation-and-overhead/results/strict-atom-representation-attribution/override-composition/{override-composition.json,override-composition.md}`（schema `override-composition/2`，含审计快照 SHA-256）。

运行方式（CPU，不启动 GPU；可重复运行，幂等覆盖自身输出）：

```bash
python3 experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/override-composition-measurement.py \
  [--audit <run>/runtime_audit.jsonl] \
  [--logs  <run>/agentdojo_logs] \
  [--out-dir <results dir>]
```

默认参数即 v17 运行目录；`--logs` 用于 query_hash→suite 映射（见 §3.3）。

## 3. 口径定义

### 3.1 override 判定

- **override（协议 §7.2 口径）**：`decision == ALLOW` 且 `guard_decision != ALLOW`
  （strict 非 ALLOW → effective ALLOW）。
- `diagnostic_uncertainty_override` 标志**不**直接用作分子：结构化分支对
  strict 已 ALLOW 的行也置 True（e77_runtime.py L209-211），快照内该标志
  True 的行中有相当部分 strict 本就是 ALLOW；脚本同时输出两种口径的交叉表
  （`override_flag_diagnostic`）供审计。

### 3.2 structured / fallback 判定

- structured：override 行 `atom_checks` 非空（逐字段 trail；对应策略函数
  结构化分支 L187-212）；fallback：`atom_checks` 为空（call-level reasons；
  分支 L213-234）。依据：审计 `atom_checks` 由 `descriptor_atom_checks`
  从比较记录的 `checks` 逐条生成（full_atom_runtime.py L338-358），
  空 checks ⇔ fallback 分支。

### 3.3 按 suite 分解

审计行只含 `query_hash`。脚本用 `agentdojo_logs/` 下每个 case 日志的
**首条 user 消息文本**重算 sha256（与 runtime 对 query 的哈希构造一致），
建立 query_hash→suite 映射（attack case 与同 user_task 的 benign case 共享
user 文本，suite 良定义）。映射失败计入 `unmapped_query_hash_prefixes`，
不猜测。

### 3.4 五类硬阻断的两层材料

- **final 材料**：`reasons`（策略后）+ `atom_checks.check_result`。override 行
  在此层出现五类 token = 违例候选（`o6_hard_block_violations_final`）。
- **initial 材料**：`initial_reasons`（recovery 前）。仅在此层出现 token 的
  override 行 = 发现已由 PLANNER_REPLAN 恢复路径解决、调用在修订 plan 下重验，
  非策略层放行；单独计数（`overrides_with_token_in_initial_reasons_only`）。

## 4. 初步测量结果（v17 部分快照，**非最终值**）

快照元数据：审计行读到 5471 行；不可解析行 0；快照 SHA-256
`ad49135aaecb9cafd8dc8f69d457cb768338f6660a6aaf9ff592f15b6fb48245`；
事件构成：precommit_check 2661、authorized_read_evidence 1425、task_plan 707、
call_revision_feedback 312、plan_revision 208、planner_replan 143。

### 4.1 override 总量与路径占比

| 指标 | 值（快照） |
|---|---:|
| pre-commit checks | 2661 |
| override 总数（协议 §7.2 口径） | 265 |
| 结构化路径 | 265 |
| fallback 路径 | 0 |
| **fallback 占比 φ** | **0.000**（阈值 0.20） |

### 4.2 按 suite 分解

| Suite | Overrides | Structured | Fallback |
|---|---:|---:|---:|
| banking | 30 | 30 | 0 |
| slack | 127 | 127 | 0 |
| travel | 14 | 14 | 0 |
| workspace | 94 | 94 | 0 |

（快照内无未映射 hash；suite 计数可能随 v17 后续 cases 变化。）

### 4.3 五类硬阻断计数

strict 非 ALLOW 且携带该发现的行（final 或 recovery 前材料）：

| 发现类 | 行数 | 这些行的 effective 判决 |
|---|---:|---|
| forbidden_field_used | 72 | DENY 32；NEEDS_REPLAN 40；无 ALLOW |
| outside_exact_plan | 96 | NEEDS_REPLAN 93；DENY 1；**ALLOW 2（违例，§4.4）** |
| tool_not_in | 152 | NEEDS_REPLAN 109；ALLOW 43（全部为恢复路径已解决，§4.4） |
| missing_e77 | 0 | — |
| revision_binding_invalid | 0 | — |

### 4.4 异常行定界

- **final 材料违例：2 行**（审计行 1097/1106，`send_email`，
  `recovery_state=CALL_REVISION_REQUIRED`）。两行均为同一调用模式：
  字段 `attachments` 两条 check，先 `outside_exact_plan`（值 'file'）后
  `matched_exact`（值 '19'）。机制：`field_decisions` 按字段名 dict 后值覆盖
  （e77_runtime.py L188-212）。**已按红线保持 runtime 源码不动，仅在此报告。**
- **initial-only：43 行**，`recovery_state` 全部为 `PLANNER_REPLAN_APPLIED`；
  对应 planner replan 恢复路径（patch L499-567）：发现先由 plan 修订解决，
  调用在修订 plan 下重新比较后才进入策略层，不计为策略层放行。

### 4.5 完整性

- `executed_without_allow`（effective 非 ALLOW 但 execution_attempted）：0；
- `strict_flag_mismatch`（strict_authorization_satisfied 与 guard_decision 矛盾）：0。

## 5. 对 O6 分流的含义（初步）

1. φ = 0.000 ≤ 20%：目前无需按 (S2) 把 O6 限定于结构化路径；finalize 复测后生效。
2. 违例 2 行 ≠ 0：O6 的 (O6-a) 在当前代码下对多值字段不成立，须先按 O6 草稿
   §4.3 的三选项处置（推荐：修复聚合为"最严格优先" + 受影响条件重跑）。
3. 在处置与 finalize 复测完成前，论文层面零承诺（决策书 §4 风险③红线）。

## 6. 局限

- v17 未完成：以上均为审计前缀快照，suite/计数会变化；快照哈希可追溯读取时点。
- suite 映射依赖 agentdojo_logs 已落盘的部分；未执行 case 的行无法映射
  （当前快照无此情况）。
- 本测量不评估 override 放行的 resolver_fill 值是否"应当"被放行（那是
  utility/over-permissiveness 问题，超出 O6 trail 完整性范畴）。
