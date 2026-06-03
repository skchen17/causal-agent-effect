#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-all}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  echo "DEEPSEEK_API_KEY must be set in the environment; it is not read from files." >&2
  exit 2
fi

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate causal-safety
export PYTHONPATH="src/auth:${PYTHONPATH:-}"

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

run_t118() {
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
    --model deepseek-v4-flash \
    --pipeline-label local \
    --logdir runs/agentdojo_t118_strongmax \
    --shard-dir analysis/results/agentdojo_t118_strongmax_shards \
    --output analysis/results/agentdojo_strongmax_matrix_t118.json \
    --output-md analysis/results/agentdojo_strongmax_matrix_t118.md \
    "${pi_args[@]}" \
    "${skip_args[@]}"
}

run_t119() {
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
    --model deepseek-v4-flash \
    --pipeline-label local \
    --shard-dir analysis/results/agentdojo_t119_fc_guard_shards \
    --staged-cache-dir analysis/results/agentdojo_t119_staged_cache \
    --eval-cache-dir analysis/results/agentdojo_t119_eval_cache \
    --output analysis/results/agentdojo_fc_guard_t119.json \
    --output-md analysis/results/agentdojo_fc_guard_t119.md \
    --trace-output data/agentdojo_fc_guard_t119.jsonl
}

run_t120() {
  python src/auth/summarize_agentdojo_strongmax_t120.py \
    --baseline-json analysis/results/agentdojo_strongmax_matrix_t118.json \
    --baseline-shard-dir analysis/results/agentdojo_t118_strongmax_shards \
    --fc-json analysis/results/agentdojo_fc_guard_t119.json \
    --fc-shard-dir analysis/results/agentdojo_t119_fc_guard_shards \
    --authgraph-json analysis/results/agentdojo_authgraph_proxy_t114_deepseek_direct_full949.json \
    --output analysis/results/agentdojo_strongmax_fc_guard_summary_t120.json \
    --output-md analysis/results/agentdojo_strongmax_fc_guard_summary_t120.md
}

case "$TARGET" in
  t118) run_t118 ;;
  t119) run_t119 ;;
  t120) run_t120 ;;
  all) run_t118; run_t119; run_t120 ;;
  *)
    echo "Usage: $0 [all|t118|t119|t120]" >&2
    exit 2
    ;;
esac
