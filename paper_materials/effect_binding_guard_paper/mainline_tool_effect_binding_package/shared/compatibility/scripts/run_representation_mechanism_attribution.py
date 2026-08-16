#!/usr/bin/env python3
"""Measure authorization ambiguity caused only by monitor representation.

The experiment holds each authorization predicate and every source-observed
effect fixed. It changes only the representation available to a hypothetical
pre-commit monitor. A representation is insufficient for a policy when two
contexts have the same representation but require different policy decisions.

This is a finite-domain mechanism-attribution experiment. It does not execute
an agent, infer user authority, or claim end-to-end attack prevention.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


SCRIPT_PATH = Path(__file__).resolve()
ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *SCRIPT_PATH.parents)
    if (candidate / "paper/current-usenix").exists()
)
AGENTDOJO_CONTEXTS = (
    ROOT
    / "experiments/human-authority-and-causal-validation/results/"
    "finite-domain-effect-binding-validation/finite-contexts.jsonl"
)
TOOL_SANDBOX_CONTEXTS = (
    ROOT
    / "experiments/human-authority-and-causal-validation/evaluation/"
    "heldout-toolsandbox-effect-binding-validation/heldout-contexts.jsonl"
)
OUTPUT_DIR = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "representation-mechanism-attribution"
)
REPORT_JSON = OUTPUT_DIR / "representation-mechanism-attribution-report.json"
REPORT_MD = OUTPUT_DIR / "representation-mechanism-attribution-report.md"
POLICIES_JSONL = OUTPUT_DIR / "authorization-policy-instances.jsonl"
RESULTS_CSV = OUTPUT_DIR / "representation-policy-results.csv"
WITNESSES_JSONL = OUTPUT_DIR / "representation-ambiguity-witnesses.jsonl"

REPRESENTATIONS = (
    "tool_name",
    "pact_role_provenance",
    "pact_value_role_provenance",
    "effect_only",
    "common_effect_tuple",
    "typed_effect_occurrence",
    "source_full_effect",
)

# PACT's public L2 vocabulary is used only to construct comparable argument
# views. This is not a reproduction of PACT's inference or benchmark protocol.
ARGUMENT_ROLES: dict[str, dict[str, str]] = {
    "workspace/add_calendar_event_participants": {
        "event_id": "selector",
        "participants": "target",
    },
    "workspace/create_file": {
        "filename": "selector",
        "content": "content",
    },
    "workspace/share_file": {
        "file_id": "selector",
        "email": "target",
        "permission": "control",
    },
    "slack/send_direct_message": {
        "recipient": "target",
        "body": "content",
    },
    "banking/schedule_transaction": {
        "recipient": "target",
        "amount": "control",
        "subject": "content",
        "date": "control",
        "recurring": "control",
    },
    "add_contact": {
        "name": "content",
        "phone_number": "target",
        "relationship": "content",
        "is_self": "control",
    },
    "remove_contact": {"person_id": "selector"},
    "add_reminder": {
        "content": "content",
        "latitude": "selector",
        "longitude": "selector",
        "reminder_timestamp": "control",
    },
    "set_location_service_status": {"on": "control"},
    "set_low_battery_mode_status": {"on": "control"},
}

ATOM_FIELDS = (
    "effect",
    "operation",
    "resource_id",
    "resource_type",
    "target_principal",
    "visibility",
    "commit_mode",
    "provenance_source",
    "control_source",
)
MISSING = "__MISSING__"


def stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): stable(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [stable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def canonical_json(value: Any) -> str:
    return json.dumps(stable(value), sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def pact_argument_view(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    include_values: bool,
) -> dict[str, Any]:
    role_map = ARGUMENT_ROLES[tool_name]
    unknown = sorted(set(arguments) - set(role_map))
    missing = sorted(set(role_map) - set(arguments))
    missing = [
        field
        for field in missing
        if not (tool_name == "add_reminder" and field in {"latitude", "longitude"})
    ]
    if unknown or missing:
        raise ValueError(
            f"{tool_name}: argument-role mismatch unknown={unknown} missing={missing}"
        )

    entries = []
    for name, value in sorted(arguments.items()):
        entry = {
            "argument": name,
            "role": role_map[name],
            "origin": "trusted_structured_call",
        }
        if include_values:
            entry["value"] = stable(value)
        entries.append(entry)
    return {
        "tool_name": tool_name,
        "contract_level": "L2_argument_role",
        "arguments": entries,
    }


def normalize_atom(atom: dict[str, Any]) -> dict[str, Any]:
    return {
        "effect": atom.get("effect"),
        "operation": atom.get("operation"),
        "resource_id": atom.get("resource_id", atom.get("resource")),
        "resource_type": atom.get("resource_type"),
        "target_principal": atom.get("target_principal", atom.get("target")),
        "visibility": atom.get("visibility"),
        "commit_mode": atom.get("commit_mode"),
        "provenance_source": atom.get("provenance_source"),
        "control_source": atom.get("control_source"),
        "qualifiers": stable(atom.get("qualifiers", {})),
    }


def effect_only(atoms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"effect": atom["effect"]} for atom in atoms]


def normalize_agentdojo() -> list[dict[str, Any]]:
    contexts = []
    for source in read_jsonl(AGENTDOJO_CONTEXTS):
        tool_name = source["tool_instance_key"]
        atoms = [normalize_atom(atom) for atom in source["source_effects"]]
        representations = source["representations"]
        contexts.append(
            {
                "dataset": "agentdojo_finite_56",
                "context_id": source["context_id"],
                "tool_name": tool_name,
                "arguments": source["args"],
                "source_atoms": atoms,
                "representations": {
                    "tool_name": tool_name,
                    "pact_role_provenance": pact_argument_view(
                        tool_name, source["args"], include_values=False
                    ),
                    "pact_value_role_provenance": pact_argument_view(
                        tool_name, source["args"], include_values=True
                    ),
                    "effect_only": effect_only(atoms),
                    "common_effect_tuple": representations[
                        "reviewed_common_contract"
                    ],
                    "typed_effect_occurrence": representations[
                        "reviewed_typed_contract"
                    ],
                    "source_full_effect": representations["source_full_effect"],
                },
            }
        )
    return contexts


def normalize_toolsandbox() -> list[dict[str, Any]]:
    contexts = []
    for source in read_jsonl(TOOL_SANDBOX_CONTEXTS):
        tool_name = source["tool_name"]
        atoms = [normalize_atom(atom) for atom in source["source_effect_atoms"]]
        representations = source["representations"]
        contexts.append(
            {
                "dataset": "toolsandbox_heldout_32",
                "context_id": source["case_id"],
                "tool_name": tool_name,
                "arguments": source["arguments"],
                "source_atoms": atoms,
                "representations": {
                    "tool_name": tool_name,
                    "pact_role_provenance": pact_argument_view(
                        tool_name, source["arguments"], include_values=False
                    ),
                    "pact_value_role_provenance": pact_argument_view(
                        tool_name, source["arguments"], include_values=True
                    ),
                    "effect_only": effect_only(atoms),
                    "common_effect_tuple": representations["common_fields"],
                    "typed_effect_occurrence": representations["typed_contract"],
                    "source_full_effect": representations["source_full_effect"],
                },
            }
        )
    return contexts


def scalar_values(atoms: list[dict[str, Any]], field_path: str) -> list[Any]:
    values = []
    for atom in atoms:
        if field_path.startswith("qualifiers."):
            key = field_path.split(".", 1)[1]
            value = atom.get("qualifiers", {}).get(key, MISSING)
        else:
            value = atom.get(field_path, MISSING)
        values.append(stable(value))
    return values


def policy_decision(policy: dict[str, Any], context: dict[str, Any]) -> bool:
    atoms = context["source_atoms"]
    operator = policy["operator"]
    if operator == "no_effects":
        return not atoms
    if operator == "effect_count_at_most":
        return len(atoms) <= policy["value"]
    if operator == "all_atom_values_equal":
        return all(
            value == policy["value"]
            for value in scalar_values(atoms, policy["field_path"])
        )
    raise ValueError(f"unsupported policy operator: {operator}")


def make_policy(
    *,
    dataset: str,
    tool_name: str | None,
    family: str,
    operator: str,
    value: Any,
    field_path: str | None,
    description: str,
) -> dict[str, Any]:
    material = {
        "dataset": dataset,
        "tool_name": tool_name,
        "family": family,
        "operator": operator,
        "value": stable(value),
        "field_path": field_path,
    }
    return {
        "policy_id": f"policy-{digest(material)[:16]}",
        **material,
        "description": description,
        "authority_source": "deterministic_exhaustive_finite_policy_generator",
    }


def generate_policies(
    contexts: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    candidates: list[dict[str, Any]] = []
    by_dataset_tool: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for context in contexts:
        by_dataset_tool[(context["dataset"], context["tool_name"])].append(context)

    for (dataset, tool_name), rows in sorted(by_dataset_tool.items()):
        counts = sorted({len(row["source_atoms"]) for row in rows})
        if len(counts) > 1:
            for threshold in range(min(counts), max(counts)):
                candidates.append(
                    make_policy(
                        dataset=dataset,
                        tool_name=tool_name,
                        family="effect_multiplicity",
                        operator="effect_count_at_most",
                        value=threshold,
                        field_path=None,
                        description=(
                            f"Authorize {tool_name} only when it produces at most "
                            f"{threshold} effect occurrence(s)."
                        ),
                    )
                )
        if 0 in counts and max(counts) > 0:
            candidates.append(
                make_policy(
                    dataset=dataset,
                    tool_name=tool_name,
                    family="effect_presence",
                    operator="no_effects",
                    value=True,
                    field_path=None,
                    description=(
                        f"Authorize {tool_name} only when the observed state transition "
                        "contains no security-relevant effect."
                    ),
                )
            )

        field_paths = list(ATOM_FIELDS)
        qualifier_keys = sorted(
            {
                key
                for row in rows
                for atom in row["source_atoms"]
                for key in atom.get("qualifiers", {})
            }
        )
        field_paths.extend(f"qualifiers.{key}" for key in qualifier_keys)
        for field_path in field_paths:
            values = sorted(
                {
                    canonical_json(value): value
                    for row in rows
                    for value in scalar_values(row["source_atoms"], field_path)
                    if value not in {None, MISSING}
                }.values(),
                key=canonical_json,
            )
            if len(values) <= 1:
                continue
            family = (
                "qualifier_constraint"
                if field_path.startswith("qualifiers.")
                else (
                    "resource_target_constraint"
                    if field_path in {"resource_id", "target_principal"}
                    else (
                        "operation_commit_constraint"
                        if field_path in {"operation", "commit_mode"}
                        else "effect_field_constraint"
                    )
                )
            )
            for value in values:
                candidates.append(
                    make_policy(
                        dataset=dataset,
                        tool_name=tool_name,
                        family=family,
                        operator="all_atom_values_equal",
                        value=value,
                        field_path=field_path,
                        description=(
                            f"Authorize {tool_name} only when every produced atom has "
                            f"{field_path}={value!r}."
                        ),
                    )
                )

    # Global effect-family policies are intentionally included as null controls:
    # a tool-name view may be sufficient when each tool has one effect family.
    by_dataset: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for context in contexts:
        by_dataset[context["dataset"]].append(context)
    for dataset, rows in sorted(by_dataset.items()):
        effects = sorted(
            {
                atom["effect"]
                for row in rows
                for atom in row["source_atoms"]
                if atom.get("effect") is not None
            }
        )
        for effect in effects:
            candidates.append(
                make_policy(
                    dataset=dataset,
                    tool_name=None,
                    family="global_effect_family",
                    operator="all_atom_values_equal",
                    value=effect,
                    field_path="effect",
                    description=(
                        "Authorize calls only when every produced atom belongs to "
                        f"effect family {effect!r}."
                    ),
                )
            )

    exercised = []
    skipped_no_decision_variation = 0
    seen = set()
    for policy in candidates:
        if policy["policy_id"] in seen:
            continue
        seen.add(policy["policy_id"])
        rows = [
            row
            for row in contexts
            if row["dataset"] == policy["dataset"]
            and (
                policy["tool_name"] is None
                or row["tool_name"] == policy["tool_name"]
            )
        ]
        decisions = {policy_decision(policy, row) for row in rows}
        if decisions != {False, True}:
            skipped_no_decision_variation += 1
            continue
        exercised.append(policy)
    return exercised, {
        "candidate_policies": len(seen),
        "exercised_policies": len(exercised),
        "skipped_no_decision_variation": skipped_no_decision_variation,
    }


def contexts_for_policy(
    contexts: list[dict[str, Any]], policy: dict[str, Any]
) -> list[dict[str, Any]]:
    return [
        context
        for context in contexts
        if context["dataset"] == policy["dataset"]
        and (
            policy["tool_name"] is None
            or context["tool_name"] == policy["tool_name"]
        )
    ]


def analyze_policy_representation(
    policy: dict[str, Any],
    representation: str,
    contexts: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cells: dict[str, list[tuple[dict[str, Any], bool]]] = defaultdict(list)
    for context in contexts:
        marker = digest(context["representations"][representation])
        cells[marker].append((context, policy_decision(policy, context)))

    n_safe = sum(decision for cell in cells.values() for _, decision in cell)
    n_unsafe = sum(not decision for cell in cells.values() for _, decision in cell)
    ambiguous_cells = 0
    ambiguous_contexts = 0
    safe_in_ambiguous = 0
    unsafe_in_ambiguous = 0
    minimum_errors = 0
    witnesses = []
    for marker, cell in sorted(cells.items()):
        safe = [row for row, decision in cell if decision]
        unsafe = [row for row, decision in cell if not decision]
        if not safe or not unsafe:
            continue
        ambiguous_cells += 1
        ambiguous_contexts += len(cell)
        safe_in_ambiguous += len(safe)
        unsafe_in_ambiguous += len(unsafe)
        minimum_errors += min(len(safe), len(unsafe))
        witnesses.append(
            {
                "policy_id": policy["policy_id"],
                "policy_family": policy["family"],
                "dataset": policy["dataset"],
                "tool_name": policy["tool_name"],
                "representation": representation,
                "representation_signature": marker,
                "safe_context_ids": [row["context_id"] for row in safe],
                "unsafe_context_ids": [row["context_id"] for row in unsafe],
                "safe_source_atoms": [row["source_atoms"] for row in safe[:2]],
                "unsafe_source_atoms": [row["source_atoms"] for row in unsafe[:2]],
                "witness_property": (
                    "identical monitored representation under one fixed authority "
                    "predicate, but different ideal authorization decisions"
                ),
            }
        )

    n = n_safe + n_unsafe
    return (
        {
            "policy_id": policy["policy_id"],
            "policy_family": policy["family"],
            "dataset": policy["dataset"],
            "tool_name": policy["tool_name"] or "ALL",
            "representation": representation,
            "n_contexts": n,
            "n_safe": n_safe,
            "n_unsafe": n_unsafe,
            "n_representation_cells": len(cells),
            "ambiguous_cells": ambiguous_cells,
            "ambiguous_contexts": ambiguous_contexts,
            "perfectly_separable": ambiguous_cells == 0,
            "fail_closed_coverage": (n - ambiguous_contexts) / n,
            "fail_closed_safe_abstain": safe_in_ambiguous,
            "fail_closed_safe_abstain_rate": (
                safe_in_ambiguous / n_safe if n_safe else 0.0
            ),
            "fail_closed_unsafe_pre_allow": 0,
            "permissive_unsafe_pre_allow": unsafe_in_ambiguous,
            "permissive_upa_rate": (
                unsafe_in_ambiguous / n_unsafe if n_unsafe else 0.0
            ),
            "permissive_false_deny": 0,
            "minimum_deterministic_errors": minimum_errors,
            "minimum_deterministic_error_rate": minimum_errors / n,
        },
        witnesses,
    )


def aggregate_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        grouped[(result["dataset"], result["representation"])].append(result)

    aggregates = []
    for (dataset, representation), rows in sorted(grouped.items()):
        n = sum(row["n_contexts"] for row in rows)
        n_safe = sum(row["n_safe"] for row in rows)
        n_unsafe = sum(row["n_unsafe"] for row in rows)
        ambiguous = sum(row["ambiguous_contexts"] for row in rows)
        safe_abstain = sum(row["fail_closed_safe_abstain"] for row in rows)
        permissive_upa = sum(row["permissive_unsafe_pre_allow"] for row in rows)
        min_errors = sum(row["minimum_deterministic_errors"] for row in rows)
        aggregates.append(
            {
                "dataset": dataset,
                "representation": representation,
                "n_policy_instances": len(rows),
                "n_policy_context_pairs": n,
                "perfectly_separable_policies": sum(
                    row["perfectly_separable"] for row in rows
                ),
                "perfectly_separable_policy_rate": (
                    sum(row["perfectly_separable"] for row in rows) / len(rows)
                ),
                "fail_closed_coverage": (n - ambiguous) / n,
                "fail_closed_safe_abstain_rate": (
                    safe_abstain / n_safe if n_safe else 0.0
                ),
                "permissive_upa_rate": (
                    permissive_upa / n_unsafe if n_unsafe else 0.0
                ),
                "minimum_deterministic_error_rate": min_errors / n,
            }
        )
    return aggregates


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError("refusing to write empty result table")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Representation Mechanism Attribution",
        "",
        "## Scope",
        "",
        (
            "This finite-domain experiment holds source-observed effects and each "
            "authorization predicate fixed, and changes only the representation "
            "available to the monitor. It does not execute an agent or infer user "
            "authority."
        ),
        "",
        "## Policy construction",
        "",
        (
            f"The deterministic generator produced "
            f"{report['policy_generation']['candidate_policies']} candidate policies; "
            f"{report['policy_generation']['exercised_policies']} had both ALLOW and "
            "DENY contexts and were retained. Policies exhaustively cover observed "
            "resource/target values, effect multiplicity, effect presence, and "
            "security-relevant qualifier values. Global effect-family policies are "
            "included as null controls."
        ),
        "",
        "## Aggregate results",
        "",
        (
            "| Dataset | Representation | Policies | Perfectly separable | "
            "Fail-closed coverage | Safe abstain | Permissive UPA | "
            "Minimum error |"
        ),
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["aggregates"]:
        lines.append(
            f"| {row['dataset']} | {row['representation']} | "
            f"{row['n_policy_instances']} | "
            f"{row['perfectly_separable_policy_rate']:.3f} | "
            f"{row['fail_closed_coverage']:.3f} | "
            f"{row['fail_closed_safe_abstain_rate']:.3f} | "
            f"{row['permissive_upa_rate']:.3f} | "
            f"{row['minimum_deterministic_error_rate']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "- A mixed cell is a constructive witness: one fixed policy requires "
                "different decisions for contexts that the monitor cannot distinguish."
            ),
            (
                "- Fail-closed coverage reports the fraction of policy-context pairs "
                "that can be decided without guessing. Its unsafe-pre-allow count is "
                "zero by construction; safe cases in mixed cells become abstentions."
            ),
            (
                "- Permissive UPA reports the opposite end of the tradeoff: mixed cells "
                "are allowed, preserving safe utility but admitting unsafe contexts."
            ),
            (
                "- The minimum deterministic error is the best possible cell-wise "
                "binary classifier under the representation; it is not a learned-model "
                "accuracy estimate."
            ),
            "",
            "## Claim boundary",
            "",
            (
                "The result attributes finite-domain authorization ambiguity to "
                "representation granularity under the tested policy family. It does "
                "not establish production safety, authority soundness, complete "
                "mediation, or end-to-end AgentDojo utility."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def run() -> dict[str, Any]:
    contexts = normalize_agentdojo() + normalize_toolsandbox()
    if len(contexts) != 88:
        raise RuntimeError(f"expected 88 frozen contexts, found {len(contexts)}")
    policies, generation = generate_policies(contexts)
    if not policies:
        raise RuntimeError("no exercised authorization policies")

    results = []
    witnesses = []
    for policy in policies:
        scoped_contexts = contexts_for_policy(contexts, policy)
        for representation in REPRESENTATIONS:
            result, found = analyze_policy_representation(
                policy, representation, scoped_contexts
            )
            results.append(result)
            witnesses.extend(found)

    aggregates = aggregate_results(results)
    typed = {
        row["dataset"]: row
        for row in aggregates
        if row["representation"] == "typed_effect_occurrence"
    }
    if set(typed) != {"agentdojo_finite_56", "toolsandbox_heldout_32"}:
        raise RuntimeError("typed effect aggregate missing a dataset")
    if any(row["minimum_deterministic_error_rate"] != 0.0 for row in typed.values()):
        raise RuntimeError("typed effect occurrence failed an exercised fixed policy")
    if not any(
        row["minimum_deterministic_error_rate"] > 0.0
        for row in aggregates
        if row["representation"]
        in {"tool_name", "pact_value_role_provenance", "common_effect_tuple"}
    ):
        raise RuntimeError("experiment did not exercise a coarser representation")

    report = {
        "experiment": "representation_mechanism_attribution",
        "status": "passed",
        "design": {
            "independent_variables": ["monitor_representation"],
            "held_fixed": [
                "source_observed_effects",
                "authorization_predicate",
                "decision_semantics",
                "recovery_semantics",
            ],
            "unit_of_analysis": "policy_context_pair",
            "representations": list(REPRESENTATIONS),
            "datasets": {
                "agentdojo_finite_56": 56,
                "toolsandbox_heldout_32": 32,
            },
        },
        "policy_generation": generation,
        "n_result_rows": len(results),
        "n_ambiguity_witnesses": len(witnesses),
        "aggregates": aggregates,
        "source_artifacts": [
            str(AGENTDOJO_CONTEXTS.relative_to(ROOT)),
            str(TOOL_SANDBOX_CONTEXTS.relative_to(ROOT)),
        ],
        "output_artifacts": [
            display_path(path)
            for path in (
                REPORT_JSON,
                REPORT_MD,
                POLICIES_JSONL,
                RESULTS_CSV,
                WITNESSES_JSONL,
            )
        ],
        "claim_boundary": (
            "Finite-domain representation sufficiency under deterministic, "
            "exhaustively generated policy predicates; not end-to-end safety."
        ),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(POLICIES_JSONL, policies)
    write_csv(RESULTS_CSV, results)
    write_jsonl(WITNESSES_JSONL, witnesses)
    REPORT_JSON.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    REPORT_MD.write_text(build_markdown(report), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = run()
    print(
        json.dumps(
            {
                "status": result["status"],
                "exercised_policies": result["policy_generation"][
                    "exercised_policies"
                ],
                "result_rows": result["n_result_rows"],
                "ambiguity_witnesses": result["n_ambiguity_witnesses"],
                "report": display_path(REPORT_JSON),
            },
            sort_keys=True,
        )
    )
