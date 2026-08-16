# Theory-Driven Experiment Plan

This plan derives each experiment from a formal claim. It avoids adding
benchmarks that do not discriminate between the theory and simpler
alternatives.

## Current Decision

The theoretical implications are valid. Experiments A and B are complete:
transparent E48/E50 representations produce explicit
authorization-separating collision witnesses, and an exhaustive 54-call
AgentDojo domain provides the first bounded positive adequacy result. The next
priority is Experiment C: freeze held-out tools and interventions before
opening their results.

## Experiment A: Representation-Collision Witness Audit

**Status:** Complete. The audit records 288 mixed witness cells. On the E48
explicit-authority subset, the ideal effect--resource representation has no
observed collision, while the extracted effect--resource representation has 30
mixed cells and a 43-error lower bound. On repaired E50, the corresponding
figures are 0 versus 8 cells and a 10-error lower bound.

**Theory target:** Theorem 1 and the compound-effect corollary.

**Input:** Existing E47--E50 rows and generators.

**Required row artifact:**

- base and counterfactual execution contexts;
- monitored representation for each evaluated method;
- concrete projected effects;
- an explicit admissible separating authority bound;
- ideal decisions under that bound;
- monitor decisions;
- collision class identifier.

**Metrics:**

- number of authorization-separating representation cells;
- number of contexts in mixed-label cells;
- cell-wise unsafe/withholding lower bound;
- observed unsafe allow, false denial, abstention, and coverage;
- gap between observed error and the representation lower bound.

**Acceptance rule:** A claimed witness is valid only when equal representation
and a concrete separating authority are both recorded. Mere score
insensitivity is not enough.

**Reuse:** E48/E50 transparent guard representations can be regenerated without
new LLM inference. For TS-Guard and Safiron, only behavior is observable; equal
decisions do not prove equal internal representations. Their E47 rows remain
behavioral comparisons unless a documented checkpoint interface exposes the
decision representation. This experiment should precede expensive model runs.

## Experiment B: Exhaustive Finite-Domain Contract Validation

**Status:** Complete for the declared finite domain. Fifty-four calls to five
source-hash-bound AgentDojo tools execute without error. The reviewed common
contract has 118 authorization-separating pairs; the reviewed typed contract
has zero collisions and zero overpartition pairs.

**Theory target:** Theorem 2.

**Design:**

1. Freeze a small set of source-backed tools with finite argument and state
   domains.
2. Freeze the admissible authority-policy family before evaluating contracts.
3. Enumerate every reachable context in each finite domain.
4. Execute each context in a deterministic sandbox and project concrete
   security effects.
5. Group contexts by candidate representation.
6. Exhaustively test every within-cell pair for authorization equivalence.

**Compared representations:**

- tool name;
- whole-call scalar/summary;
- common eight-field atoms;
- common atoms plus typed effect-specific qualifiers.

**Required cases:**

- compound effects;
- multi-resource expansion;
- effect-bearing defaults;
- interaction-only effects;
- resource aliases and canonical identifiers;
- target-principal changes;
- operation/commit changes;
- visibility changes;
- provenance/control-source changes;
- genuine surface-invariant changes.

**Metrics:**

- representation cell count and compression ratio;
- authorization-separating collision count;
- collision lower bound;
- atom over-sensitivity on true placebos;
- exhaustive sufficiency pass/fail per finite domain;
- fields proven necessary relative to the frozen policy family.

**Acceptance rule:** Positive bounded-adequacy wording is allowed only when
enumeration, collision coverage, and oracle checks are complete. Otherwise the
result remains a falsification study.

## Experiment C: Held-Out Source-Grounded Validation

**Theory target:** External validity of the mediation-gap proposition.

**Protocol:**

1. Split development and held-out tools before typed qualifiers are designed.
2. Freeze held-out tool source hashes, base calls, policy family, intervention
   generator, and all cases.
3. Use actual surface mutations rather than identity copies.
4. Report registry-key isolation separately from executed interventions.
5. Preserve all failures; do not modify qualifiers after opening held-out
   results.

**Primary result:** Compare the original common representation and the frozen
typed representation on unseen tools and interventions.

**Acceptance rule:** Same-suite correction is diagnostic only. Generalization
requires a previously unopened held-out partition.

## Experiment D: Runtime Obligation Audit

**Theory target:** O3--O5 and Theorem 3.

**Existing support:** E80 already strongly supports sandbox-local O3 and O4.

**Remaining checks:**

- totalize all effect-bearing defaults before checking;
- record unresolved identities/defaults as non-allow;
- verify witness/call/state/contract/evidence hashes at execution;
- classify every non-allow reason;
- verify no unchecked side-effect path or repeated-call override.

**Acceptance rule:** This experiment does not establish O1 or O2. It only
establishes that the runtime enforces the contract and envelope it receives.

## Experiment E: Authority-Soundness Study

**Theory target:** O2.

**Design:**

- independently derive task authority from authenticated task inputs;
- prohibit attack labels and outcomes from review inputs;
- distinguish exact values, forbidden values, and typed resolvers;
- record which relations are manually specified, source-derived, resolver
  instantiated, or unsupported;
- independently audit a sample of manifests and disagreements.

**Metrics:**

- accepted, compilable, and runtime-ready task coverage;
- resolver and alias burden;
- authority agreement;
- unsafe expansion, false restriction, and abstention;
- authoring and review time.

**Acceptance rule:** If the same execution LLM can approve its own authority
expansion, report that mode as a recovery baseline rather than evidence of O2.

## Experiment F: Practical Agent Instantiation

**Theory target:** Security relevance and utility, not theorem validity.

**Protocol fixes before rerun:**

- one uniform context policy for all methods;
- cluster-aware statistics over user and injection tasks;
- same model, keys, evaluator, tool environment, and error policy;
- explicit domain-level results;
- complete utility, ASR, coverage, abstention, and recovery reporting.

**Role of existing E78:** It already supports benchmark relevance but includes
12 non-uniform context repairs and a large utility loss. It remains a bounded
system instance rather than proof of O1/O2.

## Execution Order

1. **A: collision witness audit -- complete.**
2. **B: exhaustive finite-domain validation -- complete.**
3. **C: held-out source-grounded validation -- next.** Tests generalization and removes
   the E85 post-hoc weakness.
4. **D: runtime obligation completion.** Extend E80 only where O5/default paths
   remain uncovered.
5. **F: uniform-context AgentDojo.** Re-establish practical tradeoffs under a
   clean comparison.
6. **E: independent authority study.** Required for a stronger system claim;
   not required for the representation theorem itself.
7. Long-horizon, adaptive, and second-model studies follow only after A--F
   produce a coherent evidence chain.

## Minimum Evidence Package

The theory-centered submission needs:

- explicit real representation-collision witnesses;
- one exhaustive finite-domain adequacy result;
- one frozen held-out source-grounded result;
- sandbox complete-mediation/check-use evidence;
- one same-protocol agent benchmark with utility;
- transparent failure and assumption accounting.

Without Experiments B and C, the theory remains logically valid but the
counterfactual method lacks positive independent evidence.
