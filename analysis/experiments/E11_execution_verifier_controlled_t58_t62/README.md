# E11 T58/T62 Controlled Execution Verifier

## 目的

把 verifier 从静态 tool-call 规则推进到 execution trace candidate-effect data，并使用 validation-selected threshold 替代 ex-post threshold。

## 主要结论

T58 controlled traces 中 schema-to-trace execution verifier FNR/FPR 约为 `0.0429/0.0`；T62 使用 validation trace groups 选阈值后，在多个 trace dataset 上得到 held-out test 指标。结论是 execution evidence 有帮助，但当前仍是受控 trace，而不是 deployed-agent logs。

## 关键产物

- `src/auth/build_auth_trace_effect_schema_conditioned_data.py`
- `src/auth/experiment_auth_t58_execution_verifier.py`
- `src/auth/experiment_auth_t62_validation_threshold.py`
- `data/auth_trace_effect_schema_conditioned_v1.jsonl`
- `analysis/results/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_v1.json`
- `analysis/results/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_v1.json`

## 论文可支持的 claim

可以说 execution-level evidence 在 controlled setting 中能降低 static/representation-only miss。

## 不能支持的 claim

不能声称已经验证任意 sparse/raw logs；T69 说明 full-label trace view 会高估性能。

