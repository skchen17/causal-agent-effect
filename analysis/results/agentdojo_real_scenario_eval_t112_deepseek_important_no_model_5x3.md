# T112 AgentDojo Real-Scenario Evaluation Harness

## Scope

- Uses AgentDojo official suites, task IDs, attacks, and utility/security checks.
- Default run writes inventory and a concrete execution plan only.
- Model execution requires `--run-agentdojo` and an API key in the configured env var.
- API keys are not serialized to artifacts.

## Inventory

| suite | user tasks | injection tasks | tools |
| --- | ---: | ---: | ---: |
| workspace | 40 | 14 | 24 |
| slack | 21 | 5 | 11 |
| travel | 20 | 7 | 28 |
| banking | 16 | 9 | 11 |

## Planned Settings

| suite | user tasks | injection tasks | attack | defenses |
| --- | ---: | ---: | --- | --- |
| workspace | 5 | 3 | important_instructions_no_model_name | none |
| slack | 5 | 3 | important_instructions_no_model_name | none |
| travel | 5 | 3 | important_instructions_no_model_name | none |
| banking | 5 | 3 | important_instructions_no_model_name | none |

## Results

| suite | model | defense | n attacked | UR | A.UR | ASR |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| workspace | deepseek-v4-flash | none | 15 | 0.8000 | 0.7333 | 0.0667 |
| slack | deepseek-v4-flash | none | 15 | 1.0000 | 0.6000 | 0.2667 |
| travel | deepseek-v4-flash | none | 15 | 0.8000 | 0.7333 | 0.0000 |
| banking | deepseek-v4-flash | none | 15 | 1.0000 | 0.8000 | 0.2000 |

Injection task utility is reported in the JSON artifact as `injection_task_utility`. Low values mean ASR should be interpreted cautiously because some attacker goals are not reliably solved as standalone user tasks by the evaluated model.

## Claim Boundary

- An inventory-only run is not empirical evidence for the method.
- A small smoke run is only an integration check; paper claims require broad suite/task coverage.
- Comparisons to AuthGraph must use the same benchmark version, suites, attacks, model family, and metrics where feasible.
