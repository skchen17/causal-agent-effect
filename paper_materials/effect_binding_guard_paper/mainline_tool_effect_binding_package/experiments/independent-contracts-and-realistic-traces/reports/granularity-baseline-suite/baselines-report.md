# E64 Baselines Report

B0-B7 are implemented under a common deployable input view. B8 is now implemented as a ToolSafe/TS-Guard-style released-guardrail comparable local adapter under the same label-hidden deployable-input restriction. B8 is not an original benchmark reproduction.

## B8 Summary

| Dataset | UPA | FDeny | Coverage | Abstain |
|---|---:|---:|---:|---:|
| E55-v2 | 0.435 | 0.095 | 0.900 | 0.100 |
| E60 | 0.533 | 0.200 | 1.000 | 0.000 |
| E61 artifact-generated | 0.189 | 0.222 | 1.000 | 0.000 |
| E61 external subset | 0.000 | 0.000 | 1.000 | 0.000 |

See `baselines/baseline_results.json` for B0-B7 and `baselines/b8_released_guardrail/results_b8_*.json` for B8. The main paper should describe B8 only as a comparable local adapter.
