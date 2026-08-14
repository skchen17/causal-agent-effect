# Tool-Effect Binding 研究代码说明

该目录整理了论文主要实验的代码、冻结输入、结果文件、测试和论文源码。
核心问题是：一次工具调用可能产生多个需要分别授权的效果；如果监控器只看工具名、
整次调用或粗粒度参数，就可能把授权结果不同的效果合并到同一个表示中。

本项目使用源码执行和反事实干预验证工具会提交什么效果，再将通过验证的效果表示
用于提交前检查。当前证据支持有限域、指定策略族下的表示充分性，以及一个受限的
provenance-origin 运行时实例；不支持完整权限系统、生产安全或全局唯一最小 atom。

主要目录：

- `experiments/human-authority-and-causal-validation/`：效果普遍性、有限域碰撞、
  ToolSandbox held-out 和 232-query concrete-atom authorizer。
- `experiments/security-analysis-ablation-and-overhead/`：表示细化、策略族、
  atom-vs-field 归因和运行时消融。
- `experiments/intent-bound-runtime-guard/`：注册描述符、C1f monitor 和审计结果。
- `shared/compatibility/scripts/`：主要实验入口。
- `shared/compatibility/tests/`：对应测试。
- `EXPERIMENTS.md`：论文声明、代码和结果的逐项映射。

快速检查：

```bash
python -m pip install -r requirements-core.txt
python scripts/verify_release.py
```

模型权重、API 密钥、大型缓存、部分运行日志和真实外部副作用均不包含在仓库中。
当前仍在运行的 Qwen3-32B 强基线只保留冻结协议，不把中间结果当成最终证据。

