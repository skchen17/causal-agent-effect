# T102 Future Constraint Compiler Evaluation

## Compiler Summary

| compiler | n | schema_valid | sound_viol | decision_acc | over_perm | over_restrict | allowed_rec | forbidden_rec | ask_user |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rule_v1_gold_auth | 600 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 0.0000 |

## Family Breakdown

| family | n | sound_viol | decision_acc | over_perm | over_restrict | ask_user |
| --- | --- | --- | --- | --- | --- | --- |
| api_provider_dry_run | 75 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| browser_form | 75 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| draft_messaging | 75 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| file_cleanup | 90 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| http_status_check | 90 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| local_file_analysis | 105 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| tool_alias | 90 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |

## Claim Boundary

This evaluates the T102 constraint compiler only. It does not show shadow execution, trace-locked replay, or real pre-commit blocking; those are T103/T104.
