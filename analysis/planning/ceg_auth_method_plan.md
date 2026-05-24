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

## 5. 两阶段执行设定

为避免 post-hoc detection 太晚，CEG-Auth 最合理的系统位置是：

1. **Sandbox / dry-run phase**：在隔离环境执行 tool call，收集 raw trace 并构造 `G_t`。
2. **Selective authorization phase**：CEG-Auth 判断 ALLOW / DENY / ABSTAIN。
3. **Commit phase**：只有 ALLOW 才把 side effect commit 到真实环境；ABSTAIN 进入人工确认或更强 verifier。

如果只能 runtime audit，主文必须承认它不能阻止已经发生的 irreversible side effect。

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

