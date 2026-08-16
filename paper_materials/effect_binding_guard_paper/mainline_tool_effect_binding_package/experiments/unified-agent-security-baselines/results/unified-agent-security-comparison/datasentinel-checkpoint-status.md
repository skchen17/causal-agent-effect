# E75 DataSentinel Checkpoint Status

Status: `checkpoint_download_partial_base_model_missing`.
Repository present: `True` at `/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/runs/e75_external_baselines/open_prompt_injection`.
Detector source present: `True` at `/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/runs/e75_external_baselines/open_prompt_injection/OpenPromptInjection/apps/DataSentinelDetector.py`.
Checkpoint zip ready: `False` at `/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/runs/e75_external_baselines/datasentinel_checkpoint/datasentinel_ft.zip`.
Checkpoint partial bytes: `176685056`.
Base model ready: `False`.
AgentDojo adapter present: `False`.
Official-live imported keys: `0`.
Main-table eligible now: `False`.

## Public Checkpoint Source

`https://drive.google.com/file/d/1B0w5r5udH3I_aiZL0_-2a8WzBAqjuLsn/view?usp=sharing`

## Partial Files

- `runs/e75_external_baselines/datasentinel_checkpoint/datasentinel_ft.zip.partial`: `176685056` bytes

## Base Model Candidates Checked

- `/data/CSK/causal-agent-safety-research/models/mistralai/Mistral-7B-v0.1`: `missing`
- `/data/CSK/causal-agent-safety-research/models/Mistral-7B-v0.1`: `missing`
- `/data/CSK/causal-agent-safety-research/.hf_cache/hub/models--mistralai--Mistral-7B-v0.1`: `missing`

## Next Step

Resume the public Google Drive checkpoint download and obtain/cache mistralai/Mistral-7B-v0.1; then implement an AgentDojo observation-screening adapter.

## Boundary

DataSentinel is only a public-code/checkpoint candidate in the current E75 artifacts. It is not a same-protocol horizontal result until the checkpoint, base model, adapter, and full 726-key official-live import all exist.
