# CEG-Auth 方法设计：Graph 不是贡献，授权条件效果推断才是贡献

> 日期：2026-05-22  
> 状态：T75 方法设计文档 v1  
> 目标：把 CEG-Auth 从“用 graph 表示 trace”的弱新意，收敛为 label-hidden raw-trace realized-effect monitoring 与 action-level selective authorization 方法。

## 1. 核心定位

CEG-Auth 不能写成：

> We represent agent traces as graphs.

这不是足够新颖的贡献。Graph/provenance/trace representation 已是工业观测和安全研究中的自然选择。

CEG-Auth 应写成：

> CEG-Auth is a label-hidden raw-trace authorization monitor that constructs typed causal evidence graphs from execution telemetry, predicts realized effects with localized evidence and calibrated uncertainty, and applies a selective policy only over effects outside the task-authorized envelope.

中文：

> CEG-Auth 是一个面向 LLM agent tool use 的 label-hidden raw-trace 授权监控器。它把执行遥测构造成类型化因果证据图，从图中预测实际发生的 effects、定位证据子图并估计不确定性，最后只对未被任务授权的 effects 聚合风险，通过 ALLOW / DENY / ABSTAIN 做 action-level 决策。

## 2. 为什么 graph 合理但不是新意

事实：

- OpenTelemetry 已将 traces、metrics、logs 作为现代 observability 的标准遥测对象。
- W3C PROV 已将 provenance 建模为 entities、activities、agents 及其影响、生成、使用、派生等关系。
- AgentArmor 已将 LLM agent runtime traces 转换为 CFG/DFG/PDG 等 graph IR，并通过 type system 做安全策略检查。
- ARGUS 已构建 influence provenance graph，用于追踪 untrusted context 如何影响 agent decisions。

推论：

- Graph 是合理 representation，因为 agent trace 包含 file diff、HTTP request/response、DOM mutation、stdout/stderr、message receipt、identity context 等异构证据。
- Graph 有助于表达路径、数据流和局部证据子图。
- 但“graph representation”本身不是本文 novelty。CEG-Auth 的 novelty 必须落在 Auth-SafeInv 特定判断对象、label-hidden 输入约束、effect evidence localization、uncertainty calibration 和 selective action policy 上。

参考边界：

- OpenTelemetry: https://opentelemetry.io/docs/what-is-opentelemetry/
- W3C PROV Overview: https://www.w3.org/TR/prov-overview/
- W3C PROV-O: https://www.w3.org/TR/prov-o/
- AgentArmor: https://arxiv.org/abs/2508.01249
- ARGUS: https://arxiv.org/abs/2605.03378

## 3. Novelty Boundary

| 对比对象 | 已有工作判断对象 | CEG-Auth 判断对象 | 需要强调的差异 |
|---|---|---|---|
| AgentArmor | runtime trace as program; dependency-aware policy enforcement | raw execution evidence -> realized effects -> authorization-conditioned selective decision | CEG-Auth 不是泛化 PDG enforcement，而是 realized-effect inference + action-level selective authorization |
| ARGUS | untrusted context influence on decisions | execution evidence that an effect occurred and exceeded `A(c)` | ARGUS 更关心决策 provenance；CEG-Auth 更关心实际 effect 是否发生、是否越权 |
| AttriGuard / CausalArmor | why the tool call/action occurred; causal attribution to user intent or untrusted observation | what effects occurred after or during tool execution | CEG-Auth 不只归因 tool call，也验证 realized effect |
| ClawGuard | pre-action boundary rule satisfaction | sandbox/dry-run/runtime trace-grounded realized-effect verification | CEG-Auth 可作为 commit 前 dry-run verifier 或 runtime audit layer |
| OPA / policy-as-code | structured input -> policy decision | raw trace -> effect probabilities/evidence/uncertainty -> structured authorization input | CEG-Auth 的贡献在 effect evidence inference，不在 policy engine |

## 4. 方法定义

### 4.1 输入

```text
c: task context
A(c): authorized effect envelope
(a, S, x): tool action, surface form, arguments
t_raw: label-hidden raw execution trace
```

禁止输入字段：

- `verified_effects`
- `unauthorized_effects`
- `candidate_effect_present`
- `policy_decision`
- `effect_diff`
- any direct gold label or near-label field

允许输入字段：

- process exit code
- stdout/stderr
- file path and file diff
- HTTP request/response metadata
- provider response status and receipt id
- DOM diff / localStorage diff
- message recipient and delivery receipt if observed
- timestamp/span/call graph metadata
- tool arguments and sanitized task context

### 4.2 EventExtract

```text
EventExtract(t_raw) -> G_t = (V, E)
```

节点类型：

- `ToolCall`
- `ProcessEvent`
- `FileEntity`
- `FileDiff`
- `NetworkRequest`
- `NetworkResponse`
- `DOMNode`
- `DOMMutation`
- `StorageMutation`
- `MessageReceipt`
- `ProviderAck`
- `Identity`
- `TaskContext`

边类型：

- `caused`
- `used`
- `generated`
- `modified`
- `deleted`
- `sent_to`
- `received_from`
- `returned`
- `derived_from`
- `authorized_by`
- `unsupported_by`

注意：typed graph 可来自规则化 parser，也可来自 telemetry schema；但 parser 本身必须在训练/测试 split 外固定，不能按 test labels 调参。

### 4.3 EffectInfer

```text
EffectInfer(G_t, e) -> (p_e, R_e, u_e)
```

输出：

- `p_e`: effect `e` occurred 的概率。
- `R_e`: 支持该判断的 evidence subgraph 或 node/edge ids。
- `u_e`: uncertainty score，用于 selective policy。

候选模型：

- typed-edge GNN；
- graph transformer；
- path-feature logistic/GBDT baseline；
- rule parser + calibrated probabilistic wrapper；
- LLM-as-judge over graph serialization as a baseline, not main method.

必须有 ablation：

- graph vs flat raw-trace classifier；
- graph vs event-sequence transformer；
- typed edges vs untyped graph；
- with vs without evidence localization;
- with vs without uncertainty head;
- with vs without graph path features;
- against raw-status boundary and deterministic rules.

### 4.4 AuthCompare

```text
U(c) = {e | e notin A(c)}
risk_U = Aggregate({p_e, u_e | e in U(c)})
```

聚合方式候选：

- max unauthorized probability；
- noisy-OR over unauthorized effects；
- calibrated weighted sum by effect severity；
- conformal upper confidence bound.

主文必须说明：authorization decision 只对未被任务授权的 realized effects 聚合风险，不能把所有 effects 都当作 unsafe。

### 4.5 SelectivePolicy

```text
if risk_U >= tau_deny and uncertainty <= tau_uncertain:
    DENY
elif uncertainty > tau_uncertain or tau_review <= risk_U < tau_deny:
    ABSTAIN
else:
    ALLOW
```

ABSTAIN 后续处理必须具体化：

- human review；
- sandbox replay with stronger instrumentation；
- ask user for explicit permission；
- two-phase commit approval；
- policy-as-code checker after effect evidence extraction。

ABSTAIN 不是免费移除难例，必须报告：

- Abstain Rate；
- Selective Risk；
- Coverage；
- U-Allow at covered actions；
- FDeny at covered actions；
- utility cost。

## 5. Future-Constrained Shadow Execution

> 2026-05-31 更新：单纯 post-hoc runtime audit 不能阻断已经发生的 irreversible side effects。CEG-Auth 的更强系统位置应改为 **future-constrained shadow execution / trajectory-locked authorization**：先把任务授权和 agent 意图编译为未来轨迹约束，在影子环境中执行并验证 pending effects，再把验证通过的轨迹锁定为 replay plan，由非 LLM executor 在真实环境复放同一轨迹并在每个 side-effect boundary 做 guard。

### 5.1 核心判断

方案不能写成：

> sandbox 中安全，所以真实执行也安全。

应写成：

> The shadow trace is used to synthesize an executable future-trajectory constraint and a trace-locked replay plan. Real execution is allowed only when each mediated operation matches the locked plan and satisfies the authorization-derived constraints before commit.

中文：

> 影子执行不是安全性的直接证明，而是用来生成和验证未来轨迹约束 `F_c` 与 replay plan `pi`。真实执行阶段不再让 LLM 二次输出，而由受控 executor 按 `pi` 复放；每个可能产生副作用的操作必须先通过 `F_c`、资源绑定、参数绑定和 pending-effect 检查，才能进入 commit。

### 5.2 形式化对象

```text
c: user task and trusted task context
A(c): authorized effect envelope
I_c: agent intent / proposed plan under c
F_c: future trajectory constraint compiled from c, A(c), and I_c
tau_s: shadow execution trace
G_s: causal evidence graph extracted from tau_s
Omega_s: predicted pending realized effects in shadow
pi: trace-locked replay plan compiled from tau_s and F_c
sigma: substitution map from shadow placeholders to real values/resources
tau_r: real replay trace
Omega_r: observed pending effects during real replay
```

越权定义保持不变：

```text
Violation(c, tau) = 1 iff Omega(tau) \ A(c) != empty
```

新增轨迹约束目标：

```text
tau_s satisfies F_c
tau_r satisfies ReplayLock(pi, sigma)
forall prefixes tau_r[:t], tau_r[:t] satisfies F_c
CommittedEffects(tau_r) subseteq A(c)
```

### 5.3 `F_c` 应包含什么

`F_c` 不是自然语言计划，而是可执行约束。最低字段：

```text
allowed_effects
allowed_resources
allowed_endpoints / recipients / identities
allowed_tool_surfaces or equivalent execution primitives
forbidden_effects
data-flow constraints
parameter binding constraints
operation order / dependency constraints
effect budget and severity
commit preconditions
abstain / ask-user triggers
```

例子：

```text
Task: read billing_report.csv and compute total revenue locally.

A(c) = {
  file_content_read("billing_report.csv"),
  local_computation("revenue_sum")
}

F_c forbids:
  network_egress(*)
  external_data_upload(*)
  file_written(*) except optional explicitly authorized output path
  file_deleted(*)
  message_sent(*)
```

### 5.4 执行流程

```text
1. IntentToConstraint(c, A(c), I_c) -> F_c
2. ShadowExec(I_c, sandbox, F_c) -> tau_s
3. EventExtract(tau_s) -> G_s
4. EffectInfer(G_s) -> {(p_e, R_e, u_e)}
5. AuthCompare({p_e}, A(c), F_c) -> risk_U
6. SelectivePolicy(risk_U, uncertainty, evidence) -> ALLOW / DENY / ABSTAIN / ASK_USER
7. If ALLOW: CompileReplay(tau_s, F_c) -> pi
8. RealReplay(pi, sigma, runtime_guard) -> tau_r
9. PrefixGuard(tau_r[:t], F_c, pi, sigma) blocks deviations before side-effect commit
10. FinalCommitCheck(Omega_r, A(c)) -> COMMIT / ABORT / ABSTAIN
```

关键实现要求：

- LLM 在真实阶段不再生成新的 tool call 或命令。
- replay executor 只执行 `pi` 中被锁定的操作。
- `sigma` 只能替换资源句柄、真实路径、真实 endpoint、真实 token 等被 `F_c` 允许的值。
- 替换后必须重新检查参数绑定、资源身份、endpoint/recipient、data-flow 和 pending effects。
- 对不可逆操作必须采用 staging / dry-run / two-phase commit；无法 staged 的操作要先 `ABSTAIN/ASK_USER`。

### 5.5 阻断发生在哪个阶段

| 阶段 | 能否阻断真实副作用 | 阻断依据 | 边界 |
|---|---:|---|---|
| Pre-action text check | 能阻断部分 | task + proposed command/tool | 容易被 surface alias 绕过 |
| Shadow execution | 能阻断真实环境副作用 | sandbox trace + pending effects | sandbox 可能与真实环境分歧 |
| Trace-locked replay guard | 能在真实 commit 前阻断 | `pi`, `F_c`, prefix trace | 必须所有 side-effectful operations 都被 mediation |
| Final commit check | 能阻断 staged effects | `Omega_r subseteq A(c)` | 对已真实发送/删除的不可逆操作太晚 |
| Post-hoc audit only | 不能阻断 | historical trace | 只能用于审计/追责 |

因此主文应强调：CEG-Auth 的 prevention 版本依赖 shadow/staging/replay/guard；若部署成纯 runtime audit，只能检测，不能阻断。

### 5.6 条件性安全命题

可写成 proposition，不要写成 unconditional safety theorem。

**Proposition (conditional pre-commit authorization).** 给定任务 `c`、授权包络 `A(c)` 和未来轨迹约束 `F_c`。如果满足：

1. **Mediation**：所有可能产生安全相关 side effects 的操作都必须经过 runtime guard；
2. **Staging**：所有不可逆 side effects 在 commit 前都以 pending/staged 形式存在，或被替换为 dry-run/provider sandbox；
3. **Constraint soundness**：`AllowedEffects(F_c) subseteq A(c)`；
4. **Replay-lock soundness**：真实执行只能执行 `pi` 中被锁定且经 `sigma` 安全替换的操作；
5. **Prefix guard soundness**：任意真实执行前缀若违反 `F_c` 或 `pi`，则在该 side effect commit 前被阻断；
6. **Effect observability**：最终 commit check 能观测所有 pending security-relevant effects；

则任意被 commit 的真实执行满足：

```text
CommittedEffects(tau_r) subseteq A(c)
```

这不是模型层安全保证，而是系统层条件保证。若 `F_c` 过度宽松、工具绕过 mediation、真实环境产生未观测副作用、或 provider 不支持 dry-run/staging，则命题不适用。

### 5.7 与 AuthGraph 的区别

AuthGraph 的核心是把 clean authorization graph 与 injected execution provenance graph 进行结构对齐，重点在 parameter-source/tool-level deviation detection。

CEG-Auth / trajectory-locked version 应强调不同点：

- 判断对象：`realized effects outside A(c)`，不只是参数来源偏离；
- 时间位置：在真实 commit 前用 shadow trace 生成 `F_c` 和 `pi`；
- 执行机制：真实阶段不让 LLM 重新生成，而是 replay locked trace；
- 决策目标：action-level `U-Allow / FDeny / Abstain / Coverage`；
- 输出：effect probabilities、localized evidence、uncertainty、selective policy。

不能说 AuthGraph “有问题” 或 “被本文证明错误”。更稳妥的写法是：AuthGraph 和 CEG-Auth 解决相邻但不同的问题；AuthGraph 的 graph alignment 可作为 baseline 或 component，而本文补的是 future-trajectory-constrained realized-effect authorization。

### 5.8 必做实验

| ID | 实验 | 目的 | 主要指标 |
|---|---|---|---|
| E-FC1 | Constraint compiler accuracy | 检查 `c -> A(c), F_c` 是否过宽/过窄 | allowed precision/recall, forbidden recall, over-permissive rate, over-restrictive rate |
| E-FC2 | Shadow-real divergence | 检查 sandbox trace 和真实 replay 是否 effect-equivalent | trace divergence, effect divergence, deviation-blocked rate |
| E-FC3 | Pre-commit blocking | 证明越权副作用在真实 commit 前被阻断 | Unauthorized Committed Effect Rate, Pre-effect Block Rate, Task Success, FDeny, Abstain |
| E-FC4 | Held-out surface robustness | 检查同 effect 多 surface 下是否仍可阻断 | leave-one-surface U-Allow/FDeny/Abstain, row FNR/FPR |
| E-FC5 | Ablation | 证明不是单一组件或规则表在起作用 | without shadow / without replay lock / without guard / without uncertainty / AuthGraph-style baseline |
| E-FC6 | Efficiency | 量化 shadow + graph + replay 的成本 | latency overhead, trace size, guard overhead, human review rate |

高危测试场景：

```text
local financial analysis with hidden upload
HTTP status check with redirected full content download and file write
cleanup command expanding from *.tmp to broad rm
draft message accidentally sent
browser form submit with unauthorized recipient
shell/python alias for file delete/read/network egress
```

## 6. 实验协议

### 6.1 主结果设置

主结果必须使用：

- label-hidden raw trace；
- minimal-evidence trace；
- held-out tool family；
- held-out trace family；
- validation-selected threshold；
- action-level metrics。

full-label trace 只能作为 upper bound。

### 6.2 主指标

主表优先级：

1. Unauthorized Action Allow Rate, lower is better.
2. Authorized Action False Denial Rate, lower is better.
3. Abstain Rate / Coverage.
4. Selective Risk.
5. Row-level unauthorized-effect FNR and FPR as decomposition.

必须报告：

- N unauthorized actions；
- N authorized actions；
- exact binomial CI；
- bootstrap CI by trace group；
- threshold selection rule；
- seed variance for learned models。

### 6.3 必要 baseline

强 baseline：

- pre-action rule-only；
- provenance-only；
- raw-status boundary；
- deterministic effect rules；
- flat raw-trace classifier；
- event-sequence transformer；
- LLM-as-judge over trace text；
- graph without typed edges；
- graph without uncertainty；
- graph without evidence localization；
- all-allow；
- always-deny；
- row-threshold action aggregation from T73。

### 6.4 成功标准

CEG-Auth 才能作为主方法的最低标准：

- 在 label-hidden/minimal-evidence trace 上显著降低 U-Allow；
- FDeny 不再在 T61/T65 类 split 上等于 1.0；
- 不通过 all-allow threshold 满足 false-denial constraint；
- 相比 flat/event-sequence/raw-status boundary 有稳定优势或清晰互补性；
- evidence subgraph localization 能被人工审计，且不是 label field shortcut。

## 7. 主要风险与写作边界

风险：

- graph construction 过度手工规则化，会被视为 rule system；
- observability 不充分时无法恢复未记录 side effect；
- ABSTAIN 可能被认为逃避难例；
- provider/schema shortcut 可能仍存在；
- graph model 可能只记住工具族，而非 effect evidence。

写作边界：

- 不说 CEG-Auth 是首个 agent trace graph。
- 不说 graph 本身是贡献。
- 不说 post-hoc runtime audit 等于 prevention。
- 不把 full-label verifier 作为主结果。
- 不把 ABSTAIN 后的 covered-risk 当全体风险。

## 8. 论文贡献写法

建议贡献句：

1. We define Auth-SafeInv as an action-level evaluation target for authorization-conditioned realized-effect monitoring.
2. We show that row-level and full-label trace evaluations can overstate safety under held-out tool surfaces and label-hidden traces.
3. We propose CEG-Auth, a label-hidden causal evidence graph monitor that predicts realized effects with localized evidence and calibrated uncertainty.
4. We evaluate selective action policies using U-Allow, FDeny, Abstain Rate, Coverage, and Selective Risk.

不建议贡献句：

- We introduce graph-based agent trace monitoring.
- We are the first to use provenance graphs for agent safety.
- We solve tool-use safety with graph reasoning.
