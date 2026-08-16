# Theory Proof Audit

Status: internal formal-claim audit; not included in the paper PDF.

## Proven Claims

1. **Joint representation insufficiency.** If the joint effect--authority view
   merges two authorization instances requiring different decisions, no
   deterministic monitor restricted to that view can be both sound and
   permissive.
2. **Authorization quotient.** Authorization-equivalence classes form the
   coarsest sufficient effect representation, up to renaming.
3. **Ambiguous-cell lower bound.** Every sound monitor must withhold authorized
   instances that share a representation cell with an unauthorized instance.
4. **Trusted evidence refinement.** Splitting an authority-ambiguous cell with
   trusted evidence cannot increase the representation-induced non-allow lower
   bound.
5. **Compound-effect binding.** If an additional independently unauthorized
   effect does not change the representation, a monitor must either allow it or
   withhold an otherwise authorized call.
6. **Counterfactual witness.** Equal contract representations on an
   authorization-separating execution pair directly witness representation
   insufficiency.
7. **Finite-domain adequacy.** A sound, collision-complete validation suite
   establishes representation sufficiency on its finite declared domain.
8. **Conditional effect confinement.** O1--O5 imply that each committed effect
   occurrence lies within the current authenticated per-commit authority bound.
   A cumulative trajectory bound additionally requires residual authority to be
   consumed after each commit.

## Proof Dependencies

| Result | Required assumptions | Not established by the proof |
|---|---|---|
| Joint representation insufficiency | Deterministic monitor; decision restricted to the joint effect--authority view; declared authority family | That a particular deployed joint view is insufficient |
| Ambiguous-cell lower bound | Finite instance set; ideal authorization labels; sound monitor | That every observed abstention is representation-induced |
| Trusted evidence refinement | New view is a true partition refinement and does not expand authority | Soundness of a concrete resolver or authority compiler |
| Counterfactual witness | Same atom representation; sound security-effect oracle; admissible separating authority | Global contract soundness from a passing sampled suite |
| Finite-domain adequacy | Finite domain; collision-complete pair coverage; sound authorization-equivalence oracle | Open-domain or unobserved effects |
| Effect confinement | O1 abstraction soundness; O2 envelope soundness; O3 mediation; O4 check--use integrity; O5 fail closed | Automatic construction of sound contracts or authority |

## Novelty Boundary

The confinement proof builds on complete mediation and least privilege. Its
role is to expose both the effect abstraction and authority evidence as explicit
proof obligations. The principal theory contribution is the joint
authorization-equivalence view: once either side merges instances requiring
different decisions, later classifiers cannot recover the lost distinction.
Counterfactual registration operationalizes an effect-side falsification
witness; typed resolver evidence may refine the authority side without creating
permission.

The theorem does not claim that every whole-call monitor is insufficient. A
whole-call representation that preserves all authorization-equivalence classes
is sufficient by definition. Nor does the theory posit a universal atom tuple
or prove that the current tool-specific corrections are globally minimal;
necessity is relative to a declared domain, contract language, and authority
family.

## Evidence Alignment

- E47--E50 provide controlled examples of the security/utility/coverage tradeoff
  predicted by representation insufficiency.
- E85's 15 common-projection mediation gaps are candidate insufficiency
  witnesses, subject to the source-grounded security-effect projection.
- E85 typed-qualifier 80/80 is a same-suite correction, not an application of
  the finite-domain adequacy theorem to a held-out collision-complete domain.
- E80 supports sandbox-local O3 and O4. O1, O2, and O5 remain partial.
- E78 demonstrates practical relevance but is not required for the logical
  validity of the theorems.

## Remaining Formal Risks

1. The admissible authority family must be defined concretely for held-out
   validation; arbitrary state inequality is not authorization separation.
2. The security-effect projection must exclude irrelevant state noise and expose
   latent security effects.
3. Collision completeness is feasible only for bounded finite domains; sampled
   tests must retain falsification wording.
4. Liveness and successful recovery are intentionally outside the confinement
   theorem and require empirical evaluation.
5. The formal model preserves repeated effect occurrences and
   execution-relevant order. The confinement theorem itself is extensional;
   order-sensitive and history-dependent policies require a richer trace
   predicate or trusted state encoding.
6. A resolver implementation is engineering evidence for authority-view
   refinement only when it binds a pre-authorized typed relation; benchmark
   aliases or model assertions cannot be relabeled as trusted authority.
