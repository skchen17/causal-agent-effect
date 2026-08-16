from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "analysis/results/e80_e77_implementation_obligation_audit.json"


def test_e77_all_executed_valid_calls_are_precommit_mediated() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["status"] == "passed_with_conditional_gaps"
    assert report["official_cases"] == 726
    assert report["logs"]["valid_calls_reaching_executor"] == 3173
    assert report["precommit_audit"]["official_checks"] == 3173
    assert report["precommit_audit"]["signature_multiset_exact_match"] is True
    assert report["precommit_audit"]["missing_check_occurrences"] == 0
    assert report["precommit_audit"]["extra_check_occurrences"] == 0


def test_e77_audit_does_not_overstate_conditional_obligations() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    obligations = report["obligations"]
    assert obligations["O1_contract_soundness"]["status"] == "partial"
    assert obligations["O2_envelope_soundness"]["status"] == "partial"
    assert obligations["O3_complete_mediation"]["status"] == "passed_for_official_agentdojo_run"
    assert obligations["O4_check_use_integrity"]["status"] == "passed_for_sandbox_call_object"
    assert obligations["O5_fail_closed_uncertainty"]["status"] == "partial"


def test_e77_optional_defaults_are_empty_in_the_audited_suites() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    defaults = report["default_semantics"]
    assert defaults["optional_security_field_occurrences"] > 0
    assert defaults["all_observed_optional_security_defaults_empty_or_none"] is True
    assert defaults["nonempty_optional_defaults"] == []
