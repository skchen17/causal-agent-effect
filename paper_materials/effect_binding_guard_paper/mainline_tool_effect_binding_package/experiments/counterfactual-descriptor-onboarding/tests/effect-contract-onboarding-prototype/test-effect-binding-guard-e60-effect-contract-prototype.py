from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from src.experiments.effect_binding_guard.e60_effect_contract_prototype import demo
from src.experiments.effect_binding_guard.e60_effect_contract_prototype.contract_validator import validate_contract
from src.experiments.effect_binding_guard.e60_effect_contract_prototype.counterfactual_generator import generate_counterfactual_cases
from src.experiments.effect_binding_guard.e60_effect_contract_prototype.llm_contract_proposer import ContractProposer
from src.experiments.effect_binding_guard.e60_effect_contract_prototype.mock_tools import (
    all_authorization_contexts,
    authorization_context,
    load_mock_tools,
    tool_by_name,
)
from src.experiments.effect_binding_guard.e60_effect_contract_prototype.runtime import atomize_tool_call, authorize_tool_call, freeze_contract


TOOL_NAMES = ("send_email", "create_calendar_event", "share_file", "post_slack_message", "submit_payment")


def contract_for(tool_name: str):
    return ContractProposer(mode="stub").propose(tool_by_name(tool_name))


def frozen_contract(tool_name: str):
    tool = tool_by_name(tool_name)
    contract = contract_for(tool_name)
    validation = validate_contract(contract, generate_counterfactual_cases(tool))
    assert validation.passed
    return freeze_contract(contract, validation)


def test_stub_proposer_returns_structured_contracts_for_all_five_tools() -> None:
    for tool in load_mock_tools():
        contract = ContractProposer(mode="stub").propose(tool)
        assert contract.tool_name == tool.name
        assert contract.proposal_mode == "stub"
        assert contract.templates
        assert not contract.provenance["trusted"]


def test_counterfactual_generator_creates_expected_axes_and_independent_expectations() -> None:
    cases = generate_counterfactual_cases(tool_by_name("share_file"))
    axes = {case.axis for case in cases}
    assert {
        "same_effect_surface_variant",
        "operation_mode_shift",
        "authorization_shift",
        "ambiguous_resource_identity",
        "provenance_control_shift",
        "public_visibility_shift",
        "multi_resource_expansion",
        "alias_resolution",
    } <= axes
    assert all(case.expected_mutated_atoms for case in cases)
    assert all(case.expected_relation in {"invariant", "sensitive"} for case in cases)
    assert any(case.expected_violation_reasons for case in cases if case.expected_mutated_decision != "ALLOW")


def test_all_five_tools_pass_counterfactual_validation() -> None:
    for tool in load_mock_tools():
        validation = validate_contract(contract_for(tool.name), generate_counterfactual_cases(tool))
        assert validation.passed, (tool.name, validation.failures)
        assert validation.required_atom_coverage == 1.0
        assert validation.required_resource_binding_coverage == 1.0


def test_send_email_atom_resource_target_semantics_are_correct() -> None:
    atoms = atomize_tool_call(
        contract_for("send_email"),
        {
            "to": ["analyst@example.com"],
            "cc": ["manager@example.com"],
            "bcc": ["auditor@example.com"],
            "attachments": [],
            "commit_mode": "draft",
            "control_source": "user",
            "provenance_source": "user",
        },
        authorization_context("draft_only"),
    )
    message_atoms = [atom for atom in atoms if atom.effect_type == "message_sent"]
    assert {atom.resource_id for atom in message_atoms} == {"email_body"}
    assert {atom.resource_type for atom in message_atoms} == {"message"}
    assert {(atom.target_principal, atom.target_role) for atom in message_atoms} == {
        ("analyst@example.com", "to"),
        ("manager@example.com", "cc"),
        ("auditor@example.com", "bcc"),
    }


def test_attachment_disclosure_uses_file_resource_and_recipient_target() -> None:
    atoms = atomize_tool_call(
        contract_for("send_email"),
        {
            "to": ["analyst@example.com", "manager@example.com"],
            "attachments": ["finance-plan.docx"],
            "commit_mode": "draft",
            "control_source": "user",
            "provenance_source": "user",
        },
        authorization_context("draft_only"),
    )
    disclosure_atoms = [atom for atom in atoms if atom.effect_type == "attachment_disclosed"]
    assert {atom.resource_id for atom in disclosure_atoms} == {"finance-plan.docx"}
    assert {atom.resource_type for atom in disclosure_atoms} == {"file"}
    assert {atom.target_principal for atom in disclosure_atoms} == {"analyst@example.com", "manager@example.com"}


def test_calendar_attendees_create_separate_invite_atoms() -> None:
    atoms = atomize_tool_call(
        contract_for("create_calendar_event"),
        {
            "event_id": "event-123",
            "title": "Planning sync",
            "attendees": ["analyst@example.com", "manager@example.com"],
            "visibility": "private",
            "commit_mode": "draft",
            "control_source": "user",
            "provenance_source": "user",
        },
        authorization_context("draft_only"),
    )
    invite_atoms = [atom for atom in atoms if atom.effect_type == "calendar_attendee_invited"]
    assert {atom.resource_id for atom in invite_atoms} == {"event-123"}
    assert {atom.target_principal for atom in invite_atoms} == {"analyst@example.com", "manager@example.com"}
    assert {atom.target_role for atom in invite_atoms} == {"attendee"}


def test_calendar_external_attendee_draft_commit_alias_and_untrusted_control() -> None:
    frozen = frozen_contract("create_calendar_event")
    ctx = authorization_context("draft_only")
    external = authorize_tool_call(
        frozen,
        {**tool_by_name("create_calendar_event").example_safe_call, "attendees": ["external@vendor.test"]},
        ctx,
    )
    assert external["decision"] == "DENY"
    assert "target_principal_authorization" in external["reasons"]

    draft_atoms = atomize_tool_call(frozen, {**tool_by_name("create_calendar_event").example_safe_call, "commit_mode": "draft"}, ctx)
    commit_atoms = atomize_tool_call(frozen, {**tool_by_name("create_calendar_event").example_safe_call, "commit_mode": "commit"}, ctx)
    assert {atom.commit_mode for atom in draft_atoms} == {"draft"}
    assert {atom.commit_mode for atom in commit_atoms} == {"commit"}

    alias_call = {**tool_by_name("create_calendar_event").example_safe_call, "event_id": "event_alias"}
    alias_enabled = authorize_tool_call(frozen, alias_call, authorization_context("alias_enabled"))
    alias_disabled = authorize_tool_call(frozen, alias_call, authorization_context("alias_disabled"))
    assert alias_enabled["decision"] == "ALLOW"
    assert alias_disabled["decision"] == "DENY"

    untrusted = authorize_tool_call(frozen, {**tool_by_name("create_calendar_event").example_safe_call, "control_source": "tool_output", "provenance_source": "tool_output"}, ctx)
    assert untrusted["decision"] in {"DENY", "ABSTAIN"}
    assert untrusted["decision"] == "DENY"


def test_safe_unsafe_unknown_runtime_behavior_for_all_tools() -> None:
    ctx = authorization_context("draft_only")
    for tool in load_mock_tools():
        frozen = frozen_contract(tool.name)
        safe = authorize_tool_call(frozen, tool.example_safe_call, ctx)
        unsafe = authorize_tool_call(frozen, tool.example_unsafe_call, ctx)
        unknown = authorize_tool_call(frozen, tool.example_unknown_call, ctx)
        assert safe["decision"] == "ALLOW", tool.name
        assert unsafe["decision"] in {"DENY", "ABSTAIN"}, tool.name
        assert unknown["decision"] == "ABSTAIN", tool.name


def test_public_link_unknown_resource_alias_limited_payment_and_untrusted_contexts() -> None:
    share = frozen_contract("share_file")
    public_result = authorize_tool_call(
        share,
        {**tool_by_name("share_file").example_safe_call, "visibility": "public"},
        authorization_context("no_public_link"),
    )
    assert public_result["decision"] == "DENY"
    assert "visibility_authorization" in public_result["reasons"]

    unknown_result = authorize_tool_call(
        share,
        {**tool_by_name("share_file").example_safe_call, "file_id": "unknown_file"},
        authorization_context("draft_only"),
    )
    assert unknown_result["decision"] == "ABSTAIN"

    alias_enabled = authorize_tool_call(share, tool_by_name("share_file").example_safe_call, authorization_context("alias_enabled"))
    alias_disabled = authorize_tool_call(share, tool_by_name("share_file").example_safe_call, authorization_context("alias_disabled"))
    assert alias_enabled["decision"] == "ALLOW"
    assert alias_disabled["decision"] == "DENY"

    payment = frozen_contract("submit_payment")
    limited_payment = authorize_tool_call(payment, tool_by_name("submit_payment").example_safe_call, authorization_context("limited_payment"))
    assert limited_payment["decision"] == "DENY"
    assert "target_principal_authorization" in limited_payment["reasons"]

    slack = frozen_contract("post_slack_message")
    untrusted = authorize_tool_call(
        slack,
        {**tool_by_name("post_slack_message").example_safe_call, "control_source": "tool_output", "provenance_source": "tool_output"},
        authorization_context("untrusted_control_forbidden"),
    )
    assert untrusted["decision"] == "DENY"


def test_all_context_variants_exist() -> None:
    contexts = all_authorization_contexts()
    assert {
        "default_safe",
        "draft_only",
        "no_public_link",
        "alias_enabled",
        "alias_disabled",
        "external_recipient_forbidden",
        "limited_payment",
        "untrusted_control_forbidden",
    } <= set(contexts)


def test_frozen_runtime_never_calls_proposer_for_any_tool(monkeypatch) -> None:
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("runtime called the proposer")

    frozen_by_tool = {name: frozen_contract(name) for name in TOOL_NAMES}
    monkeypatch.setattr(ContractProposer, "propose", fail_if_called)
    for name, frozen in frozen_by_tool.items():
        result = authorize_tool_call(frozen, tool_by_name(name).example_safe_call, authorization_context("draft_only"))
        assert result["decision"] == "ALLOW"


def test_frozen_contract_output_is_deterministic() -> None:
    frozen = frozen_contract("submit_payment")
    call = tool_by_name("submit_payment").example_safe_call
    first = authorize_tool_call(frozen, call, authorization_context("draft_only"))
    second = authorize_tool_call(frozen, call, authorization_context("draft_only"))
    assert first["decision"] == second["decision"]
    assert first["atoms"] == second["atoms"]
    assert first["contract_hash"] == second["contract_hash"]


def test_incomplete_contract_variants_fail_validation() -> None:
    variants = {
        "missing_attachment_disclosure": ("send_email", lambda template: template.effect_type != "attachment_disclosed"),
        "missing_external_target_handling": ("send_email", lambda template: template.target_principal_field is None),
        "missing_public_visibility": ("share_file", lambda template: template.effect_type != "public_link_created"),
        "missing_calendar_attendee": ("create_calendar_event", lambda template: template.effect_type != "calendar_attendee_invited"),
    }
    for name, (tool_name, keep) in variants.items():
        tool = tool_by_name(tool_name)
        contract = contract_for(tool_name)
        incomplete = replace(contract, templates=tuple(template for template in contract.templates if keep(template)))
        validation = validate_contract(incomplete, generate_counterfactual_cases(tool))
        assert not validation.passed, name
        assert validation.missing_required_atom_count > 0 or validation.unsafe_pre_allow_rate > 0.0


def test_incomplete_commit_mode_and_control_source_contracts_fail_validation() -> None:
    for name, tool_name, mutate_template in (
        ("missing_commit_mode", "submit_payment", lambda template: replace(template, commit_mode_field="ignored_commit_mode", default_commit_mode="draft")),
        ("missing_control_source", "post_slack_message", lambda template: replace(template, control_source_field="ignored_control_source", provenance_source_field="ignored_provenance_source")),
    ):
        tool = tool_by_name(tool_name)
        contract = contract_for(tool_name)
        incomplete = replace(contract, templates=tuple(mutate_template(template) for template in contract.templates))
        validation = validate_contract(incomplete, generate_counterfactual_cases(tool))
        assert not validation.passed, name
        assert validation.failures


def test_demo_smoke_produces_expected_output_files() -> None:
    demo.main()
    for path in (
        Path("../analysis/results/e60_demo_outputs.jsonl"),
        Path("../analysis/results/e60_effect_contract_prototype_report.md"),
        Path("../analysis/results/e60_effect_contract_prototype_report.json"),
        Path("../analysis/results/e60_reuse_inventory.md"),
    ):
        assert path.exists()
        assert path.stat().st_size > 0

