# E20 Statistical Uncertainty Audit

## 目的

审计主实验的 N+/N-、置信区间、seed variance、threshold policy 和 small-N cell 风险。

## 主要结论

原始数据中多个关键 cell positive count 很小；mainconf v2 改善了 P0 cells，但主表仍必须报告 N+/N-/CI/threshold/seed。任何 `0.0000` FNR/FPR 都必须伴随样本数，否则容易被审稿人视为统计支撑不足。

## 关键产物

- `analysis/scripts/statistical_uncertainty_audit.py`
- `analysis/results/statistical_uncertainty_audit.json`
- `analysis/results/statistical_uncertainty_audit.md`
- `analysis/results/statistical_uncertainty_audit_mainconf_v1.json`
- `analysis/results/statistical_uncertainty_audit_mainconf_v1.md`
- `analysis/results/statistical_uncertainty_audit_mainconf_v2.json`
- `analysis/results/statistical_uncertainty_audit_mainconf_v2.md`

## 论文可支持的 claim

可以用作主表数字的统计来源和 small-N limitation 的依据。

## 不能支持的 claim

不能把小样本点估计写成稳健总体估计；small-N 结果应进 appendix 或加明确 caveat。

