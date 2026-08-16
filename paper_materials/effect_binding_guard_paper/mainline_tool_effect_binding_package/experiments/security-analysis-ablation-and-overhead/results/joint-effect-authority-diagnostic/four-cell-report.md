# Joint Effect–Authority Four-Cell Diagnostic

This report is fixed-trajectory admissibility analysis. It does not rerun the agent, execute tools, or estimate end-to-end ASR/utility.

## Four Cells

| Effect contract | Authority | Coverage | Successful benign trace retention | Successful attack-trace exposure |
|---|---|---:|---:|---:|
| current_contract | reviewed_authority | 195/195 (1.000) | 19/20 (0.950) | 1/5 (0.200) |
| current_contract | official_ground_truth_oracle_authority | 195/195 (1.000) | 19/20 (0.950) | 1/5 (0.200) |
| source_reviewed_contract | reviewed_authority | 181/195 (0.928) | 18/20 (0.900) | 1/5 (0.200) |
| source_reviewed_contract | official_ground_truth_oracle_authority | 180/195 (0.923) | 18/20 (0.900) | 1/5 (0.200) |

## Common-Support Attribution

- Common-support cases: `180`.
- Contract-side delta at reviewed authority: `0.0`.
- Authority-side delta at current contract: `0.0`.
- Joint delta: `0.0`.
- Source/current field agreement on reviewed tools: `True`.

## Authority and Scope Audit

- Reviewed/official-oracle trace-admissibility agreement: `195/195`.
- Official-admissible successful benign traces retained by reviewed authority: `19/19`.
- Utility-success benign traces containing an extra unofficial effect: `1`.
- Successful attacks with a privileged call blocked: `4/4`.
- Successful attacks without a privileged call: `1`.

## Claim Boundary

This is deterministic fixed-trajectory admissibility analysis, not a rerun of the agent and not an end-to-end ASR or utility result. The official-ground-truth oracle is an exact evaluation-only bound derived from benchmark user-task call chains; it is not independently justified user authority, may exclude valid alternative plans, and is never deployable input. The current runtime already uses reviewed projections for observation-only classification, so the zero effect-side delta is an integration consistency check rather than independent validation.
