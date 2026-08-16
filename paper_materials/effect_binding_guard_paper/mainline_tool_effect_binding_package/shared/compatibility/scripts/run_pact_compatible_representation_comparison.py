#!/usr/bin/env python3
"""Compare argument-level provenance views with effect-occurrence views.

This is a representation-level comparison inspired by PACT's public L2
argument-role contract. It is not a reproduction of PACT's inference pipeline
or AgentDojo protocol.
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *SCRIPT_PATH.parents)
    if (candidate / "paper/current-usenix").exists()
)
FINITE_CONTEXTS = (
    ROOT
    / "experiments/human-authority-and-causal-validation/results/"
    "finite-domain-effect-binding-validation/finite-contexts.jsonl"
)
HELDOUT_CONTEXTS = (
    ROOT
    / "experiments/human-authority-and-causal-validation/evaluation/"
    "heldout-toolsandbox-effect-binding-validation/heldout-contexts.jsonl"
)
OUTPUT = (
    ROOT
    / "experiments/human-authority-and-causal-validation/results/"
    "pact-compatible-effect-granularity-comparison"
)
REPORT_JSON = OUTPUT / "pact-compatible-comparison-report.json"
REPORT_MD = OUTPUT / "pact-compatible-comparison-report.md"
SUMMARY_CSV = OUTPUT / "representation-summary.csv"
WITNESSES_JSONL = OUTPUT / "authorization-separating-witnesses.jsonl"


# PACT's public contract uses target, command, credential, content, selector,
# and control roles. These reviewed static assignments intentionally give the
# argument-level view every concrete input value and a trusted origin.
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
    "add_reminder": {
        "content": "content",
        "latitude": "selector",
        "longitude": "selector",
        "reminder_timestamp": "control",
    },
    "remove_contact": {
        "person_id": "selector",
    },
    "set_location_service_status": {
        "on": "control",
    },
    "set_low_battery_mode_status": {
        "on": "control",
    },
}


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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
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
    # ToolSandbox permits optional latitude/longitude fields.
    missing = [
        field
        for field in missing
        if not (tool_name == "add_reminder" and field in {"latitude", "longitude"})
    ]
    if unknown or missing:
        raise ValueError(
            f"{tool_name}: argument-role mismatch unknown={unknown} missing={missing}"
        )

    entries: list[dict[str, Any]] = []
    for name, value in sorted(arguments.items()):
        entry = {
            "argument": name,
            "role": role_map[name],
            "origin": "trusted_structured_call",
            "trust": "USER",
        }
        if include_values:
            entry["value"] = stable(value)
        entries.append(entry)
    return {
        "tool_name": tool_name,
        "contract_level": "L2_argument_role",
        "arguments": entries,
    }


def normalize_finite() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in read_jsonl(FINITE_CONTEXTS):
        tool_name = source["tool_instance_key"]
        effects = source["source_effects"]
        rows.append(
            {
                "dataset": "agentdojo_finite_56",
                "context_id": source["context_id"],
                "tool_name": tool_name,
                "arguments": source["args"],
                "state_name": "fresh_suite_state",
                "source_effects": effects,
                "source_effect_signature": digest(effects),
                "representations": {
                    "tool_name": tool_name,
                    "pact_role_provenance": pact_argument_view(
                        tool_name, source["args"], include_values=False
                    ),
                    "pact_value_role_provenance": pact_argument_view(
                        tool_name, source["args"], include_values=True
                    ),
                    "typed_effect_occurrence": source["representations"][
                        "reviewed_typed_contract"
                    ],
                    "source_full_effect": source["representations"][
                        "source_full_effect"
                    ],
                },
            }
        )
    return rows


def normalize_heldout() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in read_jsonl(HELDOUT_CONTEXTS):
        tool_name = source["tool_name"]
        effects = source["source_effect_atoms"]
        rows.append(
            {
                "dataset": "toolsandbox_heldout_32",
                "context_id": source["case_id"],
                "tool_name": tool_name,
                "arguments": source["arguments"],
                "state_name": source["state_name"],
                "source_effects": effects,
                "source_effect_signature": digest(effects),
                "representations": {
                    "tool_name": tool_name,
                    "pact_role_provenance": pact_argument_view(
                        tool_name, source["arguments"], include_values=False
                    ),
                    "pact_value_role_provenance": pact_argument_view(
                        tool_name, source["arguments"], include_values=True
                    ),
                    "typed_effect_occurrence": source["representations"][
                        "typed_contract"
                    ],
                    "source_full_effect": source["representations"][
                        "source_full_effect"
                    ],
                },
            }
        )
    return rows


def analyze_representation(
    contexts: list[dict[str, Any]],
    representation: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    by_representation: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_effect: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for context in contexts:
        marker = digest(context["representations"][representation])
        by_representation[marker].append(context)
        by_effect[context["source_effect_signature"]].append(context)

    collision_cells = 0
    contexts_in_collision_cells = 0
    separating_pairs = 0
    witnesses: list[dict[str, Any]] = []
    for marker, cell in sorted(by_representation.items()):
        effect_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for context in cell:
            effect_groups[context["source_effect_signature"]].append(context)
        if len(effect_groups) <= 1:
            continue
        collision_cells += 1
        contexts_in_collision_cells += len(cell)
        groups = list(effect_groups.values())
        separating_pairs += sum(
            len(left) * len(right)
            for left, right in itertools.combinations(groups, 2)
        )
        for left, right in itertools.combinations(groups, 2):
            left_row, right_row = left[0], right[0]
            witnesses.append(
                {
                    "dataset": left_row["dataset"],
                    "representation": representation,
                    "representation_signature": marker,
                    "left_context_id": left_row["context_id"],
                    "right_context_id": right_row["context_id"],
                    "tool_name": left_row["tool_name"],
                    "same_arguments": (
                        canonical_json(left_row["arguments"])
                        == canonical_json(right_row["arguments"])
                    ),
                    "left_state": left_row["state_name"],
                    "right_state": right_row["state_name"],
                    "shared_representation": left_row["representations"][
                        representation
                    ],
                    "left_effects": left_row["source_effects"],
                    "right_effects": right_row["source_effects"],
                    "witness_property": (
                        "same monitored representation but distinct source-observed "
                        "effect multisets; the finite exact-effect authority family "
                        "contains an authorization-separating bound"
                    ),
                }
            )

    overpartition_effect_cells = 0
    overpartition_pairs = 0
    for effect_cell in by_effect.values():
        groups = Counter(
            digest(context["representations"][representation])
            for context in effect_cell
        )
        if len(groups) <= 1:
            continue
        overpartition_effect_cells += 1
        counts = list(groups.values())
        overpartition_pairs += sum(
            left * right for left, right in itertools.combinations(counts, 2)
        )

    return (
        {
            "dataset": contexts[0]["dataset"],
            "representation": representation,
            "n_contexts": len(contexts),
            "n_representation_cells": len(by_representation),
            "n_effect_cells": len(by_effect),
            "authorization_collision_cells": collision_cells,
            "contexts_in_collision_cells": contexts_in_collision_cells,
            "authorization_separating_pairs": separating_pairs,
            "overpartition_effect_cells": overpartition_effect_cells,
            "overpartition_pairs": overpartition_pairs,
            "finite_collision_complete": collision_cells == 0,
            "finite_partition_exact": (
                collision_cells == 0 and overpartition_pairs == 0
            ),
        },
        witnesses,
    )


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "# PACT-Compatible Argument Representation vs. Effect Occurrences",
        "",
        "## Scope",
        "",
        (
            "This deterministic audit compares a public PACT-L2-inspired "
            "argument-role/provenance view with the paper's typed effect-occurrence "
            "view. It is not a reproduction of PACT's automatic role inference, "
            "cross-step provenance inference, policy, or AgentDojo evaluation."
        ),
        "",
        (
            "The maximal argument view includes the tool name and every concrete "
            "argument name, value, reviewed semantic role, and trusted origin. "
            "This favors the argument representation. It still omits pre-state and "
            "the tool implementation's one-to-many effect expansion, because those "
            "objects are not call arguments."
        ),
        "",
        "## Results",
        "",
        "| Dataset | Representation | Cells | Collision cells | Separating pairs | "
        "Overpartition pairs | Complete | Exact |",
        "|---|---|---:|---:|---:|---:|:---:|:---:|",
    ]
    for row in report["representations"]:
        lines.append(
            f"| {row['dataset']} | {row['representation']} | "
            f"{row['n_representation_cells']} | "
            f"{row['authorization_collision_cells']} | "
            f"{row['authorization_separating_pairs']} | "
            f"{row['overpartition_pairs']} | "
            f"{'yes' if row['finite_collision_complete'] else 'no'} | "
            f"{'yes' if row['finite_partition_exact'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "On the fresh-state AgentDojo finite domain, the maximal argument "
                "view can preserve all observed distinctions. This domain alone "
                "does not separate argument values from effect occurrences."
            ),
            "",
            (
                "On the pre-registered ToolSandbox domain, identical tool names "
                "and argument values can realize different effects under different "
                "pre-states, including no-op and compound setting changes. The "
                "maximal argument view therefore retains authorization collisions, "
                "while the typed effect-occurrence view matches the source-effect "
                "partition."
            ),
            "",
            "This is a finite representation comparison, not a claim that the "
            "full PACT system is unsafe or that effect occurrences dominate every "
            "argument-provenance policy.",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> dict[str, Any]:
    if not FINITE_CONTEXTS.exists() or not HELDOUT_CONTEXTS.exists():
        missing = [
            str(path.relative_to(ROOT))
            for path in (FINITE_CONTEXTS, HELDOUT_CONTEXTS)
            if not path.exists()
        ]
        raise FileNotFoundError(f"missing required contexts: {missing}")

    datasets = {
        "agentdojo_finite_56": normalize_finite(),
        "toolsandbox_heldout_32": normalize_heldout(),
    }
    expected_counts = {
        "agentdojo_finite_56": 56,
        "toolsandbox_heldout_32": 32,
    }
    if {name: len(rows) for name, rows in datasets.items()} != expected_counts:
        raise ValueError("input context count changed from the frozen comparison")

    representation_names = [
        "tool_name",
        "pact_role_provenance",
        "pact_value_role_provenance",
        "typed_effect_occurrence",
        "source_full_effect",
    ]
    summaries: list[dict[str, Any]] = []
    witnesses: list[dict[str, Any]] = []
    for rows in datasets.values():
        for representation in representation_names:
            summary, found = analyze_representation(rows, representation)
            summaries.append(summary)
            witnesses.extend(found)

    summary_index = {
        (row["dataset"], row["representation"]): row for row in summaries
    }
    finite_maximal = summary_index[
        ("agentdojo_finite_56", "pact_value_role_provenance")
    ]
    heldout_maximal = summary_index[
        ("toolsandbox_heldout_32", "pact_value_role_provenance")
    ]
    heldout_typed = summary_index[
        ("toolsandbox_heldout_32", "typed_effect_occurrence")
    ]
    same_argument_state_witnesses = [
        row
        for row in witnesses
        if row["dataset"] == "toolsandbox_heldout_32"
        and row["representation"] == "pact_value_role_provenance"
        and row["same_arguments"]
        and row["left_state"] != row["right_state"]
    ]
    gates = {
        "finite_maximal_argument_view_complete": finite_maximal[
            "finite_collision_complete"
        ],
        "heldout_maximal_argument_view_has_collision": not heldout_maximal[
            "finite_collision_complete"
        ],
        "heldout_typed_effect_view_complete": heldout_typed[
            "finite_collision_complete"
        ],
        "heldout_same_argument_state_witness_present": bool(
            same_argument_state_witnesses
        ),
    }
    report = {
        "experiment": "pact_compatible_effect_granularity_comparison",
        "status": "passed" if all(gates.values()) else "failed",
        "source_paper": {
            "title": (
                "The Granularity Mismatch in Agent Security: Argument-Level "
                "Provenance Solves Enforcement and Isolates the LLM Reasoning "
                "Bottleneck"
            ),
            "arxiv": "2605.11039",
            "comparison_boundary": (
                "PACT-L2-inspired static argument roles and provenance only; "
                "not original code, automatic inference, policy, or benchmark "
                "reproduction"
            ),
        },
        "datasets": expected_counts,
        "argument_role_maps": ARGUMENT_ROLES,
        "representations": summaries,
        "n_witnesses": len(witnesses),
        "n_same_argument_state_witnesses": len(same_argument_state_witnesses),
        "gates": gates,
        "claim_boundary": (
            "The result separates maximal call-argument representation from "
            "effect occurrences only on the frozen ToolSandbox contexts where "
            "pre-state changes realized no-op or compound effects. It does not "
            "reproduce or evaluate the full PACT system."
        ),
    }

    OUTPUT.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    REPORT_MD.write_text(render_report(report), encoding="utf-8")
    write_jsonl(WITNESSES_JSONL, witnesses)
    with SUMMARY_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)

    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] != "passed":
        raise SystemExit(1)
    return report


if __name__ == "__main__":
    run()
