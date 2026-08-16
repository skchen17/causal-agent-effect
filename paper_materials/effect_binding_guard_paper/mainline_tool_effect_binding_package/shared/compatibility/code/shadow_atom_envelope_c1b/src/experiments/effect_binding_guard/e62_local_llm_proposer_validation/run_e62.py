from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.experiments.effect_binding_guard.e60_effect_contract_prototype.contract_validator import validate_contract
from src.experiments.effect_binding_guard.e60_effect_contract_prototype.contracts import ToolEffectContract
from src.experiments.effect_binding_guard.e60_effect_contract_prototype.runtime import freeze_contract

from .contract_parser import ParseResult, parse_contract_from_text
from .failure_analysis import FAILURE_CATEGORIES, classify_failure, validation_failure_summary
from .heldout_tools import E60_TOOL_NAMES, load_heldout_tools
from .local_llm_backend import CompletionBackend, LLMResponse, backend_from_env
from .prompting import build_proposal_prompt, build_refinement_prompt, prompt_record
from .reference_expectations import generate_reference_cases, reference_contract_for_tool


PACKAGE_ROOT = Path(__file__).resolve().parents[5]
RESULTS = PACKAGE_ROOT / "analysis/results"
REPORT_MD = RESULTS / "e62_local_llm_proposer_report.md"
REPORT_JSON = RESULTS / "e62_local_llm_proposer_report.json"
PER_TOOL_CSV = RESULTS / "e62_local_llm_per_tool_metrics.csv"
FAILURE_EXAMPLES = RESULTS / "e62_local_llm_failure_examples.jsonl"
PROMPTS_JSONL = RESULTS / "e62_local_llm_prompts.jsonl"
CLAIM_BOUNDARY = RESULTS / "e62_local_llm_claim_boundary.md"
REUSE_INVENTORY = RESULTS / "e62_local_llm_reuse_inventory.md"


def main() -> None:
    report = run_e62()
    print(json.dumps({"status": report["status"], "local_llm_status": report["local_llm_status"], "report": str(REPORT_JSON)}, indent=2))


def run_e62(backend: CompletionBackend | None = None) -> dict[str, Any]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    active_backend = backend if backend is not None else backend_from_env()
    backend_ok, backend_message = active_backend.health()
    tools = load_heldout_tools()
    if set(tool.name for tool in tools) & E60_TOOL_NAMES:
        raise RuntimeError("E62 held-out tools overlap with E60 tools")

    prompt_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []

    for tool in tools:
        cases = generate_reference_cases(tool)
        stub_contract = reference_contract_for_tool(tool)
        stub_validation = validate_contract(stub_contract, cases)
        metric_rows.append(row_from_validation("stub_harness", tool.name, True, "", stub_contract, stub_validation, "not_llm_evidence"))

    if backend_ok:
        for tool in tools:
            raw_prompt = build_proposal_prompt(tool)
            raw_prompt_id = f"{tool.name}:raw"
            raw_response = active_backend.complete(raw_prompt)
            prompt_rows.append(
                prompt_record(
                    prompt_id=raw_prompt_id,
                    tool_name=tool.name,
                    setting="raw_local_llm",
                    prompt=raw_prompt,
                    backend=active_backend.backend_name,
                    model=active_backend.model,
                    raw_output=raw_response.text,
                    status=raw_response.status,
                )
            )
            raw_row, raw_summary, raw_parse = evaluate_model_output(
                setting="raw_local_llm",
                tool_name=tool.name,
                raw_output=raw_response.text,
                response=raw_response,
            )
            metric_rows.append(raw_row)
            if raw_row["freezeable"] != "true":
                failure_rows.append(failure_row(tool.name, "raw_local_llm", raw_row, raw_summary))

            refinement_prompt = build_refinement_prompt(tool, raw_response.text, raw_summary)
            refined_response = active_backend.complete(refinement_prompt)
            prompt_rows.append(
                prompt_record(
                    prompt_id=f"{tool.name}:refined",
                    tool_name=tool.name,
                    setting="refined_local_llm",
                    prompt=refinement_prompt,
                    backend=active_backend.backend_name,
                    model=active_backend.model,
                    raw_output=refined_response.text,
                    status=refined_response.status,
                )
            )
            refined_row, refined_summary, _ = evaluate_model_output(
                setting="refined_local_llm",
                tool_name=tool.name,
                raw_output=refined_response.text,
                response=refined_response,
            )
            metric_rows.append(refined_row)
            if refined_row["freezeable"] != "true":
                failure_rows.append(failure_row(tool.name, "refined_local_llm", refined_row, refined_summary))
    else:
        for tool in tools:
            raw_prompt = build_proposal_prompt(tool)
            prompt_rows.append(
                prompt_record(
                    prompt_id=f"{tool.name}:raw",
                    tool_name=tool.name,
                    setting="raw_local_llm",
                    prompt=raw_prompt,
                    backend=active_backend.backend_name,
                    model=active_backend.model,
                    raw_output="",
                    status="not_executed",
                )
            )

    report = build_report(
        tools=tools,
        backend=active_backend,
        backend_ok=backend_ok,
        backend_message=backend_message,
        metric_rows=metric_rows,
        prompt_rows=prompt_rows,
        failure_rows=failure_rows,
    )
    write_outputs(report, metric_rows, prompt_rows, failure_rows)
    return report


def evaluate_model_output(
    *,
    setting: str,
    tool_name: str,
    raw_output: str,
    response: LLMResponse,
) -> tuple[dict[str, Any], dict[str, Any], ParseResult]:
    tool = next(tool for tool in load_heldout_tools() if tool.name == tool_name)
    if response.status != "ok":
        summary = validation_failure_summary(parse_error=response.error or response.status, validation=None)
        return row_from_parse_failure(setting, tool_name, response.error or response.status, summary), summary, ParseResult(False, None, response.error or response.status)
    parsed = parse_contract_from_text(raw_output, tool_name=tool_name, setting=setting)
    if not parsed.parse_valid or parsed.contract is None:
        summary = validation_failure_summary(parse_error=parsed.error, validation=None)
        return row_from_parse_failure(setting, tool_name, parsed.error, summary), summary, parsed
    cases = generate_reference_cases(tool)
    validation = validate_contract(parsed.contract, cases)
    summary = validation_failure_summary(validation=validation)
    row = row_from_validation(setting, tool_name, True, "", parsed.contract, validation, "local_llm")
    return row, summary, parsed


def row_from_parse_failure(setting: str, tool_name: str, parse_error: str, summary: dict[str, Any]) -> dict[str, Any]:
    categories = summary.get("failure_categories", classify_failure(parse_error=parse_error))
    return {
        "setting": setting,
        "tool_name": tool_name,
        "parse_valid": "false",
        "parse_error": parse_error,
        "validation_passed": "false",
        "freezeable": "false",
        "evidence_kind": "local_llm",
        "failure_categories": "|".join(categories),
        "required_atom_coverage": "0.000",
        "required_resource_binding_coverage": "0.000",
        "required_target_principal_coverage": "0.000",
        "unsafe_pre_allow_rate": "0.000",
        "false_deny_rate": "0.000",
        "coverage": "0.000",
        "decision_accuracy": "0.000",
        "n_cases": "0",
        "missing_required_atom_count": "0",
        "contract_hash": "",
    }


def row_from_validation(
    setting: str,
    tool_name: str,
    parse_valid: bool,
    parse_error: str,
    contract: ToolEffectContract,
    validation,
    evidence_kind: str,
) -> dict[str, Any]:
    freezeable = can_freeze(parse_valid, validation)
    if freezeable:
        freeze_contract(contract, validation)
    categories = classify_failure(parse_error=parse_error, validation=validation)
    return {
        "setting": setting,
        "tool_name": tool_name,
        "parse_valid": str(parse_valid).lower(),
        "parse_error": parse_error,
        "validation_passed": str(validation.passed).lower(),
        "freezeable": str(freezeable).lower(),
        "evidence_kind": evidence_kind,
        "failure_categories": "|".join(categories),
        "required_atom_coverage": f"{validation.required_atom_coverage:.3f}",
        "required_resource_binding_coverage": f"{validation.required_resource_binding_coverage:.3f}",
        "required_target_principal_coverage": f"{validation.required_target_principal_coverage:.3f}",
        "unsafe_pre_allow_rate": f"{validation.unsafe_pre_allow_rate:.3f}",
        "false_deny_rate": f"{validation.false_deny_rate:.3f}",
        "coverage": f"{validation.coverage:.3f}",
        "decision_accuracy": f"{validation.decision_accuracy:.3f}",
        "n_cases": str(validation.n_cases),
        "missing_required_atom_count": str(validation.missing_required_atom_count),
        "contract_hash": contract.contract_hash(),
    }


def can_freeze(parse_valid: bool, validation) -> bool:
    return bool(
        parse_valid
        and validation.passed
        and validation.required_atom_coverage == 1.0
        and validation.required_resource_binding_coverage == 1.0
        and validation.required_target_principal_coverage == 1.0
        and validation.unsafe_pre_allow_rate == 0.0
        and validation.missing_required_atom_count == 0
    )


def failure_row(tool_name: str, setting: str, row: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "setting": setting,
        "failure_categories": summary.get("failure_categories", []),
        "parse_error": row.get("parse_error", ""),
        "freezeable": row.get("freezeable", "false"),
        "required_atom_coverage": row.get("required_atom_coverage"),
        "required_resource_binding_coverage": row.get("required_resource_binding_coverage"),
        "required_target_principal_coverage": row.get("required_target_principal_coverage"),
        "unsafe_pre_allow_rate": row.get("unsafe_pre_allow_rate"),
        "false_deny_rate": row.get("false_deny_rate"),
        "hints": summary.get("hints", []),
    }


def build_report(
    *,
    tools,
    backend: CompletionBackend,
    backend_ok: bool,
    backend_message: str,
    metric_rows: list[dict[str, Any]],
    prompt_rows: list[dict[str, Any]],
    failure_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    local_rows = [row for row in metric_rows if row["evidence_kind"] == "local_llm"]
    raw_rows = [row for row in local_rows if row["setting"] == "raw_local_llm"]
    refined_rows = [row for row in local_rows if row["setting"] == "refined_local_llm"]
    local_status = "executed" if backend_ok and local_rows else "not_executed"
    conclusion = conclusion_from_rows(local_status, raw_rows, refined_rows)
    return {
        "experiment": "E62 local LLM effect-contract proposer validation",
        "status": "passed",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "backend": backend.backend_name,
        "model": backend.model,
        "model_source_path": os.environ.get("E62_LOCAL_LLM_MODEL_PATH", ""),
        "generation_limits": {
            "max_tokens": os.environ.get("E62_LOCAL_LLM_MAX_TOKENS", ""),
            "timeout_seconds": os.environ.get("E62_LOCAL_LLM_TIMEOUT", ""),
            "response_format": os.environ.get("E62_LOCAL_LLM_RESPONSE_FORMAT", "json_object"),
        },
        "backend_health": {"ok": backend_ok, "message": backend_message},
        "local_llm_status": local_status,
        "n_heldout_tools": len(tools),
        "heldout_tool_names": [tool.name for tool in tools],
        "n_prompt_records": len(prompt_rows),
        "n_metric_rows": len(metric_rows),
        "n_failure_examples": len(failure_rows),
        "stub_harness": summarize_rows([row for row in metric_rows if row["setting"] == "stub_harness"]),
        "raw_local_llm": summarize_rows(raw_rows),
        "refined_local_llm": summarize_rows(refined_rows),
        "failure_categories": list(FAILURE_CATEGORIES),
        "freeze_criteria": {
            "parse_valid": True,
            "validation_passed": True,
            "required_atom_coverage": 1.0,
            "required_resource_binding_coverage": 1.0,
            "required_target_principal_coverage": 1.0,
            "unsafe_pre_allow_rate": 0.0,
            "missing_required_atom_count": 0,
        },
        "claim_boundary": claim_boundary_text(local_status),
        "conclusion": conclusion,
        "outputs": {
            "report_md": str(REPORT_MD),
            "report_json": str(REPORT_JSON),
            "per_tool_metrics_csv": str(PER_TOOL_CSV),
            "failure_examples_jsonl": str(FAILURE_EXAMPLES),
            "prompts_jsonl": str(PROMPTS_JSONL),
            "claim_boundary_md": str(CLAIM_BOUNDARY),
            "reuse_inventory_md": str(REUSE_INVENTORY),
        },
    }


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n": 0, "parse_valid": 0, "freezeable": 0, "mean_required_atom_coverage": 0.0, "mean_unsafe_pre_allow_rate": 0.0}
    return {
        "n": len(rows),
        "parse_valid": sum(1 for row in rows if row["parse_valid"] == "true"),
        "validation_passed": sum(1 for row in rows if row["validation_passed"] == "true"),
        "freezeable": sum(1 for row in rows if row["freezeable"] == "true"),
        "mean_required_atom_coverage": mean_float(row["required_atom_coverage"] for row in rows),
        "mean_resource_binding_coverage": mean_float(row["required_resource_binding_coverage"] for row in rows),
        "mean_target_principal_coverage": mean_float(row["required_target_principal_coverage"] for row in rows),
        "mean_unsafe_pre_allow_rate": mean_float(row["unsafe_pre_allow_rate"] for row in rows),
        "mean_false_deny_rate": mean_float(row["false_deny_rate"] for row in rows),
    }


def mean_float(values) -> float:
    values = [float(value) for value in values]
    if not values:
        return 0.0
    return round(sum(values) / len(values), 3)


def conclusion_from_rows(local_status: str, raw_rows: list[dict[str, Any]], refined_rows: list[dict[str, Any]]) -> str:
    if local_status != "executed":
        return "Outcome C: local LLM was not executed; only the validation harness and stub sanity path ran."
    if refined_rows and all(row["freezeable"] == "true" for row in refined_rows):
        return "Outcome A: refined local LLM proposals passed the strict freeze gate for all held-out tools."
    if any(row["freezeable"] == "true" for row in refined_rows):
        return "Outcome B: local LLM proposals partially passed; failures require reporting and human review."
    return "Outcome C: local LLM proposals did not pass the strict freeze gate."


def claim_boundary_text(local_status: str) -> str:
    if local_status == "executed":
        return (
            "E62 supports claims about the configured local LLM backend on this 15-tool held-out mock suite. "
            "It does not support production safety, arbitrary-tool contract inference, or real external API behavior."
        )
    return (
        "E62 currently supports only the harness, prompt-leakage checks, parser, validator, and stub sanity path. "
        "It does not provide local LLM evidence until a configured backend is executed."
    )


def write_outputs(
    report: dict[str, Any],
    metric_rows: list[dict[str, Any]],
    prompt_rows: list[dict[str, Any]],
    failure_rows: list[dict[str, Any]],
) -> None:
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(report_markdown(report), encoding="utf-8")
    CLAIM_BOUNDARY.write_text(claim_boundary_markdown(report), encoding="utf-8")
    REUSE_INVENTORY.write_text(reuse_inventory_markdown(), encoding="utf-8")
    write_jsonl(PROMPTS_JSONL, prompt_rows)
    write_jsonl(FAILURE_EXAMPLES, failure_rows)
    write_csv(PER_TOOL_CSV, metric_rows)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "setting",
        "tool_name",
        "parse_valid",
        "parse_error",
        "validation_passed",
        "freezeable",
        "evidence_kind",
        "failure_categories",
        "required_atom_coverage",
        "required_resource_binding_coverage",
        "required_target_principal_coverage",
        "unsafe_pre_allow_rate",
        "false_deny_rate",
        "coverage",
        "decision_accuracy",
        "n_cases",
        "missing_required_atom_count",
        "contract_hash",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# E62 Local LLM Effect-Contract Proposer Validation Report",
        "",
        "## Summary",
        "",
        f"- Backend: `{report['backend']}`.",
        f"- Model: `{report['model']}`.",
        f"- Generation: max_tokens `{report['generation_limits'].get('max_tokens', '')}`, response_format `{report['generation_limits'].get('response_format', '')}`.",
        f"- Backend health: `{report['backend_health']['ok']}` ({report['backend_health']['message']}).",
        f"- Local LLM status: `{report['local_llm_status']}`.",
        f"- Held-out tools: `{report['n_heldout_tools']}`.",
        f"- Metric rows: `{report['n_metric_rows']}`.",
        "",
        "## Stub Harness",
        "",
        f"- Rows: `{report['stub_harness']['n']}`.",
        f"- Freezeable: `{report['stub_harness']['freezeable']}`.",
        "",
        "## Raw Local LLM",
        "",
        f"- Rows: `{report['raw_local_llm']['n']}`.",
        f"- Parse-valid: `{report['raw_local_llm']['parse_valid']}`.",
        f"- Freezeable: `{report['raw_local_llm']['freezeable']}`.",
        "",
        "## Refined Local LLM",
        "",
        f"- Rows: `{report['refined_local_llm']['n']}`.",
        f"- Parse-valid: `{report['refined_local_llm']['parse_valid']}`.",
        f"- Freezeable: `{report['refined_local_llm']['freezeable']}`.",
        "",
        "## Conclusion",
        "",
        report["conclusion"],
        "",
        "## Claim Boundary",
        "",
        report["claim_boundary"],
        "",
        "The stub harness is a validation-path sanity check only and is not counted as local LLM evidence.",
        "",
    ]
    return "\n".join(lines)


def claim_boundary_markdown(report: dict[str, Any]) -> str:
    return f"""# E62 Claim Boundary

## Supported

- The artifact implements a 15-tool held-out mock suite for local-LLM effect-contract proposal validation.
- The artifact records prompts, backend status, parse status, validation metrics, freeze gates, and failure examples.
- When `local_llm_status` is `executed`, the reported raw/refined rows describe the configured local backend only.

## Unsupported

- No production safety claim.
- No real SaaS, email, Slack, payment, CI, calendar, filesystem, shell, or network side effect is executed.
- Stub-mode rows are not local LLM evidence.
- Passing E62 does not prove arbitrary LLMs can infer complete contracts for arbitrary tools.
- Proposed contracts are not trusted until counterfactual validation and the freeze gate pass.

Current local LLM status: `{report['local_llm_status']}`.
"""


def reuse_inventory_markdown() -> str:
    return """# E62 Reuse Inventory

## Reused From E60

- `ToolSpec`, `ToolEffectContract`, `EffectTemplate`, `EffectAtom`, `AuthorizationContext`, `CounterfactualCase`, and `ValidationResult`.
- Counterfactual validator metrics: UPA, FDeny, coverage, required atom coverage, required resource binding coverage, and required target-principal coverage.
- Frozen-contract runtime and `freeze_contract` gate.

## New In E62

- Fifteen held-out mock tool specs disjoint from the E60 five-tool prototype.
- Prompt construction and leakage scanning for local LLM contract proposal.
- Strict JSON parser from local LLM text to E60-compatible contracts.
- One-step validation-summary refinement that does not expose hidden reference contracts or expected atoms.
- Local backend adapters for Ollama and OpenAI-compatible endpoints.
- Report artifacts for prompts, failures, per-tool metrics, claim boundary, and reuse inventory.

## Boundary

E62 validates local proposal quality for mock contracts. It does not replace E55/E60 deterministic runtime authorization and does not execute real external side effects.
"""


if __name__ == "__main__":
    main()
