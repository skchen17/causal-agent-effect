# E07 Mainconf v2 Scaling and Cell Statistics

## 目的

扩展原始 459 条合成场景，改善关键 effect-tool cell 的 positive count，并重新运行主线诊断和 mitigation。

## 主要结论

mainconf v2 扩展到 932 rows，7 个 P0 cells 达到 N+ >= 50。该扩展提高了统计可信度，并把最大 held-out FNR 收敛到更稳健的 `0.8036` 量级；但仍需在主表中报告 N+/N-/CI/threshold/seed，不能只报告点估计。

## 关键产物

- `data/scenarios_mainconf_increment_v2.jsonl`
- `data/scenarios_mainconf_v2.jsonl`
- `analysis/manifests/scenarios_mainconf_v2_manifest.json`
- `analysis/results/fnr_frag_qwen3-8b_scenarios_mainconf_v2.json`
- `analysis/results/baseline_comparison_qwen3-8b_scenarios_mainconf_v2.json`
- `analysis/results/contrastive_strict_lopo_qwen3-8b_scenarios_mainconf_v2.json`
- `analysis/results/statistical_uncertainty_audit_mainconf_v2.json`
- `analysis/results/statistical_uncertainty_audit_mainconf_v2.md`

## 论文可支持的 claim

mainconf v2 支持更可信的 tool-surface fragmentation stress-test 和统计审计。

## 不能支持的 claim

仍不能替代真实 deployed-agent logs；small-N cell 仍需降级或移入 appendix。

