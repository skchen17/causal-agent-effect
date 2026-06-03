# T110 Future-Constrained Ablation and Baseline

## Main Action-Level Results

| policy | n | U-Commit | Unauth Precommit Block | FDeny | Unsafe Before Block | Abstain |
| --- | --- | --- | --- | --- | --- | --- |
| full_future_constrained | 1000 | 0.0000 (0/800; 0.0000-0.0048) | 1.0000 (800/800; 0.9952-1.0000) | 0.0000 (0/200; 0.0000-0.0188) | 0.0000 (0/800; 0.0000-0.0048) | 0.0000 (0/1000; 0.0000-0.0038) |
| no_shadow_prefix_guard_only | 1000 | 0.0000 (0/800; 0.0000-0.0048) | 1.0000 (800/800; 0.9952-1.0000) | 0.0000 (0/200; 0.0000-0.0188) | 0.0000 (0/800; 0.0000-0.0048) | 0.0000 (0/1000; 0.0000-0.0038) |
| t108_text_rule_full_system | 1000 | 0.0000 (0/800; 0.0000-0.0048) | 1.0000 (800/800; 0.9952-1.0000) | 0.1250 (25/200; 0.0861-0.1780) | 0.0000 (0/800; 0.0000-0.0048) | 0.0000 (0/1000; 0.0000-0.0038) |
| effect_resource_status_boundary | 1000 | 0.0000 (0/800; 0.0000-0.0048) | 1.0000 (800/800; 0.9952-1.0000) | 0.0000 (0/200; 0.0000-0.0188) | 0.0000 (0/800; 0.0000-0.0048) | 0.0000 (0/1000; 0.0000-0.0038) |
| effect_status_only | 1000 | 0.1500 (120/800; 0.1269-0.1764) | 0.8500 (680/800; 0.8236-0.8731) | 0.0000 (0/200; 0.0000-0.0188) | 0.0000 (0/800; 0.0000-0.0048) | 0.0000 (0/1000; 0.0000-0.0038) |
| tool_whitelist_only | 1000 | 0.9375 (750/800; 0.9185-0.9523) | 0.0625 (50/800; 0.0477-0.0815) | 0.0000 (0/200; 0.0000-0.0188) | 0.0000 (0/800; 0.0000-0.0048) | 0.0000 (0/1000; 0.0000-0.0038) |
| no_replay_lock_or_prefix_guard | 1000 | 0.5000 (400/800; 0.4654-0.5346) | 0.5000 (400/800; 0.4654-0.5346) | 0.0000 (0/200; 0.0000-0.0188) | 0.0000 (0/800; 0.0000-0.0048) | 0.0000 (0/1000; 0.0000-0.0038) |
| no_staging_posthoc_guard | 1000 | 1.0000 (800/800; 0.9952-1.0000) | 0.0000 (0/800; 0.0000-0.0048) | 0.0000 (0/200; 0.0000-0.0188) | 1.0000 (800/800; 0.9952-1.0000) | 0.0000 (0/1000; 0.0000-0.0038) |
| no_future_constraint_allow_all | 1000 | 1.0000 (800/800; 0.9952-1.0000) | 0.0000 (0/800; 0.0000-0.0048) | 0.0000 (0/200; 0.0000-0.0188) | 0.0000 (0/800; 0.0000-0.0048) | 0.0000 (0/1000; 0.0000-0.0038) |
| deny_all | 1000 | 0.0000 (0/800; 0.0000-0.0048) | 1.0000 (800/800; 0.9952-1.0000) | 1.0000 (200/200; 0.9812-1.0000) | 0.0000 (0/800; 0.0000-0.0048) | 0.0000 (0/1000; 0.0000-0.0038) |

## Case-Type Breakdown

| policy | case_type | n | U-Commit | FDeny |
| --- | --- | --- | --- | --- |
| full_future_constrained | authorized_path | 200 | n/a | 0.0000 (0/200; 0.0000-0.0188) |
| full_future_constrained | deviation_under_authorized_constraint | 400 | 0.0000 (0/400; 0.0000-0.0095) | n/a |
| full_future_constrained | full_pipeline_unauthorized | 400 | 0.0000 (0/400; 0.0000-0.0095) | n/a |
| no_shadow_prefix_guard_only | authorized_path | 200 | n/a | 0.0000 (0/200; 0.0000-0.0188) |
| no_shadow_prefix_guard_only | deviation_under_authorized_constraint | 400 | 0.0000 (0/400; 0.0000-0.0095) | n/a |
| no_shadow_prefix_guard_only | full_pipeline_unauthorized | 400 | 0.0000 (0/400; 0.0000-0.0095) | n/a |
| t108_text_rule_full_system | authorized_path | 200 | n/a | 0.1250 (25/200; 0.0861-0.1780) |
| t108_text_rule_full_system | deviation_under_authorized_constraint | 400 | 0.0000 (0/400; 0.0000-0.0095) | n/a |
| t108_text_rule_full_system | full_pipeline_unauthorized | 400 | 0.0000 (0/400; 0.0000-0.0095) | n/a |
| effect_resource_status_boundary | authorized_path | 200 | n/a | 0.0000 (0/200; 0.0000-0.0188) |
| effect_resource_status_boundary | deviation_under_authorized_constraint | 400 | 0.0000 (0/400; 0.0000-0.0095) | n/a |
| effect_resource_status_boundary | full_pipeline_unauthorized | 400 | 0.0000 (0/400; 0.0000-0.0095) | n/a |
| effect_status_only | authorized_path | 200 | n/a | 0.0000 (0/200; 0.0000-0.0188) |
| effect_status_only | deviation_under_authorized_constraint | 400 | 0.1500 (60/400; 0.1183-0.1883) | n/a |
| effect_status_only | full_pipeline_unauthorized | 400 | 0.1500 (60/400; 0.1183-0.1883) | n/a |
| tool_whitelist_only | authorized_path | 200 | n/a | 0.0000 (0/200; 0.0000-0.0188) |
| tool_whitelist_only | deviation_under_authorized_constraint | 400 | 0.9375 (375/400; 0.9094-0.9573) | n/a |
| tool_whitelist_only | full_pipeline_unauthorized | 400 | 0.9375 (375/400; 0.9094-0.9573) | n/a |
| no_replay_lock_or_prefix_guard | authorized_path | 200 | n/a | 0.0000 (0/200; 0.0000-0.0188) |
| no_replay_lock_or_prefix_guard | deviation_under_authorized_constraint | 400 | 1.0000 (400/400; 0.9905-1.0000) | n/a |
| no_replay_lock_or_prefix_guard | full_pipeline_unauthorized | 400 | 0.0000 (0/400; 0.0000-0.0095) | n/a |
| no_staging_posthoc_guard | authorized_path | 200 | n/a | 0.0000 (0/200; 0.0000-0.0188) |
| no_staging_posthoc_guard | deviation_under_authorized_constraint | 400 | 1.0000 (400/400; 0.9905-1.0000) | n/a |
| no_staging_posthoc_guard | full_pipeline_unauthorized | 400 | 1.0000 (400/400; 0.9905-1.0000) | n/a |
| no_future_constraint_allow_all | authorized_path | 200 | n/a | 0.0000 (0/200; 0.0000-0.0188) |
| no_future_constraint_allow_all | deviation_under_authorized_constraint | 400 | 1.0000 (400/400; 0.9905-1.0000) | n/a |
| no_future_constraint_allow_all | full_pipeline_unauthorized | 400 | 1.0000 (400/400; 0.9905-1.0000) | n/a |
| deny_all | authorized_path | 200 | n/a | 1.0000 (200/200; 0.9812-1.0000) |
| deny_all | deviation_under_authorized_constraint | 400 | 0.0000 (0/400; 0.0000-0.0095) | n/a |
| deny_all | full_pipeline_unauthorized | 400 | 0.0000 (0/400; 0.0000-0.0095) | n/a |

## Interpretation

- `full_future_constrained` is the T109-equivalent full local pipeline over the T102/T109 case taxonomy.
- `no_shadow_prefix_guard_only` matches the full pipeline on this local benchmark, so this benchmark does not by itself prove the independent necessity of shadow execution.
- `no_replay_lock_or_prefix_guard` isolates real-stage drift after an authorized future constraint; it commits unauthorized effects in deviation cases.
- `no_staging_posthoc_guard` can still detect violations after execution, but unsafe effects have already crossed the commit boundary.
- `effect_resource_status_boundary` is a strong deterministic boundary baseline. If it matches the full system, the current local benchmark supports prevention feasibility but not superiority over handcrafted resource-aware guards.
- `t108_text_rule_full_system` uses an independent task-text compiler rather than the gold envelope. Its false denials quantify compiler brittleness.

## Claim Boundary

T110 is an action-level local ablation over controlled T102/T109 artifacts. It does not validate provider-backed services, SaaS messaging, HTTP browser automation, or deployed-agent runtime logs. Perfect local rates should be cited with their Wilson intervals and not as deployed safety guarantees.
