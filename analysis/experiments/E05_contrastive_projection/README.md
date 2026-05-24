# E05 Contrastive Projection

## 目的

检验通过对比学习/投影对齐不同工具表面形式的同 effect 表征，是否能缓解 surface-form fragmentation。

## 主要结论

full-training contrastive projection 在 observed cross-form pairs 上很强，项目记录中 5/6 effects 的 post-FNR 可到 `0.00`，但这是 observed-pair upper bound。strict LOPO 只部分改善，项目记录包括 original `40/68` improved、mainconf v2 `33/68` improved。不能作为未知工具或 coverage-missing 场景的主安全修复。

## 关键产物

- `src/solutions/solution_contrastive.py`
- `src/solutions/run_contrastive_strict_lopo.py`
- `src/solutions/run_contrastive_multiseed.py`
- `analysis/results/contrastive_qwen3-8b_scenarios_merged.json`
- `analysis/results/contrastive_strict_lopo_qwen3-8b_scenarios_merged.json`
- `analysis/results/contrastive_strict_lopo_qwen3-8b_scenarios_mainconf_v2.json`
- `analysis/results/contrastive_multiseed_qwen3-8b_scenarios_mainconf_v2.json`
- `analysis/results/contrastive_multiseed_qwen3-8b_scenarios_mainconf_v2.md`

## 论文可支持的 claim

可以写成 observed-pair repair upper bound，说明如果跨表面正样本关系已知，表示对齐可能大幅降低 stress FNR。

## 不能支持的 claim

不能把 full-training 结果写成 zero-shot 或 coverage-missing mitigation；strict LOPO 才是主要泛化证据。

