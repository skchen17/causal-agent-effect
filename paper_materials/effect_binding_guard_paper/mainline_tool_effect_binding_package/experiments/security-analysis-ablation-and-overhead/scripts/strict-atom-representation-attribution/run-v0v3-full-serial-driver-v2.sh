#!/usr/bin/env bash
# V1->V3 full-run serial driver for PROTOCOL V2 (D2 resume artifact).
#
# Context: protocol v2 (2026-08-05) redefined V1 as a TRUE whole-call
# comparator. V0 was already executed to completion under protocol v1 and is
# retained via the lineage note (protocol v2 doc section 5); this driver
# therefore runs V1, V2, V3 only, in strict serial order.
#
# Safeguards (fail-closed):
# - Preflight 1: protocol.json must declare protocol_version v2 and its
#   sha256[:16] must equal the issued protocol_id e830b9b24138f8ad.
# - Preflight 2: whole-call-envelopes.json must exist and match the hash
#   recorded in protocol.json (the runner re-verifies at launch, but the
#   driver refuses to burn GPU hours on a broken freeze).
# - Per-variant skip gate: a variant whose repeat-0 results already hold 726
#   rows AND pass the read-only completeness check is SKIPPED (recorded in
#   the manifest), never re-run or appended to.
# - A failing variant does NOT skip the remaining variants (protocol Phase 3).
#
# Optional override: V2_VARIANTS="opaque_whole_call validated_atom_fields"
# to restrict the run list.
set -u

PKG=/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package
PY="$PKG/runs/e75_agentdojo_env/bin/python"
RUNNER="$PKG/experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/run-strict-attribution.py"
CHECKER="$PKG/experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/check-variant-completeness.py"
EVAL_DIR="$PKG/experiments/security-analysis-ablation-and-overhead/evaluation/strict-atom-representation-attribution"
RUNS_BASE="$PKG/experiments/security-analysis-ablation-and-overhead/runs/strict-atom-representation-attribution/qwen32"
MANIFEST="$RUNS_BASE/_v1v3_full_driver_v2_protocol_v2_manifest_2026-08-05.log"
PORT=18087
REPEAT=0
EXPECTED_PROTOCOL_ID=e830b9b24138f8ad
VARIANTS="${V2_VARIANTS:-opaque_whole_call raw_schema_fields validated_atom_fields}"

cd "$PKG"
mkdir -p "$RUNS_BASE"

refuse() { echo "[driver-v2] REFUSED: $1" | tee -a "$MANIFEST" >&2; exit 2; }

# --- Preflight 1: protocol v2 freeze -----------------------------------------
PROTOCOL_VERSION=$("$PY" -c "import json;print(json.load(open('$EVAL_DIR/protocol.json')).get('protocol_version',''))")
[ "$PROTOCOL_VERSION" = "v2" ] || refuse "protocol.json protocol_version is '$PROTOCOL_VERSION', expected v2"
ACTUAL_ID=$(sha256sum "$EVAL_DIR/protocol.json" | cut -c1-16)
[ "$ACTUAL_ID" = "$EXPECTED_PROTOCOL_ID" ] || refuse "protocol.json sha256[:16]=$ACTUAL_ID, expected $EXPECTED_PROTOCOL_ID"

# --- Preflight 2: envelope registry integrity --------------------------------
ENVELOPE_EXPECTED=$("$PY" -c "import json;print(json.load(open('$EVAL_DIR/protocol.json'))['hashes']['whole-call-envelopes.json'])")
[ -f "$EVAL_DIR/whole-call-envelopes.json" ] || refuse "missing whole-call-envelopes.json"
ENVELOPE_ACTUAL=$(sha256sum "$EVAL_DIR/whole-call-envelopes.json" | cut -d' ' -f1)
[ "$ENVELOPE_ACTUAL" = "$ENVELOPE_EXPECTED" ] || refuse "envelope hash $ENVELOPE_ACTUAL != protocol hash $ENVELOPE_EXPECTED"
SIDECAR=$(cut -d' ' -f1 "$EVAL_DIR/whole-call-envelopes.json.sha256")
[ "$SIDECAR" = "$ENVELOPE_ACTUAL" ] || refuse "envelope sidecar $SIDECAR != file hash $ENVELOPE_ACTUAL"

echo "[driver-v2] $(date -Is) start pid=$$ protocol_id=$ACTUAL_ID envelope=$ENVELOPE_ACTUAL" >> "$MANIFEST"

for VARIANT in $VARIANTS; do
  RUN_DIR="$RUNS_BASE/$VARIANT/repeat-$REPEAT"
  RESULTS="$RUN_DIR/paired-case-results.jsonl"
  LOG="/tmp/v0v3-v2-$VARIANT.log"

  # Skip gate: complete + checked results are never re-run.
  if [ -f "$RESULTS" ] && [ "$(wc -l < "$RESULTS")" -eq 726 ]; then
    PYTHONPATH=code:. "$PY" "$CHECKER" \
      --variant "$VARIANT" --scope full --repeat-index "$REPEAT" > /tmp/v2-skip-check-$VARIANT.json 2>&1
    if [ $? -eq 0 ]; then
      echo "[driver-v2] $(date -Is) SKIP variant=$VARIANT (726 rows + completeness PASS)" >> "$MANIFEST"
      echo "[driver-v2] skipping $VARIANT (already complete and checked)"
      continue
    fi
    echo "[driver-v2] $(date -Is) variant=$VARIANT has 726 rows but completeness check FAILED; will --resume" >> "$MANIFEST"
  fi

  echo "[driver-v2] $(date -Is) LAUNCH variant=$VARIANT log=$LOG run_dir=$RUN_DIR" >> "$MANIFEST"
  PYTHONPATH=code:. "$PY" "$RUNNER" \
    --scope full --variant "$VARIANT" --repeat-index "$REPEAT" \
    --port "$PORT" --resume > "$LOG" 2>&1 &
  PID=$!
  echo "[driver-v2] $(date -Is) RUNNING variant=$VARIANT pid=$PID" >> "$MANIFEST"
  echo "[driver-v2] launched $VARIANT pid=$PID (log: $LOG)"
  wait "$PID"
  RC=$?
  echo "[driver-v2] $(date -Is) EXIT variant=$VARIANT pid=$PID rc=$RC" >> "$MANIFEST"
  echo "[driver-v2] $(date -Is) CHECK variant=$VARIANT begin" >> "$MANIFEST"
  PYTHONPATH=code:. "$PY" "$CHECKER" \
    --variant "$VARIANT" --scope full --repeat-index "$REPEAT" >> "$MANIFEST" 2>&1
  CRC=$?
  echo "[driver-v2] $(date -Is) CHECK variant=$VARIANT rc=$CRC" >> "$MANIFEST"
  echo "[driver-v2] $VARIANT exited rc=$RC, completeness check rc=$CRC"
done

echo "[driver-v2] $(date -Is) all variants done (V0 retained under protocol-v1 lineage)" >> "$MANIFEST"
echo "[driver-v2] done; manifest: $MANIFEST"
