# Main Experiment Map

The table follows the paper's evidence order. Result files are frozen evidence;
runner scripts are the code paths that generated or validate them.

| Evidence layer | Main question | Runner | Frozen result |
|---|---|---|---|
| Effect prevalence | Do benchmark tool calls commit compound or heterogeneous effects? | `shared/compatibility/scripts/run_agentdojo_tool_effect_prevalence.py` | `experiments/human-authority-and-causal-validation/results/agentdojo-tool-effect-prevalence/agentdojo-tool-effect-prevalence-report.json` |
| Finite representation | Do coarse views merge authorization-distinct source effects? | `shared/compatibility/scripts/run_finite_domain_effect_binding_validation.py` | `experiments/human-authority-and-causal-validation/results/finite-domain-effect-binding-validation/finite-domain-validation-report.json` |
| Held-out source validation | Does the typed representation transfer to a separately frozen ToolSandbox domain? | `shared/compatibility/scripts/run_toolsandbox_heldout_validation.py` | `experiments/human-authority-and-causal-validation/results/heldout-toolsandbox-effect-binding-validation/heldout-validation-report.json` |
| Counterfactual refinement | Does each accepted split monotonically reduce finite ambiguity? | `experiments/security-analysis-ablation-and-overhead/source/refinement-monotonicity-check/run_refinement_monotonicity_check.py` | `experiments/security-analysis-ablation-and-overhead/results/refinement-monotonicity-check/refinement-monotonicity-report.json` |
| Registration coverage | Which AgentDojo schema fields have valid effect-changing witnesses? | `experiments/intent-bound-runtime-guard/scripts/counterfactual-atom-envelope-guard/run_registration_sufficiency_audit_v2.py` | `experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/registration_sufficiency_audit_v2.json` |
| Concrete authorization | Can concrete atoms exactly implement the frozen finite authority relation? | `shared/compatibility/scripts/run_toolsandbox_concrete_atom_authorizer.py` | `experiments/human-authority-and-causal-validation/results/concrete-atom-authorizer-mechanism/concrete-atom-authorizer-report.json` |
| Policy-family attribution | Which representations separate exhaustively generated finite policy predicates? | `shared/compatibility/scripts/run_representation_mechanism_attribution.py` | `experiments/security-analysis-ablation-and-overhead/results/representation-mechanism-attribution/representation-mechanism-attribution-report.json` |
| Atom-vs-field attribution | What information is gained by typed effects when field coverage and policies are fixed? | `shared/compatibility/scripts/run_atom_vs_field_semantic_attribution.py` | `experiments/security-analysis-ablation-and-overhead/results/atom-vs-field-semantic-attribution/atom-vs-field-report.json` |
| Runtime mediation | Can a frozen descriptor drive deterministic, auditable pre-commit decisions? | `shared/compatibility/code/shadow_atom_envelope_c1f/src/experiments/effect_binding_guard/e77_effect_diff_runtime_guard/` | `experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard/final_guard_repair_report_2026-08-08.json` |
| Runtime mechanism control | Does effect semantics differ from generic raw-field taint? | `shared/compatibility/scripts/run_c1f_raw_field_attribution.py` | `experiments/security-analysis-ablation-and-overhead/results/c1f-raw-field-attribution/raw-field-attribution-report.json` |
| Strong baselines | How do five methods compare under one checkpoint and exact key set? | `shared/compatibility/scripts/run_current_c1f_qwen32_strong_baseline_rerun.py` | Pending; only the frozen protocol is released until the full artifact passes. |

## Recommended Deterministic Rerun

```bash
python shared/compatibility/scripts/run_finite_domain_effect_binding_validation.py
python shared/compatibility/scripts/run_toolsandbox_concrete_atom_authorizer.py --mode full
python shared/compatibility/scripts/run_representation_mechanism_attribution.py
python shared/compatibility/scripts/run_atom_vs_field_semantic_attribution.py --mode full
```

These commands use frozen local artifacts and do not invoke an LLM. AgentDojo live
runs require the separately documented benchmark/model environment. The held-out
ToolSandbox source replay additionally requires `bash scripts/setup_toolsandbox.sh`.

## Interpretation Boundary

The finite experiments establish representation sufficiency only on their frozen
domains and policy families. The runtime experiment instantiates provenance-origin
confinement over registered fields/effect labels, not a general concrete-atom ACL.
Negative utility and attribution results are retained in the artifact.
