# E63 Gemma4 Rerun Status

Requested model:
`/data/CSK/causal-agent-safety-research/.hf_cache/hub/models--google--gemma-4-26B-A4B-it`

Resolved snapshot:
`/data/CSK/causal-agent-safety-research/.hf_cache/hub/models--google--gemma-4-26B-A4B-it/snapshots/462a98a12e28e2cbcfccaf78fe41e3e50235e6ae`

Status: `four_bit_smoke_blocked_full_run_not_executed`.

The prior Qwen E63 full-run artifacts were not overwritten.

## What Ran

- Added a Gemma4-specific text-only runner:
  `code/src/experiments/effect_binding_guard/e63_counterfactual_contract_refinement/run_e63_gemma4_transformers.py`.
- Updated the strict parser to strip `<think>`, `<thought>`, and `<analysis>` blocks before JSON extraction.
- Added a BitsAndBytes 4-bit Gemma4 path to the runner, including a no-standalone-`lm_head` text-only class, explicit two-GPU layer maps, NF4/FP4 selection, BF16/FP16/FP32 compute dtype selection, and optional compact E63 prompting.
- Added compact E63 prompting. The first-round Gemma4 chat prompt drops from roughly `1414` chat-template tokens to roughly `676` tokens.
- Loaded the Gemma4 language model through `Gemma4ForCausalLM` with exact `model.language_model.* -> model.*` key mapping.
- Verified `657` language weight keys, `0` non-`lm_head` missing keys, and `0` unexpected language keys.
- Forced MoE experts to `eager` implementation after the default `batched_mm` path OOMed on E63-length prompts.
- Ran a real one-tool E63 raw-round smoke:
  `analysis/results/e63_gemma4_smoke_eager_128_report.json`.

## Smoke Result

- Tool: `forward_email`.
- Prompt leakage violations: `0`.
- Feedback leakage violations: `0`.
- Local LLM status: `executed`.
- Parse-valid contracts: `0/1`.
- Freezeable contracts: `0/1`.
- Failure: the 128-token cap produced a real but truncated JSON object:
  `<FINAL_JSON>{ "tool_name": "forward_email", "templates": ...`.

This is a genuine Gemma4 model-output smoke, but it is not a model-quality result and cannot be used as full E63 evidence.

## 4-bit Quantization Attempt

The 4-bit path was implemented and smoke-tested, but the E63 full-run was not started because no 4-bit E63 smoke produced a contract output.

Artifacts:

- `analysis/results/e63_gemma4_4bit_smoke_report.json`: one-tool 4-bit smoke failed before output with a residual `22 MiB` CUDA OOM on GPU 1.
- `analysis/results/e63_gemma4_4bit_smoke_balanced_128_report.json`: balanced layer split failed before output with a residual `20 MiB` CUDA OOM on GPU 1.
- `analysis/results/e63_gemma4_4bit_smoke_custommap_128_report.json`: custom map placing the final layer on GPU 0 failed before output with a residual `24 MiB` CUDA OOM on GPU 0.
- `analysis/results/e63_gemma4_4bit_compact_smoke_256_report.json`: compact prompt with NF4/BF16 failed before output with `CUBLAS_STATUS_NOT_SUPPORTED` in BitsAndBytes 4-bit matmul.
- `analysis/results/e63_gemma4_4bit_compact_fp4_smoke_64_report.json`: compact prompt with FP4/BF16 failed before output with the same BitsAndBytes 4-bit matmul error.

A very short non-E63 prompt can emit tokens under the custom no-standalone-head 4-bit loader, so the loader is not purely dead. However, the actual E63 prompt still fails before any parseable contract is produced. Treat this as a serving/runtime blocker, not as evidence about Gemma4 contract quality.

## Blockers

1. vLLM BF16 without CPU offload is slightly over the two-4090D memory budget.
2. vLLM CPU offload reaches model initialization but fails on the input-batch reinitialization assertion.
3. vLLM BitsAndBytes does not support Gemma4 MoE for this checkpoint.
4. Transformers text-only BF16 loading works only with CPU offload.
5. Transformers default MoE `batched_mm` attempts an 82-83 GiB allocation for the E63 prompt.
6. Forced `eager` MoE avoids OOM but is too slow for full E63: 256/512-token smoke runs were interrupted after long runtime.
7. Transformers BitsAndBytes 4-bit can load far enough to attempt generation only with a no-standalone-`lm_head` text model and explicit layer maps, but E63 smoke prompts still fail with residual CUDA OOM or `CUBLAS_STATUS_NOT_SUPPORTED`.

## Claim Boundary

Gemma4 has been started and can produce local output through the new text-only runner, but no parse-valid E63 contract and no full-run result exists. The 4-bit quantized path was implemented and smoke-tested, but it did not produce E63 contract output. The current valid full E63 local-LLM evidence remains the Qwen GGUF run.

Recommended next step: use an efficient Gemma4 serving stack or smaller/quantized Gemma-family checkpoint, or build a compact contract DSL/constrained decoder before trying Gemma4 full-run again.
