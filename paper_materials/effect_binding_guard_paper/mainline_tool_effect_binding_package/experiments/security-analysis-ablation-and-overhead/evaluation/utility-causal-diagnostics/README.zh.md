# 效用因果诊断、反事实能力与 CEGAR 机制探针

本实验用于回答三个机制问题：

1. `atom` 相比原始任务或不透明 effect 摘要，是否帮助模型区分授权字段、越权字段和可局部修订的复合调用；
2. 反事实框架能否同时验证敏感性、表面不变性、复合 effect 拆分和 provenance/authority 依赖；
3. CEGAR 是否能用训练侧反例注册有作用域的等价规则，在不增加 unsafe allow 的情况下减少误拒绝。

数据由已审查的 E84 authority-interface packet 和已注册 effect descriptor 确定性生成。模型看不到 `expected_decision`、case type 或评分信息。实验不执行工具，也不改写 AgentDojo 主结果。

运行方式：

```bash
python experiments/security-analysis-ablation-and-overhead/scripts/utility-causal-diagnostics/run_deepseek_atom_cegar_probe.py --mode prepare
DEEPSEEK_API_KEY=... python experiments/security-analysis-ablation-and-overhead/scripts/utility-causal-diagnostics/run_deepseek_atom_cegar_probe.py --mode smoke --repeats 2
DEEPSEEK_API_KEY=... python experiments/security-analysis-ablation-and-overhead/scripts/utility-causal-diagnostics/run_deepseek_atom_cegar_probe.py --mode full --repeats 2
```

API key 只能通过进程环境传入，不能写入脚本、protocol、日志或报告。

## 口径边界

这是开发期机制诊断，不是预注册实验，也不是 AgentDojo 官方端到端评测。smoke 曾用于修复 token budget 和字段级 probe scope。它可以判断某种表示或修复机制是否值得进入正式实验，但不能单独支撑 benign utility、ASR、生产安全或人类审查等论文声明。确认性证据必须使用另行冻结的 v2 协议和未参与规则形成的测试集。
