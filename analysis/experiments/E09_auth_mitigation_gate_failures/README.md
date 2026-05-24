# E09 Auth Mitigation Gate Failures

## 目的

在 Auth-SafeInv v2 的严格 split 下检验纯 representation-side mitigation 是否可以作为主方法。

## 主要结论

三个 gate 失败：T54 strict contrastive FNR `0.2804` 弱于 best baseline `0.1835`；T55 schema-conditioned FNR `0.4516`；T56 pure decomposed frozen verifier FNR `0.3547`。verifier-present upper bound 很强，但依赖 external/oracle effect-present signal。因此论文应诚实报告“纯表征侧修复不足”。

## 关键产物

- `src/auth/experiment_auth_mitigation_comparison.py`
- `src/auth/experiment_auth_schema_conditioned_mitigation.py`
- `src/auth/experiment_auth_decomposed_verifier_mitigation.py`
- `data/auth_effect_schema_conditioned_v2.jsonl`
- `analysis/results/auth_mitigation_vs_baseline_qwen3-8b_authorization_counterfactuals_v2.json`
- `analysis/results/auth_schema_conditioned_mitigation_qwen3-8b_auth_effect_schema_conditioned_v2.json`
- `analysis/results/auth_decomposed_verifier_mitigation_qwen3-8b_auth_effect_schema_conditioned_v2.json`
- `analysis/results/auth_decomposed_verifier_mitigation_qwen3-8b_auth_effect_schema_conditioned_v2_verifier_present_full.json`

## 论文可支持的 claim

可以把 gate failures 写成负结果：strict Auth-SafeInv 下，当前纯 representation-side 方法不足以成为 robust safety monitor。

## 不能支持的 claim

不能把 verifier-present upper bound 当作可部署方法；不能隐藏 gate failure。

