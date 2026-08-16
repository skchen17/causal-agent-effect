# USENIX Security '27 Parallel Execution Tracker

Last structured update: 2026-07-15.

## Track A: Evaluation

| Item | State | Completion evidence | Next gate |
|---|---|---|---|
| E77 Qwen 9B AgentDojo full run | done | 726/726 official keys; ASR 0/629, BU 32/97, attack utility 191/629; auxiliary audit events separated | Use as completed end-to-end row, not same-checkpoint superiority evidence |
| E78 Qwen3-32B strong baselines | running | Server split-mode bug fixed; 65,536-context two-GPU health check passed; full runner restarted | Same-model 726-key rows for every required method |
| Long-horizon benchmark survey | done | `analysis/usenix27_long_horizon_experiment_design.md` | ToolSandbox and AgentLAB feasibility smokes |
| E79 external benchmark static gate | done | `analysis/results/e79_external_benchmark_feasibility.{json,md}` | Preserve source and execution claim boundaries |
| E79 ToolSandbox environment smoke | full runner queued | Two-scenario native adapter smoke and 11 local-runner/guard tests pass; 30 frozen keys have no schema/milestone drift; localhost-only Qwen3-32B no-guard/effect-guard queue PID 3837961 waits for E78 | Let the paired 30-scenario run finish, then strict-finalize native utility, tokens, and precommit coverage |
| E79 AgentLAB fixed-transfer smoke | passed-with-adaptive-protocol-boundary | Public revision `36f58e6` and leakage-free 303-pair manifest are frozen; repaired no-guard and E77 smokes both continue after two tool returns, preserve utility, and pass strict API/post-tool gates; E77 has 2/2 signature-matched pre-commit checks | Complete paired 303-key fixed-transfer rerun; separately freeze attacker checkpoint/memory protocol before any method-adaptive claim |
| E79 protocol-fixed GPU queue | active | User service `e79-agentlab-protocol-fix.service` waits for E78 PID 3993354, then runs paired smoke gates before full no-guard/E77 reruns on its own Qwen3-32B server | Require both full finalizers to report `passed` before exposing ASR or utility |
| E79 long-horizon full evaluation | queued and partially implemented | ToolSandbox evidence remains separate; AgentLAB old 0/303 rows are invalidated because 294/303 trajectories had empty post-tool continuations; corrected full rerun is queued | Finish protocol-correct paired security rows and controlled horizon extension |
| Representation/runtime ablations | runtime adapters ready; execution gated | A1/A2/A7/A9/A11/A12/A13/A15 are operationally distinct; 118 AgentDojo fields have frozen defaults; typed resolvers and reviewed manifests compile into a pure precommit adapter | Complete E84 independent review, load all trusted manifests, then run identical common-protocol rows after E78 |
| Adaptive attacks | protocol and case manifest frozen | T1--T12 pass a machine gate; 40 hash-selected official AgentDojo attack keys (10/suite) form 480 strategy--case pairs with fixed budgets and environment predicates | Generate bounded variants, then execute identical no-guard/guard victims and finalize all rows |
| E88 attack evaluation dataset | staged queue active | 629 public AgentDojo task pairs x four registry attacks produce 2,516 payload-separated static cases; 97 benign controls and 480 E82 adaptive indices are frozen; all 2,516 templates materialize locally with zero errors; an 80-case development-only smoke is frozen | `e88-agentdojo-staged.service` waits for the existing E79 GPU queue, runs no-guard/ours smoke, stops unless two attack families trigger the official validator, then runs the eight-method fixed-suite comparison |
| Overhead/scaling | protocol frozen | Registration/runtime events and horizon strata specified | Instrument every registration and pre-commit event |
| E83 controlled runtime cost | done-with-scope-boundary | 18 configurations x 2,000 iterations; 36,000 deterministic ALLOW decisions; p50 is 22.1--352.0 us over reported 1--32 field / 0--64 noise points | Add end-to-end model, sandbox, replan, token, and trajectory overhead from E78/E79 logs |
| Paired statistical analysis | implementation ready | Wilson intervals, paired bootstrap differences, exact McNemar tests, Holm correction, and strict case-key gates have passing unit tests | Apply only after E78/E79 row-level outputs freeze |

## Track B: Theory and Security Analysis

| Item | State | Completion evidence | Next gate |
|---|---|---|---|
| System and threat model | drafted | `analysis/usenix27_effect_contract_security_analysis.md` | Reconcile with implementation and paper text |
| Counterfactual relevance | drafted | Positive witness / invariant / unresolved rule specified | Tests and registration report use identical semantics |
| Single-commit confinement | drafted | Proposition 1 and proof sketch | Validate O1--O5 or keep theorem conditional |
| Long-trajectory confinement | drafted | Prefix-confinement theorem and induction proof | E79 per-prefix empirical validation |
| TCB and limitations | drafted | Explicit obligations and current gaps | Code-level complete mediation and TOCTOU tests |
| Finite property validation | done | E80 checked 216 single-commit and 5,832 two-step sound-model cases and emitted an O1 counterexample | Extend from the finite model to implementation-level contract and executor properties |
| Implementation-obligation audit | done-with-caveat | 3,173 executed valid AgentDojo calls exactly match 3,173 pre-commit signatures; O3 and sandbox O4 pass | O1 contract soundness, O2 envelope soundness, and general O5 remain partial |
| O1 compound-effect check | done-with-scope-boundary | Four real `create_calendar_event` calls are covered by event plus explicit/implicit-recipient templates; a conjunction-triggered effect defeats isolated one-field tests | Extend registration to pairwise/condition-aware tests and all effectful tools |
| E85 causal-mediation validator | finite model done; AgentDojo review packet ready | Nine fixed interventions x six contract variants distinguish faithful mediation, true invariance, mediation gaps, and over-sensitivity; a source-frozen packet covers 28 AgentDojo tool instances, 25 unique tools, 35 candidate projections, and 80 schema fields | External reviewer completes the projection packet; compile approved projections, then execute the frozen intervention protocol |
| O2/O5 hardening mechanisms | done-with-scope-boundary | Independent manifest rejects an invented recipient literal; static nonempty defaults are totalized before checking; legacy failure witnesses are archived | Integrate into a new final runtime and rerun; arbitrary-language authority and hidden defaults remain conditional |
| Hardened pre-commit kernel | kernel ready | Totalization, independent manifest bounding, per-value checks, typed resolver ledger, and hash-bound witnesses pass eight fail-closed categories | Build benchmark-specific trusted manifests and integrate as a new method; E77 is unchanged |
| E84 authority-interface packet | validator ready; awaiting review | All 97 candidate rows are hash-bound; six workflow tests reject pending, tampered, or unbounded-resolver reviews; current status is `blocked_by_missing_reviewed_packet` | Independent reviewer completes the separate reviewed packet; strict validator must compile all 97 manifests |
| Extended authority/default finite model | done | Exhaustively checked 8,000 sound combinations, rejected 4,625 authority-expanding proposals, verified 8,000 static-default equivalences and dynamic-default abstentions | Keep claim finite/conditional; connect only after hardened runtime integration |

## Track C: Paper and Artifact

| Item | State | Completion evidence | Next gate |
|---|---|---|---|
| USENIX narrative | revised around causal abstraction | Tool transition -> causal effect abstraction -> counterfactual validation -> pre-commit mediation -> trajectory confinement | Preserve the action-source versus effect-semantics boundary as final results are added |
| USENIX source tree | done | `usenix27_candidate/` uses the official public USENIX conference style and compiles | Keep template and anonymity checks in the build gate |
| Main-body draft | in progress | Narrative, threat/design/registration/security/evaluation/limitations text compiles; Results intentionally empty | Insert only frozen E77/E78/E79/ablation/adaptive/overhead evidence |
| Results/claims freeze | pending | E78/E79 incomplete | Freeze tables and claim-to-source map |
| Open Science Appendix | in progress | Fail-fast candidate manifest, relative checksums, environment identity, readiness README, and current-evidence reproduction outputs exist under `usenix27_candidate/artifact/` and `reproduction/` | Add E78--E83 rows, clean-environment reproduction, final dependency locks, and anonymous stable link |
| Ethics and anonymization | current-paper pass | PDF-included sources and extracted PDF text have no local paths, credentials, private directory labels, or broken references; build intermediates are excluded | Repeat over the complete final artifact and row-level logs after result freeze |
| Final audit | pending | None | Claim/result/code, references, labels, PDF, reproduction |

## Latest Runtime Status

- E77 is complete and its corrected report excludes 20 auxiliary plan events and 80 auxiliary checks from official runtime counts.
- E78 is active on the Qwen3-32B no-guard row after repairing the installed llama.cpp `split_mode` interface mismatch. At the latest check, 640 official no-guard logs had been written under `runs/e78_qwen32_strong_baselines/agentdojo_logs/no_guard`; the server remains active and later methods have not started.
- AgentLAB source acquisition and protocol-correct local victim smokes are complete. The prior full logs are explicitly non-evaluable: all 294 rows with tool results ended in empty assistant continuations. Corrected no-guard and E77 smokes each complete two tool calls; the E77 audit matches 2/2 executed calls. No full AgentLAB ASR or utility is claimed until the queued 303-key reruns pass strict finalization.
- AgentLAB's Task-Injection evaluator is deterministic rather than LLM-judged, but the attacker-generation model and cumulative-memory protocol are not pinned consistently by the public artifact. The source audit therefore passes with protocol blockers, not as a benchmark reproduction.
- The USENIX draft now distinguishes the normative multi-template effect-contract architecture from the narrower E77 field-level prototype and records concrete O1/O2/O5 counterexamples.
- The current USENIX PDF contains 76 machine-traceable numeric/configuration claim rows, including scoped E83 kernel cost and bounded E85 metric checks. E78 performance, E79 victim results, and full E81/E82/end-to-end E83 measurements remain incomplete and keep the artifact manifest `incomplete`.
- The current USENIX draft is nine total pages including references and appendices. This is not a final page-budget result because final Results tables are absent.

## Submission Timing

USENIX Security '27 Cycle 1 registration is 2026-08-18 and paper submission is 2026-08-25. Because E78 and AttriGuard are long-running and E79 is not yet implemented, Cycle 1 is a high-risk target. Cycle 2 is the evidence-complete default unless the remaining experiments finish early without reducing scope.
