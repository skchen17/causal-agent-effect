#!/usr/bin/env python3
"""Emit an implementation-readiness record for E83 instrumentation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "analysis/results"


def main() -> int:
    report = {
        "experiment": "E83",
        "artifact_type": "overhead_instrumentation_readiness",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "implementation_ready_not_measured",
        "event_schema": [
            "run_id", "event", "case_id", "tool_name", "trajectory_index", "wall_ns", "cpu_ns",
            "max_rss_kib_before", "max_rss_kib_after", "outcome", "error_type", "attributes",
        ],
        "required_event_types": [
            "contract_registration", "counterfactual_execution", "task_envelope", "precommit_check",
            "canonicalization", "replan_model_call", "victim_model_call",
        ],
        "required_dynamic_attributes": [
            "input_tokens", "output_tokens", "atom_count", "descriptor_bytes", "resolver_count", "decision",
        ],
        "claim_boundary": (
            "The append-only recorder and distribution summaries are implemented. No latency, token, memory, "
            "registration-cost, or scaling result is claimed until event counts reconcile with a frozen evaluation run."
        ),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "e83_overhead_instrumentation_readiness.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
