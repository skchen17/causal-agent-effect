from __future__ import annotations

from src.experiments.effect_binding_guard.e80_contract_obligation_hardening import (
    AuthorityManifest,
    FieldAuthority,
    FieldDefault,
    mediate_hardened_call,
)


def manifest() -> AuthorityManifest:
    return AuthorityManifest(
        task_id="task-1",
        tools={
            "share_file": {
                "resource_id": FieldAuthority(mode="resolve", resolver_id="lookup_requested_file"),
                "recipients": FieldAuthority(
                    mode="exact", exact_values=("alice@example.com",), source_spans=("share with Alice",)
                ),
                "visibility": FieldAuthority(mode="forbidden"),
            }
        },
        resolver_catalog=frozenset({"lookup_requested_file"}),
    )


def proposal(recipient="alice@example.com", resolver="lookup_requested_file"):
    return {
        "tools": {"share_file": {"fields": {
            "resource_id": {"mode": "resolve", "resolver_id": resolver},
            "recipients": {"mode": "exact", "values": [recipient]},
            "visibility": {"mode": "forbidden"},
        }}}
    }


def mediate(arguments, proposed=None, ledger=None, visibility_default="private"):
    return mediate_hardened_call(
        tool_name="share_file",
        arguments=arguments,
        field_semantics={
            "resource_id": FieldDefault(required=True),
            "recipients": FieldDefault(required=True),
            "visibility": FieldDefault(static_default=visibility_default),
        },
        security_fields=["resource_id", "recipients", "visibility"],
        inactive_values={"visibility": ["private"]},
        proposal=proposed or proposal(),
        manifest=manifest(),
        resolver_ledger=ledger or [{
            "resolver_id": "lookup_requested_file", "values": ["file-1"],
            "typed_projection": True, "provenance": "authorized_read",
        }],
        registry_hash="registry-v1",
    )


def test_valid_totalized_call_allows_without_runtime_llm() -> None:
    result = mediate({"resource_id": "file-1", "recipients": ["alice@example.com"]})
    assert result["decision"] == "ALLOW"
    assert result["instantiated_defaults"] == ["visibility"]
    assert result["runtime_called_llm"] is False
    assert result["totalized_call_hash"]


def test_invented_plan_literal_and_resolver_abstain() -> None:
    invented_literal = mediate(
        {"resource_id": "file-1", "recipients": ["attacker@example.com"]},
        proposed=proposal(recipient="attacker@example.com"),
    )
    invented_resolver = mediate(
        {"resource_id": "file-1", "recipients": ["alice@example.com"]},
        proposed=proposal(resolver="search_any_output"),
    )
    assert invented_literal["decision"] == "ABSTAIN"
    assert invented_resolver["decision"] == "ABSTAIN"


def test_nonempty_default_is_checked_and_denied() -> None:
    result = mediate(
        {"resource_id": "file-1", "recipients": ["alice@example.com"]},
        visibility_default="public",
    )
    assert result["decision"] == "DENY"
    assert any(check["field"] == "visibility" and check["status"] == "forbidden_value_used" for check in result["checks"])


def test_each_multi_recipient_value_is_checked() -> None:
    result = mediate({
        "resource_id": "file-1",
        "recipients": ["alice@example.com", "attacker@example.com"],
    })
    assert result["decision"] == "DENY"
    recipient_checks = [check for check in result["checks"] if check["field"] == "recipients"]
    assert len(recipient_checks) == 2


def test_only_matching_typed_authorized_resolver_evidence_allows() -> None:
    untyped = mediate(
        {"resource_id": "file-1", "recipients": ["alice@example.com"]},
        ledger=[{"resolver_id": "lookup_requested_file", "values": ["file-1"], "typed_projection": False, "provenance": "authorized_read"}],
    )
    untrusted = mediate(
        {"resource_id": "file-1", "recipients": ["alice@example.com"]},
        ledger=[{"resolver_id": "lookup_requested_file", "values": ["file-1"], "typed_projection": True, "provenance": "untrusted_text"}],
    )
    assert untyped["decision"] == "ABSTAIN"
    assert untrusted["decision"] == "ABSTAIN"


def test_dynamic_default_and_unknown_field_fail_closed() -> None:
    dynamic = mediate_hardened_call(
        tool_name="share_file",
        arguments={"resource_id": "file-1", "recipients": ["alice@example.com"]},
        field_semantics={
            "resource_id": FieldDefault(required=True),
            "recipients": FieldDefault(required=True),
            "visibility": FieldDefault(dynamic_default=True),
        },
        security_fields=["resource_id", "recipients", "visibility"],
        inactive_values={"visibility": ["private"]},
        proposal=proposal(), manifest=manifest(), resolver_ledger=[], registry_hash="r",
    )
    unknown = mediate({"resource_id": "file-1", "recipients": ["alice@example.com"], "hidden": True})
    assert dynamic["decision"] == "ABSTAIN"
    assert unknown["decision"] == "ABSTAIN"
