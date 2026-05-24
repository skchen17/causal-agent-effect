# E01 Surface-Form Fragmentation LOTO

## 目的

检验同一个 causal effect 在 held-out tool surface 上是否能被线性探针稳定识别。该实验是论文 Layer 1 tool-surface over-optimism 的核心证据。

## 主要结论

LOTO stress test 显示，在训练时拿掉某个工具表面形式后，held-out FNR 明显升高；原始 stress 中最高 FNR 曾达到 `0.97`，mainconf v2 中最大 held-out FNR 为 `0.8036`。这支持 surface-form fragmentation / tool-proxy behavior，但只应解释为 coverage-missing stress-test FNR，不应写成真实部署 FNR。

## 关键产物

- `data/scenarios_merged.jsonl`
- `data/scenarios_mainconf_v1.jsonl`
- `data/scenarios_mainconf_v2.jsonl`
- `embeddings/*qwen3-8b_scenarios_merged*`
- `embeddings/*qwen3-8b_scenarios_mainconf_v2*`
- `analysis/results/fnr_frag_qwen3-8b_scenarios_merged.json`
- `analysis/results/fnr_frag_qwen3-8b_scenarios_mainconf_v2.json`
- `analysis/results/baseline_comparison_qwen3-8b_scenarios_merged.json`
- `analysis/results/baseline_comparison_qwen3-8b_scenarios_mainconf_v2.json`

## 论文可支持的 claim

证据支持：在受控合成/扩展数据中，表征侧 effect detector 会在工具表面覆盖缺失时产生高漏检。

## 不能支持的 claim

不能声称该 FNR 等于部署环境风险；不能声称 fragmentation 是唯一原因，domain shift 和小样本 cell 仍是混杂因素。

