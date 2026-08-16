# Exemplar Learning Dossier

## Learned Structure

Security measurement and systems papers that survive adversarial review usually make the evaluation object concrete before presenting performance. The final manuscript adopts that pattern:

1. Define a pre-commit safety decision over side-effectful candidate actions.
2. Define the binding tuple that the mediator should recover.
3. Introduce stress axes that isolate invariance and sensitivity.
4. Compare existing methods under the same custom-stress frame.
5. Present a reference method, then use stress failures to motivate a more explicit local infrastructure prototype.
6. Close with audits, limitations, and artifact traceability.

## Patterns Transferred Without Copying Claims

| Pattern | Transfer To This Paper |
|---|---|
| Benchmark papers specify threat model, task object, and metrics before leaderboards. | The manuscript defines tool-effect binding, UPA, FDeny, coverage, and abstention before reporting E47/E48/E55 numbers. |
| Systems-security papers distinguish design goal, enforcement boundary, and assumptions. | The paper distinguishes controlled pre-commit mediation from production safety and reports explicit non-goals. |
| Strong guardrail papers include ablations and failure modes rather than only aggregate accuracy. | E50 is used as a bottleneck result, and E57 corrections are reported as audit evidence instead of hidden cleanup. |
| Artifact-oriented venues reward reproducible source mapping. | Every headline number is tied to local JSON/Markdown artifacts and numerator/denominator counts. |

## Result-Narrative Pattern

Each Results subsection should answer one promise from the Introduction:

- Promise: surface form is not a sufficient safety object. Result: existing methods have axis-specific capability but incomplete joint binding.
- Promise: a hard guard helps but exposes bottlenecks. Result: E48 improves boundedly; E50 fails resource/auth binding at high UPA.
- Promise: explicit authorization infrastructure can mediate more decisions. Result: E55-v2 improves coverage and observed unsafe pre-allow under a local contract.
- Promise: audits reduce obvious confounds. Result: E57 human audit and E57-v2 validity checks are reported with corrections and scope limits.

## Style Implication

Use direct security language: "pre-commit mediator", "candidate action", "realized effect", "authorized resource", "unsafe pre-allow", "safe false denial", and "coverage". Avoid broad claims such as "solves tool safety" or "guarantees authorization".
