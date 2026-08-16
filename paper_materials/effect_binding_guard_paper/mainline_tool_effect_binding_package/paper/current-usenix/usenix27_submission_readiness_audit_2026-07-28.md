# USENIX Security '27 Submission Readiness Audit

Date: 2026-07-28

## Executive Decision

The work is paper-worthy, but the current submission package does **not yet
meet a low-risk USENIX Security acceptance bar**. The main blocker is not a
logical error in the core theory. It is the gap between the conditional
security argument and the evidence currently available for its two hardest
premises:

- effect-abstraction soundness is established only on bounded finite domains;
- independently justified, executable authority covers only a minority of the
  AgentDojo benign tasks.

The full AgentDojo result shows a real attack-success reduction, but it also
shows a large utility loss and uses 12 disclosed context-capacity repairs.
The latest full-benign authority run further reduces utility to 26/97. These
results do not invalidate the method, but they prevent a claim that the current
system offers a generally favorable security--utility tradeoff.

If submitted unchanged, the likely rejection arguments are:

1. the defense is substantially more conservative than the strongest prompting
   baseline;
2. the authority interface is not available for most tasks;
3. the principal end-to-end result uses one model and a non-uniform context
   overlay;
4. long-horizon evidence is not strictly admissible yet;
5. the anonymous artifact and Open Science appendix are not submission-ready;
6. the novelty boundary against PACT, ContractGuard, commit-time authorization,
   Contract2Tool, MiniScope, and temporal/effect contract systems requires a
   direct representation-level comparison.

## Official Venue Requirements

Source:
https://www.usenix.org/conference/usenixsecurity27/call-for-papers/

USENIX Security '27 states that submissions are judged on originality,
relevance, scientific rigor, correctness, and clarity, and must be finished,
complete papers. The main body may contain at most 13 pages. An Open Science
appendix describing artifact access is mandatory.

| Requirement | Current status | Decision |
|---|---|---|
| Security relevance | Clear pre-commit authorization problem for tool agents | Pass |
| Originality | Distinct effect-level representation and executable collision witness, but close 2026 overlap exists | Partial pass |
| Scientific rigor | Strong fail-fast artifacts and negative-result retention; several main external-validity gaps remain | Partial pass |
| Correctness | Formal statements are conditionally correct; key assumptions remain only partially discharged | Conditional pass |
| Clarity | Main narrative is coherent, but the paper carries too many evidence layers and dense qualifications | Pass with revision |
| 13-page body | Conclusion ends on page 13 in the current official USENIX format | Pass, no remaining body-page margin |
| Open Science appendix | Present but contains no anonymous URL or runnable entry point | Fail |
| Anonymous artifact | Current paper is clean; release manifest and repository-wide scrub are incomplete | Fail |
| Complete paper | Latest full-benign, adaptive, and long-horizon statuses are not integrated | Fail |

## Theory Audit

### What is sound

1. **Representation insufficiency.** The indistinguishability argument is
   correct: if two execution contexts have the same monitored representation
   and an admissible authority requires different decisions, a deterministic
   monitor over that representation cannot be both sound and permissive.
2. **Counterfactual witness.** An authorization-separating pair with unchanged
   atoms is a valid witness against representation sufficiency, provided the
   concrete-effect oracle and separating authority are sound.
3. **Finite-domain adequacy.** Exhaustive absence of separating collisions
   establishes sufficiency on the declared finite domain and authority family.
4. **Conditional confinement.** O1--O5 imply per-commit confinement. Cumulative
   trajectory-prefix confinement additionally requires consumable residual
   authority; a fixed reusable bound provides only the pointwise result. The
   paper correctly states that this does not prove O1 or O2 for the
   implementation.
5. **Novelty boundary.** The draft does not rename complete mediation or least
   privilege. Its strongest theoretical contribution is the
   authorization-equivalence view and the executable counterexample.

### Corrections completed and remaining risks

The formalization now represents concrete execution as an ordered effect trace
and authorization as containment of effect-occurrence multisets. Repeated
transfers, invitations, and disclosures are no longer collapsed. The theorem
is explicitly scoped to per-commit extensional authority; residual authority is
required for cumulative quotas, while richer order- and history-sensitive
predicates are outside this theorem instance. The executable E80 model checks
5,832 single-commit cases and 1,259,712 two-step cases and includes the reusable
authority counterexample.

1. **O2 independence is underdefined operationally.** The paper says the bound
   is independently justified, but most task manifests are model-produced and
   only 26/97 compile after artifact review. The trusted interface that creates
   `B_q` needs a precise source-of-authority rule.
2. **O1 remains the hard assumption.** Passing sampled interventions only
   falsifies discovered gaps. It cannot certify constant, asynchronous,
   callback, remote, hidden, or malicious-tool effects.
3. **O4 is sandbox-local.** Signature reconciliation supports check--use
   integrity in the current executor but does not cover concurrent remote
   services or state changes between check and commit.
4. **Liveness is absent by design.** This is acceptable for a safety theorem,
   but recovery and task completion must carry more empirical weight because a
   deny-all monitor satisfies the safety side.

The proofs are sufficient as the formal component of a systems-security paper.
They cannot carry the paper without a strong implementation evaluation, and
the paper must not present them as an unconditional safety guarantee.

## Experimental Evidence Audit

| Evidence unit | What it supports | Current result | USENIX-level decision |
|---|---|---|---|
| E47 released-checkpoint stress | Existing guards bind some axes but not joint effect/resource/authority | Heterogeneous sensitivity; TS-Guard UPA 15.9%, Safiron UPA 54.5% | Adequate controlled counterexample; not prevalence or original-protocol reproduction |
| E48/E50 controlled stress | Resource/authorization granularity and extraction failures | E50 full guard UPA 46/120 at 221/240 coverage | Adequate mechanism diagnosis after repair; synthetic scope must remain explicit |
| Authorization collision audit | Direct theorem instantiation | Mixed representation cells force observable error lower bounds | Strong bridge from theory to artifacts |
| E85 source-grounded interventions | Common fields miss payload, time, recurrence, interaction, and defaults | Common 65/80; typed 80/80 on same cases | Strong falsification; typed correction is post-hoc and not independent |
| 56-call finite domain | Bounded sufficiency of typed contracts, including repeated-effect occurrences | 118 common-field pairs reduced to zero | Internally strong but small, source-specific, finite submultiset authority family |
| 32-context ToolSandbox held-out | Cross-source transfer without outcome-driven revision | 41 common-field pairs reduced to zero | Useful pre-registered evidence; five tools and 32 contexts remain narrow |
| E78 AgentDojo main comparison | End-to-end attack/utility behavior | ASR 53/629 to 3/629; BU 64/97 to 33/97; UA 342/629 to 207/629 | Security effect is statistically robust, but not Pareto-superior and strongly conservative |
| E78 uniform-context sensitivity | Whether the 12 capacity repairs create the main conclusion | On 714 common 65,536-token cases: ASR 53/618 to 2/618; BU 63/96 to 32/96; UA 341/618 to 205/618 | Pass as disclosed complete-case sensitivity; 12 cases are selected by proposed-method failure and cannot replace a matched 726-case result |
| E78 dependence audit | Robustness to shared task/injection clusters | Crossed-cluster ASR delta CI [-0.126, -0.041] | Pass; should replace or accompany row-only inference in paper |
| E80 mediation audit | Sandbox-local O3/O4 | 3,173/3,173 executed calls matched | Strong scoped implementation evidence |
| E81 ablations | Contribution of runtime mechanisms | Registry validation affects utility; most other switches have low/zero applicability | Partial; insufficient to establish necessity of all mechanisms |
| E84 reviewed-authority subset | Effect of executable authority on 26 tasks | ASR 5/169 to 1/169, non-significant; BU 20/26 to 15/26 | Local case study only |
| Full 97 benign authority run | Full-denominator authority utility and fail-closed behavior | BU 26/97; 152/426 abstains; zero unmanifested-effect allows | Valid negative result; high-coverage usability gate failed |
| E83 kernel overhead | Deterministic guard cost | 22.1--352.0 microseconds across measured configurations | Pass for kernel only |
| Historical trajectory timing | Observed complete-run cost | median 53.27 s to 85.54 s; paired ratio 1.36 | Descriptive only; not causal overhead |
| Bounded adaptive search | Worst-of-four public attack-family stress | ASR 4/40 to 1/40; utility 18/40 to 12/40 | Passed protocol, but small and non-significant; mixed tradeoff |
| E79 AgentLAB transfer | Effectful long-horizon transfer | 303 runs complete; 2/1,440 calls lack pre-commit records | Not admissible until wrapper repair and strict re-finalization |

## Main Alternative Explanations Still Open

1. **Conservative rejection.** Prompt Sandwiching has ASR 8/629 with BU 60/97
   and UA 362/629, versus the proposed method's ASR 3/629, BU 33/97, and UA
   207/629. The current method improves security but loses substantially more
   utility.
2. **Authority-interface bottleneck.** Only 26/97 reviewed task manifests are
   runtime-ready, and the full benign run succeeds on 26/97 tasks. This is
   evidence that O2 is not solved, not merely an implementation footnote.
3. **One-model dependence.** The main complete comparison uses Qwen3-32B.
   The 9B run audits mediation rather than reproducing the main security and
   utility result.
4. **Protocol asymmetry.** The proposed E78 row combines 714 original
   trajectories with 12 larger-context repairs. This must be replaced by a
   uniform-context row or treated as sensitivity rather than the clean primary
   comparison.
5. **Limited adaptive evidence.** The 40-case bounded search reduces attacks
   from four to one, but paired discordance is too small to support a broad
   adaptive-robustness claim.
6. **No admissible long-horizon result yet.** E79's raw diagnostic values must
   remain excluded until all executed calls have matching pre-commit records.

## Novelty and Related-Work Risk

The defensible novelty is:

> one tool call may realize several independently authorizable effects; a
> monitor must preserve the resulting authorization-equivalence classes, and
> source-executed counterfactual interventions can falsify a proposed
> call-to-effect abstraction before runtime use.

This remains distinguishable from:

- PACT, which binds provenance and semantic roles at argument level;
- MiniScope and Progent, which construct or enforce task-scoped privileges;
- AttriGuard and CausalArmor, which intervene on model context to explain why a
  call was proposed;
- Contract2Tool, which learns precondition/effect contracts for reliable tool
  filtering;
- Agent-C, which enforces temporal trace contracts.

However, PACT reports a stronger AgentDojo security--utility result across five
models, and Contract2Tool now uses the same "tool contract/effect" vocabulary.
ContractGuard treats effect integrity as the contract layer's load-bearing
assumption; recent commit-time authorization binds fresh authority witnesses to
durable effects. The paper now distinguishes argument provenance, contract
integrity, witness freshness, learned planning effects, temporal trace policies,
and independently authorizable realized effects. A direct PACT-compatible
effect-granularity comparison remains the highest-value originality-risk
reduction.

## Reproducibility and Submission Hygiene

- Core selected tests pass: 28/28 on collision, finite-domain, ToolSandbox,
  adaptive, full-benign, and E79 finalizer/runner checks.
- Current PDF compilation passes with no undefined citations/references,
  overfull boxes, broken markers, or local paths.
- All 32 cited keys have active BibTeX entries, all entries are cited, and the
  rebuilt PDF has no undefined citation or reference. Newly added close works
  use public arXiv metadata.
- The current evidence shim reproduces 324 rows, including the full-benign
  negative result and the 714-key uniform-context sensitivity. It preserves
  the failed 50-task utility gate as evidence while separately passing
  fixed-denominator, fail-closed, and privacy checks. It also gates the completed
  40-key/320-row bounded public-family search and its paired statistics. Final
  E79 remains pending.
- `artifact/manifest.json` is stale and fails final release gates.
- The Open Science appendix lacks the required anonymous stable URL and
  concrete runnable commands.
- The wider workspace contains many absolute paths and credential-like test
  strings. A curated release package must be built and scanned rather than
  uploading the workspace directly.
- USENIX permits AI-assisted preparation, but the human authors remain
  responsible for reviewing every AI-generated claim, result, reference, and
  code artifact. The existing AI artifact review cannot substitute for that
  submission-level author verification.

## Required Work Before Submission

Priority 0, submission blockers:

1. **Repair completed; full rerun in progress:** invalid-tool calls now receive
   deterministic pre-commit denial records, and the two affected E79 cases pass
   exact 16/16 signature reconciliation. Admit E79 only after the fresh
   303-case run passes full signature reconciliation.
2. **Full-benign and bounded-adaptive integration completed:** Results and
   Limitations retain the
   26/97 utility result, 152/426 abstentions, and zero unmanifested-effect
   allows. The bounded public-family search retains its non-significant
   4/40-to-1/40 attack result and 18/40-to-12/40 utility cost.
3. Complete the queued 60-run E78 capacity-matched repair protocol. The
   714-case uniform 65,536-token complete-case sensitivity has passed, but its
   outcome-dependent exclusion rule prevents it from replacing the 726-case
   comparison.
4. Decide the paper's claim level: either improve executable authority coverage
   materially beyond 26/97, or frame the runtime as a feasibility prototype and
   make representation validation the primary contribution.
5. **Completed:** update the theory to effect-instance trace/multiset semantics
   and state the boundary for history-dependent authority.
6. **Completed in prose:** add and distinguish Contract2Tool, Agent-C, PACT,
   ScopeGate, SecureClaw, ContractGuard, Alignment Contracts, and commit-time
   authorization. A direct PACT-compatible comparison remains high-value but is
   not required for logical correctness.
7. **Partially completed:** the claim map and 324-row evidence outputs include
   full benign, uniform-context sensitivity, and bounded adaptive search. Add
   final E79 only after its strict finalizer passes.
8. Build a curated anonymous artifact, pass clean-environment reproduction and
   path/credential/identity scans, and insert the anonymous stable URL into the
   Open Science appendix before paper submission.

Priority 1, high-value acceptance-risk reductions:

1. Add a second-model full comparison on a fixed, identical protocol.
2. Report cluster-aware uncertainty for all shared-task attack comparisons.
3. Improve or analyze recovery after abstention so the system is not evaluated
   mainly as a conservative blocker.
4. Add a direct effect-granularity comparison against PACT/AuthGraph-style
   argument binding on cases where one argument participates in multiple
   effects or effects arise from defaults/state.
5. If claiming causal end-to-end overhead, run randomized/interleaved timing;
   otherwise keep the current observational wording.

## Final Readiness Judgment

- **Theory:** conditionally sound and sufficient for a systems paper after two
  modeling clarifications; not sufficient as the sole novelty.
- **Problem evidence:** adequate for showing that representation collisions
  exist and matter.
- **Contract-validation evidence:** good bounded evidence, not broad
  generalization.
- **Runtime security evidence:** meaningful but paired with severe utility and
  authority-coverage costs.
- **External validity:** currently below a low-risk USENIX bar.
- **Artifact readiness:** not ready.
- **Submission recommendation:** do not submit the current package unchanged.
  Cycle 2 remains plausible if the Priority 0 items are closed and the paper
  keeps a precise, bounded claim.
