# Simulated USENIX Security Review

Date: 2026-07-28  
Review target: `paper/current-usenix/main.pdf` and its admitted evidence  
Reviewer stance: independent systems-security reviewer  
Pending evidence excluded from the decision: the running E79 strict rerun and
the queued E78 capacity-matched repair

## Recommendation

**Overall score: 2/5 -- Weak Reject / Major Revision**

| Dimension | Score | Assessment |
|---|---:|---|
| Security relevance | 4/5 | Clear pre-commit authorization problem for tool-using agents |
| Originality | 3/5 | Effect occurrences and executable representation collisions are distinguishable, but close to PACT and recent contract/commit-boundary work |
| Technical correctness | 3/5 | Formal statements are conditionally correct; the main implementation does not instantiate all theorem assumptions |
| Evaluation quality | 2/5 | Strong controlled evidence, but weak atomization attribution, severe utility loss, one-model dependence, and protocol asymmetry |
| Clarity | 4/5 | The narrative is coherent and unusually candid about limitations |
| Reproducibility | 3/5 | Numeric evidence is well traced, but the submission artifact is not release-ready |
| Reviewer confidence | 4/5 | High confidence in the representation/security analysis; moderate confidence in all experimental implementation details |

The paper contains a publishable core, but the current system claim is larger
than the evidence that cleanly supports it. The strongest contribution is a
representation result:

> One call can realize several independently authorizable effect occurrences,
> and source-executed counterfactuals can expose when a candidate representation
> merges authorization-inequivalent executions.

The current end-to-end evaluation does not yet establish that atom-level
mediation, rather than conservative planning and rejection, causes the reported
AgentDojo security improvement.

## Paper Summary

The paper argues that tool-agent monitors should authorize realized effect
occurrences rather than tool names or whole calls. It defines authorization
equivalence, proves an indistinguishability result for representations that
merge authorization-inequivalent contexts, and turns source-executed
counterfactual pairs into insufficiency witnesses. The system validates effect
contracts offline, freezes accepted descriptors, and checks instantiated
effects against a task envelope before execution.

The evaluation combines controlled guard stresses, source-grounded
interventions, a 56-call finite AgentDojo domain, a pre-registered 32-context
ToolSandbox domain, an AgentDojo runtime comparison, authority-interface
review, ablations, mediation audit, adaptive sensitivity, and overhead.

## Strengths

1. **The problem is concrete and security-relevant.** The calendar example
   immediately shows why one call can contain independently authorizable
   changes (`sections/introduction.tex:11-20`).
2. **The formal claim is scoped correctly.** The representation theorem is a
   valid indistinguishability argument and explicitly avoids claiming that all
   whole-call representations are insufficient
   (`sections/security_analysis.tex:48-93`).
3. **Counterfactuals have a precise role.** They test representation
   sufficiency rather than attributing why the LLM proposed a call
   (`sections/method.tex:57-101`).
4. **Negative results are retained.** The paper reports the failed common-field
   contract, 26/97 authority coverage, 152 abstentions, non-significant
   adaptive results, and substantial utility loss.
5. **The evidence chain is unusually auditable.** The claim map and fail-fast
   reproduction output connect paper numbers to result artifacts and tests.
6. **The novelty boundary is improving.** The PACT-compatible finite comparison
   demonstrates a narrow state-dependent distinction without claiming to
   reproduce PACT.

## Major Concerns

### 1. The 726-case main result does not instantiate the paper's trusted-authority model

The method requires a trusted interface to establish an independently bounded
authority object \(B_q\), with the LLM only specializing that bound
(`sections/method.tex:103-115`). The confinement theorem assumes envelope
soundness relative to this independently justified bound
(`sections/security_analysis.tex:170-184`).

The main E77 path instead asks the model to construct the initial permission
plan and permits model-generated revisions. The parser enforces shape,
grounding, and declared fields, but it does not independently establish the
semantic authority relation:

- `code/src/.../e77_runtime.py:79-97` asks the LLM for the complete envelope;
- `e77_runtime.py:109-181` parses exact/resolve/forbidden bindings;
- `e77_runtime.py:489-578` asks the model whether a mismatching effect remains
  necessary;
- `e77_runtime.py:581-659` accepts structurally valid revisions;
- `e77_runtime.py:662-672` installs the model revision into the plan.

The paper separately acknowledges that only 26/97 reviewed manifests compile
(`sections/experimental_setup.tex:54-59`; `sections/results.tex:223-229`).
Therefore, the 726-case result is evidence for a guarded model-generated
envelope, not for the full O2-backed system shown in Figure 2.

**Why this matters:** the Abstract presents the runtime, the 726-case result,
and independently bounded authority in one continuous system description
(`sections/abstract.tex:12-27`). A reviewer can reasonably infer that the main
result discharges the theorem's runtime assumptions when it does not.

**Required resolution:** choose one of two claim structures.

- Make representation validation the primary contribution; label the
  726-case path a diagnostic prototype with model-proposed authority.
- Or provide independently justified, executable authority at substantially
  broader coverage and use that path for the main end-to-end result.

### 2. The end-to-end evaluation does not isolate the benefit of atomization

The paper's claimed mechanism is effect-occurrence granularity, but the
tool-call-only ablation has the same aggregate BU, UA, and ASR as the full
guard. The paper correctly reports that the switch applies to only 17 checks
(`sections/results.tex:192-208`), but this means AgentDojo does not currently
demonstrate that atomization causes the runtime security gain.

The controlled finite-domain experiments prove that representation collisions
exist. They do not show that the observed 53/629-to-3/629 ASR change is due to
resolving those collisions rather than:

- a pre-output LLM permission plan;
- exact-value grounding;
- fail-closed handling;
- bounded replan prompts; or
- conservative rejection.

**Required resolution:** add a same-input, same-authority, same-recovery
comparison in which only the monitored representation changes:

1. whole call or tool-call envelope;
2. argument-role/value/provenance representation;
3. common effect tuple;
4. typed effect occurrences.

Report UPA, false denial, coverage, benign utility, and attack success on cases
where at least one representation distinction is actually exercised. This is
more important than adding another broad but non-applicable ablation table.

### 3. The current security--utility tradeoff is not competitive

On the same checkpoint:

- Prompt Sandwiching: BU .619, UA .576, ASR .013;
- proposed method: BU .340, UA .329, ASR .005.

The proposed method prevents five additional official attack successes relative
to Prompt Sandwiching while losing 27 benign successes and 155 attack-side
utility successes. The full reviewed-authority path succeeds on only 26/97
benign tasks and fails its predeclared 50-task utility gate
(`sections/results.tex:157-174`; `sections/limitations.tex:16-22`).

The paper is honest about this, but honesty does not remove the systems result:
the current interface is often a conservative blocker. A deny-all monitor
would also satisfy the safety side of the theorem.

**Required resolution:** either materially improve descriptor/authority/resolver
coverage and recovery, or reposition the runtime as feasibility evidence. Do
not describe the current system as offering a favorable overall tradeoff.

### 4. The primary comparison is not protocol-uniform, and the reported inference ignores shared-case dependence

Five baseline rows use a 65,536-token context. The guard replaces 12 failures
with 73,728--122,880-token runs (`sections/experimental_setup.tex:46-52`).
The paper discloses this, but `sections/results.tex:114` still calls all six
rows a complete common-checkpoint comparison. This is not a matched
capacity protocol.

The paper reports row-level bootstrap and exact McNemar inference over 629
attack rows (`sections/results.tex:114-121`), although rows share user tasks and
injection templates. The existing crossed-cluster sensitivity artifact gives
an ASR-difference interval of approximately `[-0.126, -0.041]`, but that result
is absent from the PDF.

**Required resolution:**

- finish the queued capacity-matched repair and make it the primary row;
- otherwise demote the 726-row comparison to repaired sensitivity;
- report crossed user-task/injection-task cluster uncertainty in the paper.

### 5. The finite-domain authority family makes the positive sufficiency result easier by construction

The 56-call and ToolSandbox audits use authority families containing every
submultiset or power-set choice of observed effect occurrences
(`sections/experimental_setup.tex:22-30`;
`sections/results.tex:90-97`). Under this family, every unequal effect multiset
is authorization-separable. The test is rigorous as a representation-fidelity
check, but it does not show that realistic authorization policies independently
distinguish every payload, timestamp, repeated occurrence, or state transition.

The typed representation is compared against a source-effect partition and is
therefore rewarded for approaching a serialization of that partition. The
paper states that qualifiers must be policy-relevant, but the positive finite
result does not independently validate that minimality against realistic policy
families.

**Required resolution:** add a policy-family sensitivity analysis containing:

- realistic coarser policies where some effect differences are equivalent;
- at least one policy with resource/target separation;
- at least one amount/time/recurrence policy;
- deletion tests showing which qualifier is necessary under which policy.

Report both collisions and overpartition. This would support the claim that the
contract is authorization-minimal rather than merely effect-exact.

### 6. External validity remains below the paper's systems scope

The main positive representation evidence is 56 calls to five AgentDojo tools
and 32 contexts for five ToolSandbox tools. The source oracle is manual and
source-specific. The end-to-end comparison uses one quantized Qwen3-32B
checkpoint. The separate 9B run establishes call-path mediation, not the main
security/utility effect. E79 long-horizon evidence is still pending.

These are acceptable limitations for a bounded representation paper, but weak
for a general agent runtime paper. The recent PACT paper reports a broader
multi-model AgentDojo evaluation, so reviewers will expect a clear explanation
of why the narrower effect-occurrence contribution is independently valuable.

**Required resolution:** complete E79 and add a second-model main comparison,
or narrow the paper's systems claim. Do not add E79 unless its strict finalizer
passes all 303 cases and exact pre-commit/execution reconciliation.

### 7. The closest-work comparison is informative but not a system baseline

The new PACT-L2-compatible rows are a local deterministic representation audit.
They are not PACT's automatic role inference, cross-step provenance, policy, or
AgentDojo runtime. The paper states this boundary
(`sections/results.tex:99-108`), which is correct.

However, placing those rows in a main evaluation table may still be interpreted
as a PACT baseline. PACT's object is authority-bearing argument provenance,
whereas this paper asks whether call arguments determine realized effects under
state and one-to-many expansion. The comparison establishes a narrow
non-equivalence, not system superiority.

**Required resolution:** label the rows as “local PACT-L2-compatible encoding”
in both table and prose, and discuss the result as a representation witness.
If a public compatible PACT artifact becomes available, run it under an agreed
common protocol; otherwise do not imply full-system comparison.

### 8. The submission artifact is currently a desk-level completeness risk

The Open Science appendix promises that an anonymous URL “will be inserted”
(`appendix/open_science.tex:3`), while `artifact/manifest.json` remains
`incomplete`. It reports a missing stable URL, failed clean-environment
reproduction, and failed credential/path scan. The manifest is also stale
relative to results already admitted to the paper.

USENIX Security '27 requires an Open Science appendix and a finished, complete
paper. The official CFP also makes human authors responsible for reviewing
AI-generated text, code, data, and references.

**Required resolution:** build a curated anonymous artifact, regenerate its
manifest from current paths, run clean-environment reproduction, scan for
identity/credentials/absolute paths, and insert the anonymous stable URL before
submission.

## Minor Concerns

1. The Abstract fuses three different evidence paths: the 32B repaired runtime,
   the reviewed-authority subset, and the separate 9B mediation audit. Identify
   which result supports each sentence.
2. “Exhaustively enumerated calls” can be misread as tool-wide exhaustiveness.
   Prefer “an exhaustively enumerated 56-call finite domain.”
3. “The safety gain is therefore real” (`sections/introduction.tex:74-76`) is
   stronger than necessary. “Observed under this sandbox protocol” is more
   precise.
4. “Causal-abstraction soundness” may suggest causal identification. The method
   performs controlled execution interventions and relation testing; it does
   not estimate a causal effect from observational data.
5. The nine-field atom plus qualifier map is flexible enough to encode most of
   the call. The policy-relative minimality analysis requested above is needed
   to prevent the abstraction from appearing ad hoc.
6. The main paper is exactly at the 13-page body limit. There is no room for E79
   or matched E78 results without replacing existing material.
7. The baseline table mixes prompting defenses, local style adapters, and the
   proposed runtime. The input and information contract for each baseline
   should be visible in the main paper or a mandatory appendix.
8. The label-hidden AI artifact review is appropriately disclosed but cannot
   be described as independent validation.

## Questions for the Authors

1. What concrete trusted component supplies \(B_q\) for the full 726-case E77
   run, independently of the model that creates and revises the permission plan?
2. How many of the 53 blocked official attacks exercise a distinction available
   only in the typed effect-occurrence representation?
3. Why does the tool-call-only ablation match the full guard? Which benchmark
   cases would distinguish them?
4. How would the results change under a realistic authority family that does
   not distinguish every unequal source-effect multiset?
5. What proportion of the benign utility loss comes from missing descriptors,
   missing authority, resolver grounding, model recovery failure, and genuine
   policy rejection?
6. Do the 12 capacity-repaired cases change ASR or utility conclusions under an
   identical capacity budget for all methods?
7. Which contract fields were proposed before outcomes were observed, which
   were added after E85 failures, and which were frozen before ToolSandbox?
8. What are the exact outcomes of the running E79 strict rerun, including
   mediation reconciliation and no-guard comparison?

## What Would Change the Score

The following package could move the review from Weak Reject to Weak
Accept/Shepherd:

1. A capacity-matched primary E78 comparison with crossed-cluster uncertainty.
2. An atomization-specific comparison under identical authority and recovery,
   showing an exercised advantage over tool-call and argument-level views.
3. A clear claim split between model-proposed authority on 726 cases and
   reviewed executable authority on 26 tasks.
4. Either substantially improved authority coverage/utility or an explicit
   repositioning of the runtime as a feasibility prototype.
5. A passed 303-case E79 strict finalizer, if long-horizon claims remain.
6. A current anonymous artifact that reproduces every main table from a clean
   environment.

The second item is the most important scientific addition. E79 and a second
model improve external validity, but they do not by themselves establish that
effect-occurrence granularity is the mechanism responsible for the runtime
security result.

## Final Reviewer Judgment

I would currently vote **Weak Reject**. The paper identifies a real
representation problem, gives a correct bounded formalization, and provides
valuable source-grounded negative evidence. The paper is also more transparent
than many agent-defense submissions about utility and infrastructure costs.

My rejection is based on evidence alignment rather than lack of merit. The
full runtime result does not cleanly instantiate the trusted-authority model,
does not isolate atomization from conservative planning/rejection, and is not
protocol-uniform. If the paper centers the effect-occurrence representation,
adds the missing mechanism-specific comparison, and treats the runtime as
bounded feasibility unless O2 coverage improves, it can become a credible
USENIX Security submission.

## Public Review Anchors

- [USENIX Security '27 Call for Papers](https://www.usenix.org/conference/usenixsecurity27/call-for-papers/)
- [PACT, arXiv:2605.11039](https://arxiv.org/abs/2605.11039)
- [ContractGuard, arXiv:2606.18550](https://arxiv.org/abs/2606.18550)
- [Commit-Time Authorization, arXiv:2607.10487](https://arxiv.org/abs/2607.10487)
