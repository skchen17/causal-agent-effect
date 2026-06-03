# T109 Local Side-Effect Boundary Benchmark

## Overall

| n | auth_n | unauth_n | unauth_block | unauth_commit | fd | auth_commit | local_http |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1000 | 200 | 800 | 1.0000 | 0.0000 | 0.0000 | 1.0000 | 55 |

## Case Type Breakdown

| case_type | n | unauth_block | unauth_commit | fd |
| --- | --- | --- | --- | --- |
| authorized_path | 200 | 0.0000 | 0.0000 | 0.0000 |
| deviation_under_authorized_constraint | 400 | 1.0000 | 0.0000 | 0.0000 |
| full_pipeline_unauthorized | 400 | 1.0000 | 0.0000 | 0.0000 |

## Claim Boundary

This benchmark executes local observable boundaries only: overlay filesystem, staged delete moves, local HTTP dry-run server, local outbox, and local browser-submit log. It does not validate provider-backed services, SaaS messaging, or HTTP browser automation.
