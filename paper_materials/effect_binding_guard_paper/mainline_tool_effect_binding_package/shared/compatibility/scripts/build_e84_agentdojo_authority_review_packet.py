#!/usr/bin/env python3
"""Build a label-hidden authority review packet for 97 AgentDojo tasks."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentdojo.task_suite.load_suites import get_suite


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "runs/e77_runtime_audit_full_20260712_075718_e77_full_gpu1.jsonl"
CACHE = ROOT / "runs/e77_plan_cache_full_20260712_075718_e77_full_gpu1.json"
OUTPUT = ROOT / "evaluation/e84_authority_manifests"
RESULTS = ROOT / "analysis/results"
DESCRIPTORS = RESULTS / "e77_registered_effect_diff_descriptors.jsonl"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def tokens(value: Any) -> set[str]:
    return set(re.findall(r"[a-z0-9][a-z0-9_.@:+/-]*", normalize(value)))


def grounded(value: Any, prompt: str) -> bool:
    rendered = normalize(value)
    task = normalize(prompt)
    if rendered and rendered in task:
        return True
    value_tokens = tokens(value)
    return bool(value_tokens) and value_tokens <= tokens(prompt)


def candidate_payload_sha256(row: dict[str, Any]) -> str:
    """Bind reviewer-editable rows to the generated, label-hidden candidate."""
    payload = {
        "review_packet_version": row["review_packet_version"],
        "suite": row["suite"],
        "user_task_id": row["user_task_id"],
        "original_task": row["original_task"],
        "original_task_sha256": row["original_task_sha256"],
        "pre_output_plan_available": row["pre_output_plan_available"],
        "candidate_task_goal": row["candidate_task_goal"],
        "candidate_bindings": [
            {
                key: value
                for key, value in binding.items()
                if key not in {"review"}
            }
            for binding in row["candidate_bindings"]
        ],
        "forbidden_hidden_evidence_present": row["forbidden_hidden_evidence_present"],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def task_inventory() -> list[dict[str, str]]:
    rows = []
    for suite_name in ("workspace", "slack", "travel", "banking"):
        suite = get_suite("v1.1.2", suite_name)
        for task_id, task in sorted(suite.user_tasks.items(), key=lambda item: int(item[0].rsplit("_", 1)[1])):
            prompt = task.PROMPT
            rows.append({
                "suite": suite_name,
                "user_task_id": task_id,
                "prompt": prompt,
                "query_hash": hashlib.sha256(prompt.encode()).hexdigest(),
            })
    return rows


def build_resolver_catalog() -> dict[str, Any]:
    effectful = {row["tool_name"] for row in read_jsonl(DESCRIPTORS)} | {"get_webpage"}
    suites: dict[str, Any] = {}
    for suite_name in ("workspace", "slack", "travel", "banking"):
        suite = get_suite("v1.1.2", suite_name)
        tools = {}
        for tool in suite.tools:
            fields = sorted(tool.parameters.model_fields)
            required_fields = sorted(
                name for name, field in tool.parameters.model_fields.items() if field.is_required()
            )
            tools[tool.name] = {
                "parameter_fields": fields,
                "required_parameter_fields": required_fields,
                "effectful_or_external_by_registry": tool.name in effectful,
                "eligible_as_authorized_read": tool.name not in effectful,
            }
        suites[suite_name] = tools
    return {
        "catalog_version": "e84_agentdojo_v1_1_2_read_tools_v1",
        "agentdojo_version": "v1.1.2",
        "suites": suites,
        "projection_kinds": ["scalar", "list_items", "record_field", "record_list_field"],
        "claim_boundary": (
            "Eligibility excludes tools registered as effectful and the external webpage fetch. "
            "A reviewer must still constrain each read invocation and typed projection."
        ),
    }


def build() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    audit = read_jsonl(AUDIT)
    cache = json.loads(CACHE.read_text(encoding="utf-8"))
    query_to_prompt_hash: dict[str, str] = {}
    for event in audit:
        if event.get("event") != "task_plan" or not event.get("query_hash") or not event.get("prompt_hash"):
            continue
        previous = query_to_prompt_hash.setdefault(event["query_hash"], event["prompt_hash"])
        if previous != event["prompt_hash"]:
            raise RuntimeError(f"non-deterministic plan cache key for query {event['query_hash']}")

    rows = []
    binding_counts = Counter()
    exact_grounding = Counter()
    unique_tools = set()
    for task in task_inventory():
        prompt_hash = query_to_prompt_hash.get(task["query_hash"])
        cached = cache.get(prompt_hash, {}) if prompt_hash else {}
        plan = cached.get("plan")
        bindings = []
        if isinstance(plan, dict):
            for tool_name, tool_plan in sorted((plan.get("tools") or {}).items()):
                unique_tools.add(tool_name)
                for field, binding in sorted((tool_plan.get("fields") or {}).items()):
                    mode = binding.get("mode")
                    values = binding.get("values") if isinstance(binding.get("values"), list) else []
                    grounding = [grounded(value, task["prompt"]) for value in values] if mode == "exact" else []
                    binding_counts[mode] += 1
                    exact_grounding.update("grounded" if item else "ungrounded" for item in grounding)
                    bindings.append({
                        "tool_name": tool_name,
                        "field": field,
                        "mode": mode,
                        "proposed_values": values,
                        "exact_value_grounded_in_original_task": grounding,
                        "proposed_intent": binding.get("intent", ""),
                        "candidate_resolver_id": f"resolve::{tool_name}::{field}" if mode == "resolve" else None,
                        "review": {
                            "decision": "PENDING",
                            "rationale": "",
                            "source_spans": [],
                            "canonical_transform": "",
                            "resolver": {
                                "read_tool": "",
                                "query_constraint": {
                                    "arguments": {},
                                    "allow_additional_arguments": False,
                                },
                                "output_projection": {
                                    "kind": "",
                                    "field": "",
                                },
                                "max_cardinality": None,
                            },
                        },
                    })
        row = {
            "review_packet_version": "e84_agentdojo_authority_review_v1",
            "suite": task["suite"],
            "user_task_id": task["user_task_id"],
            "original_task": task["prompt"],
            "original_task_sha256": task["query_hash"],
            "pre_output_plan_available": isinstance(plan, dict),
            "candidate_task_goal": plan.get("task_goal") if isinstance(plan, dict) else None,
            "candidate_bindings": bindings,
            "human_review": {
                "reviewer_anonymous_id": "",
                "review_date": "",
                "original_task_only_confirmed": False,
                "accepted": False,
                "notes": "",
            },
            "forbidden_hidden_evidence_present": False,
        }
        row["candidate_payload_sha256"] = candidate_payload_sha256(row)
        rows.append(row)

    summary = {
        "experiment": "E84",
        "artifact_type": "agentdojo_authority_manifest_review_packet",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "awaiting_human_or_trusted_interface_review",
        "n_tasks": len(rows),
        "suite_counts": dict(sorted(Counter(row["suite"] for row in rows).items())),
        "tasks_with_pre_output_plan": sum(row["pre_output_plan_available"] for row in rows),
        "tasks_without_pre_output_plan": sum(not row["pre_output_plan_available"] for row in rows),
        "unique_proposed_tools": len(unique_tools),
        "binding_mode_counts": dict(sorted(binding_counts.items())),
        "exact_value_grounding_counts": dict(sorted(exact_grounding.items())),
        "reviewed_tasks": 0,
        "accepted_tasks": 0,
        "leakage": {
            "injection_task_ids": 0,
            "attack_goals": 0,
            "security_or_utility_labels": 0,
            "gold_atoms": 0,
        },
        "claim_boundary": (
            "The packet exposes only original tasks and plans generated before tool output. Grounding checks are lexical diagnostics, "
            "not authority approval. No task is a trusted manifest until a human or independent structured interface reviews it."
        ),
    }
    return rows, summary


def main() -> int:
    rows, summary = build()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    rendered_packet = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    (OUTPUT / "review_packet.jsonl").write_text(rendered_packet, encoding="utf-8")
    (OUTPUT / "review_packet.template.jsonl").write_text(rendered_packet, encoding="utf-8")
    (OUTPUT / "resolver_catalog.json").write_text(
        json.dumps(build_resolver_catalog(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (OUTPUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (RESULTS / "e84_agentdojo_authority_interface_burden.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# E84 AgentDojo Authority-Interface Review Packet", "", f"Status: `{summary['status']}`.", "",
        f"- Tasks: `{summary['n_tasks']}`; pre-output plans: `{summary['tasks_with_pre_output_plan']}`; missing plans: `{summary['tasks_without_pre_output_plan']}`.",
        f"- Binding modes: `{json.dumps(summary['binding_mode_counts'], sort_keys=True)}`.",
        f"- Exact-value lexical grounding: `{json.dumps(summary['exact_value_grounding_counts'], sort_keys=True)}`.",
        "", "## Claim Boundary", "", summary["claim_boundary"], "",
    ]
    (RESULTS / "e84_agentdojo_authority_interface_burden.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
