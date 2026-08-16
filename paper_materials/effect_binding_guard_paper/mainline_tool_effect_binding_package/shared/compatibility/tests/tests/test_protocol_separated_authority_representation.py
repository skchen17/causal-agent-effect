from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest

from shared.compatibility.scripts.independent_authority_benchmark import (
    authority_model,
    context_generator,
    descriptor_runtime,
    sandbox,
    specs,
    transition_oracle,
)


def descriptor_map():
    return {item["tool_name"]: item for item in specs.descriptor_candidates()["descriptors"]}


def test_oracle_and_descriptor_modules_do_not_import_each_other():
    oracle_tree = ast.parse(Path(transition_oracle.__file__).read_text(encoding="utf-8"))
    descriptor_tree = ast.parse(Path(descriptor_runtime.__file__).read_text(encoding="utf-8"))
    oracle_imports = [node for node in ast.walk(oracle_tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    descriptor_imports = [node for node in ast.walk(descriptor_tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert "descriptor" not in " ".join(ast.unparse(node) for node in oracle_imports)
    assert "transition_oracle" not in " ".join(ast.unparse(node) for node in descriptor_imports)


def test_evaluation_generator_is_label_and_descriptor_blind():
    rows = context_generator.generate_evaluation(context_generator.generator_config())
    assert len(rows) == 1024
    forbidden = {"gold_label", "ideal_decision", "typed_effects", "descriptor", "expected_decision"}
    assert all(not forbidden.intersection(row) for row in rows)
    assert {row["stratum"] for row in rows} == {"routine", "boundary"}
    assert all(len([item for item in rows if item["argument_group_id"] == row["argument_group_id"]]) == 4 for row in rows[:16])


def test_registration_counterfactuals_match_independent_oracle():
    rows = context_generator.generate_registration(context_generator.generator_config())
    descriptors = descriptor_map()
    assert len(rows) == 384
    for row in rows:
        source = transition_oracle.derive(row["pre_state"], sandbox.execute(row), row["tool_name"])
        atoms = descriptor_runtime.compile_descriptor(descriptors[row["tool_name"]], row)
        typed = [{
            "operation": atom["operation"], "resource_type": atom["resource_type"], "resource_id": atom["resource_id"],
            "target_principal": atom["target_principal"], "attributes": atom["qualifiers"], "commit_mode": atom["commit_mode"],
        } for atom in atoms]
        assert source == typed


def test_descriptor_is_executable_data_not_ornamental_manifest():
    row = context_generator.generate_registration(context_generator.generator_config())[0]
    original = descriptor_map()[row["tool_name"]]
    changed = copy.deepcopy(original)
    changed["rules"][0]["emit"]["operation"] = "calendar.draft.changed"
    draft_row = copy.deepcopy(row)
    draft_row["arguments"]["commit_mode"] = "draft"
    before = descriptor_runtime.compile_descriptor(original, draft_row)
    after = descriptor_runtime.compile_descriptor(changed, draft_row)
    assert before != after


def test_frozen_sorted_json_does_not_change_descriptor_dependencies():
    row = next(item for item in context_generator.generate_registration(context_generator.generator_config()) if item["tool_name"] == "post_message")
    descriptor = descriptor_map()["post_message"]
    sorted_round_trip = json.loads(json.dumps(descriptor, sort_keys=True))
    assert descriptor_runtime.compile_descriptor(descriptor, row) == descriptor_runtime.compile_descriptor(sorted_round_trip, row)


def test_workspace_revoke_uses_pre_state_permission():
    row = next(item for item in context_generator.generate_registration(context_generator.generator_config()) if item["tool_name"] == "share_document")
    row = copy.deepcopy(row)
    row["arguments"].update({"operation": "revoke", "permission": "commenter", "recipients": ["alice"]})
    row["pre_state"]["documents"]["doc:report"]["acl"]["alice"] = "viewer"
    atoms = descriptor_runtime.compile_descriptor(descriptor_map()["share_document"], row)
    revoke = next(atom for atom in atoms if atom["operation"] == "document.share.revoke")
    assert revoke["qualifiers"]["permission"] == "viewer"


def test_sandbox_does_not_mutate_frozen_pre_state():
    row = context_generator.generate_registration(context_generator.generator_config())[0]
    before = copy.deepcopy(row["pre_state"])
    sandbox.execute(row)
    assert row["pre_state"] == before


def test_acl_capability_and_delegation_paths_are_live():
    state = authority_model.authority_state()
    acl = {"subject": "agent:assistant", "operation": "calendar.participant.invite", "resource_type": "calendar",
           "resource_id": "calendar:team", "target_principal": "alice@example.com", "attributes": {}, "commit_mode": "commit"}
    cap = {"subject": "agent:assistant", "operation": "message.post", "resource_type": "channel",
           "resource_id": "channel:internal", "target_principal": None, "attributes": {"payload_class": "internal"}, "commit_mode": "commit"}
    delegation = {"subject": "agent:assistant", "operation": "bank.transfer.commit", "resource_type": "bank_account",
                  "resource_id": "account:checking", "target_principal": "payee:acme", "attributes": {"amount": 100, "currency": "USD"}, "commit_mode": "commit"}
    assert authority_model.authorize_request(acl, state, authority_model.default_context("calendar"), partial=False)[0] == "ALLOW"
    assert authority_model.authorize_request(cap, state, authority_model.default_context("messaging"), partial=False)[0] == "ALLOW"
    assert authority_model.authorize_request(delegation, state, authority_model.default_context("banking"), partial=False)[0] == "ALLOW"
    no_cap = {**authority_model.default_context("messaging"), "active_capabilities": []}
    assert authority_model.authorize_request(cap, state, no_cap, partial=False)[0] == "DENY"
    no_delegation = {**authority_model.default_context("banking"), "active_delegations": []}
    assert authority_model.authorize_request(delegation, state, no_delegation, partial=False)[0] == "DENY"


def test_partial_authority_facts_abstain_and_known_violations_deny():
    state = authority_model.authority_state()
    context = authority_model.default_context("calendar")
    incomplete = {"subject": "agent:assistant", "operation": "calendar.participant.invite", "resource_type": "calendar",
                  "resource_id": None, "target_principal": "alice@example.com", "attributes": {}, "commit_mode": "commit"}
    unauthorized = {**incomplete, "resource_id": "calendar:team", "target_principal": "eve@example.com"}
    assert authority_model.authorize_request(incomplete, state, context, partial=True)[0] == "ABSTAIN"
    assert authority_model.authorize_request(unauthorized, state, context, partial=True)[0] == "DENY"


def test_complete_empty_effect_inventory_allows_noop():
    state = authority_model.authority_state()
    context = authority_model.default_context("workspace")
    assert authority_model.authorize_all([], state, context, partial=True, inventory_complete=True)[0] == "ALLOW"
    assert authority_model.authorize_all([], state, context, partial=True, inventory_complete=False)[0] == "ABSTAIN"


def test_malformed_descriptor_fails_closed():
    row = context_generator.generate_registration(context_generator.generator_config())[0]
    malformed = copy.deepcopy(descriptor_map()[row["tool_name"]])
    del malformed["schema_version"]
    with pytest.raises(ValueError):
        descriptor_runtime.compile_descriptor(malformed, row)
