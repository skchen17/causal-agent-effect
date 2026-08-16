# E75 PIGuard Checkpoint Status

Status: `full_726_imported`.
Repository present: `True` at `/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/runs/e75_external_baselines/injecguard`.
Adapter patch present: `True` at `/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/code/src/experiments/effect_binding_guard/e75_unified_agentdojo_comparison/agentdojo_piguard_detector_patch.py`.
HF cache present: `True` at `/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/runs/e75_external_baselines/hf_cache/hub/models--leolee99--PIGuard`.
Latest snapshot: `/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/runs/e75_external_baselines/hf_cache/hub/models--leolee99--PIGuard/snapshots/dd78b24e330193a22d2293ac66922dd4f982f563`.
Tokenizer ready: `True`.
Model weight ready: `True`.
AgentDojo smoke log count: `2`.
Official-live imported keys: `726`.
Main-table eligible now: `True`.

## Snapshot Files

- `added_tokens.json`
- `config.json`
- `model.safetensors`
- `modeling_piguard.py`
- `special_tokens_map.json`
- `spm.model`
- `tokenizer.json`
- `tokenizer_config.json`

## Incomplete Blobs

- none

## Last Smoke Attempt

`{'tokenizer_load': 'passed_with_network_escalation', 'model_load': 'passed', 'agentdojo_smoke': 'passed', 'failure_mode': ''}`

## Next Step

No PIGuard action needed for the same-protocol table; keep the checkpoint/run boundary with the metrics.

## Boundary

PIGuard is a same-protocol official-live AgentDojo row for this paper's common 726-key v1.1.2 table; it is not an original PIGuard benchmark reproduction.
