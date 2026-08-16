from __future__ import annotations

import json
import re
from typing import Any

from .schemas import E55Case


FORBIDDEN_KEY_TOKENS = (
    "expected_decision",
    "violation_reasons",
    "expanded_atoms",
    "gold",
    "oracle",
    "risk_label",
    "unsafe_label",
    "safe_label",
    "expected_label",
)

FORBIDDEN_STRING_TOKENS = (
    "expected_decision",
    "violation_reasons",
    "gold_",
    "oracle_",
    "__allow__",
    "__deny__",
    "__unsafe__",
    "__safe__",
    "outside_scope",
)

LABELISH_ID_PATTERN = re.compile(r"(?:^|[_-])(allow|deny|unsafe|safe|gold|expected)(?:[_-]|$)", re.IGNORECASE)


def audit_cases(cases: list[E55Case]) -> dict[str, Any]:
    violations = []
    for case in cases:
        input_violations = audit_deployable_input(case.label_hidden_input)
        id_violation = bool(LABELISH_ID_PATTERN.search(case.case_id))
        if input_violations or id_violation:
            violations.append(
                {
                    "case_id": case.case_id,
                    "input_violations": input_violations,
                    "case_id_label_marker": id_violation,
                }
            )
    return {
        "n_cases": len(cases),
        "n_violations": len(violations),
        "violations": violations,
        "leakage_free": len(violations) == 0,
        "notes": (
            "`allowed_*` fields inside authorization_context are visible authorization infrastructure, "
            "not label leakage. Resource strings are checked for artificial outside_scope markers."
        ),
    }


def audit_deployable_input(value: Any) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []

    def visit(obj: Any, path: str) -> None:
        if isinstance(obj, dict):
            for key, child in obj.items():
                key_text = str(key)
                key_path = f"{path}.{key_text}" if path else key_text
                if is_forbidden_key(key_text):
                    violations.append({"path": key_path, "kind": "forbidden_key", "value": key_text})
                visit(child, key_path)
        elif isinstance(obj, list):
            for index, child in enumerate(obj):
                visit(child, f"{path}[{index}]")
        elif isinstance(obj, str):
            lower = obj.lower()
            for token in FORBIDDEN_STRING_TOKENS:
                if token in lower:
                    violations.append({"path": path, "kind": "forbidden_string_token", "value": token})

    visit(value, "")
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True).lower()
    if '"expected_decision"' in serialized or '"violation_reasons"' in serialized or '"expanded_atoms"' in serialized:
        violations.append({"path": "$", "kind": "serialized_marker", "value": "direct_label_field"})
    return violations


def is_forbidden_key(key: str) -> bool:
    if key.startswith("allowed_"):
        return False
    if key == "non_oracle_views":
        return False
    return any(token in key for token in FORBIDDEN_KEY_TOKENS)
