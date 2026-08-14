#!/usr/bin/env python3
"""Run the pre-registered ToolSandbox held-out effect-binding validation."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import itertools
import json
import sys
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable


def find_root(path: Path) -> Path:
    for candidate in path.resolve().parents:
        if (candidate / "experiments").is_dir() and (candidate / "paper").is_dir():
            return candidate
    raise RuntimeError("could not locate consolidated package root")


ROOT = find_root(Path(__file__))
TOOL_SANDBOX = (
    ROOT
    / "experiments/long-horizon-transfer/runs/"
    "long-horizon-cross-environment-transfer/external-benchmarks/ToolSandbox"
)
EVALUATION = (
    ROOT
    / "experiments/human-authority-and-causal-validation/evaluation/"
    "heldout-toolsandbox-effect-binding-validation"
)
RESULTS = (
    ROOT
    / "experiments/human-authority-and-causal-validation/results/"
    "heldout-toolsandbox-effect-binding-validation"
)
PREREGISTRATION = EVALUATION / "preregistration.json"
CONTEXTS = EVALUATION / "heldout-contexts.jsonl"
WITNESSES = RESULTS / "authorization-separating-witnesses.jsonl"
SUMMARY_CSV = RESULTS / "representation-summary.csv"
REPORT_JSON = RESULTS / "heldout-validation-report.json"
REPORT_MD = RESULTS / "heldout-validation-report.md"

SEED_CONTACTS = {
    "seed_contact_alpha": {
        "person_id": str(
            uuid.uuid5(uuid.NAMESPACE_URL, "effect-binding-heldout-alpha")
        ),
        "name": "Alpha Heldout",
        "phone_number": "+12025550201",
        "relationship": "friend",
        "is_self": False,
    },
    "seed_contact_beta": {
        "person_id": str(
            uuid.uuid5(uuid.NAMESPACE_URL, "effect-binding-heldout-beta")
        ),
        "name": "Beta Heldout",
        "phone_number": "+12025550202",
        "relationship": "coworker",
        "is_self": False,
    },
}
SETTING_FIELDS = (
    "cellular",
    "wifi",
    "location_service",
    "low_battery_mode",
)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object in {path}")
    return value


def load_preregistration_module() -> Any:
    path = ROOT / "scripts/preregister_toolsandbox_heldout_validation.py"
    spec = importlib.util.spec_from_file_location("toolsandbox_preregistration", path)
    if not spec or not spec.loader:
        raise RuntimeError("cannot load preregistration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_preregistration(payload: dict[str, Any]) -> list[str]:
    if payload["status"] != "frozen_before_contract_evaluation":
        raise ValueError("held-out protocol was not frozen before evaluation")
    regenerated = load_preregistration_module().build_manifest()
    errors = []
    if payload["source"]["revision"] != regenerated["source"]["revision"]:
        errors.append("source revision mismatch")
    frozen = {row["tool_name"]: row for row in payload["frozen_tools"]}
    current = {row["tool_name"]: row for row in regenerated["frozen_tools"]}
    for name, row in frozen.items():
        if name not in current:
            errors.append(f"missing frozen tool: {name}")
            continue
        for key in ("source_file_sha256", "function_source_sha256"):
            if row[key] != current[name][key]:
                errors.append(f"{name} {key} mismatch")
    return errors


def make_atom(
    *,
    effect: str,
    operation: str,
    resource_id: str,
    resource_type: str,
    target_principal: str | None = None,
    qualifiers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "effect": effect,
        "operation": operation,
        "resource_id": resource_id,
        "resource_type": resource_type,
        "target_principal": target_principal,
        "visibility": "local_private",
        "commit_mode": "commit",
        "provenance_source": "authenticated_tool_call",
        "control_source": "agent_plan",
        "qualifiers": qualifiers or {},
    }


def normalize_atoms(atoms: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(atoms, key=canonical)


def current_rows(context: Any, namespace: Any) -> list[dict[str, Any]]:
    rows = context.get_database(namespace=namespace).to_dicts()
    return [
        {key: value for key, value in row.items() if key != "sandbox_message_index"}
        for row in rows
    ]


def source_effect_oracle(
    tool_name: str,
    before: dict[str, list[dict[str, Any]]],
    after: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Reconstruct committed effects only from before/after sandbox state."""

    if tool_name in {"add_contact", "remove_contact"}:
        before_rows = {row["person_id"]: row for row in before["contact"]}
        after_rows = {row["person_id"]: row for row in after["contact"]}
        if tool_name == "add_contact":
            added = [after_rows[key] for key in after_rows.keys() - before_rows.keys()]
            return normalize_atoms(
                make_atom(
                    effect="contact_created",
                    operation="create",
                    resource_id="generated:new_contact",
                    resource_type="contact",
                    target_principal=row["phone_number"],
                    qualifiers={
                        "name": row["name"],
                        "phone_number": row["phone_number"],
                        "relationship": row["relationship"],
                        "is_self": row["is_self"],
                    },
                )
                for row in added
            )
        removed = [before_rows[key] for key in before_rows.keys() - after_rows.keys()]
        return normalize_atoms(
            make_atom(
                effect="contact_removed",
                operation="delete",
                resource_id=row["person_id"],
                resource_type="contact",
                target_principal=row["phone_number"],
                qualifiers={"removed_contact_identity": row["person_id"]},
            )
            for row in removed
        )

    if tool_name == "add_reminder":
        before_rows = {row["reminder_id"]: row for row in before["reminder"]}
        after_rows = {row["reminder_id"]: row for row in after["reminder"]}
        added = [after_rows[key] for key in after_rows.keys() - before_rows.keys()]
        return normalize_atoms(
            make_atom(
                effect="reminder_created",
                operation="create",
                resource_id="generated:new_reminder",
                resource_type="reminder",
                qualifiers={
                    "content": row["content"],
                    "reminder_timestamp": row["reminder_timestamp"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                },
            )
            for row in added
        )

    if tool_name in {
        "set_location_service_status",
        "set_low_battery_mode_status",
    }:
        before_row = before["setting"][0]
        after_row = after["setting"][0]
        atoms = []
        for field in SETTING_FIELDS:
            if before_row[field] != after_row[field]:
                atoms.append(
                    make_atom(
                        effect="setting_changed",
                        operation="set",
                        resource_id=field,
                        resource_type="device_setting",
                        qualifiers={
                            "new_boolean_value": after_row[field],
                            "dependent_setting": (
                                field
                                if tool_name == "set_low_battery_mode_status"
                                and field != "low_battery_mode"
                                else None
                            ),
                            "compound_expansion": tool_name
                            == "set_low_battery_mode_status",
                        },
                    )
                )
        return normalize_atoms(atoms)
    raise ValueError(f"unsupported source oracle tool: {tool_name}")


def typed_contract_atoms(
    tool_name: str,
    arguments: dict[str, Any],
    pre_state: dict[str, Any],
) -> list[dict[str, Any]]:
    """Instantiate the frozen candidate contract from call and pre-state only."""

    if tool_name == "add_contact":
        return [
            make_atom(
                effect="contact_created",
                operation="create",
                resource_id="generated:new_contact",
                resource_type="contact",
                target_principal=arguments["phone_number"],
                qualifiers={
                    "name": arguments["name"],
                    "phone_number": arguments["phone_number"],
                    "relationship": arguments["relationship"],
                    "is_self": arguments.get("is_self", False),
                },
            )
        ]
    if tool_name == "remove_contact":
        contact = next(
            (
                row
                for row in pre_state["contact"]
                if row["person_id"] == arguments["person_id"]
            ),
            None,
        )
        if contact is None:
            return []
        return [
            make_atom(
                effect="contact_removed",
                operation="delete",
                resource_id=contact["person_id"],
                resource_type="contact",
                target_principal=contact["phone_number"],
                qualifiers={"removed_contact_identity": contact["person_id"]},
            )
        ]
    if tool_name == "add_reminder":
        return [
            make_atom(
                effect="reminder_created",
                operation="create",
                resource_id="generated:new_reminder",
                resource_type="reminder",
                qualifiers={
                    "content": arguments["content"],
                    "reminder_timestamp": arguments["reminder_timestamp"],
                    "latitude": arguments.get("latitude"),
                    "longitude": arguments.get("longitude"),
                },
            )
        ]
    setting = pre_state["setting"][0]
    requested = arguments["on"]
    if tool_name == "set_location_service_status":
        if setting["location_service"] == requested:
            return []
        if requested and setting["low_battery_mode"]:
            return []
        return [
            make_atom(
                effect="setting_changed",
                operation="set",
                resource_id="location_service",
                resource_type="device_setting",
                qualifiers={
                    "new_boolean_value": requested,
                    "dependent_setting": None,
                    "compound_expansion": False,
                },
            )
        ]
    if tool_name == "set_low_battery_mode_status":
        if setting["low_battery_mode"] == requested:
            return []
        fields = ["low_battery_mode"]
        if requested:
            fields.extend(field for field in SETTING_FIELDS[:3] if setting[field])
        return normalize_atoms(
            make_atom(
                effect="setting_changed",
                operation="set",
                resource_id=field,
                resource_type="device_setting",
                qualifiers={
                    "new_boolean_value": requested if field == "low_battery_mode" else False,
                    "dependent_setting": (
                        field if field != "low_battery_mode" else None
                    ),
                    "compound_expansion": True,
                },
            )
            for field in fields
        )
    raise ValueError(f"unsupported typed contract tool: {tool_name}")


def common_contract_atoms(typed_atoms: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return normalize_atoms(
        {key: value for key, value in atom.items() if key != "qualifiers"}
        for atom in typed_atoms
    )


def setting_state(name: str) -> dict[str, bool]:
    states = {
        "location_on_low_battery_off": {
            "cellular": True,
            "wifi": True,
            "location_service": True,
            "low_battery_mode": False,
        },
        "location_off_low_battery_off": {
            "cellular": True,
            "wifi": True,
            "location_service": False,
            "low_battery_mode": False,
        },
        "location_off_low_battery_on": {
            "cellular": False,
            "wifi": False,
            "location_service": False,
            "low_battery_mode": True,
        },
        "all_services_on_low_battery_off": {
            "cellular": True,
            "wifi": True,
            "location_service": True,
            "low_battery_mode": False,
        },
        "cellular_off_low_battery_off": {
            "cellular": False,
            "wifi": True,
            "location_service": True,
            "low_battery_mode": False,
        },
        "wifi_off_low_battery_off": {
            "cellular": True,
            "wifi": False,
            "location_service": True,
            "low_battery_mode": False,
        },
        "all_services_off_low_battery_on": {
            "cellular": False,
            "wifi": False,
            "location_service": False,
            "low_battery_mode": True,
        },
    }
    return states[name]


def enumerate_context_specs(prereg: dict[str, Any]) -> list[dict[str, Any]]:
    frozen = {row["tool_name"]: row for row in prereg["frozen_tools"]}
    rows: list[dict[str, Any]] = []

    spec = frozen["add_contact"]
    domain = spec["call_domain"]
    for values in itertools.product(
        domain["name"],
        domain["phone_number"],
        domain["relationship"],
        domain["is_self"],
    ):
        arguments = dict(
            zip(("name", "phone_number", "relationship", "is_self"), values)
        )
        rows.append(
            {
                "tool_name": "add_contact",
                "state_name": "fresh_default_context",
                "arguments": arguments,
            }
        )

    for selector in frozen["remove_contact"]["call_domain"]["person_id_selector"]:
        rows.append(
            {
                "tool_name": "remove_contact",
                "state_name": "two_frozen_seed_contacts",
                "arguments": {"person_id": SEED_CONTACTS[selector]["person_id"]},
                "selector": selector,
            }
        )

    domain = frozen["add_reminder"]["call_domain"]
    for content, timestamp, location in itertools.product(
        domain["content"],
        domain["reminder_timestamp"],
        domain["location"],
    ):
        arguments: dict[str, Any] = {
            "content": content,
            "reminder_timestamp": timestamp,
        }
        if location is not None:
            arguments["latitude"], arguments["longitude"] = location
        rows.append(
            {
                "tool_name": "add_reminder",
                "state_name": "fresh_default_context",
                "arguments": arguments,
            }
        )

    for tool_name in (
        "set_location_service_status",
        "set_low_battery_mode_status",
    ):
        spec = frozen[tool_name]
        for state_name, requested in itertools.product(
            spec["state_domain"],
            spec["call_domain"]["on"],
        ):
            rows.append(
                {
                    "tool_name": tool_name,
                    "state_name": state_name,
                    "arguments": {"on": requested},
                }
            )

    for index, row in enumerate(rows):
        row["case_id"] = f"toolsandbox-heldout-{index:03d}"
    return rows


def prepare_context(spec: dict[str, Any]) -> Any:
    import polars as pl
    from tool_sandbox.common.execution_context import DatabaseNamespace, ExecutionContext

    context = ExecutionContext()
    if spec["tool_name"] == "remove_contact":
        context.add_to_database(
            namespace=DatabaseNamespace.CONTACT,
            rows=list(SEED_CONTACTS.values()),
        )
    if spec["tool_name"].startswith("set_"):
        state = setting_state(spec["state_name"])
        context.update_database(
            namespace=DatabaseNamespace.SETTING,
            dataframe=context.get_database(
                namespace=DatabaseNamespace.SETTING
            ).with_columns(
                [pl.lit(value).alias(field) for field, value in state.items()]
            ),
        )
    return context


def snapshot(context: Any) -> dict[str, list[dict[str, Any]]]:
    from tool_sandbox.common.execution_context import DatabaseNamespace

    return {
        "contact": current_rows(context, DatabaseNamespace.CONTACT),
        "reminder": current_rows(context, DatabaseNamespace.REMINDER),
        "setting": current_rows(context, DatabaseNamespace.SETTING),
    }


def execute_context(spec: dict[str, Any]) -> dict[str, Any]:
    from tool_sandbox.common.execution_context import new_context
    from tool_sandbox.tools.contact import add_contact, remove_contact
    from tool_sandbox.tools.reminder import add_reminder
    from tool_sandbox.tools.setting import (
        set_location_service_status,
        set_low_battery_mode_status,
    )

    functions: dict[str, Callable[..., Any]] = {
        "add_contact": add_contact,
        "remove_contact": remove_contact,
        "add_reminder": add_reminder,
        "set_location_service_status": set_location_service_status,
        "set_low_battery_mode_status": set_low_battery_mode_status,
    }
    context = prepare_context(spec)
    error: dict[str, str] | None = None
    with new_context(context):
        before = snapshot(context)
        try:
            functions[spec["tool_name"]](**spec["arguments"])
        except Exception as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
        after = snapshot(context)
    source_atoms = source_effect_oracle(spec["tool_name"], before, after)
    typed_atoms = normalize_atoms(
        typed_contract_atoms(spec["tool_name"], spec["arguments"], before)
    )
    return {
        **spec,
        "execution_error": error,
        "source_effect_atoms": source_atoms,
        "representations": {
            "tool_name": spec["tool_name"],
            "common_fields": common_contract_atoms(typed_atoms),
            "typed_contract": typed_atoms,
            "source_full_effect": source_atoms,
        },
        "typed_relation_agreement": canonical(typed_atoms) == canonical(source_atoms),
    }


def representation_audit(
    rows: list[dict[str, Any]],
    representation: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        cells[canonical(row["representations"][representation])].append(row)

    collision_cells = 0
    separating_pairs = 0
    witnesses = []
    for rep_key, members in cells.items():
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for member in members:
            groups[canonical(member["source_effect_atoms"])].append(member)
        if len(groups) <= 1:
            continue
        collision_cells += 1
        group_rows = list(groups.values())
        separating_pairs += sum(
            len(left) * len(right)
            for left, right in itertools.combinations(group_rows, 2)
        )
        witnesses.append(
            {
                "representation": representation,
                "representation_key": rep_key,
                "case_ids": [row["case_id"] for row in members],
                "n_source_effect_sets": len(groups),
                "source_effect_sets": [json.loads(key) for key in groups],
            }
        )

    source_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        source_groups[canonical(row["source_effect_atoms"])].append(row)
    overpartition_pairs = 0
    for members in source_groups.values():
        rep_groups: dict[str, int] = defaultdict(int)
        for member in members:
            rep_groups[canonical(member["representations"][representation])] += 1
        if len(rep_groups) > 1:
            values = list(rep_groups.values())
            overpartition_pairs += sum(
                left * right for left, right in itertools.combinations(values, 2)
            )

    summary = {
        "representation": representation,
        "n_cells": len(cells),
        "authorization_collision_cells": collision_cells,
        "authorization_separating_pairs": separating_pairs,
        "overpartition_pairs": overpartition_pairs,
        "finite_collision_complete": collision_cells == 0,
        "finite_partition_exact": collision_cells == 0
        and overpartition_pairs == 0,
    }
    return summary, witnesses


def write_outputs(
    prereg: dict[str, Any],
    rows: list[dict[str, Any]],
    source_errors: list[str],
) -> dict[str, Any]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    EVALUATION.mkdir(parents=True, exist_ok=True)
    CONTEXTS.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )

    summaries = []
    witnesses = []
    for representation in prereg["representations"]:
        summary, current = representation_audit(rows, representation)
        summaries.append(summary)
        witnesses.extend(current)
    WITNESSES.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in witnesses),
        encoding="utf-8",
    )
    with SUMMARY_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)

    typed = next(row for row in summaries if row["representation"] == "typed_contract")
    typed_agreement = sum(row["typed_relation_agreement"] for row in rows)
    status = (
        "passed"
        if not source_errors
        and typed["finite_partition_exact"]
        and typed_agreement == len(rows)
        else "failed"
    )
    by_tool: dict[str, dict[str, int]] = {}
    for tool_name in sorted({row["tool_name"] for row in rows}):
        selected = [row for row in rows if row["tool_name"] == tool_name]
        by_tool[tool_name] = {
            "n_contexts": len(selected),
            "n_execution_errors": sum(
                row["execution_error"] is not None for row in selected
            ),
            "typed_relation_agreement": sum(
                row["typed_relation_agreement"] for row in selected
            ),
        }
    report = {
        "experiment": "heldout_toolsandbox_effect_binding_validation",
        "status": status,
        "source_revision": prereg["source"]["revision"],
        "n_tools": len(by_tool),
        "n_contexts": len(rows),
        "n_execution_errors_retained": sum(
            row["execution_error"] is not None for row in rows
        ),
        "source_verification_errors": source_errors,
        "typed_relation_agreement": {
            "successes": typed_agreement,
            "total": len(rows),
            "rate": typed_agreement / len(rows),
        },
        "by_tool": by_tool,
        "representations": summaries,
        "n_witness_cells": len(witnesses),
        "preregistration": str(PREREGISTRATION.relative_to(ROOT)),
        "claim_boundary": (
            "This is a pre-registered, source-hash-bound validation on five "
            "public ToolSandbox tools held out from the AgentDojo contract "
            "design. It uses AI artifact review, not independent human review, "
            "and establishes only finite-domain adequacy for the frozen calls, "
            "state variants, source oracle, and authority family."
        ),
    }
    REPORT_JSON.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# ToolSandbox Held-Out Effect-Binding Validation",
        "",
        f"Status: `{status}`.",
        "",
        f"- Frozen tools: `{report['n_tools']}`.",
        f"- Executed contexts: `{report['n_contexts']}`.",
        f"- Retained execution errors: `{report['n_execution_errors_retained']}`.",
        (
            "- Typed contract/source relation agreement: "
            f"`{typed_agreement}/{len(rows)}`."
        ),
        "",
        "| Representation | Cells | Collision cells | Separating pairs | Overpartition pairs | Exact |",
        "|---|---:|---:|---:|---:|:---:|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['representation']} | {row['n_cells']} | "
            f"{row['authorization_collision_cells']} | "
            f"{row['authorization_separating_pairs']} | "
            f"{row['overpartition_pairs']} | "
            f"{'yes' if row['finite_partition_exact'] else 'no'} |"
        )
    lines.extend(["", "## Claim Boundary", "", report["claim_boundary"], ""])
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    return report


def main() -> int:
    prereg = read_json(PREREGISTRATION)
    source_errors = verify_preregistration(prereg)
    if str(TOOL_SANDBOX) not in sys.path:
        sys.path.insert(0, str(TOOL_SANDBOX))
    specs = enumerate_context_specs(prereg)
    rows = [execute_context(spec) for spec in specs]
    report = write_outputs(prereg, rows, source_errors)
    print(
        json.dumps(
            {
                "status": report["status"],
                "n_tools": report["n_tools"],
                "n_contexts": report["n_contexts"],
                "typed_relation_agreement": report["typed_relation_agreement"],
                "representations": report["representations"],
            },
            indent=2,
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
