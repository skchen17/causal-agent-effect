#!/usr/bin/env python3
"""Audit external long-horizon benchmarks before E79 integration.

This is a static, fail-closed gate. It does not treat a README review as an
executed benchmark and it never calls a model provider or a real tool API.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT / "runs/e79_external_benchmarks"
RESULTS = ROOT / "analysis/results"


@dataclass(frozen=True)
class BenchmarkAudit:
    benchmark_id: str
    public_repository: str
    source_snapshot: str
    source_revision: str | None
    source_complete: bool
    license_verified: bool
    stateful_sandbox: bool
    executable_tools: bool
    trajectory_state_snapshots: bool
    terminal_validator: bool
    prefix_or_milestone_validator: bool
    native_long_horizon_attacks: bool
    local_model_endpoint: bool
    proprietary_model_required_by_default: bool
    real_external_side_effects_required: bool
    label_hidden_adapter_feasible: bool
    current_gate: str
    blocking_reasons: tuple[str, ...]
    recommended_role: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_revision(path: Path) -> str | None:
    if not (path / ".git").exists():
        return None
    completed = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def _contains(path: Path, *needles: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="replace").lower()
    return all(needle.lower() in text for needle in needles)


def build_audits() -> list[BenchmarkAudit]:
    tool_sandbox = EXTERNAL / "ToolSandbox"
    agentlab_meta = EXTERNAL / "metadata/AgentLAB"
    tau_meta = EXTERNAL / "metadata/tau2-bench"

    tool_complete = all(
        path.exists()
        for path in (
            tool_sandbox / "LICENSE",
            tool_sandbox / "pyproject.toml",
            tool_sandbox / "tool_sandbox/common/execution_context.py",
            tool_sandbox / "tool_sandbox/common/evaluation.py",
            tool_sandbox / "tool_sandbox/scenarios/multiple_tool_call_scenarios.py",
        )
    )
    tool_milestones = _contains(tool_sandbox / "README.md", "milestone dag", "world state")

    agentlab_metadata = all(
        path.exists()
        for path in (agentlab_meta / "README.md", agentlab_meta / "LICENSE", agentlab_meta / "requirements.txt")
    )
    agentlab_default_proprietary = _contains(agentlab_meta / "README.md", "planner and judge", "gpt-5.1")

    tau_metadata = all(
        path.exists()
        for path in (tau_meta / "README.md", tau_meta / "LICENSE", tau_meta / "pyproject.toml")
    )

    return [
        BenchmarkAudit(
            benchmark_id="toolsandbox",
            public_repository="https://github.com/apple/ToolSandbox",
            source_snapshot=str(tool_sandbox.relative_to(ROOT)),
            source_revision=_git_revision(tool_sandbox),
            source_complete=tool_complete,
            license_verified=(tool_sandbox / "LICENSE").exists(),
            stateful_sandbox=True,
            executable_tools=True,
            trajectory_state_snapshots=True,
            terminal_validator=True,
            prefix_or_milestone_validator=tool_milestones,
            native_long_horizon_attacks=False,
            local_model_endpoint=True,
            proprietary_model_required_by_default=False,
            real_external_side_effects_required=False,
            label_hidden_adapter_feasible=True,
            current_gate="ready_for_offline_environment_smoke" if tool_complete and tool_milestones else "blocked",
            blocking_reasons=(
                "Search scenarios require RapidAPI and must be excluded from the offline subset.",
                "The user simulator must be replaced with the fixed local checkpoint for comparable runs.",
                "Prompt-injection variants and per-prefix unauthorized-effect validators are not native and must be added.",
            ),
            recommended_role="Primary external long-task utility/state-dependency benchmark after an offline subset smoke.",
        ),
        BenchmarkAudit(
            benchmark_id="agentlab",
            public_repository="https://github.com/TanqiuJiang/AgentLAB",
            source_snapshot=str(agentlab_meta.relative_to(ROOT)),
            source_revision=None,
            source_complete=False,
            license_verified=agentlab_metadata and _contains(agentlab_meta / "LICENSE", "mit license"),
            stateful_sandbox=True,
            executable_tools=True,
            trajectory_state_snapshots=False,
            terminal_validator=True,
            prefix_or_milestone_validator=False,
            native_long_horizon_attacks=True,
            local_model_endpoint=True,
            proprietary_model_required_by_default=agentlab_default_proprietary,
            real_external_side_effects_required=False,
            label_hidden_adapter_feasible=True,
            current_gate="blocked_pending_full_source_and_local_judge_adapter",
            blocking_reasons=(
                "Only public metadata is complete locally; the full source checkout has not completed.",
                "The released default planner and judge use GPT-5.1, so a local replacement must be validated before a comparable run.",
                "Its judge-based success labels must be separated from deployable agent and guard inputs.",
            ),
            recommended_role="Adaptive long-horizon security extension after dependency and judge replacement smokes.",
        ),
        BenchmarkAudit(
            benchmark_id="tau2_bench",
            public_repository="https://github.com/sierra-research/tau2-bench",
            source_snapshot=str(tau_meta.relative_to(ROOT)),
            source_revision=None,
            source_complete=False,
            license_verified=tau_metadata and _contains(tau_meta / "LICENSE", "mit license"),
            stateful_sandbox=True,
            executable_tools=True,
            trajectory_state_snapshots=True,
            terminal_validator=True,
            prefix_or_milestone_validator=False,
            native_long_horizon_attacks=False,
            local_model_endpoint=True,
            proprietary_model_required_by_default=False,
            real_external_side_effects_required=False,
            label_hidden_adapter_feasible=True,
            current_gate="fallback_pending_full_source_checkout",
            blocking_reasons=(
                "Only public metadata is complete locally; the full source checkout has not completed.",
                "The benchmark supplies dynamic user interaction but not an indirect-prompt-injection attack protocol.",
                "Python 3.12+ requires an isolated environment from the current AgentDojo runner.",
            ),
            recommended_role="Fallback external long-task benchmark when dynamic user interaction is prioritized.",
        ),
    ]


def write_outputs(audits: list[BenchmarkAudit]) -> dict[str, Any]:
    source_files = sorted(
        path for path in EXTERNAL.glob("metadata/**/*") if path.is_file()
    ) + sorted(
        path
        for path in (
            EXTERNAL / "ToolSandbox/README.md",
            EXTERNAL / "ToolSandbox/LICENSE",
            EXTERNAL / "ToolSandbox/pyproject.toml",
        )
        if path.exists()
    )
    report: dict[str, Any] = {
        "experiment": "E79",
        "audit_type": "external_long_horizon_benchmark_static_gate",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if any(a.current_gate == "ready_for_offline_environment_smoke" for a in audits) else "blocked",
        "execution_claim": "No benchmark, model, tool, or external API was executed by this static audit.",
        "selection": {
            "offline_environment_smoke": "toolsandbox",
            "adaptive_attack_extension": "agentlab_after_local_judge_validation",
            "fallback": "tau2_bench",
        },
        "benchmarks": [asdict(audit) for audit in audits],
        "source_hashes": {
            str(path.relative_to(ROOT)): _sha256(path)
            for path in source_files
        },
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    json_path = RESULTS / "e79_external_benchmark_feasibility.json"
    md_path = RESULTS / "e79_external_benchmark_feasibility.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# E79 External Long-Horizon Benchmark Gate",
        "",
        f"Status: `{report['status']}`.",
        "",
        report["execution_claim"],
        "",
        "| Benchmark | Source | Gate | Intended role |",
        "|---|---|---|---|",
    ]
    for audit in audits:
        lines.append(
            f"| {audit.benchmark_id} | {'complete' if audit.source_complete else 'metadata only'} | "
            f"`{audit.current_gate}` | {audit.recommended_role} |"
        )
    lines.extend(["", "## Blocking Reasons", ""])
    for audit in audits:
        lines.append(f"### {audit.benchmark_id}")
        lines.extend(f"- {reason}" for reason in audit.blocking_reasons)
        lines.append("")
    lines.extend(
        [
            "## Decision",
            "",
            "ToolSandbox advances first to an offline environment smoke because its complete local snapshot exposes stateful tools, state snapshots, and milestone-DAG evaluation without requiring real external effects. AgentLAB remains the preferred adaptive-attack extension, but it cannot be reported as executed until the full source and a reproducible local planner/judge path pass. tau2-bench remains the dynamic-user fallback.",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-toolsandbox-ready", action="store_true")
    args = parser.parse_args()
    report = write_outputs(build_audits())
    if report["status"] != "passed":
        return 1
    if args.require_toolsandbox_ready:
        tool = next(row for row in report["benchmarks"] if row["benchmark_id"] == "toolsandbox")
        if tool["current_gate"] != "ready_for_offline_environment_smoke":
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
