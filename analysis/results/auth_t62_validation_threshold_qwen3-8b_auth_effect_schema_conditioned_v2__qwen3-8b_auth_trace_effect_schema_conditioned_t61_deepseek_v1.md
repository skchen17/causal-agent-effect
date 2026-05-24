# T62 Validation-Selected Threshold Evaluation

- Train data: `qwen3-8b_auth_effect_schema_conditioned_v2`
- Trace data: `qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1`
- Train rows used: 11712
- Trace rows: 960
- Validation rows: 384
- Test rows: 576
- Target FPR: 0.1

## Selected Thresholds

| Method | Threshold | Under target | Val FNR | Val FPR | Val N+ | Val N- |
|---|---:|---:|---:|---:|---:|---:|
| `execution_trace_sgd_auth_validation_selected` | 0.05 | True | 0.0 | 0.0 | 42 | 288 |
| `static_trace_semantic_sgd_auth_validation_selected` | 0.05 | True | 1.0 | 0.0 | 42 | 288 |
| `static_monitored_effect_only_sgd_auth_validation_selected` | 0.05 | True | 1.0 | 0.0 | 42 | 288 |

## Held-Out Test Results

| Method | Threshold | Test FNR | Test FPR | Test N+ | Test N- |
|---|---:|---:|---:|---:|---:|
| `execution_trace_sgd_auth_validation_selected` | 0.05 | 0.0 | 0.0 | 78 | 432 |
| `static_trace_semantic_sgd_auth_validation_selected` | 0.05 | 1.0 | 0.0 | 78 | 432 |
| `static_monitored_effect_only_sgd_auth_validation_selected` | 0.05 | 1.0 | 0.0 | 78 | 432 |

## Effect-Level Held-Out Results

| Method | Effect | Threshold | Test FNR | Test FPR | Test N+ | Test N- |
|---|---|---:|---:|---:|---:|---:|
| `execution_trace_sgd_auth_validation_selected` | `content_fetched` | 0.05 | 0.0 | 0.0 | 37 | 20 |
| `execution_trace_sgd_auth_validation_selected` | `network_egress` | 0.05 | 0.0 | None | 21 | 0 |
| `execution_trace_sgd_auth_validation_selected` | `tool_error` | 0.05 | 0.0 | 0.0 | 20 | 52 |
| `static_trace_semantic_sgd_auth_validation_selected` | `content_fetched` | 0.05 | 1.0 | 0.0 | 37 | 20 |
| `static_trace_semantic_sgd_auth_validation_selected` | `network_egress` | 0.05 | 1.0 | None | 21 | 0 |
| `static_trace_semantic_sgd_auth_validation_selected` | `tool_error` | 0.05 | 1.0 | 0.0 | 20 | 52 |
| `static_monitored_effect_only_sgd_auth_validation_selected` | `content_fetched` | 0.05 | 1.0 | 0.0 | 37 | 20 |
| `static_monitored_effect_only_sgd_auth_validation_selected` | `network_egress` | 0.05 | 1.0 | None | 21 | 0 |
| `static_monitored_effect_only_sgd_auth_validation_selected` | `tool_error` | 0.05 | 1.0 | 0.0 | 20 | 52 |

## Caveats

- Thresholds are selected on validation trace groups and evaluated on held-out trace groups.
- Trace groups are synthetic or controlled/API-backed groups, not live deployment traffic.
- This is a calibration diagnostic; it does not by itself establish deployment safety.
