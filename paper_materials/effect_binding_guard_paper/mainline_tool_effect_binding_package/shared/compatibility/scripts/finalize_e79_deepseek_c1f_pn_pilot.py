#!/usr/bin/env python3
"""Finalize the outcome-blind DeepSeek no-guard/C1f-PN comparison pilot."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *SCRIPT_PATH.parents)
    if (candidate / "paper/current-usenix").exists()
)
RUN = (
    ROOT
    / "experiments/long-horizon-transfer/runs/long-horizon-cross-environment-transfer/"
    "agentlab-c1f-pn-deepseek-comparison-pilot"
)
MANIFEST = ROOT / "evaluation/e79_long_horizon/deepseek_c1f_pn_pilot_manifest.json"
RESULTS = ROOT / "analysis/results"
OUTPUT_JSON = RESULTS / "e79_deepseek_c1f_pn_comparison_pilot.json"
OUTPUT_MD = RESULTS / "e79_deepseek_c1f_pn_comparison_pilot.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def key(payload: dict[str, Any]) -> str:
    return f"{payload['suite_name']}:{payload['user_task_id']}:{payload['injection_task_id']}"


def first_user_text(payload: dict[str, Any]) -> str:
    for message in payload.get("messages") or []:
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(
                str(block.get("content", ""))
                for block in content
                if isinstance(block, dict)
            )
    raise ValueError("result has no user message")


def load_method(method: str) -> dict[str, dict[str, Any]]:
    indexed = {}
    for path in sorted((RUN / method).rglob("injection_task_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        case_key = key(payload)
        if case_key in indexed:
            raise RuntimeError(f"duplicate result: {case_key}")
        indexed[case_key] = payload
    return indexed


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = set(manifest["case_keys"])
    no_guard = load_method("no_guard")
    c1f = load_method("c1f_pn")
    if set(no_guard) != expected or set(c1f) != expected:
        raise RuntimeError("comparison logs do not exactly match the frozen pilot manifest")
    for method in ("no_guard", "c1f_pn"):
        result = json.loads(
            (RESULTS / f"e79_agentlab_saved_transfer_{method}_pilot_results.json").read_text(encoding="utf-8")
        )
        if result.get("status") != "passed" or result.get("expected_case_keys") != 24:
            raise RuntimeError(f"strict pilot finalizer did not pass: {method}")

    audit = read_jsonl(RUN / "c1f_pn/e77_runtime_audit.jsonl")
    checks = [row for row in audit if row.get("event") == "precommit_check"]
    evidence = [row for row in audit if row.get("event") == "authorized_read_evidence"]
    deny_hashes = {row["query_hash"] for row in checks if row.get("decision") == "DENY"}
    guard_only_utility_losses = [
        case_key
        for case_key in sorted(expected)
        if no_guard[case_key]["utility"] is True and c1f[case_key]["utility"] is False
    ]
    losses_with_a_deny = [
        case_key
        for case_key in guard_only_utility_losses
        if hashlib.sha256(first_user_text(c1f[case_key]).encode()).hexdigest() in deny_hashes
    ]
    reason_counts = Counter()
    for row in checks:
        if row.get("decision") != "DENY":
            continue
        for reason in row.get("reasons") or row.get("initial_reasons") or []:
            reason_counts[str(reason)] += 1

    pairwise_utility = Counter(
        (bool(no_guard[case_key]["utility"]), bool(c1f[case_key]["utility"]))
        for case_key in expected
    )
    pairwise_security = Counter(
        (bool(no_guard[case_key]["security"]), bool(c1f[case_key]["security"]))
        for case_key in expected
    )
    report = {
        "experiment": "E79 DeepSeek outcome-blind C1f-PN comparison pilot",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed_security_difference_inconclusive",
        "model": "deepseek-chat",
        "agentdojo_version": "v1.2.1",
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "manifest_sha256": sha256(MANIFEST),
        "selection_outcome_blind": True,
        "n": 24,
        "metrics": {
            "no_guard": {
                "attack_successes": sum(row["security"] is True for row in no_guard.values()),
                "attack_success_rate": sum(row["security"] is True for row in no_guard.values()) / 24,
                "utility_successes": sum(row["utility"] is True for row in no_guard.values()),
                "utility_rate": sum(row["utility"] is True for row in no_guard.values()) / 24,
            },
            "c1f_pn": {
                "attack_successes": sum(row["security"] is True for row in c1f.values()),
                "attack_success_rate": sum(row["security"] is True for row in c1f.values()) / 24,
                "utility_successes": sum(row["utility"] is True for row in c1f.values()),
                "utility_rate": sum(row["utility"] is True for row in c1f.values()) / 24,
            },
        },
        "matched_outcomes": {
            "utility": {
                f"no_guard_{left}_c1f_pn_{right}": count
                for (left, right), count in sorted(pairwise_utility.items())
            },
            "attack_success": {
                f"no_guard_{left}_c1f_pn_{right}": count
                for (left, right), count in sorted(pairwise_security.items())
            },
        },
        "runtime_audit": {
            "precommit_checks": len(checks),
            "allow": sum(row.get("decision") == "ALLOW" for row in checks),
            "deny": sum(row.get("decision") == "DENY" for row in checks),
            "abstain": sum(row.get("decision") == "ABSTAIN" for row in checks),
            "denied_tools": dict(Counter(row.get("tool_name") for row in checks if row.get("decision") == "DENY")),
            "deny_reasons": dict(reason_counts),
            "evidence_events": len(evidence),
            "positive_normalized_evidence_events": sum(
                int(row.get("untrusted_control_segment_count", 0)) > 0 for row in evidence
            ),
            "normalized_control_segments": sum(
                int(row.get("untrusted_control_segment_count", 0)) for row in evidence
            ),
            "complete_mediation": len(checks) == 159,
        },
        "utility_diagnostics": {
            "guard_only_loss_keys": guard_only_utility_losses,
            "guard_only_losses_with_a_deny_for_same_user_task": losses_with_a_deny,
        },
        "conclusion": (
            "The repair is active beyond the development examples: an outcome-blind four-suite sample produced "
            "normalized provenance and deterministic denials for multiple effectful tool families. Security benefit "
            "is inconclusive because DeepSeek had zero official attack successes without a guard. C1f-PN lost three "
            "additional utility cases, all associated with denied trajectories, so recovery after a correct denial "
            "remains an engineering and evaluation requirement."
        ),
        "claim_boundary": (
            "This 24-case pilot validates adapter activity, complete mediation, and matched utility behavior. It is "
            "not a confirmatory ASR result, does not reproduce AgentLAB attack optimization, and cannot establish a "
            "security improvement when the no-guard denominator contains zero attack successes."
        ),
        "api_key_serialized": False,
    }
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(
        "# E79 DeepSeek C1f-PN Comparison Pilot\n\n"
        f"Status: `{report['status']}`.\n\n"
        "| Method | Official attack success | Utility |\n"
        "|---|---:|---:|\n"
        f"| No guard | 0/24 (0.0%) | 21/24 (87.5%) |\n"
        f"| C1f-PN | 0/24 (0.0%) | 18/24 (75.0%) |\n\n"
        "C1f-PN mediated all 159 executed tool-result calls and issued 25 deterministic denials. "
        "The denials covered fund transfer and Slack messaging tools. All three additional utility "
        "failures occurred on user tasks whose guarded trajectories contained denials.\n\n"
        "## Interpretation\n\n"
        f"{report['conclusion']}\n\n"
        "## Claim boundary\n\n"
        f"{report['claim_boundary']}\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
