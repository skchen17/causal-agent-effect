"""Tests for the corrected atom-specificity runner's explicit condition schema.

Guards against the Round 1--5 wiring defect where a positional boolean
tuple element named `is_atom` was fed into the `shuffle` parameter. These
tests enforce the three pre-registered invariants:

1. correct and shuffled conditions must produce different prompt hashes;
2. correct conditions must preserve the registry's original field roles;
3. the neutral control (no_guard) must stay tokenizer-exact with BASE_SYSTEM.
"""

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCRIPT_DIR = (
    _REPO_ROOT
    / "experiments"
    / "intent-bound-runtime-guard"
    / "source"
    / "atom-targeted-prompt-guidance"
)
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import atom_specificity_corrected as corrected  # noqa: E402


def _by_id(condition_id: str) -> corrected.ConditionSpec:
    for spec in corrected.CONDITIONS:
        if spec.condition_id == condition_id:
            return spec
    raise AssertionError(f"missing condition {condition_id}")


@pytest.fixture(scope="module")
def validated() -> dict:
    return corrected.load_validated()


def test_conditions_use_explicit_named_schema() -> None:
    ids = [spec.condition_id for spec in corrected.CONDITIONS]
    assert ids == [
        "no_guard",
        "generic_intent",
        "atom_without_rules",
        "atom_with_rules",
        "atom_shuffled_rules",
    ]
    for spec in corrected.CONDITIONS:
        # Every flag is a declared named field; positional tuples are banned.
        assert isinstance(spec.uses_intent, bool)
        assert isinstance(spec.uses_atom, bool)
        assert isinstance(spec.uses_grounding_rules, bool)
        assert isinstance(spec.shuffle_roles, bool)
        if spec.uses_grounding_rules or spec.shuffle_roles:
            assert spec.uses_atom


def test_condition_spec_rejects_inconsistent_flags() -> None:
    with pytest.raises(ValueError):
        corrected.ConditionSpec(
            "bad", "bad", uses_intent=True, uses_atom=False,
            uses_grounding_rules=True, shuffle_roles=False,
        )
    with pytest.raises(ValueError):
        corrected.ConditionSpec(
            "bad", "bad", uses_intent=True, uses_atom=False,
            uses_grounding_rules=False, shuffle_roles=True,
        )


def test_correct_and_shuffled_prompt_hashes_differ(validated) -> None:
    correct = _by_id("atom_with_rules")
    shuffled = _by_id("atom_shuffled_rules")
    diverging = 0
    for case in corrected.CASES:
        for variant in ("clean_evidence", "injected_evidence"):
            evidence = case[variant]
            m_correct = corrected.build_messages(correct, case, evidence, validated)
            m_shuffled = corrected.build_messages(shuffled, case, evidence, validated)
            h_correct = corrected.prompt_hash(m_correct)
            h_shuffled = corrected.prompt_hash(m_shuffled)
            assert h_correct != h_shuffled, (
                f"{case['case_id']}/{variant}: correct and shuffled prompts are identical; "
                "the role-permutation contrast is void"
            )
            if corrected.multiple_distinct_roles(validated.get(case["expected_tool"], {})):
                diverging += 1
    # At least one case must exercise a genuinely permuted role assignment.
    assert diverging >= 1


def test_correct_condition_preserves_registry_roles(validated) -> None:
    correct = _by_id("atom_with_rules")
    for case in corrected.CASES:
        for tool_name in case.get("tools", {}):
            row = validated.get(tool_name)
            if row is None:
                continue
            original = corrected.registry_roles(row)
            supplement = corrected.render_atom_supplement(
                row, uses_grounding_rules=True, shuffle_roles=False
            )
            for field_name, role in original.items():
                assert f"{field_name}->{role}" in supplement, (
                    f"{tool_name}.{field_name}: correct condition must render "
                    f"the registry role {role!r} unchanged"
                )
            messages = corrected.build_messages(correct, case, case["clean_evidence"], validated)
            system_text = messages[0]["content"]
            for field_name, role in original.items():
                assert f"{field_name}->{role}" in system_text


def test_shuffled_roles_rotate_deterministically() -> None:
    original = {"a": "target_principal", "b": "data_payload", "c": "scope_constraint"}
    shuffled = corrected.shuffled_roles(original)
    assert shuffled != original
    assert sorted(shuffled.values()) == sorted(original.values())
    assert corrected.shuffled_roles(original) == shuffled
    uniform = {"a": "data_payload", "b": "data_payload"}
    assert corrected.shuffled_roles(uniform) == uniform


def test_neutral_control_is_tokenizer_exact(validated) -> None:
    no_guard = _by_id("no_guard")
    for case in corrected.CASES:
        for variant in ("clean_evidence", "injected_evidence"):
            messages = corrected.build_messages(no_guard, case, case[variant], validated)
            assert messages[0]["content"] == corrected.BASE_SYSTEM
            assert len(messages) == 2
            joined = messages[0]["content"]
            assert "ATOMIZED_EFFECT_INTERFACE" not in joined
            assert "intent" not in joined.lower() or joined == corrected.BASE_SYSTEM


def test_no_condition_leaks_labels_into_prompts(validated) -> None:
    for spec in corrected.CONDITIONS:
        for case in corrected.CASES:
            messages = corrected.build_messages(spec, case, case["injected_evidence"], validated)
            serialized = json.dumps(messages, sort_keys=True).lower()
            for banned in ("expected_args", "attack_args", "expected_tool", "gold"):
                assert banned not in serialized


def test_prompt_hashes_are_stable_and_distinct_per_condition(validated) -> None:
    hashes: dict[str, set] = {}
    case = corrected.CASES[0]
    for spec in corrected.CONDITIONS:
        messages = corrected.build_messages(spec, case, case["clean_evidence"], validated)
        hashes.setdefault(spec.condition_id, set()).add(corrected.prompt_hash(messages))
        assert corrected.prompt_hash(messages) == corrected.prompt_hash(messages)
    all_hashes = [h for group in hashes.values() for h in group]
    assert len(all_hashes) == len(set(all_hashes)), "conditions must not share prompt hashes"
