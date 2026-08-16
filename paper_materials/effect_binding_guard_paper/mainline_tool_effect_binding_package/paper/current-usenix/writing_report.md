# USENIX Security '27 Writing Report

Last updated: 2026-08-16.

## Active Manuscript

- Source: `paper/current-usenix/main.tex`.
- Title: *Falsifying Authorization Interfaces for Tool-Using Agents: Counterfactual Validation of Policy-Relevant Effects*.
- Target: USENIX Security 2027 Cycle 2.
- Structure: Introduction, Related Work, Problem and Security Model, Executable Authorization-Interface Validation, Security Analysis, Evaluation Methodology, Results, Limitations, and Conclusion.

## Final Narrative

The manuscript treats authorization observability as a security obligation. A representation partitions tool executions and therefore upper-bounds every downstream policy consumer. A policy-separating collision is a constructive failure certificate. Counterfactual source execution tests candidate interfaces before they are frozen, while the validation record binds a successful candidate to its implementation, intervention manifest, policy family, and unresolved evidence.

Typed effects are one evaluated candidate. A strong state-aware request reaches the same decisions in both positive domains, confirming that the theory is representation-neutral. Typed effects contribute canonicalization, lower source-equivalent overpartition, lower policy-facing raw-state exposure, and a different placement of tool semantics; prototype latency and executable code size are mixed.

The AgentDojo provenance-origin monitor is a compact pre-commit consumption study. It demonstrates execution reconciliation and deterministic runtime checks, not the paper's primary representation result.

## Core Evidence

- Source replay covers 339 AgentDojo calls; 17.0% of effectful calls contain multiple effect units and 13.0% cross effect types or subsystems.
- The 56-call source domain yields 564 tool-name, 548 effect-only, and 118 common-field policy-separating pairs.
- Three pinned public MCP implementations contribute 11 tools, 264 registration contexts, and 264 descriptor-blind post-freeze contexts.
- The native-delta policy agrees with the typed path on all 528 third-party decisions. Registration detects 37 of 47 systematic descriptor faults; the other 10 are decision-equivalent in both frozen domains.
- The four-domain explicit-authority protocol contains 384 registration contexts, 192 counterfactual pairs, and 1,024 post-freeze contexts. Typed-effect and state-aware interfaces have no mixed cell and reproduce every source-derived decision.
- The interface-economy audit finds 3,252 and 90 source-equivalent overpartition pairs for state-aware requests versus zero for typed effects in the two domains. Median policy-facing trusted-state leaves are 9 and 4 for state-aware requests versus zero after typed instantiation.
- The 30-trajectory concrete consumer commits 10 authorized calls, denies 20 unauthorized calls, and records zero check--use or transition-reconciliation failures.

## Final Runtime Evidence

- Four interleaved DeepSeek repetitions produce benign utility 77.6% without a guard, 78.6% under Spotlighting, and 76.5% under the provenance monitor. The one-sided lower bound is -5.4 percentage points, missing the preregistered -5.0-point non-inferiority margin by 0.4 points.
- The matched Qwen3-32B protocol uses the exact same 97 benign and 629 attack keys for all five methods. Attack success is 10.0% for no guard, 9.5% for Spotlighting, 1.0% for Prompt Sandwiching, 0.0% for PromptArmor-style, and 2.9% for the provenance monitor. Benign utility is 61.9%, 66.0%, 68.0%, 27.8%, and 60.8%, respectively.
- Prompt Sandwiching provides the best combined Qwen security--utility point. PromptArmor-style eliminates observed attack success with a large utility reduction.
- On the frozen 320-case public-family set, attack success is 1.2% without a guard and 0.0% under both Spotlighting and the monitor.

## Prose Revision

The final prose follows one claim chain: concrete authorization failure,
observation-interface upper bound, executable falsification, post-freeze
conformance, and downstream consumption. A de-defensiveness pass removed 10.0%
of the prose in the eight core sections while preserving every formal statement,
citation, and numeric result. Method now reads as an executable pipeline;
Evaluation groups isolation controls as a design principle; Results lead with
findings; and empirical or deployment reservations are concentrated in
`sections/limitations.tex`.

`failure certificate` is the primary prose term. Witness terminology remains
where it distinguishes implementation change from policy separation. The
remaining contrast constructions express the central authorization boundary,
formal premises, protocol controls, or explicit limitations.

## Final Frozen Validation


## Matched Utility and Second Model

- DeepSeek benign utility over four interleaved repetitions: no guard 301/388, Spotlighting 305/388, C1f 297/388.
- C1f-minus-no-guard difference: -0.0103; one-sided 95% lower bound: -0.0541; non-inferior at -0.05: `false`.
- Qwen3-32B attack success: no guard 63/629, Spotlighting 60/629, Prompt Sandwiching 6/629, PromptArmor-style 0/629, C1f 18/629.
- Qwen3-32B benign utility: no guard 60/97, Spotlighting 64/97, Prompt Sandwiching 66/97, PromptArmor-style 27/97, C1f 59/97.

## Held-Out, Transfer, and Attribution

- Frozen 320-case held-out ASR counts: no guard 4/320, Spotlighting 0/320, C1f 0/320.
- Frozen 40-key worst-of-four ASR counts: no guard 4/40, current C1f 2/40.
- Current-profile AgentLAB saved transfer: no guard attack/utility 95/303 and 185/303; C1f 1/303 and 132/303.
- Four-view closed-loop ASR counts: no guard 38/273, whole-call 11/273, effect-only 21/273, registered-field C1f 7/273.
- Raw-field attribution: raw-field ASR 10/273; paired same-call disagreements 28/788; atom-semantic runtime difference: `true`; defined security/selectivity benefit: `true`.
- Concrete-atom authorizer matches the finite 232-query source-effect relation without unsafe pre-allow or false denial: `true`.

## Reproduction

The strict entry point is:

```bash
python paper/current-usenix/reproduction/reproduce_main_claims.py
```

It must report `status=passed`, `n_claim_rows=368`, and an empty `pending` list. Generated final tables are derived directly from strict-passed result JSONs. Each ledger row records the artifact, key or aggregate expression, generator, and numerator/denominator.

The final USENIX-template build contains an 11-page technical body under the
13-page limit and a 17-page complete PDF.

## Verification Note

The active targeted suite covers claim reproduction, state-aware authorization, third-party execution, native-delta isolation, descriptor mutation, table rendering, reference checks, and artifact manifests. Repository-wide collection also reaches legacy experiments that require separate `src` roots and the AgentDojo environment; those dependency failures are recorded separately and are not presented as a full-suite pass.

## Author-Only Completion

Authors must verify AI-assisted prose, numbers, citations, author metadata, conflicts, and the anonymous artifact URL. A clean-environment artifact run remains an author release step.
