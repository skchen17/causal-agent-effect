# E10 T57 Static Effect-Present Verifier

## 目的

用 non-oracle deterministic static verifier 替换 T56 中的 oracle `candidate_effect_present`，测试 effect-present signal 是否可以从可审计规则中得到。

## 主要结论

T57 在 controlled/static setting 中表现强，记录中的 LOTO FNR/FPR 为 `0.0262/0.073`，family FNR/FPR 为 `0.1221/0.0048`。这支持 verifier-assisted 方向，但该 verifier 仍是 handcrafted static rules，不是 live execution verifier。

## 关键产物

- `src/auth/experiment_auth_t57_effect_present_verifier.py`
- `analysis/results/auth_t57_effect_present_verifier_qwen3-8b_auth_effect_schema_conditioned_v2.json`
- `analysis/results/auth_t57_effect_present_verifier_qwen3-8b_auth_effect_schema_conditioned_v2.md`

## 论文可支持的 claim

可以说 effect-present signal 能显著改善授权监控，但需要明确这是 static/controlled verifier evidence。

## 不能支持的 claim

不能声称 T57 已验证真实执行效果；不能把 handcrafted rules 写成 learned generalized verifier。

