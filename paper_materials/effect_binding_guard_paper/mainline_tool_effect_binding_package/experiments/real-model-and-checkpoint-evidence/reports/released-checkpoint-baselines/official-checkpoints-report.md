# B8-official / E67 Released Checkpoint Baselines

Claim boundary: these are released checkpoints evaluated on this paper's adapted label-hidden common-input stress view. The run is not an original ToolSafe, TS-Guard, or Safiron benchmark reproduction.

| Model | Dataset | Rows | UPA | FDeny | Coverage | Abstain | Accuracy | Parse-valid |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| TS-Guard | E55-v2 | 600 | 0.656 | 0.016 | 0.930 | 0.070 | 0.512 | 0.930 |
| TS-Guard | E60 | 480 | 1.000 | 0.000 | 1.000 | 0.000 | 0.500 | 1.000 |
| TS-Guard | E61 artifact-generated | 300 | 0.189 | 0.000 | 0.993 | 0.007 | 0.923 | 0.993 |
| TS-Guard | E61 external subset | 156 | 0.493 | 0.045 | 0.660 | 0.340 | 0.231 | 0.660 |
| Safiron | E55-v2 | 600 | 0.094 | 0.631 | 1.000 | 0.000 | 0.572 | 1.000 |
| Safiron | E60 | 480 | 0.917 | 0.121 | 1.000 | 0.000 | 0.471 | 1.000 |
| Safiron | E61 artifact-generated | 300 | 0.063 | 0.217 | 1.000 | 0.000 | 0.840 | 1.000 |
| Safiron | E61 external subset | 156 | 0.179 | 0.182 | 1.000 | 0.000 | 0.821 | 1.000 |
