# Title Positioning Note

## Recommendation

Keep Title A for the current submission draft:

`Tool-Effect Binding in LLM Agents: Counterfactual Measurement and Pre-Commit Authorization`

Reason: E61 external subset and B8 strengthen the evaluation, but the paper is still a measurement-plus-abstraction-plus-artifact-bounded authorization paper. A pure system title would over-emphasize deployment-ready authorization.

## Title A

`Tool-Effect Binding in LLM Agents: Counterfactual Measurement and Pre-Commit Authorization`

- Problem emphasis: binding tool actions to effects/resources/authorization/provenance.
- Method emphasis: counterfactual measurement plus pre-commit authorization.
- Evidence-chain fit: covers E48/E50 measurement, E55-v2 local contract, E60/E61 transfer/trace evidence, E62/E63 mechanism/burden, and E64/B8 baselines.
- Overclaim risk: low; it does not imply production authorization.
- NDSS first impression: security problem framing with measurement and mitigation, closest to the actual paper arc.
- Recommendation: strongest current choice.

## Title B

`Atom-Level Pre-Commit Authorization for Tool-Using LLM Agents`

- Problem emphasis: authorization system design.
- Method emphasis: atom-level mediation.
- Evidence-chain fit: fits E55-v2/E60/E61/E62/E63/E64, but under-covers E48/E50 counterfactual measurement and existing-method diagnosis.
- Overclaim risk: medium; may create expectations of a complete authorization system.
- NDSS first impression: stronger systems paper signal, but reviewers may expect deployment integration and production-grade policy infrastructure.
- Recommendation: use only if the paper is later rewritten into a system-centered submission.

## Title C

`Tool Calls Are Containers: Effect-Resource-Operation Binding for LLM-Agent Safety`

- Problem emphasis: the core atom insight that tool calls are under-decomposed containers.
- Method emphasis: effect-resource-operation binding.
- Evidence-chain fit: strong for E50 granularity failure and atom abstraction; weaker for provenance/authorization and B8 baseline framing.
- Overclaim risk: medium; "safety" is broader than the evidence.
- NDSS first impression: memorable but less formal; may read as a workshop-style title.
- Recommendation: viable alternate if the abstract foregrounds the atom abstraction more than the measurement framework.

## Title D

`Effect-Resource-Operation Binding for Safe Tool-Using LLM Agents`

- Problem emphasis: atom fields and safety.
- Method emphasis: binding, but less explicit about counterfactual measurement or pre-commit mediation.
- Evidence-chain fit: covers atoms and E50/E55/E60/E61, but hides the measurement framework and may understate authorization/provenance context.
- Overclaim risk: medium-high because "Safe Tool-Using LLM Agents" can sound like deployed safety.
- NDSS first impression: concise, but too broad for artifact-bounded evidence.
- Recommendation: not preferred unless the title is softened, e.g. `Effect-Resource-Operation Binding for Pre-Commit Tool Mediation`.

## Final Position

Do not change the LaTeX title in this pass. Title A remains the best match for the current evidence chain and claim boundary.
