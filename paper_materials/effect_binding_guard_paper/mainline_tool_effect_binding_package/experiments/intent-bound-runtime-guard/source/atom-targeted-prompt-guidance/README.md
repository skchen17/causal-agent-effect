# Atom-Targeted Prompt Guidance

该实验使用 8 个 AgentDojo 工具 schema 构造单轴 clean/injected 配对。我们的方案只使用 atom 提示和 system prompt 引导，不启用 guard；其他基线保留输入检测、提示包装、净化、masked re-execution 或 causal shadow 机制。实验不执行任何真实或 sandbox 工具。

运行器同时记录 guard 前候选调用、guard 诊断和最终调用。评分 sidecar 与 deployable prompt 分离，因此标签不会进入模型或防御输入。
