# E84 独立授权运行时接入状态

## 已完成

- 44 份 `trusted_manifests.jsonl` 均可通过结构编译。
- 对 60 个 resolver 在 AgentDojo v1.1.2 干净沙箱中执行兼容性审计。
- 审计发现原 resolver 的 typed projection 成功数为 `0/60`，因此未直接用于性能实验。
- 生成 60 行 label-hidden resolver 修复模板、人工审查指南和独立验证器。
- 验证器检查 immutable payload hash、审查元数据、只读工具资格、固定查询参数、真实沙箱执行和 typed scalar projection。
- 新增 AgentDojo `ToolsExecutor` 前置仲裁器。运行时按原任务哈希选择独立 manifest；只读工具可执行，有副作用工具必须通过 totalization 和独立字段授权。
- 生成 25 份不依赖 resolver 或 canonical transform 的 exact-only runtime manifest。
- exact-only 接线冒烟通过：25 份 manifest 的任务哈希全部匹配；其中 24 份只含只读任务，1 份含有副作用工具；exact-authority 调用为 `ALLOW`，越界调用为 `DENY`。

## AI Artifact Review

60 行 resolver 修复已由 `AI_ARTIFACT_REVIEW_01` 完成 label-hidden artifact review：

- `APPROVE`: `2`
- `REJECT`: `58`
- validator: `passed_with_rejections`
- runtime-ready manifests: `26`，其中 resolver-enabled manifest 为 `1`
- reviewer type 明确记录为 `ai_artifact_reviewer`，不得写成人类审查或 human agreement。

两个批准项均经过真实 AgentDojo 干净沙箱复核。resolver-enabled 冒烟结果为：匹配授权调用 `ALLOW`，未证明资源 `ABSTAIN`，越界参与者 `DENY`。

## 后续运行

验证器可重复运行：

```bash
PYTHONPATH=code runs/e75_agentdojo_env/bin/python \
  experiments/security-analysis-ablation-and-overhead/scripts/runtime-mechanism-ablation/validate-e84-resolver-repair.py
```

当前已生成 `runtime_ready_trusted_manifests.jsonl`，可以启动固定的 26-task runtime pilot。但其中 24 个任务只读、一个 exact-only effectful、一个 resolver-enabled effectful，因此只能作为窄范围独立授权实验，不能替代完整 AgentDojo 评测。

## 已运行检查

- E75 method config / method ID：`2 passed`。
- E81 trusted interface、reviewed runtime、E84 authority review：`16 passed`。
- AgentDojo 专用环境导入、索引、编译、exact-only smoke 和 resolver-enabled smoke：通过。
- 更宽的 E75 测试中有一项既有 E73 projection artifact 映射测试得到 `0/156` 而失败；该失败与本次 E84 接线无直接关系，未通过修改 E84 代码掩盖。

## Claim Boundary

当前证据支持“label-hidden AI artifact review 产生的 manifest 已接入确定性 pre-commit runtime，并在两个有副作用任务的小范围内正确区分已授权、未证明和越界字段”。当前证据不支持独立人类审查、human agreement、完整 AgentDojo attack robustness、production safety 或完整自动授权基础设施。
