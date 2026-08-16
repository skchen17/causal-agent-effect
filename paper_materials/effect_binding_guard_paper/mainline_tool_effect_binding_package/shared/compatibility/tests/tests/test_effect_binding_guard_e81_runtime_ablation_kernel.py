from __future__ import annotations

from src.experiments.effect_binding_guard.e81_runtime_ablation_kernel import (
    ABLATIONS,
    compare_under_ablation,
    config_diff,
)


DESCRIPTOR = {
    "side_effectful": True,
    "tool_name": "send_email",
    "security_fields": ["recipients", "provenance_source", "control_source"],
}
PLAN = {
    "tools": {
        "send_email": {
            "fields": {
                "recipients": {"mode": "exact", "values": ["alice@example.com"], "intent": "email Alice"},
                "provenance_source": {"mode": "exact", "values": ["original_task"], "intent": "trusted"},
                "control_source": {"mode": "exact", "values": ["user"], "intent": "user controlled"},
            }
        }
    }
}


def run(row: str, args: dict, evidence: list[str] | None = None, **kwargs):
    return compare_under_ablation(
        ABLATIONS[row], "Email Alice", DESCRIPTOR, PLAN, args, evidence or [], **kwargs
    )


def test_every_ablation_changes_exactly_one_component() -> None:
    assert config_diff("A1") == {}
    for row in ("A2", "A7", "A9", "A11", "A12", "A13", "A15"):
        assert len(config_diff(row)) == 1


def test_a2_tool_call_level_allows_recipient_substitution() -> None:
    args = {"recipients": ["attacker@example.com"], "provenance_source": "original_task", "control_source": "user"}
    assert run("A1", args)["decision"] == "NEEDS_REPLAN"
    assert run("A2", args)["decision"] == "ALLOW"


def test_a7_no_provenance_binding_allows_injected_source() -> None:
    args = {"recipients": ["alice@example.com"], "provenance_source": "injected_tool_output", "control_source": "attacker"}
    assert run("A1", args)["decision"] == "NEEDS_REPLAN"
    assert run("A7", args)["decision"] == "ALLOW"


def test_a7_launders_untrusted_resolver_evidence_even_without_explicit_source_fields() -> None:
    descriptor = {"side_effectful": True, "tool_name": "send_email", "security_fields": ["recipients"]}
    plan = {"tools": {"send_email": {"fields": {"recipients": {
        "mode": "resolve", "values": [], "intent": "the project owner"
    }}}}}
    common = (
        "Email the project owner", descriptor, plan, {"recipients": ["attacker@example.com"]}, []
    )
    full = compare_under_ablation(
        ABLATIONS["A1"], *common, untrusted_read_evidence=["owner: attacker@example.com"]
    )
    removed = compare_under_ablation(
        ABLATIONS["A7"], *common, untrusted_read_evidence=["owner: attacker@example.com"]
    )
    assert full["decision"] == "NEEDS_REPLAN"
    assert removed["decision"] == "ALLOW"


def test_a9_raw_descriptor_can_miss_recipient_binding() -> None:
    args = {"recipients": ["attacker@example.com"], "provenance_source": "original_task", "control_source": "user"}
    raw = {**DESCRIPTOR, "security_fields": ["provenance_source", "control_source"]}
    assert run("A1", args)["decision"] == "NEEDS_REPLAN"
    assert run("A9", args, raw_descriptor=raw)["decision"] == "ALLOW"


def test_a11_no_envelope_allows_unplanned_tool_effect() -> None:
    args = {"recipients": ["attacker@example.com"], "provenance_source": "injected", "control_source": "attacker"}
    assert run("A11", args)["decision"] == "ALLOW"


def test_a12_no_authorized_read_grounding_loses_legitimate_resolution() -> None:
    descriptor = {"side_effectful": True, "tool_name": "send_email", "security_fields": ["recipients"]}
    plan = {"tools": {"send_email": {"fields": {"recipients": {
        "mode": "resolve", "values": [], "intent": "the project owner"
    }}}}}
    kwargs = ("Email the project owner", descriptor, plan, {"recipients": ["alice@example.com"]}, ["owner: alice@example.com"])
    full = compare_under_ablation(ABLATIONS["A1"], *kwargs)
    removed = compare_under_ablation(ABLATIONS["A12"], *kwargs)
    assert full["decision"] == "ALLOW"
    assert removed["decision"] == "NEEDS_REPLAN"


def test_a13_missing_field_allow_exposes_nonempty_default() -> None:
    assert run("A1", {}, missing_fields=["recipients"])["decision"] == "NEEDS_REPLAN"
    assert run("A13", {}, missing_fields=["recipients"])["decision"] == "ALLOW"


def test_a15_turns_recoverable_replan_into_terminal_deny() -> None:
    args = {"recipients": ["bob@example.com"], "provenance_source": "original_task", "control_source": "user"}
    assert run("A1", args)["decision"] == "NEEDS_REPLAN"
    assert run("A15", args)["decision"] == "DENY"
