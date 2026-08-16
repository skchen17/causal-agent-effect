# Authorization Interface Validation 研究代码说明

该仓库包含论文主要实验的代码、冻结输入、结果、测试和论文源码。论文核心问题是：
授权系统只能区分 observation interface 保留下来的执行差异。如果两个执行需要不同的
授权结论，却被表示成同一个值，那么任何下游 authorizer 都无法同时避免不安全放行和
拒绝合法工作。

项目通过 copied sandbox 中的反事实执行验证候选接口。源码执行确定工具实际提交的
状态变化，独立提供的 policy 判断哪些变化需要不同授权，representation collision
构成可复现的失败证书。Typed effects 是其中一个被评估的候选接口，不是理论上唯一或
普遍正确的表示；项目同时评估了充分的 state-aware request interface。

主要证据包括：

- AgentDojo 和有限源码域中的复合效果与授权分离碰撞；
- 三个公开 MCP 实现、11 个工具和 264 个 descriptor-blind post-freeze contexts；
- mechanically separated native-delta policy 与 descriptor mutation audit；
- 1,024-context ACL、capability 和 delegation 授权实验；
- interface economy、30-call pre-commit integration 和 matched runtime baselines；
- 360 条严格 claim ledger 与 7,001 条逐 case 结果汇总。

快速检查：

```bash
python -m pip install -r requirements-core.txt
python scripts/verify_release.py
python scripts/reproduce_usenix_main.py
```

最终复现应输出 `status=passed`、`n_claim_rows=360` 和空的 `pending` 列表。
活动论文位于 `paper/current-usenix/main.pdf`，技术正文为 12/13 页。

模型权重、API 密钥、缓存、本地绝对路径和用户信息均未包含在发布仓库中。所有工具
执行均发生在 copied sandbox 或保存的 benchmark artifacts 上，不产生真实外部副作用。
