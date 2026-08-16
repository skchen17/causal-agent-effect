# Source Index

## Venue Sources

| Source | Use In Manuscript |
|---|---|
| [NDSS 2027 Call for Papers](https://www.ndss-symposium.org/ndss2027/submissions/call-for-papers/) | Venue fit, page limit, systems-security positioning, fall deadline context. |
| [NDSS 2027 Submissions](https://www.ndss-symposium.org/ndss2027/submissions/) | Submission and template routing. |
| [NDSS 2027 Call for Artifacts](https://www.ndss-symposium.org/ndss2027/submissions/call-for-artifacts/) | Artifact/reproducibility expectations and artifact appendix framing. |

## Related-Work Sources Checked

| Source | Paper Role |
|---|---|
| [AgentDojo arXiv page](https://arxiv.org/abs/2406.13352) | Benchmark context for prompt-injection and tool-agent security evaluation. |
| [ToolEmu arXiv page](https://arxiv.org/abs/2309.15817) | High-stakes tool-agent risk evaluation through an LM-emulated sandbox. |
| [CaMeL arXiv page](https://arxiv.org/abs/2503.18813) | Capability/security-layer comparison point for tool-agent control/data-flow mediation. |
| [IPIGuard arXiv page](https://arxiv.org/abs/2508.15310) | Tool-dependency-graph comparison point for indirect prompt-injection defenses. |
| [ToolSafe arXiv page](https://arxiv.org/abs/2601.10156) | Step-level tool invocation safety and TS-Guard custom-stress comparison point. |
| [Safiron arXiv page](https://arxiv.org/abs/2510.09781) | Pre-execution guardrail comparison point and custom-stress checkpoint row. |
| [Progent arXiv page](https://arxiv.org/abs/2504.11703) | Programmable least-privilege policy representation and deterministic tool-call enforcement. |
| [MiniScope arXiv page](https://arxiv.org/abs/2512.11147) | Permission hierarchy reconstruction and least-privilege authorization for tool-calling agents. |

## Local Evidence Sources

| Source | Paper Role |
|---|---|
| `paper/writing-workspace/evidence_bank.md` | Canonical local number map for the active paper. |
| `results/analysis/results/e48_tuple_guard_results.json` | Reference hard Effect-Binding Guard main custom-stress numbers. |
| `results/analysis/results/e50_hard_guard_robustness_results.json` | Resource/authorization and provenance stress-test bottleneck evidence. |
| `tables/table1_existing_defenses_capability_matrix.md` | Existing-method custom-stress capability profiles. |
| `tables/tables/official_checkpoint_summary.md` | Released-checkpoint stress summaries for TS-Guard and Safiron. |
| `audit/analysis/results/e55_v2_precommit_authz_results_strict.json` | Main E55-v2 pre-commit authorization prototype result. |
| `results/analysis/results/e55_human_corrected_sensitivity.json` | Original E55 human-corrected sensitivity. |
| `audit/analysis/results/e57_human_audit_validation.json` | Completed 60-row human audit and correction counts. |
| `audit/analysis/results/e57_v2_validity_checks_report.json` | E55-v2 perturbation and independent reference-authorizer checks. |

## Citation Hygiene Notes

- External sources are used for positioning and comparison, not as evidence for this paper's own metrics.
- Local result files are the only source for numeric claims about Effect-Binding Guard, E55/E57, and custom-stress evaluations.
- Existing-method rows are described as custom-stress evaluations of released checkpoints/components, not original-paper benchmark reproductions.
