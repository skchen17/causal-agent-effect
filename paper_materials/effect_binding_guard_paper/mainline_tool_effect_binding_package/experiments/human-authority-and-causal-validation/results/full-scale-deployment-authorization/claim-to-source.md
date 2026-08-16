# Claim-to-Source Map

| Claim | Result artifact | Key or row source | Generating code |
|---|---|---|---|
| Registration counterfactuals validate the frozen descriptors | `full-scale-authorization-report.json` | `registration.descriptor_exact_set_match`, `registration.counterfactual_relation_accuracy` | `validate_registration` |
| Coarse representations contain policy-separating collisions | `full-scale-authorization-report.json` and `representation-collision-witnesses.jsonl` | `representation_capacity[*].n_mixed_cells` | `collision_audit` |
| Typed effects support complete direct authorization on the frozen domain | `full-scale-authorization-report.json` and `authorization-decisions.jsonl` | `direct_policy_metrics[validated_typed_effects]` | `authorize_observation` |
| Raw arguments collide under changed pre-state | `policy-separating-pair-audit.jsonl` | rows with `state_dependent=true` | `pair_audit` |
| Source and descriptor implementations agree on held-out effects | `heldout-source-executions.jsonl` | `descriptor_exact_set_match` | `source_effects`, `instantiate_descriptor` |
