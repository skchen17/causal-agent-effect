# T104 Pre-Commit Blocking Benchmark

## Overall

| n | auth_n | unauth_n | unauth_block | unauth_commit | fd | auth_commit |
| --- | --- | --- | --- | --- | --- | --- |
| 1000 | 200 | 800 | 1.0000 | 0.0000 | 0.0000 | 1.0000 |

## Case Type Breakdown

| case_type | n | unauth_block | unauth_commit | fd | auth_commit |
| --- | --- | --- | --- | --- | --- |
| authorized_path | 200 | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
| deviation_under_authorized_constraint | 400 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| full_pipeline_unauthorized | 400 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |

## Family Breakdown

| family | n | unauth_block | unauth_commit | fd |
| --- | --- | --- | --- | --- |
| api_provider_dry_run | 125 | 1.0000 | 0.0000 | 0.0000 |
| browser_form | 125 | 1.0000 | 0.0000 | 0.0000 |
| draft_messaging | 125 | 1.0000 | 0.0000 | 0.0000 |
| file_cleanup | 150 | 1.0000 | 0.0000 | 0.0000 |
| http_status_check | 150 | 1.0000 | 0.0000 | 0.0000 |
| local_file_analysis | 175 | 1.0000 | 0.0000 | 0.0000 |
| tool_alias | 150 | 1.0000 | 0.0000 | 0.0000 |

## Claim Boundary

This is an instrumented local pre-commit benchmark. It uses staged local effects, dry-run network counters, local outbox entries, and simulated browser-submit commits. It does not contact live external services or delete real user files. Provider-backed and deployed-runtime validation remain future external-validity work.
