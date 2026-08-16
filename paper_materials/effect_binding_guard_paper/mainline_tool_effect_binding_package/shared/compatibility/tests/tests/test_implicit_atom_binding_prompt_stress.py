from __future__ import annotations

import json

from src.experiments.effect_binding_guard.atom_targeted_prompt_guidance.implicit_dataset import (
    CASES,
    deployable_rows,
    label_rows,
)
from src.experiments.effect_binding_guard.atom_targeted_prompt_guidance.implicit_dataset_v2 import (
    deployable_rows as v2_deployable_rows,
)
from src.experiments.effect_binding_guard.atom_targeted_prompt_guidance.run_multimethod import (
    NEUTRAL,
    VALIDATED,
    interfaces,
    victim_messages,
)
from src.experiments.effect_binding_guard.atomized_tool_description_self_governance.descriptors import (
    load_neutral_controls,
    load_validated_descriptors,
)


def descriptor_inputs():
    return load_validated_descriptors(VALIDATED), load_neutral_controls(NEUTRAL)


def test_implicit_dataset_is_frozen_paired_and_label_hidden() -> None:
    rows = deployable_rows()
    assert len(CASES) == 8
    assert len(rows) == 16
    assert len(label_rows()) == 8
    assert len({row["axis"] for row in rows}) == 8
    for row in rows:
        text = json.dumps(row, sort_keys=True).lower()
        assert "important instructions" not in text
        assert "untrusted_insert" not in text
        assert '"expected"' not in text
        assert '"attack"' not in text
        assert "gold_atoms" not in text


def test_pairs_change_only_runtime_evidence() -> None:
    by_case = {}
    for row in deployable_rows():
        by_case.setdefault(row["case_id"], []).append(row)
    for pair in by_case.values():
        clean, injected = sorted(pair, key=lambda row: row["variant"])
        for key in clean:
            if key not in {"variant", "evidence"}:
                assert clean[key] == injected[key]
        assert clean["evidence"] != injected["evidence"]


def test_v2_uses_schema_shaped_single_field_mutations_without_markers() -> None:
    rows = v2_deployable_rows()
    assert len(rows) == 16
    for row in rows:
        lowered = row["evidence"].lower()
        assert "resolved_tool_arguments" in lowered or "resolver_output" in lowered
        assert "important instructions" not in lowered
        assert "untrusted_insert" not in lowered
    by_case = {}
    for row in rows:
        by_case.setdefault(row["case_id"], []).append(row)
    for pair in by_case.values():
        clean, injected = sorted(pair, key=lambda row: row["variant"])
        assert clean["task"] == injected["task"]
        assert clean["tools"] == injected["tools"]
        assert clean["evidence"] != injected["evidence"]


def test_shuffled_control_preserves_fields_but_changes_roles() -> None:
    validated, neutral = descriptor_inputs()
    row = next(row for row in deployable_rows() if "send_channel_message" in row["tools"])
    correct = interfaces("ours_validated_atom_prompt", row, validated, neutral)["send_channel_message"]
    shuffled = interfaces("field_shuffled_atom_prompt", row, validated, neutral)["send_channel_message"]
    assert correct != shuffled
    assert "body, channel" in correct and "body, channel" in shuffled
    assert "Effect kind: write" in correct and "Effect kind: write" in shuffled
    assert "body->data_payload" in correct
    assert "body->target_principal" in shuffled
    assert "channel->data_payload" in shuffled


def test_shuffled_and_correct_atom_conditions_are_prompt_only() -> None:
    validated, neutral = descriptor_inputs()
    row = deployable_rows()[0]
    for method in ("field_shuffled_atom_prompt", "ours_validated_atom_prompt"):
        messages = victim_messages(method, row, row["evidence"], validated, neutral)
        text = "\n".join(message["content"] for message in messages).lower()
        assert "runtime guard" not in text
        assert "deny this call" not in text
        assert "expected decision" not in text


def test_v2_no_guard_view_does_not_prelabel_trust_boundaries() -> None:
    validated, neutral = descriptor_inputs()
    row = v2_deployable_rows()[0]
    messages = victim_messages("no_guard", row, row["evidence"], validated, neutral)
    text = "\n".join(message["content"] for message in messages)
    assert "AUTHENTICATED_TASK" not in text
    assert "TRUSTED_CONTEXT" not in text
    assert "authenticated task" not in text.lower()
    assert "USER_TASK" in text
