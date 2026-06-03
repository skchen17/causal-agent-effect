# T107 Future-Constrained Result Audit

## Rate Metrics

| source | metric | count/n | rate | Wilson 95% CI | direction |
| --- | --- | --- | --- | --- | --- |
| future_constraint_compiler_eval_t102_v1.json | schema_validity | 600/600 | 1.0000 | [0.9936, 1.0000] | higher_better |
| future_constraint_compiler_eval_t102_v1.json | constraint_soundness | 600/600 | 1.0000 | [0.9936, 1.0000] | higher_better |
| future_constraint_compiler_eval_t102_v1.json | decision_accuracy | 600/600 | 1.0000 | [0.9936, 1.0000] | higher_better |
| future_constraint_compiler_eval_t102_v1.json | over_permission_error | 0/600 | 0.0000 | [0.0000, 0.0064] | lower_better |
| future_constraint_compiler_eval_t102_v1.json | over_restriction_error | 0/600 | 0.0000 | [0.0000, 0.0064] | lower_better |
| future_shadow_replay_t103_v1.json | unauthorized_block_rate | 400/400 | 1.0000 | [0.9905, 1.0000] | higher_better |
| future_shadow_replay_t103_v1.json | unauthorized_committed_action_rate | 0/400 | 0.0000 | [0.0000, 0.0095] | lower_better |
| future_shadow_replay_t103_v1.json | authorized_false_denial_rate | 0/200 | 0.0000 | [0.0000, 0.0188] | lower_better |
| future_shadow_replay_t103_v1.json | deviation_block_rate | 200/200 | 1.0000 | [0.9812, 1.0000] | higher_better |
| precommit_blocking_t104_v1.json | pre_effect_block_rate_unauthorized | 800/800 | 1.0000 | [0.9952, 1.0000] | higher_better |
| precommit_blocking_t104_v1.json | unauthorized_committed_action_rate | 0/800 | 0.0000 | [0.0000, 0.0048] | lower_better |
| precommit_blocking_t104_v1.json | authorized_false_denial_rate | 0/200 | 0.0000 | [0.0000, 0.0188] | lower_better |
| precommit_blocking_t104_v1.json | authorized_commit_rate | 200/200 | 1.0000 | [0.9812, 1.0000] | higher_better |
| shadow_real_divergence_t105_v1.json | faithful_allow_rate | 200/200 | 1.0000 | [0.9812, 1.0000] | higher_better |
| shadow_real_divergence_t105_v1.json | unsafe_nonallow_rate | 200/200 | 1.0000 | [0.9812, 1.0000] | higher_better |
| shadow_real_divergence_t105_v1.json | unsafe_deny_rate | 200/200 | 1.0000 | [0.9812, 1.0000] | context |
| shadow_real_divergence_t105_v1.json | unsafe_abstain_rate | 0/200 | 0.0000 | [0.0000, 0.0188] | context |

## Timing Metrics

| stage | n | mean_ms | median_ms | p95_ms | max_ms |
| --- | --- | --- | --- | --- | --- |
| T102_compile_validate | 600 | 0.0878 | 0.0836 | 0.1058 | 0.2065 |
| T103_shadow_plan_replay | 600 | 0.0164 | 0.0013 | 0.0688 | 0.1211 |
| T105_divergence_faithful | 200 | 0.0684 | 0.0606 | 0.1041 | 0.1274 |
| T105_divergence_unsafe | 200 | 0.1504 | 0.1357 | 0.1956 | 0.2121 |
| T104_build_precommit_cases | 1000 | 0.0760 | 0.0760 | 0.0760 | 0.0760 |

## Claim Register

| claim | status | boundary |
| --- | --- | --- |
| The future-constrained pipeline is implementable end-to-end in a local staged prototype. | supported_for_local_prototype | Does not imply provider-backed or deployed-runtime safety. |
| Compiled future constraints can avoid over-permission on the current T102 dataset. | supported_only_for_rule_gold_envelope | Not yet evidence for LLM compiler reliability or natural task authorization extraction. |
| Trace-locked replay and prefix guards can block constructed unauthorized deviations before staged commit. | supported_for_constructed_local_cases | Requires mediation, staging, and observable effects; no live external side effects tested. |
| The method is deploy-ready for real providers, SaaS messaging, or HTTP browser automation. | not_supported | Requires T109/T111-style real boundary and external-validity experiments. |
| The current results prove superiority over existing agent-security defenses. | not_supported | Requires T110 ablations and faithful baselines. |

## Paper-Use Guidance

Use T102-T106 as controlled local prototype evidence. Do not describe these results as deployed-agent validation, provider-backed safety, HTTP browser automation, SaaS messaging protection, or superiority over existing defenses. Main-conference claims require T108 non-gold compiler stress, T109 real local side-effect boundaries, T110 ablations/baselines, and T111 external validity.
