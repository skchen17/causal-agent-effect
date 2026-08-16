#!/usr/bin/env python3
"""Freeze the final protocol for the AgentDojo tool-effect prevalence census."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *SCRIPT_PATH.parents)
    if (candidate / "paper/current-usenix").exists()
)
OUTPUT = (
    ROOT
    / "experiments/human-authority-and-causal-validation/evaluation/"
    "agentdojo-tool-effect-prevalence"
)
PROTOCOL = OUTPUT / "protocol.json"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def protocol() -> dict[str, Any]:
    return {
        "protocol_id": "agentdojo-official-benign-tool-effect-prevalence-v1",
        "frozen_on": "2026-08-03",
        "analysis_status": (
            "descriptive protocol frozen after an exploratory coverage audit; "
            "not result-blind preregistration"
        ),
        "benchmark": "AgentDojo v1.1.2",
        "population": {
            "suites": ["banking", "slack", "travel", "workspace"],
            "task_selection": "all official benign user tasks",
            "call_selection": "all calls in each official ground-truth trajectory",
            "expected_tasks": 97,
            "expected_calls": 339,
            "exclusions": [],
        },
        "execution": {
            "environment": "fresh in-memory suite state per user task",
            "trajectory_semantics": "sequential prefix replay",
            "expected_inventory_source_manifest_sha256": (
                "acf583a361ee0acad397b4f5d6aadb9e0bc1adcc0df08c3dd3e43d22a4393ef7"
            ),
            "external_side_effects": False,
            "retain_execution_errors": True,
            "post_result_case_deletion": False,
        },
        "oracle": {
            "candidate_contract_input": False,
            "attack_or_outcome_label_input": False,
            "method": "before/after benchmark-state difference",
            "ignored_mirrors": [
                "calendar.initial_events",
                "cloud_drive.initial_files",
                "inbox.initial_emails",
                "inbox.sent",
                "inbox.received",
                "inbox.trash",
                "inbox.drafts",
            ],
            "ignored_volatile_fields": ["last_modified", "size", "timestamp"],
            "logical_unit_rule": (
                "Collapse storage mirrors and metadata into one resource mutation; "
                "expand independently addressable principals, messages, permissions, "
                "membership changes, and per-object read-state changes."
            ),
        },
        "primary_metrics": [
            "official_tool_inventory_coverage",
            "state_or_external_effect_call_rate",
            "effectful_observed_tool_rate",
            "compound_call_rate",
            "heterogeneous_compound_call_rate",
            "multi_target_call_rate",
            "cross_namespace_call_rate",
            "maximum_effect_units_per_call",
        ],
        "definitions": {
            "effectful_call": "one or more normalized logical effect units",
            "compound_call": "more than one normalized logical effect unit",
            "heterogeneous_compound_call": "more than one effect kind",
            "multi_target_call": "more than one non-null target principal",
            "cross_namespace_call": "effect units modify more than one logical subsystem",
        },
        "claim_boundary": (
            "The census estimates prevalence only in AgentDojo v1.1.2 official "
            "benign ground-truth trajectories. It is not an ecosystem-wide estimate, "
            "an attack evaluation, or proof that the normalization is complete for "
            "unseen tools and states."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    payload = protocol()
    payload["protocol_sha256"] = hashlib.sha256(
        canonical_json(payload).encode()
    ).hexdigest()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if PROTOCOL.exists() and not args.force:
        current = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        if current != payload:
            raise SystemExit(
                "existing protocol differs; inspect it or pass --force explicitly"
            )
        print(f"unchanged: {PROTOCOL}")
        return 0
    PROTOCOL.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote: {PROTOCOL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
