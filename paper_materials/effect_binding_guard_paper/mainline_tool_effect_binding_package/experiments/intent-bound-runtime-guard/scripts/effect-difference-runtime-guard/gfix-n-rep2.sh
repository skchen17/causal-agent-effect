#!/bin/bash
# N rep2 (no_guard, DeepSeek) — protocol C.5 form; new logdir.
# Requires: E77_LLM_BASE_URL / E77_LLM_API_KEY / E77_LLM_MODEL set by caller.
set -e
cd "$(dirname "$0")/../../../.."
ROOT=$(pwd)
LOGDIR=$ROOT/experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/deepseek-noguard-rep2-20260807/agentdojo_logs
E75PY=experiments/unified-agent-security-baselines/runs/unified-agent-security-comparison/agentdojo-env/bin/python
mkdir -p "$LOGDIR"
for SUITE_TASKS in \
  "banking:user_task_0 user_task_1 user_task_10 user_task_11 user_task_12 user_task_13 user_task_14 user_task_15 user_task_2 user_task_3 user_task_5 user_task_7 user_task_8" \
  "slack:user_task_0 user_task_11 user_task_12 user_task_13 user_task_15 user_task_16 user_task_17 user_task_18 user_task_19 user_task_2 user_task_3 user_task_5 user_task_6 user_task_7 user_task_8" \
  "travel:user_task_0 user_task_1 user_task_10 user_task_16 user_task_18 user_task_4 user_task_5 user_task_7 user_task_8 user_task_9" \
  "workspace:user_task_0 user_task_1 user_task_10 user_task_11 user_task_12 user_task_13 user_task_14 user_task_15 user_task_16 user_task_18 user_task_2 user_task_20 user_task_21 user_task_24 user_task_26 user_task_28 user_task_3 user_task_33 user_task_36 user_task_4 user_task_5 user_task_6 user_task_7 user_task_8 user_task_9"; do
  SUITE=${SUITE_TASKS%%:*}; TASKS=${SUITE_TASKS#*:}
  TASK_ARGS=""; for T in $TASKS; do TASK_ARGS="$TASK_ARGS --live-user-task $T"; done
  PYTHONPATH=code:. \
  $E75PY -m src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.run_e75 \
    --mode official-live-run --agentdojo-version v1.1.2 \
    --live-method no_guard --live-suites $SUITE --live-modes benign \
    $TASK_ARGS --live-logdir "$LOGDIR" --local-llm-port 18087 \
    > "$LOGDIR/../command_status.$SUITE.log" 2>&1
  echo "[N-rep2] $SUITE rc=$?"
done
