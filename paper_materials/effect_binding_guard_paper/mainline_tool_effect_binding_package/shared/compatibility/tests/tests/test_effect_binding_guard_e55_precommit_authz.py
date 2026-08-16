from __future__ import annotations

from src.experiments.effect_binding_guard.e55_precommit_authz.atom_expansion import expand_tool_call
from src.experiments.effect_binding_guard.e55_precommit_authz.authz_model import authorize_atoms
from src.experiments.effect_binding_guard.e55_precommit_authz.dataset_builder import build_case, build_dataset, dataset_counts
from src.experiments.effect_binding_guard.e55_precommit_authz.guards import authz_aware_guard
from src.experiments.effect_binding_guard.e55_precommit_authz.leakage_audit import audit_cases, audit_deployable_input


def test_dataset_counts_and_slice_targets() -> None:
    cases = build_dataset()
    counts = dataset_counts(cases)
    assert counts["n_rows"] == 600
    assert counts["domain_counts"] == {"email": 120, "calendar": 120, "file": 120, "slack": 120, "transaction": 120}
    assert counts["pair_group_count"] == 60
    assert counts["slice_counts"]["multi_resource"] >= 180
    assert counts["slice_counts"]["draft_commit"] >= 150
    assert counts["slice_counts"]["alias"] >= 120
    assert counts["slice_counts"]["public_visibility"] >= 90
    assert counts["slice_counts"]["provenance_shift"] >= 90


def test_email_cc_bcc_and_attachment_expansion() -> None:
    atoms = expand_tool_call(
        "email",
        "send_email",
        {
            "to": ["a@example.com"],
            "cc": ["b@example.com"],
            "bcc": ["c@example.com"],
            "attachments": ["file-1.pdf"],
            "control_source": "user",
        },
    )
    assert [(atom.resource_id, atom.recipient_role) for atom in atoms if atom.resource_type == "recipient"] == [
        ("a@example.com", "to"),
        ("b@example.com", "cc"),
        ("c@example.com", "bcc"),
    ]
    assert any(atom.effect == "file_attached" and atom.resource_id == "file-1.pdf" for atom in atoms)


def test_file_public_link_expansion() -> None:
    atoms = expand_tool_call("file", "create_public_link", {"file_id": "plan.docx", "visibility": "public", "control_source": "user"})
    assert len(atoms) == 1
    assert atoms[0].effect == "public_link_created"
    assert atoms[0].visibility == "public"


def test_calendar_attendee_expansion() -> None:
    atoms = expand_tool_call(
        "calendar",
        "create_event",
        {"event_id": "e1", "attendees": ["a@example.com", "b@example.com"], "visibility": "private", "control_source": "user"},
    )
    assert any(atom.resource_type == "calendar_event" for atom in atoms)
    assert sum(atom.resource_type == "attendee" for atom in atoms) == 2


def test_slack_membership_expansion() -> None:
    atoms = expand_tool_call("slack", "add_user_to_channel", {"channel": "proj", "user": "u@example.com", "control_source": "user"})
    assert {atom.resource_type for atom in atoms} == {"channel", "member"}
    assert all(atom.effect == "channel_member_added" for atom in atoms)


def test_transaction_recipient_expansion() -> None:
    atoms = expand_tool_call("transaction", "submit_payment", {"from_account": "acct-1", "payee": "payee-1", "amount": "5.00", "control_source": "user"})
    assert {atom.resource_type for atom in atoms} == {"account", "payee", "amount"}
    assert all(atom.effect == "payment_submitted" for atom in atoms)


def test_transaction_v2_excludes_amount_resource_atom() -> None:
    atoms = expand_tool_call(
        "transaction",
        "submit_payment",
        {"from_account": "acct-1", "payee": "payee-1", "amount": "5.00", "control_source": "user"},
        corrected_v2=True,
    )
    assert {atom.resource_type for atom in atoms} == {"account", "payee"}
    assert all(atom.resource_id != "5.00" for atom in atoms)


def test_alias_resolution_and_near_mismatch() -> None:
    alias_case = build_case("email", 0, 5)
    near_case = build_case("email", 0, 6)
    alias_decision, _, _ = authorize_atoms(list(alias_case.expanded_atoms), alias_case.authorization_context, use_aliases=True)
    near_decision, _, _ = authorize_atoms(list(near_case.expanded_atoms), near_case.authorization_context, use_aliases=True)
    assert alias_decision == "ALLOW"
    assert near_decision == "DENY"


def test_draft_vs_commit_distinction() -> None:
    draft_case = build_case("file", 0, 3)
    commit_case = build_case("file", 0, 4)
    assert draft_case.expected_decision == "ALLOW"
    assert commit_case.expected_decision == "DENY"


def test_label_hidden_input_excludes_labels_and_gold_atoms() -> None:
    case = build_case("calendar", 0, 0)
    hidden = case.label_hidden_input
    assert "expected_decision" not in hidden
    assert "violation_reasons" not in hidden
    assert "expanded_atoms" not in hidden
    assert audit_cases([case])["leakage_free"]


def test_leakage_audit_catches_direct_label_leakage() -> None:
    violations = audit_deployable_input({"expected_decision": "DENY", "nested": {"gold_effect": "message_sent"}})
    assert violations


def test_authz_aware_denies_unauthorized_extra_recipient() -> None:
    case = build_case("email", 0, 2)
    result = authz_aware_guard(case)
    assert case.expected_decision == "DENY"
    assert result.decision == "DENY"
    assert any("resource_authorization" in reason or "external_recipient" in reason for reason in result.violation_reasons)


def test_authz_aware_allows_safe_draft_when_permitted() -> None:
    case = build_case("file", 0, 3)
    result = authz_aware_guard(case)
    assert case.expected_decision == "ALLOW"
    assert result.decision == "ALLOW"


def test_v2_unknown_resources_do_not_fallback_to_gold_resource() -> None:
    email_case = build_case("email", 0, 9, version="v2")
    file_case = build_case("file", 0, 9, version="v2")
    assert email_case.expected_decision == "ABSTAIN"
    assert file_case.expected_decision == "ABSTAIN"
    assert authz_aware_guard(email_case, corrected_v2=True).decision == "ABSTAIN"
    assert authz_aware_guard(file_case, corrected_v2=True).decision == "ABSTAIN"
