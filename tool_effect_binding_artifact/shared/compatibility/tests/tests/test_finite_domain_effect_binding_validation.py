from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = next(
    candidate
    for candidate in Path(__file__).resolve().parents
    if (candidate / "paper/current-usenix").exists()
)
SCRIPT = ROOT / "scripts/run_finite_domain_effect_binding_validation.py"
SPEC = importlib.util.spec_from_file_location("finite_validation", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_finite_call_domain_has_expected_size_and_tools() -> None:
    rows = MODULE.finite_calls()
    assert len(rows) == 56
    assert {tool for _, tool, _ in rows} == {
        "add_calendar_event_participants",
        "create_file",
        "share_file",
        "send_direct_message",
        "schedule_transaction",
    }
    assert any(
        tool == "add_calendar_event_participants"
        and args["participants"] == ["finite.a@example.com", "finite.a@example.com"]
        for _, tool, args in rows
    )


def test_collision_analysis_detects_authorization_separation() -> None:
    contexts = [
        {
            "context_id": "a",
            "source_effect_signature": "effect-a",
            "source_effects": [{"effect": "a"}],
            "representations": {"coarse": "same"},
        },
        {
            "context_id": "b",
            "source_effect_signature": "effect-b",
            "source_effects": [{"effect": "b"}],
            "representations": {"coarse": "same"},
        },
    ]
    summary, witnesses = MODULE.analyze_representation(contexts, "coarse")
    assert summary["authorization_collision_cells"] == 1
    assert summary["authorization_separating_pairs"] == 1
    assert summary["finite_collision_complete"] is False
    assert len(witnesses) == 1


def test_collision_analysis_preserves_effect_multiplicity() -> None:
    effect = {"effect": "invitation_sent", "target": "finite.a@example.com"}
    contexts = [
        {
            "context_id": "once",
            "source_effect_signature": "once",
            "source_effects": [effect],
            "representations": {"coarse": "same"},
        },
        {
            "context_id": "twice",
            "source_effect_signature": "twice",
            "source_effects": [effect, effect],
            "representations": {"coarse": "same"},
        },
    ]
    summary, witnesses = MODULE.analyze_representation(contexts, "coarse")
    assert summary["authorization_separating_pairs"] == 1
    assert witnesses[0]["authorized_context_id"] == "once"
    assert witnesses[0]["authority_bound"] == [effect]


def test_collision_analysis_separates_completeness_from_overpartition() -> None:
    contexts = [
        {
            "context_id": "a",
            "source_effect_signature": "same-effect",
            "source_effects": [{"effect": "a"}],
            "representations": {"fine": "left"},
        },
        {
            "context_id": "b",
            "source_effect_signature": "same-effect",
            "source_effects": [{"effect": "a"}],
            "representations": {"fine": "right"},
        },
    ]
    summary, _ = MODULE.analyze_representation(contexts, "fine")
    assert summary["finite_collision_complete"] is True
    assert summary["overpartition_pairs"] == 1
    assert summary["finite_partition_exact"] is False


def test_full_run_artifact_records_bounded_positive_result() -> None:
    report_path = (
        ROOT
        / "experiments/human-authority-and-causal-validation/results/"
        "finite-domain-effect-binding-validation/finite-domain-validation-report.json"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    rows = {row["representation"]: row for row in report["representations"]}
    assert report["status"] == "passed"
    assert report["n_contexts"] == 56
    assert report["source_verification_errors"] == []
    assert rows["reviewed_common_contract"]["authorization_separating_pairs"] == 118
    assert rows["reviewed_typed_contract"]["finite_collision_complete"] is True
    assert rows["reviewed_typed_contract"]["finite_partition_exact"] is True
