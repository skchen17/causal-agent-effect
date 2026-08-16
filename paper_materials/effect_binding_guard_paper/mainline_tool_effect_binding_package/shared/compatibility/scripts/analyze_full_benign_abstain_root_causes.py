#!/usr/bin/env python3
"""Attribute full-benign guard interventions without exposing task text."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
RUN_ROOT = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/runs/"
    "runtime-mechanism-ablation/e84-qwen32-pilot-full-denominator-v3-full"
)
LOG_ROOT = RUN_ROOT / "agentdojo_logs/e84_reviewed_authority"
AUDIT_PATH = RUN_ROOT / "e84_runtime_audit.jsonl"
FROZEN_ROWS = (
    ROOT
    / "experiments/unified-agent-security-baselines/results/"
    "strong-model-baseline-comparison/qwen32-frozen-case-rows.jsonl"
)
OUT_DIR = (
    ROOT
    / "experiments/human-authority-and-causal-validation/results/"
    "full-benign-runtime-guard-validation"
)

BLOCKING_CATEGORIES = (
    "authority_manifest_unavailable",
    "resolver_value_unproven",
    "security_field_unbound",
    "tool_outside_bounded_plan",
    "outside_exact_authority",
    "other_guard_intervention",
)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def message_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(item.get("content", item.get("text", "")))
            if isinstance(item, dict)
            else str(item)
            for item in content
        )
    return str(content)


def task_hash(payload: dict[str, Any]) -> str:
    user_messages = [
        message
        for message in payload.get("messages", [])
        if message.get("role") == "user"
    ]
    if not user_messages:
        raise ValueError("trajectory contains no user message")
    query = message_text(user_messages[0].get("content"))
    return hashlib.sha256(query.encode()).hexdigest()


def category(row: dict[str, Any]) -> str:
    decision = row.get("decision")
    reasons = [str(reason) for reason in row.get("reasons", [])]
    if decision == "ALLOW":
        return "allow"
    if decision == "DENY" and any(
        "outside_exact_authority" in reason for reason in reasons
    ):
        return "outside_exact_authority"
    if row.get("manifest_available") is False:
        return "authority_manifest_unavailable"
    if any("resolver_value_unproven" in reason for reason in reasons):
        return "resolver_value_unproven"
    if any("security_field_unbound" in reason for reason in reasons):
        return "security_field_unbound"
    if any("tool_not_in_bounded_plan" in reason for reason in reasons):
        return "tool_outside_bounded_plan"
    return "other_guard_intervention"


def reason_families(row: dict[str, Any]) -> set[str]:
    reasons = [str(reason) for reason in row.get("reasons", [])]
    families: set[str] = set()
    if (
        row.get("decision") == "ABSTAIN"
        and row.get("manifest_available") is False
    ):
        families.add("authority_manifest_unavailable")
    if any("resolver_value_unproven" in reason for reason in reasons):
        families.add("resolver_value_unproven")
    if any("security_field_unbound" in reason for reason in reasons):
        families.add("security_field_unbound")
    if any("tool_not_in_bounded_plan" in reason for reason in reasons):
        families.add("tool_outside_bounded_plan")
    if any("outside_exact_authority" in reason for reason in reasons):
        families.add("outside_exact_authority")
    return families


def load_trajectories() -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for path in LOG_ROOT.rglob("none/none.json"):
        payload = read_json(path)
        if not str(payload.get("user_task_id", "")).startswith("user_task_"):
            continue
        query_hash = task_hash(payload)
        if query_hash in indexed:
            raise ValueError(f"duplicate trajectory query hash: {query_hash}")
        indexed[query_hash] = {
            "suite": payload["suite_name"],
            "user_task_id": payload["user_task_id"],
            "utility": payload["utility"],
            "error": payload.get("error"),
            "source_file": str(path.relative_to(ROOT)),
        }
    if len(indexed) != 97:
        raise ValueError(f"expected 97 benign trajectories, got {len(indexed)}")
    return indexed


def load_no_guard_utility() -> dict[tuple[str, str], bool]:
    rows = read_jsonl(FROZEN_ROWS)
    out = {
        (row["suite"], row["user_task_id"]): bool(row["utility"])
        for row in rows
        if row["method_id"] == "agentdojo_live_local_no_guard"
        and row["mode"] == "benign"
    }
    if len(out) != 97:
        raise ValueError(f"expected 97 no-guard benign rows, got {len(out)}")
    return out


def summarize() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    trajectories = load_trajectories()
    no_guard = load_no_guard_utility()
    audit = [
        row
        for row in read_jsonl(AUDIT_PATH)
        if row.get("event") == "precommit_check"
    ]
    if len(audit) != 426:
        raise ValueError(f"expected 426 precommit checks, got {len(audit)}")
    unknown_hashes = {row["query_hash"] for row in audit} - set(trajectories)
    if unknown_hashes:
        raise ValueError(f"audit has {len(unknown_hashes)} unknown task hashes")

    by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in audit:
        by_hash[row["query_hash"]].append(row)

    task_rows: list[dict[str, Any]] = []
    for query_hash, trajectory in trajectories.items():
        checks = by_hash.get(query_hash, [])
        categories = Counter(category(row) for row in checks)
        blockers = [
            name for name in BLOCKING_CATEGORIES if categories.get(name, 0)
        ]
        primary = next(iter(blockers), "no_guard_intervention")
        key = (trajectory["suite"], trajectory["user_task_id"])
        task_rows.append(
            {
                "suite": trajectory["suite"],
                "user_task_id": trajectory["user_task_id"],
                "guard_utility": bool(trajectory["utility"]),
                "no_guard_utility": no_guard[key],
                "guard_error": trajectory["error"] is not None,
                "precommit_checks": len(checks),
                "allow_checks": categories["allow"],
                "abstain_checks": sum(
                    1 for row in checks if row.get("decision") == "ABSTAIN"
                ),
                "deny_checks": sum(
                    1 for row in checks if row.get("decision") == "DENY"
                ),
                "manifest_available_for_all_checks": all(
                    bool(row.get("manifest_available")) for row in checks
                )
                if checks
                else False,
                "blocking_categories": blockers,
                "primary_blocking_category": primary,
                "source_file": trajectory["source_file"],
            }
        )
    task_rows.sort(key=lambda row: (row["suite"], row["user_task_id"]))

    check_categories = Counter(category(row) for row in audit)
    reason_family_incidence = Counter(
        family for row in audit for family in reason_families(row)
    )
    decision_counts = Counter(str(row["decision"]) for row in audit)
    tools_by_category: dict[str, Counter[str]] = defaultdict(Counter)
    for row in audit:
        tools_by_category[category(row)][str(row["tool_name"])] += 1

    paired = Counter()
    for row in task_rows:
        key = (
            "guard_success" if row["guard_utility"] else "guard_failure",
            "no_guard_success" if row["no_guard_utility"] else "no_guard_failure",
        )
        paired["__".join(key)] += 1

    category_task_stats = {}
    for name in BLOCKING_CATEGORIES:
        exposed = [
            row for row in task_rows if name in row["blocking_categories"]
        ]
        category_task_stats[name] = {
            "tasks_exposed": len(exposed),
            "guard_utility_successes": sum(
                row["guard_utility"] for row in exposed
            ),
            "no_guard_only_successes": sum(
                row["no_guard_utility"] and not row["guard_utility"]
                for row in exposed
            ),
        }

    failed = [row for row in task_rows if not row["guard_utility"]]
    no_guard_only = [
        row
        for row in task_rows
        if row["no_guard_utility"] and not row["guard_utility"]
    ]
    report = {
        "experiment": "full_benign_abstain_root_cause_audit",
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agentdojo_version": "v1.1.2",
        "n_tasks": len(task_rows),
        "precommit_checks": len(audit),
        "decision_counts": dict(sorted(decision_counts.items())),
        "check_category_counts": dict(sorted(check_categories.items())),
        "reason_family_check_incidence": dict(
            sorted(reason_family_incidence.items())
        ),
        "task_utility": {
            "guard_successes": sum(row["guard_utility"] for row in task_rows),
            "no_guard_successes": sum(
                row["no_guard_utility"] for row in task_rows
            ),
            "paired_contingency": dict(sorted(paired.items())),
        },
        "failed_task_primary_blocker_counts": dict(
            sorted(Counter(row["primary_blocking_category"] for row in failed).items())
        ),
        "no_guard_only_primary_blocker_counts": dict(
            sorted(
                Counter(
                    row["primary_blocking_category"] for row in no_guard_only
                ).items()
            )
        ),
        "category_task_stats": category_task_stats,
        "tools_by_check_category": {
            name: dict(counter.most_common())
            for name, counter in sorted(tools_by_category.items())
        },
        "mechanism_interpretation": {
            "authority_manifest_unavailable": (
                "O2/interface-coverage limitation: no task-specific executable "
                "authority was available, so effectful calls failed closed."
            ),
            "resolver_value_unproven": (
                "Trusted-evidence interface/compiler limitation: a concrete "
                "runtime value could not be justified by an approved resolver."
            ),
            "security_field_unbound": (
                "Contract/interface completeness limitation: a security-relevant "
                "field lacked an executable binding."
            ),
            "tool_outside_bounded_plan": (
                "Planner-to-authority mismatch: the proposed tool was absent from "
                "the bounded task plan."
            ),
            "outside_exact_authority": (
                "Exact-authority mismatch requiring call-level adjudication; the "
                "audit alone does not establish whether the model call or the "
                "authority bound was wrong."
            ),
            "no_guard_intervention": (
                "The guard recorded no blocking decision; task failure is not "
                "mechanically attributable to pre-commit denial."
            ),
        },
        "privacy_gate": {
            "task_text_emitted": False,
            "tool_arguments_emitted": False,
            "raw_model_output_emitted": False,
            "query_hash_emitted": False,
        },
        "claim_boundary": (
            "This is a mechanical correlation audit over paired task keys, not a "
            "causal decomposition of utility. No-guard and guarded trajectories "
            "were separate deterministic-temperature runs, and a blocking event "
            "need not be the sole reason a task failed. Task text, arguments, and "
            "model output are excluded from the artifact."
        ),
    }
    return report, task_rows


def main() -> int:
    report, task_rows = summarize()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUT_DIR / "full-benign-abstain-root-cause.json", report)
    with (OUT_DIR / "full-benign-abstain-task-rows.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        fields = [
            "suite",
            "user_task_id",
            "guard_utility",
            "no_guard_utility",
            "guard_error",
            "precommit_checks",
            "allow_checks",
            "abstain_checks",
            "deny_checks",
            "manifest_available_for_all_checks",
            "blocking_categories",
            "primary_blocking_category",
            "source_file",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in task_rows:
            writer.writerow(
                {
                    **row,
                    "blocking_categories": ";".join(row["blocking_categories"]),
                }
            )

    counts = report["check_category_counts"]
    families = report["reason_family_check_incidence"]
    utility = report["task_utility"]
    lines = [
        "# Full-Benign Abstain Root-Cause Audit",
        "",
        f"- Tasks: `{report['n_tasks']}`",
        f"- Pre-commit decisions: `{report['decision_counts']}`",
        (
            "- Guard/no-guard utility: "
            f"`{utility['guard_successes']}/97` / "
            f"`{utility['no_guard_successes']}/97`"
        ),
        (
            "- Missing-authority abstains: "
            f"`{counts.get('authority_manifest_unavailable', 0)}`"
        ),
        (
            "- Unproven-resolver abstains: "
            f"`{counts.get('resolver_value_unproven', 0)}`"
        ),
        (
            "- Unbound-field abstains: "
            f"`{families.get('security_field_unbound', 0)}`"
        ),
        (
            "- Outside-plan abstains: "
            f"`{counts.get('tool_outside_bounded_plan', 0)}`"
        ),
        "",
        "## Failed-Task Correlates",
        "",
    ]
    for name, count in report["failed_task_primary_blocker_counts"].items():
        lines.append(f"- `{name}`: `{count}`")
    lines.extend(["", "## Claim Boundary", "", report["claim_boundary"], ""])
    (OUT_DIR / "full-benign-abstain-root-cause.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
