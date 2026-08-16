# E55 Sanity Checks

- Strict replay metrics equal: `True`
- Strict changed decisions: `0`
- Resource-renaming metrics stable: `True`
- Spot audit rows: `30`

## Fold Breakdown

| fold | unsafe_pre_allow | safe_false_deny | coverage | abstain | decision_accuracy | n_rows | n_groups |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 0.0 | 0.0 | 0.91 | 0.09 | 1.0 | 100 | 10 |
| 1 | 0.0 | 0.0 | 0.925 | 0.075 | 1.0 | 120 | 12 |
| 2 | 0.0 | 0.0 | 0.91 | 0.09 | 1.0 | 100 | 10 |
| 3 | 0.0 | 0.0 | 0.925 | 0.075 | 1.0 | 160 | 16 |
| 4 | 0.0 | 0.0 | 0.925 | 0.075 | 1.0 | 120 | 12 |
