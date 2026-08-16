from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

from .adapters import REPO_URLS, _git_commit


def audit_external_reproductions(root: Path) -> dict[str, Any]:
    audits = {
        "toolsafe": audit_toolsafe(root),
        "safiron": audit_safiron(root),
        "ipiguard": audit_ipiguard(root),
        "camel": audit_camel(root),
    }
    return {
        "schema_version": "tool_effect_fragmentation_phase2_reproduction_audit_v1",
        "audits": audits,
        "acceptance_summary": {
            "non_agentdojo_complete_audit": any(audit["audit_complete"] for audit in audits.values()),
            "original_method_result_available": any(audit["status"] == "original_method_runnable" for audit in audits.values()),
            "complete_adapter_failed_available": any(audit["status"] == "adapter_failed_complete" for audit in audits.values()),
            "priority_order": ["toolsafe", "safiron", "ipiguard", "camel"],
        },
    }


def audit_toolsafe(root: Path) -> dict[str, Any]:
    repo = root / "external/systems/toolsafe"
    config = repo / "src/config_guardrail_eval/agentdojo_traj.yaml"
    script = repo / "src/guardian_experiment.py"
    ts_bench = repo / "TS-Bench"
    expected_model_path = "/mnt/shared-storage-user/mouyutao/AShell-ours/verl-main/checkpoints/verl_grpo_ashell_guardian_v2.4.0-rollout16_multitask_uniform/qwen2.5_7b_function_rm/global_step_80/actor_hf"
    blockers = []
    if not repo.exists():
        blockers.append("repository_missing")
    if not ts_bench.exists():
        blockers.append("ts_bench_missing")
    if not script.exists():
        blockers.append("guardian_experiment_missing")
    if not config.exists():
        blockers.append("agentdojo_traj_config_missing")
    if not Path(expected_model_path).exists():
        blockers.append(f"configured_local_ts_guard_model_missing:{expected_model_path}")
    if not _module_available("vllm"):
        blockers.append("vllm_not_installed_for_local_guardian")
    if not _module_available("transformers"):
        blockers.append("transformers_not_installed")
    attempted = [
        "python src/guardian_experiment.py --config ./src/config_guardrail_eval/agentdojo_traj.yaml",
    ]
    return _audit(
        system="toolsafe",
        repo=repo,
        artifact=ts_bench,
        model_url="https://huggingface.co/MurrayTom/TS-Guard",
        attempted_commands=attempted,
        blockers=blockers,
        notes=[
            "TS-Bench data and evaluation script are present in the cloned repository.",
            "Exact TS-Guard reproduction requires the released/local guardian checkpoint and vLLM-compatible runtime.",
        ],
    )


def audit_safiron(root: Path) -> dict[str, Any]:
    repo = root / "external/systems/agentic_guardian"
    dataset = repo / "Pre-Ex-Bench/dataset.json"
    local_model = root / "models/Safiron/Safiron"
    blockers = []
    if not repo.exists():
        blockers.append("repository_missing")
    if not dataset.exists():
        blockers.append("pre_ex_bench_dataset_missing")
    if not _module_available("vllm"):
        blockers.append("vllm_not_installed_for_safiron")
    if not local_model.exists():
        blockers.append(f"safiron_model_not_verified_locally:{local_model}")
    attempted = [
        'python -c "from vllm import LLM; LLM(model=\'Safiron/Safiron\')"',
        "python evaluation/eval.py --test-file <predictions.json> --model gpt-4o-mini --out-file evaluation/eval_results.json",
    ]
    return _audit(
        system="safiron",
        repo=repo,
        artifact=dataset,
        model_url="https://huggingface.co/Safiron/Safiron",
        attempted_commands=attempted,
        blockers=blockers,
        notes=[
            "Pre-Ex-Bench dataset is present and already used by the proxy adapter.",
            "Exact Safiron result requires model inference with vLLM and optional LLM explanation evaluator; this audit does not count model availability unless a local model path is verified.",
        ],
    )


def audit_ipiguard(root: Path) -> dict[str, Any]:
    repo = root / "external/systems/ipiguard"
    eval_script = repo / "eval.sh"
    agentdojo_pkg = repo / "agentdojo"
    blockers = []
    if not repo.exists():
        blockers.append("repository_missing")
    if not eval_script.exists():
        blockers.append("eval_sh_missing")
    if not agentdojo_pkg.exists():
        blockers.append("vendored_agentdojo_missing")
    if not os.environ.get("OPENAI_API_KEY"):
        blockers.append("OPENAI_API_KEY_missing_for_official_eval")
    if not os.environ.get("OPENAI_BASE_URL"):
        blockers.append("OPENAI_BASE_URL_missing_for_official_eval")
    attempted = ["bash eval.sh"]
    return _audit(
        system="ipiguard",
        repo=repo,
        artifact=eval_script,
        model_url="OpenAI-compatible API configured by OPENAI_API_KEY/OPENAI_BASE_URL",
        attempted_commands=attempted,
        blockers=blockers,
        notes=[
            "IPIGuard official evaluation is API-backed and AgentDojo-based.",
            "Phase 2 does not run the official eval unless OpenAI-compatible API credentials are configured externally.",
        ],
    )


def audit_camel(root: Path) -> dict[str, Any]:
    repo = root / "external/systems/camel"
    main = repo / "main.py"
    blockers = []
    if not repo.exists():
        blockers.append("repository_missing")
    if not main.exists():
        blockers.append("main_py_missing")
    if not os.environ.get("OPENAI_API_KEY"):
        blockers.append("OPENAI_API_KEY_missing_for_camel_eval")
    attempted = ["uv run --env-file .env main.py MODEL_NAME=<model>"]
    return _audit(
        system="camel",
        repo=repo,
        artifact=main,
        model_url="structural defense code; model selected at runtime",
        attempted_commands=attempted,
        blockers=blockers,
        notes=[
            "CaMeL is a structural-defense contrast, not a row classifier.",
            "No non-side-effectful Tool-Effect dry-run adapter is currently wired.",
        ],
    )


def audit_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 2 External Reproduction Audit",
        "",
        "| System | Status | Repo commit | Artifact | Model/API | Blockers |",
        "|---|---|---|---|---|---|",
    ]
    for system, audit in result["audits"].items():
        lines.append(
            "| `{}` | `{}` | `{}` | `{}` | {} | {} |".format(
                system,
                audit["status"],
                audit["source_commit_hash"],
                audit["source_artifact_path"],
                audit["model_or_api"],
                "; ".join(audit["blockers"]) or "none",
            )
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- `adapter_failed_complete` means reproduction was audited and blocked; it is not a negative method result.",
            "- `original_method_runnable` only means the local prerequisites appear present; paper-grade status still requires running and validating outputs.",
        ]
    )
    return "\n".join(lines) + "\n"


def _audit(
    *,
    system: str,
    repo: Path,
    artifact: Path,
    model_url: str,
    attempted_commands: list[str],
    blockers: list[str],
    notes: list[str],
) -> dict[str, Any]:
    status = "original_method_runnable" if not blockers else "adapter_failed_complete"
    return {
        "system": system,
        "status": status,
        "audit_complete": True,
        "source_repo_url": REPO_URLS.get(system, ""),
        "source_commit_hash": _git_commit(repo),
        "source_artifact_path": str(artifact),
        "repo_present": repo.exists(),
        "artifact_present": artifact.exists(),
        "model_or_api": model_url,
        "attempted_commands": attempted_commands,
        "blockers": blockers,
        "notes": notes,
        "claim_scope": "adapter_failed" if blockers else "original_method_candidate",
    }


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None
