#!/usr/bin/env python3
"""Summarize the E79 provenance-normalization development evidence."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentlab_provenance_normalized_patch import extract_agentlab_untrusted_control_segments
from src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.atom_envelope_policy import (
    evaluate_atom_envelope,
)


SCRIPT_PATH = Path(__file__).resolve()
ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *SCRIPT_PATH.parents)
    if (candidate / "paper/current-usenix").exists()
)
OLD_RUN = (
    ROOT
    / "experiments/long-horizon-transfer/runs/long-horizon-cross-environment-transfer/"
    "agentlab-c1f-current-profile/full/c1f"
)
PILOT = (
    ROOT
    / "experiments/long-horizon-transfer/runs/long-horizon-cross-environment-transfer/"
    "agentlab-c1f-provenance-normalized-deepseek-pilot"
)
QUEUE_STATUS = (
    ROOT
    / "experiments/long-horizon-transfer/runs/long-horizon-cross-environment-transfer/"
    "agentlab-c1f-provenance-normalized-qwen32/queue_status.json"
)
DESCRIPTORS = (
    ROOT
    / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/"
    "registered-effect-diff-descriptors.jsonl"
)
OUTPUT_JSON = ROOT / "analysis/results/e79_agentlab_provenance_normalization_pilot_report.json"
OUTPUT_MD = ROOT / "analysis/results/e79_agentlab_provenance_normalization_pilot_report.md"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def message_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "\n".join(
        str(block.get("content", ""))
        for block in content
        if isinstance(block, dict)
    )


def load_descriptors() -> dict[str, dict[str, Any]]:
    return {row["tool_name"]: row for row in read_jsonl(DESCRIPTORS)}


def retrospective_audit() -> dict[str, Any]:
    descriptors = load_descriptors()
    totals: Counter[str] = Counter()
    by_suite: dict[str, Counter[str]] = {}
    for path in sorted(OLD_RUN.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        suite = payload["suite_name"]
        suite_counts = by_suite.setdefault(suite, Counter())
        user_task = next(
            (message_text(row) for row in payload.get("messages", []) if row.get("role") == "user"),
            "",
        )
        evidence: list[dict[str, Any]] = []
        case_denied = False
        case_positive_evidence = False
        for message in payload.get("messages", []):
            if message.get("role") == "assistant":
                for call in message.get("tool_calls") or []:
                    descriptor = descriptors.get(call.get("function"))
                    if descriptor is None:
                        continue
                    decision = evaluate_atom_envelope(
                        user_task,
                        {**descriptor, "side_effectful": True},
                        call.get("args") or {},
                        evidence,
                    )
                    totals["effectful_calls"] += 1
                    totals[f"decision_{decision['decision'].lower()}"] += 1
                    case_denied = case_denied or decision["decision"] == "DENY"
            elif message.get("role") == "tool":
                segments = extract_agentlab_untrusted_control_segments(message.get("content"))
                totals["tool_outputs"] += 1
                totals["normalized_segments"] += len(segments)
                if segments:
                    totals["positive_tool_outputs"] += 1
                    case_positive_evidence = True
                    evidence.append({"untrusted_control_segments": segments})
        attack = payload.get("security") is True
        totals["cases"] += 1
        totals["cases_with_normalized_evidence"] += case_positive_evidence
        totals["cases_with_retrospective_deny"] += case_denied
        totals["attack_success_cases"] += attack
        totals["attack_success_cases_with_retrospective_deny"] += attack and case_denied
        suite_counts["cases"] += 1
        suite_counts["cases_with_normalized_evidence"] += case_positive_evidence
        suite_counts["attack_success_cases"] += attack
        suite_counts["attack_success_cases_with_retrospective_deny"] += attack and case_denied
    return {
        **dict(totals),
        "by_suite": {suite: dict(values) for suite, values in sorted(by_suite.items())},
    }


def deepseek_pilot() -> list[dict[str, Any]]:
    rows = []
    for case_dir in sorted(PILOT.iterdir() if PILOT.is_dir() else []):
        result_paths = [path for path in case_dir.rglob("injection_task_*.json") if path.is_file()]
        audit_path = case_dir / "e77_runtime_audit.jsonl"
        if len(result_paths) != 1 or not audit_path.is_file():
            continue
        payload = json.loads(result_paths[0].read_text(encoding="utf-8"))
        audit = read_jsonl(audit_path)
        evidence = [
            int(row.get("untrusted_control_segment_count", 0))
            for row in audit
            if row.get("event") == "authorized_read_evidence"
        ]
        checks = [row for row in audit if row.get("event") == "precommit_check"]
        rows.append(
            {
                "case": f"{payload['suite_name']}:{payload['user_task_id']}:{payload['injection_task_id']}",
                "utility": payload.get("utility"),
                "attack_success": payload.get("security"),
                "error": payload.get("error"),
                "precommit_checks": len(checks),
                "deny_checks": sum(row.get("decision") == "DENY" for row in checks),
                "positive_evidence_events": sum(value > 0 for value in evidence),
                "normalized_control_segments": sum(evidence),
                "runtime_versions": sorted(
                    {str(row["runtime_version"]) for row in audit if row.get("runtime_version")}
                ),
            }
        )
    return rows


def main() -> int:
    retrospective = retrospective_audit()
    pilot = deepseek_pilot()
    queue = json.loads(QUEUE_STATUS.read_text(encoding="utf-8")) if QUEUE_STATUS.is_file() else None
    report = {
        "experiment": "E79 AgentLAB provenance-normalization repair",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "development_pilot_passed_full_qwen_rerun_queued",
        "root_cause": (
            "AgentLAB saved attacks use explicit ChatML role blocks, while the frozen C1f adapter only "
            "recognized AgentDojo INFORMATION blocks; untrusted control therefore failed to reach pre-commit checks."
        ),
        "repair": (
            "A format-only adapter maps explicit ChatML saved-message blocks to C1f's existing untrusted-control "
            "interface without reading labels, attack goals, expected decisions, or validator outcomes."
        ),
        "retrospective_qwen32_diagnostic": retrospective,
        "deepseek_development_pilot": {
            "n": len(pilot),
            "attack_successes": sum(row["attack_success"] is True for row in pilot),
            "utility_successes": sum(row["utility"] is True for row in pilot),
            "rows": pilot,
        },
        "full_qwen32_queue": queue,
        "claim_boundary": (
            "The retrospective audit diagnoses whether already-recorded calls would meet the normalized policy; "
            "it does not model recovery after denial. The three-case DeepSeek run is development-only and did not "
            "exercise an effectful denial. Security and utility claims require the queued 303-case Qwen rerun and "
            "strict finalization."
        ),
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(
        "# E79 AgentLAB Provenance-Normalization Pilot\n\n"
        f"Status: `{report['status']}`.\n\n"
        "## Root cause and repair\n\n"
        f"{report['root_cause']} {report['repair']}\n\n"
        "## Retrospective Qwen3-32B diagnostic\n\n"
        f"- Saved cases: {retrospective['cases']}\n"
        f"- Cases with normalized evidence: {retrospective['cases_with_normalized_evidence']}\n"
        f"- Recovered control segments: {retrospective['normalized_segments']}\n"
        f"- Original attack successes: {retrospective['attack_success_cases']}\n"
        "- Original attack successes containing a retrospectively denied effectful call: "
        f"{retrospective['attack_success_cases_with_retrospective_deny']}\n\n"
        "## DeepSeek development pilot\n\n"
        f"Three fixed cases produced {report['deepseek_development_pilot']['attack_successes']} attack successes "
        f"and {report['deepseek_development_pilot']['utility_successes']} utility successes.\n\n"
        "## Claim boundary\n\n"
        f"{report['claim_boundary']}\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
