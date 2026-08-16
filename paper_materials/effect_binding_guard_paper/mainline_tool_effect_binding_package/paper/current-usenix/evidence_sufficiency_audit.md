# Experimental Evidence Sufficiency Audit

Status: evidence audit for the current USENIX candidate. This document is an
internal review artifact and is not included in the paper PDF.

## Overall Decision

The current artifacts are sufficient to support the paper's controlled problem
claim, the resource/authorization granularity diagnosis, and a scoped sandbox
implementation claim. They are not yet sufficient for a strong system-wide
generality or deployment-readiness claim. A USENIX Security submission is
plausible only if the paper keeps the current conditional claim boundary and
closes the primary evaluation gaps below.

## Evidence by Claim

| Claim layer | Main evidence | Decision | Limitation |
|---|---|---|---|
| Compound and multi-target effects occur in the benchmark rather than only in constructed examples | Full source-state replay of 339 calls in all 97 official benign AgentDojo trajectories: 100 effectful, 17 compound, 13 heterogeneous/cross-subsystem, seven multi-target | Sufficient for within-benchmark descriptive prevalence | 55/74 tools observed; normalization was frozen after exploratory inspection and is not independent human certification or ecosystem prevalence |
| Existing guards bind some axes but fail joint binding | E47, 528 adapted rows from 24 anchor groups; released TS-Guard and Safiron checkpoints; audited subset | Sufficient for controlled characterization | Custom stress, not original-paper benchmark reproduction or field prevalence |
| A hard tuple guard still fails resource/authorization granularity | E48, 822 rows and 6,840 relations; E50, 240 resource/authorization and 336 provenance rows | Sufficient for mechanism diagnosis | Synthetic/simulated counterfactual evidence |
| A common fixed tuple omits execution-relevant distinctions | E85 common projection, 65/80 relation agreement with 15 observed mediation gaps | Persuasive negative evidence | Only 16 reviewed tools and a generated intervention suite |
| Typed qualifiers solve the representation gap | E85 typed projection, 80/80 on the same cases; pre-registered ToolSandbox held-out check, 32/32 relation agreement and zero typed collisions | Bounded cross-artifact evidence | The held-out result covers five public tools and 32 frozen contexts, not an open tool domain |
| The guard lowers AgentDojo attack success | E78, 54/627 to 2/627 on paired evaluable keys; 3/629 for the guard overall | Persuasive within the benchmark | Large utility loss, one model, non-uniform context repair for 12 guarded rows |
| The E78 effect is statistically robust | Paired row statistics plus cluster-aware sensitivity audit | Supported after clustering sensitivity | Paper still reports row-level McNemar/bootstrap; cluster result must replace or qualify it |
| The 63/97 to 33/97 E78 benign-utility change is inherent to atom decomposition | Full 97-task pathway audit: 32/37 losses contain runtime feedback; feedback stratum net -31, no-feedback stratum net +1 | Not supported | The observed loss concentrates in plan, typed-evidence, and recovery paths; separate stochastic runs prevent randomized causal attribution |
| The current trusted-evidence interface contributes to utility loss | 22/32 feedback-associated losses contain binding/evidence findings; 12 loss cases reject a resolver value literally present in an earlier benign tool result | Strong diagnostic evidence | Literal occurrence does not prove semantic relation, trust, or authorization; requires a frozen interface repair and rerun |
| The identified resolver-planning defect is repairable without default allow | Source-catalog probe; three-task local-Qwen pilot; one-call registered-relation planner pilot; and a two-row Qwen3-32B end-to-end smoke in which the corrected bill transfer executes | Bounded mechanism evidence | The recovered 1/1 benign result uses one fixed bill parser and one configured runtime default; it is not a benchmark-wide utility or security estimate |
| One registered bill relation materially recovers the broader diagnosed resolver-loss stratum | Frozen 16-task benign mechanism pilot: 1/12 historical target losses recover, 4/4 stable controls remain successful, with zero errors and zero executed non-ALLOW checks | Not supported | Outcome-conditioned diagnostic subset, not an unbiased utility estimate; 14 exact source-to-target-field groups are observed, two in the recovered case and 12 in failed cases |
| Reviewed authority supports practical mediation | E84, 26 benign and 169 attack cases | Weak/local evidence | Only 26/97 tasks, AI artifact review, non-significant ASR difference, selection/compilation bottleneck |
| Reviewed authority rejects officially expected successful calls on the evaluated fixed traces | Four-cell deterministic replay, 195/195 agreement with official-call oracle and 19/19 admissible benign successes retained | This simple false-denial explanation is not observed | Fixed trajectories only; does not evaluate recovery, alternative plans, or the missing 71 task manifests |
| The E84 20/26 to 15/26 utility difference measures guard false denial | Seven-case discordance audit: zero runtime denial/abstention; official net gap -5 becomes -3 on visible final answers | Not supported as a causal interpretation | Three remaining net losses are model retrieval/exact-answer variation; repeated paired runs are still absent |
| Runtime checks completely mediate executed sandbox calls | E80, 3,173 executed signatures matched to 3,173 precommit checks | Strong scoped implementation evidence | Does not establish contract or authority soundness |
| Individual runtime mechanisms are necessary | E81 exact-key ablations | Partial | Only registry validation has a clear utility effect; most switches have narrow or zero applicability |
| Runtime overhead is low | E83, 36,000 kernel decisions; post-hoc 726-key trajectory pairing | Kernel cost supported; complete-trajectory magnitude observed | Sequential historical timing cannot causally attribute the 1.36 median ratio to the guard; 12 guarded rows use context repairs |
| The method transfers to long tasks/environments | E79, 303 fixed saved AgentLAB attacks: goals 95 to 0 and utility 180 to 87 | Supported for fixed saved transfer | Not adaptive AgentLAB generation or cumulative optimization; large utility loss |

## Primary Risks

1. **Security/utility tradeoff.** E78 reduces ASR by 50 successes but also loses
   31/97 benign successes and 135/629 attack-side task successes. Prompt
   Sandwiching is a strong competing tradeoff and prevents a Pareto-dominance
   claim. The pathway audit attributes most observed losses to the current
   plan/evidence/recovery path, which reduces conceptual risk but raises the
   expectation that the implementation should be repaired and rerun.
2. **Context fairness.** The guarded E78 row combines 714 original trajectories
   with 12 larger-context repairs, while primary baselines use 65,536 tokens.
   This is disclosed but remains a main-comparison weakness.
3. **Dependence-aware statistics.** The 629 attack rows share user tasks and
   injection tasks. The cluster-aware audit shows the ASR effect survives, but
   the paper currently cites row-level exact tests.
4. **Authority coverage.** Only 26/97 reviewed task manifests compile into the
   runtime. The four-cell replay shows no reviewed-vs-official admission gap on
   the 195 fixed subset rows, but it does not address the missing 71 task
   manifests or end-to-end recovery.
5. **Bounded held-out scope.** The AgentDojo census now establishes that
   compound effects occur in the complete official benign workload, but it does
   not validate a learned contract. The pre-registered ToolSandbox check removes the
   direct post-hoc-repair explanation for five tools, but its 32 contexts and
   source-specific oracle do not establish open-domain generalization.
6. **External validity.** The main agent result uses one checkpoint and one
   benchmark family. Long-horizon, adaptive, and second-model evidence is not
   final.

## Required Before Submission

1. Replace or supplement row-level E78 inference with task- and
   injection-cluster-aware intervals.
2. Produce a uniform-context E78 guarded row, or freeze a conservative policy
   that treats all 12 context failures identically across methods.
3. Expand the pre-registered held-out check beyond five ToolSandbox tools only
   if the paper seeks a broader transfer claim; the current bounded claim is
   already reproducible.
4. Keep the current end-to-end timing claim observational. Run randomized or
   interleaved timing only if claiming causally attributable guard overhead.
5. The first bounded trusted-source projection and runtime default pass one
   bill-payment smoke, but the frozen multi-task pilot recovers only 1/12
   diagnosed target losses. Before another full E78 comparison, define and
   validate a systematic onboarding procedure for address, channel, URL,
   calendar, participant, and attachment relations. Predeclare a new held-out
   pilot and retain unresolved cases; do not add task-specific parsers after
   observing their outcomes.

## High-Value Extensions

- Complete a protocol-clean strong released-artifact baseline or keep the
  adapted AttriGuard row explicitly provisional.
- Add a second-model sensitivity run.
- Complete and strictly finalize the frozen bounded adaptive-family search.
- Obtain independent human authority review only if upgrading E84 beyond its
  current artifact-reviewed interface case-study wording.

## Submission-Level Judgment

The problem and mechanism evidence are paper-worthy. The current system
evaluation is not yet at a low-risk USENIX Security evidence bar because the
utility cost, context mismatch, limited authority coverage, and missing
held-out/long-horizon evidence leave obvious alternative explanations. The
current claim boundary is appropriately conservative; strengthening claims
without completing the required items above would reduce credibility.
