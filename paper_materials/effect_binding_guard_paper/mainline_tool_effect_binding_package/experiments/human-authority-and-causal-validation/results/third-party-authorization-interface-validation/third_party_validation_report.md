# Third-Party Authorization-Interface Validation

Status: `passed`. Eleven tools from three pinned public MCP implementations were executed in disposable local fixtures.

Registration used 264 executions; post-freeze evaluation used 264 disjoint contexts. Human refinements: 0.

## Collision Results

| Representation | Cells | Mixed cells | Separating pairs |
|---|---:|---:|---:|
| tool_name | 11 | 11 | 1552 |
| raw_call | 155 | 5 | 100 |
| state_aware_raw_call | 161 | 0 | 0 |
| common_field | 126 | 12 | 200 |
| typed_effect | 138 | 0 | 0 |
| source_effect_oracle | 138 | 0 | 0 |

## Diagnostic Authorization

| Representation | UPA | False denial | Coverage | Accuracy |
|---|---:|---:|---:|---:|
| tool_name | 0.000 | 0.000 | 0.000 | 0.000 |
| raw_call | 0.000 | 0.000 | 0.364 | 0.364 |
| state_aware_raw_call | 0.000 | 0.000 | 1.000 | 1.000 |
| common_field | 0.000 | 0.000 | 0.424 | 0.424 |
| typed_effect | 0.000 | 0.000 | 1.000 | 1.000 |
| source_effect_oracle | 0.000 | 0.000 | 1.000 | 1.000 |

The state-aware and raw-call authorization rows use disclosed, static request adapters. Collision counts are the pure observation-interface result.
