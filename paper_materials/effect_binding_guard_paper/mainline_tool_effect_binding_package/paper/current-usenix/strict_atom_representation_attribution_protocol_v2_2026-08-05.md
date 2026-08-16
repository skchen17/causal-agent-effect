# 严格 Atom 表示归因实验执行协议 —— v2 修订件

- **修订 ID**: `protocol_v2_true_whole_call`
- **签发时间**: 2026-08-05T18:35:00Z
- **基线文档**: `strict_atom_representation_attribution_protocol_2026-08-03.md`（下称 v1 协议）
- **新 protocol_id**: `e830b9b24138f8ad` = `sha256(evaluation/strict-atom-representation-attribution/protocol.json)[:16]`（v2 文件字节）
- **被替代 protocol_id**: `bccf19ea51b13f27`（v1；归档为 `protocol-v1.json`，sha256 `bccf19ea51b13f27c12244c8c2805c53e6a6700247069732a90722c44dba0561`）
- **决策依据**: `recommendations_analysis_2026-08-05.md` §2（D1–D4/D7，已获用户确认）

本修订件是协议级变更。除下列明确列出的条款外，v1 协议其余条款全部保持有效。

---

## 1. 修订动机（观察到的事实）

1. v1 协议 §15 预先声明了风险条款："`opaque_whole_call` 需在实现评审中确认没有暗中复用 V3 的 per-field feedback；其 verdict 可由字段约束 conjunction 产生，但界面必须保持 call-level opaque。"
2. 2026-08-05 实现核实（`recommendations_analysis_2026-08-05.md` §2.1）：protocol v1 的 V1 实现 `agentdojo_representation_patch.py::_make_opaque_whole_call` 在 L163 **直接调用** `base_compare`（即 V3/E77 字段级比较器 `compare_call_to_plan_with_evidence`），再将其 ALLOW/非 ALLOW 塌缩为 call-level 标签。
3. 因此 v1 实现的 V1 条件在**内部**执行了完整的字段级授权比较：字段级 evidence grounding、per-field check 与字段约束 conjunction 全部参与了判决，只有输出界面是 opaque 的。这**不是**"whole-call 表示"，而是"字段级表示 + opaque 输出界面"。
4. 结论：在 v1 实现下，V1 与 V3 之间的差异无法归因于"表示粒度"这一个因素，V1 的因果归因无效。这是实现与协议意图的偏离，不是实验负结果。

## 2. V1 语义修订（方案 A：真 whole-call representation）

### 2.1 变更前（v1 协议 §4 V1 原文）

> - 将 totalized tool call 视为一个不可分的授权对象。
> - 先使用共同的 totalization、canonicalization 和 authorized-read resolver，把候选调用与 authority envelope 实例化；再将该工具的全部约束合并成一个 conjunction，最终只产生一次 call-level `match/mismatch`。
> - 不暴露哪个字段或哪个 effect 不匹配；replan feedback 只说 `whole_call_outside_authorized_envelope`。
> - evidence 可以参与 whole-call envelope 的实例化，但不产生 per-field authorization decision、per-target expansion 或 role-specific repair。
> - 用途：区分"检查整个调用"与"能独立授权多个效果字段"。

### 2.2 变更后（v2 V1 定义，正式文本）

**V1 `opaque_whole_call`（protocol v2，真 whole-call）**

1. 表示对象：totalized tool call 作为**不可分**授权对象。totalization 使用与其他三个变体完全相同的共享管线（v1 协议 §5 不变）。
2. 授权依据：**预注册 whole-call envelope 集合**——frozen common plan cache 的确定性 exact-match 投影（注册规则见 §3；落盘产物 `whole-call-envelopes.json` + `.sha256`）。
3. 比较逻辑：对 totalized call 生成不可分规范签名
   `whole_call_signature = sha256(json.dumps({"tool_name": t, "args": totalized_args}, sort_keys=True, default=str))`，
   与当前 plan（键 = `plan_signature`，同一规范序列化）下该工具的预注册签名集合做 **exact-match**。
4. 判决（comparator 层）：
   - `ALLOW`（reason `whole_call_within_authorized_envelope`）：签名命中注册集合；
   - `NEEDS_REPLAN`（reason `whole_call_outside_authorized_envelope`）：签名未命中；
   - `NEEDS_REPLAN`（reason `whole_call_envelope_not_registered`）：当前 plan/工具无注册 envelope（含 runtime 修订产生的新 plan——它们不在冻结缓存中）；
   - `NEEDS_REPLAN`（reasons `task_permission_plan_unavailable` / `tool_not_in_initial_permission_plan`）：与 V0 逐字相同，保证恢复分支跨变体一致；
   - **comparator 不产生 `DENY`**：match/mismatch 是二值的；DENY 只能经由四变体共享的 revision-DENY 恢复路径产生（恢复机制不变，只隔离表示粒度一个因素）。
5. 禁止事项：**不调用** V3/E77 字段级比较器；**不做**字段分解、per-field repair、per-target expansion；evidence resolver 输出**不参与** V1 判决；所有 V1 verdict 的 `checks == []`（界面 opaque，实现也 opaque）。
6. 运行时标签：`RUNTIME_VERSION = strict_representation_opaque_whole_call_v2`（仅 V1 升级；V0/V2/V3 保持 `_v1` 字节不变）。
7. 用途（不变）：区分"检查整个调用"与"能独立授权多个效果字段"。
8. 防退化门禁（v1 协议 §4 注意事项保留）：单元测试必须构造"工具在计划中但参数被替换"的调用，要求 V0 ALLOW、V1 非 ALLOW；并新增"V1 永不调用字段级比较器"与"签名跨实现字节一致"两项门禁。

### 2.3 预注册的科学后果（非缺陷，必须随结果一起报告）

- resolve-bound 字段使调用静态不可实例化 → 该 plan/tool 无 envelope → NEEDS_REPLAN。frozen cache 的 874 个字段 bindings 中 468 个为 resolve-bound（266 forbidden、140 exact），因此 V1 的低执行覆盖/高 NEEDS_REPLAN 是 whole-call 表示盲目性的**预期刻画**，属于 H4 报告内容。
- `allow_with_trail` 不确定性策略对 `checks == []` 的 NEEDS_REPLAN 不会 override（V1 reasons 不含 resolver_fill），因此部分调用仍会执行——报告 V1 时必须同时给出该机制。

## 3. Whole-call authority 注册规则（D4 预注册，摘要）

完整规则见 `evaluation/strict-atom-representation-attribution/whole-call-envelope-registration-rules.md`。要点：

- 输入：`frozen-common-plan-cache.json`（445 entries；仅 222 个 accepted plan 参与投影）+ 冻结 runtime catalog + 25 个注册 effectful/external 工具名单。
- 注册条件：plan 工具项的全部 binding 为 `exact`（≥1 值）或 `forbidden`；任何 `resolve` binding 阻断注册（whole-call 无法表达"运行时从授权证据解析取值"）。
- 多值 `exact` binding 取笛卡尔积（上限 64/工具项）；`forbidden` 字段不进候选。
- 每个候选经**同一 totalization 管线**实例化；不可 totalize 的候选不注册。
- envelope = totalized 参数的 `whole_call_signature`；registry 键 = `plan_signature`。
- **claim boundary**：envelope 只覆盖冻结 plan cache 中可静态实例化的调用形态；运行时修订 plan、resolve-bound 形态、未注册工具一律无 whole-call authority（fail-closed 到 NEEDS_REPLAN）。
- 产物哈希固化进 `protocol.json` hashes 表（`702331d4a37cae77f93e96deb49024139e6a430d8d96369ed9ebdb25c5d5abf1`），runner `verify_frozen_inputs` 在每个 case 运行前校验。

## 4. 受影响条款清单

| 条款 | 变更 |
|---|---|
| §4 V1 `opaque_whole_call` | 按 §2.2 重写（唯一语义变更） |
| §4 V0/V2/V3 | 不变（代码路径字节级不变，测试门禁保留） |
| §5 一致性系统部分 | 不变（totalization/canonicalization/recovery/policy 跨变体一致） |
| §6 运行记录 schema | 不变（`protocol_id` 字段语义不变；V0/V1-V3 取值不同，见 §5） |
| §9 Phase 2 | 触发：protocol 修订属"代码错误修复"，**四个条件全部重跑 smoke**（命令见 §6） |
| §9 Phase 3 | V1 在 smoke 通过后从 V1 起重串行；V0 结果保留（见 §5 血缘注记） |
| §15 第 2 条 | 关闭：实现评审已完成，结论为实现偏离协议意图；v2 以不可分签名 exact-match 取代 conjunction 实现 |

## 5. V0 血缘注记（不重跑 V0 的依据）

- V0 于 protocol v1 下启动（2026-08-05，PID 1448380 驱动），其 runner 进程在启动时已将 v1 protocol_id `bccf19ea51b13f27` 捕获于内存；全部 726 行将携带该 id（已核实首行一致）。
- protocol v2 **没有修改 V0 的任何代码路径**（`compare_tool_identity_only` 字节不变；envelope 加载仅当 `STRICT_ATTRIB_VARIANT=opaque_whole_call` 时触发；V0 运行时标签保持 `strict_representation_tool_identity_only_v1`）。
- 依据：V0 结果在 v1/v2 下语义与实现完全同一，重跑只改变墙钟与 RNG 无关的确定性输入之外的采样噪声，不改变协议合规性；以血缘注记替代重跑（节省约 9.5 GPU h）。若 finalize 的配对/完整性门禁对混合 protocol_id 报错，优先修 finalizer 记录规则而非重跑 V0，并在报告中披露。

## 6. 重启要求（与 D2 指引配套）

1. V0 完成（726 行）→ read-only completeness check（`check-variant-completeness.py --variant tool_identity_only`，rc=0）→ 按 `pause-after-v0.sh` 归档并终止驱动。
2. protocol v2 生效后，**四变体 smoke 全部重跑**（v1 协议 §9 Phase 2 要求；命令见 `pause-resume-runbook_2026-08-05.md`，不在本文件重复）。
3. smoke 通过后，从 **V1** 开始按 V1→V2→V3 顺序串行全量（driver v2：`run-v0v3-full-serial-driver-v2.sh`，V0 跳过）。

## 7. 变更记录（change log）

| 字段 | 值 |
|---|---|
| 时间戳 | 2026-08-05T18:35:00Z |
| 动机 | §1（v1 实现 V1 内部调用 V3 字段级比较器，表示粒度归因无效） |
| 变更前 V1 文本 | §2.1（v1 协议 §4 V1 原文，逐字引用） |
| 新 V1 文本 | §2.2（本文件为正式文本） |
| 受影响条款 | §4 表格 |
| 新 protocol_id | `e830b9b24138f8ad` |
| 新增冻结产物 | `whole-call-envelopes.json`（sha256 `702331d4...`，注册规则 `whole_call_exact_match_v2`） |
| 代码变更摘要 | `agentdojo_representation_patch.py`（V1 comparator 重写、envelope 加载 fail-closed、V1 runtime tag v2）；`variant_semantics.py`（V1 签名集合语义）；`run-strict-attribution.py`（新增 envelope env）；新增 `whole_call_envelope.py`、`build-whole-call-envelopes.py` |
| 测试 | `test_strict_atom_representation_attribution.py` 51 项全过（原 47 + 新增 4） |
