# 联合效果与权限四格诊断

## 目的

该实验把运行时的两个信息接口分开：

- 工具效果表示：当前已注册字段或 source-reviewed 效果投影；
- 任务权限表示：当前 reviewed manifest 或 AgentDojo 官方 `ground_truth()` 调用链构造
  的精确评估 oracle。

四个组合在同一组 26 个 AgentDojo 任务、26 条良性轨迹和 169 条官方攻击轨迹上做
确定性调用重放。实验不重新调用模型、不执行工具，也不改变任何原始日志。

## 重要口径

官方 oracle 只读取 benchmark user-task 的调用链，不读取模型轨迹、攻击轨迹、攻击
目标或攻击标签。它不是可部署权限，也不证明用户真实授权；官方调用链还可能排除
其他合法实现。该列只用于判断当前损失更可能来自效果表示还是权限接口。

Source-reviewed 投影只覆盖 16 个工具。缺少投影时 source-oracle 格子记为不可评估，
不会回退到当前字段或静默放行。输出的攻击和效用数字都是固定轨迹可接纳性诊断，
不是重新运行 AgentDojo 后的 ASR 或 utility。

## 运行

```bash
PYTHONPATH=shared/compatibility/code \
python experiments/security-analysis-ablation-and-overhead/source/\
joint-effect-authority-diagnostic/run_diagnostic.py
```

输出位于：

`experiments/security-analysis-ablation-and-overhead/results/joint-effect-authority-diagnostic/`
