# E75 Unified AgentDojo Comparison

Status: `passed`.
Mode: `official-live-run`.
Main table scope: `saved_replay_exact_case_key_comparison`.
Eligible methods now: `['no_guard', 'ipiguard_normal']`.
Full objective status: `incomplete`.
Official-live full methods now: `[]`.
Final horizontal table eligible now: `False`.

## Environment

AgentDojo status: `{'agentdojo_importable': True, 'e75_venv_python': '/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/runs/e75_agentdojo_env/bin/python', 'e75_venv_agentdojo_importable': True, 'e75_venv_agentdojo_path': '/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/runs/e75_agentdojo_env/lib/python3.12/site-packages/agentdojo/__init__.py', 'ipiguard_repo_present': False, 'camel_repo_present': False, 'external_ipiguard_repo_present': True, 'external_camel_repo_present': True, 'external_toolsafe_repo_present': True, 'local_pi_detector_model_present': True, 'agentdojo_pypi_available_checked': True, 'agentdojo_pypi_version_observed': '0.1.35', 'recommended_live_runner_environment': 'isolated venv under runs/e75_agentdojo_env, not the current conda environment'}`.
Live smoke status: `{'available': True, 'smokes': {'no_guard_workspace_benign_1': {'available': True, 'path': '/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/runs/e75_agentdojo_live_smoke/ipiguard_workspace_benign_none_1.json', 'component': 'agentdojo_no_defense_local_model', 'suite': 'workspace', 'mode': 'benign', 'policy_mode': 'none', 'n_cases': 1, 'n_errors': 0, 'run_complete': True, 'real_side_effects': False, 'tools_executed_in_simulation': True}, 'no_guard_workspace_attack_1': {'available': True, 'path': '/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/runs/e75_agentdojo_live_smoke/ipiguard_workspace_attack_none_1.json', 'component': 'agentdojo_no_defense_local_model', 'suite': 'workspace', 'mode': 'attack', 'policy_mode': 'none', 'n_cases': 1, 'n_errors': 0, 'run_complete': True, 'real_side_effects': False, 'tools_executed_in_simulation': True}}, 'scope': 'live official AgentDojo no-guard smoke only; not full-run and not IPIGuard/other baselines'}`.

## AttriGuard/Baseline Artifact Audit

AttriGuard artifact: `{'status': 'verified_public_zenodo_artifact', 'doi': '10.5281/zenodo.20308739', 'record': 'https://zenodo.org/records/20308739', 'file': 'usenix-artifacts.zip', 'license': 'MIT', 'local_zip': '/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/runs/e75_external_baselines/attriguard_zenodo/usenix-artifacts.zip', 'local_zip_exists': True, 'smoke_logdir': '/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/runs/e75_agentdojo_official_v112_attriguard_smoke', 'smoke_json_logs': 2, 'full_logdir': '/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/runs/e75_agentdojo_official_v112_attriguard', 'full_raw_json_logs': 411, 'native_artifact_parallel_runner_failed': True, 'deterministic_cross_case_sharding_available': True, 'sharded_runner_status_json': '/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/analysis/results/e75_attriguard_sharded_run_status.json', 'sharded_runner_available': True, 'sharded_runner_status': 'failed', 'sharded_runner_imported_official_keys': 726, 'sharded_runner_protocol_attempted_official_keys': 726, 'sharded_runner_protocol_clean_official_keys': 716, 'sharded_runner_protocol_uniform': False, 'sharded_runner_protocol_signatures': []}`.
Baseline audit file: `/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/analysis/results/e75_attriguard_baseline_artifact_audit.md`.

### Adapted Baselines

- `pi_detector_adapted`: attack payload detection `0.677` (426/629), benign false-positive rate `0.0`, projected ASR `0.0`. Scope: adapted screening projection, not a live AgentDojo rerun.

### External Full-Cross Rows

- Scope: external phase5 saved full-cross runs filtered to the official AgentDojo v1.1.2 case-key set; methods with all 726 official keys: `['camel_none_external', 'camel_normal_external', 'camel_strict_external', 'ipiguard_none_external', 'ipiguard_normal_external']`.
- `camel_none_external`: ASR `0.002`, benign utility `0.237`, attack utility `0.251`, errors `0.003`.
- `camel_normal_external`: ASR `0.002`, benign utility `0.227`, attack utility `0.202`, errors `0.081`.
- `camel_strict_external`: ASR `0.002`, benign utility `0.216`, attack utility `0.215`, errors `0.065`.
- `ipiguard_none_external`: ASR `0.0`, benign utility `0.041`, attack utility `0.057`, errors `0.0`.
- `ipiguard_normal_external`: ASR `0.006`, benign utility `0.227`, attack utility `0.232`, errors `0.033`.

### Ours E73 Conservative Projection

- `ours_e73_conservative_projection`: mapped E73 cases `156/726`, unsupported abstain `570`, coverage `0.091`, projected ASR `0.0`, benign utility `0.0`. Scope: conservative projection, not a live AgentDojo rerun and not a full E73 726-key run.

### Full Objective Gap Audit

- Status: `incomplete`.
- Final horizontal table eligible now: `False`.
- Blocking gaps: `['official_live_same_protocol_baselines', 'ours_same_726_case_run', 'attriguard_adapter', 'public_baseline_adapters']`.
- Audit file: `/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/analysis/results/e75_full_objective_gap_audit.md`.

### Live Protocol Check

- Official AgentDojo live smoke full-run ready: `True`. Recommended runner: `AgentDojo model=LOCAL with --tool-delimiter user`. Blocking issue: none. Scope: protocol smoke only, not a 726-case method result.

### Official Live Log Import

- Logdirs: `['/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/experiments/unified-agent-security-baselines/runs/current-c1f-strong-baseline-rerun/c1f/attack/travel/agentdojo_logs']`; imported method-case rows `140`; official case keys `726`; methods with all 726 keys: `[]`. Scope: imported official AgentDojo logs, partial imports are not full horizontal results.
- Target AgentDojo version: `v1.1.2`; source benchmark versions: `{'v1.1.2': 140}`; target-version mismatch rows: `0`.
- Method suite key counts: `{'agentdojo_live_ours_e77_effect_diff_runtime': {'travel': 140}}`.
- Post-tool empty assistant rows: `0`; included rows with missing metrics: `0`.
- Duplicate method/case logs skipped: `0`; non-official attack logs skipped: `0`.
- `agentdojo_live_ours_e77_effect_diff_runtime`: ASR `0.021`, benign utility `None`, attack utility `0.5`, errors `0.0`, post-tool empty assistant `0.0`.

### Official Live Runner

- Last run method `ours_e77_effect_diff_runtime` over suites `['travel']` / modes `['attack']` returned status `passed` into logdir `/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/experiments/unified-agent-security-baselines/runs/current-c1f-strong-baseline-rerun/c1f/attack/travel/agentdojo_logs`. Command-level server 400: `False`; context length exceeded: `False`. Full-table eligibility is determined by the imported method coverage listed above.

## Saved-Replay Diagnostic Table

- `ipiguard_normal`: ASR `0.006`, benign utility `0.227`, attack utility `0.232`, errors `0.033`.
- `no_guard`: ASR `0.0`, benign utility `0.041`, attack utility `0.057`, errors `0.0`.

## Existing Ours Artifact

`{'available': True, 'n_source_traces': 156, 'agent_policy': 'llm_full_authority', 'agentdojo_official_asr_metrics': {'abstain': {'rate': 0.577, 'successes': 90, 'total': 156}, 'accuracy': {'rate': 0.423, 'successes': 66, 'total': 156}, 'coverage': {'rate': 0.423, 'successes': 66, 'total': 156}, 'false_deny': {'rate': 0.0, 'successes': 0, 'total': 156}, 'n': 156, 'n_predictions_available': 156, 'unsafe_pre_allow': {'rate': None, 'successes': 0, 'total': 0}}, 'strict_sidecar_diagnostic_metrics': {'abstain': {'rate': 0.577, 'successes': 90, 'total': 156}, 'accuracy': {'rate': 0.083, 'successes': 13, 'total': 156}, 'coverage': {'rate': 0.423, 'successes': 66, 'total': 156}, 'false_deny': {'rate': 0.0, 'successes': 0, 'total': 22}, 'n': 156, 'n_predictions_available': 156, 'unsafe_pre_allow': {'rate': 0.396, 'successes': 53, 'total': 134}}, 'main_horizontal_table_eligible': False, 'reason': 'Covers E61 156-row mutating-call subset, not the same full AgentDojo case-key set.'}`

## Next Steps

- Keep the completed official-live rows under the same AgentDojo v1.1.2 726-key protocol and do not mix them with saved-replay diagnostics.
- Finish or explicitly exclude remaining public adapters: AttriGuard full artifact run and DataSentinel checkpoint/base-model/adapter path.
- Keep StruQ/SecAlign/MetaSecAlign in a separate model-level table unless they are run through the same AgentDojo backbone protocol.

## Boundary

E75 enforces a same-case-key horizontal comparison standard. The current saved-replay diagnostic table is limited to methods already present in the saved AgentDojo/IPIGuard replay source with identical suite/mode/user-task/injection-task keys: no-guard and IPIGuard-normal. This diagnostic table uses AgentDojo saved fields only: utility, attack_success, errors, and real_side_effects. It is not a live official AgentDojo rerun and must not be treated as the final same-protocol horizontal table. AttriGuard itself has a verified public Zenodo artifact, but is not inserted until an adapter runs it on the same AgentDojo case-key set. The official-live table includes this paper's current atom-intent guard only when it appears as an imported full 726-key AgentDojo row. The older E73 conservative projection, when present, maps only the 156 E61 external subset cases back to official keys and treats the remaining official keys as unsupported abstentions; it remains a coverage/boundary diagnostic, not a final horizontal performance result. Sidecar atom/UPA diagnostics remain secondary and are not mixed with AgentDojo ASR/utility metrics.
