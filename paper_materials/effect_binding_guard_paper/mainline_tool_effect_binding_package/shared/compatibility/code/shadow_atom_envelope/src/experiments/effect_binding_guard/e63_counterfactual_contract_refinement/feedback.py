from __future__ import annotations

from collections import Counter
from typing import Any

from src.experiments.effect_binding_guard.e60_effect_contract_prototype.contracts import ValidationResult
from src.experiments.effect_binding_guard.e62_local_llm_proposer_validation.failure_analysis import classify_failure, hints_for_categories
from src.experiments.effect_binding_guard.e62_local_llm_proposer_validation.prompting import FORBIDDEN_PROMPT_TERMS


EXTRA_FORBIDDEN_FEEDBACK_TERMS = (
    "expected_base_atoms",
    "expected_mutated_atoms",
    "expected_base_decision",
    "expected_mutated_decision",
    "expected_violation_reasons",
    "missing\":",
)


def build_feedback_payload(
    *,
    parse_error: str = "",
    validation: ValidationResult | None = None,
    round_index: int,
) -> dict[str, Any]:
    categories = classify_failure(parse_error=parse_error, validation=validation)
    payload: dict[str, Any] = {
        "round_index": round_index,
        "feedback_policy": "sanitized_counterfactual_summary_no_hidden_evaluation_materials",
        "failure_categories": categories,
        "repair_hints": hints_for_categories(categories),
    }
    if parse_error:
        payload["parse_status"] = "invalid"
        payload["parse_error_class"] = parse_error.split(":", 1)[0]
    if validation is not None:
        payload.update(
            {
                "parse_status": "valid",
                "validation_passed": validation.passed,
                "metrics": {
                    "required_atom_coverage": validation.required_atom_coverage,
                    "required_resource_binding_coverage": validation.required_resource_binding_coverage,
                    "required_target_principal_coverage": validation.required_target_principal_coverage,
                    "unsafe_pre_allow_rate": validation.unsafe_pre_allow_rate,
                    "false_deny_rate": validation.false_deny_rate,
                    "coverage": validation.coverage,
                    "decision_accuracy": validation.decision_accuracy,
                    "missing_required_atom_count": validation.missing_required_atom_count,
                },
                "failed_axes": failed_axis_counts(validation),
                "n_failures_shown": len(validation.failures),
            }
        )
    scan = feedback_leakage_scan(payload)
    payload["leakage_free"] = scan["leakage_free"]
    payload["leakage_hits"] = scan["hits"]
    return payload


def failed_axis_counts(validation: ValidationResult) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for failure in validation.failures:
        axis = str(failure.get("axis", "unknown_axis"))
        counts[axis] += 1
    return dict(sorted(counts.items()))


def feedback_leakage_scan(payload: dict[str, Any]) -> dict[str, Any]:
    text = repr(payload).lower()
    hits = [term for term in FORBIDDEN_PROMPT_TERMS + EXTRA_FORBIDDEN_FEEDBACK_TERMS if term in text]
    return {"leakage_free": not hits, "hits": hits}
