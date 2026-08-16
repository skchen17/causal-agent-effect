# AgentDojo 工具效果普遍性审计

## 目的

该实验回答一个有限但关键的问题：复合工具效果是否只存在于论文构造的
示例中，还是也出现在 AgentDojo 官方良性任务的真实源码执行轨迹中。

## 方法

- 数据范围：AgentDojo v1.1.2 的 97 个官方良性任务，共 339 次官方
  ground-truth 工具调用。
- 执行方式：每个任务从 fresh in-memory sandbox 开始，按官方轨迹顺序执行。
- 效果判定：比较调用前后的 benchmark state，不读取候选 contract、攻击标签、
  gold atom 或结果标签。
- 归一化：移除存储镜像和时间戳等易变元数据；把同一资源的一次实现更新合并，
  并按可独立寻址的对象、目标、权限、消息和成员关系展开逻辑效果单元。
- 研究边界：总量曾在探索性覆盖审计中被查看，因此本实验是最终规则冻结后的
  描述性 census，不声称结果盲预注册。

## 结果

- 339/339 次调用执行成功，无运行错误。
- 官方轨迹覆盖 55/74 个 suite-specific 工具实例。
- 100/339 次调用产生可观察的状态或外部交互效果。
- 17/100 个 effectful calls 包含多个逻辑效果单元。
- 13/100 跨效果类型和 benchmark 子系统。
- 7/100 涉及多个目标主体。
- 单次调用最多产生 6 个逻辑效果单元。

这些结果支持“AgentDojo 内确实存在复合、跨目标和状态相关工具效果”的问题
陈述，但不能证明每个单元在真实策略中都需要不同授权，也不能外推到所有 agent
工具生态。

## 复现

```bash
python scripts/freeze_agentdojo_tool_effect_prevalence_protocol.py
experiments/unified-agent-security-baselines/runs/unified-agent-security-comparison/agentdojo-env/bin/python3 \
  scripts/run_agentdojo_tool_effect_prevalence.py
python -m pytest tests/tests/test_agentdojo_tool_effect_prevalence.py -q
```

主要结果见 `agentdojo-tool-effect-prevalence-report.json`；逐调用证据见
`official-call-effects.jsonl`；逐工具统计见 `tool-effect-summary.csv`。
