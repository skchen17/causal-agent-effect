# T108 Independent Future-Constraint Compiler Stress Test

## Summary

| n | schema_valid | decision_acc | over_perm | over_restrict | env_allowed_rec | env_forbidden_rec | fc_allowed_rec_auth |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 600 | 1.0000 | 0.9583 | 0.0000 | 0.0417 | 0.7973 | 0.3222 | 0.7973 |

## Family Breakdown

| family | n | decision_acc | over_perm | over_restrict |
| --- | --- | --- | --- | --- |
| api_provider_dry_run | 75 | 0.6667 | 0.0000 | 0.3333 |
| browser_form | 75 | 1.0000 | 0.0000 | 0.0000 |
| draft_messaging | 75 | 1.0000 | 0.0000 | 0.0000 |
| file_cleanup | 90 | 1.0000 | 0.0000 | 0.0000 |
| http_status_check | 90 | 1.0000 | 0.0000 | 0.0000 |
| local_file_analysis | 105 | 1.0000 | 0.0000 | 0.0000 |
| tool_alias | 90 | 1.0000 | 0.0000 | 0.0000 |

## Claim Boundary

This compiler does not read `gold_authorized_envelope`, but it is still a deterministic task-text rule compiler tuned to the T102 task grammar. It is not yet an LLM compiler or evidence that arbitrary natural-language authorization can be extracted reliably.
