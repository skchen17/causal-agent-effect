from __future__ import annotations

from pathlib import Path
from typing import Any

from .reproduction_audit import audit_external_reproductions, audit_markdown


LOCAL_SMOKE_PATH = Path("analysis/results/tool_effect_fragmentation_external_smoke_phase3.json")
OFFICIAL_STRESS_PATHS = {
    "toolsafe": Path("analysis/results/tool_effect_fragmentation_toolsafe_official_stress_phase3.json"),
    "safiron": Path("analysis/results/tool_effect_fragmentation_safiron_official_stress_phase3.json"),
}


def run_phase3_reproduction_audit(root: Path, *, allow_model_download: bool = False, smoke_examples: int = 8) -> dict[str, Any]:
    base = audit_external_reproductions(root)
    local_smokes = load_local_smoke_results(root)
    official_stress = load_official_stress_results(root)
    for system, audit in base["audits"].items():
        saved_smoke = local_smokes.get(system)
        audit["phase3_smoke"] = saved_smoke or official_smoke_status(
            root, system, allow_model_download=allow_model_download, smoke_examples=smoke_examples
        )
        if system in official_stress:
            stress = official_stress[system]
            audit["phase3_official_custom_stress"] = stress
            audit["status"] = "original_method_custom_stress_available"
            audit["claim_scope"] = "original_method_custom_stress"
            audit["blockers"] = [
                "original_paper_benchmark_metric_reproduction_not_run",
                "custom_stress_expected_labels_are_proxy_or_published_derived",
            ]
            continue
        claim_scope = audit["phase3_smoke"].get("claim_scope")
        if audit["phase3_smoke"]["status"] == "smoke_passed" and claim_scope == "original_method_smoke":
            audit["status"] = "original_method_smoke_available"
            audit["claim_scope"] = "original_method_smoke"
            audit["blockers"] = ["full_tool_effect_fragmentation_evaluation_not_run"]
        elif audit["phase3_smoke"]["status"] == "smoke_passed" and claim_scope == "local_model_substitute":
            audit["status"] = "local_model_substitute_result_available"
            audit["claim_scope"] = "local_model_substitute"
            audit["blockers"] = [
                "official_api_backed_method_not_run",
                "full_tool_effect_fragmentation_evaluation_not_run",
            ]
        else:
            audit["status"] = "adapter_failed_complete"
            audit["claim_scope"] = "adapter_failed"
    base["acceptance_summary"] = {
        "original_method_result_available": any(audit["status"] == "original_method_result_available" for audit in base["audits"].values()),
        "original_method_smoke_available": any(audit["status"] == "original_method_smoke_available" for audit in base["audits"].values()),
        "original_method_custom_stress_available": any(
            audit["status"] == "original_method_custom_stress_available" for audit in base["audits"].values()
        ),
        "complete_adapter_failed_available": any(audit["status"] == "adapter_failed_complete" for audit in base["audits"].values()),
        "local_model_substitute_result_available": any(
            audit["status"] == "local_model_substitute_result_available" for audit in base["audits"].values()
        ),
        "non_agentdojo_phase3_target_satisfied": any(
            audit["status"] in {
                "original_method_result_available",
                "original_method_custom_stress_available",
                "original_method_smoke_available",
                "local_model_substitute_result_available",
                "adapter_failed_complete",
            }
            for audit in base["audits"].values()
        ),
        "allow_model_download": allow_model_download,
    }
    return base


def load_local_smoke_results(root: Path) -> dict[str, dict[str, Any]]:
    path = root / LOCAL_SMOKE_PATH
    if not path.exists():
        return {}
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("systems", {})


def load_official_stress_results(root: Path) -> dict[str, dict[str, Any]]:
    import json

    results: dict[str, dict[str, Any]] = {}
    for system, relative_path in OFFICIAL_STRESS_PATHS.items():
        path = root / relative_path
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("n_cases", 0) <= 0 or payload.get("n_parse_valid", 0) <= 0:
            continue
        results[system] = {
            "status": "custom_stress_completed",
            "claim_scope": "original_method_custom_stress",
            "method_name": payload.get("method_name"),
            "n_cases": payload.get("n_cases"),
            "n_parse_valid": payload.get("n_parse_valid"),
            "metrics": payload.get("metrics", {}),
            "metrics_by_perturbation": payload.get("metrics_by_perturbation", {}),
            "result_path": str(relative_path),
            "executes_tools": False,
            "executes_side_effects": False,
            "claim_boundary": payload.get("claim_boundary", []),
        }
    return results


def official_smoke_status(root: Path, system: str, *, allow_model_download: bool, smoke_examples: int) -> dict[str, Any]:
    if system == "toolsafe":
        model_path = root / "models/MurrayTom/TS-Guard"
        if not model_path.exists():
            return {
                "status": "not_run",
                "reason": f"local_ts_guard_checkpoint_missing:{model_path}",
                "recovery_option": "Provide TS-Guard local checkpoint path or rerun with explicit model download support.",
                "smoke_examples": smoke_examples,
            }
        return {
            "status": "not_run",
            "reason": "checkpoint_present_but_phase3_runner_does_not_execute_vllm_without_explicit_inference_adapter",
            "recovery_option": "Wire Guardian.get_judgment_res over TS-Bench rows and mark outputs original_method only after parsing succeeds.",
            "smoke_examples": smoke_examples,
        }
    if system == "safiron":
        model_path = root / "models/Safiron/Safiron"
        if not model_path.exists():
            return {
                "status": "not_run",
                "reason": f"local_safiron_model_missing:{model_path}",
                "recovery_option": "Place Safiron/Safiron model under models/Safiron/Safiron or run a dedicated model download step.",
                "smoke_examples": smoke_examples,
            }
        return {
            "status": "not_run",
            "reason": "local_model_present_but_no_official_inference_adapter_executed",
            "recovery_option": "Run vLLM/transformers inference over Pre-Ex-Bench and parse risk outputs.",
            "smoke_examples": smoke_examples,
        }
    if system == "ipiguard":
        return {
            "status": "not_run",
            "reason": "official_eval_requires_openai_compatible_api_and_is_not_side_effect_free_in_this_runner",
            "recovery_option": "Configure OPENAI_API_KEY/OPENAI_BASE_URL and run IPIGuard eval in a separate audited smoke harness.",
            "smoke_examples": smoke_examples,
        }
    if system == "camel":
        return {
            "status": "not_run",
            "reason": "no_non_side_effect_tool_effect_dry_run_adapter_available",
            "recovery_option": "Build a structural-defense dry-run adapter before reporting CaMeL comparisons.",
            "smoke_examples": smoke_examples,
        }
    return {"status": "not_run", "reason": "unknown_system", "smoke_examples": smoke_examples}


def phase3_reproduction_markdown(result: dict[str, Any]) -> str:
    text = audit_markdown(result)
    lines = text.rstrip().splitlines()
    if lines:
        lines[0] = "# Phase 3 External Reproduction Audit"
    lines.extend(["", "## Phase 3 Smoke Status", ""])
    for system, audit in result["audits"].items():
        smoke = audit.get("phase3_smoke", {})
        reason = smoke.get("reason", "completed")
        lines.append(
            f"- `{system}`: `{smoke.get('status')}`; claim scope: `{smoke.get('claim_scope', audit.get('claim_scope'))}`; "
            f"reason: {reason}"
        )
    lines.extend(["", "## Official-Checkpoint Custom Stress", ""])
    for system, audit in result["audits"].items():
        stress = audit.get("phase3_official_custom_stress")
        if not stress:
            lines.append(f"- `{system}`: not available")
            continue
        lines.append(
            f"- `{system}`: `{stress['n_cases']}` E47 custom cases, "
            f"`{stress['n_parse_valid']}` parse-valid; scope `{stress['claim_scope']}`."
        )
    lines.extend(
        [
            "",
            "## Phase 3 Claim Boundary",
            "",
            "- `original_method_custom_stress` uses a released checkpoint with its published prompt/output format on E47-adapted inputs.",
            "- It is stronger than a runnable smoke, but it is not an original-paper benchmark metric reproduction.",
            "- IPIGuard and CaMeL local-model substitutes validate adapter feasibility only and do not establish original-method behavior.",
        ]
    )
    return "\n".join(lines) + "\n"
