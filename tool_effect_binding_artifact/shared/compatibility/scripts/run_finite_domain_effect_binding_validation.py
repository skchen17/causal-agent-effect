#!/usr/bin/env python3
"""Exhaustively check effect representations on a finite AgentDojo domain."""

from __future__ import annotations

import copy
import csv
import hashlib
import importlib.util
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable


SCRIPT_PATH = Path(__file__).resolve()
ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *SCRIPT_PATH.parents)
    if (candidate / "paper/current-usenix").exists()
)
TRUSTED_PROJECTIONS = (
    ROOT
    / "evaluation/e85_security_effect_projections/"
    "trusted_security_effect_projections.jsonl"
)
E85_RUNNER = ROOT / "scripts/run_e85_agentdojo_projection_interventions.py"
OUTPUT = (
    ROOT
    / "experiments/human-authority-and-causal-validation/results/"
    "finite-domain-effect-binding-validation"
)
CONTEXTS_PATH = OUTPUT / "finite-contexts.jsonl"
WITNESSES_PATH = OUTPUT / "authorization-separating-witnesses.jsonl"
SUMMARY_CSV = OUTPUT / "representation-summary.csv"
REPORT_JSON = OUTPUT / "finite-domain-validation-report.json"
REPORT_MD = OUTPUT / "finite-domain-validation-report.md"


def stable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
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


def load_e85_runner() -> Any:
    spec = importlib.util.spec_from_file_location("e85_projection_runner", E85_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {E85_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def added_multiset(before: list[Any], after: list[Any]) -> list[Any]:
    before_counts = Counter(canonical_json(item) for item in before)
    values = {canonical_json(item): item for item in after}
    after_counts = Counter(canonical_json(item) for item in after)
    result: list[Any] = []
    for marker, count in sorted((after_counts - before_counts).items()):
        result.extend(copy.deepcopy(values[marker]) for _ in range(count))
    return result


def calendar_participant_effects(
    before: dict[str, Any],
    after: dict[str, Any],
    args: dict[str, Any],
    _output: Any,
) -> list[dict[str, Any]]:
    event_id = str(args["event_id"])
    before_event = before["calendar"]["events"][event_id]
    after_event = after["calendar"]["events"][event_id]
    added = added_multiset(before_event["participants"], after_event["participants"])
    return [
        {
            "effect": "calendar_participant_added",
            "operation": "add_participant",
            "resource": event_id,
            "target": participant,
            "visibility": "private",
            "commit_mode": "commit",
            "qualifiers": {},
        }
        for participant in added
    ]


def file_creation_effects(
    before: dict[str, Any],
    after: dict[str, Any],
    _args: dict[str, Any],
    _output: Any,
) -> list[dict[str, Any]]:
    before_files = before["cloud_drive"]["files"]
    after_files = after["cloud_drive"]["files"]
    created_ids = sorted(set(after_files) - set(before_files))
    return [
        {
            "effect": "file_created",
            "operation": "create",
            "resource": file_id,
            "target": after_files[file_id]["owner"],
            "visibility": "private",
            "commit_mode": "commit",
            "qualifiers": {
                "content": after_files[file_id]["content"],
                "filename": after_files[file_id]["filename"],
            },
        }
        for file_id in created_ids
    ]


def file_sharing_effects(
    before: dict[str, Any],
    after: dict[str, Any],
    args: dict[str, Any],
    _output: Any,
) -> list[dict[str, Any]]:
    file_id = str(args["file_id"])
    before_acl = before["cloud_drive"]["files"][file_id]["shared_with"]
    after_acl = after["cloud_drive"]["files"][file_id]["shared_with"]
    changed = [
        email
        for email in sorted(after_acl)
        if before_acl.get(email) != after_acl.get(email)
    ]
    return [
        {
            "effect": "file_permission_granted",
            "operation": "share",
            "resource": file_id,
            "target": email,
            "visibility": after_acl[email],
            "commit_mode": "commit",
            "qualifiers": {},
        }
        for email in changed
    ]


def direct_message_effects(
    before: dict[str, Any],
    after: dict[str, Any],
    args: dict[str, Any],
    _output: Any,
) -> list[dict[str, Any]]:
    recipient = args["recipient"]
    new_messages = added_multiset(
        before["slack"]["user_inbox"].get(recipient, []),
        after["slack"]["user_inbox"].get(recipient, []),
    )
    return [
        {
            "effect": "direct_message_delivered",
            "operation": "send",
            "resource": f"payload:{digest({'recipient': recipient, 'body': row['body']})[:16]}",
            "target": recipient,
            "visibility": "private",
            "commit_mode": "commit",
            "qualifiers": {},
        }
        for row in new_messages
    ]


def scheduled_transaction_effects(
    before: dict[str, Any],
    after: dict[str, Any],
    _args: dict[str, Any],
    _output: Any,
) -> list[dict[str, Any]]:
    new_rows = added_multiset(
        before["bank_account"]["scheduled_transactions"],
        after["bank_account"]["scheduled_transactions"],
    )
    return [
        {
            "effect": "funds_transfer_scheduled",
            "operation": "schedule",
            "resource": f"account_funds:{row['amount']}",
            "target": row["recipient"],
            "visibility": "private",
            "commit_mode": "scheduled",
            "qualifiers": {
                "date": row["date"],
                "recurring": row["recurring"],
                "subject": row["subject"],
            },
        }
        for row in new_rows
    ]


ORACLES: dict[str, Callable[..., list[dict[str, Any]]]] = {
    "add_calendar_event_participants": calendar_participant_effects,
    "create_file": file_creation_effects,
    "share_file": file_sharing_effects,
    "send_direct_message": direct_message_effects,
    "schedule_transaction": scheduled_transaction_effects,
}


def finite_calls() -> list[tuple[str, str, dict[str, Any]]]:
    rows: list[tuple[str, str, dict[str, Any]]] = []
    for event_id, participants in itertools.product(
        ("6", "9"),
        (
            ["finite.a@example.com"],
            ["finite.b@example.com"],
            ["finite.a@example.com", "finite.b@example.com"],
            ["finite.a@example.com", "finite.a@example.com"],
        ),
    ):
        rows.append(
            (
                "workspace",
                "add_calendar_event_participants",
                {"event_id": event_id, "participants": participants},
            )
        )
    for filename, content in itertools.product(
        ("finite-a.txt", "finite-b.txt"), ("alpha", "beta")
    ):
        rows.append(
            ("workspace", "create_file", {"filename": filename, "content": content})
        )
    for file_id, email, permission in itertools.product(
        ("0", "1"),
        ("finite.a@example.com", "finite.b@example.com"),
        ("r", "rw"),
    ):
        rows.append(
            (
                "workspace",
                "share_file",
                {"file_id": file_id, "email": email, "permission": permission},
            )
        )
    for recipient, body in itertools.product(("Alice", "Bob"), ("alpha", "beta")):
        rows.append(
            ("slack", "send_direct_message", {"recipient": recipient, "body": body})
        )
    for recipient, amount, subject, date, recurring in itertools.product(
        ("CH9300762011623852957", "GB29NWBK60161331926819"),
        (10.0, 25.0),
        ("invoice-a", "invoice-b"),
        ("2026-08-01", "2026-08-15"),
        (False, True),
    ):
        rows.append(
            (
                "banking",
                "schedule_transaction",
                {
                    "recipient": recipient,
                    "amount": amount,
                    "subject": subject,
                    "date": date,
                    "recurring": recurring,
                },
            )
        )
    return rows


def source_projection(
    effects: list[dict[str, Any]], fields: tuple[str, ...]
) -> list[dict[str, Any]]:
    return sorted(
        [{field: stable(effect[field]) for field in fields} for effect in effects],
        key=canonical_json,
    )


def representation_values(
    tool_key: str,
    effects: list[dict[str, Any]],
    reviewed_common: list[dict[str, Any]],
    reviewed_typed: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "tool_name": tool_key,
        "source_effect_only": source_projection(effects, ("effect",)),
        "source_common_fields": source_projection(
            effects,
            (
                "effect",
                "operation",
                "resource",
                "target",
                "visibility",
                "commit_mode",
            ),
        ),
        "reviewed_common_contract": reviewed_common,
        "reviewed_typed_contract": reviewed_typed,
        "source_full_effect": effects,
    }


def execute_contexts() -> tuple[list[dict[str, Any]], list[str]]:
    from agentdojo.functions_runtime import FunctionsRuntime
    from agentdojo.task_suite.load_suites import get_suite

    e85 = load_e85_runner()
    reviewed_rows = read_jsonl(TRUSTED_PROJECTIONS)
    reviewed = {row["tool_instance_key"]: row for row in reviewed_rows}
    suites = {
        name: get_suite("v1.1.2", name) for name in ("workspace", "slack", "banking")
    }
    runtimes = {
        name: FunctionsRuntime(suite.tools) for name, suite in suites.items()
    }
    tool_index = {
        (suite_name, tool.name): tool
        for suite_name, suite in suites.items()
        for tool in suite.tools
    }
    source_errors: list[str] = []
    contexts: list[dict[str, Any]] = []

    for index, (suite_name, tool_name, args) in enumerate(finite_calls()):
        tool_key = f"{suite_name}/{tool_name}"
        review = reviewed[tool_key]
        if index == 0 or not any(
            row["tool_instance_key"] == tool_key for row in contexts
        ):
            source_errors.extend(
                f"{tool_key}:{error}"
                for error in e85.verify_source(tool_index[(suite_name, tool_name)], review)
            )
        outcome = e85.execute(runtimes[suite_name], suites[suite_name], tool_name, args)
        if outcome["error"] is not None:
            raise RuntimeError(f"{tool_key} failed for {args}: {outcome['error']}")
        effects = ORACLES[tool_name](
            outcome["before"], outcome["after"], args, outcome["output"]
        )
        if not effects:
            raise RuntimeError(f"{tool_key} produced no source-grounded security effect")
        effects = sorted(effects, key=canonical_json)
        common = e85.instantiate_atoms(
            review,
            args,
            outcome["before"],
            outcome["output"],
            include_qualifiers=False,
        )
        typed = e85.instantiate_atoms(
            review,
            args,
            outcome["before"],
            outcome["output"],
            include_qualifiers=True,
        )
        contexts.append(
            {
                "context_id": f"finite-{index:03d}",
                "suite": suite_name,
                "tool_name": tool_name,
                "tool_instance_key": tool_key,
                "args": stable(args),
                "source_effects": effects,
                "source_effect_signature": digest(effects),
                "observed_state_delta": outcome["delta"],
                "source_file_sha256": review["source_evidence"][
                    "source_file_sha256"
                ],
                "function_source_sha256": review["source_evidence"][
                    "function_source_sha256"
                ],
                "representations": representation_values(
                    tool_key, effects, common, typed
                ),
            }
        )
    return contexts, source_errors


def analyze_representation(
    contexts: list[dict[str, Any]], representation: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    by_representation: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_effect: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for context in contexts:
        rep_signature = digest(context["representations"][representation])
        by_representation[rep_signature].append(context)
        by_effect[context["source_effect_signature"]].append(context)

    collision_cells: list[list[dict[str, Any]]] = []
    separating_pairs = 0
    witnesses: list[dict[str, Any]] = []
    for rep_signature, cell in sorted(by_representation.items()):
        effect_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for context in cell:
            effect_groups[context["source_effect_signature"]].append(context)
        if len(effect_groups) <= 1:
            continue
        collision_cells.append(cell)
        group_values = list(effect_groups.values())
        separating_pairs += sum(
            len(left) * len(right)
            for left, right in itertools.combinations(group_values, 2)
        )
        left, right = group_values[0][0], group_values[1][0]
        left_effects = Counter(
            canonical_json(effect) for effect in left["source_effects"]
        )
        right_effects = Counter(
            canonical_json(effect) for effect in right["source_effects"]
        )
        if left_effects <= right_effects:
            authorized_context, rejected_context = left, right
        elif right_effects <= left_effects:
            authorized_context, rejected_context = right, left
        else:
            authorized_context, rejected_context = left, right
        witnesses.append(
            {
                "representation": representation,
                "representation_signature": rep_signature,
                "authorized_context_id": authorized_context["context_id"],
                "rejected_context_id": rejected_context["context_id"],
                "shared_representation": authorized_context["representations"][
                    representation
                ],
                "authority_bound": authorized_context["source_effects"],
                "authorized_effects": authorized_context["source_effects"],
                "rejected_effects": rejected_context["source_effects"],
                "witness_property": (
                    "same representation; authorized effect multiset is within "
                    "the constructed bound; the other effect multiset is not"
                ),
            }
        )

    overpartition_pairs = 0
    overpartition_effect_cells = 0
    for effect_cell in by_effect.values():
        groups: dict[str, int] = Counter(
            digest(context["representations"][representation])
            for context in effect_cell
        )
        if len(groups) <= 1:
            continue
        overpartition_effect_cells += 1
        counts = list(groups.values())
        overpartition_pairs += sum(a * b for a, b in itertools.combinations(counts, 2))

    summary = {
        "representation": representation,
        "n_contexts": len(contexts),
        "n_representation_cells": len(by_representation),
        "n_effect_cells": len(by_effect),
        "authorization_collision_cells": len(collision_cells),
        "contexts_in_collision_cells": sum(len(cell) for cell in collision_cells),
        "authorization_separating_pairs": separating_pairs,
        "overpartition_effect_cells": overpartition_effect_cells,
        "overpartition_pairs": overpartition_pairs,
        "finite_collision_complete": not collision_cells,
        "finite_partition_exact": not collision_cells and overpartition_pairs == 0,
    }
    return summary, witnesses


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "# Finite-Domain Effect-Binding Validation",
        "",
        "## Scope",
        "",
        (
            f"The audit exhaustively executed {report['n_contexts']} valid calls "
            f"covering {report['n_tools']} AgentDojo v1.1.2 tool instances. "
            "A source-specific oracle reconstructed committed security effects "
            "from fresh before/after states. Candidate representations were "
            "then compared against those effects; the oracle was not generated "
            "from the candidate contracts."
        ),
        "",
        "The admissible finite policy family contains every submultiset of the "
        "observed atomic-effect occurrences. Consequently, any two different "
        "concrete effect multisets can be separated by an authority bound. A representation is finite "
        "collision-complete exactly when no representation cell contains two "
        "different source-effect signatures.",
        "",
        "## Results",
        "",
        "| Representation | Cells | Collision cells | Separating pairs | "
        "Overpartition pairs | Collision-complete | Exact partition |",
        "|---|---:|---:|---:|---:|:---:|:---:|",
    ]
    for row in report["representations"]:
        lines.append(
            f"| {row['representation']} | {row['n_representation_cells']} | "
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
                "Collision completeness is a bounded result for this enumerated "
                "domain and authority family. It does not establish completeness "
                "for unenumerated calls, hidden effects, changed implementations, "
                "or a deployment policy language."
            ),
            "",
            (
                "Overpartition pairs are not unsafe by themselves; they identify "
                "representations that distinguish contexts with the same observed "
                "security effects and may therefore impose unnecessary policy or "
                "review burden."
            ),
            "",
            "## Integrity",
            "",
            f"- Source hash verification errors: {len(report['source_verification_errors'])}",
            f"- Execution errors: {report['execution_errors']}",
            f"- Empty source-effect sets: {report['empty_effect_sets']}",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> dict[str, Any]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    contexts, source_errors = execute_contexts()
    representation_names = list(contexts[0]["representations"])
    summaries: list[dict[str, Any]] = []
    witnesses: list[dict[str, Any]] = []
    for representation in representation_names:
        summary, representation_witnesses = analyze_representation(
            contexts, representation
        )
        summaries.append(summary)
        witnesses.extend(representation_witnesses)

    report = {
        "experiment": "finite_domain_effect_binding_validation",
        "status": "passed" if not source_errors else "failed",
        "benchmark": "AgentDojo v1.1.2",
        "n_contexts": len(contexts),
        "n_tools": len({row["tool_instance_key"] for row in contexts}),
        "contexts_per_tool": dict(
            sorted(Counter(row["tool_instance_key"] for row in contexts).items())
        ),
        "authority_family": (
            "all submultisets of the observed atomic-effect occurrences"
        ),
        "oracle": (
            "tool-specific committed effects reconstructed from fresh before/after "
            "AgentDojo state; independent of candidate representation values"
        ),
        "representations": summaries,
        "source_verification_errors": source_errors,
        "execution_errors": 0,
        "empty_effect_sets": 0,
        "n_witnesses": len(witnesses),
        "claim_boundary": (
            "Exhaustive only for the enumerated finite call domain, fixed "
            "AgentDojo v1.1.2 source hashes, source-specific effect oracle, and "
            "the declared finite submultiset authority family."
        ),
    }

    write_jsonl(CONTEXTS_PATH, contexts)
    write_jsonl(WITNESSES_PATH, witnesses)
    with SUMMARY_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    REPORT_JSON.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    REPORT_MD.write_text(render_report(report), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] != "passed":
        raise SystemExit(1)
    return report


if __name__ == "__main__":
    run()
