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
| workspace | 40 | 14 | direct | none |
| slack | 21 | 5 | direct | none |
| travel | 20 | 7 | direct | none |
| banking | 16 | 9 | direct | none |

## Results

| suite | model | defense | n attacked | UR | A.UR | ASR |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| workspace | deepseek-v4-flash | none | 560 | 0.8000 | 0.8786 | 0.0000 |
| slack | deepseek-v4-flash | none | 105 | 0.9524 | 0.9238 | 0.1238 |
| travel | deepseek-v4-flash | none | 140 | 0.8000 | 0.7714 | 0.0071 |
| banking | deepseek-v4-flash | none | 144 | 0.9375 | 0.9236 | 0.1806 |

Injection task utility is reported in the JSON artifact as `injection_task_utility`. Low values mean ASR should be interpreted cautiously because some attacker goals are not reliably solved as standalone user tasks by the evaluated model.

## Claim Boundary

- An inventory-only run is not empirical evidence for the method.
- A small smoke run is only an integration check; paper claims require broad suite/task coverage.
- Comparisons to AuthGraph must use the same benchmark version, suites, attacks, model family, and metrics where feasible.
