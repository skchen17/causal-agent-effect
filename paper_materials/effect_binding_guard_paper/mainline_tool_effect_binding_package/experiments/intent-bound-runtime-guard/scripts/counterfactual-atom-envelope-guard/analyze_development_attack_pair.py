#!/usr/bin/env python3
"""Compare the frozen 16-case DeepSeek no-guard and C1 development runs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / "paper").is_dir() and (parent / "experiments").is_dir()
)
MANIFEST = (
    ROOT / "experiments/intent-bound-runtime-guard/evaluation/"
    "effect-difference-runtime-guard/benign97_threeway_attack_smoke_manifest_2026-08-08.json"
)
NO_GUARD = (
    ROOT / "experiments/intent-bound-runtime-guard/runs/counterfactual-atom-envelope-guard/"
    "deepseek-development-no-guard-20260808"
)
C1 = (
    ROOT / "experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/"
    "recovery-normalization-qwen32-pilot-36-allow-with-trail-c1-deepseek-attack16-dev"
)
OUT = ROOT / "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard"


def load_log(condition: str, suite: str, user: str, injection: str) -> dict:
    if condition == "no_guard":
        path = (
            NO_GUARD / f"{suite}-{injection}/agentdojo_logs/local" /
            suite / user / "important_instructions" / f"{injection}.json"
        )
    else:
        path = (
            C1 / "agentdojo_logs/local-ours_e77_effect_diff_runtime" /
            suite / user / "important_instructions" / f"{injection}.json"
        )
    if not path.exists():
        raise FileNotFoundError(path)
    row = json.loads(path.read_text(encoding="utf-8"))
    return {
        "path": str(path.relative_to(ROOT)),
        "utility": bool(row.get("utility")),
        "attack_success": bool(row.get("security")),
        "error": row.get("error"),
    }


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = []
    for case in manifest["cases"]:
        key = (case["suite"], case["user_task_id"], case["injection_task_id"])
        rows.append(
            {
                "case_key": case["case_key"],
                "no_guard": load_log("no_guard", *key),
                "c1": load_log("c1", *key),
            }
        )
    metrics = {}
    for condition in ("no_guard", "c1"):
        metrics[condition] = {
            "n": len(rows),
            "attack_successes": sum(row[condition]["attack_success"] for row in rows),
            "utility_successes": sum(row[condition]["utility"] for row in rows),
            "errors": sum(row[condition]["error"] is not None for row in rows),
        }
    metrics["paired"] = {
        "attacks_blocked_by_c1": sum(
            row["no_guard"]["attack_success"] and not row["c1"]["attack_success"]
            for row in rows
        ),
        "attacks_introduced_by_c1": sum(
            not row["no_guard"]["attack_success"] and row["c1"]["attack_success"]
            for row in rows
        ),
        "utility_gained_by_c1": sum(
            not row["no_guard"]["utility"] and row["c1"]["utility"] for row in rows
        ),
        "utility_lost_by_c1": sum(
            row["no_guard"]["utility"] and not row["c1"]["utility"] for row in rows
        ),
    }
    audit = [
        json.loads(line)
        for line in (C1 / "runtime_audit.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    precommit = [row for row in audit if row.get("event") == "precommit_check"]
    metrics["c1_audit"] = {
        "precommit_checks": len(precommit),
        "allow": sum(row.get("decision") == "ALLOW" for row in precommit),
        "deny": sum(row.get("decision") == "DENY" for row in precommit),
        "abstain": sum(row.get("decision") == "ABSTAIN" for row in precommit),
        "executed_without_allow": sum(
            row.get("execution_attempted") and row.get("decision") != "ALLOW"
            for row in precommit
        ),
        "runtime_llm_calls": sum(bool(row.get("runtime_called_llm")) for row in precommit),
    }
    report = {
        "experiment": "DeepSeek attack16 no-guard vs C1 development pair",
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "metrics": metrics,
        "rows": rows,
        "claim_boundary": (
            "Frozen development smoke set; not an overall AgentDojo ASR estimate and not "
            "used for final baseline ranking."
        ),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "deepseek_attack16_development_pair.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    md = f"""# DeepSeek Attack-16 Development Pair

| Condition | Attack success | Attack-task utility | Errors |
|---|---:|---:|---:|
| No guard | {metrics['no_guard']['attack_successes']}/16 | {metrics['no_guard']['utility_successes']}/16 | {metrics['no_guard']['errors']} |
| C1 atom envelope | {metrics['c1']['attack_successes']}/16 | {metrics['c1']['utility_successes']}/16 | {metrics['c1']['errors']} |

Paired attacks blocked by C1: `{metrics['paired']['attacks_blocked_by_c1']}`;
introduced: `{metrics['paired']['attacks_introduced_by_c1']}`. Executed without
an `ALLOW` audit decision: `{metrics['c1_audit']['executed_without_allow']}`.

This is a frozen development smoke set, not a full AgentDojo ASR estimate.
"""
    (OUT / "deepseek_attack16_development_pair.md").write_text(md, encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
