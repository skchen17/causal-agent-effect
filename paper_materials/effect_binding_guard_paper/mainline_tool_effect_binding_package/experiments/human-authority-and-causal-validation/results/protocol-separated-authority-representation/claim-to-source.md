# Claim-to-Source Map

| Claim | Result key | Source rows |
|---|---|---|
| Registration validates executable descriptors | `registration.*` | `registration-pair-audit.jsonl` |
| Typed effects match concrete transitions | `evaluation.descriptor_exact_match_rate` | `source-executions-and-typed-effects.jsonl` |
| Direct authorization metrics | `direct_metrics[]` | `authorization-decisions.jsonl` |
| Coarse views contain mixed cells | `collision_metrics[]` | `representation-collision-witnesses.jsonl` |
| Raw arguments collide under changed pre-state | `state_dependent.*` | evaluation rows grouped by `argument_group_id` |
