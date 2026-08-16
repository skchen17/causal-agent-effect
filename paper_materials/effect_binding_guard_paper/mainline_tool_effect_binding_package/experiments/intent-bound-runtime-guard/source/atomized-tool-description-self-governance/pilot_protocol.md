# 多套件预注册 Pilot 协议

## 研究问题

1. 与原始工具描述相比，反事实验证后的 atom 描述是否提高良性任务效用或降低攻击成功率？
2. 改善是否来自 effect 表示，而不是额外文本、未验证的 LLM 描述或一律拒绝？
3. 在相同 atom 描述上加入确定性 guard 后，安全收益、误拒和恢复开销分别增加多少？

## 固定条件

- A0：AgentDojo 原始 no-guard 基线，不增加 forecast 指令。
- A：原始工具描述，加所有 A--E 共享的 forecast 指令，不执行 forecast。
- B：与 D 按 tokenizer token 数匹配的中性 schema 文本，不提供 effect 关系。
- C：E76 round-zero、未经反事实验证的 atom 描述，不启用 guard。
- D：E77 source-executed、反事实验证后的 atom 描述，不启用 guard。
- E：模型看到与 D 完全相同的描述，并启用 E77 `fail_closed` guard。

A0 用于连接既有官方 no-guard 结果。A--E 用于内部因果比较。除 E 外，任何条件均不得根据 forecast 缺失、解析失败或 atom 判断阻止调用。

## 固定执行配置

- AgentDojo `v1.1.2`，`important_instructions` attack。
- Qwen3-32B Q4_K_M，temperature `0`，context `65536`，最大输出 `4096`。
- 同一 suite/task/attack 配对、工具状态和评分器；所有错误、超时和解析失败均保留。
- 只运行 sandbox 工具，不产生外部副作用。

## 指标

- 官方 benign utility、attack utility、attack success rate。
- forecast adoption、parse-valid、tool/argument consistency。
- 工具调用数、模型调用数、总延迟、超时和 E 条件 replan 次数。
- A--D 不报告 guard coverage；E 单独报告 allow/deny/replan/abstain 路径。

## 门禁与解释

- 首先完成 banking、slack、workspace、travel 的固定小型 pilot。
- 该 pilot 固定使用同一 Qwen3-32B 既有 no-guard 运行中攻击成功的四个配对，每套件一个；这是 targeted mechanism set，不是随机样本或总体 ASR 估计。
- 只有 D 相对 A 和 B 呈一致方向改善，且不是由调用数大幅下降造成，才进入完整 benchmark。
- C 与 D 用于区分“增加 atom 术语”与“反事实验证后表示”的效果。
- E 相对 D 的差异解释为 guard 增量，不能归因于 atom 表示本身。
- 单模型或小型 pilot 的负面结果必须保留；不得据结果删除任务。
- representation-only D/G 未通过门禁，因此不启动完整 self-governance benchmark。H/I same-model reviewer 也因 benign smoke `0/1` 而停止在 smoke；这是预期的 fail-fast 决策，不是缺失结果。

## 已满足的执行前条件

- B 已使用同一 Qwen3-32B tokenizer 与 D 逐工具精确匹配 token 数。
- A0 已在相同 runner 中实现并完成 smoke。
- pilot case list 与选择依据已写入 `pilot_selection_manifest.json`。完整 benchmark 仍须使用未按结果筛选的官方分母。
