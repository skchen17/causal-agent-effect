#!/usr/bin/env python3
"""Replay official AgentDojo benign trajectories and census observable effects.

The oracle is deliberately independent of every candidate effect contract. It
executes each official ground-truth trajectory against an in-memory benchmark
environment and normalizes before/after state differences into logical effect
units. No external service or real tool is invoked.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import inspect
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


SCRIPT_PATH = Path(__file__).resolve()
ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *SCRIPT_PATH.parents)
    if (candidate / "paper/current-usenix").exists()
)
EVALUATION = (
    ROOT
    / "experiments/human-authority-and-causal-validation/evaluation/"
    "agentdojo-tool-effect-prevalence"
)
OUTPUT = (
    ROOT
    / "experiments/human-authority-and-causal-validation/results/"
    "agentdojo-tool-effect-prevalence"
)
PROTOCOL = EVALUATION / "protocol.json"
CALLS_JSONL = OUTPUT / "official-call-effects.jsonl"
WITNESSES_JSONL = OUTPUT / "compound-effect-witnesses.jsonl"
TOOLS_CSV = OUTPUT / "tool-effect-summary.csv"
REPORT_JSON = OUTPUT / "agentdojo-tool-effect-prevalence-report.json"
REPORT_MD = OUTPUT / "agentdojo-tool-effect-prevalence-report.md"
TABLE_TEX = OUTPUT / "table_agentdojo_effect_prevalence.tex"
PAPER_TABLE_TEX = ROOT / "paper/current-usenix/tables/table_agentdojo_effect_prevalence.tex"
VOLATILE_FIELDS = {"last_modified", "size", "timestamp"}
MIRROR_ROOTS = {
    ("calendar", "initial_events"),
    ("cloud_drive", "initial_files"),
    ("inbox", "initial_emails"),
    ("inbox", "sent"),
    ("inbox", "received"),
    ("inbox", "trash"),
    ("inbox", "drafts"),
}


def stable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return stable(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {
            str(key): stable(item)
            for key, item in sorted(value.items())
            if str(key) not in VOLATILE_FIELDS
        }
    if isinstance(value, (list, tuple)):
        return [stable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def canonical_json(value: Any) -> str:
    return json.dumps(stable(value), sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def added_rows(before: Iterable[Any], after: Iterable[Any]) -> list[Any]:
    before_counts = Counter(canonical_json(row) for row in before)
    after_by_key = {canonical_json(row): row for row in after}
    after_counts = Counter(canonical_json(row) for row in after)
    return [
        copy.deepcopy(after_by_key[key])
        for key, count in sorted((after_counts - before_counts).items())
        for _ in range(count)
    ]


def effect(
    kind: str,
    namespace: str,
    resource: str,
    *,
    target: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "effect": kind,
        "namespace": namespace,
        "resource": resource,
        "target": target,
        "details": stable(details or {}),
    }


def keyed(rows: list[dict[str, Any]], key: str = "id") -> dict[str, dict[str, Any]]:
    result = {}
    for index, row in enumerate(rows):
        identity = row.get(key, row.get("id_", index))
        result[str(identity)] = row
    return result


def calendar_effects(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    if "calendar" not in before:
        return []
    old = before["calendar"].get("events", {})
    new = after["calendar"].get("events", {})
    units = []
    for event_id in sorted(set(new) - set(old)):
        units.append(effect("calendar_event_created", "calendar", f"event:{event_id}"))
    for event_id in sorted(set(old) - set(new)):
        units.append(effect("calendar_event_deleted", "calendar", f"event:{event_id}"))
    for event_id in sorted(set(old) & set(new)):
        old_event, new_event = old[event_id], new[event_id]
        old_people = Counter(old_event.get("participants") or [])
        new_people = Counter(new_event.get("participants") or [])
        for person, count in sorted((new_people - old_people).items()):
            units.extend(
                effect(
                    "calendar_participant_added",
                    "calendar",
                    f"event:{event_id}",
                    target=str(person),
                )
                for _ in range(count)
            )
        for person, count in sorted((old_people - new_people).items()):
            units.extend(
                effect(
                    "calendar_participant_removed",
                    "calendar",
                    f"event:{event_id}",
                    target=str(person),
                )
                for _ in range(count)
            )
        changed = sorted(
            field
            for field in set(old_event) | set(new_event)
            if field != "participants" and old_event.get(field) != new_event.get(field)
        )
        if changed:
            units.append(
                effect(
                    "calendar_event_updated",
                    "calendar",
                    f"event:{event_id}",
                    details={"changed_fields": changed},
                )
            )
    return units


def inbox_effects(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    if "inbox" not in before:
        return []
    old = before["inbox"].get("emails", {})
    new = after["inbox"].get("emails", {})
    units = []
    for message_id in sorted(set(new) - set(old)):
        row = new[message_id]
        targets = list(row.get("recipients") or [])
        targets += list(row.get("cc") or [])
        targets += list(row.get("bcc") or [])
        targets = sorted(set(targets), key=str)
        if not targets:
            targets = [None]
        for target in targets:
            units.append(
                effect(
                    "email_delivered",
                    "inbox",
                    f"email:{message_id}",
                    target=None if target is None else str(target),
                    details={"subject": row.get("subject")},
                )
            )
    for message_id in sorted(set(old) - set(new)):
        units.append(effect("email_deleted", "inbox", f"email:{message_id}"))
    for message_id in sorted(set(old) & set(new)):
        if old[message_id].get("read") != new[message_id].get("read"):
            units.append(
                effect(
                    "email_read_state_changed",
                    "inbox",
                    f"email:{message_id}",
                    details={"read": new[message_id].get("read")},
                )
            )
    return units


def drive_effects(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    if "cloud_drive" not in before:
        return []
    old = before["cloud_drive"].get("files", {})
    new = after["cloud_drive"].get("files", {})
    units = []
    for file_id in sorted(set(new) - set(old)):
        units.append(effect("file_created", "cloud_drive", f"file:{file_id}"))
    for file_id in sorted(set(old) - set(new)):
        units.append(effect("file_deleted", "cloud_drive", f"file:{file_id}"))
    for file_id in sorted(set(old) & set(new)):
        old_row, new_row = old[file_id], new[file_id]
        old_acl = old_row.get("shared_with") or {}
        new_acl = new_row.get("shared_with") or {}
        for principal in sorted(set(old_acl) | set(new_acl)):
            if old_acl.get(principal) != new_acl.get(principal):
                units.append(
                    effect(
                        "file_permission_changed",
                        "cloud_drive",
                        f"file:{file_id}",
                        target=str(principal),
                        details={"permission": new_acl.get(principal)},
                    )
                )
        changed = sorted(
            field
            for field in set(old_row) | set(new_row)
            if field not in VOLATILE_FIELDS | {"shared_with"}
            and old_row.get(field) != new_row.get(field)
        )
        if changed:
            units.append(
                effect(
                    "file_updated",
                    "cloud_drive",
                    f"file:{file_id}",
                    details={"changed_fields": changed},
                )
            )
    return units


def banking_effects(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    units = []
    if "bank_account" in before:
        for field, kind in (
            ("transactions", "funds_transferred"),
            ("scheduled_transactions", "scheduled_transfer_changed"),
        ):
            old_rows = keyed(before["bank_account"].get(field, []))
            new_rows = keyed(after["bank_account"].get(field, []))
            for row_id in sorted(set(new_rows) - set(old_rows)):
                row = new_rows[row_id]
                units.append(
                    effect(
                        kind,
                        "bank_account",
                        f"{field}:{row_id}",
                        target=str(row.get("recipient")),
                    )
                )
            for row_id in sorted(set(old_rows) - set(new_rows)):
                units.append(effect(kind, "bank_account", f"{field}:{row_id}"))
            for row_id in sorted(set(old_rows) & set(new_rows)):
                if old_rows[row_id] != new_rows[row_id]:
                    changed = sorted(
                        key
                        for key in set(old_rows[row_id]) | set(new_rows[row_id])
                        if old_rows[row_id].get(key) != new_rows[row_id].get(key)
                    )
                    units.append(
                        effect(
                            kind,
                            "bank_account",
                            f"{field}:{row_id}",
                            target=str(new_rows[row_id].get("recipient")),
                            details={"changed_fields": changed},
                        )
                    )
    if "user_account" in before:
        for field in sorted(set(before["user_account"]) | set(after["user_account"])):
            if before["user_account"].get(field) != after["user_account"].get(field):
                units.append(
                    effect(
                        "account_attribute_changed",
                        "user_account",
                        f"account_field:{field}",
                        details={"field": field},
                    )
                )
    return units


def slack_effects(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    units = []
    if "slack" in before:
        old, new = before["slack"], after["slack"]
        for user in sorted(set(new.get("users", [])) - set(old.get("users", []))):
            units.append(effect("workspace_user_invited", "slack", f"user:{user}", target=str(user)))
        for user in sorted(set(old.get("user_channels", {})) | set(new.get("user_channels", {}))):
            old_channels = set(old.get("user_channels", {}).get(user, []))
            new_channels = set(new.get("user_channels", {}).get(user, []))
            for channel in sorted(new_channels - old_channels):
                units.append(
                    effect(
                        "channel_membership_added",
                        "slack",
                        f"channel:{channel}",
                        target=str(user),
                    )
                )
            for channel in sorted(old_channels - new_channels):
                units.append(
                    effect(
                        "channel_membership_removed",
                        "slack",
                        f"channel:{channel}",
                        target=str(user),
                    )
                )
        for user in sorted(set(old.get("user_inbox", {})) | set(new.get("user_inbox", {}))):
            for index, row in enumerate(
                added_rows(old.get("user_inbox", {}).get(user, []), new.get("user_inbox", {}).get(user, []))
            ):
                units.append(
                    effect(
                        "direct_message_delivered",
                        "slack",
                        f"direct_message:{digest(row)[:16]}:{index}",
                        target=str(user),
                    )
                )
        for channel in sorted(set(old.get("channel_inbox", {})) | set(new.get("channel_inbox", {}))):
            for index, row in enumerate(
                added_rows(old.get("channel_inbox", {}).get(channel, []), new.get("channel_inbox", {}).get(channel, []))
            ):
                units.append(
                    effect(
                        "channel_message_delivered",
                        "slack",
                        f"channel_message:{digest(row)[:16]}:{index}",
                        target=str(channel),
                    )
                )
    if "web" in before:
        old_web, new_web = before["web"], after["web"]
        changed_urls = {
            str(url)
            for url in set(old_web.get("web_content", {})) | set(new_web.get("web_content", {}))
            if old_web.get("web_content", {}).get(url) != new_web.get("web_content", {}).get(url)
        }
        for url in sorted(changed_urls):
            units.append(effect("webpage_published", "web", f"url:{url}", target=url))
        for url in added_rows(old_web.get("web_requests", []), new_web.get("web_requests", [])):
            if str(url) not in changed_urls:
                units.append(effect("external_web_request", "web", f"url:{url}", target=str(url)))
    return units


def reservation_effects(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    if "reservation" not in before or before["reservation"] == after["reservation"]:
        return []
    changed = sorted(
        field
        for field in set(before["reservation"]) | set(after["reservation"])
        if before["reservation"].get(field) != after["reservation"].get(field)
    )
    return [
        effect(
            "reservation_changed",
            "reservation",
            "active_reservation",
            target=str(after["reservation"].get("title") or "unknown"),
            details={"changed_fields": changed},
        )
    ]


def normalized_effects(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    units = []
    for extractor in (
        calendar_effects,
        inbox_effects,
        drive_effects,
        banking_effects,
        slack_effects,
        reservation_effects,
    ):
        units.extend(extractor(before, after))
    return sorted(units, key=canonical_json)


def raw_changed_paths(before: Any, after: Any, prefix: tuple[str, ...] = ()) -> list[str]:
    if prefix[:2] in MIRROR_ROOTS or (prefix and prefix[-1] in VOLATILE_FIELDS):
        return []
    if type(before) is not type(after):
        return [".".join(prefix)]
    if isinstance(before, dict):
        rows = []
        for key in sorted(set(before) | set(after), key=str):
            child = prefix + (str(key),)
            if key not in before or key not in after:
                if child[:2] not in MIRROR_ROOTS and str(key) not in VOLATILE_FIELDS:
                    rows.append(".".join(child))
            else:
                rows.extend(raw_changed_paths(before[key], after[key], child))
        return rows
    if isinstance(before, list):
        return [] if before == after else [".".join(prefix)]
    return [] if before == after else [".".join(prefix)]


def source_evidence(tool: Any) -> dict[str, Any]:
    path = Path(inspect.getsourcefile(tool.run) or "")
    lines, start = inspect.getsourcelines(tool.run)
    return {
        "module": tool.run.__module__,
        "function": tool.run.__name__,
        "start_line": start,
        "source_file_name": path.name,
        "source_file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "function_source_sha256": hashlib.sha256("".join(lines).encode()).hexdigest(),
    }


def execute_all() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from agentdojo.functions_runtime import FunctionsRuntime
    from agentdojo.task_suite.load_suites import get_suite

    calls = []
    inventory = []
    call_index = 0
    for suite_name in ("banking", "slack", "travel", "workspace"):
        suite = get_suite("v1.1.2", suite_name)
        runtime = FunctionsRuntime(suite.tools)
        tools = {tool.name: tool for tool in suite.tools}
        used_tools = set()
        for task_id, task in sorted(
            suite.user_tasks.items(), key=lambda item: int(item[0].rsplit("_", 1)[1])
        ):
            environment = task.init_environment(
                suite.load_and_inject_default_environment({})
            )
            trajectory = task.ground_truth(environment)
            for step, call in enumerate(trajectory):
                before = stable(environment)
                _output, error = runtime.run_function(
                    environment, call.function, copy.deepcopy(call.args)
                )
                after = stable(environment)
                units = normalized_effects(before, after)
                paths = raw_changed_paths(before, after)
                targets = sorted({row["target"] for row in units if row["target"] is not None})
                kinds = sorted({row["effect"] for row in units})
                namespaces = sorted({row["namespace"] for row in units})
                row = {
                    "call_id": f"official-call-{call_index:03d}",
                    "suite": suite_name,
                    "task_id": task_id,
                    "trajectory_step": step,
                    "tool_name": call.function,
                    "tool_instance_key": f"{suite_name}/{call.function}",
                    "arguments": stable(call.args),
                    "runtime_error": error,
                    "call_signature": digest(
                        {
                            "suite": suite_name,
                            "task_id": task_id,
                            "step": step,
                            "tool": call.function,
                            "arguments": call.args,
                        }
                    ),
                    "effect_signature": digest(units),
                    "normalized_raw_changed_paths": paths,
                    "effect_units": units,
                    "n_effect_units": len(units),
                    "effectful": bool(units),
                    "compound": len(units) > 1,
                    "heterogeneous_compound": len(kinds) > 1,
                    "multi_target": len(targets) > 1,
                    "cross_namespace": len(namespaces) > 1,
                    "effect_kinds": kinds,
                    "targets": targets,
                    "namespaces": namespaces,
                }
                calls.append(row)
                used_tools.add(call.function)
                call_index += 1
        for name, tool in sorted(tools.items()):
            inventory.append(
                {
                    "suite": suite_name,
                    "tool_name": name,
                    "tool_instance_key": f"{suite_name}/{name}",
                    "observed_in_official_benign_trajectory": name in used_tools,
                    "source_evidence": source_evidence(tool),
                }
            )
    return calls, inventory


def ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def build_report(calls: list[dict[str, Any]], inventory: list[dict[str, Any]], protocol: dict[str, Any]) -> dict[str, Any]:
    errors = [row for row in calls if row["runtime_error"] is not None]
    source_manifest_hash = digest(
        [
            {
                "tool_instance_key": row["tool_instance_key"],
                "source_evidence": row["source_evidence"],
            }
            for row in sorted(inventory, key=lambda item: item["tool_instance_key"])
        ]
    )
    source_manifest_match = source_manifest_hash == protocol["execution"][
        "expected_inventory_source_manifest_sha256"
    ]
    observed_keys = {row["tool_instance_key"] for row in calls}
    effectful_calls = [row for row in calls if row["effectful"]]
    effectful_tools = {row["tool_instance_key"] for row in effectful_calls}
    compound = [row for row in effectful_calls if row["compound"]]
    heterogeneous = [row for row in effectful_calls if row["heterogeneous_compound"]]
    multi_target = [row for row in effectful_calls if row["multi_target"]]
    cross_namespace = [row for row in effectful_calls if row["cross_namespace"]]
    suites = Counter(row["suite"] for row in calls)
    task_keys = {(row["suite"], row["task_id"]) for row in calls}
    return {
        "experiment": "agentdojo_tool_effect_prevalence",
        "status": (
            "passed"
            if not errors
            and len(calls) == 339
            and len(task_keys) == 97
            and source_manifest_match
            else "failed"
        ),
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": protocol["protocol_sha256"],
        "analysis_status": protocol["analysis_status"],
        "benchmark": "AgentDojo v1.1.2",
        "n_suites": 4,
        "n_tasks": len(task_keys),
        "n_official_calls": len(calls),
        "n_runtime_errors": len(errors),
        "calls_by_suite": dict(sorted(suites.items())),
        "tool_inventory": {
            "n_tool_instances": len(inventory),
            "n_observed_tool_instances": len(observed_keys),
            "coverage": ratio(len(observed_keys), len(inventory)),
            "n_unobserved_tool_instances": len(inventory) - len(observed_keys),
        },
        "prevalence": {
            "n_effectful_calls": len(effectful_calls),
            "effectful_call_rate_all_calls": ratio(len(effectful_calls), len(calls)),
            "n_effectful_observed_tools": len(effectful_tools),
            "effectful_observed_tool_rate": ratio(len(effectful_tools), len(observed_keys)),
            "n_compound_calls": len(compound),
            "compound_rate_all_calls": ratio(len(compound), len(calls)),
            "compound_rate_effectful_calls": ratio(len(compound), len(effectful_calls)),
            "n_heterogeneous_compound_calls": len(heterogeneous),
            "heterogeneous_rate_effectful_calls": ratio(len(heterogeneous), len(effectful_calls)),
            "n_multi_target_calls": len(multi_target),
            "multi_target_rate_effectful_calls": ratio(len(multi_target), len(effectful_calls)),
            "n_cross_namespace_calls": len(cross_namespace),
            "cross_namespace_rate_effectful_calls": ratio(len(cross_namespace), len(effectful_calls)),
            "maximum_effect_units_per_call": max((row["n_effect_units"] for row in calls), default=0),
        },
        "effect_kind_counts": dict(sorted(Counter(kind for row in calls for kind in row["effect_kinds"]).items())),
        "source_evidence": {
            "all_inventory_entries_hashed": all(row["source_evidence"]["source_file_sha256"] for row in inventory),
            "inventory_source_manifest_sha256": source_manifest_hash,
            "inventory_source_manifest_matches_protocol": source_manifest_match,
            "candidate_contract_used_by_oracle": False,
            "attack_or_outcome_labels_used_by_oracle": False,
            "execution_errors": [row["call_id"] for row in errors],
        },
        "limitations": [
            "Official benign trajectories cover only the observed 55 of 74 tool instances.",
            "Logical effect normalization is a frozen benchmark-state oracle, not independent human certification.",
            "The result measures AgentDojo v1.1.2 and does not estimate ecosystem-wide prevalence.",
            "No-op calls are retained; absence of a state delta in one reachable state does not prove a tool is read-only.",
        ],
        "claim_boundary": protocol["claim_boundary"],
    }


def write_outputs(calls: list[dict[str, Any]], inventory: list[dict[str, Any]], report: dict[str, Any]) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    CALLS_JSONL.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in calls), encoding="utf-8"
    )
    witnesses = sorted(
        (row for row in calls if row["compound"]),
        key=lambda row: (-row["n_effect_units"], row["call_id"]),
    )
    WITNESSES_JSONL.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in witnesses), encoding="utf-8"
    )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in calls:
        grouped[row["tool_instance_key"]].append(row)
    with TOOLS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "tool_instance_key",
                "observed",
                "n_calls",
                "n_effectful_calls",
                "n_compound_calls",
                "n_heterogeneous_calls",
                "n_multi_target_calls",
                "max_effect_units",
                "effect_kinds",
                "source_file_sha256",
                "function_source_sha256",
            ],
        )
        writer.writeheader()
        for item in sorted(inventory, key=lambda row: row["tool_instance_key"]):
            rows = grouped[item["tool_instance_key"]]
            writer.writerow(
                {
                    "tool_instance_key": item["tool_instance_key"],
                    "observed": item["observed_in_official_benign_trajectory"],
                    "n_calls": len(rows),
                    "n_effectful_calls": sum(row["effectful"] for row in rows),
                    "n_compound_calls": sum(row["compound"] for row in rows),
                    "n_heterogeneous_calls": sum(row["heterogeneous_compound"] for row in rows),
                    "n_multi_target_calls": sum(row["multi_target"] for row in rows),
                    "max_effect_units": max((row["n_effect_units"] for row in rows), default=0),
                    "effect_kinds": ";".join(sorted({kind for row in rows for kind in row["effect_kinds"]})),
                    "source_file_sha256": item["source_evidence"]["source_file_sha256"],
                    "function_source_sha256": item["source_evidence"]["function_source_sha256"],
                }
            )
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    p = report["prevalence"]
    inv = report["tool_inventory"]
    REPORT_MD.write_text(
        "\n".join(
            [
                "# AgentDojo Tool-Effect Prevalence Census",
                "",
                f"- Status: `{report['status']}`",
                f"- Population: `{report['n_tasks']}` official benign tasks and `{report['n_official_calls']}` sequentially replayed calls.",
                f"- Tool coverage: `{inv['n_observed_tool_instances']}/{inv['n_tool_instances']} = {inv['coverage']:.3f}`.",
                f"- Effectful calls: `{p['n_effectful_calls']}/{report['n_official_calls']} = {p['effectful_call_rate_all_calls']:.3f}`.",
                f"- Effectful observed tools: `{p['n_effectful_observed_tools']}/{inv['n_observed_tool_instances']} = {p['effectful_observed_tool_rate']:.3f}`.",
                f"- Compound calls: `{p['n_compound_calls']}/{p['n_effectful_calls']} = {p['compound_rate_effectful_calls']:.3f}` of effectful calls.",
                f"- Heterogeneous compound calls: `{p['n_heterogeneous_compound_calls']}/{p['n_effectful_calls']} = {p['heterogeneous_rate_effectful_calls']:.3f}`.",
                f"- Multi-target calls: `{p['n_multi_target_calls']}/{p['n_effectful_calls']} = {p['multi_target_rate_effectful_calls']:.3f}`.",
                f"- Cross-namespace calls: `{p['n_cross_namespace_calls']}/{p['n_effectful_calls']} = {p['cross_namespace_rate_effectful_calls']:.3f}`.",
                f"- Maximum logical units in one call: `{p['maximum_effect_units_per_call']}`.",
                "",
                "## Interpretation",
                "",
                "The official benign trajectories contain concrete source-executed examples in which one tool call changes multiple independently addressable objects, principals, or subsystems. This establishes within-benchmark prevalence of the representation problem; it does not establish ecosystem-wide prevalence or contract completeness.",
                "",
                "## Evidence Boundary",
                "",
                report["claim_boundary"],
                "",
                "## Limitations",
                "",
                *[f"- {item}" for item in report["limitations"]],
                "",
            ]
        ),
        encoding="utf-8",
    )
    table_text = "\n".join(
        [
                "\\begin{table}[t]",
                "\\centering",
                "\\small",
                "\\caption{Source-executed effects in all official AgentDojo v1.1.2 benign trajectories. Rates after the first row use effectful calls as the denominator.}",
                "\\label{tab:agentdojo-effect-prevalence}",
                "\\begin{tabular}{lrr}",
                "\\toprule",
                "Measure & Count & Rate \\\\",
                "\\midrule",
                f"Effectful calls & {p['n_effectful_calls']}/{report['n_official_calls']} & {p['effectful_call_rate_all_calls']:.3f} \\\\",
                f"Compound effects & {p['n_compound_calls']}/{p['n_effectful_calls']} & {p['compound_rate_effectful_calls']:.3f} \\\\",
                f"Heterogeneous effects & {p['n_heterogeneous_compound_calls']}/{p['n_effectful_calls']} & {p['heterogeneous_rate_effectful_calls']:.3f} \\\\",
                f"Multiple targets & {p['n_multi_target_calls']}/{p['n_effectful_calls']} & {p['multi_target_rate_effectful_calls']:.3f} \\\\",
                f"Cross-subsystem effects & {p['n_cross_namespace_calls']}/{p['n_effectful_calls']} & {p['cross_namespace_rate_effectful_calls']:.3f} \\\\",
                "\\bottomrule",
                "\\end{tabular}",
                "\\end{table}",
                "",
        ]
    )
    TABLE_TEX.write_text(table_text, encoding="utf-8")
    PAPER_TABLE_TEX.write_text(table_text, encoding="utf-8")


def main() -> int:
    if not PROTOCOL.exists():
        raise SystemExit("missing protocol; run freeze_agentdojo_tool_effect_prevalence_protocol.py")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    payload = dict(protocol)
    claimed_hash = payload.pop("protocol_sha256")
    if digest(payload) != claimed_hash:
        raise SystemExit("protocol hash mismatch")
    calls, inventory = execute_all()
    report = build_report(calls, inventory, protocol)
    write_outputs(calls, inventory, report)
    print(json.dumps({"status": report["status"], "calls": len(calls), "output": str(OUTPUT)}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
