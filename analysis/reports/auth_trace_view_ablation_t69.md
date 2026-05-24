# T69 Trace-View Verifier Independence Ablation

- Train data: `qwen3-8b_auth_effect_schema_conditioned_v2`
- Train condition: `full_tool_chain`
- Trace condition: `full_tool_chain`
- Views: `['full_labels', 'label_hidden_raw', 'minimal_evidence']`
- Target FPR: 0.1
- Validation split seed: 20260520

## View Definitions

- `full_labels`: existing execution verifier using structured `verified_effects` / `effect_diff` fields.
- `label_hidden_raw`: raw execution-result, tool-call, pre-state, and post-state rules with trace label fields hidden.
- `minimal_evidence`: stricter raw-evidence rules using result/status/state deltas and avoiding broad tool-family semantics where possible.

## Aggregate

| View | Mean test FNR | Max test FNR | Mean U-Allow | Mean FDeny | Mean present FNR vs full |
|---|---:|---:|---:|---:|---:|
| `full_labels` | 0.0353 | 0.1765 | 0.0417 | 0.4544 | 0.0 |
| `label_hidden_raw` | 0.1162 | 0.3387 | 0.0459 | 0.7428 | 0.1204 |
| `minimal_evidence` | 0.1465 | 0.3387 | 0.0588 | 0.4771 | 0.2138 |

## Per Dataset

| Trace data | View | Threshold | Test FNR | Test FPR | Present FNR | Present FPR | U-Allow | FDeny | Delta FNR vs full |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `qwen3-8b_auth_trace_effect_schema_conditioned_v1` | `full_labels` | 0.05 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.1591 | 0.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_v1` | `label_hidden_raw` | 0.05 | 0.0455 | 0.129 | 0.0849 | 0.129 | 0.0256 | 0.8182 | 0.0455 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_v1` | `minimal_evidence` | 0.05 | 0.2273 | 0.0287 | 0.3396 | 0.0287 | 0.1026 | 0.2955 | 0.2273 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1` | `full_labels` | 0.05 | 0.1765 | 0.0 | 0.0 | 0.0 | 0.2 | 0.3571 | 0.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1` | `label_hidden_raw` | 0.05 | 0.1765 | 0.0506 | 0.0 | 0.0506 | 0.2 | 0.4286 | 0.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1` | `minimal_evidence` | 0.05 | 0.1765 | 0.0 | 0.1667 | 0.0 | 0.2 | 0.3571 | 0.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1` | `full_labels` | 0.05 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 0.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1` | `label_hidden_raw` | 0.05 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 0.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1` | `minimal_evidence` | 0.05 | 0.0 | 0.0 | 0.1389 | 0.0 | 0.0 | 1.0 | 0.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1` | `full_labels` | 0.05 | 0.0351 | 0.0 | 0.0 | 0.0 | 0.05 | 0.21 | 0.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1` | `label_hidden_raw` | 0.05 | 0.0351 | 0.0 | 0.0 | 0.0 | 0.05 | 0.21 | 0.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1` | `minimal_evidence` | 0.05 | 0.0351 | 0.0 | 0.0 | 0.0 | 0.05 | 0.21 | 0.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1` | `full_labels` | 0.05 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | 0.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1` | `label_hidden_raw` | 0.05 | 0.3387 | 0.0 | 0.5636 | 0.0 | 0.0 | 1.0 | 0.3387 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1` | `minimal_evidence` | 0.05 | 0.3387 | 0.0 | 0.5636 | 0.0 | 0.0 | 1.0 | 0.3387 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1` | `full_labels` | 0.05 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1` | `label_hidden_raw` | 0.05 | 0.1015 | 0.1085 | 0.0741 | 0.1085 | 0.0 | 1.0 | 0.1015 |
| `qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1` | `minimal_evidence` | 0.05 | 0.1015 | 0.0316 | 0.0741 | 0.0316 | 0.0 | 0.0 | 0.1015 |

## Interpretation

- If `label_hidden_raw` is close to `full_labels`, the verifier evidence is not merely copying explicit label fields.
- If `minimal_evidence` degrades, the method should be described as requiring structured but label-hidden execution evidence, not arbitrary sparse logs.
- These are held-out trace-group diagnostics under the T62 threshold-selection policy, not deployment safety certification.

## Hidden Fields

- `verified_effects`
- `unauthorized_effects`
- `effect_diff`
- `effects`
- `effect_verifier`
- `effect_verifier_rules`
- `candidate_effect_present`
- `label_unauthorized_effect`
- `label_absent_not_authorized`
