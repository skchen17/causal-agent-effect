# E08 Auth-SafeInv Counterfactual Evaluation

## 目的

把研究目标从“effect 是否被表示”扩展到 authorization-conditioned realized-effect monitoring：给定任务授权包络 A(c)，判断 action/trace 中实际 effect 是否越权。

## 主要结论

Auth-SafeInv 提供了更贴近 agent safety 的评价对象：`Omega(a,t) \ A(c)`。v2 数据扩展到 1464 authorization counterfactual rows，7 个 focus effects 都有多个 unauthorized tools。该实验支持论文 evaluation target，但不是部署安全认证。

## 关键产物

- `src/auth/build_authorization_counterfactuals.py`
- `src/auth/build_authorization_counterfactuals_v2.py`
- `src/auth/experiment_auth_safeinv.py`
- `data/authorization_counterfactuals_v1.jsonl`
- `data/authorization_counterfactuals_v2.jsonl`
- `analysis/manifests/authorization_counterfactuals_v2_manifest.json`
- `analysis/results/auth_safeinv_qwen3-8b_authorization_counterfactuals_v2.json`
- `analysis/results/surface_graph_alignment_authorization_counterfactuals_v2.json`

## 论文可支持的 claim

可以把 Auth-SafeInv 写成 action-level authorization-conditioned evaluation target。

## 不能支持的 claim

不能把 counterfactual rows 写成真实执行日志；不能把 Auth-SafeInv 指标本身写成防御方法。

