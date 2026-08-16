from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = next(
    candidate
    for candidate in Path(__file__).resolve().parents
    if (candidate / "paper/current-usenix").exists()
)
SCRIPT = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/source/"
    "policy-family-sensitivity/run_policy_family_sensitivity.py"
)
SPEC = importlib.util.spec_from_file_location("policy_family_sensitivity", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def make_context(
    context_id: str,
    effects: list[dict],
    typed_atoms: list[dict] | None = None,
) -> dict:
    return {
        "context_id": context_id,
        "tool_instance_key": "suite/tool",
        "effects": effects,
        "full_effect_signature": MODULE.digest(effects),
        "typed_atoms": typed_atoms if typed_atoms is not None else effects,
        "resource_field": "resource",
    }


def test_family_projections_implement_separability_by_projection() -> None:
    effect_a = {"effect": "funds_transfer_scheduled", "resource": "account:10"}
    effect_b = {"effect": "funds_transfer_scheduled", "resource": "account:25"}
    effect_c = {"effect": "file_created", "resource": "26"}
    assert MODULE.family_projection("power_set", [effect_a], "resource") != \
        MODULE.family_projection("power_set", [effect_b], "resource")
    assert MODULE.family_projection("effect_kind", [effect_a], "resource") == \
        MODULE.family_projection("effect_kind", [effect_b], "resource")
    assert MODULE.family_projection("effect_kind", [effect_a], "resource") != \
        MODULE.family_projection("effect_kind", [effect_c], "resource")
    assert MODULE.family_projection("resource", [effect_a], "resource") != \
        MODULE.family_projection("resource", [effect_b], "resource")
    twice = MODULE.family_projection("count_truncated", [effect_a, effect_a], "resource")
    once = MODULE.family_projection("count_truncated", [effect_a], "resource")
    assert twice == [["funds_transfer_scheduled", "ge2"]]
    assert once == [["funds_transfer_scheduled", "1"]]


def test_metrics_separate_redundant_from_separating_collisions() -> None:
    effect_a = {"effect": "funds_transfer_scheduled", "resource": "account:10"}
    effect_b = {"effect": "funds_transfer_scheduled", "resource": "account:25"}
    shared_atom = {"effect": "funds_transfer_scheduled", "resource": "shared"}
    contexts = [
        make_context("a", [effect_a], [shared_atom]),
        make_context("b", [effect_b], [shared_atom]),
    ]
    power_set = MODULE.compute_metrics(contexts, "power_set", "none")
    assert power_set["separating_pairs"] == 1
    assert power_set["redundant_pairs"] == 0
    effect_kind = MODULE.compute_metrics(contexts, "effect_kind", "none")
    assert effect_kind["separating_pairs"] == 0
    assert effect_kind["redundant_pairs"] == 1
    assert effect_kind["redundancy_rate"] == 1.0


def test_metrics_count_overpartition_and_false_rejections() -> None:
    effect = {"effect": "setting_changed", "resource": "cellular"}
    contexts = [
        make_context("a", [effect], [{"effect": "setting_changed", "resource": "x"}]),
        make_context("b", [effect], [{"effect": "setting_changed", "resource": "y"}]),
    ]
    metrics = MODULE.compute_metrics(contexts, "power_set", "none")
    assert metrics["separating_pairs"] == 0
    assert metrics["overpartition_cells"] == 1
    assert metrics["false_rejection_pairs"] == 1


def test_qualifier_deletion_drops_only_declared_keys() -> None:
    atom = {
        "effect": "funds_transfer_scheduled",
        "resource": "account_funds:10.0",
        "visibility": "private",
        "qualifiers": {"date": "2026-08-01", "recurring": False, "subject": "s"},
    }
    without_date = MODULE.atom_after_deletion(atom, "date")
    assert "date" not in without_date["qualifiers"]
    assert without_date["qualifiers"]["subject"] == "s"
    assert atom["qualifiers"]["date"] == "2026-08-01"  # input untouched
    invisible = MODULE.atom_after_deletion(atom, "visibility")
    assert invisible["visibility"] == MODULE.DELETED_FIELD_MARKER
    payload_atom = {
        "effect": "direct_message_delivered",
        "resource": "payload:cfae2a8c18683855",
        "visibility": "private",
    }
    masked = MODULE.atom_after_deletion(payload_atom, "payload")
    assert masked["resource"] == MODULE.MASKED_PAYLOAD_RESOURCE


def test_toolsandbox_schema_deletions() -> None:
    atom = {
        "effect": "reminder_created",
        "resource_id": "generated:new_reminder",
        "visibility": "local_private",
        "qualifiers": {"content": "c", "reminder_timestamp": 1.0},
    }
    without_date = MODULE.atom_after_deletion(atom, "date")
    assert "reminder_timestamp" not in without_date["qualifiers"]
    assert without_date["qualifiers"]["content"] == "c"
    # subject and recurrence are not instantiated on the held-out schema
    assert MODULE.atom_after_deletion(atom, "subject") == atom
    assert MODULE.atom_after_deletion(atom, "recurrence") == atom
    without_payload = MODULE.atom_after_deletion(atom, "payload")
    assert "content" not in without_payload["qualifiers"]


def test_full_run_artifact_is_complete_and_reproduces_baselines() -> None:
    report_path = (
        ROOT
        / "experiments/security-analysis-ablation-and-overhead/results/"
        "policy-family-sensitivity/policy-family-sensitivity-report.json"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    coverage = report["coverage"]
    assert coverage["complete"] is True
    assert coverage["observed_rows"] == 48  # 2 domains x 4 families x 6 conditions
    assert all(row["passed"] for row in report["validations"])

    grid = {
        (row["domain"], row["family"], row["qualifier"]): row
        for row in report["grid_rows"]
    }
    # Typed contract is an exact partition at every family baseline.
    for domain in coverage["domains"]:
        for family in report["families"]:
            baseline = grid[(domain, family, "none")]
            assert baseline["separating_pairs"] == 0
            assert baseline["redundant_pairs"] == 0
    # AgentDojo: date/subject/recurrence each merge 16 schedule pairs that
    # remain separable only under the power-set family.
    for qualifier in ("date", "subject", "recurrence"):
        assert grid[("agentdojo_finite_domain", "power_set", qualifier)][
            "separating_pairs"
        ] == 16
        for family in ("effect_kind", "resource", "count_truncated"):
            row = grid[("agentdojo_finite_domain", family, qualifier)]
            assert row["separating_pairs"] == 0
            assert row["redundant_pairs"] == 16
    # AgentDojo payload: resource family keeps DM payload resources separable.
    payload_resource = grid[("agentdojo_finite_domain", "resource", "payload")]
    assert payload_resource["separating_pairs"] == 2
    assert payload_resource["redundant_pairs"] == 6
    # ToolSandbox: payload deletion merges 8 contact + 8 reminder pairs.
    assert grid[("toolsandbox_heldout", "power_set", "payload")][
        "separating_pairs"
    ] == 16
    assert grid[("toolsandbox_heldout", "effect_kind", "payload")][
        "redundant_pairs"
    ] == 16
    # ToolSandbox subject/recurrence roles are not instantiated.
    verdicts = {
        (row["domain"], row["qualifier"]): row for row in report["verdicts"]
    }
    assert verdicts[("toolsandbox_heldout", "subject")]["summary"] == "vacuous"
    assert verdicts[("toolsandbox_heldout", "recurrence")]["summary"] == "vacuous"
    assert (
        verdicts[("agentdojo_finite_domain", "date")]["summary"]
        == "necessary_only_under_power_set"
    )
