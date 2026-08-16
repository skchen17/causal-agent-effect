# Existing Evidence Feasibility Against the Theory

## Decision

The next experiments can proceed, but current artifacts do not uniformly expose
the objects required by the representation-insufficiency theorem. E48/E50 and
E85 can be upgraded into explicit witnesses because their monitored
representations are implemented locally. Released neural checkpoints in E47
provide behavioral sensitivity evidence but do not expose an internal
representation \(\rho\); they cannot by themselves prove a representation
collision.

## Artifact Review

| Evidence | Concrete effects | Authority | Reconstructable representation | Decision | Theory use |
|---|---:|---:|---:|---:|---|
| E47 Phase-4 audit packet | Proposed realized effects are recorded | Authorized effects/resources and expected decision are recorded | Only for explicit proxy/local rule adapters | All method decisions are recorded | Behavioral partial-binding comparison; exact theorem witness only for transparent methods |
| E47 TS-Guard/Safiron | Sidecar effects and authorization are available | Yes, in the custom stress construction | No access to checkpoint-internal decision representation | Yes | Cannot claim internal representation collision; can report invariance or error under an authorization-separating intervention |
| E48 tuple guard | Effect/resource/authorization tuple is explicit | Yes | Yes | Yes | Can generate exact representation cells and collision lower bounds |
| E50 hard guard | Local matching components and policy oracle are explicit | Yes | Yes | Yes | Strongest existing source for resource/authorization collision witnesses |
| E85 common/typed projections | Canonical atoms and sandbox state deltas are recorded | No explicit separating authority bound per row | Yes | Relation pass/fail, not runtime decision | Can show execution-relation gaps now; requires frozen per-row admissible authority to become a formal Proposition witness |

## Consequences

1. Do not reinterpret every E47 model error as a proof of representation
   insufficiency. A model may observe a sufficient input and still reason
   incorrectly.
2. For transparent guards, serialize the exact representation used before the
   decision. Equality must be byte/canonical-structure equality, not merely
   equal final decisions.
3. Add an explicit `separating_authority` object and the two ideal decisions to
   every formal counterfactual witness.
4. Keep `state_delta_changed` separate from
   `authorization_decision_changed`. The former is an execution observation;
   only the latter establishes authorization inequivalence.
5. E85 needs true non-security surface mutations and must report descriptor-key
   isolation outside the executed intervention denominator.

## Immediate Feasible Work

- **No new LLM run:** regenerate E48/E50 transparent representation cells,
  separating policies, lower bounds, and observed outcomes.
- **Small source-backed run:** repair E85 surface controls and add frozen
  separating-authority labels.
- **New central experiment:** build a finite exhaustive source-backed domain for
  collision-complete validation.

These steps directly test the theory and should occur before another large
AgentDojo model run.
