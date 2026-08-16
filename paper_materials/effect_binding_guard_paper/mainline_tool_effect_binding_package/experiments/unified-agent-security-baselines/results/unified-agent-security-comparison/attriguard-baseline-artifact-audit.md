# E75 AttriGuard Baseline Artifact Audit

Source paper: AttriGuard: Defeating Indirect Prompt Injection in LLM Agents via Causal Attribution of Tool Invocations
AttriGuard artifact: `{'status': 'verified_public_zenodo_artifact', 'doi': '10.5281/zenodo.20308739', 'record': 'https://zenodo.org/records/20308739', 'file': 'usenix-artifacts.zip', 'license': 'MIT', 'local_zip': '/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/runs/e75_external_baselines/attriguard_zenodo/usenix-artifacts.zip', 'local_zip_exists': True, 'smoke_logdir': '/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/runs/e75_agentdojo_official_v112_attriguard_smoke', 'smoke_json_logs': 2, 'full_logdir': '/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/runs/e75_agentdojo_official_v112_attriguard', 'full_raw_json_logs': 411, 'native_artifact_parallel_runner_failed': True, 'deterministic_cross_case_sharding_available': True, 'sharded_runner_status_json': '/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/analysis/results/e75_attriguard_sharded_run_status.json', 'sharded_runner_available': True, 'sharded_runner_status': 'failed', 'sharded_runner_imported_official_keys': 726, 'sharded_runner_protocol_attempted_official_keys': 726, 'sharded_runner_protocol_clean_official_keys': 716, 'sharded_runner_protocol_uniform': False, 'sharded_runner_protocol_signatures': []}`

## Baselines

| Method | Role in AttriGuard | Public artifact status | Local status | Priority | URL |
|---|---|---|---|---|---|
| attriguard | proposed_method | verified_zenodo_software_artifact | local_artifact_downloaded_smoke_passed_full_pending | candidate_after_adapter | https://doi.org/10.5281/zenodo.20308739 |
| pi_detector | detection_baseline | verified_public_huggingface_model | local_model_present | high | https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2 |
| promptguard | detection_baseline | verified_gated_huggingface_model | not_runnable_without_hf_access | blocked_by_credentials | https://huggingface.co/meta-llama/Prompt-Guard-86M |
| piguard | detection_baseline | verified_git_repository | repo_cloned_adapter_implemented_full_run_pending | high | https://github.com/safolab-wisc/injecguard |
| datasentinel | detection_baseline | verified_git_repository_family | checkpoint_download_partial_base_model_missing | medium | https://github.com/liu00222/Open-Prompt-Injection |
| promptarmor | sanitizer_baseline | not_verified_as_public_code | paper_defined_local_adapter_available | medium | https://arxiv.org/abs/2507.15219 |
| melon | detection_baseline | verified_git_repository | repo_cloned_local_comparable_adapter_implemented_full_run_pending | medium | https://github.com/kaijiezhu11/MELON |
| prompt_sandwiching | prompting_baseline | paper_defined_prompting_strategy | paper_defined_adapter_implemented_full_run_pending | high | https://learnprompting.org/docs/prompt_hacking/defensive_measures/sandwich_defense |
| spotlighting | prompting_baseline | verified_git_repository | paper_defined_delimiting_adapter_full_run_pending | high | https://github.com/realArcherL/spotlighting-datamarking |
| struq | training_baseline | verified_git_repository | not_installed | separate_model_level_table | https://github.com/Sizhe-Chen/StruQ |
| secalign | training_baseline | verified_git_repository | not_installed | separate_model_level_table | https://github.com/facebookresearch/SecAlign |
| meta_secalign | training_baseline | verified_git_repository | not_installed | separate_model_level_table | https://github.com/facebookresearch/Meta_SecAlign |
| camel | system_level_baseline | verified_git_repository | external_repo_present | high_after_protocol_alignment | https://github.com/google-research/camel-prompt-injection |
| ipiguard | system_level_baseline | verified_git_repository | external_repo_present_and_saved_replay_present | already_in_saved_replay_table | https://github.com/Greysahy/ipiguard |

## Recommended Order

- Treat no_guard, repeat_user_prompt, spotlighting, transformers_pi_detector, prompt_sandwiching, PIGuard, PromptArmor-local, MELON-local, and this paper's current live guard as completed same-key official-live rows.
- Next inspect or supply DataSentinel/Open-Prompt-Injection's required fine-tuned checkpoint path and continue the AttriGuard artifact shard runner.
- Keep PromptGuard blocked until gated model access is available.
- Keep StruQ/SecAlign/MetaSecAlign in a separate model-level comparison unless rerun with the same AgentDojo backbone.
- Treat AttriGuard itself as a candidate adapter from Zenodo, not as absent code.
