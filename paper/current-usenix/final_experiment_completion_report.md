# Final Frozen-Experiment Completion Report

Generated: 2026-08-16T04:15:59.332235+00:00.

All eight required frozen artifacts report `status=passed`; no unfavorable row is removed.

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
- Qwen methods that Pareto-dominate C1f on the three reported counts: `prompt_sandwiching`.

## Claim Boundary

The results support policy-relative effect representation and a bounded provenance-origin mediation instance. They do not establish global minimality, complete authorization, production safety, adaptive AgentLAB reproduction, or SOTA.
