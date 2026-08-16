# Theory and Utility Risk Update

Date: 2026-07-30

## Decision

The revised main line is coherent and lowers conceptual review risk:

1. tool registration searches for a tool-specific effect representation rather
   than assuming one universal atom tuple;
2. source-executed counterexamples falsify or refine candidate contracts;
3. task authority is a separate, independently justified representation;
4. typed evidence may instantiate an authorized symbolic relation but may not
   create authority; and
5. pre-commit mediation is conditional on both representations being sound.

This framing preserves the existing representation-insufficiency and
confinement results while removing the impression that the paper merely
declares nine universal fields. It also positions counterexample-guided
refinement as an application of an established verification pattern rather
than claiming that pattern itself as new.

## Review Risks Reduced

- **Arbitrary atom ontology:** reduced. Atoms are tool-specific typed effect
  instances; common roles are an evaluated initial candidate.
- **Concept renaming:** reduced. Complete mediation, least privilege, and
  counterexample-guided refinement remain prior foundations.
- **Policy-relative minimality:** clarified. Minimality is relative to domain,
  authority family, and contract language, and need not be unique.
- **Utility-by-rejection explanation:** made testable. Mixed joint-view cells
  impose a representation-induced non-allow lower bound; implementation and
  recovery failures are additional, separately measured losses.
- **Effect/authority conflation:** reduced. Offline tool registration addresses
  effect abstraction; task manifests and resolvers address authority evidence.

## Risks Not Yet Reduced Empirically

- Current experiments do not demonstrate general automatic LLM contract
  synthesis. E85 is a reviewed same-suite correction, and the ToolSandbox check
  validates frozen typed contracts rather than a full proposal/refinement loop.
- The headline AgentDojo profile still uses a plan-derived envelope; only 26/97
  reviewed task manifests compile. Thus O2 remains partial.
- Full benign utility remains 33/97 in the headline comparison and 26/97 in the
  reviewed-authority run.
- Direct whole-call versus atom attribution remains conditioned on a 321-case
  applicability subset.
- Cross-model and adaptive AgentLAB generalization remain open.

## Completed Joint Diagnostic

The fixed four-cell diagnostic now covers identical 26 benign and 169 attack
keys:

| Effect contract | Task authority | Purpose |
|---|---|---|
| current | current | observed system |
| source-oracle | current | upper bound on contract-side repair |
| current | evaluation-oracle | upper bound on authority-side repair |
| source-oracle | evaluation-oracle | joint diagnostic ceiling |

The first attempted authority oracle used successful benign model trajectories.
Audit found that AgentDojo utility can remain true despite an extra effectful
call, so that construction was rejected and overwritten. The final oracle uses
only official AgentDojo user-task `ground_truth()` calls. It reads no model
trace, attack row, attack goal, or attack label.

On 180 common-support cases, all four cells admit 170 traces. Current and
source-reviewed effect fields agree on all 16 reviewed tool instances. Reviewed
authority and the official oracle agree on all 195 trace-admissibility
decisions. All 19 successful benign traces that are official-oracle admissible
are retained; the twentieth utility-success trace contains an extra transfer
absent from the official call chain. Four of five successful no-guard attacks
contain a privileged call and all four are rejected; the fifth contains no
privileged call and is outside pre-commit effect mediation.

The current runtime already incorporates reviewed projections when classifying
observation-only tools. The zero contract-side delta therefore verifies
integration consistency; it is not an independent second validation of the
effect abstraction.

This result rules out a simple explanation that the reviewed kernel rejects the
officially expected calls in these successful fixed traces. It does not explain
end-to-end recovery loss, expand 26/97 authority coverage, or turn official
ground truth into deployable authority. The official call chain may also
exclude valid alternative plans.

An additional deterministic audit isolates the seven benign tasks whose
official utility labels differ between no defense and reviewed authority. All
seven execute only read-only calls and receive no runtime denial or abstention.
Reapplying the official task predicates to visible final answers, rather than
the complete answer containing `<think>` content, changes the discordant-case
net gap from -5 to -3. Four cases are reasoning-sensitive, with a net effect of
-2; the remaining three losses reflect different retrieval paths or exact
answer strings across independent model runs. This does not estimate repeated
run variance, but it rules out interpreting the five-task aggregate difference
as five guard-induced false denials.

A second deterministic audit covers the full 97-task capacity-matched E78
benign denominator. Of 37 no-defense-success/guard-failure transitions, 32
contain explicit runtime feedback. The 47 feedback-bearing trajectories have a
net utility change of -31, while the 50 without feedback have a net change of
+1. Initial-plan parse or tool-coverage findings occur in 16/32 direct losses;
binding/evidence findings occur in 22/32, with six overlapping. A conservative
literal probe finds 38/85 rejected resolver-field values in earlier benign tool
results, spread across 12 loss cases. Literal presence is not an authorization
oracle, and independent model trajectories prevent randomized causal
attribution. Nevertheless, the concentration shows that the headline loss is
not evidence that effect decomposition intrinsically destroys utility; the
current planner, typed-evidence relation, and recovery implementation are the
dominant observed pathways.

A four-cell deterministic source-relation probe then tests the existing typed
resolver on one representative bill workflow. It admits amount and recipient
values when the permission plan names the actual `read_file` source, requests
replanning when the plan names the nonmatching `read_bill` source, and fails
closed when the prior result contains two plausible account identifiers. This
shows that the typed projector can support the intended relation when the plan
constructs it correctly. It is a mechanism isolation result, not a recovered
utility estimate or evidence for weakening provenance constraints.

Code inspection found a concrete planner-interface defect behind that example:
the appended source catalog was not formatted as an f-string, so the model saw
the literal catalog expression rather than the available tool names. The same
prompt labeled source-call parameters as if they were result fields. The repair
now registers declared result shapes and fields, requires structured sources to
select a result field, and keeps free-text or dynamic results tool-scoped. A
three-task local-Qwen planner pilot produced three schema-valid plans, no
unknown source names, and the expected `email` binding for a structured contact
lookup, without executing tools. This establishes that the interface repair is
runnable; it does not establish recovered AgentDojo utility.

A sequence of Qwen3-32B mechanism smokes then exercises the repair through the
complete sandbox runtime. In v5, the deterministic checker accepts the bill
amount and recipient from `read_file`, but the call does not execute because
date and subject have no registered relation. In v7, the planner correctly
selects a bill-subject projection and execution-date default, but exact string
equality still rejects the descriptive subject. In v8, a closed deterministic
equivalence relation admits only the registered service label, optionally
followed by the same parsed amount. The first proposal receives exact
call-revision feedback; the second matches the configured runtime date and
registered subject projection and executes. Benign utility is 1/1. The paired
injected document yields no registered projection and no transfer execution.

This progression supports a narrow mechanism conclusion: at least one observed
utility loss came from an incomplete trusted-relation interface rather than an
inherent need to reject the authorized effect. It does not estimate benchmark
utility or attack success. The parser is specific to one fixed bill schema, and
the paired attack has false AgentDojo utility.

The next frozen mechanism pilot selects all 12 historical benign losses with a
resolver value literally present in an earlier trusted tool result, plus four
stable controls. The repaired runtime recovers only 1/12 target cases and
retains 4/4 controls. Seven remaining failures contain unresolved runtime
relations; four fail during permission-plan construction. No runtime error
occurs, and no non-ALLOW check reaches execution. Thus the one-task repair does
not establish that resolver engineering broadly explains or solves the utility
loss. It instead exposes a systematic onboarding obligation: each admissible
cross-tool transformation must be registered, validated, and bounded before
runtime use. A post-pilot inventory contains 14 exact
`source_tool -> target_tool.field` groups and 17 relation-case rows because one
calendar case has two candidate sources. Only the two bill bindings occur in a
recovered case; 12 groups occur in failed cases. These observations define
validation targets, not authorization grants.

## Registration Experiment Gate

An automatic or LLM-assisted onboarding result becomes claim-eligible only if:

- proposal, refinement, and held-out test sets are separated;
- the effect and authority oracles are independent of the candidate contract;
- prompts contain no held-out atoms, decisions, or attack labels;
- every refinement counterexample and contract version is retained;
- held-out authorization collisions decrease relative to the initial and fixed
  common-role representations;
- overpartition, atom/template count, registration queries, time, and
  human-review routing are reported; and
- runtime evaluation compares learned, fixed, whole-call, and source-oracle
  contracts under the same authority and recovery implementation.

## Utility Engineering Gate

Before another 726-case Qwen3-32B run:

- raise runtime-ready coverage from 26/97 toward at least 48/60 effectful tasks;
- replace one-off relation parsers with a predeclared onboarding and validation
  procedure covering the relation families observed in the frozen pilot;
- reduce missing-manifest and unproven-resolver abstentions without silently
  allowing unresolved values;
- validate deterministic default, alias, projection, and evidence binding on a
  new held-out benign set;
- demonstrate materially higher target recovery while retaining stable controls
  and exact pre-commit witnesses; and
- freeze code before evaluating attacks.

Default-allow uncertainty remains a diagnostic, not a paper method. It neither
improved the fixed pilot's utility nor satisfies independent-authority
confinement.

## Expected Review Effect

The revision can improve originality and technical-clarity assessments because
the paper now states a general joint information obligation and a bounded
contract-refinement mechanism. It does not by itself improve the evaluation
score. A lower-risk USENIX submission still requires either materially improved
authority/resolver coverage and utility or a successful isolation showing that
the representation contribution remains useful under a complete authority
interface.
