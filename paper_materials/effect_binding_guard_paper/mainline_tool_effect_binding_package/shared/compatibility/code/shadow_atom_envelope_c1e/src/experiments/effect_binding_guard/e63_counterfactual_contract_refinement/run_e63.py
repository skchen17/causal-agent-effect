from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.experiments.effect_binding_guard.e60_effect_contract_prototype.contract_validator import validate_contract
from src.experiments.effect_binding_guard.e60_effect_contract_prototype.contracts import ToolEffectContract, stable_hash
from src.experiments.effect_binding_guard.e60_effect_contract_prototype.runtime import freeze_contract
from src.experiments.effect_binding_guard.e62_local_llm_proposer_validation.contract_parser import ParseResult, parse_contract_from_text
from src.experiments.effect_binding_guard.e62_local_llm_proposer_validation.failure_analysis import classify_failure
from src.experiments.effect_binding_guard.e62_local_llm_proposer_validation.heldout_tools import E60_TOOL_NAMES, load_heldout_tools
from src.experiments.effect_binding_guard.e62_local_llm_proposer_validation.local_llm_backend import (
    CompletionBackend,
    LLMResponse,
    OllamaBackend,
    OpenAICompatibleBackend,
    UnavailableBackend,
)
from src.experiments.effect_binding_guard.e62_local_llm_proposer_validation.reference_expectations import generate_reference_cases, reference_contract_for_tool

from .feedback import build_feedback_payload, feedback_leakage_scan
from .prompting import build_round_prompt, round_prompt_hash, scan_round_prompt
from .selection import select_best_candidate


PACKAGE_ROOT = Path(__file__).resolve().parents[5]
RESULTS = PACKAGE_ROOT / "analysis/results"
OUTPUT_PREFIX = os.environ.get("E63_OUTPUT_PREFIX", "").strip()


def output_path(default_name: str, prefixed_suffix: str) -> Path:
    if OUTPUT_PREFIX:
        return RESULTS / f"{OUTPUT_PREFIX}_{prefixed_suffix}"
    return RESULTS / default_name


REPORT_JSON = output_path("e63_counterfactual_refinement_report.json", "report.json")
REPORT_MD = output_path("e63_counterfactual_refinement_report.md", "report.md")
ROUND_METRICS_CSV = output_path("e63_round_metrics.csv", "round_metrics.csv")
CANDIDATE_CONTRACTS = output_path("e63_candidate_contracts.jsonl", "candidate_contracts.jsonl")
PROMPTS_JSONL = output_path("e63_prompts.jsonl", "prompts.jsonl")
FEEDBACK_JSONL = output_path("e63_feedback_payloads.jsonl", "feedback_payloads.jsonl")
FAILURE_EXAMPLES = output_path("e63_failure_examples.jsonl", "failure_examples.jsonl")
FROZEN_CONTRACTS = output_path("e63_frozen_contracts.jsonl", "frozen_contracts.jsonl")
CLAIM_BOUNDARY = output_path("e63_claim_boundary.md", "claim_boundary.md")


def main() -> None:
    report = run_e63()
    print(json.dumps({"status": report["status"], "local_llm_status": report["local_llm_status"], "report": str(REPORT_JSON)}, indent=2))


def run_e63(
    *,
    backend: CompletionBackend | None = None,
    max_rounds: int | None = None,
    tool_limit: int | None = None,
) -> dict[str, Any]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    active_backend = backend if backend is not None else backend_from_e63_env()
    backend_ok, backend_message = active_backend.health()
    rounds = max_rounds if max_rounds is not None else int(os.environ.get("E63_MAX_REFINEMENT_ROUNDS", "4"))
    tools = load_heldout_tools()
    if tool_limit is not None:
        tools = tools[:tool_limit]
    if set(tool.name for tool in tools) & E60_TOOL_NAMES:
        raise RuntimeError("E63 held-out tools overlap with E60 tools")

    metric_rows: list[dict[str, Any]] = []
    prompt_rows: list[dict[str, Any]] = []
    feedback_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    selection_rows: list[dict[str, Any]] = []

    for tool in tools:
        cases = generate_reference_cases(tool)
        stub_contract = reference_contract_for_tool(tool)
        stub_validation = validate_contract(stub_contract, cases)
        metric_rows.append(row_from_validation("stub_harness", -1, tool.name, True, "", stub_contract, stub_validation, "not_llm_evidence"))

    if backend_ok:
        for tool in tools:
            previous_output = ""
            previous_feedback: dict[str, Any] | None = None
            tool_rows: list[dict[str, Any]] = []
            for round_index in range(rounds + 1):
                setting = "round_0_raw" if round_index == 0 else f"round_{round_index}"
                prompt = build_round_prompt(
                    tool=tool,
                    round_index=round_index,
                    previous_contract_json=previous_output,
                    feedback_payload=previous_feedback,
                )
                prompt_scan = scan_round_prompt(prompt)
                if not prompt_scan["leakage_free"]:
                    raise RuntimeError(f"E63 prompt leakage for {tool.name} {setting}: {prompt_scan['hits']}")
                response = active_backend.complete(prompt)
                prompt_rows.append(
                    {
                        "prompt_id": f"{tool.name}:{setting}",
                        "tool_name": tool.name,
                        "setting": setting,
                        "round_index": round_index,
                        "backend": active_backend.backend_name,
                        "model": active_backend.model,
                        "prompt_hash": round_prompt_hash(prompt),
                        "output_hash": stable_hash({"output": response.text}),
                        "leakage_free": prompt_scan["leakage_free"],
                        "leakage_hits": prompt_scan["hits"],
                        "status": response.status,
                        "prompt": prompt,
                        "raw_output": response.text,
                    }
                )
                row, feedback, parsed = evaluate_round_output(
                    setting=setting,
                    round_index=round_index,
                    tool_name=tool.name,
                    raw_output=response.text,
                    response=response,
                )
                metric_rows.append(row)
                tool_rows.append(row)
                feedback_scan = feedback_leakage_scan(feedback)
                if not feedback_scan["leakage_free"]:
                    raise RuntimeError(f"E63 feedback leakage for {tool.name} {setting}: {feedback_scan['hits']}")
                feedback_rows.append(
                    {
                        "tool_name": tool.name,
                        "setting": setting,
                        "round_index": round_index,
                        "feedback": feedback,
                        "leakage_free": feedback_scan["leakage_free"],
                        "leakage_hits": feedback_scan["hits"],
                    }
                )
                candidate_rows.append(candidate_row(tool.name, setting, round_index, row, response, parsed))
                if row["freezeable"] != "true":
                    failure_rows.append(failure_row(tool.name, setting, row, feedback))
                previous_output = response.text
                previous_feedback = feedback
                if row["freezeable"] == "true":
                    break
            selection_rows.append(selection_row(tool.name, tool_rows))
    else:
        for tool in tools:
            prompt = build_round_prompt(tool=tool, round_index=0)
            prompt_scan = scan_round_prompt(prompt)
            prompt_rows.append(
                {
                    "prompt_id": f"{tool.name}:round_0_raw",
                    "tool_name": tool.name,
                    "setting": "round_0_raw",
                    "round_index": 0,
                    "backend": active_backend.backend_name,
                    "model": active_backend.model,
                    "prompt_hash": round_prompt_hash(prompt),
                    "output_hash": "",
                    "leakage_free": prompt_scan["leakage_free"],
                    "leakage_hits": prompt_scan["hits"],
                    "status": "not_executed",
                    "prompt": prompt,
                    "raw_output": "",
                }
            )

    report = build_report(
        tools=tools,
        backend=active_backend,
        backend_ok=backend_ok,
        backend_message=backend_message,
        max_rounds=rounds,
        metric_rows=metric_rows,
        prompt_rows=prompt_rows,
        feedback_rows=feedback_rows,
        candidate_rows=candidate_rows,
        failure_rows=failure_rows,
        selection_rows=selection_rows,
    )
    write_outputs(report, metric_rows, prompt_rows, feedback_rows, candidate_rows, failure_rows, selection_rows)
    return report


def backend_from_e63_env() -> CompletionBackend:
    backend = os.environ.get("E63_LOCAL_LLM_BACKEND", "none").strip().lower() or "none"
    model = os.environ.get("E63_LOCAL_LLM_MODEL", "").strip()
    base_url = os.environ.get("E63_LOCAL_LLM_BASE_URL", "").strip()
    max_tokens = int(os.environ.get("E63_LOCAL_LLM_MAX_TOKENS", "4096"))
    timeout = int(os.environ.get("E63_LOCAL_LLM_TIMEOUT", "240"))
    response_format = os.environ.get("E63_LOCAL_LLM_RESPONSE_FORMAT", "json_object").strip().lower()
    if backend == "none":
        return UnavailableBackend("E63_LOCAL_LLM_BACKEND is unset or none")
    if not model:
        return UnavailableBackend("E63_LOCAL_LLM_MODEL is required for local LLM execution")
    if backend == "ollama":
        return OllamaBackend(model, base_url or "http://127.0.0.1:11434", timeout=timeout, max_tokens=max_tokens, response_format=response_format)
    if backend == "openai_compatible":
        if not base_url:
            return UnavailableBackend("E63_LOCAL_LLM_BASE_URL is required for openai_compatible")
        return OpenAICompatibleBackend(model, base_url, timeout=timeout, max_tokens=max_tokens, response_format=response_format)
    return UnavailableBackend(f"Unsupported E63_LOCAL_LLM_BACKEND={backend}")


def evaluate_round_output(
    *,
    setting: str,
    round_index: int,
    tool_name: str,
    raw_output: str,
    response: LLMResponse,
) -> tuple[dict[str, Any], dict[str, Any], ParseResult]:
    tool = next(tool for tool in load_heldout_tools() if tool.name == tool_name)
    if response.status != "ok":
        feedback = build_feedback_payload(parse_error=response.error or response.status, round_index=round_index)
        return row_from_parse_failure(setting, round_index, tool_name, response.error or response.status, feedback), feedback, ParseResult(False, None, response.error or response.status)
    parsed = parse_contract_from_text(raw_output, tool_name=tool_name, setting=setting)
    if not parsed.parse_valid or parsed.contract is None:
        feedback = build_feedback_payload(parse_error=parsed.error, round_index=round_index)
        return row_from_parse_failure(setting, round_index, tool_name, parsed.error, feedback), feedback, parsed
    validation = validate_contract(parsed.contract, generate_reference_cases(tool))
    feedback = build_feedback_payload(validation=validation, round_index=round_index)
    row = row_from_validation(setting, round_index, tool_name, True, "", parsed.contract, validation, "local_llm")
    return row, feedback, parsed


def row_from_parse_failure(setting: str, round_index: int, tool_name: str, parse_error: str, feedback: dict[str, Any]) -> dict[str, Any]:
    categories = feedback.get("failure_categories", classify_failure(parse_error=parse_error))
    return {
        "setting": setting,
        "round_index": str(round_index),
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
    round_index: int,
    tool_name: str,
    parse_valid: bool,
    parse_error: str,
    contract: ToolEffectContract,
    validation,
    evidence_kind: str,
) -> dict[str, Any]:
    freezeable = can_freeze(parse_valid, validation)
    frozen_hash = ""
    if freezeable:
        frozen_hash = freeze_contract(contract, validation).contract_hash
    categories = classify_failure(parse_error=parse_error, validation=validation)
    return {
        "setting": setting,
        "round_index": str(round_index),
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
        "frozen_contract_hash": frozen_hash,
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


def candidate_row(tool_name: str, setting: str, round_index: int, row: dict[str, Any], response: LLMResponse, parsed: ParseResult) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "setting": setting,
        "round_index": round_index,
        "parse_valid": row["parse_valid"],
        "freezeable": row["freezeable"],
        "validation_passed": row["validation_passed"],
        "contract_hash": row.get("contract_hash", ""),
        "output_hash": stable_hash({"output": response.text}),
        "contract": parsed.contract.to_dict() if parsed.contract is not None else None,
        "parse_error": row.get("parse_error", ""),
        "raw_output": response.text,
    }


def failure_row(tool_name: str, setting: str, row: dict[str, Any], feedback: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "setting": setting,
        "round_index": row.get("round_index", ""),
        "failure_categories": feedback.get("failure_categories", []),
        "failed_axes": feedback.get("failed_axes", {}),
        "parse_error": row.get("parse_error", ""),
        "freezeable": row.get("freezeable", "false"),
        "required_atom_coverage": row.get("required_atom_coverage"),
        "required_resource_binding_coverage": row.get("required_resource_binding_coverage"),
        "required_target_principal_coverage": row.get("required_target_principal_coverage"),
        "unsafe_pre_allow_rate": row.get("unsafe_pre_allow_rate"),
        "false_deny_rate": row.get("false_deny_rate"),
        "hints": feedback.get("repair_hints", []),
    }


def selection_row(tool_name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    best = select_best_candidate(rows)
    return {
        "tool_name": tool_name,
        "selected_setting": best["setting"],
        "selected_round_index": best["round_index"],
        "selected_contract_hash": best.get("contract_hash", ""),
        "freezeable": best["freezeable"],
        "requires_human_review": str(best["freezeable"] != "true").lower(),
        "selection_reason": "first_freezeable" if best["freezeable"] == "true" else "best_non_freezeable_by_ordered_score",
        "required_atom_coverage": best.get("required_atom_coverage", ""),
        "required_resource_binding_coverage": best.get("required_resource_binding_coverage", ""),
        "required_target_principal_coverage": best.get("required_target_principal_coverage", ""),
        "unsafe_pre_allow_rate": best.get("unsafe_pre_allow_rate", ""),
        "false_deny_rate": best.get("false_deny_rate", ""),
        "decision_accuracy": best.get("decision_accuracy", ""),
    }


def build_report(
    *,
    tools,
    backend: CompletionBackend,
    backend_ok: bool,
    backend_message: str,
    max_rounds: int,
    metric_rows: list[dict[str, Any]],
    prompt_rows: list[dict[str, Any]],
    feedback_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    failure_rows: list[dict[str, Any]],
    selection_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    local_rows = [row for row in metric_rows if row["evidence_kind"] == "local_llm"]
    local_status = "executed" if backend_ok and local_rows else "not_executed"
    e62 = load_e62_comparison()
    freezeable_tools = [row for row in selection_rows if row["freezeable"] == "true"]
    return {
        "experiment": "E63 iterative counterfactual contract refinement",
        "status": "passed",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "backend": backend.backend_name,
        "model": backend.model,
        "model_source_path": os.environ.get("E63_LOCAL_LLM_MODEL_PATH", ""),
        "generation_limits": {
            "max_tokens": os.environ.get("E63_LOCAL_LLM_MAX_TOKENS", ""),
            "timeout_seconds": os.environ.get("E63_LOCAL_LLM_TIMEOUT", ""),
            "response_format": os.environ.get("E63_LOCAL_LLM_RESPONSE_FORMAT", "json_object"),
            "max_refinement_rounds": max_rounds,
        },
        "backend_health": {"ok": backend_ok, "message": backend_message},
        "local_llm_status": local_status,
        "n_heldout_tools": len(tools),
        "heldout_tool_names": [tool.name for tool in tools],
        "n_prompt_records": len(prompt_rows),
        "n_feedback_records": len(feedback_rows),
        "n_candidate_records": len(candidate_rows),
        "n_metric_rows": len(metric_rows),
        "n_failure_examples": len(failure_rows),
        "prompt_leakage_violations": sum(1 for row in prompt_rows if not row.get("leakage_free")),
        "feedback_leakage_violations": sum(1 for row in feedback_rows if not row.get("leakage_free")),
        "stub_harness": summarize_rows([row for row in metric_rows if row["setting"] == "stub_harness"]),
        "local_llm_all_rounds": summarize_rows(local_rows),
        "local_llm_final_selection": summarize_selection(selection_rows),
        "round_summaries": summarize_by_round(local_rows),
        "e62_comparison": e62,
        "freeze_criteria": {
            "parse_valid": True,
            "validation_passed": True,
            "required_atom_coverage": 1.0,
            "required_resource_binding_coverage": 1.0,
            "required_target_principal_coverage": 1.0,
            "unsafe_pre_allow_rate": 0.0,
            "missing_required_atom_count": 0,
        },
        "claim_boundary": claim_boundary_text(local_status, len(freezeable_tools), len(tools)),
        "conclusion": conclusion_text(local_status, len(freezeable_tools), len(tools)),
        "outputs": {
            "report_json": str(REPORT_JSON),
            "report_md": str(REPORT_MD),
            "round_metrics_csv": str(ROUND_METRICS_CSV),
            "candidate_contracts_jsonl": str(CANDIDATE_CONTRACTS),
            "prompts_jsonl": str(PROMPTS_JSONL),
            "feedback_payloads_jsonl": str(FEEDBACK_JSONL),
            "failure_examples_jsonl": str(FAILURE_EXAMPLES),
            "frozen_contracts_jsonl": str(FROZEN_CONTRACTS),
            "claim_boundary_md": str(CLAIM_BOUNDARY),
        },
    }


def load_e62_comparison() -> dict[str, Any]:
    path = RESULTS / "e62_local_llm_proposer_report.json"
    if not path.exists():
        return {"available": False}
    obj = json.loads(path.read_text(encoding="utf-8"))
    return {
        "available": True,
        "raw_parse_valid": obj.get("raw_local_llm", {}).get("parse_valid"),
        "raw_freezeable": obj.get("raw_local_llm", {}).get("freezeable"),
        "refined_parse_valid": obj.get("refined_local_llm", {}).get("parse_valid"),
        "refined_freezeable": obj.get("refined_local_llm", {}).get("freezeable"),
        "conclusion": obj.get("conclusion", ""),
    }


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n": 0, "parse_valid": 0, "validation_passed": 0, "freezeable": 0}
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
        "mean_decision_accuracy": mean_float(row["decision_accuracy"] for row in rows),
    }


def summarize_by_round(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["setting"], []).append(row)
    return {key: summarize_rows(value) for key, value in sorted(grouped.items())}


def summarize_selection(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n_tools": 0, "freezeable_tools": 0, "human_review_required": 0}
    return {
        "n_tools": len(rows),
        "freezeable_tools": sum(1 for row in rows if row["freezeable"] == "true"),
        "human_review_required": sum(1 for row in rows if row["requires_human_review"] == "true"),
        "mean_required_atom_coverage": mean_float(row["required_atom_coverage"] for row in rows),
        "mean_resource_binding_coverage": mean_float(row["required_resource_binding_coverage"] for row in rows),
        "mean_target_principal_coverage": mean_float(row["required_target_principal_coverage"] for row in rows),
        "mean_unsafe_pre_allow_rate": mean_float(row["unsafe_pre_allow_rate"] for row in rows),
        "mean_false_deny_rate": mean_float(row["false_deny_rate"] for row in rows),
    }


def mean_float(values) -> float:
    parsed = [float(value) for value in values if value not in ("", None)]
    if not parsed:
        return 0.0
    return round(sum(parsed) / len(parsed), 3)


def conclusion_text(local_status: str, freezeable: int, total: int) -> str:
    if local_status != "executed":
        return "Outcome C: local LLM was not executed; only the harness and prompt/feedback gates ran."
    if freezeable == total and total:
        return "Outcome A: iterative counterfactual feedback produced freezeable contracts for all held-out tools."
    if freezeable:
        return "Outcome B: iterative counterfactual feedback produced some freezeable contracts; remaining tools require human review."
    return "Outcome C: iterative counterfactual feedback did not produce freezeable contracts; validation routed all tools to human review."


def claim_boundary_text(local_status: str, freezeable: int, total: int) -> str:
    if local_status != "executed":
        return "E63 validates the iterative harness only until a configured local LLM backend is executed."
    return (
        f"E63 evaluates one configured local LLM backend on a 15-tool held-out mock suite with up to four sanitized counterfactual feedback rounds. "
        f"It froze {freezeable}/{total} tools. It does not support production safety, arbitrary-tool inference, live deployment safety, or real external API behavior."
    )


def write_outputs(
    report: dict[str, Any],
    metric_rows: list[dict[str, Any]],
    prompt_rows: list[dict[str, Any]],
    feedback_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    failure_rows: list[dict[str, Any]],
    selection_rows: list[dict[str, Any]],
) -> None:
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(report_markdown(report), encoding="utf-8")
    CLAIM_BOUNDARY.write_text(claim_boundary_markdown(report), encoding="utf-8")
    write_csv(ROUND_METRICS_CSV, metric_rows)
    write_jsonl(PROMPTS_JSONL, prompt_rows)
    write_jsonl(FEEDBACK_JSONL, feedback_rows)
    write_jsonl(CANDIDATE_CONTRACTS, candidate_rows)
    write_jsonl(FAILURE_EXAMPLES, failure_rows)
    write_jsonl(FROZEN_CONTRACTS, selection_rows)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "setting",
        "round_index",
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
        "frozen_contract_hash",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# E63 Iterative Counterfactual Contract Refinement Report",
        "",
        "## Summary",
        "",
        f"- Backend: `{report['backend']}`.",
        f"- Model: `{report['model']}`.",
        f"- Generation: max_tokens `{report['generation_limits'].get('max_tokens', '')}`, response_format `{report['generation_limits'].get('response_format', '')}`, max refinement rounds `{report['generation_limits'].get('max_refinement_rounds', '')}`.",
        f"- Backend health: `{report['backend_health']['ok']}` ({report['backend_health']['message']}).",
        f"- Local LLM status: `{report['local_llm_status']}`.",
        f"- Held-out tools: `{report['n_heldout_tools']}`.",
        f"- Candidate records: `{report['n_candidate_records']}`.",
        f"- Prompt leakage violations: `{report['prompt_leakage_violations']}`.",
        f"- Feedback leakage violations: `{report['feedback_leakage_violations']}`.",
        "",
        "## Final Selection",
        "",
        f"- Freezeable tools: `{report['local_llm_final_selection']['freezeable_tools']}/{report['local_llm_final_selection']['n_tools']}`.",
        f"- Human-review required: `{report['local_llm_final_selection']['human_review_required']}`.",
        f"- Mean required atom coverage: `{report['local_llm_final_selection'].get('mean_required_atom_coverage', 0.0)}`.",
        f"- Mean resource binding coverage: `{report['local_llm_final_selection'].get('mean_resource_binding_coverage', 0.0)}`.",
        f"- Mean target-principal coverage: `{report['local_llm_final_selection'].get('mean_target_principal_coverage', 0.0)}`.",
        "",
        "## E62 Comparison",
        "",
        json.dumps(report["e62_comparison"], indent=2, sort_keys=True),
        "",
        "## Conclusion",
        "",
        report["conclusion"],
        "",
        "## Claim Boundary",
        "",
        report["claim_boundary"],
        "",
    ]
    return "\n".join(lines)


def claim_boundary_markdown(report: dict[str, Any]) -> str:
    return f"""# E63 Claim Boundary

## Supported

- E63 evaluates iterative local-LLM contract proposal with sanitized counterfactual validation feedback.
- The artifact records every prompt, feedback payload, candidate contract, validation metric row, selected candidate, and freeze/human-review status.
- Frozen contracts are only emitted when strict validation gates pass.

## Unsupported

- No production safety claim.
- No real SaaS, email, Slack, payment, CI, calendar, filesystem, shell, or network side effect is executed.
- Non-freezeable selected candidates are not trusted runtime contracts.
- Passing E63 would not prove arbitrary LLMs can infer complete contracts for arbitrary tools.

Current local LLM status: `{report['local_llm_status']}`.

{report['claim_boundary']}
"""


if __name__ == "__main__":
    main()
