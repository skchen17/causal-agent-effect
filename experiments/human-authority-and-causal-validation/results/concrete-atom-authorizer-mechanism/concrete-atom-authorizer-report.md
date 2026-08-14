# Concrete-Atom Authorizer Mechanism Check

Status: `passed`.

The run evaluates 232 ordered authorization queries over 32 frozen executions of 5 ToolSandbox tools.

| View | UPA | False deny | Coverage | Accuracy |
|---|---:|---:|---:|---:|
| `whole_call_tool_name` | 150/150 (1.000) | 0/82 (0.000) | 1.000 | 0.353 |
| `raw_arguments_exact` | 14/150 (0.093) | 28/82 (0.341) | 1.000 | 0.819 |
| `common_effect_atoms` | 85/150 (0.567) | 0/82 (0.000) | 1.000 | 0.634 |
| `concrete_effect_atoms` | 0/150 (0.000) | 0/82 (0.000) | 1.000 | 1.000 |
| `source_effect_oracle` | 0/150 (0.000) | 0/82 (0.000) | 1.000 | 1.000 |

## Interpretation Boundary

This is a finite, source-executed mechanism check. The authority bound for each query is another observed concrete-effect multiset, not a human-authored deployment policy. The result tests whether each representation can implement that fixed relation; it does not establish open-domain contract soundness, complete authorization, or production safety.
