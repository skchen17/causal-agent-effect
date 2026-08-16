# E85 Causal Effect-Contract Validation Protocol

## Question

Does a frozen effect contract preserve the security-relevant distinctions caused
by interventions on a tool call, its declared defaults, and trusted pre-state?

This is an execution-semantics test. It is separate from action-source
attribution, which intervenes on observations and reruns an agent to determine
why the agent proposed a call.

## Pair Protocol

For each base call and intervention:

1. clone the same pre-state;
2. hold prior action history, implementation version, nonintervened arguments,
   and the security-effect projection fixed;
3. execute base and mutated calls in separate sandboxes;
4. project each concrete state difference into security effects;
5. compile base and mutated calls through the candidate contract;
6. canonicalize aliases and ordering;
7. require every concrete effect in both branches to be represented by an atom;
8. compare concrete-effect, atom, and authorization relations.

Pairs are classified as `faithful_mediation`, `true_invariance`,
`mediation_gap`, or `over_sensitive`. Execution errors and unresolved dynamic
defaults are retained as unresolved failures rather than dropped.

## Intervention Families

- resource and canonical identity;
- target principal or recipient;
- operation and commit mode;
- visibility;
- provenance and control source;
- list expansion and multi-resource calls;
- omitted versus explicit defaults;
- pairwise and condition-triggered effects;
- surface and representation placebos;
- descriptor ablation and compatible-tool binding swaps.

## Current Phase

The finite controlled implementation is complete in
`e85_causal_effect_contract_validation`. It contains nine intervention pairs and
six contract variants. Its result validates the metric implementation and
failure detection only.

## AgentDojo Extension Gate

The next phase must define an independent security-effect projection for each
registered AgentDojo tool before reusing the existing E77 sandbox executor. It
must not classify arbitrary output differences as security effects. Main-paper
admission requires:

- exact case and intervention manifests frozen before execution;
- single-field, interaction, default, expansion, and placebo coverage;
- no gold label or attack-goal input to contract generation or runtime;
- row-level base/mutated state hashes, effect sets, atom sets, and decisions;
- mediation precision/recall, gap rate, effect-change miss rate, surface
  invariance, interaction coverage, and authorization-flip agreement;
- explicit unresolved and unsupported denominators;
- independent audit of a held-out effect-projection sample.

Passing the finite phase does not satisfy this gate.
