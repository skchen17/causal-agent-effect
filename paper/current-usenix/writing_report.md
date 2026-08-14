# USENIX Security '27 Writing Report

Last updated: 2026-08-14.

## Active Manuscript

- Source: `paper/current-usenix/main.tex`.
- Title: *Binding Agent Tool Calls to Effects: Counterfactually Validated Atoms for Pre-Commit Mediation*.
- Target: USENIX Security 2027 Cycle 2.
- Template: the public USENIX two-column style distributed with this workspace.
- Current build: 15 PDF pages total before insertion of the final five-method table; the technical body ends on page 11 after the compact Figure 2 pass. Technical-body counting must be repeated after that result is inserted; total PDF pages are not the submission-limit measure.
- Build state: no undefined citation/reference, missing file, fatal error, or overfull box in the latest successful compile.
- Figures: all four main TikZ figures were redrawn or refined on 2026-08-14. Figure 1 follows the argument from paired calls to source-executed effects and then to coarse versus atom authorization views. Figure 2 adopts a message-oriented actor/interface layout: the offline panel shows executable schema and an untrusted candidate entering a highlighted counterfactual registry, followed by either a counterexample or a frozen descriptor; the online panel shows authenticated authority and the exact agent-proposed call meeting at a highlighted deterministic pre-commit monitor, followed by commit or stop/replan. This removes the former cross-panel arrow, trust-boundary enclosure, and crowded policy branch while preserving the distinction between offline representation validation and online mediation. Figures 3 and 4 summarize representation and security--utility results. A restrained blue/teal/orange/red/gold palette and original TikZ vector icons encode roles without making color the only carrier of meaning; labels, arrow directions, and marker shapes remain sufficient in grayscale. No externally licensed icon asset is bundled in the anonymous artifact.
- Experimental visualization: two evidence figures were added without increasing the technical-body page count. Figure 3 replaces two main-text diagnostic tables with a normalized horizontal-bar comparison of policy-separating pairs in the 56-call AgentDojo source domain and 32-context held-out ToolSandbox domain; absolute counts remain at bar ends and the complete collision tables remain in the appendix. Figure 4 replaces the main DeepSeek runtime table with a two-panel security--utility scatter plot for the official 629-pair and frozen 320-case protocols. Exact scope-aligned values remain in the appendix. Both plots were checked against their source tables, inspected in the compiled two-column PDF, and passed the submission-source audit.

## Controlling Argument

The paper makes three bounded contributions. First, it defines the effect-side representation obligation required by pre-commit authorization and proves the collision tradeoff for authorization-distinct executions that share a monitor view. Second, it uses source-executed counterfactuals to falsify and refine tool-local effect atoms relative to a frozen intervention and policy family. Third, it demonstrates the interface through a finite concrete-atom authorizer and one deterministic provenance-origin monitor driven by a frozen conservative registry.

The 2026-08-14 narrative pass organizes the evidence into four non-interchangeable layers: committed-effect facts, policy-separating witnesses, representation sufficiency, and runtime mediation. The active manuscript now states that the planner proposes calls but cannot define or enlarge the authority context. DeepSeek AgentDojo results are described as a bounded descriptor-driven mediation case study rather than proof of atom-specific numerical dominance.

The same pass now structures Evaluation and Results as four matching research questions: effect prevalence, representation and registration, finite-policy realization, and runtime mediation. Related Work is organized by comparison axis rather than system name. It distinguishes upstream counterfactual attribution of an agent's proposed action from this paper's downstream execution interventions over calls and pre-state. The onboarding candidate may be written by a developer or seeded by an LLM; only source-executed validation supports registration, so the paper makes no automatic contract-synthesis claim.

C1f is not presented as a complete permission system. It does not infer ACLs, delegation, quotas, or arbitrary user authority. Its policy asks whether untrusted observations introduced a registered effect or registered field value outside the authenticated task. Complete mediation and least privilege are treated as prior principles rather than renamed contributions.

## Verified Evidence In The Current PDF

- AgentDojo prevalence: 100/339 calls in 97 benign reference trajectories have normalized state/external-interaction effects; 17 are compound and 13 are heterogeneous or cross-subsystem.
- Controlled binding diagnosis: existing methods have partial axis sensitivity but incomplete joint binding; the repaired resource/authorization stress raises the hard guard's UPA from 0.036 to 0.383.
- Finite source domain: on 56 calls, tool-name and effect-only views induce 564 and 548 authorization-separating pairs; a reviewed typed effect view induces zero under the enumerated policy family.
- Frozen external-source validation: on 32 ToolSandbox contexts, common fields induce 41 separating pairs and typed effects induce zero; eight invalid contexts are retained.
- Finite concrete-atom authorization: all 232 ordered queries over the same 32 ToolSandbox contexts pass the frozen protocol. Concrete typed atoms match the source-effect oracle with 0/150 unsafe pre-allows and 0/82 false denials; tool identity admits 150/150 unauthorized pairs, exact raw arguments admit 14/150 and falsely deny 28/82 authorized pairs, and common effect fields admit 85/150.
- Registration audit: the AgentDojo registry marks 67/67 unique fields security-relevant. A multi-base, suite-scoped audit produces 1,017/1,325 valid interventions, at least five valid intervention kinds for 38/75 field instances, and a committed-effect witness for 66/75. This is conservative coverage and partial necessity evidence, not sparse-field discovery.
- DeepSeek C1f development/frozen evidence: 6/629 no-guard versus 0/629 C1f attack successes, with 2,783 pre-commit checks, 90 denials, no abstentions, and no executed call lacking an allow record. Spotlighting also records 0/629 and higher attack-task utility.
- Closed-loop granularity attribution: on a selection-conditioned 321-case subset, no guard, whole-call provenance, effect-only, and registered-field C1f record 38/273, 11/273, 21/273, and 7/273 attack successes. The completed raw-field control records 10/273, versus 7/273 for C1f; raw fields preserve higher benign and attack-task utility. Atom semantics therefore change decisions and improve security slightly on this subset, but do not establish a selectivity advantage.
- Current AgentLAB saved transfer: under one Qwen3-32B checkpoint and frozen 303-case manifest, no guard records 95/303 attack successes and 185/303 utility, while the provenance-normalized registered-field profile records 1/303 and 132/303. All 1,334 executed guarded calls match pre-commit records exactly. This is fixed saved replay with a substantial utility cost, not adaptive AgentLAB reproduction.
- Repeated DeepSeek benign utility: no guard, Spotlighting, and C1f obtain 301/388, 305/388, and 297/388 successes across four interleaved repetitions. The mean C1f difference is -0.010, but the task-clustered one-sided 95% lower bound is -0.054, so the pre-registered -0.05 non-inferiority criterion is not met.
- Frozen held-out public-family validation: all three methods complete 320/320 rows with no errors. No guard, Spotlighting, and C1f record 4/320, 0/320, and 0/320 attack successes, with task utility 250/320, 238/320, and 235/320.

## Required Result Still Running

- A fresh five-method Qwen3-32B comparison is running. It evaluates no guard, Spotlighting, Prompt Sandwiching, a PromptArmor-style local adapter, and C1f over the same 97 benign and 629 attack keys. Prompt-based adapters are comparable implementations, not original-paper benchmark reproductions.
- Final table rendering, PDF compilation, claim-ledger validation, and the second simulated review are queued after this run.

Intermediate rows from the running job are excluded from paper claims. AgentLAB transfer, four-view, bounded-search, raw-field attribution, and the finite concrete-atom authorizer all report `status=passed`. The only missing required artifact is the five-method Qwen3-32B result.

The current PDF now includes the already passed DeepSeek repeated-benign and 320-case held-out summaries in `sections/generated_final_validation_results.tex`. The strict final generator will overwrite that interim rendering only after the Qwen artifact passes; the fail-fast reproduction status remains pending rather than treating the partial section as final.

## Remaining Experimental Attribution Risk

The frozen registry retains every schema field, and C1f's current value-taint check therefore approximates a generic structured-field provenance policy. The source-oracle collision experiments supply the cleanest independent representation evidence. The completed raw-field control shows a real runtime difference: on identical calls it allows 28 checks that C1f denies, and its closed-loop ASR is 10/273 rather than 7/273. However, raw-field taint also has substantially higher utility. The supportable conclusion is therefore that validated effect semantics add a stricter security distinction, not that they solve the safety--utility tradeoff or dominate generic field taint.

## Reproduction

Run `python scripts/reproduce_usenix_main.py`. The command verifies fixed result schemas, all quantitative cells in the current main tables, and result-bearing prose. The refreshed partial ledger contains 232 verified rows and exits nonzero in strict mode while the five-method strong-baseline artifact is missing. `--allow-pending` regenerates the current JSON/CSV/Markdown index without weakening the final gate. Two unauditable PACT-style auxiliary rows were removed from the ToolSandbox table because no result artifact exposed their values as reproducible keys; this does not change the source-executed common-field versus typed-effect comparison.

The same entry point regenerates `reproduction/sanitized_fixed_support.json` in the source workspace. This path-free extract carries SHA-256 hashes for the two raw early reports whose machine metadata is excluded from the anonymous package; it changes neither result values nor extraction semantics.

## Submission Boundary

The current evidence supports a finite-domain representation result, a counterfactual registration procedure that preserves unresolved fields, and a sandboxed provenance-origin runtime instance. It does not support production safety, universal minimality, open-domain descriptor soundness, complete authorization, deployed traces, unrestricted adaptive robustness, or SOTA claims.
