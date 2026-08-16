# Whole-call envelope 注册规则（protocol v2 / D4 预注册）

- **规则版本**: `whole_call_exact_match_v2`
- **签发**: 2026-08-05（protocol v2 修订件 §3）
- **产物**: `whole-call-envelopes.json` + `.sha256`（本目录）
- **产物 sha256**: `702331d4a37cae77f93e96deb49024139e6a430d8d96369ed9ebdb25c5d5abf1`
- **实现**: `source/strict-atom-representation-attribution/whole_call_envelope.py`（投影）+
  `scripts/strict-atom-representation-attribution/build-whole-call-envelopes.py`（构建，`--check` 验证确定性）
- **消费方**: `agentdojo_representation_patch.py::_load_whole_call_envelopes`（仅 V1 变体；sidecar 哈希校验 fail-closed）

本文件是 V1 变体 whole-call authority 的**预注册规则**。规则一经签发即冻结；任何规则修改必须走新的 protocol 修订。

---

## 1. 输入（全部为已冻结产物，哈希固化）

| 输入 | sha256 | 用途 |
|---|---|---|
| `frozen-common-plan-cache.json` | `ea881cfc4495c599f50221ea10b5dd45e1ae1f61d0e1eee98a0600ef8a16528d` | 投影源（初始 authority） |
| `agentdojo_runtime_catalog.json` | `ec2e5dc3d2e52136a7f5d5294bb715e3aabc6c7dd159b87e426faf8f716c8468` | totalization 目录（static defaults / required / dynamic 字段） |
| `registered-effect-diff-descriptors.jsonl` | `dc9e16d87eefcf6ba54e71bc0e799b96eaaa062f6e22cfdf9db0616b6954e9e4` | 25 个注册 effectful/external 工具名单 |

## 2. 投影规则（逐条）

1. **条目筛选**：plan cache 共 445 entries；仅 `entry["plan"]` 为对象的 accepted plan（222 个）参与投影。revision 条目与 plan=null 条目不产生任何 authority。
2. **plan 键**：`plan_signature = sha256(json.dumps(plan, sort_keys=True, default=str))`。运行时 plan 是冻结缓存 JSON 的字节一致往返，故同一 plan 内容在投影侧与运行时比较侧哈希一致；运行时修订产生的新 plan 天然不在 registry 中。
3. **工具范围**：仅 25 个注册 effectful/external 工具；plan 中的其他工具不产生 whole-call authority（本次投影中 286 个 plan 工具项全部属于注册集合，skip 计数为 0）。
4. **binding 资格**（每个 plan 工具项，字段级判定）：
   - `exact`（≥1 值）：取值为候选值；多值取笛卡尔积，上限 `MAX_COMBINATIONS_PER_TOOL_PLAN = 64`，超限则该工具项不注册（防组合爆炸）；
   - `forbidden`：字段不出现在任何候选参数中（设置 forbidden 字段的调用永不命中）；
   - `resolve`：**阻断整个工具项注册**——whole-call 表示无法表达"运行时从授权证据解析取值"；
   - 非法 binding 结构或未知 mode：阻断（fail-closed）。
5. **totalization 门槛**：每个候选参数对象必须经与运行时**完全相同**的管线 totalize（`e77_runtime.totalize_registered_call` + 冻结 runtime catalog；static defaults 实例化、required 缺失/dynamic 未解析 → 不可注册）。运行时比较器收到的本来就是 totalized 参数，此门槛保证两侧签名可比。
6. **envelope**：`whole_call_signature = sha256(json.dumps({"tool_name": t, "args": totalized_args}, sort_keys=True, default=str))`——与运行时审计行的 `call_signature` 同一函数。重复签名去重。

## 3. Allow / Deny 语义

- **ALLOW**：totalized call 的签名 ∈ 当前 plan（`plan_signature`）下该工具的注册集合。
- **NEEDS_REPLAN（comparator 层，feedback opaque，`checks == []`）**：
  - `whole_call_outside_authorized_envelope`：签名未命中；
  - `whole_call_envelope_not_registered`：plan/工具无注册 envelope（含运行时修订 plan）；
  - `task_permission_plan_unavailable` / `tool_not_in_initial_permission_plan`：与 V0 逐字一致。
- **DENY**：whole-call comparator **永不产生**。DENY 仅经四变体共享的 revision-DENY 恢复路径可达（恢复机制跨变体一致，保证只隔离表示粒度一个因素）。
- **未注册调用**（25 工具之外的 effectful 调用）：在 comparator 之前的共享上游路径处理（`missing_e77_registered_descriptor` / `invalid_tool_precommit`），与 V0/V2/V3 相同。

## 4. 注册结果（预注册数字，产物 summary 逐字）

- cache entries 445；accepted plans 222；plan 工具项 286；
- 注册成功的工具项 43；注册 envelope（签名）50；含 ≥1 envelope 的 plan 42；
- 阻断原因计数（reason occurrences）：`resolve_bound_field_not_instantiable` = 468，`totalization_unresolved` = 49；skip = 0。
- 对照：plan cache 全部 874 个字段 bindings = 468 resolve + 266 forbidden + 140 exact。

## 5. Claim boundary（必须随结果一起报告）

1. envelope 只覆盖**冻结 plan cache 中可静态实例化**的调用形态；运行时修订 plan、resolve-bound 形态、组合超限形态、totalization 不可解析形态一律无 whole-call authority（fail-closed 到 NEEDS_REPLAN）。这是 whole-call 表示的固有表达能力边界，是本次归因实验要测量的对象本身，不是实现缺陷。
2. V1 的高 NEEDS_REPLAN / 低执行覆盖若出现，属预注册预期（protocol v2 §2.3），解释时必须同时报告 `allow_with_trail` 对 `checks == []` 的 fallback 行为。
3. 本 registry 不构成对任何未见调用形态的授权；exact-match 之外无任何泛化（无类型匹配、无前缀匹配、无 evidence 参与）。

## 6. 重建与校验（确定性）

```bash
cd <repo-root>
PYTHONPATH=code:. runs/e75_agentdojo_env/bin/python \
  experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/build-whole-call-envelopes.py --check
```

产物无墙钟字段；`--check` 对既有产物做字节级确定性重建比对（当前状态：PASS）。若需重建（仅在冻结输入变化且经 protocol 修订批准后）：去掉 `--check` 重写产物，随后必须更新 `protocol.json` hashes 表并再次走 protocol 修订流程。
