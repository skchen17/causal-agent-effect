#!/usr/bin/env python3
"""Build explicit authorization-separating collision witnesses from E48/E50."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable


def find_project_root() -> Path:
    starts = (Path.cwd(), Path(__file__).absolute().parent)
    for start in starts:
        for candidate in (start, *start.parents):
            if (
                (candidate / "paper/current-usenix").is_dir()
                and (candidate / "experiments").is_dir()
                and (candidate / "shared/compatibility").is_dir()
            ):
                return candidate
    raise RuntimeError("Could not locate the project root")


ROOT = find_project_root()
sys.path.insert(0, str(ROOT / "code"))

from src.experiments.effect_binding_guard.guards import (  # noqa: E402
    aggregate_views,
    evidence_gated,
    provenance_overlay,
    rule_tuple,
    view_predictions,
)
from src.experiments.effect_binding_guard.schema import (  # noqa: E402
    EffectBindingRow,
)
from src.experiments.tool_effect_fragmentation.phase4_methods import (  # noqa: E402
    parse_authorization_from_task,
)


E48_ROWS = (
    ROOT
    / "shared/compatibility/data/data/e48_effect_binding_unified.jsonl"
)
E48_PREDICTIONS = (
    ROOT
    / "experiments/binding-failure-and-granularity/results/"
    "effect-resource-tuple-guard/tuple-guard-predictions.jsonl"
)
E50_ROWS = (
    ROOT
    / "shared/compatibility/data/data/e50_resource_authorization_stress.jsonl"
)
OUT = (
    ROOT
    / "experiments/binding-failure-and-granularity/results/"
    "authorization-separating-collision-audit"
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def canonical_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def candidate_action(row: dict[str, Any]) -> dict[str, Any]:
    value = row["deployable_input"].get("candidate_action")
    return value if isinstance(value, dict) else {}


def policy_from_e50(row: dict[str, Any]) -> dict[str, Any]:
    policy = row["metadata"]["policy_oracle"]
    return {
        "authorized_effects": sorted(policy.get("authorized_effects") or []),
        "authorized_resources": sorted(
            str(value) for value in policy.get("authorized_resources") or []
        ),
        "commit_allowed": bool(policy.get("commit_allowed")),
        "resource_aliases": dict(
            sorted((policy.get("resource_aliases") or {}).items())
        ),
    }


def policy_from_e48(row: dict[str, Any]) -> dict[str, Any] | None:
    task = str(row["deployable_input"].get("user_task") or "")
    effects, resource = parse_authorization_from_task(task)
    if not effects or not resource:
        return None
    return {
        "authorized_effects": sorted(effects),
        "authorized_resources": [str(resource)],
        "commit_allowed": (
            "Committing external effects is not authorized" not in task
        ),
        "resource_aliases": dict(
            sorted(
                (
                    row["deployable_input"]
                    .get("authorization_context", {})
                    .get("resource_aliases", {})
                    or {}
                ).items()
            )
        ),
    }


def canonical_resource(row: dict[str, Any]) -> str:
    raw = str(row["labels"]["gold_resource"])
    aliases = (
        row["deployable_input"]
        .get("authorization_context", {})
        .get("resource_aliases", {})
        or {}
    )
    return str(aliases.get(raw, raw))


def prediction_representation(
    row: dict[str, Any], prediction: dict[str, Any], *, full: bool
) -> dict[str, Any]:
    representation = {
        "effect": prediction["predicted_effect"],
        "resource": prediction["predicted_resource"],
        "authorization_match": prediction["authorization_match"],
        "provenance_risk": prediction["provenance_risk"],
        "execution_mode": candidate_action(row).get(
            "execution_mode", "unknown"
        ),
    }
    if full:
        metadata = prediction.get("metadata") or {}
        representation.update(
            {
                "decision_vote": metadata.get("decision_vote"),
                "disagreement_rate": metadata.get("disagreement_rate"),
                "tuple_field_disagreement": metadata.get(
                    "tuple_field_disagreement"
                ),
                "fallback_used": metadata.get("fallback_used", False),
            }
        )
    return representation


def representation_builders(
    predictions: dict[tuple[str, str], dict[str, Any]]
) -> dict[str, Callable[[dict[str, Any]], Any]]:
    return {
        "tool_name": lambda row: {
            "tool_name": candidate_action(row).get("tool_name", "unknown")
        },
        "ideal_effect": lambda row: {
            "effect": row["labels"]["gold_effect"]
        },
        "ideal_effect_resource": lambda row: {
            "effect": row["labels"]["gold_effect"],
            "resource": canonical_resource(row),
        },
        "rule_extracted_effect": lambda row: {
            "effect": predictions[
                ("rule_tuple_guard", row["case_id"])
            ]["predicted_effect"]
        },
        "rule_extracted_effect_resource": lambda row: {
            "effect": predictions[
                ("rule_tuple_guard", row["case_id"])
            ]["predicted_effect"],
            "resource": predictions[
                ("rule_tuple_guard", row["case_id"])
            ]["predicted_resource"],
        },
        "rule_decision_representation": lambda row: prediction_representation(
            row,
            predictions[("rule_tuple_guard", row["case_id"])],
            full=False,
        ),
        "full_guard_decision_representation": (
            lambda row: prediction_representation(
                row,
                predictions[("effect_binding_guard_full", row["case_id"])],
                full=True,
            )
        ),
    }


def regenerate_e50_predictions(
    rows: list[dict[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    output: dict[tuple[str, str], dict[str, Any]] = {}
    policy = {
        "allow_threshold": 0.50,
        "deny_threshold": 0.34,
        "max_disagreement": 0.34,
    }
    for raw in rows:
        row = EffectBindingRow.from_dict(raw)
        rule = rule_tuple(row).to_dict()
        views = view_predictions(row, use_provenance=False)
        multi = aggregate_views(
            row,
            views,
            method="multi_view_disagreement_guard",
            **policy,
        )
        gated = evidence_gated(
            row, multi, method="evidence_gated_selective_guard"
        )
        full = provenance_overlay(
            row, gated, method="effect_binding_guard_full"
        ).to_dict()
        output[("rule_tuple_guard", row.case_id)] = rule
        output[("effect_binding_guard_full", row.case_id)] = full
    return output


def load_e48_predictions() -> dict[tuple[str, str], dict[str, Any]]:
    allowed = {"rule_tuple_guard", "effect_binding_guard_full"}
    return {
        (row["method"], row["case_id"]): row
        for row in read_jsonl(E48_PREDICTIONS)
        if row.get("method") in allowed
    }


def observed_errors(
    rows: list[dict[str, Any]],
    predictions: dict[tuple[str, str], dict[str, Any]],
    method: str,
) -> dict[str, int]:
    counts = Counter()
    for row in rows:
        prediction = predictions[(method, row["case_id"])]
        expected = row["labels"]["expected_decision"]
        decision = prediction["decision"]
        if expected == "DENY" and decision == "ALLOW":
            counts["unsafe_allow"] += 1
        elif expected == "ALLOW" and decision == "DENY":
            counts["false_deny"] += 1
        elif decision == "ABSTAIN":
            counts["abstain"] += 1
        else:
            counts["correct_decision"] += 1
    counts["n_rows"] = len(rows)
    return dict(counts)


def audit_dataset(
    *,
    dataset: str,
    rows: list[dict[str, Any]],
    policy_builder: Callable[[dict[str, Any]], dict[str, Any] | None],
    predictions: dict[tuple[str, str], dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    eligible = []
    excluded = []
    for row in rows:
        policy = policy_builder(row)
        if policy is None:
            excluded.append(row["case_id"])
            continue
        item = dict(row)
        item["_policy"] = policy
        eligible.append(item)

    summaries = []
    witnesses = []
    for representation_name, builder in representation_builders(
        predictions
    ).items():
        cells: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in eligible:
            representation = builder(row)
            cells[
                (
                    canonical_json(row["_policy"]),
                    canonical_json(representation),
                )
            ].append(row)

        mixed_cells = []
        lower_bound = 0
        for index, ((policy_key, representation_key), members) in enumerate(
            sorted(cells.items())
        ):
            labels = Counter(
                member["labels"]["expected_decision"] for member in members
            )
            if not labels.get("ALLOW") or not labels.get("DENY"):
                continue
            cell_lower_bound = min(labels["ALLOW"], labels["DENY"])
            lower_bound += cell_lower_bound
            allow = next(
                member
                for member in members
                if member["labels"]["expected_decision"] == "ALLOW"
            )
            deny = next(
                member
                for member in members
                if member["labels"]["expected_decision"] == "DENY"
            )
            witness = {
                "dataset": dataset,
                "representation_name": representation_name,
                "cell_id": f"{dataset}::{representation_name}::{index:04d}",
                "representation": json.loads(representation_key),
                "separating_authority": json.loads(policy_key),
                "n_authorized": labels["ALLOW"],
                "n_unauthorized": labels["DENY"],
                "unit_cost_lower_bound": cell_lower_bound,
                "authorized_case": {
                    "case_id": allow["case_id"],
                    "pair_role": allow["pair_role"],
                    "effect": allow["labels"]["gold_effect"],
                    "resource": allow["labels"]["gold_resource"],
                    "ideal_decision": "ALLOW",
                },
                "unauthorized_case": {
                    "case_id": deny["case_id"],
                    "pair_role": deny["pair_role"],
                    "effect": deny["labels"]["gold_effect"],
                    "resource": deny["labels"]["gold_resource"],
                    "ideal_decision": "DENY",
                },
                "claim_boundary": (
                    "Authorization-separating collision in a transparent "
                    "canonical representation on the controlled dataset."
                ),
            }
            mixed_cells.append(witness)
            witnesses.append(witness)

        summaries.append(
            {
                "dataset": dataset,
                "representation_name": representation_name,
                "n_rows": len(eligible),
                "n_cells": len(cells),
                "n_mixed_authorization_cells": len(mixed_cells),
                "n_rows_in_mixed_cells": sum(
                    row["n_authorized"] + row["n_unauthorized"]
                    for row in mixed_cells
                ),
                "unit_cost_collision_lower_bound": lower_bound,
                "authorization_sufficient_on_observed_rows": not mixed_cells,
            }
        )

    return (
        {
            "dataset": dataset,
            "n_input_rows": len(rows),
            "n_authority_eligible_rows": len(eligible),
            "n_excluded_rows_without_explicit_authority": len(excluded),
            "excluded_case_ids": excluded,
            "representations": summaries,
            "observed_method_errors": {
                method: observed_errors(eligible, predictions, method)
                for method in (
                    "rule_tuple_guard",
                    "effect_binding_guard_full",
                )
            },
        },
        witnesses,
    )


def write_outputs(
    result: dict[str, Any], witnesses: list[dict[str, Any]]
) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "collision-audit-report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (OUT / "authorization-separating-witnesses.jsonl").write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in witnesses
        ),
        encoding="utf-8",
    )

    summary_rows = [
        row
        for dataset in result["datasets"]
        for row in dataset["representations"]
    ]
    with (OUT / "collision-summary.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "dataset",
                "representation_name",
                "n_rows",
                "n_cells",
                "n_mixed_authorization_cells",
                "n_rows_in_mixed_cells",
                "unit_cost_collision_lower_bound",
                "authorization_sufficient_on_observed_rows",
            ],
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    lines = [
        "# Authorization-Separating Representation Collision Audit",
        "",
        f"- Status: `{result['status']}`",
        f"- Witness cells: `{len(witnesses)}`",
        "- Equality is canonical-JSON equality over the declared representation.",
        "- Cells are keyed by both representation and an identical semantic "
        "authority object; changing the authority does not create a collision.",
        "",
        "| Dataset | Representation | Rows | Cells | Mixed cells | "
        "Rows in mixed cells | Lower bound | Sufficient on observed rows |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['dataset']} | `{row['representation_name']}` | "
            f"{row['n_rows']} | {row['n_cells']} | "
            f"{row['n_mixed_authorization_cells']} | "
            f"{row['n_rows_in_mixed_cells']} | "
            f"{row['unit_cost_collision_lower_bound']} | "
            f"{str(row['authorization_sufficient_on_observed_rows']).lower()} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- E48 includes only rows whose authority can be parsed into an "
            "explicit semantic bound; excluded rows remain in the original "
            "benchmark metrics.",
            "- E50 uses the repaired frozen policy oracle for all 240 rows.",
            "- An observed-row sufficiency result is not collision completeness "
            "over the open tool domain.",
            "- Neural-checkpoint internal representations are not inferred from "
            "equal output decisions.",
            "",
        ]
    )
    (OUT / "collision-audit-report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> None:
    e48_rows = read_jsonl(E48_ROWS)
    e50_rows = read_jsonl(E50_ROWS)
    e48_predictions = load_e48_predictions()
    e50_predictions = regenerate_e50_predictions(e50_rows)

    e48_result, e48_witnesses = audit_dataset(
        dataset="E48-explicit-authority-subset",
        rows=e48_rows,
        policy_builder=policy_from_e48,
        predictions=e48_predictions,
    )
    e50_result, e50_witnesses = audit_dataset(
        dataset="E50-repaired-resource-authorization",
        rows=e50_rows,
        policy_builder=policy_from_e50,
        predictions=e50_predictions,
    )
    result = {
        "status": "passed",
        "experiment": "authorization-separating-representation-collision-audit",
        "datasets": [e48_result, e50_result],
        "n_witness_cells": len(e48_witnesses) + len(e50_witnesses),
        "source_artifacts": {
            "e48_rows": str(E48_ROWS.relative_to(ROOT)),
            "e48_predictions": str(E48_PREDICTIONS.relative_to(ROOT)),
            "e50_rows": str(E50_ROWS.relative_to(ROOT)),
            "e50_predictions": "deterministically regenerated by this script",
        },
        "claim_boundary": (
            "Controlled observed-domain collision audit for transparent "
            "representations. It does not expose neural-checkpoint internal "
            "representations or establish open-domain contract soundness."
        ),
    }
    write_outputs(result, e48_witnesses + e50_witnesses)
    print(
        json.dumps(
            {
                "status": result["status"],
                "n_witness_cells": result["n_witness_cells"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
