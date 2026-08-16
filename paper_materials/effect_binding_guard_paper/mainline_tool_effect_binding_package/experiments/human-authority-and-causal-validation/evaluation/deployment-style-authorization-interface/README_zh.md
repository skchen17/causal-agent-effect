# 部署式授权接口验证

## 目的

使用四个带状态的复制 sandbox 工具和冻结的 ACL、capability、delegation 风格策略，比较工具名、原始参数、公共效果字段和经过反事实验证的 typed effects 对授权决策的支持能力。

## 关键控制

- 四种表示使用完全相同的调用、pre-state、policy 和授权消费者。
- 实际执行后的状态差分只用于生成 ideal decision 和离线验证 descriptor，不进入 pre-commit 表示。
- 主消费者对 mixed representation cell 返回 `ABSTAIN`；统一 fail-open 与 fail-closed 诊断分别量化 unsafe allow 和 false denial。
- 所有 48 个 context 在 full run 中保留，不按结果删除。

## 结论边界

该实验是四领域、有限 context 的 deployment-style policy 机制验证，不代表真实部署策略的分布，也不证明开放域 descriptor 完备性或生产安全。
