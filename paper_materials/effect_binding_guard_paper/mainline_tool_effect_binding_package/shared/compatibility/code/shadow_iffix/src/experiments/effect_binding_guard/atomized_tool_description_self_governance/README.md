# Atomized Tool Description Self-Governance

本实验检验经过反事实验证的 effect atom 描述是否能直接改善 LLM 自身的工具调用决策，而不把安全收益全部归因于确定性 guard 的拒绝行为。

一个桥接基线和五个内部比较条件保持模型、AgentDojo 任务、工具能力和评分器一致；A--E 还共享结构化 effect forecast 指令：

- `a0_pristine`：原始 AgentDojo no-guard，不增加 forecast 指令，用于连接既有基线。
- `a_raw`：原始工具描述，不增加 atom 信息，不启用 guard。
- `b_neutral`：增加长度相近的 schema/参数说明，不提供 effect 分解，不启用 guard。
- `c_unvalidated_atoms`：加入 E76 第一轮 LLM atom 提议，但不使用 E77 source-executed 验证结果，不启用 guard。
- `d_validated_atoms`：加入 E77 反事实验证后的 effect kind、security fields 和字段角色，不启用 guard。
- `e_validated_atoms_guard`：模型看到与 D 相同的描述，同时启用 E77 `fail_closed` guard。

每次副作用工具调用前要求模型输出可见的结构化 `EFFECT_FORECAST`。该字段用于实验审计，不包含隐藏思维链，也不在 A--D 中阻止工具执行。E 条件的安全决定仍由确定性运行时作出。

Smoke 命令：

```bash
cd code && PYTHONPATH=. python -m \
  src.experiments.effect_binding_guard.atomized_tool_description_self_governance.run_pilot \
  --mode smoke
```

本实验仅执行 AgentDojo sandbox 工具，不产生真实外部副作用。Smoke/pilot 结果不能写成全 benchmark 结论。

## 解释边界

- A--D 只改变模型可见的工具表示，不阻止调用；因此它们用于回答 atom 表示本身是否改善模型决策。
- E 在 D 的同一描述上增加确定性 `fail_closed` guard，用于测量 mediation 的增量收益和恢复开销。
- `EFFECT_FORECAST` 是可审计输出，不是隐藏思维链。缺失或格式错误会计入 adoption 指标，但 A--D 不因此拒绝工具调用。
- E76 的 round-zero atom 仅作为未验证对照；E77 的 source-executed descriptor 才属于反事实验证条件。
- 未出现在副作用 descriptor registry 中的只读工具保留原始描述，不能被错误标记为“副作用未知”。

后续多套件实验协议见 `pilot_protocol.md`。在该协议完成前，不将 smoke 写成安全性或效用的总体结论。
