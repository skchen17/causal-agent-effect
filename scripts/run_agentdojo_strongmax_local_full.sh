#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-all}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate causal-safety
export PYTHONPATH="src/auth:${PYTHONPATH:-}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-1}"

LOCAL_MODEL_PATH="${AGENTDOJO_LOCAL_MODEL_PATH:-models/Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf}"
LOCAL_MODEL_NAME="${AGENTDOJO_LOCAL_MODEL_NAME:-qwen3.5-9b-deepseek-v4-flash-gguf}"
LOCAL_IO_LOGDIR="${AGENTDOJO_LOCAL_IO_LOGDIR:-runs/agentdojo_local_model_io_strongmax}"

if [[ ! -s "$LOCAL_MODEL_PATH" ]]; then
  echo "Local GGUF model not found: $LOCAL_MODEL_PATH" >&2
  exit 2
fi

ensure_llama_cpp() {
  python - <<'PY'
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("llama_cpp") is not None else 1)
PY
}

ensure_pi_detector_model() {
  if [[ "${SKIP_TRANSFORMERS_PI_DETECTOR:-0}" == "1" ]]; then
    return
  fi

  local default_dir="models/protectai_deberta-v3-base-prompt-injection-v2"
  local required=(
    "config.json"
    "model.safetensors"
    "tokenizer.json"
    "tokenizer_config.json"
    "special_tokens_map.json"
    "added_tokens.json"
    "spm.model"
  )

  if [[ -z "${AGENTDOJO_PI_DETECTOR_MODEL:-}" && -f "$default_dir/model.safetensors" ]]; then
    export AGENTDOJO_PI_DETECTOR_MODEL="$default_dir"
  fi
  if [[ -n "${AGENTDOJO_PI_DETECTOR_MODEL:-}" && -f "${AGENTDOJO_PI_DETECTOR_MODEL}/model.safetensors" ]]; then
    return
  fi
  if [[ "${AUTO_DOWNLOAD_HF_MODELS:-1}" != "1" ]]; then
    return
  fi

  local mirror="${HF_MIRROR_BASE:-https://hf-mirror.com}"
  mkdir -p "$default_dir"
  for file in "${required[@]}"; do
    if [[ ! -s "$default_dir/$file" ]]; then
      echo "Downloading PI detector dependency via mirror: $file" >&2
      curl -fL --retry 3 --connect-timeout 20 --max-time 900 \
        -o "$default_dir/$file" \
        "$mirror/protectai/deberta-v3-base-prompt-injection-v2/resolve/main/$file"
    fi
  done
  export AGENTDOJO_PI_DETECTOR_MODEL="$default_dir"
}

common_local_args=(
  --model-backend local
  --model "$LOCAL_MODEL_NAME"
  --pipeline-label local
  --local-model-path "$LOCAL_MODEL_PATH"
  --local-io-logdir "$LOCAL_IO_LOGDIR"
)

run_t118_smoke() {
  ensure_llama_cpp
  ensure_pi_detector_model
  local pi_args=()
  if [[ -n "${AGENTDOJO_PI_DETECTOR_MODEL:-}" ]]; then
    pi_args+=(--pi-detector-model "$AGENTDOJO_PI_DETECTOR_MODEL")
  fi
  python src/auth/agentdojo_strongmax_matrix_t118.py \
    --run-agentdojo \
    --resume \
    --benchmark-version v1.2.2 \
    --suite workspace \
    --attack direct \
    --attack important_instructions \
    --defense none \
    --defense repeat_user_prompt \
    --max-user-tasks 2 \
    --max-injection-tasks 2 \
    --logdir runs/agentdojo_t118_strongmax_local_smoke \
    --shard-dir analysis/results/agentdojo_t118_strongmax_local_smoke_shards \
    --output analysis/results/agentdojo_strongmax_matrix_t118_local_smoke.json \
    --output-md analysis/results/agentdojo_strongmax_matrix_t118_local_smoke.md \
    "${common_local_args[@]}" \
    "${pi_args[@]}"
}

run_t118() {
  ensure_llama_cpp
  local skip_args=()
  local pi_args=()
  if [[ "${SKIP_TRANSFORMERS_PI_DETECTOR:-0}" == "1" ]]; then
    skip_args+=(--skip-defense transformers_pi_detector)
  else
    ensure_pi_detector_model
    if [[ -n "${AGENTDOJO_PI_DETECTOR_MODEL:-}" ]]; then
      pi_args+=(--pi-detector-model "$AGENTDOJO_PI_DETECTOR_MODEL")
    fi
  fi
  python src/auth/agentdojo_strongmax_matrix_t118.py \
    --run-agentdojo \
    --resume \
    --benchmark-version v1.2.2 \
    --attack-set strong_max \
    --defense-set paper \
    --logdir runs/agentdojo_t118_strongmax_local \
    --shard-dir analysis/results/agentdojo_t118_strongmax_local_shards \
    --output analysis/results/agentdojo_strongmax_matrix_t118_local.json \
    --output-md analysis/results/agentdojo_strongmax_matrix_t118_local.md \
    "${common_local_args[@]}" \
    "${pi_args[@]}" \
    "${skip_args[@]}"
}

run_t119_smoke() {
  ensure_llama_cpp
  python src/auth/agentdojo_fc_guard_t119.py \
    --run-agentdojo \
    --resume \
    --benchmark-version v1.2.2 \
    --suite workspace \
    --attack direct \
    --attack important_instructions \
    --policy fc_prod_proxy_v1 \
    --max-user-tasks 2 \
    --max-injection-tasks 2 \
    --shard-dir analysis/results/agentdojo_t119_fc_guard_local_smoke_shards \
    --staged-cache-dir analysis/results/agentdojo_t119_staged_local_smoke_cache \
    --eval-cache-dir analysis/results/agentdojo_t119_eval_local_smoke_cache \
    --output analysis/results/agentdojo_fc_guard_t119_local_smoke.json \
    --output-md analysis/results/agentdojo_fc_guard_t119_local_smoke.md \
    --trace-output data/agentdojo_fc_guard_t119_local_smoke.jsonl \
    "${common_local_args[@]}"
}

run_t119() {
  ensure_llama_cpp
  python src/auth/agentdojo_fc_guard_t119.py \
    --run-agentdojo \
    --resume \
    --benchmark-version v1.2.2 \
    --attack-set strong_max \
    --policy fc_prod_proxy_v1 \
    --policy no_staging_posthoc_checker \
    --policy effect_resource_boundary \
    --policy tool_whitelist_only \
    --policy allow_all \
    --policy deny_all \
    --shard-dir analysis/results/agentdojo_t119_fc_guard_local_shards \
    --staged-cache-dir analysis/results/agentdojo_t119_staged_local_cache \
    --eval-cache-dir analysis/results/agentdojo_t119_eval_local_cache \
    --output analysis/results/agentdojo_fc_guard_t119_local.json \
    --output-md analysis/results/agentdojo_fc_guard_t119_local.md \
    --trace-output data/agentdojo_fc_guard_t119_local.jsonl \
    "${common_local_args[@]}"
}

run_t120() {
  python src/auth/summarize_agentdojo_strongmax_t120.py \
    --baseline-json analysis/results/agentdojo_strongmax_matrix_t118_local.json \
    --baseline-shard-dir analysis/results/agentdojo_t118_strongmax_local_shards \
    --fc-json analysis/results/agentdojo_fc_guard_t119_local.json \
    --fc-shard-dir analysis/results/agentdojo_t119_fc_guard_local_shards \
    --authgraph-json analysis/results/agentdojo_authgraph_proxy_t114_deepseek_direct_full949.json \
    --output analysis/results/agentdojo_strongmax_fc_guard_summary_t120_local.json \
    --output-md analysis/results/agentdojo_strongmax_fc_guard_summary_t120_local.md
}

case "$TARGET" in
  smoke) run_t118_smoke; run_t119_smoke ;;
  t118-smoke) run_t118_smoke ;;
  t119-smoke) run_t119_smoke ;;
  t118) run_t118 ;;
  t119) run_t119 ;;
  t120) run_t120 ;;
  all) run_t118; run_t119; run_t120 ;;
  *)
    echo "Usage: $0 [all|smoke|t118-smoke|t119-smoke|t118|t119|t120]" >&2
    exit 2
    ;;
esac

