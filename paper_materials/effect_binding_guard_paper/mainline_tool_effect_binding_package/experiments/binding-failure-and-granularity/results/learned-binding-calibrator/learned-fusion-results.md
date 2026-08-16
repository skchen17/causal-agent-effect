# E49 Learned Effect-Binding Calibrator

- E48 rows: `822`
- Feature leakage free: `True`
- Local-Qwen parse-valid rate reused from E48: `0.995`

## Source-Balanced Alpha=0.10

| Split | Method | UPA | FDeny | Coverage | Abstain |
|---|---:|---:|---:|---:|---:|
| `source_balanced_seed0` | `logistic_calibrator:full:overlay=True` | 0.135 | 0.032 | 0.988 | 0.012 |
| `source_balanced_seed1` | `logistic_calibrator:full:overlay=True` | 0.095 | 0.000 | 0.988 | 0.012 |
| `source_balanced_seed2` | `logistic_calibrator:full:overlay=True` | 0.041 | 0.147 | 0.988 | 0.012 |
| `source_balanced_seed3` | `logistic_calibrator:full:overlay=True` | 0.108 | 0.000 | 0.988 | 0.012 |
| `source_balanced_seed4` | `logistic_calibrator:full:overlay=True` | 0.081 | 0.000 | 0.988 | 0.012 |

# E49 Claim Boundary

- E49 evaluates lightweight learned calibration over E48 non-oracle tuple features on controlled custom stress artifacts.
- The main model excludes construction metadata, source metadata, audit status, gold tuple fields, oracle outputs, and E48 globally calibrated policy decisions.
- Provenance hard overlay is part of the main method and is reported separately from learned risk fusion.
- Resource/auth and control-provenance stress sets are evaluation-only and are not used for training or threshold selection.
- Results do not establish production safety, a complete permission system, original-paper benchmark reproduction, or real deployed-agent readiness.
- If learned fusion does not improve over the E48 hard guard under source-balanced splits, the correct interpretation is calibration diagnostic evidence, not a solved guard.
