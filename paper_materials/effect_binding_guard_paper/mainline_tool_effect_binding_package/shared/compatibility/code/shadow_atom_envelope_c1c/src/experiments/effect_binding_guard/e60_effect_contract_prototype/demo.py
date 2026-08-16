from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from .contract_refiner import refine_contract
from .contract_validator import validate_contract
from .counterfactual_generator import generate_counterfactual_cases
from .llm_contract_proposer import ContractProposer
from .mock_tools import all_authorization_contexts, authorization_context, load_mock_tools
from .runtime import authorize_tool_call, freeze_contract


PACKAGE_ROOT = Path(__file__).resolve().parents[5]
RESULTS = PACKAGE_ROOT / "analysis/results"
DEMO_OUTPUTS = RESULTS / "e60_demo_outputs.jsonl"
REPORT_MD = RESULTS / "e60_effect_contract_prototype_report.md"
REPORT_JSON = RESULTS / "e60_effect_contract_prototype_report.json"
REUSE_INVENTORY = RESULTS / "e60_reuse_inventory.md"


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    tools = load_mock_tools()
    proposer = ContractProposer(mode="stub")
    contexts = all_authorization_contexts()
    output_rows: list[dict[str, Any]] = []
    tool_summaries: list[dict[str, Any]] = []
    total_cases = 0
    runtime_count = 0

    for tool in tools:
        candidate = proposer.propose(tool)
        if tool.name == "share_file":
            candidate = inject_demo_incompleteness(candidate)
        cases = generate_counterfactual_cases(tool)
        total_cases += len(cases)
        initial_validation = validate_contract(candidate, cases)
        final_contract = candidate
        final_validation = initial_validation
        refined = False
        if not initial_validation.passed:
            refined = True
            final_contract = refine_contract(candidate, initial_validation, tool)
            final_validation = validate_contract(final_contract, cases)

        frozen = freeze_contract(final_contract, final_validation)
        runtime_examples = runtime_examples_for_tool(tool)
        runtime_rows = []
        for example_name, call, context_name in runtime_examples:
            result = authorize_tool_call(frozen, call, contexts[context_name])
            runtime_count += 1
            row = {
                "row_type": "runtime_example",
                "tool_name": tool.name,
                "example": example_name,
                "context": context_name,
                "decision": result["decision"],
                "reasons": result["reasons"],
                "n_atoms": len(result["atoms"]),
                "contract_hash": result["contract_hash"],
            }
            runtime_rows.append(row)
            output_rows.append(row)

        validation_row = {
            "row_type": "validation_summary",
            "tool_name": tool.name,
            "initial_passed": initial_validation.passed,
            "final_passed": final_validation.passed,
            "refined": refined,
            "n_counterfactual_cases": len(cases),
            "initial_validation": initial_validation.to_dict(),
            "final_validation": final_validation.to_dict(),
            "frozen_contract_hash": frozen.contract_hash,
        }
        output_rows.append(validation_row)
        tool_summaries.append(
            {
                "tool_name": tool.name,
                "candidate_contract_hash": candidate.contract_hash(),
                "frozen_contract_hash": frozen.contract_hash,
                "initial_passed": initial_validation.passed,
                "final_passed": final_validation.passed,
                "refined": refined,
                "n_counterfactual_cases": len(cases),
                "metrics": final_validation.to_dict(),
                "runtime_examples": runtime_rows,
            }
        )

    report = {
        "experiment": "E60 effect contract prototype",
        "status": "passed" if all(row["final_passed"] for row in tool_summaries) else "failed",
        "n_tools_tested": len(tools),
        "n_candidate_contracts": len(tools),
        "n_counterfactual_cases": total_cases,
        "n_runtime_examples": runtime_count,
        "validation_pass_fail_per_tool": {row["tool_name"]: row["final_passed"] for row in tool_summaries},
        "field_sensitivity_accuracy": mean(row["metrics"]["field_sensitivity_accuracy"] for row in tool_summaries),
        "surface_invariance_accuracy": mean(row["metrics"]["surface_invariance_accuracy"] for row in tool_summaries),
        "unsafe_pre_allow_rate": mean(row["metrics"]["unsafe_pre_allow_rate"] for row in tool_summaries),
        "false_deny_rate": mean(row["metrics"]["false_deny_rate"] for row in tool_summaries),
        "coverage": mean(row["metrics"]["coverage"] for row in tool_summaries),
        "atom_coverage": mean(row["metrics"]["atom_coverage"] for row in tool_summaries),
        "expected_decision_agreement": mean(row["metrics"]["expected_decision_agreement"] for row in tool_summaries),
        "required_atom_coverage": mean(row["metrics"]["required_atom_coverage"] for row in tool_summaries),
        "required_resource_binding_coverage": mean(row["metrics"]["required_resource_binding_coverage"] for row in tool_summaries),
        "required_target_principal_coverage": mean(row["metrics"]["required_target_principal_coverage"] for row in tool_summaries),
        "test_status": "not_run_by_demo",
        "authorization_contexts_available": sorted(contexts),
        "authorization_contexts_used": sorted({row["context"] for tool in tool_summaries for row in tool["runtime_examples"]}),
        "runtime_uses_frozen_contracts_only": True,
        "runtime_llm_or_proposer_calls_after_freeze": 0,
        "incomplete_contract_demonstrations": [
            {
                "tool_name": row["tool_name"],
                "initial_passed": row["initial_passed"],
                "final_passed": row["final_passed"],
                "refined": row["refined"],
            }
            for row in tool_summaries
            if row["refined"]
        ],
        "tools": tool_summaries,
        "claim_boundary": (
            "This prototype demonstrates LLM-compatible candidate contract proposal, "
            "counterfactual validation, contract freezing, and deterministic runtime authorization. "
            "It is not a production system."
        ),
        "limitation": (
            "The runtime authorizer is only as complete as the validated tool effect contract. "
            "If a contract omits a security-relevant side effect, the authorizer cannot check it."
        ),
    }

    write_jsonl(DEMO_OUTPUTS, output_rows)
    write_json(REPORT_JSON, report)
    write_text(REPORT_MD, report_markdown(report))
    write_text(REUSE_INVENTORY, reuse_inventory_markdown())
    print(json.dumps({"status": report["status"], "n_tools": len(tools), "n_counterfactual_cases": total_cases, "report": str(REPORT_JSON)}, indent=2))


def runtime_examples_for_tool(tool) -> list[tuple[str, dict[str, Any], str]]:
    rows: list[tuple[str, dict[str, Any], str]] = [
        ("safe_default", tool.example_safe_call, "default_safe"),
        ("safe_draft_only", tool.example_safe_call, "draft_only"),
        ("unsafe_external_forbidden", tool.example_unsafe_call, "external_recipient_forbidden"),
        ("unknown_draft_only", tool.example_unknown_call, "draft_only"),
        (
            "untrusted_control_forbidden",
            {**tool.example_safe_call, "control_source": "tool_output", "provenance_source": "tool_output"},
            "untrusted_control_forbidden",
        ),
    ]
    if tool.name == "share_file":
        rows.extend(
            [
                ("public_no_public_link", {**tool.example_safe_call, "visibility": "public"}, "no_public_link"),
                ("alias_disabled", tool.example_safe_call, "alias_disabled"),
            ]
        )
    if tool.name == "create_calendar_event":
        rows.extend(
            [
                ("event_alias_enabled", {**tool.example_safe_call, "event_id": "event_alias"}, "alias_enabled"),
                ("event_alias_disabled", {**tool.example_safe_call, "event_id": "event_alias"}, "alias_disabled"),
            ]
        )
    if tool.name == "post_slack_message":
        rows.append(("channel_alias_disabled", tool.example_safe_call, "alias_disabled"))
    if tool.name == "submit_payment":
        rows.extend(
            [
                ("payment_alias_disabled", tool.example_safe_call, "alias_disabled"),
                ("limited_payment", tool.example_safe_call, "limited_payment"),
            ]
        )
    return rows


def inject_demo_incompleteness(contract):
    templates = [template for template in contract.templates if template.effect_type != "file_reader_added"]
    provenance = dict(contract.provenance)
    provenance["demo_injected_incomplete_candidate"] = "removed file_reader_added template before validation"
    return replace(contract, templates=tuple(templates), provenance=provenance)


def mean(values) -> float:
    values = list(values)
    if not values:
        return 0.0
    return round(sum(float(value) for value in values) / len(values), 3)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# E60 Effect Contract Prototype Report",
        "",
        "## Purpose",
        "",
        "This prototype demonstrates an onboarding workflow in which an LLM-compatible proposer creates candidate effect contracts, field-level counterfactual tests validate those candidates, validated contracts are frozen, and runtime mediation uses only frozen contracts for atom-level authorization.",
        "",
        "It is not a production system and does not execute real external side effects.",
        "",
        "## Reused Code Summary",
        "",
        "The runtime authorization path reuses E55 resource canonicalization, operation-mode, visibility, and provenance/control-source helper semantics, then adds E60-specific target-principal authorization after converting prototype atoms and contexts to compatible forms. The prototype keeps separate contract dataclasses so onboarding, validation, refinement, and freezing metadata remain explicit.",
        "",
        "## Architecture",
        "",
        "Candidate proposal is isolated from runtime authorization. Stub proposals are treated as untrusted contracts until counterfactual validation passes. Runtime authorization accepts only `FrozenContract` objects and never calls the proposer or an LLM.",
        "",
        "## Mock Tools Supported",
        "",
    ]
    for tool in report["tools"]:
        lines.append(f"- `{tool['tool_name']}`: final validation passed `{tool['final_passed']}`, refined `{tool['refined']}`.")
    lines.extend(
        [
            "",
            "## Counterfactual Validation Summary",
            "",
            f"- Tools tested: `{report['n_tools_tested']}`.",
            f"- Candidate contracts: `{report['n_candidate_contracts']}`.",
            f"- Counterfactual cases: `{report['n_counterfactual_cases']}`.",
            f"- Field sensitivity accuracy: `{report['field_sensitivity_accuracy']}`.",
            f"- Surface invariance accuracy: `{report['surface_invariance_accuracy']}`.",
            f"- Unsafe pre-allow rate: `{report['unsafe_pre_allow_rate']}`.",
            f"- False deny rate: `{report['false_deny_rate']}`.",
            f"- Coverage: `{report['coverage']}`.",
            f"- Atom coverage: `{report['atom_coverage']}`.",
            f"- Expected decision agreement: `{report['expected_decision_agreement']}`.",
            f"- Required atom coverage: `{report['required_atom_coverage']}`.",
            f"- Required resource binding coverage: `{report['required_resource_binding_coverage']}`.",
            f"- Required target-principal coverage: `{report['required_target_principal_coverage']}`.",
            "",
            "## Authorization Contexts",
            "",
            f"- Context variants available: `{', '.join(report['authorization_contexts_available'])}`.",
            f"- Context variants exercised by demo runtime examples: `{', '.join(report['authorization_contexts_used'])}`.",
            "",
            "## Runtime Authorization Examples",
            "",
            f"The demo ran `{report['n_runtime_examples']}` runtime examples across safe, unsafe, and unknown inputs. Rows are written to `analysis/results/e60_demo_outputs.jsonl`.",
            "",
            "Runtime authorization uses frozen contracts only. The demo records `runtime_llm_or_proposer_calls_after_freeze = 0`.",
            "",
            "## Incomplete Contract Detection",
            "",
            "The demo intentionally removes the `file_reader_added` template from the initial `share_file` candidate. Counterfactual validation catches the incomplete contract, the deterministic refiner restores the missing template, and only the validated refined contract is frozen.",
            "",
            "## Example Effect Contract",
            "",
            "The `send_email` contract binds the message body as the operated resource and places `to`, `cc`, and `bcc` entries in `target_principal`. Attachment-disclosure atoms use the disclosed file as `resource_id` and the recipient as `target_principal`. `commit_mode`, `control_source`, and `provenance_source` are security-relevant fields validated by counterfactual cases.",
            "",
            "## Example Atomization",
            "",
            "A safe `send_email` draft with one recipient and one attachment expands to a `message_sent` atom over `email_body` targeted at the recipient, plus an `attachment_disclosed` atom over `finance-plan.docx` targeted at the same recipient. The frozen runtime authorizer checks both resource and target-principal authorization before allowing the call.",
            "",
            "## Limitations",
            "",
            "- This is not a production system.",
            "- It does not call real email, calendar, Slack, file, payment, browser, shell, or network APIs.",
            "- It performs no real SaaS/API integration and executes no real external side effects.",
            "- Stub proposal is not proof that LLMs reliably infer contracts for arbitrary tools.",
            "- The LLM-compatible proposal is not trusted and is not used as the final runtime safety judge.",
            "- The runtime authorizer is only as complete as the validated tool effect contract. If a contract omits a security-relevant side effect, the authorizer cannot check it.",
            "- Unknown or high-risk tools should default to `ABSTAIN` or human review.",
            "- The prototype demonstrates onboarding, validation, and frozen runtime authorization, not full deployment generalization.",
            "",
            "## Connection to E55/E56/E57",
            "",
            "E55 supplied the local authorization-aware atom-checking semantics reused here. E56/E57 supplied the audit and validation discipline that motivates leakage separation, independent checking, and conservative claim boundaries. E60 adds an onboarding prototype for validating and freezing effect contracts before runtime use.",
        ]
    )
    return "\n".join(lines) + "\n"


def reuse_inventory_markdown() -> str:
    return """# E60 Reuse Inventory

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
"""


if __name__ == "__main__":
    main()
