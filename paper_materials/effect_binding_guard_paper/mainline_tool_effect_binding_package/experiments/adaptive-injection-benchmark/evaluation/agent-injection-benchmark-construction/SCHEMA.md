# E88 Artifact Schema

## `dataset_manifest.json`

Dataset-level version, counts, scoring rule, intended use, prohibited use, and claim boundary.

## `attack_family_manifest.json`

Public AgentDojo attack registry names and coarse family descriptions. It contains no payload strings.

## `static_case_manifest.jsonl`

One row per fixed public-template attack case:

- `case_id`: stable E88 identifier.
- `suite`, `user_task_id`, `injection_task_id`: AgentDojo case identity.
- `attack_family_id`, `agentdojo_attack_name`: attack template identity.
- `base_case_key_sha256`, `source_log_sha256`: frozen provenance.
- `adaptive_split`: goal-grouped development/test assignment.
- `payload_materialization`: local public-registry resolution method.
- `environment_evaluator`: deterministic benchmark evaluator.

## `benign_control_manifest.jsonl`

The 97 official benign task keys and provenance hashes.

## `adaptive_case_index.jsonl`

Payload-free references to E82 strategy/case pairs, including strategy ID, budget, observable feedback, evaluator, and explicit success predicate.

## `smoke_case_manifest.jsonl`

An 80-row diagnostic-only subset: five user tasks per suite under one development-only injection task, crossed with four fixed attack families. It is frozen before execution and is not paper-result eligible.

## `split_manifest.json`

Group-level adaptive split assignment. The grouping unit is `(suite, injection_task_id)`.

## `validation_report.json`

Machine gate for row counts, unique IDs, payload separation, environment scoring, hashes, split disjointness, and disabled external side effects.
