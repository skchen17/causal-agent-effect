#!/usr/bin/env bash
set -euo pipefail

# Auth-SafeInv reproduction entrypoint.
#
# This script records the intended command order for rebuilding the current
# Auth-SafeInv artifacts. Some steps are GPU-heavy and may take time; run from
# the repository root inside the `causal-safety` conda environment.

PYTHON_BIN="${PYTHON_BIN:-python}"
: "${CUDA_VISIBLE_DEVICES:=1}"
export CUDA_VISIBLE_DEVICES

echo "Using CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES}"

echo "[1/53] Build authorization counterfactuals"
"${PYTHON_BIN}" src/auth/build_authorization_counterfactuals.py

echo "[2/53] Extract Qwen3-8B authorization embeddings"
"${PYTHON_BIN}" src/embeddings/extract_embeddings_llm.py Qwen/Qwen3-8B authorization_counterfactuals_v1.jsonl --batch-size 8

echo "[3/53] Build auth v1 simulated/static traces"
"${PYTHON_BIN}" src/auth/build_auth_execution_traces.py

echo "[4/53] Build auth observed/v2 traces"
"${PYTHON_BIN}" src/auth/build_auth_observed_execution_traces.py

echo "[5/53] Run Auth-SafeInv held-out evaluation"
"${PYTHON_BIN}" src/auth/experiment_auth_safeinv.py qwen3-8b_authorization_counterfactuals_v1

echo "[6/53] Analyze auth surface graph alignment"
"${PYTHON_BIN}" src/auth/analyze_surface_graph_alignment.py authorization_counterfactuals_v1

echo "[7/53] Run pIIA direction and embedding-space controls"
"${PYTHON_BIN}" src/intervention/interchange_intervention_controls.py qwen3-8b_scenarios_mainconf_v2

echo "[8/53] Run pIIA hook controls confirmatory scale-up"
"${PYTHON_BIN}" src/intervention/interchange_intervention_hook_controls.py \
  --data-name qwen3-8b_scenarios_mainconf_v2 \
  --max-effects 6 \
  --max-eval-tools 2 \
  --pairs-per-mode 3 \
  --out-json analysis/piia_hook_controls_confirmatory_qwen3-8b_scenarios_mainconf_v2.json \
  --out-md analysis/piia_hook_controls_confirmatory_qwen3-8b_scenarios_mainconf_v2.md

echo "[9/53] Run Auth-SafeInv strong baseline pilot"
"${PYTHON_BIN}" src/auth/experiment_auth_baselines.py qwen3-8b_authorization_counterfactuals_v1 --torch-epochs 25

echo "[10/53] Run Auth-SafeInv baseline confirmatory sweep"
"${PYTHON_BIN}" src/auth/experiment_auth_baseline_confirmatory.py qwen3-8b_authorization_counterfactuals_v1

echo "[11/53] Run Auth-SafeInv mitigation-vs-baseline comparison"
"${PYTHON_BIN}" src/auth/experiment_auth_mitigation_comparison.py qwen3-8b_authorization_counterfactuals_v1

echo "[12/53] Build authorization counterfactuals v2 surface-graph expansion"
"${PYTHON_BIN}" src/auth/build_authorization_counterfactuals_v2.py

echo "[13/53] Extract Qwen3-8B authorization v2 embeddings"
"${PYTHON_BIN}" src/embeddings/extract_embeddings_llm.py Qwen/Qwen3-8B authorization_counterfactuals_v2.jsonl --batch-size 8

echo "[14/53] Run Auth-SafeInv v2 held-out evaluation"
"${PYTHON_BIN}" src/auth/experiment_auth_safeinv.py qwen3-8b_authorization_counterfactuals_v2

echo "[15/53] Analyze auth v2 surface graph alignment"
"${PYTHON_BIN}" src/auth/analyze_surface_graph_alignment.py authorization_counterfactuals_v2

echo "[16/53] Run Auth-SafeInv v2 baseline confirmatory sweep"
"${PYTHON_BIN}" src/auth/experiment_auth_baseline_confirmatory.py qwen3-8b_authorization_counterfactuals_v2

echo "[17/53] Run Auth-SafeInv v2 mitigation-vs-baseline comparison"
"${PYTHON_BIN}" src/auth/experiment_auth_mitigation_comparison.py qwen3-8b_authorization_counterfactuals_v2

echo "[18/53] Build T55 effect-schema conditioned data"
"${PYTHON_BIN}" src/auth/build_auth_effect_schema_conditioned_data.py

echo "[19/53] Extract Qwen3-8B T55 effect-schema conditioned embeddings"
"${PYTHON_BIN}" src/embeddings/extract_embeddings_llm.py Qwen/Qwen3-8B auth_effect_schema_conditioned_v2.jsonl --batch-size 8

echo "[20/53] Run T55 schema-conditioned mitigation evaluation"
"${PYTHON_BIN}" src/auth/experiment_auth_schema_conditioned_mitigation.py qwen3-8b_auth_effect_schema_conditioned_v2

echo "[21/53] Run T56 full decomposed/verifier mitigation evaluation"
"${PYTHON_BIN}" src/auth/experiment_auth_decomposed_verifier_mitigation.py qwen3-8b_auth_effect_schema_conditioned_v2

echo "[22/53] Run T56 verifier-present full-tool-chain upper-bound evaluation"
"${PYTHON_BIN}" src/auth/experiment_auth_decomposed_verifier_mitigation.py qwen3-8b_auth_effect_schema_conditioned_v2 \
  --conditions full_tool_chain \
  --methods verifier_present_sgd_auth verifier_present_per_effect_sgd_auth \
  --output-suffix _verifier_present_full

echo "[23/53] Run T57 trace-calibrated effect-present verifier evaluation"
"${PYTHON_BIN}" src/auth/experiment_auth_t57_effect_present_verifier.py qwen3-8b_auth_effect_schema_conditioned_v2 \
  --conditions full_tool_chain

echo "[24/53] Build T58 trace candidate-effect data"
"${PYTHON_BIN}" src/auth/build_auth_trace_effect_schema_conditioned_data.py --conditions full_tool_chain

echo "[25/53] Extract Qwen3-8B T58 trace candidate-effect embeddings"
"${PYTHON_BIN}" src/embeddings/extract_embeddings_llm.py Qwen/Qwen3-8B auth_trace_effect_schema_conditioned_v1.jsonl --batch-size 16

echo "[26/53] Run T58 execution-level effect-present verifier evaluation"
"${PYTHON_BIN}" src/auth/experiment_auth_t58_execution_verifier.py --conditions full_tool_chain

echo "[27/53] Build T59 real-agent-tools local-adapter traces"
"${PYTHON_BIN}" src/auth/build_real_agent_tool_execution_traces_t59.py

echo "[28/53] Build T59 real-agent-tools candidate-effect data"
"${PYTHON_BIN}" src/auth/build_auth_trace_effect_schema_conditioned_data.py \
  --input data/agent_tool_traces_real_agent_tools_t59_v1.jsonl \
  --output data/auth_trace_effect_schema_conditioned_t59_v1.jsonl \
  --manifest analysis/auth_trace_effect_schema_conditioned_t59_v1_manifest.json \
  --manifest-md analysis/auth_trace_effect_schema_conditioned_t59_v1_manifest.md \
  --conditions full_tool_chain

echo "[29/53] Extract Qwen3-8B T59 real-agent-tools candidate-effect embeddings"
"${PYTHON_BIN}" src/embeddings/extract_embeddings_llm.py Qwen/Qwen3-8B auth_trace_effect_schema_conditioned_t59_v1.jsonl --batch-size 16

echo "[30/53] Run T59 real-agent-tools execution-level verifier stress test"
"${PYTHON_BIN}" src/auth/experiment_auth_t58_execution_verifier.py \
  --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1 \
  --conditions full_tool_chain

echo "[31/53] Run T62 validation-selected threshold evaluation on T58 controlled traces"
"${PYTHON_BIN}" src/auth/experiment_auth_t62_validation_threshold.py \
  --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_v1

echo "[32/53] Run T62 validation-selected threshold evaluation on T59 real-agent-tools traces"
"${PYTHON_BIN}" src/auth/experiment_auth_t62_validation_threshold.py \
  --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1

echo "[33/53] Run T62 validation-selected threshold evaluation on T61 DeepSeek traces when artifacts exist"
if [[ -f data/auth_trace_effect_schema_conditioned_t61_deepseek_v1.jsonl && -f embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1.npy ]]; then
  "${PYTHON_BIN}" src/auth/experiment_auth_t62_validation_threshold.py \
    --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1
else
  echo "Skipping T61 DeepSeek validation-threshold rerun because API-backed artifacts are absent."
fi

echo "[34/53] Build T63 broader web/search/browser/messaging local-adapter traces"
"${PYTHON_BIN}" src/auth/build_broader_agent_tool_traces_t63.py

echo "[35/53] Build T63 broader tool-family candidate-effect data"
"${PYTHON_BIN}" src/auth/build_auth_trace_effect_schema_conditioned_data.py \
  --input data/agent_tool_traces_broader_tools_t63_v1.jsonl \
  --output data/auth_trace_effect_schema_conditioned_t63_broader_v1.jsonl \
  --manifest analysis/auth_trace_effect_schema_conditioned_t63_broader_v1_manifest.json \
  --manifest-md analysis/auth_trace_effect_schema_conditioned_t63_broader_v1_manifest.md \
  --conditions full_tool_chain

echo "[36/53] Extract Qwen3-8B T63 broader candidate-effect embeddings"
"${PYTHON_BIN}" src/embeddings/extract_embeddings_llm.py Qwen/Qwen3-8B auth_trace_effect_schema_conditioned_t63_broader_v1.jsonl --batch-size 16

echo "[37/53] Run T63 broader execution-level verifier evaluation"
"${PYTHON_BIN}" src/auth/experiment_auth_t58_execution_verifier.py \
  --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1 \
  --conditions full_tool_chain

echo "[38/53] Run T63 broader validation-selected threshold evaluation"
"${PYTHON_BIN}" src/auth/experiment_auth_t62_validation_threshold.py \
  --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1

echo "[39/53] Build T64 key-free live/protocol traces"
"${PYTHON_BIN}" src/auth/build_live_protocol_tool_traces_t64.py

echo "[40/53] Build T64 live/protocol candidate-effect data"
"${PYTHON_BIN}" src/auth/build_auth_trace_effect_schema_conditioned_data.py \
  --input data/agent_tool_traces_live_protocol_t64_v1.jsonl \
  --output data/auth_trace_effect_schema_conditioned_t64_live_protocol_v1.jsonl \
  --manifest analysis/auth_trace_effect_schema_conditioned_t64_live_protocol_v1_manifest.json \
  --manifest-md analysis/auth_trace_effect_schema_conditioned_t64_live_protocol_v1_manifest.md \
  --conditions full_tool_chain

echo "[41/53] Extract Qwen3-8B T64 live/protocol candidate-effect embeddings"
"${PYTHON_BIN}" src/embeddings/extract_embeddings_llm.py Qwen/Qwen3-8B auth_trace_effect_schema_conditioned_t64_live_protocol_v1.jsonl --batch-size 4

echo "[42/53] Run T64 live/protocol execution-level verifier evaluation"
"${PYTHON_BIN}" src/auth/experiment_auth_t58_execution_verifier.py \
  --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1 \
  --conditions full_tool_chain

echo "[43/53] Run T64 live/protocol validation-selected threshold evaluation"
"${PYTHON_BIN}" src/auth/experiment_auth_t62_validation_threshold.py \
  --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1

echo "[44/53] Build T65 file-backed headless Chrome browser-runtime traces"
"${PYTHON_BIN}" src/auth/build_headless_browser_runtime_traces_t65.py --repetitions 30

echo "[45/53] Build T65 browser-runtime candidate-effect data"
"${PYTHON_BIN}" src/auth/build_auth_trace_effect_schema_conditioned_data.py \
  --input data/agent_tool_traces_headless_browser_t65_v1.jsonl \
  --output data/auth_trace_effect_schema_conditioned_t65_browser_v1.jsonl \
  --manifest analysis/auth_trace_effect_schema_conditioned_t65_browser_v1_manifest.json \
  --manifest-md analysis/auth_trace_effect_schema_conditioned_t65_browser_v1_manifest.md \
  --conditions full_tool_chain

echo "[46/53] Extract Qwen3-8B T65 browser-runtime candidate-effect embeddings"
"${PYTHON_BIN}" src/embeddings/extract_embeddings_llm.py Qwen/Qwen3-8B auth_trace_effect_schema_conditioned_t65_browser_v1.jsonl --batch-size 4

echo "[47/53] Run T65 browser-runtime execution-level verifier evaluation"
"${PYTHON_BIN}" src/auth/experiment_auth_t58_execution_verifier.py \
  --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1 \
  --conditions full_tool_chain

echo "[48/53] Run T65 browser-runtime validation-selected threshold evaluation"
"${PYTHON_BIN}" src/auth/experiment_auth_t62_validation_threshold.py \
  --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1

echo "[49/53] Run T68 action-level Auth-SafeInv allow/deny metrics"
"${PYTHON_BIN}" analysis/auth_action_level_metrics.py

echo "[50/53] Run T69 verifier-independence trace-view ablation"
"${PYTHON_BIN}" analysis/auth_trace_view_ablation_t69.py

echo "[51/53] Run T70 existing-defense proxy ablation"
"${PYTHON_BIN}" analysis/auth_existing_defense_ablation_t70.py

echo "[52/53] Run T73 action-level threshold calibration diagnostic"
"${PYTHON_BIN}" analysis/auth_action_level_calibration_t73.py

echo "[53/53] Generate result-source appendix"
"${PYTHON_BIN}" analysis/generate_auth_result_source_appendix.py

echo "Auth-SafeInv reproduction pipeline completed."
