# E06 Causal-Chain Conditioning

## 目的

研究向模型输入显式或半显式任务-动作-effect 因果链，是否会改变 effect 表征组织并降低 ToolProxyGap。

## 主要结论

causal-chain conditioning 结果是 mixed diagnostic：部分 effect 在显式因果链下改善，但 wrong-chain / typed wrong-chain 条件显示鲁棒性不足。该方向适合作为 appendix diagnostic，不足以作为当前主方法。

## 关键产物

- `data/causal_chain_conditioning.jsonl`
- `data/causal_chain_conditioning_v2.jsonl`
- `analysis/manifests/causal_chain_conditioning_manifest.json`
- `analysis/manifests/causal_chain_conditioning_v2_manifest.json`
- `analysis/results/causal_chain_conditioning_qwen3-8b.json`
- `analysis/results/causal_chain_mechanism_qwen3-8b_causal_chain_conditioning_v2.json`
- `analysis/results/causal_chain_mechanism_qwen3-8b_causal_chain_conditioning_v2.md`
- `analysis/reports/causal_chain_conditioning_qwen3-8b.md`

## 论文可支持的 claim

可以说 causal-chain textual conditioning 对表征有可观测影响，但效果不稳定，提示“给 LLM 因果链”不是直接稳健解法。

## 不能支持的 claim

不能声称 causal-chain conditioning 已能解决越权检测；不能把 wrong-chain 脆弱性忽略。

