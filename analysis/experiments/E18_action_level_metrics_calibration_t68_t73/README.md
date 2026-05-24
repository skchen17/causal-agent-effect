# E18 T68/T73 Action-Level Metrics and Calibration

## 目的

把 candidate-effect row-level predictions 聚合为 action-level allow/deny，检查 row FNR/FPR 是否能代表实际 policy risk，并测试简单 action-level threshold calibration。

## 主要结论

T68 显示 row-level 指标与 action-level risk 可严重脱节，T61/T65 中 execution verifier 的 authorized-action false denial 可达 `1.0`。T73 进一步显示在 validation FDeny <= 0.10 约束下，多个 family 的 calibration 会退化为 all-allow，held-out unauthorized-action allow = `1.0`。这是 Layer 3 row-to-action over-optimism 的核心证据。

## 关键产物

- `analysis/scripts/auth_action_level_metrics.py`
- `analysis/scripts/auth_action_level_calibration_t73.py`
- `analysis/results/auth_action_level_metrics_t68.json`
- `analysis/reports/auth_action_level_metrics_t68.md`
- `analysis/results/auth_action_level_calibration_t73.json`
- `analysis/reports/auth_action_level_calibration_t73.md`

## 论文可支持的 claim

可以说安全评估必须报告 action-level U-Allow / FDeny / abstain 或 coverage 指标，row-level FNR/FPR 不足以判断 monitor 是否可部署。

## 不能支持的 claim

不能把简单 threshold calibration 写成解决方案；当前它是负结果。

