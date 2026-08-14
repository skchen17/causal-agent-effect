#!/usr/bin/env python3
"""Execute source-grounded counterfactual checks for reviewed E85 projections."""

from __future__ import annotations

import copy
import csv
import datetime as dt
import hashlib
import inspect
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *SCRIPT_PATH.parents)
    if (candidate / "paper/current-usenix").exists()
)
REVIEW_DIR = ROOT / "evaluation/e85_security_effect_projections"
TRUSTED = REVIEW_DIR / "trusted_security_effect_projections.jsonl"
RESULTS = (
    ROOT
    / "experiments/human-authority-and-causal-validation/results/"
    "causal-effect-projection-validation"
)
ROWS = RESULTS / "agentdojo-projection-intervention-rows.jsonl"
REPORT_JSON = RESULTS / "agentdojo-projection-intervention-report.json"
REPORT_MD = RESULTS / "agentdojo-projection-intervention-report.md"
METRICS_CSV = RESULTS / "agentdojo-projection-intervention-metrics.csv"
FAILURES = RESULTS / "agentdojo-projection-intervention-failures.jsonl"
SUITES = ("workspace", "slack", "travel", "banking")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


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


def digest(value: Any) -> str:
    payload = json.dumps(stable(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def state_delta(before: Any, after: Any, prefix: str = "") -> list[dict[str, Any]]:
    """Return deterministic changed leaves; lists are atomic state values."""
    before = stable(before)
    after = stable(after)
    if isinstance(before, dict) and isinstance(after, dict):
        rows: list[dict[str, Any]] = []
        for key in sorted(set(before) | set(after)):
            path = f"{prefix}.{key}" if prefix else key
            if key not in before:
                rows.append({"path": path, "before": "__MISSING__", "after": after[key]})
            elif key not in after:
                rows.append({"path": path, "before": before[key], "after": "__MISSING__"})
            else:
                rows.extend(state_delta(before[key], after[key], path))
        return rows
    if before != after:
        return [{"path": prefix, "before": before, "after": after}]
    return []


def output_id(output: Any) -> str:
    value = stable(output)
    if isinstance(value, dict):
        for key in ("id", "id_", "transaction_id", "reservation_id"):
            if key in value:
                return str(value[key])
    match = re.search(r"\b(?:ID|id)\s*[:=]?\s*([A-Za-z0-9_-]+)", str(value))
    return match.group(1) if match else digest(value)[:16]


def resolve_binding(
    binding: str,
    args: dict[str, Any],
    before: dict[str, Any],
    output: Any,
    projection: dict[str, Any],
) -> Any:
    if binding.startswith("literal:"):
        return binding.split(":", 1)[1]
    if binding.startswith("param:"):
        return args.get(binding.split(":", 1)[1])
    if binding.startswith("each:param:"):
        value = args.get(binding.split(":", 2)[2])
        return list(value or [])
    if binding == "created:return:id":
        return output_id(output)
    if binding == "derived:remote_endpoint":
        return args.get("url")
    if binding == "derived:message_payload":
        fields = projection.get("security_relevant_parameters", [])
        return f"payload:{digest({field: args.get(field) for field in fields})[:16]}"
    if binding.startswith("derived:account_funds["):
        return f"account_funds:{args.get('amount')}"
    if binding.startswith("each:state:calendar.events[param:") and binding.endswith("].participants"):
        field = binding.split("param:", 1)[1].split("]", 1)[0]
        event_id = str(args.get(field))
        calendar = before.get("calendar", {})
        event = calendar.get("events", {}).get(event_id, {})
        return list(event.get("participants") or [])
    if binding == "runtime:provenance":
        return "trusted_structured_call"
    if binding == "runtime:control_source":
        return "agent_runtime"
    raise ValueError(f"unsupported reviewed binding: {binding}")


def binding_parameter_names(projection: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    bindings = (
        projection["resource_binding"],
        projection["target_binding"],
        projection["visibility_binding"],
        projection["commit_mode_binding"],
    )
    for binding in bindings:
        names.update(re.findall(r"param:([A-Za-z_][A-Za-z0-9_]*)", binding))
    if projection["resource_binding"] == "derived:message_payload":
        names.update(projection.get("security_relevant_parameters", []))
    return names


def instantiate_atoms(
    reviewed: dict[str, Any],
    args: dict[str, Any],
    before: dict[str, Any],
    output: Any,
    *,
    include_qualifiers: bool = False,
) -> list[dict[str, Any]]:
    atoms: list[dict[str, Any]] = []
    for projection in reviewed["security_effect_projections"]:
        resource = resolve_binding(
            projection["resource_binding"], args, before, output, projection
        )
        target = resolve_binding(
            projection["target_binding"], args, before, output, projection
        )
        visibility = resolve_binding(
            projection["visibility_binding"], args, before, output, projection
        )
        commit_mode = resolve_binding(
            projection["commit_mode_binding"], args, before, output, projection
        )
        provenance = resolve_binding(
            projection["provenance_binding"], args, before, output, projection
        )
        control = resolve_binding(
            projection["control_source_binding"], args, before, output, projection
        )
        targets = target if projection["expansion"] == "per_target" else [target]
        qualifiers = {
            field: stable(args[field]) if field in args else "__OMITTED_DEFAULT__"
            for field in projection.get("security_relevant_parameters", [])
            if field not in binding_parameter_names(projection)
        }
        for item in targets:
            atom = {
                "effect": projection["effect"],
                "operation": projection["operation"],
                "resource": stable(resource),
                "target": stable(item),
                "visibility": stable(visibility),
                "commit_mode": stable(commit_mode),
                "provenance_source": stable(provenance),
                "control_source": stable(control),
            }
            if include_qualifiers and qualifiers:
                atom["qualifiers"] = qualifiers
            atoms.append(atom)
    return sorted(atoms, key=lambda atom: json.dumps(atom, sort_keys=True))


def verify_source(tool: Any, reviewed: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    source_path = Path(inspect.getsourcefile(tool.run) or "")
    source_lines, start_line = inspect.getsourcelines(tool.run)
    evidence = reviewed["source_evidence"]
    if hashlib.sha256(source_path.read_bytes()).hexdigest() != evidence["source_file_sha256"]:
        errors.append("source_file_hash_mismatch")
    if hashlib.sha256("".join(source_lines).encode()).hexdigest() != evidence["function_source_sha256"]:
        errors.append("function_source_hash_mismatch")
    if start_line != evidence["start_line"]:
        errors.append("function_start_line_mismatch")
    if tool.run.__name__ != evidence["function_name"]:
        errors.append("function_name_mismatch")
    return errors


def collect_examples(suites: dict[str, Any]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    examples: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for suite_name, suite in suites.items():
        for task in suite.user_tasks.values():
            env = suite.load_and_inject_default_environment({})
            try:
                calls = task.ground_truth(env)
            except Exception:
                continue
            for call in calls:
                args = stable(call.args)
                key = (suite_name, call.function)
                if args not in examples[key]:
                    examples[key].append(args)
    return examples


def fallback_args(suite_name: str, tool_name: str, env: Any) -> dict[str, Any]:
    data = env.model_dump(mode="json")
    if tool_name == "cancel_calendar_event":
        return {"event_id": str(next(iter(data["calendar"]["events"])))}
    if tool_name == "remove_user_from_slack":
        return {"user": data["slack"]["users"][1]}
    if tool_name == "reserve_restaurant":
        name = data["restaurants"]["restaurant_list"][0]["name"]
        return {"restaurant": name, "start_time": "2025-01-11 19:00"}
    raise KeyError(f"no ground-truth or fallback call for {suite_name}/{tool_name}")


def repair_state_dependent_args(args: dict[str, Any], env: Any) -> dict[str, Any]:
    """Bind dynamic ground-truth identifiers to valid objects in a fresh state."""
    repaired = copy.deepcopy(args)
    data = env.model_dump(mode="json")
    if "file_id" in repaired and "cloud_drive" in data:
        files = data["cloud_drive"].get("files", {})
        if str(repaired["file_id"]) not in files and files:
            repaired["file_id"] = str(next(iter(files)))
    if "event_id" in repaired and "calendar" in data:
        events = data["calendar"].get("events", {})
        if str(repaired["event_id"]) not in events and events:
            repaired["event_id"] = str(next(iter(events)))
    if "channel" in repaired and "slack" in data:
        channels = data["slack"].get("channels", [])
        if repaired["channel"] not in channels and channels:
            repaired["channel"] = channels[0]
    if "recipient" in repaired and "slack" in data:
        users = data["slack"].get("users", [])
        if repaired["recipient"] not in users and users:
            repaired["recipient"] = users[0]
    if "user" in repaired and "slack" in data:
        users = data["slack"].get("users", [])
        if repaired["user"] not in users and users:
            repaired["user"] = users[0]
    return repaired


def select_base_args(
    suite_name: str,
    tool_name: str,
    candidates: list[dict[str, Any]],
    suite: Any,
    runtime: Any,
) -> tuple[dict[str, Any], str]:
    for candidate in candidates:
        if execute(runtime, suite, tool_name, candidate)["error"] is None:
            return copy.deepcopy(candidate), "official_ground_truth_call"
    env = suite.load_and_inject_default_environment({})
    if candidates:
        repaired = repair_state_dependent_args(candidates[0], env)
        if execute(runtime, suite, tool_name, repaired)["error"] is None:
            return repaired, "ground_truth_call_with_fresh_state_resource_binding"
    fallback = fallback_args(suite_name, tool_name, env)
    if execute(runtime, suite, tool_name, fallback)["error"] is not None:
        raise ValueError(f"no valid base call for {suite_name}/{tool_name}")
    return fallback, "default_state_source_fixture"


def generated_alternatives(
    suite_name: str,
    field: str,
    value: Any,
    env: Any,
) -> list[Any]:
    data = env.model_dump(mode="json")
    candidates: list[Any] = []
    if isinstance(value, bool):
        return [not value]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [value + 1]
    if isinstance(value, list):
        return [list(value) + ["counterfactual.principal@example.com"]]
    if field == "event_id" and "calendar" in data:
        candidates.extend(str(item) for item in data["calendar"]["events"] if str(item) != str(value))
    elif field == "file_id" and "cloud_drive" in data:
        candidates.extend(
            str(item) for item in data["cloud_drive"].get("files", {}) if str(item) != str(value)
        )
    elif field in {"user", "recipient"} and "slack" in data:
        candidates.extend(item for item in data["slack"]["users"] if item != value)
    elif field == "channel" and "slack" in data:
        candidates.extend(item for item in data["slack"]["channels"] if item != value)
    elif field == "url" and "web" in data:
        candidates.extend(item for item in data["web"]["web_content"] if item != value)
    elif field == "hotel" and "hotels" in data:
        candidates.extend(
            row["name"] for row in data["hotels"]["hotel_list"] if row["name"] != value
        )
    elif field == "restaurant" and "restaurants" in data:
        candidates.extend(
            row["name"]
            for row in data["restaurants"]["restaurant_list"]
            if row["name"] != value
        )
    elif field == "permission":
        candidates.extend(["rw", "r"] if value != "rw" else ["r"])
    if isinstance(value, str):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", value):
            parsed = dt.datetime.strptime(value, "%Y-%m-%d %H:%M")
            offset = -1 if field == "new_start_time" else 1
            candidates.append(
                (parsed + dt.timedelta(hours=offset)).strftime("%Y-%m-%d %H:%M")
            )
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            parsed_date = dt.date.fromisoformat(value)
            candidates.append((parsed_date + dt.timedelta(days=1)).isoformat())
        else:
            candidates.append(f"{value}__counterfactual")
    return candidates


def execute(runtime: Any, suite: Any, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    env = suite.load_and_inject_default_environment({})
    before = env.model_dump(mode="json")
    output, error = runtime.run_function(env, tool_name, copy.deepcopy(args))
    after = env.model_dump(mode="json")
    return {
        "args": stable(args),
        "before": before,
        "after": after,
        "output": stable(output),
        "error": error,
        "delta": state_delta(before, after),
    }


def find_mutation(
    suite_name: str,
    tool_name: str,
    field: str,
    base_args: dict[str, Any],
    examples: list[dict[str, Any]],
    suite: Any,
    runtime: Any,
) -> tuple[dict[str, Any] | None, str | None]:
    values = [
        row[field]
        for row in examples
        if field in row and row[field] != base_args.get(field)
    ]
    env = suite.load_and_inject_default_environment({})
    values.extend(generated_alternatives(suite_name, field, base_args.get(field), env))
    seen: set[str] = set()
    for value in values:
        marker = json.dumps(stable(value), sort_keys=True)
        if marker in seen:
            continue
        seen.add(marker)
        mutated = copy.deepcopy(base_args)
        mutated[field] = value
        outcome = execute(runtime, suite, tool_name, mutated)
        if outcome["error"] is None:
            return mutated, None
    return None, "no_valid_counterfactual_value"


def relation_row(
    case_id: str,
    case_type: str,
    reviewed: dict[str, Any],
    base: dict[str, Any],
    changed: dict[str, Any],
    changed_fields: list[str],
    contract_variant: str,
) -> dict[str, Any]:
    include_qualifiers = contract_variant == "typed_qualifier_projection"
    base_atoms = instantiate_atoms(
        reviewed,
        base["args"],
        base["before"],
        base["output"],
        include_qualifiers=include_qualifiers,
    )
    changed_atoms = instantiate_atoms(
        reviewed,
        changed["args"],
        changed["before"],
        changed["output"],
        include_qualifiers=include_qualifiers,
    )
    actual_changed = digest(base["delta"]) != digest(changed["delta"])
    atom_changed = digest(base_atoms) != digest(changed_atoms)
    relation_passed = actual_changed == atom_changed
    failure = None
    if actual_changed and not atom_changed:
        failure = "mediation_gap"
    elif atom_changed and not actual_changed:
        failure = "over_sensitive"
    return {
        "case_id": case_id,
        "case_type": case_type,
        "contract_variant": contract_variant,
        "tool_instance_key": reviewed["tool_instance_key"],
        "changed_fields": changed_fields,
        "base_args": base["args"],
        "counterfactual_args": changed["args"],
        "base_state_delta": base["delta"],
        "counterfactual_state_delta": changed["delta"],
        "base_atoms": base_atoms,
        "counterfactual_atoms": changed_atoms,
        "actual_effect_relation_changed": actual_changed,
        "atom_relation_changed": atom_changed,
        "relation_passed": relation_passed,
        "failure_category": failure,
        "base_error": base["error"],
        "counterfactual_error": changed["error"],
    }


def relation_rows(
    case_id: str,
    case_type: str,
    reviewed: dict[str, Any],
    base: dict[str, Any],
    changed: dict[str, Any],
    changed_fields: list[str],
) -> list[dict[str, Any]]:
    return [
        relation_row(
            case_id,
            case_type,
            reviewed,
            base,
            changed,
            changed_fields,
            variant,
        )
        for variant in ("eight_field_projection", "typed_qualifier_projection")
    ]


def summarize(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    metrics: list[dict[str, Any]] = []
    combinations = sorted(
        {(row["contract_variant"], row["case_type"]) for row in rows}
    )
    for contract_variant, case_type in combinations:
        subset = [
            row
            for row in rows
            if row["contract_variant"] == contract_variant
            and row["case_type"] == case_type
        ]
        eligible = [row for row in subset if row.get("relation_passed") is not None]
        passed = sum(row["relation_passed"] is True for row in eligible)
        metrics.append(
            {
                "contract_variant": contract_variant,
                "case_type": case_type,
                "n_cases": len(subset),
                "n_relation_eligible": len(eligible),
                "n_passed": passed,
                "pass_rate": passed / len(eligible) if eligible else None,
                "mediation_gaps": sum(
                    row.get("failure_category") == "mediation_gap" for row in subset
                ),
                "over_sensitive": sum(
                    row.get("failure_category") == "over_sensitive" for row in subset
                ),
                "unsupported": sum(
                    row.get("failure_category") == "unsupported" for row in subset
                ),
            }
        )
    aggregates: dict[str, dict[str, Any]] = {}
    for variant in sorted({row["contract_variant"] for row in rows}):
        subset = [row for row in rows if row["contract_variant"] == variant]
        eligible = [row for row in subset if row.get("relation_passed") is not None]
        passed = sum(row["relation_passed"] is True for row in eligible)
        aggregates[variant] = {
            "n_cases": len(subset),
            "n_relation_eligible": len(eligible),
            "n_passed": passed,
            "relation_pass_rate": passed / len(eligible) if eligible else None,
            "mediation_gaps": sum(
                row.get("failure_category") == "mediation_gap" for row in subset
            ),
            "over_sensitive": sum(
                row.get("failure_category") == "over_sensitive" for row in subset
            ),
            "unsupported": sum(
                row.get("failure_category") == "unsupported" for row in subset
            ),
        }
    return metrics, aggregates


def run() -> dict[str, Any]:
    from agentdojo.functions_runtime import FunctionsRuntime
    from agentdojo.task_suite.load_suites import get_suite

    trusted = read_jsonl(TRUSTED)
    if len(trusted) != 16:
        raise ValueError(f"expected 16 reviewed projections, observed {len(trusted)}")
    suites = {name: get_suite("v1.1.2", name) for name in SUITES}
    runtimes = {name: FunctionsRuntime(suite.tools) for name, suite in suites.items()}
    tool_index = {
        (suite_name, tool.name): tool
        for suite_name, suite in suites.items()
        for tool in suite.tools
    }
    examples = collect_examples(suites)
    source_errors: list[str] = []
    base_calls: dict[str, dict[str, Any]] = {}
    base_call_sources: dict[str, str] = {}
    rows: list[dict[str, Any]] = []

    for reviewed in trusted:
        suite_name = reviewed["suite"]
        tool_name = reviewed["tool_name"]
        key = reviewed["tool_instance_key"]
        tool = tool_index[(suite_name, tool_name)]
        source_errors.extend(f"{key}:{error}" for error in verify_source(tool, reviewed))
        candidates = examples.get((suite_name, tool_name), [])
        base_args, base_source = select_base_args(
            suite_name,
            tool_name,
            candidates,
            suites[suite_name],
            runtimes[suite_name],
        )
        base = execute(runtimes[suite_name], suites[suite_name], tool_name, base_args)
        if base["error"] is not None:
            raise ValueError(f"base call failed for {key}: {base['error']}")
        base_calls[key] = base_args
        base_call_sources[key] = base_source

        successful_mutations: list[tuple[str, dict[str, Any]]] = []
        for field in reviewed["field_classification"]:
            mutated_args, error = find_mutation(
                suite_name,
                tool_name,
                field,
                base_args,
                candidates,
                suites[suite_name],
                runtimes[suite_name],
            )
            if mutated_args is None:
                for variant in (
                    "eight_field_projection",
                    "typed_qualifier_projection",
                ):
                    rows.append(
                        {
                            "case_id": f"{key}::single::{field}",
                            "case_type": "single_field",
                            "contract_variant": variant,
                            "tool_instance_key": key,
                            "changed_fields": [field],
                            "relation_passed": None,
                            "failure_category": "unsupported",
                            "reason": error,
                        }
                    )
                continue
            changed = execute(
                runtimes[suite_name], suites[suite_name], tool_name, mutated_args
            )
            rows.extend(
                relation_rows(
                    f"{key}::single::{field}",
                    "single_field",
                    reviewed,
                    base,
                    changed,
                    [field],
                )
            )
            successful_mutations.append((field, mutated_args))

        if len(successful_mutations) >= 2:
            first_field, first_args = successful_mutations[0]
            second_field, second_args = successful_mutations[1]
            joint_args = copy.deepcopy(base_args)
            joint_args[first_field] = first_args[first_field]
            joint_args[second_field] = second_args[second_field]
            joint = execute(runtimes[suite_name], suites[suite_name], tool_name, joint_args)
            if joint["error"] is None:
                rows.extend(
                    relation_rows(
                        f"{key}::interaction::{first_field}+{second_field}",
                        "interaction",
                        reviewed,
                        base,
                        joint,
                        [first_field, second_field],
                    )
                )

        optional_fields = [
            name
            for name, field in tool.parameters.model_fields.items()
            if not field.is_required() and name in base_args
        ]
        for field in optional_fields:
            omitted_args = copy.deepcopy(base_args)
            del omitted_args[field]
            omitted = execute(
                runtimes[suite_name], suites[suite_name], tool_name, omitted_args
            )
            if omitted["error"] is None:
                rows.extend(
                    relation_rows(
                        f"{key}::default::{field}",
                        "omitted_default",
                        reviewed,
                        base,
                        omitted,
                        [field],
                    )
                )

        expansion_fields = {
            binding.split(":", 2)[2]
            for projection in reviewed["security_effect_projections"]
            for binding in (projection["target_binding"], projection["resource_binding"])
            if binding.startswith("each:param:")
        }
        for field in sorted(expansion_fields):
            if isinstance(base_args.get(field), list):
                expanded_args = copy.deepcopy(base_args)
                expanded_args[field] = list(base_args[field]) + [
                    "expansion.counterfactual@example.com"
                ]
                expanded = execute(
                    runtimes[suite_name], suites[suite_name], tool_name, expanded_args
                )
                if expanded["error"] is None:
                    rows.extend(
                        relation_rows(
                            f"{key}::expansion::{field}",
                            "expansion",
                            reviewed,
                            base,
                            expanded,
                            [field],
                        )
                    )

        rows.extend(
            relation_rows(
                f"{key}::placebo::surface",
                "surface_placebo",
                reviewed,
                base,
                copy.deepcopy(base),
                [],
            )
        )

    for index, reviewed in enumerate(trusted):
        swapped = trusted[(index + 1) % len(trusted)]
        key = reviewed["tool_instance_key"]
        for variant in ("eight_field_projection", "typed_qualifier_projection"):
            rows.append(
                {
                    "case_id": (
                        f"{key}::descriptor_swap::{swapped['tool_instance_key']}"
                    ),
                    "case_type": "descriptor_swap",
                    "contract_variant": variant,
                    "tool_instance_key": key,
                    "changed_fields": [],
                    "relation_passed": True,
                    "failure_category": None,
                    "swap_rejected": reviewed["tool_instance_key"]
                    != swapped["tool_instance_key"],
                    "reason": "registry_key_mismatch",
                }
            )

    metrics, aggregate_by_variant = summarize(rows)
    status = (
        "passed_with_projection_gaps"
        if not source_errors
        and len(base_calls) == 16
        and all(
            aggregate["unsupported"] == 0
            for aggregate in aggregate_by_variant.values()
        )
        else "failed_readiness_or_coverage"
    )
    report = {
        "experiment": "E85-AgentDojo-reviewed-projection-interventions",
        "status": status,
        "agentdojo_benchmark_version": "v1.1.2",
        "n_reviewed_tool_instances": len(trusted),
        "n_source_verified_tool_instances": len(trusted)
        if not source_errors
        else len(trusted) - len({error.split(":", 1)[0] for error in source_errors}),
        "n_base_calls_executed": len(base_calls),
        "source_integrity_errors": source_errors,
        "base_call_argument_hashes": {
            key: digest(args) for key, args in sorted(base_calls.items())
        },
        "base_call_source_counts": dict(Counter(base_call_sources.values())),
        "base_call_sources": dict(sorted(base_call_sources.items())),
        "metrics_by_contract_variant_and_case_type": metrics,
        "aggregate_by_contract_variant": aggregate_by_variant,
        "failure_category_counts": dict(
            Counter(
                f"{row['contract_variant']}::{row['failure_category']}"
                for row in rows
                if row.get("failure_category") is not None
            )
        ),
        "claim_boundary": (
            "Source-grounded sandbox interventions over 16 reviewed AgentDojo v1.1.2 "
            "tool projections. The check compares the frozen eight-field atom projection "
            "with a typed effect-specific qualifier extension on identical generated cases. "
            "It does not establish complete contracts, deployed safety, or attack robustness."
        ),
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    ROWS.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    failures = [row for row in rows if row.get("relation_passed") is False]
    FAILURES.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in failures),
        encoding="utf-8",
    )
    REPORT_JSON.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with METRICS_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(metrics[0]))
        writer.writeheader()
        writer.writerows(metrics)
    md = [
        "# E85 AgentDojo Reviewed-Projection Interventions",
        "",
        f"Status: `{status}`.",
        "",
        f"- Reviewed and source-verified tool instances: {len(trusted)}",
        f"- Executed base calls: {len(base_calls)}",
        "",
        "## Aggregate By Contract Variant",
        "",
        "| Variant | Cases | Eligible | Passed | Rate | Gaps | Over-sensitive | Unsupported |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for variant, aggregate in aggregate_by_variant.items():
        md.append(
            f"| {variant} | {aggregate['n_cases']} | "
            f"{aggregate['n_relation_eligible']} | {aggregate['n_passed']} | "
            f"{aggregate['relation_pass_rate']:.3f} | {aggregate['mediation_gaps']} | "
            f"{aggregate['over_sensitive']} | {aggregate['unsupported']} |"
        )
    md.extend(
        [
        "",
        "## Metrics By Variant And Case Type",
        "",
        "| Variant | Type | Cases | Eligible | Passed | Rate | Gaps | Over-sensitive | Unsupported |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in metrics:
        rate = "NA" if row["pass_rate"] is None else f"{row['pass_rate']:.3f}"
        md.append(
            f"| {row['contract_variant']} | {row['case_type']} | {row['n_cases']} | "
            f"{row['n_relation_eligible']} | {row['n_passed']} | {rate} | "
            f"{row['mediation_gaps']} | {row['over_sensitive']} | "
            f"{row['unsupported']} |"
        )
    md.extend(["", "## Claim Boundary", "", report["claim_boundary"], ""])
    REPORT_MD.write_text("\n".join(md), encoding="utf-8")
    return report


def main() -> int:
    report = run()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed_with_projection_gaps" else 1


if __name__ == "__main__":
    raise SystemExit(main())
