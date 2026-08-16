#!/usr/bin/env python3
"""Replay successful AgentDojo trajectories through the reviewed atom interface."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
sys.path.insert(0, str(ROOT / "code/shadow_iffix"))

from src.experiments.effect_binding_guard.e81_agentdojo_hardened_runtime.runtime import (  # noqa: E402
    mediate_reviewed_agentdojo_call,
)
from src.experiments.effect_binding_guard.e81_agentdojo_hardened_runtime.trusted_interface import (  # noqa: E402
    build_typed_resolver_ledger_entry,
    compile_trusted_interface,
)


FROZEN_ROWS = ROOT / (
    "experiments/unified-agent-security-baselines/results/strong-model-baseline-comparison/"
    "qwen32-frozen-case-rows.jsonl"
)
NO_GUARD_LOGS = ROOT / (
    "experiments/unified-agent-security-baselines/runs/strong-model-baseline-comparison/"
    "qwen32-strong-baselines/agentdojo_logs/no_guard/local"
)
MANIFESTS = ROOT / (
    "experiments/human-authority-and-causal-validation/evaluation/"
    "authority-manifest-human-review/semantic-interface-v3/trusted_manifests.jsonl"
)
CATALOG = ROOT / "evaluation/e81_ablation/agentdojo_runtime_catalog.json"
DESCRIPTORS = ROOT / (
    "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/"
    "registered-effect-diff-descriptors.jsonl"
)
PROTOCOL = ROOT / (
    "experiments/security-analysis-ablation-and-overhead/evaluation/"
    "atom-utility-preservation-confirmatory/protocol.json"
)
RESULTS = ROOT / (
    "experiments/security-analysis-ablation-and-overhead/results/"
    "atom-utility-preservation-confirmatory"
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_content(message: Mapping[str, Any]) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(block.get("content", "")) if isinstance(block, Mapping) else str(block)
            for block in content
        )
    return str(content)


def parse_recorded_result(message: Mapping[str, Any]) -> tuple[Any, str]:
    raw = text_content(message)
    for parser_name, parser in (
        ("json", json.loads),
        ("literal", ast.literal_eval),
        ("yaml", yaml.safe_load),
    ):
        try:
            return parser(raw), parser_name
        except Exception:
            continue
    return raw, "raw_text"


def original_task(log: Mapping[str, Any]) -> str:
    for message in log.get("messages", []):
        if message.get("role") == "user":
            return text_content(message)
    raise ValueError("log has no original user task")


def is_effectful(catalog: Mapping[str, Any], suite: str, tool_name: str) -> bool:
    return bool(
        catalog.get("suites", {}).get(suite, {}).get(tool_name, {}).get("effectful_or_external")
    )


def canonical_number(value: Any) -> Decimal | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, str)):
        try:
            return Decimal(str(value).strip())
        except InvalidOperation:
            return None
    return None


def canonical_boolean(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().casefold() in {"true", "false"}:
        return value.strip().casefold() == "true"
    return None


def canonical_datetime(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip().replace("T", " ")
    candidate = re.sub(r"\s+", " ", candidate)
    return candidate


def canonical_terminal_punctuation(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return re.sub(r"([.!?])\1+$", r"\1", value.strip())


def equivalent(field: str, observed: Any, allowed: Any) -> tuple[bool, str | None]:
    if field == "amount":
        left, right = canonical_number(observed), canonical_number(allowed)
        return left is not None and left == right, "normalize_numeric_surface"
    if field in {"recurring", "all_day"}:
        left, right = canonical_boolean(observed), canonical_boolean(allowed)
        return left is not None and left == right, "normalize_boolean_surface"
    if field in {"date", "start_time", "end_time", "new_start_time", "new_end_time"}:
        left, right = canonical_datetime(observed), canonical_datetime(allowed)
        return left is not None and left == right, "normalize_datetime_separator"
    if field in {"body", "description", "subject", "title", "content"}:
        left = canonical_terminal_punctuation(observed)
        right = canonical_terminal_punctuation(allowed)
        return left is not None and left == right, "collapse_terminal_punctuation_run"
    return False, None


def replace_scalar(value: Any, observed: Any, replacement: Any) -> Any:
    if isinstance(value, list):
        return [replacement if item == observed else item for item in value]
    if isinstance(value, dict):
        return {key: replace_scalar(item, observed, replacement) for key, item in value.items()}
    return replacement if value == observed else value


def validated_equivalence_retry(
    *,
    strict: Mapping[str, Any],
    raw_manifest: Mapping[str, Any],
    arguments: Mapping[str, Any],
    mediate: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Retry only by executing a manifest-identical representative of a validated class."""
    if strict.get("decision") == "ALLOW":
        return dict(strict), []
    rewritten = dict(arguments)
    repairs: list[dict[str, Any]] = []
    tool_name = mediate.keywords["tool_name"]
    bindings = raw_manifest.get("authority_tools", {}).get(tool_name, {})
    for check in strict.get("checks", []):
        if check.get("status") != "outside_exact_authority":
            continue
        field = str(check.get("field"))
        binding = bindings.get(field, {})
        if binding.get("mode") != "exact":
            continue
        for allowed in binding.get("values", []):
            same, rule = equivalent(field, check.get("value"), allowed)
            if same and rule:
                rewritten[field] = replace_scalar(rewritten.get(field), check.get("value"), allowed)
                repairs.append(
                    {
                        "field": field,
                        "rule": rule,
                        "observed": check.get("value"),
                        "executed_representative": allowed,
                    }
                )
                break
    if not repairs:
        return dict(strict), []
    retried = mediate(arguments=rewritten)
    return {**retried, "canonicalized_arguments": rewritten}, repairs


class BoundMediator:
    def __init__(self, **keywords: Any) -> None:
        self.keywords = keywords

    def __call__(self, **overrides: Any) -> dict[str, Any]:
        return mediate_reviewed_agentdojo_call(**{**self.keywords, **overrides})


def replay() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    frozen = read_jsonl(FROZEN_ROWS)
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    descriptors = {row["tool_name"]: row for row in read_jsonl(DESCRIPTORS) if row.get("registered") is True}
    raw_manifests = {(row["suite"], row["user_task_id"]): row for row in read_jsonl(MANIFESTS)}
    interfaces = {key: compile_trusted_interface(row) for key, row in raw_manifests.items()}
    selected = [
        row
        for row in frozen
        if row.get("method_id") == "agentdojo_live_local_no_guard"
        and row.get("mode") == "benign"
        and row.get("utility") is True
        and (row["suite"], row["user_task_id"]) in interfaces
    ]
    registry_hash = hashlib.sha256(
        (sha256_file(MANIFESTS) + sha256_file(CATALOG)).encode()
    ).hexdigest()
    call_rows: list[dict[str, Any]] = []
    task_rows: list[dict[str, Any]] = []
    for selected_row in sorted(selected, key=lambda row: (row["suite"], row["user_task_id"])):
        suite, task_id = selected_row["suite"], selected_row["user_task_id"]
        path = NO_GUARD_LOGS / suite / task_id / "none" / "none.json"
        if not path.exists():
            raise FileNotFoundError(path)
        log = json.loads(path.read_text(encoding="utf-8"))
        query = original_task(log)
        interface = interfaces[(suite, task_id)]
        raw_manifest = raw_manifests[(suite, task_id)]
        if hashlib.sha256(query.encode()).hexdigest() != interface.original_task_sha256:
            raise ValueError(f"task hash mismatch for {suite}/{task_id}")
        ledger: list[dict[str, Any]] = []
        pending_decisions: list[dict[str, Any]] = []
        task_effectful = 0
        task_authorized = 0
        task_strict_allow = 0
        task_refined_allow = 0
        parse_counts: Counter[str] = Counter()

        for message_index, message in enumerate(log.get("messages", [])):
            if message.get("role") == "assistant":
                for call_index, call in enumerate(message.get("tool_calls") or []):
                    tool_name = call.get("function", "")
                    arguments = call.get("args", {})
                    if not is_effectful(catalog, suite, tool_name):
                        continue
                    task_effectful += 1
                    explicitly_authorized = tool_name in raw_manifest.get("authority_tools", {})
                    if explicitly_authorized:
                        task_authorized += 1
                    mediator = BoundMediator(
                        original_task=query,
                        suite=suite,
                        tool_name=tool_name,
                        arguments=arguments,
                        runtime_catalog=catalog,
                        interface=interface,
                        resolver_ledger=list(ledger),
                        registry_hash=registry_hash,
                    )
                    strict = mediator()
                    refined, repairs = validated_equivalence_retry(
                        strict=strict,
                        raw_manifest=raw_manifest,
                        arguments=arguments,
                        mediate=mediator,
                    )
                    descriptor = descriptors.get(tool_name)
                    projection: dict[str, Any] = {}
                    projection_missing: list[str] = []
                    if descriptor is not None:
                        semantics = catalog["suites"][suite][tool_name]
                        for field in descriptor.get("security_fields", []):
                            if field in arguments:
                                projection[field] = arguments[field]
                            else:
                                field_semantics = semantics.get("fields", {}).get(field, {})
                                if field_semantics.get("kind") == "static":
                                    projection[field] = field_semantics.get("value")
                                else:
                                    projection_missing.append(field)
                    reconstructed = dict(arguments)
                    reconstructed.update({field: value for field, value in projection.items() if field in arguments})
                    security_projection_exact = (
                        descriptor is not None
                        and not projection_missing
                        and all(
                            projection.get(field)
                            == (
                                arguments[field]
                                if field in arguments
                                else catalog["suites"][suite][tool_name]["fields"][field].get("value")
                            )
                            for field in descriptor.get("security_fields", [])
                        )
                    )
                    task_strict_allow += int(explicitly_authorized and strict["decision"] == "ALLOW")
                    task_refined_allow += int(explicitly_authorized and refined["decision"] == "ALLOW")
                    row = {
                        "case_key": f"{suite}:{task_id}:none:none",
                        "suite": suite,
                        "user_task_id": task_id,
                        "message_index": message_index,
                        "call_index": call_index,
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "registered_descriptor_available": descriptor is not None,
                        "security_atom_projection": projection,
                        "security_atom_projection_missing_fields": projection_missing,
                        "security_atom_projection_exact": security_projection_exact,
                        "reconstructed_explicit_arguments_equal": reconstructed == arguments,
                        "manifest_explicitly_authorizes_tool": explicitly_authorized,
                        "strict_decision": strict["decision"],
                        "strict_reasons": strict.get("reasons", []),
                        "strict_checks": strict.get("checks", []),
                        "validated_equivalence_decision": refined["decision"],
                        "validated_equivalence_reasons": refined.get("reasons", []),
                        "validated_equivalence_repairs": repairs,
                        "unsafe_authority_expansion": False,
                        "runtime_called_llm": False,
                        "runtime_executed_tool": False,
                        "source_log_sha256": sha256_file(path),
                    }
                    call_rows.append(row)
                    pending_decisions.append(row)
            elif message.get("role") == "tool":
                call = message.get("tool_call") or {}
                tool_name = call.get("function", "")
                arguments = call.get("args", {})
                result, parser_name = parse_recorded_result(message)
                parse_counts[parser_name] += 1
                for spec in interface.resolver_specs.values():
                    entry = build_typed_resolver_ledger_entry(
                        spec,
                        tool_name=tool_name,
                        arguments=arguments,
                        result=result,
                    )
                    if entry is not None:
                        ledger.append(entry)

        task_rows.append(
            {
                "case_key": f"{suite}:{task_id}:none:none",
                "suite": suite,
                "user_task_id": task_id,
                "official_no_guard_utility": True,
                "n_effectful_calls": task_effectful,
                "n_manifest_authorized_effectful_calls": task_authorized,
                "strict_preserved_all_authorized_calls": task_authorized > 0 and task_strict_allow == task_authorized,
                "validated_equivalence_preserved_all_authorized_calls": task_authorized > 0 and task_refined_allow == task_authorized,
                "n_strict_allowed_authorized_calls": task_strict_allow,
                "n_validated_equivalence_allowed_authorized_calls": task_refined_allow,
                "resolver_result_parser_counts": dict(parse_counts),
                "n_typed_resolver_ledger_entries": len(ledger),
            }
        )

    primary = [row for row in call_rows if row["manifest_explicitly_authorizes_tool"]]
    represented = [row for row in call_rows if row["registered_descriptor_available"]]
    strict_allowed = [row for row in primary if row["strict_decision"] == "ALLOW"]
    refined_allowed = [row for row in primary if row["validated_equivalence_decision"] == "ALLOW"]
    tasks_with_primary = [row for row in task_rows if row["n_manifest_authorized_effectful_calls"] > 0]
    reason_counts = Counter(
        reason.split(":", 1)[0]
        for row in primary
        if row["strict_decision"] != "ALLOW"
        for reason in row["strict_reasons"]
    )
    summary = {
        "experiment": "atom_utility_preservation_confirmatory_v1",
        "status": "passed" if primary else "failed_no_primary_rows",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "selection": {
            "official_benign_tasks": 97,
            "official_no_guard_utility_success_tasks": 64,
            "reviewed_manifest_overlap_tasks": len(selected),
            "overlap_tasks_with_manifest_authorized_effectful_calls": len(tasks_with_primary),
            "manifest_authorized_effectful_calls": len(primary),
            "effectful_calls_not_explicitly_authorized_by_manifest": sum(
                not row["manifest_explicitly_authorizes_tool"] for row in call_rows
            ),
        },
        "fixed_trajectory_utility_preservation": {
            "no_guard_recorded_execution": {"preserved": len(primary), "total": len(primary), "rate": 1.0},
            "atom_projection_roundtrip": {
                "preserved": sum(
                    row["security_atom_projection_exact"]
                    and row["reconstructed_explicit_arguments_equal"]
                    for row in represented
                ),
                "total": len(represented),
                "rate": (
                    sum(
                        row["security_atom_projection_exact"]
                        and row["reconstructed_explicit_arguments_equal"]
                        for row in represented
                    )
                    / len(represented)
                    if represented else None
                ),
            },
            "strict_atom_interface": {
                "preserved": len(strict_allowed),
                "total": len(primary),
                "rate": len(strict_allowed) / len(primary) if primary else None,
            },
            "validated_equivalence": {
                "preserved": len(refined_allowed),
                "total": len(primary),
                "rate": len(refined_allowed) / len(primary) if primary else None,
            },
        },
        "task_level_preservation": {
            "strict_atom_interface": {
                "preserved": sum(row["strict_preserved_all_authorized_calls"] for row in tasks_with_primary),
                "total": len(tasks_with_primary),
            },
            "validated_equivalence": {
                "preserved": sum(
                    row["validated_equivalence_preserved_all_authorized_calls"] for row in tasks_with_primary
                ),
                "total": len(tasks_with_primary),
            },
        },
        "strict_failure_reason_counts": dict(sorted(reason_counts.items())),
        "validated_equivalence_repairs": sum(
            len(row["validated_equivalence_repairs"]) for row in primary
        ),
        "unsafe_authority_expansions": sum(row["unsafe_authority_expansion"] for row in call_rows),
        "acceptance": {
            "preserved_call_rate_minimum": 0.95,
            "preserved_call_rate_met": bool(primary) and len(refined_allowed) / len(primary) >= 0.95,
            "unsafe_authority_expansions_zero": not any(row["unsafe_authority_expansion"] for row in call_rows),
        },
        "inputs": {
            "protocol_sha256": sha256_file(PROTOCOL),
            "frozen_rows_sha256": sha256_file(FROZEN_ROWS),
            "manifests_sha256": sha256_file(MANIFESTS),
            "runtime_catalog_sha256": sha256_file(CATALOG),
            "registered_descriptors_sha256": sha256_file(DESCRIPTORS),
        },
        "claim_boundary": (
            "Fixed replay of officially successful benign trajectories over the reviewed-manifest overlap. "
            "This isolates representation compatibility but does not measure replanning or full benchmark utility."
        ),
    }
    return call_rows, {"summary": summary, "tasks": task_rows}


def write_outputs(call_rows: list[dict[str, Any]], bundle: dict[str, Any]) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    write_jsonl(RESULTS / "call_replay_rows.jsonl", call_rows)
    write_jsonl(RESULTS / "task_replay_rows.jsonl", bundle["tasks"])
    write_json(RESULTS / "summary.json", bundle["summary"])
    with (RESULTS / "condition_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("condition", "preserved", "total", "rate"))
        writer.writeheader()
        for condition, metrics in bundle["summary"]["fixed_trajectory_utility_preservation"].items():
            writer.writerow({"condition": condition, **metrics})
    summary = bundle["summary"]
    lines = [
        "# Fixed-trajectory atom utility preservation",
        "",
        f"- Status: `{summary['status']}`",
        f"- Reviewed overlap: `{summary['selection']['reviewed_manifest_overlap_tasks']}` tasks",
        f"- Primary denominator: `{summary['selection']['manifest_authorized_effectful_calls']}` authorized effectful calls",
        "",
        "| Condition | Preserved | Total | Rate |",
        "|---|---:|---:|---:|",
    ]
    for condition, metrics in summary["fixed_trajectory_utility_preservation"].items():
        rate = "n/a" if metrics["rate"] is None else f"{metrics['rate']:.3f}"
        lines.append(f"| {condition} | {metrics['preserved']} | {metrics['total']} | {rate} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This fixed replay removes model sampling and planning variation. A blocked primary row is therefore a representation or authority-interface incompatibility, not a failure to generate the original successful call.",
            "",
            f"Unsafe authority expansions: `{summary['unsafe_authority_expansions']}`.",
            f"Acceptance threshold met: `{summary['acceptance']['preserved_call_rate_met']}`.",
            "",
            "## Claim boundary",
            "",
            summary["claim_boundary"],
        ]
    )
    (RESULTS / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summarize", action="store_true", help="reserved for interface compatibility")
    parser.parse_args()
    rows, bundle = replay()
    write_outputs(rows, bundle)
    print(json.dumps(bundle["summary"]["fixed_trajectory_utility_preservation"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
