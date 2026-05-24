# E03 pIIA Transfer Diagnostics

## 目的

用 probe-mediated interchange intervention 和 hook controls 检查 effect direction 是否能跨工具表面形式稳定迁移。

## 主要结论

pIIA-Drop 在多个 effect 上为正，项目记录中范围为 `0.052` 到 `0.366`；confirmatory hook controls 给出 pIIA-Drop 与 max held-out FNR 的正相关信号。该结果支持 activation-level transfer fragility，但它是 probe-mediated diagnostic，不是标准 SCM-style IIA 或因果证明。

## 关键产物

- `analysis/results/iia_true_qwen3-8b_scenarios_merged.json`
- `analysis/results/iia_true_raw_qwen3-8b_scenarios_merged.jsonl`
- `analysis/results/iia_true_bootstrap_qwen3-8b_scenarios_merged.json`
- `analysis/results/piia_controls_qwen3-8b_scenarios_mainconf_v2.json`
- `analysis/results/piia_hook_controls_qwen3-8b_scenarios_mainconf_v2.json`
- `analysis/results/piia_hook_controls_confirmatory_qwen3-8b_scenarios_mainconf_v2.json`
- `analysis/results/piia_hook_controls_confirmatory_qwen3-8b_scenarios_mainconf_v2.md`

## 论文可支持的 claim

可以作为 E01 的机制性支持证据：跨工具表面形式的 activation transfer 不稳定，与 LOTO failure 方向一致。

## 不能支持的 claim

不能把 pIIA 写成 causal proof、standard IIA 或安全保证；应使用 `pIIA` / `probe-mediated IIA` 和 `pIIA-Drop`。

