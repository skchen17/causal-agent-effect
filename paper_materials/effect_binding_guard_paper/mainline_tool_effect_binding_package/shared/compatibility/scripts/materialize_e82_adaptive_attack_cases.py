#!/usr/bin/env python3
"""Materialize a deterministic, payload-free E82 AgentDojo subset."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "runs/e77_agentdojo_official_v112_full_20260712_075718_e77_full_gpu1/local-ours_e77_effect_diff_runtime"
PROTOCOL = ROOT / "evaluation/e82_adaptive_attacks/attack_manifest.json"
OUTPUT = ROOT / "evaluation/e82_adaptive_attacks"


def sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def base_attack_keys(source: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in source.rglob("*.json"):
        parts = path.relative_to(source).parts
        if len(parts) != 4:
            continue
        suite, user_task_id, attack_type, filename = parts
        injection_task_id = Path(filename).stem
        if not user_task_id.startswith("user_task_") or not injection_task_id.startswith("injection_task_"):
            continue
        key = f"{suite}/{user_task_id}/{attack_type}/{injection_task_id}"
        rows.append({
            "suite": suite,
            "user_task_id": user_task_id,
            "attack_type": attack_type,
            "injection_task_id": injection_task_id,
            "official_case_key": key,
            "official_case_key_sha256": hashlib.sha256(key.encode()).hexdigest(),
            "frozen_source_log_sha256": sha256_bytes(path),
        })
    return sorted(rows, key=lambda row: row["official_case_key"])


def select_stratified(rows: list[dict[str, str]], per_suite: int) -> list[dict[str, str]]:
    suites = sorted({row["suite"] for row in rows})
    selected: list[dict[str, str]] = []
    for suite in suites:
        candidates = [row for row in rows if row["suite"] == suite]
        ranked = sorted(candidates, key=lambda row: (row["official_case_key_sha256"], row["official_case_key"]))
        if len(ranked) < per_suite:
            raise RuntimeError(f"suite {suite} has only {len(ranked)} attack keys")
        selected.extend(ranked[:per_suite])
    return sorted(selected, key=lambda row: row["official_case_key"])


def materialize(source: Path, per_suite: int) -> tuple[list[dict], dict]:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    attacks = protocol["attacks"]
    base = base_attack_keys(source)
    if len(base) != 629:
        raise RuntimeError(f"expected 629 official attack keys, found {len(base)}")
    selected = select_stratified(base, per_suite)
    rows = []
    for base_row in selected:
        for attack in attacks:
            case_id = f"E82-{attack['attack_id']}-{base_row['official_case_key_sha256'][:16]}"
            rows.append({
                "case_id": case_id,
                "attack_id": attack["attack_id"],
                "suite": base_row["suite"],
                "user_task_id": base_row["user_task_id"],
                "attack_type": base_row["attack_type"],
                "injection_task_id": base_row["injection_task_id"],
                "official_case_key": base_row["official_case_key"],
                "official_case_key_sha256": base_row["official_case_key_sha256"],
                "frozen_source_log_sha256": base_row["frozen_source_log_sha256"],
                "mutation_operator": attack["mutation_operator"],
                "attacker_observes": attack["attacker_observes"],
                "search_budget": attack["search_budget"],
                "environment_evaluator": attack["environment_evaluator"],
                "success_predicate": attack["success_predicate"],
                "base_payload_in_manifest": False,
                "status": "pending_variant_generation_and_execution",
            })
    ids = [row["case_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate E82 case id")
    summary = {
        "experiment": "E82",
        "status": "case_manifest_frozen_execution_pending",
        "official_attack_key_inventory": len(base),
        "selected_base_attack_keys": len(selected),
        "per_suite": per_suite,
        "suite_counts": dict(sorted(Counter(row["suite"] for row in selected).items())),
        "adaptive_strategies": len(attacks),
        "materialized_strategy_case_pairs": len(rows),
        "attack_counts": dict(sorted(Counter(row["attack_id"] for row in rows).items())),
        "contains_raw_attack_payload": False,
        "contains_environment_outcomes": False,
        "selection": "lowest SHA-256 official case keys within each suite",
        "claim_boundary": (
            "The 480-row manifest freezes evaluator-side case identities and adaptive strategy budgets without embedding attack text. "
            "It contains no victim outputs or security results; variant generation and same-checkpoint no-guard/guard execution remain pending."
        ),
    }
    return rows, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--per-suite", type=int, default=10)
    args = parser.parse_args()
    rows, summary = materialize(args.source, args.per_suite)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "case_manifest.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )
    (OUTPUT / "case_manifest_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
