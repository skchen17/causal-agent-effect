#!/bin/bash
# Master experiment pipeline — reproduces all experiments in order.
# Usage: bash run_experiments.sh [qwen3-8b_scenarios_merged]
set -euo pipefail

PYTHON=/home/user/anaconda3/envs/causal-safety/bin/python
DIR="$(cd "$(dirname "$0")" && pwd)"
DATA="${1:-qwen3-8b_scenarios_merged}"

echo "=============================================="
echo " Full Experiment Pipeline"
echo " Data: $DATA"
echo "=============================================="

# Phase 0: Data generation (run once)
echo ""
echo "--- Phase 0: Data Generation ---"
echo "  (skip if data already exists)"
if [ ! -f "$DIR/data/scenarios_counterfactual.jsonl" ]; then
    "$PYTHON" "$DIR/src/data/generate_counterfactual_data.py"
fi
if [ ! -f "$DIR/data/targeted_synthetic.jsonl" ]; then
    "$PYTHON" "$DIR/src/data/generate_targeted_data.py"
fi
if [ ! -f "$DIR/data/scenarios_merged.jsonl" ]; then
    "$PYTHON" "$DIR/src/data/merge_data.py"
fi

# Phase 1: Embedding extraction
echo ""
echo "--- Phase 1: Embedding Extraction ---"
echo "  MiniLM:"
"$PYTHON" "$DIR/src/embeddings/extract_embeddings.py" scenarios_merged.jsonl
echo "  Qwen3-8B:"
"$PYTHON" "$DIR/src/embeddings/extract_embeddings_llm.py" Qwen/Qwen3-8B scenarios_merged.jsonl

# Phase 2: Probe training (linear + nonlinear delta)
echo ""
echo "--- Phase 2: Probe Training ---"
"$PYTHON" "$DIR/src/probes/train_probes.py" scenarios_merged
"$PYTHON" "$DIR/src/probes/train_probes.py" qwen3-8b_scenarios_merged

# Phase 3: Cross-tool generalization
echo ""
echo "--- Phase 3: Cross-Tool Generalization ---"
"$PYTHON" "$DIR/src/probes/cross_tool_generalization.py" scenarios_merged
"$PYTHON" "$DIR/src/probes/cross_tool_generalization.py" qwen3-8b_scenarios_merged

# Phase 4: Pairwise tool matrix
echo ""
echo "--- Phase 4: Pairwise Tool Matrix ---"
"$PYTHON" "$DIR/src/probes/pairwise_tool_matrix.py" qwen3-8b_scenarios_merged

# Phase 5: True IIA (interchange intervention)
echo ""
echo "--- Phase 5: True IIA (interchange intervention) ---"
"$PYTHON" "$DIR/src/intervention/interchange_intervention_true.py"

# Phase 6: Baseline comparison + LOTO table
echo ""
echo "--- Phase 6: Baseline Comparison ---"
"$PYTHON" "$DIR/src/experiments/experiment_baselines.py" qwen3-8b_scenarios_merged

# Phase 7: FNR + Frag analysis
echo ""
echo "--- Phase 7: FNR + Frag Analysis ---"
"$PYTHON" "$DIR/src/experiments/experiment_fnr_frag.py" qwen3-8b_scenarios_merged

echo ""
echo "=============================================="
echo " All experiments complete."
echo " Results in: $DIR/analysis/"
echo "=============================================="
