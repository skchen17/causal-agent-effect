from __future__ import annotations

from pathlib import Path
from typing import Any

from .access_guards import audit_prediction_access
from .io_utils import write_json
from .metrics import summarize_by_method
from .schema import AdapterManifest, ClaimScope, ToolEffectPrediction, ToolEffectStressCase


def write_system_report(
    *,
    system: str,
    cases: list[ToolEffectStressCase],
    predictions: list[ToolEffectPrediction],
    manifest: AdapterManifest,
    output_json: Path,
    output_md: Path,
) -> dict[str, Any]:
    metrics = summarize_by_method(cases, predictions)
    access = access_guard_summary(predictions)
    payload = {
        "schema_version": "tool_effect_fragmentation_v1",
        "system": system,
        "manifest": manifest.to_dict(),
        "n_cases": len(cases),
        "n_predictions": len(predictions),
        "metrics_by_method": metrics,
        "access_guard_summary": access,
        "claim_boundary": claim_boundary(manifest),
    }
    write_json(output_json, payload)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(system_markdown(payload), encoding="utf-8")
    return payload


def write_unified_report(system_payloads: list[dict[str, Any]], output_json: Path, output_md: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    adapter_failures: list[dict[str, Any]] = []
    for payload in system_payloads:
        if payload["manifest"]["adapter_status"] == "adapter_failed":
            adapter_failures.append(
                {
                    "system": payload["system"],
                    "adapter_status": payload["manifest"]["adapter_status"],
                    "source_repo_url": payload["manifest"].get("source_repo_url", ""),
                    "source_commit_hash": payload["manifest"].get("source_commit_hash", ""),
                    "source_artifact_path": payload["manifest"].get("source_artifact_path", ""),
                    "notes": payload["manifest"].get("notes", []),
                }
            )
        for method, metrics in payload["metrics_by_method"].items():
            rows.append(
                {
                    "system": payload["system"],
                    "adapter_status": payload["manifest"]["adapter_status"],
                    "paper_grade_eligible": payload["manifest"]["paper_grade_eligible"],
                    "paper_grade_environment": payload["manifest"].get("paper_grade_environment", False),
                    "paper_grade_method": payload["manifest"].get("paper_grade_method", False),
                    "method": method,
                    "claim_scope": method_claim_scope(method),
                    "n_cases": payload["n_cases"],
                    "fnr": metrics["fnr"]["rate"],
                    "held_out_tool_fnr": metrics["held_out_tool_fnr"]["rate"],
                    "held_out_wrapper_fnr": metrics["held_out_wrapper_fnr"]["rate"],
                    "tool_proxy_gap": metrics["tool_proxy_gap"],
                    "unsafe_action_pre_allow": metrics["unsafe_action_pre_allow"]["rate"],
                    "safe_action_false_deny": metrics["safe_action_false_deny"]["rate"],
                    "abstain_rate": metrics["abstain_rate"]["rate"],
                    "intra_action_decision_inconsistency": metrics["intra_action_decision_inconsistency"]["rate"],
                    "action_level_decision_error": metrics["action_level_decision_error"]["rate"],
                    "access_guard_passed": payload["access_guard_summary"].get(method, {}).get("passed", False),
                }
            )
    payload = {
        "schema_version": "tool_effect_fragmentation_unified_v1",
        "systems": [p["system"] for p in system_payloads],
        "manifests": [p["manifest"] for p in system_payloads],
        "adapter_failures": adapter_failures,
        "comparison_rows": rows,
        "answers": answer_required_questions(rows),
        "claim_boundary": [
            "Only systems with paper_grade_eligible=true support paper-grade conclusions.",
            "Proxy diagnostics identify stress-test feasibility and likely failure modes; they are not author-method reproductions.",
            "Negative results must be separated from adapter/reproduction failures.",
        ],
    }
    write_json(output_json, payload)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(unified_markdown(payload), encoding="utf-8")
    return payload


def claim_boundary(manifest: AdapterManifest) -> list[str]:
    if manifest.paper_grade_eligible:
        return [
            "Paper-grade only for the local artifacts named in source_path/source_version.",
            "Perturbed stress cases are synthetic transformations and should be reported as stress tests, not original benchmark metrics.",
        ]
    if manifest.adapter_status == "proxy_diagnostic":
        return [
            "Proxy diagnostic only; not an original-author reproduction.",
            "Use for framework validation and hypothesis generation, not for method-performance claims.",
        ]
    return ["Adapter failed; no method conclusion should be drawn."]


def system_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Tool-Effect Fragmentation: {payload['system']}",
        "",
        f"- Adapter status: `{payload['manifest']['adapter_status']}`",
        f"- Paper-grade eligible: `{payload['manifest']['paper_grade_eligible']}`",
        f"- Cases: `{payload['n_cases']}`",
        "",
        "## Metrics",
        "",
        "| Method | FNR | Held-out-tool FNR | Held-out-wrapper FNR | ToolProxyGap | Unsafe pre-allow | Safe false deny | Abstain | Intra-action inconsistency | Action-level error | Access guard |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for method, metrics in payload["metrics_by_method"].items():
        access = payload["access_guard_summary"].get(method, {})
        lines.append(
            "| `{}` | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                method,
                _fmt(metrics["fnr"]["rate"]),
                _fmt(metrics["held_out_tool_fnr"]["rate"]),
                _fmt(metrics["held_out_wrapper_fnr"]["rate"]),
                _fmt(metrics["tool_proxy_gap"]),
                _fmt(metrics["unsafe_action_pre_allow"]["rate"]),
                _fmt(metrics["safe_action_false_deny"]["rate"]),
                _fmt(metrics["abstain_rate"]["rate"]),
                _fmt(metrics["intra_action_decision_inconsistency"]["rate"]),
                _fmt(metrics["action_level_decision_error"]["rate"]),
                "PASS" if access.get("passed") else "FAIL",
            )
        )
    lines.extend(["", "## Claim Boundary", ""])
    lines.extend(f"- {item}" for item in payload["claim_boundary"])
    lines.extend(["", "## Reproduction Notes", ""])
    lines.extend(f"- {item}" for item in payload["manifest"]["notes"])
    return "\n".join(lines) + "\n"


def unified_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Unified Tool-Effect Fragmentation Comparison",
        "",
        "## Required Questions",
        "",
    ]
    for question, answer in payload["answers"].items():
        lines.append(f"- **{question}** {answer}")
    lines.extend([
        "",
        "## Paper-Grade Environment Results",
        "",
    ])
    lines.extend(_table([row for row in payload["comparison_rows"] if row["paper_grade_environment"]]))
    lines.extend(["", "## Original Method Reproductions", ""])
    lines.extend(_table([row for row in payload["comparison_rows"] if row["paper_grade_method"] or row["claim_scope"] == ClaimScope.ORIGINAL_METHOD.value]))
    lines.extend(["", "## Proxy Diagnostics", ""])
    lines.extend(_table([row for row in payload["comparison_rows"] if row["adapter_status"] == "proxy_diagnostic"]))
    lines.extend(["", "## Baselines", ""])
    lines.extend(_table([row for row in payload["comparison_rows"] if row["claim_scope"] == ClaimScope.BASELINE.value]))
    lines.extend(["", "## Oracle / Upper-Bound Rows", ""])
    lines.extend(_table([row for row in payload["comparison_rows"] if row["claim_scope"] == ClaimScope.UPPER_BOUND.value]))
    lines.extend(["", "## Adapter Failures", ""])
    lines.extend(_failure_table(payload.get("adapter_failures", [])))
    lines.extend(["", "## Claim Boundary", ""])
    lines.extend(f"- {item}" for item in payload["claim_boundary"])
    return "\n".join(lines) + "\n"


def answer_required_questions(rows: list[dict[str, Any]]) -> dict[str, str]:
    paper_rows = [row for row in rows if row["paper_grade_eligible"]]
    graph_rows = [row for row in rows if row["system"] in {"ipiguard"}]
    return {
        "Does the method detect realized effects or tool surfaces?": "Compare tool-name/schema baselines against effect/resource and execution-evidence baselines; high ToolProxyGap indicates surface dependence.",
        "Does performance collapse under tool surface shift?": "Use held-out-tool FNR and Effect Invariance Gap; v1 reports these per method and system.",
        "Which granularity is most robust to fragmentation?": "Compare systems by granularity through the system-specific tables; v1 has paper-grade AgentDojo and proxy step/graph diagnostics.",
        "Do graph/provenance/evidence-grounded methods reduce fragmentation?": f"Evidence-grounded rows available: {len(paper_rows)} paper-grade rows; graph rows available: {len(graph_rows)} proxy rows.",
        "Do row-level metrics overestimate action-level safety?": "Use intra-action inconsistency, action-level decision error, unsafe pre-allow, and safe false deny together; do not rely on row-level FNR alone.",
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def access_guard_summary(predictions: list[ToolEffectPrediction]) -> dict[str, Any]:
    by_method: dict[str, list[ToolEffectPrediction]] = {}
    for pred in predictions:
        by_method.setdefault(pred.method_name, []).append(pred)
    out: dict[str, Any] = {}
    for method, preds in by_method.items():
        violations = []
        for pred in preds:
            audit = audit_prediction_access(pred)
            violations.extend(audit.violations)
        out[method] = {"passed": not violations, "violations": sorted(set(violations))}
    return out


def method_claim_scope(method: str) -> str:
    if method in {"effect_resource_abstraction", "execution_evidence_upper_bound"}:
        return ClaimScope.UPPER_BOUND.value
    return ClaimScope.BASELINE.value


def _table(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| System | Status | Method | N | Held-out-tool FNR | ToolProxyGap | Unsafe pre-allow | Safe false deny | Intra-action inconsistency | Action-level error | Access |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    if not rows:
        lines.append("| NA | NA | NA | 0 | NA | NA | NA | NA | NA | NA | NA |")
        return lines
    for row in rows:
        lines.append(
            "| `{}` | `{}` | `{}` | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                row["system"],
                row["adapter_status"],
                row["method"],
                row["n_cases"],
                _fmt(row["held_out_tool_fnr"]),
                _fmt(row["tool_proxy_gap"]),
                _fmt(row["unsafe_action_pre_allow"]),
                _fmt(row["safe_action_false_deny"]),
                _fmt(row["intra_action_decision_inconsistency"]),
                _fmt(row["action_level_decision_error"]),
                "PASS" if row["access_guard_passed"] else "FAIL",
            )
        )
    return lines


def _failure_table(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| System | Status | Repo | Commit | Artifact | Notes |",
        "|---|---|---|---|---|---|",
    ]
    if not rows:
        lines.append("| NA | NA | NA | NA | NA | NA |")
        return lines
    for row in rows:
        notes = " ".join(str(item) for item in row.get("notes", []))
        lines.append(
            "| `{}` | `{}` | {} | `{}` | `{}` | {} |".format(
                row["system"],
                row["adapter_status"],
                row.get("source_repo_url", ""),
                row.get("source_commit_hash", ""),
                row.get("source_artifact_path", ""),
                notes.replace("|", "/"),
            )
        )
    return lines
