from __future__ import annotations

from src.experiments.effect_binding_guard.e80_contract_obligation_hardening import (
    AuthorityManifest,
    FieldAuthority,
    FieldDefault,
    totalize_call,
    validate_plan_against_manifest,
)


def manifest() -> AuthorityManifest:
    return AuthorityManifest(
        task_id="task-1",
        tools={
            "send_email": {
                "recipients": FieldAuthority(
                    mode="exact",
                    exact_values=("alice@example.com",),
                    source_spans=("Email Alice",),
                ),
                "attachment_ids": FieldAuthority(
                    mode="resolve",
                    resolver_id="lookup_named_attachment",
                ),
                "bcc": FieldAuthority(mode="forbidden"),
            }
        },
        resolver_catalog=frozenset({"lookup_named_attachment"}),
    )


def test_independent_manifest_accepts_narrow_grounded_plan() -> None:
    proposal = {
        "tools": {
            "send_email": {
                "fields": {
                    "recipients": {"mode": "exact", "values": ["alice@example.com"]},
                    "attachment_ids": {"mode": "resolve", "resolver_id": "lookup_named_attachment"},
                    "bcc": {"mode": "forbidden"},
                }
            }
        }
    }
    result = validate_plan_against_manifest(proposal, manifest())
    assert result.accepted
    assert result.bounded_plan["authority_source"] == "independent_manifest"


def test_independent_manifest_rejects_invented_exact_literal() -> None:
    proposal = {
        "tools": {
            "send_email": {
                "fields": {"recipients": {"mode": "exact", "values": ["attacker@example.com"]}}
            }
        }
    }
    result = validate_plan_against_manifest(proposal, manifest())
    assert not result.accepted
    assert result.violations == ("literal_not_grounded:send_email.recipients",)


def test_independent_manifest_rejects_invented_resolver() -> None:
    proposal = {
        "tools": {
            "send_email": {
                "fields": {"attachment_ids": {"mode": "resolve", "resolver_id": "search_any_tool_output"}}
            }
        }
    }
    result = validate_plan_against_manifest(proposal, manifest())
    assert not result.accepted
    assert result.violations == ("resolver_not_authorized:send_email.attachment_ids",)


def test_static_nonempty_default_is_instantiated_before_authorization() -> None:
    totalized = totalize_call(
        {"resource_id": "doc-1"},
        {
            "resource_id": FieldDefault(required=True),
            "visibility": FieldDefault(static_default="public"),
            "notify": FieldDefault(static_default=True),
        },
    )
    assert totalized.resolved
    assert totalized.arguments == {"resource_id": "doc-1", "visibility": "public", "notify": True}
    assert totalized.instantiated_defaults == ("notify", "visibility")


def test_omitted_and_explicit_static_defaults_are_decision_equivalent() -> None:
    semantics = {
        "resource_id": FieldDefault(required=True),
        "visibility": FieldDefault(static_default="public"),
    }
    omitted = totalize_call({"resource_id": "doc-1"}, semantics)
    explicit = totalize_call({"resource_id": "doc-1", "visibility": "public"}, semantics)
    assert omitted.arguments == explicit.arguments


def test_dynamic_or_unknown_default_fails_closed() -> None:
    dynamic = totalize_call(
        {"resource_id": "doc-1"},
        {
            "resource_id": FieldDefault(required=True),
            "owner": FieldDefault(dynamic_default=True),
        },
    )
    unknown = totalize_call(
        {"resource_id": "doc-1"},
        {"resource_id": FieldDefault(required=True), "visibility": FieldDefault()},
    )
    assert not dynamic.resolved and dynamic.reasons == ("dynamic_default_unresolved:owner",)
    assert not unknown.resolved and unknown.reasons == ("default_semantics_unknown:visibility",)
