#!/usr/bin/env python3
"""Build a label-hidden human repair packet for non-executable E84 resolvers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from agentdojo.task_suite.load_suites import get_suite


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir() and (candidate / "experiments").is_dir() and (candidate / "shared").is_dir()
)
E84 = ROOT / "experiments/human-authority-and-causal-validation/evaluation/authority-manifest-human-review"
AUDIT = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/runtime-mechanism-ablation/e84-runtime-compatibility-audit.json"
)
RESULTS = ROOT / "experiments/security-analysis-ablation-and-overhead/results/runtime-mechanism-ablation"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def payload_hash(row: dict[str, Any]) -> str:
    frozen = {key: value for key, value in row.items() if key not in {"human_review", "candidate_payload_sha256"}}
    return hashlib.sha256(
        json.dumps(frozen, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def target_bindings(manifest: dict[str, Any], resolver_id: str) -> list[dict[str, str]]:
    return [
        {"tool_name": tool_name, "field": field_name}
        for tool_name, fields in manifest.get("authority_tools", {}).items()
        for field_name, binding in fields.items()
        if binding.get("resolver_id") == resolver_id
    ]


def main() -> int:
    manifests = {
        (row["suite"], row["user_task_id"]): row for row in read_jsonl(E84 / "trusted_manifests.jsonl")
    }
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    packet: list[dict[str, Any]] = []
    for observed in audit["resolver_rows"]:
        if observed["typed_projection_succeeded"]:
            continue
        key = (observed["suite"], observed["user_task_id"])
        manifest = manifests[key]
        resolver = manifest["resolver_specs"][observed["resolver_id"]]
        task = get_suite("v1.1.2", observed["suite"]).user_tasks[observed["user_task_id"]]
        row = {
            "packet_version": "e84_resolver_runtime_repair_v1",
            "suite": observed["suite"],
            "user_task_id": observed["user_task_id"],
            "original_task": task.PROMPT,
            "original_task_sha256": manifest["original_task_sha256"],
            "resolver_id": observed["resolver_id"],
            "target_bindings": target_bindings(manifest, observed["resolver_id"]),
            "approved_resolver_before_runtime_audit": resolver,
            "runtime_observation": {
                "query_arguments": observed["query_arguments"],
                "query_errors": observed["query_errors"],
                "runtime_error": observed["runtime_error"],
                "result_shape": observed["runtime_result_shape"],
                "result_fields": observed.get("runtime_result_fields", []),
                "typed_projection_succeeded": False,
                "result_values_hidden": True,
            },
            "human_review": {
                "decision": "PENDING",
                "rationale": "",
                "repaired_resolver": {
                    "read_tool": resolver["read_tool"],
                    "query_constraint": resolver["query_constraint"],
                    "output_projection": {"kind": "", "field": ""},
                    "max_cardinality": resolver["max_cardinality"],
                },
                "original_task_only_and_schema_observation_confirmed": False,
                "reviewer_anonymous_id": "",
                "review_date": "",
            },
            "forbidden_hidden_evidence_present": False,
        }
        row["candidate_payload_sha256"] = payload_hash(row)
        packet.append(row)

    output = E84 / "runtime_repair_packet.template.jsonl"
    output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in packet), encoding="utf-8")
    summary = {
        "experiment": "E84-resolver-runtime-repair",
        "status": "awaiting_independent_human_review",
        "template_rows": len(packet),
        "runtime_values_hidden": True,
        "forbidden_hidden_evidence_present": False,
        "output": str(output.relative_to(ROOT)),
        "claim_boundary": (
            "The packet exposes original tasks, approved resolver specifications, and runtime type/error observations. "
            "It contains no benchmark utility/security labels and no runtime result values. No repaired resolver is "
            "trusted until a reviewer selects an executable typed projection or rejects the resolver."
        ),
    }
    (RESULTS / "e84-resolver-repair-status.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
