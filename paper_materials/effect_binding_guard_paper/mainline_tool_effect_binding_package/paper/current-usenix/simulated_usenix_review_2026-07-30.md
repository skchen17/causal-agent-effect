# Simulated USENIX Security Review

Date: 2026-07-30  
Target: `paper/current-usenix/main.pdf` and its admitted evidence  
Stance: skeptical systems-security reviewer

## Recommendation

**Overall: 3/5 -- Borderline / Weak Reject**

| Dimension | Score | Assessment |
|---|---:|---|
| Security relevance | 5/5 | Precise pre-commit authorization problem for tool agents |
| Originality | 3/5 | Distinct representation obligation and executable collision test, but close to recent argument-provenance and contract work |
| Technical correctness | 4/5 | Formal results are correct under explicit assumptions; implementation discharges only a subset |
| Evaluation | 3/5 | Broad and unusually auditable, with direct attribution and transfer, but one model and severe utility loss |
| Clarity | 4/5 | Coherent spine and candid limitations; evidence density remains high |
| Reproducibility | 4/5 | Strong claim-to-source and fail-fast checks; release artifact is not yet complete |
| Confidence | 4/5 | High on the representation result; moderate on general systems impact |

The paper now contains a defensible USENIX contribution. The strongest claim is
not that atomization solves agent security, but that a pre-commit monitor must
preserve authorization-relevant distinctions among concrete effects, and that
source-executed counterfactuals can expose violations of this obligation.

The remaining acceptance risk is systems-level: the current runtime buys a
large attack-success reduction at a large task-utility cost, independently
executable authority covers only 26/97 tasks, and the complete end-to-end
comparison uses one victim checkpoint.

## Summary

The paper decomposes one tool call into independently authorizable effect
instances. It defines authorization equivalence, proves an indistinguishability
result for insufficient representations, and makes an
authorization-separating counterfactual collision an executable witness.
Candidate contracts are tested offline through controlled executions and then
used by a deterministic pre-commit monitor.

The evaluation combines controlled binding stress, observed representation
collisions, source-grounded interventions, an exhaustively enumerated finite
domain, a pre-registered ToolSandbox check, capacity-matched AgentDojo
comparisons, direct whole-call-versus-atom attribution, fixed AgentLAB transfer,
authority-interface measurements, ablations, call-path audits, and kernel cost.

## Strengths

1. **The failure mode is concrete.** The calendar example shows why a call can
   contain separately authorizable event, invitation, and visibility effects.
2. **The theory clarifies rather than renames prior principles.** Complete
   mediation and least privilege are inputs; authorization-sufficient effect
   representation is the paper's new obligation.
3. **Counterfactual validation has a precise security role.** It falsifies
   candidate call-to-effect abstractions rather than attempting to explain the
   model's internal reasoning.
4. **The evidence chain is strong.** Negative common-field results, post-hoc
   correction, held-out validation, runtime tradeoffs, non-evaluable rows, and
   applicability gaps are all retained.
5. **The primary comparison is now capacity matched within each case.** The
   54/627-to-2/627 matched attack result has row- and user-task-cluster
   intervals that exclude zero.
6. **The paper now includes direct mechanism evidence.** On the targeted
   applicability subset, only the monitor representation changes; the
   whole-call view permits 3/273 attack goals and atom fields permit none.
7. **Long-task transfer is no longer only prospective.** The fixed 303-case
   AgentLAB replay records 95/303 versus 0/303 attack goals and reconciles all
   1,439 executed guarded calls with pre-commit records.
8. **The claim boundary is unusually disciplined.** The paper does not claim
   production safety, open-domain soundness, Pareto dominance, or unrestricted
   adaptive robustness.

## Major Concerns

### 1. Utility and authority coverage remain the dominant systems weakness

On matched AgentDojo keys, benign utility falls from 63/97 to 33/97 and
attack-side utility from 345/627 to 207/627. Prompt Sandwiching retains
substantially more utility with ASR 8/627. On fixed AgentLAB attacks, task
utility falls from 180/303 to 87/303. Only 26/97 reviewed authority manifests
compile, and the full benign authority path records 152/426 abstentions.

These outcomes are compatible with the safety theorem but leave a practical
alternative explanation: much of the security gain comes from withholding
execution when authority or resolution infrastructure is missing. The paper
reports this honestly, but a systems reviewer may still judge the prototype too
conservative.

**Improvement:** prioritize executable authority and resolver coverage, then
rerun the same fixed protocols. Report recovery success after abstention and a
root-cause decomposition of utility loss. If coverage cannot improve, position
the runtime strictly as feasibility evidence and keep representation validation
as the primary contribution.

### 2. The headline runtime does not instantiate every theorem premise

The architecture requires independently justified task authority, while the
headline frozen profile uses a plan-derived envelope and only a smaller
reviewed-authority subset instantiates the stronger interface. O3/O4 are
supported by exact call-path audits; O1 is finite and source-specific; O2 is
partial.

The Method section now discloses this boundary, but readers can still connect
the full AgentDojo result too directly to the conditional confinement theorem.

**Improvement:** keep a visible obligation-to-evidence mapping in the body.
Describe the 726-key path as the evaluated frozen profile and the 26-task
authority path as an interface instantiation. Avoid any sentence implying that
the full benchmark discharges O1--O5 together.

### 3. External validity rests on one victim checkpoint

The common end-to-end result uses Qwen3-32B. The finite contract audits cover
five AgentDojo and five ToolSandbox tools. AgentLAB adds a different task
distribution but reuses Qwen3-32B and fixed saved attacks.

**Improvement:** a second matched victim model is the highest-value remaining
experiment. A smaller complete rerun on a predeclared representative subset is
preferable to another large custom stress, provided all methods share case
keys, capacity, evaluators, and failure handling.

### 4. Direct atom-granularity attribution is narrow

The 321-case comparison is correctly controlled, but selection is conditioned
on the atom-field monitor emitting feedback. Only three attack outcomes differ
between whole-call and atom-field views. This proves that granularity can
matter in the closed loop; it does not estimate how much of the full benchmark
gain comes from atomization.

**Improvement:** define the applicability subset before outcome inspection,
include argument-role/value/provenance and common-effect intermediate views,
and report both the targeted effect and its prevalence in the full benchmark.
Do not extrapolate 0/273 versus 3/273 to a benchmark-wide causal effect.

### 5. Contract minimality is policy relative and only partially tested

The finite-domain authority family makes unequal concrete effect multisets
separable. This is rigorous for effect fidelity, but it can reward
overpartitioning. The typed correction is also evaluated on the 80 cases that
revealed the common contract's gaps; ToolSandbox supplies held-out evidence but
remains small.

**Improvement:** add realistic coarser policy families and deletion tests that
identify which qualifier is necessary under which policy. Report both
collisions and overpartition or false denial. This would strengthen the claim
that the representation is authorization-relevant rather than merely an exact
serialization of observed state changes.

### 6. Baseline and missingness boundaries require careful reading

The capacity-matched protocol retains nine non-evaluable baseline trajectories.
All-key bounds show that this cannot reverse the main security conclusion, but
point estimates use different evaluable denominators. Several baseline rows are
local comparable adapters rather than original-protocol reproductions.

**Improvement:** keep the all-key bounds adjacent to the headline point
estimate, release every error row, and provide a compact input-contract table
for each baseline. Avoid ranking methods by small ASR differences when utility,
information access, or adapter fidelity differ.

### 7. Fixed AgentLAB replay is not adaptive long-horizon robustness

The transfer result is valuable, but the attacks are saved before evaluation.
It does not reproduce AgentLAB's adaptive generation or cumulative
optimization, and the utility loss is large.

**Improvement:** either retain the current fixed-replay wording or add a
predeclared adaptive generation pass. Do not describe fixed replay as a full
AgentLAB reproduction.

### 8. Artifact release remains a submission blocker

The evidence manifest passes, but the release ledger still lacks a clean
environment rerun, a complete artifact anonymity/credential scan, and an
anonymous stable URL. The Open Science appendix still contains a placeholder.

**Improvement:** build a curated artifact rather than upload the workspace,
reproduce all main tables from the documented environment, scan every packaged
file, freeze checksums, and insert the stable anonymous URL.

## Minor Concerns

1. The abstract is number dense. If further space is needed, retain one
   representation result, the main matched AgentDojo result, and the fixed
   transfer result; move secondary denominators to the body.
2. “Typed contract” should always mean effect-specific typed qualifiers, not a
   generally verified contract language.
3. The nine-field atom plus qualifier map is flexible. A short worked example
   should show what is fixed by the schema, derived from runtime evidence, and
   checked against authority.
4. The PACT-compatible comparison must remain labeled as a local encoding, not
   a PACT system reproduction.
5. Kernel latency is useful but secondary while recovery-model calls dominate
   end-to-end cost.
6. The body is exactly 13 pages. Any camera-ready expansion will require
   replacing text or moving another secondary result to the appendix.

## Questions for the Authors

1. What trusted component supplies the authority bound in the headline
   726-key path, and which parts are model proposed?
2. How many full-benchmark attack reductions require an atom-level distinction
   unavailable to a whole-call or argument-role monitor?
3. What fraction of utility loss is attributable to missing contracts, missing
   authority, unresolved identities, policy rejection, and failed replanning?
4. Would a realistic coarser authority family retain the same typed
   qualifiers, or reveal overpartition?
5. Does the main security--utility ordering hold on a second model?
6. How would adaptive AgentLAB generation change the fixed-replay result?

## Decision Rationale

The paper has moved from a synthetic local-contract proof to a coherent,
auditable representation-and-mediation paper. The theory, negative results,
capacity-matched comparison, direct granularity attribution, and fixed transfer
are sufficient to justify serious consideration.

I remain below weak accept because the deployable authority interface covers a
minority of tasks, task utility is roughly halved in both main end-to-end
settings, and generalization is shown for tools and traces but not for victim
models. A reviewer who values the representation theorem and unusually strict
claim boundaries may score this as weak accept; a systems-oriented reviewer is
likely to require better utility or a second model.
