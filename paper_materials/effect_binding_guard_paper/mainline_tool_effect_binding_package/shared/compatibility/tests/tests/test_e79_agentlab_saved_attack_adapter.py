from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "analysis/results/e79_agentlab_saved_attack_adapter_smoke.json"


def test_saved_attack_adapter_smoke_is_no_victim_and_native_field_complete() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["victim_llm_calls"] == 0
    assert report["tool_executions"] == 0
    assert {
        "new_insert_email_subject", "new_insert_email_body",
        "new_calendar_event_title", "new_calendar_event_description",
        "new_insert_file_name", "new_insert_file_content",
    } <= set(report["injection_fields"])
    assert "No victim model" in report["claim_boundary"]
