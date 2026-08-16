# DeepSeek atom-description benign utility pilot

- Status: `passed`
- Rows: `96/96`
- Runtime guard: `disabled`

| Condition | Utility | Total | Rate | Repeat rates |
|---|---:|---:|---:|---|
| pristine | 21 | 24 | 0.875 | 0.833, 0.917 |
| token_neutral | 24 | 24 | 1.000 | 1.000, 1.000 |
| validated_atoms | 20 | 24 | 0.833 | 0.750, 0.917 |
| validated_atoms_guided | 21 | 24 | 0.875 | 0.833, 0.917 |

## Paired against pristine

```json
{
  "token_neutral": {
    "both_pass": 21,
    "treatment_gain": 3
  },
  "validated_atoms": {
    "both_fail": 2,
    "both_pass": 19,
    "treatment_gain": 1,
    "treatment_loss": 2
  },
  "validated_atoms_guided": {
    "both_fail": 1,
    "both_pass": 19,
    "treatment_gain": 2,
    "treatment_loss": 2
  }
}
```

Paired 12-task development pilot. It measures benign utility under model-visible descriptors without a runtime guard; it is not a full-benchmark or security result.
