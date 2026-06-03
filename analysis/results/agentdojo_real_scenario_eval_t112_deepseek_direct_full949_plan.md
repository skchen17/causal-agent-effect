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

No AgentDojo model calls were run in this invocation.

## Claim Boundary

- An inventory-only run is not empirical evidence for the method.
- A small smoke run is only an integration check; paper claims require broad suite/task coverage.
- Comparisons to AuthGraph must use the same benchmark version, suites, attacks, model family, and metrics where feasible.
