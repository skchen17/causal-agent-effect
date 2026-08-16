#!/usr/bin/env python3
"""Read-only per-variant completeness check (protocol section 9, Phase 3).

Run immediately after each full variant finishes; never mutates any file and
never looks at comparative headline metrics.  Gates checked:

1. exactly 726 rows (or the scope's expected count), one per manifest key;
2. no duplicate and no missing case keys;
3. every row carries the protocol section 6 required fields (null allowed
   where the protocol allows null, but the key must exist);
4. benign rows have official_attack_success == null;
5. frozen-input hashes are identical across all rows (single-variant slice);
6. no row reports run_completed=False silently: failures are listed.

Exit code 0 = pass, 1 = integrity failure.  This check does NOT decide
whether later variants run (protocol: a failed variant is re-run later, the
other variants proceed).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
EXPERIMENT_ROOT = ROOT / "experiments/security-analysis-ablation-and-overhead"
EVAL_DIR = EXPERIMENT_ROOT / "evaluation/strict-atom-representation-attribution"
RUNS_BASE = EXPERIMENT_ROOT / "runs/strict-atom-representation-attribution/qwen32"

SCOPE_MANIFEST = {
    "smoke": ("smoke-subset.jsonl", 16),
    "full": ("all-official-cases.jsonl", 726),
    "stability": ("stability-subset.jsonl", 160),
}

REQUIRED_FIELDS = [
    "protocol_id",
    "run_id",
    "repeat_index",
    "variant",
    "case_key",
    "suite",
    "mode",
    "user_task_id",
    "attack_type",
    "injection_task_id",
    "official_benign_utility",
    "official_attack_utility",
    "official_attack_success",
    "run_completed",
    "scorer_completed",
    "runtime_error",
    "n_candidate_effectful_calls",
    "n_precommit_checks",
    "n_allow",
    "n_deny",
    "n_abstain",
    "n_needs_replan",
    "n_uncertainty_override",
    "n_executed_effectful_calls",
    "n_strictly_authorized_executed_calls",
    "n_unregistered_tool_calls",
    "initial_plan_hash",
    "final_plan_hash",
    "prompt_hashes",
    "tool_call_hashes",
    "runtime_audit_path",
    "model_hash",
    "manifest_hash",
    "runtime_catalog_hash",
    "relation_catalog_hash",
    "tool_schema_hash",
    "decoding_hash",
    "scorer_hash",
]

FROZEN_HASH_FIELDS = [
    "protocol_id",
    "initial_plan_hash",
    "model_hash",
    "manifest_hash",
    "runtime_catalog_hash",
    "relation_catalog_hash",
    "tool_schema_hash",
    "decoding_hash",
    "scorer_hash",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--scope", choices=tuple(SCOPE_MANIFEST), default="full")
    parser.add_argument("--repeat-index", type=int, default=0)
    parser.add_argument("--runs-base", default=str(RUNS_BASE))
    args = parser.parse_args(argv)

    manifest_name, expected_count = SCOPE_MANIFEST[args.scope]
    manifest_path = EVAL_DIR / manifest_name
    expected_keys = [
        json.loads(line)["case_key"]
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(expected_keys) == expected_count

    results_path = (
        Path(args.runs_base) / args.variant / f"repeat-{args.repeat_index}"
        / "paired-case-results.jsonl"
    )
    errors: list[str] = []
    if not results_path.exists():
        print(json.dumps({"variant": args.variant, "status": "FAIL",
                          "errors": [f"missing {results_path}"]}, indent=2))
        return 1
    rows = [
        json.loads(line)
        for line in results_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    if len(rows) != expected_count:
        errors.append(f"row count {len(rows)} != expected {expected_count}")
    seen: dict[str, int] = {}
    for row in rows:
        seen[row.get("case_key", "<missing-key>")] = (
            seen.get(row.get("case_key", "<missing-key>"), 0) + 1
        )
    duplicates = sorted(k for k, n in seen.items() if n > 1)
    missing = sorted(set(expected_keys) - set(seen))
    if duplicates:
        errors.append(f"{len(duplicates)} duplicate case keys")
    if missing:
        errors.append(f"{len(missing)} missing case keys")

    for field in REQUIRED_FIELDS:
        if any(field not in row for row in rows):
            errors.append(f"required field absent in some rows: {field}")

    benign_asr_violations = [
        row["case_key"]
        for row in rows
        if row.get("mode") == "benign"
        and row.get("official_attack_success") is not None
    ]
    if benign_asr_violations:
        errors.append(
            f"{len(benign_asr_violations)} benign rows with non-null "
            f"official_attack_success"
        )

    for field in FROZEN_HASH_FIELDS:
        values = {row.get(field) for row in rows if field in row}
        if len(values) > 1:
            errors.append(f"frozen field disagrees across rows: {field}")
        if None in values or "" in values:
            errors.append(f"frozen field has null/empty value: {field}")

    failed_runs = sorted(
        row["case_key"] for row in rows if not row.get("run_completed")
    )
    unscored = sorted(
        row["case_key"] for row in rows if not row.get("scorer_completed")
    )

    report = {
        "variant": args.variant,
        "scope": args.scope,
        "repeat_index": args.repeat_index,
        "results_path": str(results_path.relative_to(ROOT))
        if results_path.is_relative_to(ROOT)
        else str(results_path),
        "rows": len(rows),
        "expected": expected_count,
        "duplicate_keys": len(duplicates),
        "missing_keys": len(missing),
        "failed_runs": failed_runs,
        "unscored": unscored,
        "errors": errors,
        "status": "PASS" if not errors else "FAIL",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
