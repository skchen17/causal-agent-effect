#!/bin/bash
# 一键运行: 反事实数据生成 → 嵌入提取 → 线性+非线性探针对比
# 用法: bash run_all.sh [counterfactual|template]
set -euo pipefail

PYTHON=/home/user/anaconda3/envs/causal-safety/bin/python
DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_TYPE="${1:-counterfactual}"

if [ "$DATA_TYPE" = "counterfactual" ]; then
    echo "=== Phase 1: Generate counterfactual data ==="
    "$PYTHON" "$DIR/src/data/generate_counterfactual_data.py"
    DATA_FILE="scenarios_counterfactual.jsonl"
    PROBE_ARG="scenarios_counterfactual"
elif [ "$DATA_TYPE" = "template" ]; then
    echo "=== Phase 1: Generate template data ==="
    "$PYTHON" "$DIR/src/data/generate_data.py"
    DATA_FILE="scenarios_template.jsonl"
    PROBE_ARG="scenarios_template"
else
    echo "Usage: bash run_all.sh [counterfactual|template]"
    exit 1
fi

echo ""
echo "=== Phase 2: Extract LLM embeddings ==="
"$PYTHON" "$DIR/src/embeddings/extract_embeddings.py" "$DATA_FILE"

echo ""
echo "=== Phase 3: Train linear + nonlinear probes ==="
"$PYTHON" "$DIR/src/probes/train_probes.py" "$PROBE_ARG"

echo ""
echo "Done. Results in analysis/ directory."
