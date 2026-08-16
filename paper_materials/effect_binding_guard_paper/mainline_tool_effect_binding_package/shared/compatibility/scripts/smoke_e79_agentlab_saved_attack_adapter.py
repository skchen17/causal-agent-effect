#!/usr/bin/env python3
"""Run one no-victim smoke of the E79 saved-attack adapter."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from agentdojo.task_suite.load_suites import get_suite

from src.experiments.effect_binding_guard.e79_agentlab_saved_attack_adapter import (
    E79AgentLABSavedTransferAttack,
)


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "analysis/results"


def main() -> int:
    suite = get_suite("v1.2.1", "workspace")
    user_task = suite.get_user_task_by_id("user_task_1")
    injection_task = suite.get_injection_task_by_id("injection_task_5")
    attack = E79AgentLABSavedTransferAttack(suite, object())
    injections = attack.attack(user_task, injection_task)
    expected = {"new_insert_email_subject", "new_insert_email_body", "new_calendar_event_title", "new_calendar_event_description", "new_insert_file_name", "new_insert_file_content"}
    report = {
        "experiment": "E79",
        "smoke_type": "agentlab_saved_attack_adapter_no_victim",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if expected <= set(injections) and all(isinstance(v, str) and v for v in injections.values()) else "failed",
        "suite": "workspace",
        "user_task_id": "user_task_1",
        "injection_task_id": "injection_task_5",
        "injection_fields": sorted(injections),
        "n_injection_fields": len(injections),
        "victim_llm_calls": 0,
        "tool_executions": 0,
        "claim_boundary": (
            "The adapter loaded and rendered one hash-frozen public saved attack into native AgentDojo injection fields. "
            "No victim model, tool trajectory, utility predicate, or attack-success predicate was executed."
        ),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "e79_agentlab_saved_attack_adapter_smoke.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
