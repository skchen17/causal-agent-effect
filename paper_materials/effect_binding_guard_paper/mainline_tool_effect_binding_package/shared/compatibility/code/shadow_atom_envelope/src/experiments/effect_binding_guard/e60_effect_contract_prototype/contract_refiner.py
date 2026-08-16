from __future__ import annotations

from dataclasses import replace

from .contracts import ToolEffectContract, ToolSpec, ValidationResult
from .llm_contract_proposer import complete_templates, non_security_fields


def refine_contract(contract: ToolEffectContract, validation: ValidationResult, tool: ToolSpec) -> ToolEffectContract:
    actions: list[str] = []
    templates = list(contract.templates)
    requires_human_review = contract.requires_human_review

    if validation.missing_atom_count > 0 or validation.missing_required_atom_count > 0 or validation.unsafe_pre_allow_rate > 0.0:
        templates = complete_templates(tool.name)
        actions.append("restored_complete_stub_templates_for_missing_or_unsafe_atoms")

    if validation.over_sensitive_field_count > 0:
        actions.append("marked_surface_fields_as_non_security")

    if not actions and not validation.passed:
        requires_human_review = True
        actions.append("requires_human_review_for_unresolved_validation_failure")

    provenance = dict(contract.provenance)
    provenance["refinement_actions"] = actions
    provenance["previous_validation_passed"] = validation.passed

    return replace(
        contract,
        templates=tuple(templates),
        non_security_fields=tuple(sorted(set(contract.non_security_fields) | set(non_security_fields(tool.name)))),
        requires_human_review=requires_human_review,
        provenance=provenance,
    )
