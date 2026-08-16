# Counterfactual Atom-Envelope Guard

本目录保存效用优先的 atom 运行时守卫实验结果。守卫不再要求每个调用参数与
初始 LLM 权限计划逐字一致，而是使用离线反事实注册得到的安全相关字段，在提交
前检查这些字段及工具效果是否受到显式不可信控制片段影响。

开发顺序固定为：单元测试与静态 replay 诊断、63 条良性与 24 条攻击 smoke、候选
冻结、97 条良性与 629 条攻击确认。未通过联合效用/安全门槛的候选不得进入论文
主结果。该实验只评估 AgentDojo 沙箱，不执行真实外部副作用。

最终 DeepSeek 证据汇总见 `final_guard_repair_report_2026-08-08.md`。同模型强基线
见 `deepseek_same_model_strong_baselines.md`。可从保存的逐任务日志重建分析并核验
冻结源文件哈希：

```bash
python3 experiments/intent-bound-runtime-guard/scripts/counterfactual-atom-envelope-guard/reproduce_deepseek_guard_repair.py
```

该复现入口不调用模型；`reproduction_status_2026-08-08.json` 记录分析器退出语义、
完整运行样本数、错误数和冻结文件哈希。C1d 的联合门禁失败是保留的负面结果，
不是复现失败。C1f 与 spotlighting 在本次官方攻击成功数上并列，当前证据不支持
SOTA 声明。
