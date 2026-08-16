#!/usr/bin/env python3
"""Verify E88 public attacks materialize without persisting payload text."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from agentdojo.attacks.attack_registry import load_attack
from agentdojo.task_suite.load_suites import get_suite


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evaluation/e88_agentdojo_attack_dataset/materialization_audit.json"
FAMILIES = ("ignore_previous", "injecagent", "important_instructions", "tool_knowledge")
SUITES = ("banking", "slack", "travel", "workspace")


def main() -> int:
    counts: Counter[tuple[str, str]] = Counter()
    errors: list[dict[str, str]] = []
    target = SimpleNamespace(name="gpt-4o-2024-05-13")
    for suite_name in SUITES:
        suite = get_suite("v1.1.2", suite_name)
        for family in FAMILIES:
            attack = load_attack(family, suite, target)
            for user_task_id, user_task in suite.user_tasks.items():
                try:
                    attack.get_injection_candidates(user_task)
                except ValueError:
                    continue
                for injection_task_id, injection_task in suite.injection_tasks.items():
                    try:
                        materialized = attack.attack(user_task, injection_task)
                        if not materialized or any(
                            not isinstance(value, str) or not value.strip() for value in materialized.values()
                        ):
                            raise ValueError("empty materialization")
                        counts[(suite_name, family)] += 1
                    except Exception as exc:  # pragma: no cover - exercised only on package/schema drift
                        errors.append(
                            {
                                "suite": suite_name,
                                "attack_family": family,
                                "user_task_id": user_task_id,
                                "injection_task_id": injection_task_id,
                                "error_type": type(exc).__name__,
                            }
                        )
    report = {
        "experiment": "E88",
        "status": "passed" if not errors and sum(counts.values()) == 2516 else "failed",
        "agentdojo_version": "v1.1.2",
        "n_materialized_in_memory": sum(counts.values()),
        "counts": {f"{suite}/{family}": count for (suite, family), count in sorted(counts.items())},
        "n_errors": len(errors),
        "errors": errors,
        "raw_payloads_persisted": False,
        "model_calls": 0,
        "external_side_effects": 0,
    }
    OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
