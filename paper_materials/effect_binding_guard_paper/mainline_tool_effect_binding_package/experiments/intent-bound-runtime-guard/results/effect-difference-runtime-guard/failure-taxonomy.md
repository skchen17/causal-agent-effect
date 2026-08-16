# E77 Payload-Free Failure Taxonomy

Status: `passed`.

| Mode | Cases | Utility | Cases with replan feedback | Replan events | Terminal unexecuted calls |
|---|---:|---:|---:|---:|---:|
| benign | 97 | 33/97 (0.340) | 47 | 115 | 1 |
| attack | 629 | 207/629 (0.329) | 312 | 794 | 3 |

## Utility-Failure Strata

- benign: `{"effectful_calls_intercepted_no_effectful_commit": 35, "effectful_commit_and_replan_feedback": 8, "no_structured_tool_call": 1, "read_only_or_unregistered_tool_trajectory": 19, "terminal_unexecuted_call": 1}`
- attack: `{"effectful_calls_intercepted_no_effectful_commit": 229, "effectful_commit_and_replan_feedback": 35, "effectful_commit_without_replan_feedback": 19, "no_structured_tool_call": 6, "read_only_or_unregistered_tool_trajectory": 130, "terminal_unexecuted_call": 3}`

## Claim Boundary

Strata describe observed trajectory mechanics and association with utility; they do not identify a unique causal root cause. No prompt, injection payload, task text, model response, or tool-result body is copied into this artifact.
