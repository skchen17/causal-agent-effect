# E04 Baselines and Tool-Proxy Behavior

## 目的

比较 pooled probe、balanced training、tool-conditioned probe、group reweight、Procrustes 等自然 baseline，判断 surface-form fragmentation 是否可由简单线性/几何校正消除。

## 主要结论

这些 baseline 可以改善部分平均指标，但不能消除 worst-form held-out FNR。该实验支持“现有自然 baseline 不足以解决 coverage-missing fragility”，但不能写成“所有 domain-generalization 方法都失败”。

## 关键产物

- `src/experiments/experiment_baselines.py`
- `src/solutions/solution_procrustes.py`
- `analysis/results/baseline_comparison_qwen3-8b_scenarios_merged.json`
- `analysis/results/baseline_comparison_qwen3-8b_scenarios_mainconf_v1.json`
- `analysis/results/baseline_comparison_qwen3-8b_scenarios_mainconf_v2.json`
- `analysis/results/procrustes_qwen3-8b_scenarios_merged.json`

## 论文可支持的 claim

可以说若干自然的 split-matched baseline 无法稳定解决 held-out tool-surface 漏检。

## 不能支持的 claim

不要把 inverse-frequency group weighting 称作 GroupDRO，除非实现实际优化 worst-group loss；不要声称已覆盖所有强 OOD/domain-generalization baseline。

