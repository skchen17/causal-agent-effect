#!/bin/bash
# N condition (no_guard) for the benign97 three-way comparison — DeepSeek v4-flash.
# Task lists are generated statically from the preregistered 97-case manifest
# (benign97_three_way_manifest_2026-08-08.json) — NOT hand-typed.
# Protocol: pilot protocol C.5 four-suite form (interface_fix_and_deepseek_pilot_2026-08-07.md).
#
# Requires (set by caller): REP_LABEL (e.g. r1|r2), E77_LLM_BASE_URL, E77_LLM_API_KEY, E77_LLM_MODEL.
# Optional: E75PY (default = unified-agent-security-baselines venv python).
set -euo pipefail
cd "$(dirname "$0")/../../../.."
ROOT=$(pwd)
EVAL=$ROOT/experiments/intent-bound-runtime-guard/evaluation/effect-difference-runtime-guard
MANIFEST=$EVAL/benign97_three_way_manifest_2026-08-08.json
LOGDIR=$ROOT/experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/deepseek-benign97-n-20260808-${REP_LABEL:-MISSING_REP}/agentdojo_logs
E75PY=${E75PY:-$ROOT/experiments/unified-agent-security-baselines/runs/unified-agent-security-comparison/agentdojo-env/bin/python}

# Generate "SUITE:TASK1 TASK2 ..." lines from the manifest (deterministic order).
SUITE_LINES=$(python3 - "$MANIFEST" <<'PYEOF'
import json, sys
from collections import defaultdict
m = json.load(open(sys.argv[1]))
by = defaultdict(list)
for c in m["cases"]:
    by[c["suite"]].append(c["user_task_id"])
for s in sorted(by):
    tasks = sorted(by[s], key=lambda t: int(t.split("_")[-1]))
    print(f"{s}:{' '.join(tasks)}")
PYEOF
)

mkdir -p "$LOGDIR"
while IFS= read -r SUITE_TASKS; do
  SUITE=${SUITE_TASKS%%:*}; TASKS=${SUITE_TASKS#*:}
  TASK_ARGS=""; for T in $TASKS; do TASK_ARGS="$TASK_ARGS --live-user-task $T"; done
  echo "[benign97-N-${REP_LABEL}] suite=$SUITE tasks=$(echo $TASKS | wc -w) logdir=$LOGDIR"
  PYTHONPATH=code:. \
  "$E75PY" -m src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.run_e75 \
    --mode official-live-run --agentdojo-version v1.1.2 \
    --live-method no_guard --live-suites "$SUITE" --live-modes benign \
    $TASK_ARGS --live-logdir "$LOGDIR" --local-llm-port 18087 \
    > "$LOGDIR/../command_status.$SUITE.log" 2>&1
  rc=$?
  echo "[benign97-N-${REP_LABEL}] suite=$SUITE rc=$rc"
  [ $rc -eq 0 ] || { echo "FAILED suite=$SUITE rc=$rc"; exit $rc; }
done <<< "$SUITE_LINES"
echo "[benign97-N-${REP_LABEL}] ALL SUITES DONE"
