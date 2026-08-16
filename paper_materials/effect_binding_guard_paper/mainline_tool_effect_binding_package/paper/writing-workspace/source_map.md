# Source Map

- Repository root: the enclosing `mainline_tool_effect_binding_package` directory.
- Sole active manuscript: `paper/current-usenix/main.tex`.
- Target: USENIX Security 2027 Cycle 2.
- Canonical claim map: `paper/current-usenix/claim_to_source.md`.
- Machine-readable reproduction index: `paper/current-usenix/reproduction/main_claims.json`.

| Evidence unit | Authoritative artifact | Paper role |
|---|---|---|
| AgentDojo effect prevalence | `experiments/human-authority-and-causal-validation/results/agentdojo-tool-effect-prevalence/agentdojo-tool-effect-prevalence-report.json` | Establish compound/heterogeneous benchmark effects |
| Existing-method binding stress | repaired E47/E48/E50 results under `experiments/binding-failure-and-granularity/results/` | Diagnose partial joint binding and resource/authorization bottleneck |
| 56-call finite source domain | `experiments/human-authority-and-causal-validation/results/finite-domain-effect-binding-validation/finite-domain-validation-report.json` | Representation-collision lower bound |
| 32-context ToolSandbox holdout | `experiments/human-authority-and-causal-validation/results/heldout-toolsandbox-effect-binding-validation/heldout-validation-report.json` | Frozen external-source validation |
| Registration sufficiency | `experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/registration_sufficiency_audit_v2.json` | Disclose 67/67 retention and partial necessity evidence |
| Frozen DeepSeek C1f | `experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/final_guard_repair_report_2026-08-08.json` | Narrow runtime mediation case study |
| Granularity attribution | `experiments/security-analysis-ablation-and-overhead/results/representation-closed-loop-attribution/closed-loop-attribution-report.json` | Selection-conditioned field-vs-whole-call comparison |
| Pending repeated utility | `.../deepseek_benign_interleaved_results.json` | Non-inferiority gate |
| Pending second model | `.../qwen32_matched_results.json` | Cross-model matched comparison |
| Pending locked attacks | `experiments/adaptive-injection-benchmark/results/usenix-heldout-public-families/results.json` | Result-blind public-family holdout |
| Pending transfer | `analysis/results/e79_agentlab_saved_transfer_c1f_results.json` | Fixed saved-attack cross-environment transfer |

Old E55/E84 authority-contract and retracted prompt-guidance artifacts are historical only and are not part of the active claim map.
