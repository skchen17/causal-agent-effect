# 对称 context-repair 政策预注册：严格归因实验 V0–V3（context-repair-policy-v0v3）

- **政策 ID**：`ctx-repair-v0v3-2026-08-05`
- **预注册时间**：2026-08-05T10:20:00Z（本地 18:20+08:00）；哈希固化见同目录
  `context-repair-policy-v0v3.attestation.json`
- **机器可读正本**：`context-repair-policy-v0v3.json`（本 .md 为说明；冲突时以 JSON 为准，
  以 attestation 哈希为准）
- **依据**：《建议》§3.2 第 4 条；recommendations_analysis §1.5 / §4.3 D5；
  P2-b 执行先例（`p2b_execution_report_2026-08-05.md`）
- **执行智能体**：experimental-researcher（只读核查；本文件与 attestation 落盘除外）

## 0. 为什么现在落盘（时间约束）

v17 的 9 例 400 截断全部发生在 workspace `user_task_35`/`user_task_38`（长 context 任务），
案例顺序为 banking→slack→travel→workspace，即每个变体最后 ~280 个 case 才进入风险区。
V0（tool_identity_only）预计 08-06 凌晨到达 workspace。本政策在 V0 进入 workspace 前
预注册，保证 V0 的 workspace 行一旦出现截断签名，即按**事先固定**的规则处置，
杜绝"结果知情后调整规则"。落盘时点 V0 进度 ~233/726（slack/travel 段），
server 日志实际 HTTP 400 计数为 0。

## 1. 适用范围

- 实验：`strict_atom_representation_attribution`（protocol_id `bccf19ea51b13f27`，已冻结）。
- 四变体：`tool_identity_only`(V0) / `opaque_whole_call`(V1) / `raw_schema_fields`(V2) /
  `validated_atom_fields`(V3)，repeat-0，full scope 726 案例
  （`all-official-cases.jsonl` sha256 `c3442ecd…5d71`）。
- 运行目录：`experiments/security-analysis-ablation-and-overhead/runs/strict-atom-representation-attribution/qwen32/<variant>/repeat-0/`；
  server 日志：同目录树 `_server-repeat-0/llama_cpp_server.log`（每变体一次 server 启动，端口 18087）。
- 基础窗口 65536，tensor_split 0.5/0.5（runner 现状，与 P2-b 修复先例一致）。

## 2. 基础设施失败枚举定义（检测规则）

四类信号，语义逐字继承 v17 P2-b 先例与 `context-repair-v17.py` 的实现
（sha256 `a82198fc…d4a8`，预注册时点快照），仅路径/模式重映射到严格归因运行布局：

| 类别 | 信号 | 检测规则 | 角色 |
|---|---|---|---|
| F1 | HTTP 400 | server 日志正则 `HTTP/1\.1" 400`，**排除** "CUDA Graph id 400" 噪声（P2-b §1） | 佐证/触发排查；单独不构成枚举依据（需与案例执行窗口归因） |
| F2 | server log error | 5xx 访问行、`Traceback (most recent call last)`、`cudaMalloc failed` / `CUDA error` / `out of memory` | 触发只读排查；案例须由 F3/F4 确认损坏才入 T |
| F3 | post-tool empty assistant | 与 `context-repair-v17.py::has_post_tool_empty_assistant` 完全同义（tool 消息之后出现空化 assistant 消息；消息扁平化与 run_e75 相同） | **权威枚举信号**（案例级、确定性、不依赖日志归因） |
| F4 | case-level failure | case 日志 `error` 非空；或 paired 行 `run_completed=false`/`scorer_completed=false`；或变体完成后官方案例文件缺失（parse_case_log / completeness-check 语义） | **权威枚举信号** |

明确**不是**基础设施失败：NEEDS_REPLAN、DENY、低 utility、攻击成功——它们是实验结果，
永远不触发修复（《建议》§3.2-3："基础设施失败不得被记作安全成功"，反之亦然）。

F3 的机制依据：AgentDojo `local_llm.py` 的 `except Exception` 吞掉 400/context-length 异常并
返回空串 → case 日志无 error、`run_completed=true`、官方 scorer 照常打分 → 截断轨迹以
"干净行"身份进入统计（pm_process_review §1.4；v17 r1/r2 两次证实）。这正是必须预注册修复政策的原因。

**枚举定义**：变体 v 的失败集 `T_v = { 官方案例 c : F3(c) ∨ F4(c) }`，在变体 runner 退出且
completeness check 运行之后、任何统计计算之前检测。

## 3. 对称规则

**采用"逐变体独立枚举 + 逐字相同的政策参数"**，拒绝"先检测到的变体为准（并集 T）"：

1. 截断是否发生取决于轨迹长度，而轨迹长度受变体比较器影响（NEEDS_REPLAN/恢复分支不同），
   四变体的失败集**不保证相同**（v17 r1/r2 的同案例差异已表明边界案例行为不稳定）；
2. 若以并集强制修复在某变体下本已干净的案例，违反"只修枚举出的基础设施失败"；
3. 对称性定义在**政策层**：四变体使用逐字相同的检测规则、同一窗口阶梯、同一 stage 选择规则、
   同一 merge 规则、同一 claim boundary。同一案例出现在多个 T_v 中时，在每个受影响变体下
   以**相同参数**各修复一次；**禁止跨变体复用修复行**（比较器不同，行语义不可迁移）。
4. 一致性交叉核对（无歧义条款）：枚举后，T_v 中每个案例应能归因到其执行窗口内至少一条 F1
   400 行（paired-case-results 顺序 + duration）；无法归因或出现无 T_v 案例对应的 400 时，
   记入检测报告并在修复前人工复核；F3/F4 签名保持权威地位。

## 4. 窗口分级与修复执行

沿用 P2-b 先例（同硬件 2×RTX 4090 D、同模型、同基础窗口 65536）：

| stage | 窗口 | KV | tensor_split | 范围 |
|---|---|---|---|---|
| 1 | 73728 | f16 | 0.5/0.5 | T_v 全部案例 |
| 2 | 81920 | f16 | 0.5/0.5 | stage 1 后仍带 F3 签名/校验失败的残余案例 |
| 3 | 122880 | q8_0 | 0.5/0.5 | 残余案例（f16 在该窗口不可容纳，P2-b 先例） |

- 与基础运行的**唯一**已披露差异是 `n_ctx`（stage 3 另加 KV 量化）：严格归因 runner 本身
  使用 0.5/0.5 分片（不同于 v17 基础运行的 0.35/0.65），因此本实验的修复分歧面比 P2-b 更小。
- 修复端口 18088（实验用 18087）；**GPU 独占守卫**：`pgrep -f run-strict-attribution.py`
  与 `pgrep -f llama_cpp.server` 均为空才允许启动修复 server（v17 工具内置守卫只匹配 v17
  runner 模式，严格归因模式由 adapter 追加，见 §6）。
- 环境契约：修复重跑环境 = `run-strict-attribution.py::variant_env`，仅替换运行/审计/
  plan-cache 路径与端口；`STRICT_ATTRIB_VARIANT`、冻结输入哈希、temperature=0、
  benchmark v1.1.2、执行日期继承均不变。任何判定阈值、比较器、描述符、目录、scorer
  参数不得改变。
- **stage 3 后仍失败**：宣布该案例修复失败，保留原行、从官方统计中**显式剔除并披露**
  （不插补），报告用户；未经政策修订不得临时加第四窗口。
- 失败尝试（OOM/探活失败等）整体归档留证（P2-b 先例：两个归档目录）。

## 5. 取证、overlay manifest 与 claim boundary

- **原始行保留取证**：变体基础运行目录只读；merge 前后全目录 sha256 指纹 diff 必须为空；
  截断原始行留在基础目录，绝不删除或改写。
- **overlay**：硬链接 overlay 生成 `<variant>/repeat-0-context-repaired`；仅替换修复案例的
  case 日志；merged `runtime_audit.jsonl` = base 审计 + 各 stage 审计按序拼接；
  plan cache 按"repair 触碰键取 repair 条目、其余取 base 条目"合并（v17 工具语义）。
- **manifest 记录**：每 stage `protocol_manifest.json` + `repair_report.json`；merged 目录
  `merge_manifest.json`（selected_rows 逐案例 stage/window/kv/u/s/source_sha256、plan_hash、
  stage_roots、base 指纹、`original_artifacts_modified=false`、claim_boundary）。
- **claim boundary**：修复仅覆盖各变体枚举出的 T_v；一切正文数字（ASR/utility/decision
  分布/配对统计/H1–H5）只相对 merged 且 finalizer 通过的 artifact 陈述；修复案例逐案例披露
  窗口/KV/分片；不得用修复案例论证安全收益（除非未修复多数配对支持）。
- **变体验收**（merged 后、进入四变体 finalize 前）：726 case 日志齐全、T_v 外行与 base
  逐字节一致、merged 上 F3=0 且 F4=0、paired 行重推一致；全部通过后写 finalizer-passed 标记；
  最终 `finalize-strict-attribution.py --runs-base <merged runs base>` 照常跑全部门禁。

## 6. 与 context-repair-v17 工具链的衔接（子命令复用与参数映射）

| 子命令 | 复用内容 | 映射/适配 |
|---|---|---|
| `detect` | `detect_truncated_cases` / `has_post_tool_empty_assistant` / 官方行过滤，逐字复用 | `--run-root <variant repeat 目录>`；`--method local-ours_e77_effect_diff_runtime-strict_<variant>`；因严格归因运行目录无 `protocol_manifest.json`（`inspect_base_run` 会拒绝），经 adapter 调用检测函数，检测报告写 results/，不写运行目录 |
| `repair` | `server_command`（端口/窗口/KV 参数化）、`wait_for_server`（/v1/models 探活）、benchmark 命令形状、`validate_repaired_row`、repair_report | 环境不用 v17 的 `base_env_for_repair`，改用严格归因 `variant_env` 契约（§4）；`--tensor-split 0.5,0.5`、`--port 18088`；GPU 守卫追加 `run-strict-attribution.py` 模式 |
| `merge` | 硬链接 overlay、行替换、审计拼接、plan-cache 合并、plan_hash、merge_manifest、幂等门 | 内嵌的 v17 finalizer 调用**替换**为 §5 的变体验收 + `finalize-strict-attribution.py` |
| `selftest` | 全断言复用 | 任何实际修复执行前必须先通过（CPU-only） |

adapter（工作名 `strict-context-repair-adapter.py`，修复执行时在
`experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/`
创建）以库方式导入 `context-repair-v17` 与 `run-strict-attribution`，**不修改** v17 工具本体；
adapter 自身与全部被复用模块的 sha256 记入每个 manifest。若确需改动 v17 工具：必须政策修订
（新 policy_id）、仅限披露准确性/路径映射、selftest + §7 回测复验。

预注册时点代码快照哈希（防漂移）：
`run-strict-attribution.py` `6c110166…7d19`、`finalize-strict-attribution.py` `e9673cc9…2450`、
`check-variant-completeness.py` `d230fc6f…614d`、`agentdojo_representation_patch.py` `29ac74ff…fb11`。

## 7. 政策自检（预注册的回测义务）

在任何 V0–V3 修复执行前，用 **v17 r2 先例数据**（历史数据，ground truth 已知）回测本政策
检测规则，三项断言：

1. 对 r2 base 运行跑 F3 检测 → 必须恰好复现 P2-b §1 的 9 案例集合 T（u35×6 + u38×3）；
2. 对 r2 server 日志跑 F1 规则 → 非噪声 400 行恰为 9 条；
3. 对 r2 merged 运行跑 F3 检测 → 0 案例（修复有效性）。

回测产物归档于
`experiments/security-analysis-ablation-and-overhead/results/strict-atom-representation-attribution/context-repair-v0v3/policy-selfcheck/`。
回测只使用过去已完成、已分析的数据，不构成对 V0–V3 政策参数的结果知情调整。

## 8. 修订纪律

本政策一经 attestation 哈希固化即不可变。任何修订必须产生新政策文档 + 新 policy_id +
新 attestation，并说明修订动机；**严禁**在观察到 V0–V3 结果后回填式修改检测规则、
窗口阶梯或 claim boundary。
