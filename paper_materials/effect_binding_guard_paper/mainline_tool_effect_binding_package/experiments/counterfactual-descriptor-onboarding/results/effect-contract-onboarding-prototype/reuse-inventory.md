# E60 Reuse Inventory

## Files Inspected

- `code/src/experiments/effect_binding_guard/e55_precommit_authz/schemas.py`
- `code/src/experiments/effect_binding_guard/e55_precommit_authz/authz_model.py`
- `code/src/experiments/effect_binding_guard/e55_precommit_authz/atom_expansion.py`
- `code/src/experiments/effect_binding_guard/e55_precommit_authz/mock_tools.py`
- `code/src/experiments/effect_binding_guard/e55_precommit_authz/metrics.py`
- `code/src/experiments/effect_binding_guard/e55_precommit_authz/leakage_audit.py`
- `code/src/experiments/effect_binding_guard/e55_precommit_authz/e57_validity_checks.py`
- `tests/tests/test_effect_binding_guard_e55_precommit_authz.py`
- `tests/tests/test_effect_binding_guard_e57_validity.py`

## Reusable Components

- E55 `AuthorizationContext` and `EffectAtom` field vocabulary.
- E55 resource canonicalization, operation-mode, visibility, and provenance/control-source authorization semantics.
- E55 resource canonicalization plus E60-specific target-principal authorization.
- E55 atom metric vocabulary: UPA, FDeny, coverage, atom coverage, and exact atom signatures.
- E55/E57 testing pattern for label-hidden runtime inputs and deterministic validation.

## Components Reused Directly

- `e55_precommit_authz.authz_model.canonical_resource`
- E55-compatible `AuthorizationContext` and `EffectAtom` conversion targets for resource, operation, visibility, and provenance checks.

## Components Adapted

- E55 atom fields are adapted into E60 `EffectAtom` with explicit resource/target separation, `target_principal`, `permission_delta`, and `evidence_ref`.
- E55 metric style is adapted to contract-validation metrics over paired counterfactual cases.
- E57 perturbation discipline is adapted into field-level counterfactual validation cases.

## New Components Created

- Candidate contract dataclasses and frozen-contract representation.
- Stub proposer and optional LLM-compatible proposer interface.
- Counterfactual generator for mock tool onboarding.
- Contract validator and deterministic refiner.
- Frozen-contract runtime mediator.
- Demo CLI and prototype reports.

## Components Intentionally Not Reused

- E55 dataset builders are not reused because E60 is a tool-onboarding prototype rather than a fixed-row dataset generator.
- E55 production guard wrappers are not reused because runtime mediation here must depend only on frozen contracts.
- E57 human-audit packet generation is not reused because this prototype has no external human-review claim.
