# E75 Ours Full Atom Runtime Official Full Run Report

- Status: `completed`
- Method: `agentdojo_live_ours_full_atom_runtime`
- AgentDojo version: `v1.1.2`
- Official imported keys: `726/726`
- GPU policy: `CUDA_VISIBLE_DEVICES=1`; Qwen server ran on GPU1 only
- Run status: `passed_with_model_request_errors`; import status: `passed`
- Logdir: `/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/runs/e75_agentdojo_official_v112_ours_full_atom_runtime_gpu1_full_20260709_210020_ours_full_gpu1`
- Audit JSONL: `/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/runs/e75_ours_full_atom_runtime_audit_gpu1_full_20260709_210020_ours_full_gpu1.jsonl`

## Main Metrics

| Metric | Value |
|---|---:|
| Total official rows | 726 |
| Benign rows | 97 |
| Attack rows | 629 |
| Benign utility | 48/97 = 0.495 |
| Attack success | 17/629 = 0.027 |
| Attack user utility | 270/629 = 0.429 |
| Error rows | 0 |
| Post-tool empty assistant rows | 82 = 0.113 |

## Runtime Guard Audit

| Audit item | Value |
|---|---:|
| Audit rows | 4007 |
| Task plans | 696 |
| Task plan parse failures | 31 |
| Precommit checks | 3311 |
| Precommit `ALLOW` | 2346 |
| Precommit `ALLOW_EXPLICIT_OVERRIDE` | 452 |
| Precommit `NEEDS_REPLAN` | 513 |

## Run Diagnostics

All AgentDojo subprocesses returned code `0`. Some workspace/travel subprocess logs include context-length `400` diagnostics from local Qwen calls; the official log importer still found complete rows for all 726 manifest keys and `n_error=0`.

## Claim Boundary

This is a same-protocol official AgentDojo v1.1.2 live run on the 726-key manifest for this paper's ours_full_atom_runtime adapter. It is not a production-safety claim. The run status records context-length/server-400 diagnostics in some suites, but the importer found 726 complete official rows with n_error=0.
