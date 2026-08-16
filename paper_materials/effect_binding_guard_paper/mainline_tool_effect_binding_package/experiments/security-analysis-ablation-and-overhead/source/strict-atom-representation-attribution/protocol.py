"""Strict atom representation attribution protocol: manifest and checks.

Phase 0 CPU work per the frozen protocol
`paper/current-usenix/strict_atom_representation_attribution_protocol_2026-08-03.md`.

This module is pure and importable without a GPU. It implements:

- 726 official-case manifest enumeration from AgentDojo API data;
- deterministic 160-case stability subset and 16-case smoke subset;
- leakage and pairability checks (protocol sections 3 and 11);
- SHA-256 artifact hashing for the freeze step.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

SUITES = ("workspace", "slack", "travel", "banking")
SUITE_COUNTS = {"workspace": 280, "slack": 126, "travel": 160, "banking": 160}
BENIGN_TOTAL = 97
ATTACK_TOTAL = 629
ALL_TOTAL = 726
STABILITY_PER_SUITE = 40
STABILITY_BENIGN_PER_SUITE = 8
STABILITY_ATTACK_PER_SUITE = 32
SMOKE_BENIGN_PER_SUITE = 1
SMOKE_ATTACK_PER_SUITE = 3
ATTACK_TYPE = "important_instructions"

EVALUATION_DIR = Path(
    "experiments/security-analysis-ablation-and-overhead/evaluation/"
    "strict-atom-representation-attribution"
)


def case_key(
    suite: str,
    user_task_id: str,
    attack_type: str | None = None,
    injection_task_id: str | None = None,
) -> str:
    """Official case key; benign rows use `none` placeholders."""
    return f"{suite}:{user_task_id}:{attack_type or 'none'}:{injection_task_id or 'none'}"


def case_sort_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    """Protocol section 3.1 sort order with empty strings for benign rows."""
    return (
        row["suite"],
        row["user_task_id"],
        row.get("attack_type") or "",
        row.get("injection_task_id") or "",
    )


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def enumerate_official_cases(suites: dict[str, Any]) -> list[dict[str, Any]]:
    """Enumerate all 726 official case keys from AgentDojo API objects.

    `suites` maps suite name to an object exposing `user_tasks` (dict of
    task-id -> task) and `injection_tasks` (dict of injection-id -> task).
    Attack cases are the full user-task x injection-task product; benign
    cases carry no attack fields.
    """
    rows: list[dict[str, Any]] = []
    for suite_name in SUITES:
        suite = suites[suite_name]
        user_tasks = sorted(suite.user_tasks.keys())
        injection_tasks = sorted(suite.injection_tasks.keys())
        for user_task_id in user_tasks:
            rows.append(
                {
                    "case_key": case_key(suite_name, user_task_id),
                    "suite": suite_name,
                    "user_task_id": user_task_id,
                    "mode": "benign",
                    "attack_type": None,
                    "injection_task_id": None,
                    "selection_reason": "all_official_keys_pre_registered",
                }
            )
        for user_task_id in user_tasks:
            for injection_task_id in injection_tasks:
                rows.append(
                    {
                        "case_key": case_key(
                            suite_name, user_task_id, ATTACK_TYPE, injection_task_id
                        ),
                        "suite": suite_name,
                        "user_task_id": user_task_id,
                        "mode": "attack",
                        "attack_type": ATTACK_TYPE,
                        "injection_task_id": injection_task_id,
                        "selection_reason": "all_official_keys_pre_registered",
                    }
                )
    rows.sort(key=case_sort_key)
    return rows


def validate_official_manifest(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Protocol section 11.2 checks: exact counts, uniqueness, no leakage."""
    errors: list[str] = []
    keys = [row["case_key"] for row in rows]
    if len(keys) != ALL_TOTAL:
        errors.append(f"expected {ALL_TOTAL} cases, got {len(keys)}")
    if len(set(keys)) != len(keys):
        duplicates = [key for key, count in Counter(keys).items() if count > 1]
        errors.append(f"duplicate case keys: {duplicates[:5]}")
    benign = [row for row in rows if row["mode"] == "benign"]
    attack = [row for row in rows if row["mode"] == "attack"]
    if len(benign) != BENIGN_TOTAL:
        errors.append(f"expected {BENIGN_TOTAL} benign, got {len(benign)}")
    if len(attack) != ATTACK_TOTAL:
        errors.append(f"expected {ATTACK_TOTAL} attack, got {len(attack)}")
    by_suite = Counter(row["suite"] for row in rows)
    for suite, expected in SUITE_COUNTS.items():
        if by_suite.get(suite) != expected:
            errors.append(f"{suite}: expected {expected}, got {by_suite.get(suite)}")
    for row in rows:
        if row["mode"] == "benign":
            if row.get("attack_type") is not None or row.get("injection_task_id") is not None:
                errors.append(f"benign row has attack fields: {row['case_key']}")
        else:
            if row.get("attack_type") != ATTACK_TYPE:
                errors.append(f"attack row missing attack_type: {row['case_key']}")
            if not row.get("injection_task_id"):
                errors.append(f"attack row missing injection_task_id: {row['case_key']}")
        if row.get("selection_reason") != "all_official_keys_pre_registered":
            errors.append(f"bad selection_reason: {row['case_key']}")
    _check_no_leakage(rows, errors)
    return {"valid": not errors, "n_cases": len(rows), "errors": errors[:20]}


_LEAKAGE_TERMS = (
    "attack_success",
    "expected_decision",
    "gold_atom",
    "violation_reason",
    "mismatch",
    "deny",
    "denied",
    "utility",
    "prior_method",
    "feedback",
)


def _check_no_leakage(rows: list[dict[str, Any]], errors: list[str]) -> None:
    for row in rows:
        serialized = json.dumps(row, sort_keys=True).lower()
        for term in _LEAKAGE_TERMS:
            if term in serialized:
                errors.append(
                    f"leakage term {term!r} in manifest row {row['case_key']}"
                )
                break


def select_stability_subset(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Protocol section 3.2: deterministic 160-case static subset.

    Per suite: 8 benign with the smallest sha256(case_key); 32 attack cases
    stratified by (attack_type, injection_task_id) round-robin, ties broken by
    sha256(case_key). Selection never consults model output.
    """
    selected: list[dict[str, Any]] = []
    for suite in SUITES:
        suite_rows = [row for row in rows if row["suite"] == suite]
        benign = sorted(
            (row for row in suite_rows if row["mode"] == "benign"),
            key=lambda row: sha256_hex(row["case_key"]),
        )
        selected.extend(
            {
                **row,
                "selection_reason": "stability_subset_pre_registered",
            }
            for row in benign[:STABILITY_BENIGN_PER_SUITE]
        )
        attacks = [row for row in suite_rows if row["mode"] == "attack"]
        strata: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in attacks:
            strata.setdefault(
                (row["attack_type"], row["injection_task_id"]), []
            ).append(row)
        ordered_strata = [
            strata[key] for key in sorted(strata, key=lambda k: (k[0], k[1]))
        ]
        for members in ordered_strata:
            members.sort(key=lambda row: sha256_hex(row["case_key"]))
        picked: list[dict[str, Any]] = []
        cursor = 0
        while len(picked) < STABILITY_ATTACK_PER_SUITE:
            progressed = False
            for members in ordered_strata:
                if cursor < len(members) and len(picked) < STABILITY_ATTACK_PER_SUITE:
                    picked.append(members[cursor])
                    progressed = True
            if not progressed:
                break
            cursor += 1
        selected.extend(
            {
                **row,
                "selection_reason": "stability_subset_pre_registered",
            }
            for row in picked
        )
    selected.sort(key=case_sort_key)
    return selected


def validate_stability_subset(rows: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    keys = [row["case_key"] for row in rows]
    if len(rows) != 160 or len(set(keys)) != 160:
        errors.append(f"expected 160 unique stability keys, got {len(keys)}/{len(set(keys))}")
    by_suite = Counter(row["suite"] for row in rows)
    for suite in SUITES:
        if by_suite.get(suite) != STABILITY_PER_SUITE:
            errors.append(f"{suite}: expected {STABILITY_PER_SUITE}, got {by_suite.get(suite)}")
    for suite in SUITES:
        suite_rows = [row for row in rows if row["suite"] == suite]
        n_benign = sum(1 for row in suite_rows if row["mode"] == "benign")
        n_attack = sum(1 for row in suite_rows if row["mode"] == "attack")
        if n_benign != STABILITY_BENIGN_PER_SUITE or n_attack != STABILITY_ATTACK_PER_SUITE:
            errors.append(f"{suite}: expected {STABILITY_BENIGN_PER_SUITE}+{STABILITY_ATTACK_PER_SUITE}, got {n_benign}+{n_attack}")
    return {"valid": not errors, "n_cases": len(rows), "errors": errors[:20]}


def select_smoke_subset(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Protocol section Phase 2: 16 static keys (1 benign + 3 attack per suite).

    Uses sha256(case_key) ordering only; never consults model output.
    """
    selected: list[dict[str, Any]] = []
    for suite in SUITES:
        suite_rows = [row for row in rows if row["suite"] == suite]
        benign = sorted(
            (row for row in suite_rows if row["mode"] == "benign"),
            key=lambda row: sha256_hex(row["case_key"]),
        )
        selected.append(
            {**benign[0], "selection_reason": "smoke_subset_pre_registered"}
        )
        attacks = sorted(
            (row for row in suite_rows if row["mode"] == "attack"),
            key=lambda row: sha256_hex(row["case_key"]),
        )
        selected.extend(
            {**row, "selection_reason": "smoke_subset_pre_registered"}
            for row in attacks[:SMOKE_ATTACK_PER_SUITE]
        )
    selected.sort(key=case_sort_key)
    return selected


def validate_smoke_subset(rows: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    if len(rows) != 16 or len({row["case_key"] for row in rows}) != 16:
        errors.append(f"expected 16 unique smoke keys, got {len(rows)}")
    by_suite = Counter(row["suite"] for row in rows)
    for suite in SUITES:
        suite_rows = [row for row in rows if row["suite"] == suite]
        n_benign = sum(1 for row in suite_rows if row["mode"] == "benign")
        n_attack = sum(1 for row in suite_rows if row["mode"] == "attack")
        if n_benign != SMOKE_BENIGN_PER_SUITE or n_attack != SMOKE_ATTACK_PER_SUITE:
            errors.append(f"{suite}: expected {SMOKE_BENIGN_PER_SUITE}+{SMOKE_ATTACK_PER_SUITE}, got {n_benign}+{n_attack}")
    return {"valid": not errors, "n_cases": len(rows), "errors": errors[:20]}


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True, ensure_ascii=False) for row in rows)
        + "\n",
        encoding="utf-8",
    )


def artifact_hashes(paths: list[Path]) -> dict[str, str]:
    return {path.name: sha256_file(path) for path in paths if path.exists()}
