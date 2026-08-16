#!/usr/bin/env python3
"""v17 merged vs E78-era no_guard benign pairing (read-only, CPU-only).

PURPOSE
  Recompute, on the v17 merged caliber, the benign no-defense-success ->
  guard-failure transition table that the E78-era pathway audit reported for
  the E78-era runs (then: 37 transitions, 32/37 with runtime feedback).  The
  E78-era composition is thus re-derived for the CURRENT merged system.

CALIBER (frozen in this docstring before computing any number)
  P1  v17 side: 97 official benign cases of the merged root, utility taken
      from the payload (anchor: 46/97, verified, fail otherwise).
  P2  Baseline side: experiments/unified-agent-security-baselines/runs/
      strong-model-baseline-comparison/qwen32-strong-baselines/agentdojo_logs/
      no_guard/local/<suite>/<user_task>/none/none.json (anchor 64/97,
      verified).  This is the E78-era no-defense run used for the headline
      66% figure; same model (Qwen3-32B-Q4_K_M), same AgentDojo v1.1.2,
      different runner era.  Transitions therefore confound the guard with
      runner/runtime evolution between eras; report as such.
  P3  Keys are suite:user_task_id:none:none; pairing requires the key to be
      present on both sides (expected 97).
  P4  Transition classes:
        T_LOSS    no_guard utility True  -> v17 utility False
        T_GAIN    no_guard utility False -> v17 utility True
        BOTH_FAIL / BOTH_OK otherwise.
  P5  Cross-tabulation: join with the loss-decomposition artifact
      (v17-merged-utility-loss-decomposition.json) by case key to report,
      within T_LOSS, the failure stratum, interface-finding presence and
      runtime-feedback presence (from that artifact; no re-derivation).

Output: same directory as the loss-decomposition artifact.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *HERE.parents)
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
METHOD = "local-ours_e77_effect_diff_runtime"
MERGED = (
    ROOT
    / "experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/"
    "recovery-normalization-qwen32-full-allow-with-trail-v17-726-r2-context-repaired"
)
NO_GUARD_ROOT = (
    ROOT
    / "experiments/unified-agent-security-baselines/runs/strong-model-baseline-comparison/"
    "qwen32-strong-baselines/agentdojo_logs/no_guard/local"
)
LOSS_DECOMP = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "strict-atom-representation-attribution/utility-loss-decomposition/"
    "v17-merged-utility-loss-decomposition.json"
)
OUT_DIR = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "strict-atom-representation-attribution/utility-loss-decomposition"
)

SUITES = ("workspace", "slack", "travel", "banking")


def is_benign_payload(payload: dict[str, Any]) -> bool:
    suite = str(payload.get("suite_name"))
    if suite not in SUITES:
        return False
    if payload.get("injection_task_id") not in (None, "none", ""):
        return False
    if payload.get("attack_type") not in (None, "none", ""):
        return False
    return not str(payload.get("user_task_id")).startswith("injection_task_")


def load_benign(root: Path) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("none.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(payload, dict) or not is_benign_payload(payload):
            continue
        key = f"{payload['suite_name']}:{payload['user_task_id']}:none:none"
        if key in cases:
            raise SystemExit(f"duplicate benign key: {key}")
        cases[key] = {
            "utility": bool(payload.get("utility")),
            "error": payload.get("error"),
        }
    return cases


def main() -> int:
    v17 = load_benign(MERGED / "agentdojo_logs" / METHOD)
    noguard = load_benign(NO_GUARD_ROOT)
    if len(v17) != 97 or sum(1 for c in v17.values() if c["utility"]) != 46:
        raise SystemExit(f"v17 anchor failed: {len(v17)} cases")
    if len(noguard) != 97 or sum(1 for c in noguard.values() if c["utility"]) != 64:
        raise SystemExit(f"no_guard anchor failed: {len(noguard)} cases")
    common = sorted(set(v17) & set(noguard))
    if len(common) != 97:
        raise SystemExit(f"pairing incomplete: {len(common)}/97")

    classes = {"T_LOSS": [], "T_GAIN": [], "BOTH_FAIL": [], "BOTH_OK": []}
    for key in common:
        ng = noguard[key]["utility"]
        vg = v17[key]["utility"]
        if ng and not vg:
            classes["T_LOSS"].append(key)
        elif not ng and vg:
            classes["T_GAIN"].append(key)
        elif not ng and not vg:
            classes["BOTH_FAIL"].append(key)
        else:
            classes["BOTH_OK"].append(key)

    loss_detail: dict[str, dict[str, Any]] = {}
    if LOSS_DECOMP.is_file():
        decomp = json.loads(LOSS_DECOMP.read_text(encoding="utf-8"))
        for row in decomp["benign"]["failed_case_list"]:
            loss_detail[row["case"]] = row

    cross: dict[str, Any] = {"with_interface_finding": 0, "with_runtime_feedback": 0,
                             "with_blocked_rows": 0, "by_stratum": {}, "no_decomp_row": []}
    for key in classes["T_LOSS"]:
        row = loss_detail.get(key)
        if row is None:
            cross["no_decomp_row"].append(key)
            continue
        if row["interface_finding_rows"] > 0:
            cross["with_interface_finding"] += 1
        if row["runtime_feedback_events"] > 0:
            cross["with_runtime_feedback"] += 1
        if row["n_rows"] - row["n_attempted"] > 0:
            cross["with_blocked_rows"] += 1
        cross["by_stratum"][row["stratum"]] = cross["by_stratum"].get(row["stratum"], 0) + 1

    report = {
        "schema": "v17-vs-noguard-benign-pairing/1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "anchors": {"v17_benign_utility": "46/97", "no_guard_benign_utility": "64/97"},
        "inputs": {
            "v17_merged_root": str(MERGED),
            "no_guard_root": str(NO_GUARD_ROOT),
        },
        "transitions": {k: {"n": len(v), "cases": v} for k, v in classes.items()},
        "t_loss_cross_tab": cross,
        "caveats": [
            "no_guard rows come from the E78-era strong-baseline run (same model and benchmark, earlier runner); transitions confound guard effect with runner/runtime evolution and with run-to-run nondeterminism.",
            "Pairing is case-level; the two runs are independent temperature-0 trajectories.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "v17-vs-noguard-benign-pairing.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"\n[pairing] ok -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
