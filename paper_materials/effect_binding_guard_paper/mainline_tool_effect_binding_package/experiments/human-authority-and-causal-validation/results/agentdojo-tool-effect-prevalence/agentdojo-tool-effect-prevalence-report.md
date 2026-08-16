# AgentDojo Tool-Effect Prevalence Census

- Status: `passed`
- Population: `97` official benign tasks and `339` sequentially replayed calls.
- Tool coverage: `55/74 = 0.743`.
- Effectful calls: `100/339 = 0.295`.
- Effectful observed tools: `23/55 = 0.418`.
- Compound calls: `17/100 = 0.170` of effectful calls.
- Heterogeneous compound calls: `13/100 = 0.130`.
- Multi-target calls: `7/100 = 0.070`.
- Cross-namespace calls: `13/100 = 0.130`.
- Maximum logical units in one call: `6`.

## Interpretation

The official benign trajectories contain concrete source-executed examples in which one tool call changes multiple independently addressable objects, principals, or subsystems. This establishes within-benchmark prevalence of the representation problem; it does not establish ecosystem-wide prevalence or contract completeness.

## Evidence Boundary

The census estimates prevalence only in AgentDojo v1.1.2 official benign ground-truth trajectories. It is not an ecosystem-wide estimate, an attack evaluation, or proof that the normalization is complete for unseen tools and states.

## Limitations

- Official benign trajectories cover only the observed 55 of 74 tool instances.
- Logical effect normalization is a frozen benchmark-state oracle, not independent human certification.
- The result measures AgentDojo v1.1.2 and does not estimate ecosystem-wide prevalence.
- No-op calls are retained; absence of a state delta in one reachable state does not prove a tool is read-only.
