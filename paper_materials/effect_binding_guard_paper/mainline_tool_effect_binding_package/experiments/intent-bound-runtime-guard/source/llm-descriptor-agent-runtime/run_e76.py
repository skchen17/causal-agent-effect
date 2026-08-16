"""Build E76 LLM-generated descriptors for AgentDojo official-live runtime."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from openai import OpenAI

from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.full_atom_runtime import SIDE_EFFECT_TO_EFFECT
from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.run_e75 import E75_VENV_PYTHON, PACKAGE_ROOT
from src.experiments.effect_binding_guard.e76_llm_descriptor_agentdojo_runtime.llm_descriptor_runtime import (
    descriptor_prompt,
    extract_json_object,
    parse_descriptor,
    runtime_registry_report,
    sanitized_feedback,
    validate_descriptor_against_tool,
)


RESULTS = PACKAGE_ROOT / "analysis/results"
TOOL_VIEWS_JSONL = RESULTS / "e76_agentdojo_tool_onboarding_views.jsonl"
CANDIDATES_JSONL = RESULTS / "e76_llm_descriptor_candidates.jsonl"
FEEDBACK_JSONL = RESULTS / "e76_counterfactual_descriptor_feedback.jsonl"
SCORES_CSV = RESULTS / "e76_counterfactual_descriptor_scores.csv"
REGISTERED_JSONL = RESULTS / "e76_registered_llm_tool_descriptors.jsonl"
REPORT_JSON = RESULTS / "e76_llm_descriptor_registration_report.json"
REPORT_MD = RESULTS / "e76_llm_descriptor_registration_report.md"
CLAIM_BOUNDARY_MD = RESULTS / "e76_claim_boundary.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run E76 LLM descriptor registration.")
    parser.add_argument("--agentdojo-version", default="v1.1.2")
    parser.add_argument("--suites", default="workspace,slack,travel,banking")
    parser.add_argument("--base-url", default="http://127.0.0.1:18080/v1")
    parser.add_argument("--model", default="")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--timeout", type=float, default=240.0)
    parser.add_argument("--reuse-candidates", action="store_true")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main() -> None:
    report = run(parse_args())
    print(json.dumps({"status": report["status"], "report": str(REPORT_JSON)}, indent=2))


def run(args: argparse.Namespace) -> dict[str, Any]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    tool_views = extract_agentdojo_tool_views(args.agentdojo_version, parse_csv(args.suites))
    write_jsonl(TOOL_VIEWS_JSONL, tool_views)
    if args.reuse_candidates and CANDIDATES_JSONL.exists():
        candidates = read_jsonl(CANDIDATES_JSONL)
        feedback_rows = read_jsonl(FEEDBACK_JSONL) if FEEDBACK_JSONL.exists() else []
    else:
        candidates, feedback_rows = run_llm_descriptor_loop(args, tool_views)
        write_jsonl(CANDIDATES_JSONL, candidates)
        write_jsonl(FEEDBACK_JSONL, feedback_rows)
    scores = score_candidates(candidates, tool_views)
    selected = select_registered(candidates, scores)
    write_scores_csv(SCORES_CSV, scores)
    write_jsonl(REGISTERED_JSONL, selected)
    report = build_report(args, tool_views, candidates, feedback_rows, scores, selected)
    write_json(REPORT_JSON, report)
    write_report_md(REPORT_MD, report)
    CLAIM_BOUNDARY_MD.write_text(report["claim_boundary"] + "\n", encoding="utf-8")
    return report


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def extract_agentdojo_tool_views(agentdojo_version: str, suites: list[str]) -> list[dict[str, Any]]:
    if not E75_VENV_PYTHON.exists():
        raise FileNotFoundError(f"Missing AgentDojo venv: {E75_VENV_PYTHON}")
    code = r'''
import json
from agentdojo.task_suite.load_suites import get_suite
version = __VERSION__
suites = __SUITES__
rows = []
for suite_name in suites:
    suite = get_suite(version, suite_name)
    for tool in suite.tools:
        schema = tool.parameters.model_json_schema()
        rows.append({
            "suite_name": suite_name,
            "tool_name": tool.name,
            "description": tool.description or "",
            "parameters": schema.get("properties", {}),
            "required_fields": sorted(schema.get("required", [])),
        })
print(json.dumps(rows, sort_keys=True))
'''.replace("__VERSION__", json.dumps(agentdojo_version)).replace("__SUITES__", json.dumps(suites))
    completed = subprocess.run([str(E75_VENV_PYTHON), "-c", code], text=True, capture_output=True, check=True)
    raw_rows = json.loads(completed.stdout)
    grouped: dict[str, dict[str, Any]] = {}
    for row in raw_rows:
        tool_name = row["tool_name"]
        if tool_name not in SIDE_EFFECT_TO_EFFECT:
            continue
        current = grouped.setdefault(
            tool_name,
            {
                "tool_name": tool_name,
                "suite_names": [],
                "description": "",
                "parameters": {},
                "required_fields": [],
                "reference_effect_hidden_from_prompt": SIDE_EFFECT_TO_EFFECT[tool_name],
            },
        )
        current["suite_names"].append(row["suite_name"])
        if row.get("description") and row["description"] not in current["description"]:
            current["description"] = (current["description"] + "\n" + row["description"]).strip()
        current["parameters"].update(row.get("parameters", {}))
        current["required_fields"] = sorted(set(current["required_fields"]) | set(row.get("required_fields", [])))
    return [grouped[name] for name in sorted(grouped)]


def run_llm_descriptor_loop(args: argparse.Namespace, tool_views: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    client = OpenAI(api_key="EMPTY", base_url=args.base_url, timeout=args.timeout)
    model = args.model or client.models.list().data[0].id
    candidates: list[dict[str, Any]] = read_jsonl(CANDIDATES_JSONL) if args.resume and CANDIDATES_JSONL.exists() else []
    feedback_rows: list[dict[str, Any]] = read_jsonl(FEEDBACK_JSONL) if args.resume and FEEDBACK_JSONL.exists() else []
    seen_candidate_ids = {row["candidate_id"] for row in candidates}
    CANDIDATES_JSONL.parent.mkdir(parents=True, exist_ok=True)
    if not args.resume:
        CANDIDATES_JSONL.write_text("", encoding="utf-8")
        FEEDBACK_JSONL.write_text("", encoding="utf-8")
    for tool_view in tool_views:
        previous: dict[str, Any] | None = None
        feedback: dict[str, Any] | None = None
        for round_index in range(args.rounds + 1):
            candidate_id = f"{tool_view['tool_name']}#round{round_index}"
            if candidate_id in seen_candidate_ids:
                existing = next(row for row in candidates if row["candidate_id"] == candidate_id)
                if existing.get("parse_valid"):
                    previous = existing.get("descriptor")
                feedback = sanitized_feedback(
                    validate_descriptor_against_tool(existing["descriptor"], tool_view)
                    if existing.get("parse_valid")
                    else {
                        "registered": False,
                        "failure_categories": ["parse_invalid"],
                        "unclassified_fields": sorted(tool_view["parameters"]),
                        "unknown_references": [],
                        "missing_required_fields": sorted(tool_view["required_fields"]),
                    }
                )
                continue
            prompt = descriptor_prompt(tool_view, previous=previous, feedback=feedback)
            started = time.time()
            raw = ""
            parse_valid = False
            descriptor = None
            error = ""
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    top_p=1.0,
                    max_tokens=args.max_tokens,
                    response_format={"type": "json_object"},
                )
                raw = response.choices[0].message.content or ""
                descriptor = normalize_param_literals(parse_descriptor(extract_json_object(raw), tool_view["tool_name"]), tool_view)
                parse_valid = True
            except Exception as exc:  # noqa: BLE001
                error = repr(exc)
            validation = validate_descriptor_against_tool(descriptor, tool_view) if parse_valid else {
                "registered": False,
                "referenced_params": [],
                "non_security_fields": [],
                "unknown_references": [],
                "unclassified_fields": sorted(tool_view["parameters"]),
                "missing_required_fields": sorted(tool_view["required_fields"]),
                "field_sensitivity_checks": [],
                "field_sensitivity_pass_rate": 0.0,
                "surface_invariance_pass": False,
                "injection_stability_pass": False,
                "failure_categories": ["parse_invalid"],
            }
            row = {
                "candidate_id": f"{tool_view['tool_name']}#round{round_index}",
                "tool_name": tool_view["tool_name"],
                "suite_names": tool_view["suite_names"],
                "round_index": round_index,
                "parse_valid": parse_valid,
                "parse_error": error,
                "descriptor": descriptor,
                "elapsed_seconds": round(time.time() - started, 3),
                "raw_output_prefix": raw[:1200],
                "registered": validation["registered"],
                "descriptor_score": descriptor_score(parse_valid, validation),
                **validation,
            }
            candidates.append(row)
            feedback = sanitized_feedback(validation)
            feedback_row = {
                "candidate_id": row["candidate_id"],
                "tool_name": tool_view["tool_name"],
                "round_index": round_index,
                "feedback": feedback,
                "feedback_is_sanitized": True,
                "hidden_reference_not_in_feedback": True,
            }
            feedback_rows.append(feedback_row)
            append_jsonl(CANDIDATES_JSONL, row)
            append_jsonl(FEEDBACK_JSONL, feedback_row)
            if parse_valid:
                previous = descriptor
            if validation["registered"]:
                break
    return candidates, feedback_rows


def descriptor_score(parse_valid: bool, validation: dict[str, Any]) -> float:
    if not parse_valid:
        return 0.0
    score = 0.35
    if validation["registered"]:
        score += 0.35
    score += 0.15 * validation.get("field_sensitivity_pass_rate", 0.0)
    score += 0.05 if validation.get("surface_invariance_pass") else 0.0
    score += 0.05 if validation.get("injection_stability_pass") else 0.0
    score -= 0.02 * len(validation.get("unclassified_fields", []))
    score -= 0.02 * len(validation.get("unknown_references", []))
    score -= 0.02 * len(validation.get("missing_required_fields", []))
    return round(max(0.0, min(1.0, score)), 4)


def normalize_param_literals(descriptor: dict[str, Any], tool_view: dict[str, Any]) -> dict[str, Any]:
    params = set(tool_view.get("parameters", {}))

    def fix_binding(binding: str) -> str:
        raw = binding
        if binding.startswith("literal:"):
            raw = binding.split(":", 1)[1]
        if raw in params:
            return f"param:{raw}"
        for field in sorted(params, key=len, reverse=True):
            if raw == f"{{{field}}}" or raw.endswith(f":{{{field}}}") or raw.endswith(f":{field}"):
                return f"param:{field}"
        return binding

    descriptor["field_bindings"] = {key: fix_binding(value) for key, value in descriptor["field_bindings"].items()}
    for template in descriptor["atom_templates"]:
        template["field_bindings"] = {key: fix_binding(value) for key, value in template["field_bindings"].items()}
    return descriptor


def score_candidates(candidates: list[dict[str, Any]], tool_views: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tool_by_name = {row["tool_name"]: row for row in tool_views}
    scores = []
    for row in candidates:
        validation = validate_descriptor_against_tool(row["descriptor"], tool_by_name[row["tool_name"]]) if row.get("parse_valid") else {
            "registered": False,
            "failure_categories": ["parse_invalid"],
            "referenced_params": [],
            "non_security_fields": [],
            "unknown_references": [],
            "unclassified_fields": sorted(tool_by_name[row["tool_name"]]["parameters"]),
            "missing_required_fields": sorted(tool_by_name[row["tool_name"]]["required_fields"]),
            "field_sensitivity_pass_rate": 0.0,
        }
        scores.append(
            {
                "candidate_id": row["candidate_id"],
                "tool_name": row["tool_name"],
                "round_index": row["round_index"],
                "parse_valid": bool(row.get("parse_valid")),
                "registered": bool(validation["registered"]),
                "descriptor_score": descriptor_score(bool(row.get("parse_valid")), validation),
                **validation,
            }
        )
    return scores


def select_registered(candidates: list[dict[str, Any]], scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidate_by_id = {row["candidate_id"]: row for row in candidates}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for score in scores:
        grouped[score["tool_name"]].append(score)
    selected = []
    for tool_name, rows in sorted(grouped.items()):
        ordered = sorted(rows, key=lambda row: (row["registered"], row["descriptor_score"], -row["round_index"]), reverse=True)
        best = ordered[0]
        candidate = candidate_by_id[best["candidate_id"]]
        selected.append(
            {
                "tool_name": tool_name,
                "candidate_id": best["candidate_id"],
                "round_index": best["round_index"],
                "parse_valid": best["parse_valid"],
                "registered": best["registered"],
                "requires_human_review": not best["registered"],
                "descriptor_score": best["descriptor_score"],
                "failure_categories": best["failure_categories"],
                "referenced_params": best["referenced_params"],
                "non_security_fields": best["non_security_fields"],
                "unclassified_fields": best["unclassified_fields"],
                "missing_required_fields": best["missing_required_fields"],
                "unknown_references": best["unknown_references"],
                "registration_policy": "llm_descriptor_counterfactual_field_gate",
                "descriptor": candidate.get("descriptor") if best["registered"] else None,
                "best_nonregistered_descriptor": candidate.get("descriptor") if not best["registered"] else None,
                "claim_boundary": "Registered means accepted for this AgentDojo official-live experimental runtime, not production-certified.",
            }
        )
    return selected


def build_report(
    args: argparse.Namespace,
    tool_views: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    feedback_rows: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    selected: list[dict[str, Any]],
) -> dict[str, Any]:
    registry = runtime_registry_report(selected)
    return {
        "experiment": "E76 LLM-generated atom descriptor AgentDojo runtime registration",
        "status": "passed",
        "agentdojo_version": args.agentdojo_version,
        "n_tool_views": len(tool_views),
        "n_descriptor_candidates": len(candidates),
        "n_feedback_rows": len(feedback_rows),
        "registry_summary": registry,
        "registered_tools": [row["tool_name"] for row in selected if row["registered"]],
        "unregistered_tools": [row["tool_name"] for row in selected if not row["registered"]],
        "artifacts": {
            "tool_views_jsonl": str(TOOL_VIEWS_JSONL),
            "descriptor_candidates_jsonl": str(CANDIDATES_JSONL),
            "feedback_jsonl": str(FEEDBACK_JSONL),
            "scores_csv": str(SCORES_CSV),
            "registered_jsonl": str(REGISTERED_JSONL),
        },
        "claim_boundary": (
            "E76 uses a local LLM only for offline effect recognition and atom descriptor generation. "
            "Counterfactual field checks register only descriptors whose tool parameters are either atom-bound "
            "or explicitly non-security. Runtime AgentDojo execution must load only the registered descriptor JSONL; "
            "unregistered side-effect tools fail closed. This is not a production-safety claim."
        ),
    }


def write_scores_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "candidate_id",
        "tool_name",
        "round_index",
        "parse_valid",
        "registered",
        "descriptor_score",
        "field_sensitivity_pass_rate",
        "failure_categories",
        "referenced_params",
        "non_security_fields",
        "unclassified_fields",
        "missing_required_fields",
        "unknown_references",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(row.get(key), sort_keys=True) if isinstance(row.get(key), (list, dict)) else row.get(key) for key in fieldnames})


def write_report_md(path: Path, report: dict[str, Any]) -> None:
    registry = report["registry_summary"]
    lines = [
        "# E76 LLM Descriptor Registration Report",
        "",
        f"- Status: `{report['status']}`",
        f"- AgentDojo version: `{report['agentdojo_version']}`",
        f"- Tool views: `{report['n_tool_views']}`",
        f"- Descriptor candidates: `{report['n_descriptor_candidates']}`",
        f"- Registered tools: `{registry['registered_tools']}/{registry['n_tools']}`",
        f"- Unregistered tools: `{registry['unregistered_tools']}/{registry['n_tools']}`",
        "",
        "## Registered Tools",
        "",
        ", ".join(f"`{name}`" for name in report["registered_tools"]) or "None",
        "",
        "## Unregistered Tools",
        "",
        ", ".join(f"`{name}`" for name in report["unregistered_tools"]) or "None",
        "",
        "## Claim Boundary",
        "",
        report["claim_boundary"],
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    main()
