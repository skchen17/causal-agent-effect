# Concrete-Atom Authorizer Mechanism Check

Status: `passed`.

The run evaluates 20 ordered authorization queries over 10 frozen executions of 5 ToolSandbox tools.

| View | UPA | False deny | Coverage | Accuracy |
|---|---:|---:|---:|---:|
| `whole_call_tool_name` | 8/8 (1.000) | 0/12 (0.000) | 1.000 | 0.600 |
| `raw_arguments_exact` | 0/8 (0.000) | 2/12 (0.167) | 1.000 | 0.900 |
| `common_effect_atoms` | 4/8 (0.500) | 0/12 (0.000) | 1.000 | 0.800 |
| `concrete_effect_atoms` | 0/8 (0.000) | 0/12 (0.000) | 1.000 | 1.000 |
| `source_effect_oracle` | 0/8 (0.000) | 0/12 (0.000) | 1.000 | 1.000 |

## Interpretation Boundary

This is a finite, source-executed mechanism check. The authority bound for each query is another observed concrete-effect multiset, not a human-authored deployment policy. The result tests whether each representation can implement that fixed relation; it does not establish open-domain contract soundness, complete authorization, or production safety.
