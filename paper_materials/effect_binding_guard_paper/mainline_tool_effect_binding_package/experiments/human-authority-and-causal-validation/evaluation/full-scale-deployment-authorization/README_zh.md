# Full-Scale Deployment-Style Authorization Experiment

本实验验证经过注册期反事实测试的 concrete typed-effect representation，是否能在同一组 deployment-style 授权策略和同一个三态授权引擎下，比工具名、原始参数和 common-effect fields 更充分地支持授权决策。

## 实验设计

- 8 个领域和工具：calendar、workspace sharing、messaging、banking、email、repository access、cloud storage、expense approval。
- 144 条注册期 context，组成 72 个反事实 pair：每个工具包含 8 个安全敏感 pair 和 1 个 surface-invariant pair。
- 192 条冻结 held-out context，组成 96 个 policy-separating pair；每个 pair 包含一个 `ALLOW` 和一个 `DENY` context。
- 26 个 held-out pair 使用完全相同的显式 arguments、不同的 pre-state，并产生不同 committed effects 和授权结果。
- 策略类型包括 ACL、capability 和 delegation。策略只读取 concrete effect atoms，不使用 source-effect multiset containment。

## 证据隔离

1. `execute_tool` 只在复制的内存状态上执行调用。
2. `source_effects` 从执行前后状态差分得到实际 committed effects。
3. `instantiate_descriptor` 不执行工具，也不调用 `source_effects`，而是从冻结 descriptor、调用参数和 pre-state 实例化 atoms。
4. ideal decision 由真实策略对 source-derived effects 判定。
5. 所有表示都交给同一个 `authorize_observation` 引擎；信息缺失返回 `ABSTAIN`，已知越权事实返回 `DENY`。

## 运行

```bash
python shared/compatibility/scripts/run_full_scale_deployment_authorization.py --mode full
PYTHONPATH=. python -m pytest \
  shared/compatibility/tests/tests/test_full_scale_deployment_authorization.py -q
```

输入已由 `protocol.json` 的 SHA-256 固定。重新冻结输入需要显式传入 `--freeze-inputs --force-freeze`；正常复现不应重新冻结。

## Claim Boundary

这是一个受控、八工具、copied-sandbox 授权实验。它验证冻结干预族和策略族上的表示充分性，不证明任意未知工具的 descriptor 完备性、策略本身正确、真实部署分布或 production safety。

