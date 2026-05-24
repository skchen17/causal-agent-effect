# T62 Validation-Selected Threshold Evaluation

- Train data: `qwen3-8b_auth_effect_schema_conditioned_v2`
- Trace data: `qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1`
- Train rows used: 11712
- Trace rows: 960
- Validation rows: 384
- Test rows: 576
- Target FPR: 0.1

## Selected Thresholds

| Method | Threshold | Under target | Val FNR | Val FPR | Val N+ | Val N- |
|---|---:|---:|---:|---:|---:|---:|
| `execution_trace_sgd_auth_validation_selected` | 0.05 | True | 0.0 | 0.0 | 28 | 279 |
| `static_trace_semantic_sgd_auth_validation_selected` | 0.05 | True | 1.0 | 0.0 | 28 | 279 |
| `static_monitored_effect_only_sgd_auth_validation_selected` | 0.05 | True | 1.0 | 0.0 | 28 | 279 |

## Held-Out Test Results

| Method | Threshold | Test FNR | Test FPR | Test N+ | Test N- |
|---|---:|---:|---:|---:|---:|
| `execution_trace_sgd_auth_validation_selected` | 0.05 | 0.0 | 0.0 | 62 | 411 |
| `static_trace_semantic_sgd_auth_validation_selected` | 0.05 | 1.0 | 0.0 | 62 | 411 |
| `static_monitored_effect_only_sgd_auth_validation_selected` | 0.05 | 1.0 | 0.0 | 62 | 411 |

## Effect-Level Held-Out Results

| Method | Effect | Threshold | Test FNR | Test FPR | Test N+ | Test N- |
|---|---|---:|---:|---:|---:|---:|
| `execution_trace_sgd_auth_validation_selected` | `content_fetched` | 0.05 | 0.0 | None | 41 | 0 |
| `execution_trace_sgd_auth_validation_selected` | `tool_error` | 0.05 | 0.0 | 0.0 | 21 | 51 |
| `static_trace_semantic_sgd_auth_validation_selected` | `content_fetched` | 0.05 | 1.0 | None | 41 | 0 |
| `static_trace_semantic_sgd_auth_validation_selected` | `tool_error` | 0.05 | 1.0 | 0.0 | 21 | 51 |
| `static_monitored_effect_only_sgd_auth_validation_selected` | `content_fetched` | 0.05 | 1.0 | None | 41 | 0 |
| `static_monitored_effect_only_sgd_auth_validation_selected` | `tool_error` | 0.05 | 1.0 | 0.0 | 21 | 51 |

## Caveats

- Thresholds are selected on validation trace groups and evaluated on held-out trace groups.
- Trace groups inherit the provenance of the trace dataset; inspect the source trace manifest before making external-validity or deployment claims.
- This is a calibration diagnostic; it does not by itself establish deployment safety.
