# E02 Lexical Control

## 目的

检验 E01 的 LOTO 失败是否只是工具名、URL、命令字符串等显式词汇特征导致的 shortcut。

## 主要结论

lexical normalization 后总体 held-out FNR 基本不变，项目记录中的主口径为 `0.378 -> 0.382`。这反驳了“只是关键词捷径”的最简单解释，但不能完全排除模板风格、任务叙述或生成器风格等更高层 surface artifact。

## 关键产物

- `src/experiments/lexical_control_experiment.py`
- `data/scenarios_merged_lexical_control.jsonl`
- `analysis/manifests/lexical_control_manifest.json`
- `embeddings/*qwen3-8b_scenarios_merged_lexical_control*`
- `analysis/results/lexical_control_qwen3-8b_scenarios_merged_lexical_control.json`

## 论文可支持的 claim

可以说 lexical normalization 没有消除 LOTO degradation，因此 tool-surface fragmentation 不只是显式工具名或 URL/command token shortcut。

## 不能支持的 claim

不能声称已经排除所有 lexical/template artifact；只能排除当前 normalization 覆盖的表面词汇因素。

