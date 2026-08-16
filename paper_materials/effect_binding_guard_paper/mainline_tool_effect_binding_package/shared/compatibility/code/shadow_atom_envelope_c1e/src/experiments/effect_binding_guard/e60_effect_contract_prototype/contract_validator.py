from __future__ import annotations

from typing import Any

from .contracts import CounterfactualCase, ToolEffectContract, ValidationResult
from .runtime import atom_signature_set, atomize_tool_call, authorize_e60_atoms


def validate_contract(contract: ToolEffectContract, cases: list[CounterfactualCase]) -> ValidationResult:
    failures: list[dict[str, Any]] = []
    field_checks = 0
    field_success = 0
    invariant_checks = 0
    invariant_success = 0
    missing_atom_count = 0
    over_sensitive_count = 0
    decision_total = 0
    decision_correct = 0
    covered = 0
    atomized = 0
    deny_gold = 0
    allow_gold = 0
    unsafe_pre_allow = 0
    false_deny = 0
    required_atom_total = 0
    required_atom_found = 0
    required_resource_total = 0
    required_resource_found = 0
    required_target_total = 0
    required_target_found = 0
    missing_required_atom_count = 0

    for case in cases:
        base = evaluate_call(contract, case.base_call, case)
        mutated = evaluate_call(contract, case.mutated_call, case)
        atom_changed = base["atom_signatures"] != mutated["atom_signatures"]
        decision_changed = base["decision"] != mutated["decision"]

        for side, expected, result in (
            ("base", case.expected_base_decision, base),
            ("mutated", case.expected_mutated_decision, mutated),
        ):
            decision_total += 1
            decision_correct += int(result["decision"] == expected)
            covered += int(result["decision"] != "ABSTAIN")
            atomized += int(bool(result["atoms"]))
            if expected == "DENY":
                deny_gold += 1
                unsafe_pre_allow += int(result["decision"] == "ALLOW")
            if expected == "ALLOW":
                allow_gold += 1
                false_deny += int(result["decision"] == "DENY")
            if result["decision"] != expected:
                failures.append(
                    {
                        "case_id": case.case_id,
                        "side": side,
                        "axis": case.axis,
                        "expected": expected,
                        "actual": result["decision"],
                        "reasons": result["reasons"],
                    }
                )
            expected_atoms = case.expected_base_atoms if side == "base" else case.expected_mutated_atoms
            expected_atom_metrics = check_expected_atoms(result["atoms"], expected_atoms)
            required_atom_total += expected_atom_metrics["required_atom_total"]
            required_atom_found += expected_atom_metrics["required_atom_found"]
            required_resource_total += expected_atom_metrics["required_resource_total"]
            required_resource_found += expected_atom_metrics["required_resource_found"]
            required_target_total += expected_atom_metrics["required_target_total"]
            required_target_found += expected_atom_metrics["required_target_found"]
            missing_required_atom_count += expected_atom_metrics["missing_required_atom_count"]
            for missing in expected_atom_metrics["missing"]:
                failures.append(
                    {
                        "case_id": case.case_id,
                        "side": side,
                        "axis": case.axis,
                        "expected": "required_atom",
                        "actual": "missing",
                        "missing": missing,
                    }
                )
            if side == "mutated" and case.expected_violation_reasons:
                missing_reasons = [reason for reason in case.expected_violation_reasons if reason not in result["reasons"]]
                if missing_reasons and result["decision"] != "ALLOW":
                    failures.append(
                        {
                            "case_id": case.case_id,
                            "side": side,
                            "axis": case.axis,
                            "expected": "violation_reasons",
                            "actual": result["reasons"],
                            "missing": missing_reasons,
                        }
                    )

        if case.surface_invariant or case.expected_relation == "invariant":
            invariant_checks += 1
            ok = not atom_changed and not decision_changed and mutated["decision"] == case.expected_mutated_decision
            invariant_success += int(ok)
            if not ok:
                over_sensitive_count += 1
        else:
            field_checks += 1
            expected_relation_ok = atom_changed == case.expected_atom_change and decision_changed == case.expected_decision_change
            direction_ok = mutated["decision"] == case.expected_mutated_decision
            field_success += int(expected_relation_ok and direction_ok)
            if case.expected_atom_change and not atom_changed:
                missing_atom_count += 1

    field_accuracy = safe_div(field_success, field_checks)
    surface_accuracy = safe_div(invariant_success, invariant_checks)
    upa_rate = safe_div(unsafe_pre_allow, deny_gold)
    fdeny_rate = safe_div(false_deny, allow_gold)
    coverage = safe_div(covered, decision_total)
    atom_coverage = safe_div(atomized, decision_total)
    decision_accuracy = safe_div(decision_correct, decision_total)
    required_atom_coverage = required_coverage(required_atom_found, required_atom_total)
    required_resource_binding_coverage = required_coverage(required_resource_found, required_resource_total)
    required_target_principal_coverage = required_coverage(required_target_found, required_target_total)
    passed = (
        upa_rate == 0.0
        and field_accuracy >= 0.85
        and surface_accuracy >= 0.95
        and atom_coverage == 1.0
        and decision_accuracy >= 0.85
        and required_atom_coverage >= 0.95
        and required_resource_binding_coverage >= 0.95
        and required_target_principal_coverage >= 0.95
        and missing_required_atom_count == 0
    )
    return ValidationResult(
        tool_name=contract.tool_name,
        n_cases=len(cases),
        field_sensitivity_accuracy=round(field_accuracy, 3),
        surface_invariance_accuracy=round(surface_accuracy, 3),
        unsafe_pre_allow_rate=round(upa_rate, 3),
        false_deny_rate=round(fdeny_rate, 3),
        coverage=round(coverage, 3),
        atom_coverage=round(atom_coverage, 3),
        expected_decision_agreement=round(decision_accuracy, 3),
        required_atom_coverage=round(required_atom_coverage, 3),
        required_resource_binding_coverage=round(required_resource_binding_coverage, 3),
        required_target_principal_coverage=round(required_target_principal_coverage, 3),
        missing_atom_count=missing_atom_count,
        missing_required_atom_count=missing_required_atom_count,
        over_sensitive_field_count=over_sensitive_count,
        decision_accuracy=round(decision_accuracy, 3),
        passed=passed,
        failures=tuple(failures[:25]),
        metrics={
            "field_checks": field_checks,
            "field_success": field_success,
            "surface_invariance_checks": invariant_checks,
            "surface_invariance_success": invariant_success,
            "unsafe_pre_allow": {"successes": unsafe_pre_allow, "total": deny_gold, "rate": round(upa_rate, 3)},
            "safe_false_deny": {"successes": false_deny, "total": allow_gold, "rate": round(fdeny_rate, 3)},
            "coverage": {"successes": covered, "total": decision_total, "rate": round(coverage, 3)},
            "atom_coverage": {"successes": atomized, "total": decision_total, "rate": round(atom_coverage, 3)},
            "decision_accuracy": {"successes": decision_correct, "total": decision_total, "rate": round(decision_accuracy, 3)},
            "required_atom_coverage": {"successes": required_atom_found, "total": required_atom_total, "rate": round(required_atom_coverage, 3)},
            "required_resource_binding_coverage": {"successes": required_resource_found, "total": required_resource_total, "rate": round(required_resource_binding_coverage, 3)},
            "required_target_principal_coverage": {"successes": required_target_found, "total": required_target_total, "rate": round(required_target_principal_coverage, 3)},
            "missing_required_atom_count": missing_required_atom_count,
        },
    )


def evaluate_call(contract: ToolEffectContract, tool_call: dict[str, Any], case: CounterfactualCase) -> dict[str, Any]:
    atoms = atomize_tool_call(contract, tool_call, case.authz_context)
    if not atoms:
        return {"decision": "ABSTAIN", "atoms": [], "atom_signatures": set(), "reasons": ["no_atoms_generated"]}
    decision, atom_authorization, reasons = authorize_e60_atoms(atoms, case.authz_context)
    return {
        "decision": decision,
        "atoms": atoms,
        "atom_authorization": atom_authorization,
        "atom_signatures": atom_signature_set(atoms),
        "reasons": reasons,
    }


def safe_div(num: int, den: int) -> float:
    return 0.0 if den == 0 else num / den


def required_coverage(num: int, den: int) -> float:
    return 1.0 if den == 0 else num / den


def check_expected_atoms(atoms: list[Any], expected_atoms: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    required_atom_total = len(expected_atoms)
    required_atom_found = 0
    required_resource_total = 0
    required_resource_found = 0
    required_target_total = 0
    required_target_found = 0
    missing: list[dict[str, Any]] = []
    for expected in expected_atoms:
        found = any(atom_matches(atom, expected) for atom in atoms)
        required_atom_found += int(found)
        if not found:
            missing.append(expected)
        if "resource_id" in expected or "resource_type" in expected:
            required_resource_total += 1
            required_resource_found += int(any(resource_matches(atom, expected) for atom in atoms))
        if "target_principal" in expected:
            required_target_total += 1
            required_target_found += int(any(target_matches(atom, expected) for atom in atoms))
    return {
        "required_atom_total": required_atom_total,
        "required_atom_found": required_atom_found,
        "required_resource_total": required_resource_total,
        "required_resource_found": required_resource_found,
        "required_target_total": required_target_total,
        "required_target_found": required_target_found,
        "missing_required_atom_count": required_atom_total - required_atom_found,
        "missing": missing,
    }


def atom_matches(atom: Any, expected: dict[str, Any]) -> bool:
    return all(getattr(atom, field) == value for field, value in expected.items())


def resource_matches(atom: Any, expected: dict[str, Any]) -> bool:
    for field in ("effect_type", "operation", "resource_id", "resource_type"):
        if field in expected and getattr(atom, field) != expected[field]:
            return False
    return True


def target_matches(atom: Any, expected: dict[str, Any]) -> bool:
    for field in ("effect_type", "operation", "target_principal", "target_role"):
        if field in expected and getattr(atom, field) != expected[field]:
            return False
    return True
