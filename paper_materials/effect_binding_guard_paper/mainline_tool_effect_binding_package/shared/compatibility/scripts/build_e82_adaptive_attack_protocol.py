#!/usr/bin/env python3
"""Freeze and validate the E82 payload-free adaptive-attack protocol."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.experiments.effect_binding_guard.e82_adaptive_attack_protocol import protocol_rows, validate_protocol


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "evaluation/e82_adaptive_attacks"
RESULTS = ROOT / "analysis/results"


def main() -> int:
    rows = [row.to_dict() for row in protocol_rows()]
    validation = validate_protocol(rows)
    if validation["status"] != "passed":
        raise RuntimeError(json.dumps(validation, sort_keys=True))
    manifest = {
        "experiment": "E82",
        "artifact_type": "adaptive_attack_protocol",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "protocol_validated_case_materialization_pending",
        "protocol_version": "e82_usenix27_v1",
        "attacks": rows,
        "validation": validation,
        "required_full_run_outputs": [
            "case_manifest.jsonl", "results_no_guard.json", "results_effect_contract_guard.json",
            "predictions_no_guard.jsonl", "predictions_effect_contract_guard.jsonl",
        ],
        "claim_boundary": (
            "This artifact freezes attack capabilities, budgets, observations, denominator rules, and environment-level success relations. "
            "It is protocol-readiness evidence only; no adaptive victim-model result is claimed until exact cases and both method outputs exist."
        ),
    }
    EVAL.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (EVAL / "attack_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (RESULTS / "e82_adaptive_attack_protocol_readiness.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# E82 Adaptive-Attack Protocol Readiness", "", f"Status: `{manifest['status']}`.", "",
        f"The frozen matrix contains `{validation['n_attacks']}` strategies (T1--T12). Every row has a fixed search budget, "
        "observable feedback contract, environment-level success relation, and denominator-retention rule.", "",
        "No victim-model attack result is present yet. Exact case materialization and identical no-guard/guard runs remain required.", "",
        "## Claim Boundary", "", manifest["claim_boundary"], "",
    ]
    (RESULTS / "e82_adaptive_attack_protocol_readiness.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "n_attacks": validation["n_attacks"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
