"""Build a payload-separated AgentDojo attack evaluation dataset.

The generated artifact freezes public benchmark case identities and attack
families. Attack text and injection goals remain in the local AgentDojo
package and are materialized only by the benchmark runner.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
DEFAULT_SOURCE = (
    ROOT
    / "runs/e77_agentdojo_official_v112_full_20260712_075718_e77_full_gpu1"
    / "local-ours_e77_effect_diff_runtime"
)
DEFAULT_E82 = ROOT / "evaluation/e82_adaptive_attacks/case_manifest.jsonl"
DEFAULT_OUTPUT = ROOT / "evaluation/e88_agentdojo_attack_dataset"

EXPECTED_ATTACK_PAIRS = 629
EXPECTED_BENIGN_CONTROLS = 97
EXPECTED_ADAPTIVE_ROWS = 480
EXPECTED_SMOKE_ROWS = 80


ATTACK_FAMILIES: tuple[dict[str, Any], ...] = (
    {
        "family_id": "S1",
        "agentdojo_attack_name": "ignore_previous",
        "family": "instruction_priority_override",
        "source": "AgentDojo public attack registry",
        "fixed_template": True,
        "tool_sequence_disclosed": False,
    },
    {
        "family_id": "S2",
        "agentdojo_attack_name": "injecagent",
        "family": "high_salience_task_redirect",
        "source": "AgentDojo public InjecAgent-style attack registry entry",
        "fixed_template": True,
        "tool_sequence_disclosed": False,
    },
    {
        "family_id": "S3",
        "agentdojo_attack_name": "important_instructions",
        "family": "impersonated_important_message",
        "source": "AgentDojo public attack registry",
        "fixed_template": True,
        "tool_sequence_disclosed": False,
    },
    {
        "family_id": "S4",
        "agentdojo_attack_name": "tool_knowledge",
        "family": "tool_sequence_guided_redirect",
        "source": "AgentDojo public attack registry",
        "fixed_template": True,
        "tool_sequence_disclosed": True,
    },
)


def _sha256_bytes(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: expected JSON object")
            rows.append(row)
    return rows


def _source_inventory(source: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    attacks: list[dict[str, str]] = []
    benign: list[dict[str, str]] = []
    for path in sorted(source.rglob("*.json")):
        parts = path.relative_to(source).parts
        if len(parts) != 4:
            continue
        suite, task_id, attack_name, filename = parts
        leaf_id = Path(filename).stem
        if task_id.startswith("user_task_") and attack_name == "important_instructions" and leaf_id.startswith(
            "injection_task_"
        ):
            base_key = f"{suite}/{task_id}/{leaf_id}"
            attacks.append(
                {
                    "suite": suite,
                    "user_task_id": task_id,
                    "injection_task_id": leaf_id,
                    "base_case_key": base_key,
                    "base_case_key_sha256": _sha256_text(base_key),
                    "source_log_sha256": _sha256_bytes(path),
                }
            )
        elif task_id.startswith("user_task_") and attack_name == "none" and leaf_id == "none":
            base_key = f"{suite}/{task_id}/none"
            benign.append(
                {
                    "suite": suite,
                    "user_task_id": task_id,
                    "base_case_key": base_key,
                    "base_case_key_sha256": _sha256_text(base_key),
                    "source_log_sha256": _sha256_bytes(path),
                }
            )
    attacks.sort(key=lambda row: row["base_case_key"])
    benign.sort(key=lambda row: row["base_case_key"])
    return attacks, benign


def _group_splits(base_rows: Iterable[dict[str, str]], development_fraction: float = 0.2) -> dict[str, str]:
    groups_by_suite: dict[str, set[str]] = defaultdict(set)
    for row in base_rows:
        groups_by_suite[row["suite"]].add(row["injection_task_id"])

    assignment: dict[str, str] = {}
    for suite, groups in sorted(groups_by_suite.items()):
        ranked = sorted(groups, key=lambda value: (_sha256_text(f"{suite}/{value}"), value))
        n_development = max(1, round(len(ranked) * development_fraction))
        development = set(ranked[:n_development])
        for injection_task_id in ranked:
            assignment[f"{suite}/{injection_task_id}"] = (
                "adaptive_development" if injection_task_id in development else "adaptive_locked_test"
            )
    return assignment


def _build_smoke_rows(static_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected_base_keys: set[tuple[str, str, str]] = set()
    suites = sorted({row["suite"] for row in static_rows})
    for suite in suites:
        development_rows = [
            row
            for row in static_rows
            if row["suite"] == suite and row["adaptive_split"] == "adaptive_development"
        ]
        development_goals = sorted(
            {row["injection_task_id"] for row in development_rows},
            key=lambda value: (_sha256_text(f"{suite}/{value}"), value),
        )
        if not development_goals:
            raise RuntimeError(f"suite {suite} has no adaptive-development injection task")
        injection_task_id = development_goals[0]
        user_tasks = sorted(
            {
                row["user_task_id"]
                for row in development_rows
                if row["injection_task_id"] == injection_task_id
            },
            key=lambda value: (_sha256_text(f"{suite}/{injection_task_id}/{value}"), value),
        )[:5]
        if len(user_tasks) != 5:
            raise RuntimeError(f"suite {suite} development goal has only {len(user_tasks)} user tasks")
        selected_base_keys.update((suite, user_task_id, injection_task_id) for user_task_id in user_tasks)

    smoke_rows = [
        {**row, "tier": "diagnostic_smoke", "paper_result_eligible": False}
        for row in static_rows
        if (row["suite"], row["user_task_id"], row["injection_task_id"]) in selected_base_keys
    ]
    smoke_rows.sort(key=lambda row: (row["suite"], row["agentdojo_attack_name"], row["user_task_id"]))
    if len(smoke_rows) != EXPECTED_SMOKE_ROWS:
        raise RuntimeError(f"expected {EXPECTED_SMOKE_ROWS} smoke rows, found {len(smoke_rows)}")
    return smoke_rows


def build_dataset(source: Path = DEFAULT_SOURCE, e82_manifest: Path = DEFAULT_E82) -> dict[str, Any]:
    base_attacks, base_benign = _source_inventory(source)
    if len(base_attacks) != EXPECTED_ATTACK_PAIRS:
        raise RuntimeError(f"expected {EXPECTED_ATTACK_PAIRS} attack pairs, found {len(base_attacks)}")
    if len(base_benign) != EXPECTED_BENIGN_CONTROLS:
        raise RuntimeError(f"expected {EXPECTED_BENIGN_CONTROLS} benign controls, found {len(base_benign)}")

    split_assignment = _group_splits(base_attacks)
    static_rows: list[dict[str, Any]] = []
    for base in base_attacks:
        split = split_assignment[f"{base['suite']}/{base['injection_task_id']}"]
        for family in ATTACK_FAMILIES:
            case_key = f"{base['base_case_key']}/{family['agentdojo_attack_name']}"
            static_rows.append(
                {
                    "case_id": f"E88-{family['family_id']}-{_sha256_text(case_key)[:16]}",
                    "tier": "fixed_static",
                    "suite": base["suite"],
                    "user_task_id": base["user_task_id"],
                    "injection_task_id": base["injection_task_id"],
                    "attack_family_id": family["family_id"],
                    "agentdojo_attack_name": family["agentdojo_attack_name"],
                    "base_case_key_sha256": base["base_case_key_sha256"],
                    "source_log_sha256": base["source_log_sha256"],
                    "adaptive_split": split,
                    "fixed_full_benchmark_member": True,
                    "payload_materialization": "local_agentdojo_public_attack_registry",
                    "contains_raw_attack_text": False,
                    "environment_evaluator": "official_agentdojo_injection_task_validator",
                    "no_external_side_effects": True,
                }
            )

    benign_rows = [
        {
            "case_id": f"E88-C-{row['base_case_key_sha256'][:16]}",
            "tier": "benign_control",
            "suite": row["suite"],
            "user_task_id": row["user_task_id"],
            "base_case_key_sha256": row["base_case_key_sha256"],
            "source_log_sha256": row["source_log_sha256"],
            "payload_materialization": "none",
            "contains_raw_attack_text": False,
            "environment_evaluator": "official_agentdojo_user_task_validator",
            "no_external_side_effects": True,
        }
        for row in base_benign
    ]

    adaptive_source = _read_jsonl(e82_manifest)
    if len(adaptive_source) != EXPECTED_ADAPTIVE_ROWS:
        raise RuntimeError(f"expected {EXPECTED_ADAPTIVE_ROWS} E82 rows, found {len(adaptive_source)}")
    adaptive_rows: list[dict[str, Any]] = []
    for row in adaptive_source:
        split = split_assignment.get(f"{row['suite']}/{row['injection_task_id']}")
        if split is None:
            raise RuntimeError(f"E82 row references unknown group: {row['suite']}/{row['injection_task_id']}")
        adaptive_rows.append(
            {
                "case_id": row["case_id"],
                "tier": "bounded_adaptive",
                "attack_id": row["attack_id"],
                "suite": row["suite"],
                "base_case_key_sha256": row["official_case_key_sha256"],
                "source_log_sha256": row["frozen_source_log_sha256"],
                "adaptive_split": split,
                "search_budget": row["search_budget"],
                "attacker_observes": row["attacker_observes"],
                "environment_evaluator": row["environment_evaluator"],
                "success_predicate": row["success_predicate"],
                "contains_raw_attack_text": False,
                "no_external_side_effects": True,
                "status": row["status"],
            }
        )

    smoke_rows = _build_smoke_rows(static_rows)
    split_counts = Counter(row["adaptive_split"] for row in static_rows)
    group_counts = Counter(split_assignment.values())
    manifest = {
        "experiment": "E88",
        "artifact_type": "payload_separated_agentdojo_attack_dataset",
        "agentdojo_version": "v1.1.2",
        "static_attack_pairs": len(static_rows),
        "base_attack_pairs": len(base_attacks),
        "benign_controls": len(benign_rows),
        "adaptive_strategy_case_pairs": len(adaptive_rows),
        "diagnostic_smoke_cases": len(smoke_rows),
        "attack_families": len(ATTACK_FAMILIES),
        "suite_counts_base": dict(sorted(Counter(row["suite"] for row in base_attacks).items())),
        "static_family_counts": dict(
            sorted(Counter(row["agentdojo_attack_name"] for row in static_rows).items())
        ),
        "static_split_row_counts": dict(sorted(split_counts.items())),
        "adaptive_group_counts": dict(sorted(group_counts.items())),
        "contains_raw_attack_text": False,
        "payload_resolution": (
            "Fixed attack text and injection goals are resolved from the pinned local AgentDojo public registry at execution."
        ),
        "scoring": "Official environment validators; no LLM security judge.",
        "intended_use": "Sandboxed research evaluation of indirect-instruction robustness and pre-commit mediation.",
        "prohibited_use": [
            "real external side effects",
            "real credentials or personal data",
            "API safety-classifier evasion",
            "obfuscated or encoded payload delivery",
        ],
        "claim_boundary": (
            "E88 is a benchmark manifest over public AgentDojo tasks and attacks. It is not a corpus of deployed attacks, "
            "does not contain raw injection text, and does not establish production safety."
        ),
    }
    return {
        "manifest": manifest,
        "attack_families": list(ATTACK_FAMILIES),
        "static_rows": static_rows,
        "benign_rows": benign_rows,
        "adaptive_rows": adaptive_rows,
        "smoke_rows": smoke_rows,
        "split_assignment": split_assignment,
    }


def validate_dataset(dataset: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    manifest = dataset["manifest"]
    static_rows = dataset["static_rows"]
    benign_rows = dataset["benign_rows"]
    adaptive_rows = dataset["adaptive_rows"]
    smoke_rows = dataset["smoke_rows"]

    expected_static = EXPECTED_ATTACK_PAIRS * len(ATTACK_FAMILIES)
    if len(static_rows) != expected_static:
        errors.append(f"static row count: expected {expected_static}, found {len(static_rows)}")
    if len(benign_rows) != EXPECTED_BENIGN_CONTROLS:
        errors.append(f"benign row count: expected {EXPECTED_BENIGN_CONTROLS}, found {len(benign_rows)}")
    if len(adaptive_rows) != EXPECTED_ADAPTIVE_ROWS:
        errors.append(f"adaptive row count: expected {EXPECTED_ADAPTIVE_ROWS}, found {len(adaptive_rows)}")
    if len(smoke_rows) != EXPECTED_SMOKE_ROWS:
        errors.append(f"smoke row count: expected {EXPECTED_SMOKE_ROWS}, found {len(smoke_rows)}")

    all_rows = static_rows + benign_rows + adaptive_rows
    ids = [row["case_id"] for row in all_rows]
    if len(ids) != len(set(ids)):
        errors.append("case IDs are not globally unique")
    forbidden_keys = {"raw_attack_text", "attack_payload", "injection_goal", "expected_decision", "gold_atoms"}
    for row in all_rows:
        present = forbidden_keys.intersection(row)
        if present:
            errors.append(f"{row['case_id']}: forbidden fields {sorted(present)}")
        if row.get("contains_raw_attack_text") is not False:
            errors.append(f"{row['case_id']}: raw attack text flag must be false")
        if row.get("no_external_side_effects") is not True:
            errors.append(f"{row['case_id']}: external side effects must be disabled")
        for hash_field in ("base_case_key_sha256", "source_log_sha256"):
            value = row.get(hash_field)
            if not isinstance(value, str) or len(value) != 64:
                errors.append(f"{row['case_id']}: invalid {hash_field}")

    family_counts = Counter(row["agentdojo_attack_name"] for row in static_rows)
    for family in ATTACK_FAMILIES:
        name = family["agentdojo_attack_name"]
        if family_counts[name] != EXPECTED_ATTACK_PAIRS:
            errors.append(f"{name}: expected {EXPECTED_ATTACK_PAIRS}, found {family_counts[name]}")

    group_splits: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in static_rows:
        group_splits[(row["suite"], row["injection_task_id"])].add(row["adaptive_split"])
    if any(len(splits) != 1 for splits in group_splits.values()):
        errors.append("an injection-task group crosses adaptive development and locked-test splits")
    observed_splits = {next(iter(splits)) for splits in group_splits.values()}
    if observed_splits != {"adaptive_development", "adaptive_locked_test"}:
        errors.append(f"expected both adaptive splits, found {sorted(observed_splits)}")

    if manifest.get("contains_raw_attack_text") is not False:
        errors.append("dataset manifest must declare raw attack text absent")
    if "API safety-classifier evasion" not in manifest.get("prohibited_use", []):
        errors.append("dataset policy must prohibit safety-classifier evasion")
    static_ids = {row["case_id"] for row in static_rows}
    if any(row["case_id"] not in static_ids for row in smoke_rows):
        errors.append("smoke rows must be a strict subset of fixed static rows")
    if any(row.get("adaptive_split") != "adaptive_development" for row in smoke_rows):
        errors.append("smoke rows may not open adaptive locked-test groups")
    smoke_family_counts = Counter(row["agentdojo_attack_name"] for row in smoke_rows)
    if any(smoke_family_counts[family["agentdojo_attack_name"]] != 20 for family in ATTACK_FAMILIES):
        errors.append(f"smoke families must each contain 20 cases: {dict(smoke_family_counts)}")

    return {
        "experiment": "E88",
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "n_errors": len(errors),
        "n_static_rows": len(static_rows),
        "n_benign_rows": len(benign_rows),
        "n_adaptive_rows": len(adaptive_rows),
        "n_smoke_rows": len(smoke_rows),
        "all_payload_separated": all(row.get("contains_raw_attack_text") is False for row in all_rows),
        "all_environment_scored": all(bool(row.get("environment_evaluator")) for row in all_rows),
        "all_no_external_side_effects": all(row.get("no_external_side_effects") is True for row in all_rows),
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_dataset(dataset: dict[str, Any], output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    validation = validate_dataset(dataset)
    _write_json(output / "dataset_manifest.json", dataset["manifest"])
    _write_json(output / "attack_family_manifest.json", {"families": dataset["attack_families"]})
    _write_jsonl(output / "static_case_manifest.jsonl", dataset["static_rows"])
    _write_jsonl(output / "benign_control_manifest.jsonl", dataset["benign_rows"])
    _write_jsonl(output / "adaptive_case_index.jsonl", dataset["adaptive_rows"])
    _write_jsonl(output / "smoke_case_manifest.jsonl", dataset["smoke_rows"])
    _write_json(
        output / "split_manifest.json",
        {
            "unit": "suite/injection_task_id",
            "purpose": "Development may use only adaptive_development groups; final adaptive reporting uses locked test groups.",
            "assignment": dataset["split_assignment"],
            "static_fixed_suite": "All 2,516 fixed public-template cases are reported without prompt tuning.",
        },
    )
    _write_json(output / "validation_report.json", validation)
    if validation["status"] != "passed":
        raise RuntimeError(f"E88 validation failed: {validation['errors']}")
    return validation
