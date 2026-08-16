#!/usr/bin/env bash
set -euo pipefail

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-1}"
BASE_URL="${BASE_URL:-http://127.0.0.1:18080/v1}"
MODEL="${MODEL:-Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf}"
BOOTSTRAP_ITERS="${BOOTSTRAP_ITERS:-2000}"

python -m src.experiments.tool_effect_fragmentation.phase5_local_server start
trap 'python -m src.experiments.tool_effect_fragmentation.phase5_local_server stop >/dev/null 2>&1 || true' EXIT

python -m src.experiments.tool_effect_fragmentation.phase5_original_runner \
  --stage build \
  --system both \
  --base-url "${BASE_URL}"

external/systems/ipiguard/agentdojo/.venv/bin/python \
  -m src.experiments.tool_effect_fragmentation.phase5_ipiguard_component_worker \
  --resume \
  --base-url "${BASE_URL}" \
  --model "${MODEL}"

external/systems/camel/.venv/bin/python \
  -m src.experiments.tool_effect_fragmentation.phase5_camel_component_worker

python -m src.experiments.tool_effect_fragmentation.phase5_original_runner \
  --stage smoke \
  --system ipiguard \
  --suite all \
  --attack important_instructions \
  --case-protocol full_cross_product \
  --max-cases 0 \
  --resume \
  --worker-timeout 86400 \
  --base-url "${BASE_URL}" \
  --model "${MODEL}"

python -m src.experiments.tool_effect_fragmentation.phase5_original_runner \
  --stage smoke \
  --system camel \
  --suite all \
  --attack important_instructions \
  --case-protocol full_cross_product \
  --max-cases 0 \
  --resume \
  --worker-timeout 86400 \
  --base-url "${BASE_URL}" \
  --model "${MODEL}"

python -m src.experiments.tool_effect_fragmentation.run_tool_effect_fragmentation_phase5 \
  --bootstrap-iters "${BOOTSTRAP_ITERS}"
