#!/usr/bin/env python3
"""Decompose the E78 headline benign-utility gap by observed runtime pathway."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any


NO_GUARD = "agentdojo_live_local_no_guard"
OURS = "agentdojo_live_ours_e77_effect_diff_runtime"
FEEDBACK_PREFIX = "ATOM_RUNTIME_NEEDS_REPLAN:"
REASON_CODES = (
    "resolver_fill_requires_replan",
    "outside_exact_plan",
    "forbidden_field_used",
    "unbound_field",
    "tool_not_in_initial_permission_plan",
    "task_permission_plan_parse_failed",
    "required_field_missing",
    "dynamic_default_unresolved",
    "default_semantics_unknown",
)

EXPECTED = {
    "benign_cases": 97,
    "no_guard_successes": 63,
    "ours_successes": 33,
    "transitions": {
        "0->0": 27,
        "0->1": 7,
        "1->0": 37,
        "1->1": 26,
    },
    "feedback_cases": 47,
    "feedback_no_guard_successes": 35,
    "feedback_ours_successes": 4,
    "no_feedback_cases": 50,
    "no_feedback_no_guard_successes": 28,
    "no_feedback_ours_successes": 29,
    "losses_with_feedback": 32,
    "losses_without_feedback": 5,
}


def find_root(start: Path) -> Path:
    for candidate in (start.resolve(), *start.resolve().parents):
        if all((candidate / name).is_dir() for name in ("experiments", "paper", "shared")):
            return candidate
    raise RuntimeError("could not locate consolidated package root")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected JSON object")
        rows.append(value)
    return rows


def content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(item.get("content", item.get("text", "")))
            if isinstance(item, Mapping)
            else str(item)
            for item in content
        )
    if isinstance(content, Mapping):
        return str(content.get("content", content.get("text", "")))
    return str(content or "")


def user_task_text(payload: Mapping[str, Any]) -> str:
    for message in payload.get("messages", []):
        if message.get("role") == "user":
            return content_text(message.get("content")).strip()
    raise ValueError("log contains no user task")


def call_signature(tool_name: str, args: Mapping[str, Any]) -> str:
    rendered = json.dumps(
        {"tool_name": tool_name, "args": dict(args)},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def normalized_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).strip()).casefold()


def literal_grounded(value: Any, source: str) -> bool:
    """Conservative literal probe; it does not decide authorization."""
    if isinstance(value, (list, tuple)):
        return bool(value) and all(literal_grounded(item, source) for item in value)
    if isinstance(value, bool):
        return bool(
            re.search(
                rf"(?<!\w){str(value).casefold()}(?!\w)",
                source.casefold(),
            )
        )
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        canonical = str(float(value)).rstrip("0").rstrip(".")
        candidates = re.findall(
            r"(?<![\w.])[+-]?\d+(?:\.\d+)?(?![\w.])",
            source,
        )
        return any(
            str(float(candidate)).rstrip("0").rstrip(".") == canonical
            for candidate in candidates
        )
    candidate = normalized_text(value)
    if not candidate:
        return False
    haystack = normalized_text(source)
    pattern = re.escape(candidate).replace(r"\ ", r"\s+")
    boundary = r"[\w@.+-]" if "@" in candidate or "://" in candidate else r"\w"
    return bool(re.search(rf"(?<!{boundary}){pattern}(?!{boundary})", haystack))


def reason_codes(value: Any) -> list[str]:
    rendered = value if isinstance(value, str) else json.dumps(value, default=str)
    return [code for code in REASON_CODES if code in rendered]


def parse_feedback(message: Mapping[str, Any]) -> dict[str, Any] | None:
    if message.get("role") != "tool":
        return None
    rendered = content_text(message.get("content")).strip()
    if not rendered.startswith(FEEDBACK_PREFIX):
        return None
    tool_call = message.get("tool_call")
    if not isinstance(tool_call, Mapping):
        raise ValueError("runtime feedback lacks a structured tool_call")
    tool_name = str(tool_call.get("function") or "")
    args = tool_call.get("args") or {}
    if not tool_name or not isinstance(args, Mapping):
        raise ValueError("runtime feedback has a malformed tool_call")
    state_match = re.search(r"Recovery state: ([^.]+)", rendered)
    return {
        "tool_name": tool_name,
        "args": dict(args),
        "call_signature": call_signature(tool_name, args),
        "recovery_state": state_match.group(1) if state_match else "unknown",
        "reason_codes": reason_codes(rendered),
    }


def relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_pairs(root: Path) -> dict[tuple[str, str], dict[str, dict[str, Any]]]:
    path = root / "shared/compatibility/analysis/results/e78_capacity_matched_merged_rows.jsonl"
    pairs: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in read_jsonl(path):
        if row.get("mode") != "benign" or row.get("method_id") not in {NO_GUARD, OURS}:
            continue
        key = (str(row["suite"]), str(row["user_task_id"]))
        method = str(row["method_id"])
        if method in pairs[key]:
            raise ValueError(f"duplicate E78 benign row: {key} / {method}")
        pairs[key][method] = row
    if len(pairs) != EXPECTED["benign_cases"]:
        raise ValueError(f"expected 97 paired benign keys, observed {len(pairs)}")
    if any(set(methods) != {NO_GUARD, OURS} for methods in pairs.values()):
        raise ValueError("an E78 benign key lacks one of the paired methods")
    return dict(pairs)


def log_path(
    root: Path,
    suite: str,
    user_task_id: str,
    method: str,
    row: Mapping[str, Any],
) -> Path:
    source_file = str(row.get("source_file") or "")
    if method == NO_GUARD and source_file.startswith("experiments/"):
        path = root / source_file
    elif method == NO_GUARD:
        path = (
            root
            / "shared/compatibility/runs/e78_qwen32_strong_baselines/"
            "agentdojo_logs/no_guard/local"
            / suite
            / user_task_id
            / "none/none.json"
        )
    else:
        path = (
            root
            / "experiments/intent-bound-runtime-guard/runs/"
            "effect-difference-runtime-guard/"
            "recovery-normalization-qwen32-full-context-repaired/"
            "agentdojo_logs/local-ours_e77_effect_diff_runtime"
            / suite
            / user_task_id
            / "none/none.json"
        )
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def precommit_index(root: Path) -> dict[tuple[str, str], list[dict[str, Any]]]:
    path = (
        root
        / "experiments/intent-bound-runtime-guard/runs/"
        "effect-difference-runtime-guard/"
        "recovery-normalization-qwen32-full-context-repaired/runtime_audit.jsonl"
    )
    index: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(path):
        if row.get("event") != "precommit_check":
            continue
        key = (str(row.get("query_hash")), str(row.get("call_signature")))
        index[key].append(row)
    return dict(index)


def match_precommit(
    index: Mapping[tuple[str, str], list[dict[str, Any]]],
    query_hash: str,
    feedback: Mapping[str, Any],
) -> dict[str, Any]:
    candidates = list(index.get((query_hash, str(feedback["call_signature"])), []))
    candidates = [
        row
        for row in candidates
        if row.get("decision") == "NEEDS_REPLAN"
        and row.get("tool_name") == feedback["tool_name"]
    ]
    state_matches = [
        row
        for row in candidates
        if str(row.get("recovery_state")) == feedback["recovery_state"]
    ]
    if state_matches:
        candidates = state_matches
    code_matches = [
        row
        for row in candidates
        if set(feedback["reason_codes"]) <= set(reason_codes(row.get("reasons", [])))
    ]
    if code_matches:
        candidates = code_matches
    if not candidates:
        raise ValueError(
            "could not bind runtime feedback to a precommit audit record: "
            f"{feedback['tool_name']} / {feedback['call_signature']}"
        )
    fingerprints = {
        json.dumps(
            {
                "reasons": row.get("reasons"),
                "atom_checks": row.get("atom_checks"),
                "recovery_state": row.get("recovery_state"),
            },
            sort_keys=True,
        )
        for row in candidates
    }
    if len(fingerprints) != 1:
        raise ValueError(
            "ambiguous precommit audit binding: "
            f"{feedback['tool_name']} / {feedback['call_signature']}"
        )
    return candidates[0]


def inspect_ours_log(
    payload: Mapping[str, Any],
    index: Mapping[tuple[str, str], list[dict[str, Any]]],
) -> dict[str, Any]:
    task = user_task_text(payload)
    query_hash = hashlib.sha256(task.encode("utf-8")).hexdigest()
    prior_results: list[dict[str, str]] = []
    feedback_events: list[dict[str, Any]] = []
    for message in payload.get("messages", []):
        parsed = parse_feedback(message)
        if parsed is None:
            if message.get("role") == "tool":
                call = message.get("tool_call")
                if isinstance(call, Mapping) and call.get("function"):
                    prior_results.append(
                        {
                            "tool_name": str(call["function"]),
                            "content": content_text(message.get("content")),
                        }
                    )
            continue
        audit = match_precommit(index, query_hash, parsed)
        field_checks = []
        for check in audit.get("atom_checks", []):
            if not isinstance(check, Mapping):
                continue
            field = str(check.get("resource_type") or "")
            value = check.get("resource_id")
            task_grounded = literal_grounded(value, task)
            source_tools = sorted(
                {
                    item["tool_name"]
                    for item in prior_results
                    if literal_grounded(value, item["content"])
                }
            )
            if task_grounded and source_tools:
                grounding = "task_and_prior_tool_result_literal"
            elif task_grounded:
                grounding = "original_task_literal"
            elif source_tools:
                grounding = "prior_tool_result_literal"
            else:
                grounding = "not_literally_observed"
            field_checks.append(
                {
                    "field": field,
                    "check_result": str(check.get("check_result")),
                    "literal_grounding_probe": grounding,
                    "prior_source_tools": source_tools,
                }
            )
        feedback_events.append(
            {
                "tool_name": parsed["tool_name"],
                "call_signature": parsed["call_signature"],
                "recovery_state": parsed["recovery_state"],
                "reason_codes": parsed["reason_codes"],
                "field_checks": field_checks,
            }
        )
    return {
        "feedback_event_count": len(feedback_events),
        "feedback_events": feedback_events,
        "feedback_reason_codes": sorted(
            {
                code
                for event in feedback_events
                for code in event["reason_codes"]
            }
        ),
        "recovery_states": [
            event["recovery_state"] for event in feedback_events
        ],
    }


def summarize_stratum(cases: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cases": len(cases),
        "no_guard_successes": sum(case["no_guard_utility"] for case in cases),
        "ours_successes": sum(case["ours_utility"] for case in cases),
        "net_ours_minus_no_guard": sum(
            int(case["ours_utility"]) - int(case["no_guard_utility"])
            for case in cases
        ),
        "transitions": dict(
            sorted(Counter(case["utility_transition"] for case in cases).items())
        ),
    }


def build_report(root: Path) -> dict[str, Any]:
    pairs = load_pairs(root)
    audit_index = precommit_index(root)
    cases = []
    for (suite, user_task_id), methods in sorted(pairs.items()):
        no_guard_path = log_path(
            root, suite, user_task_id, NO_GUARD, methods[NO_GUARD]
        )
        ours_path = log_path(root, suite, user_task_id, OURS, methods[OURS])
        no_guard_payload = read_json(no_guard_path)
        ours_payload = read_json(ours_path)
        no_guard_utility = bool(methods[NO_GUARD]["utility"])
        ours_utility = bool(methods[OURS]["utility"])
        if bool(no_guard_payload.get("utility")) != no_guard_utility:
            raise ValueError(f"no-guard log/merged-label mismatch: {suite}/{user_task_id}")
        if bool(ours_payload.get("utility")) != ours_utility:
            raise ValueError(f"ours log/merged-label mismatch: {suite}/{user_task_id}")
        inspected = inspect_ours_log(ours_payload, audit_index)
        transition = f"{int(no_guard_utility)}->{int(ours_utility)}"
        if transition == "1->0":
            pathway = (
                "runtime_feedback_observed_before_failure"
                if inspected["feedback_event_count"]
                else "no_runtime_feedback_model_or_scoring_variation"
            )
        elif transition == "0->1":
            pathway = (
                "runtime_feedback_observed_before_gain"
                if inspected["feedback_event_count"]
                else "no_runtime_feedback_model_or_scoring_variation"
            )
        else:
            pathway = (
                "runtime_feedback_observed_same_utility"
                if inspected["feedback_event_count"]
                else "no_runtime_feedback_same_utility"
            )
        cases.append(
            {
                "case_key": f"{suite}/{user_task_id}",
                "suite": suite,
                "user_task_id": user_task_id,
                "no_guard_utility": no_guard_utility,
                "ours_utility": ours_utility,
                "utility_transition": transition,
                "observed_pathway": pathway,
                "no_guard_source_file": relative(root, no_guard_path),
                "no_guard_source_sha256": sha256(no_guard_path),
                "ours_source_file": relative(root, ours_path),
                "ours_source_sha256": sha256(ours_path),
                **inspected,
            }
        )

    feedback = [case for case in cases if case["feedback_event_count"]]
    no_feedback = [case for case in cases if not case["feedback_event_count"]]
    losses = [case for case in cases if case["utility_transition"] == "1->0"]
    direct_losses = [case for case in losses if case["feedback_event_count"]]
    direct_loss_reason_case_counts = Counter(
        code
        for case in direct_losses
        for code in set(case["feedback_reason_codes"])
    )
    direct_loss_reason_event_counts = Counter(
        code
        for case in direct_losses
        for event in case["feedback_events"]
        for code in set(event["reason_codes"])
    )
    recovery_state_counts = Counter(
        event["recovery_state"]
        for case in direct_losses
        for event in case["feedback_events"]
    )
    field_checks = [
        check
        for case in direct_losses
        for event in case["feedback_events"]
        for check in event["field_checks"]
    ]
    resolver_checks = [
        check
        for check in field_checks
        if check["check_result"] == "resolver_fill_requires_replan"
    ]
    grounding_counts = Counter(
        check["literal_grounding_probe"] for check in resolver_checks
    )
    resolver_cases_with_prior_literal = sum(
        any(
            check["check_result"] == "resolver_fill_requires_replan"
            and check["literal_grounding_probe"]
            in {
                "prior_tool_result_literal",
                "task_and_prior_tool_result_literal",
            }
            for event in case["feedback_events"]
            for check in event["field_checks"]
        )
        for case in direct_losses
    )

    overall = summarize_stratum(cases)
    feedback_summary = summarize_stratum(feedback)
    no_feedback_summary = summarize_stratum(no_feedback)
    observed = {
        "benign_cases": overall["cases"],
        "no_guard_successes": overall["no_guard_successes"],
        "ours_successes": overall["ours_successes"],
        "transitions": overall["transitions"],
        "feedback_cases": feedback_summary["cases"],
        "feedback_no_guard_successes": feedback_summary["no_guard_successes"],
        "feedback_ours_successes": feedback_summary["ours_successes"],
        "no_feedback_cases": no_feedback_summary["cases"],
        "no_feedback_no_guard_successes": no_feedback_summary["no_guard_successes"],
        "no_feedback_ours_successes": no_feedback_summary["ours_successes"],
        "losses_with_feedback": len(direct_losses),
        "losses_without_feedback": len(losses) - len(direct_losses),
    }
    if observed != EXPECTED:
        raise ValueError(f"E78 frozen benign audit changed: {observed!r}")

    return {
        "status": "passed",
        "experiment": "E78-headline-benign-utility-pathway-audit",
        "agentdojo_version": "v1.1.2",
        "model_calls": 0,
        "tool_executions": 0,
        "contains_task_text_or_model_outputs": False,
        "overall": overall,
        "feedback_stratum": feedback_summary,
        "no_feedback_stratum": no_feedback_summary,
        "discordant": {
            "cases": len(losses)
            + sum(case["utility_transition"] == "0->1" for case in cases),
            "losses": len(losses),
            "gains": sum(case["utility_transition"] == "0->1" for case in cases),
            "losses_with_runtime_feedback": len(direct_losses),
            "losses_without_runtime_feedback": len(losses) - len(direct_losses),
        },
        "runtime_feedback_loss_anatomy": {
            "reason_case_counts_nonexclusive": dict(
                sorted(direct_loss_reason_case_counts.items())
            ),
            "reason_event_counts_nonexclusive": dict(
                sorted(direct_loss_reason_event_counts.items())
            ),
            "recovery_state_counts": dict(sorted(recovery_state_counts.items())),
            "plan_construction_cases": sum(
                bool(
                    set(case["feedback_reason_codes"])
                    & {
                        "task_permission_plan_parse_failed",
                        "tool_not_in_initial_permission_plan",
                    }
                )
                for case in direct_losses
            ),
            "binding_or_evidence_cases": sum(
                bool(
                    set(case["feedback_reason_codes"])
                    & {
                        "resolver_fill_requires_replan",
                        "outside_exact_plan",
                        "forbidden_field_used",
                        "unbound_field",
                    }
                )
                for case in direct_losses
            ),
            "overlap_plan_and_binding_cases": sum(
                bool(
                    set(case["feedback_reason_codes"])
                    & {
                        "task_permission_plan_parse_failed",
                        "tool_not_in_initial_permission_plan",
                    }
                )
                and bool(
                    set(case["feedback_reason_codes"])
                    & {
                        "resolver_fill_requires_replan",
                        "outside_exact_plan",
                        "forbidden_field_used",
                        "unbound_field",
                    }
                )
                for case in direct_losses
            ),
        },
        "literal_grounding_probe": {
            "scope": "resolver_fill checks on the 32 feedback-associated losses",
            "resolver_check_count": len(resolver_checks),
            "grounding_counts": dict(sorted(grounding_counts.items())),
            "loss_cases_with_a_resolver_value_seen_in_prior_tool_output": (
                resolver_cases_with_prior_literal
            ),
            "interpretation": (
                "A literal match shows that the concrete value appeared in the "
                "original task or an earlier benign tool result. It does not prove "
                "that the value was semantically related, trustworthy, or authorized."
            ),
        },
        "interpretation": {
            "headline_net_gap": overall["net_ours_minus_no_guard"],
            "net_gap_on_feedback_cases": feedback_summary[
                "net_ours_minus_no_guard"
            ],
            "net_gap_on_no_feedback_cases": no_feedback_summary[
                "net_ours_minus_no_guard"
            ],
            "loss_share_with_observed_runtime_feedback": (
                len(direct_losses) / len(losses)
            ),
            "conclusion": (
                "The headline utility gap is concentrated in trajectories that "
                "receive runtime feedback, especially initial-plan and "
                "binding/evidence failures. This implicates the current planning, "
                "evidence, and recovery interfaces; it does not show that effect "
                "decomposition itself requires the observed utility loss."
            ),
        },
        "claim_boundary": (
            "This is a deterministic post-hoc pathway audit of frozen E78 logs. "
            "Runtime feedback is directly observed, but the no-guard and guarded "
            "model trajectories are separate stochastic runs, so stratum differences "
            "are not randomized causal effects. The literal-grounding probe is a "
            "diagnostic sensitivity check, not an authorization oracle. Official "
            "AgentDojo utility labels remain unchanged."
        ),
        "cases": cases,
    }


def write_outputs(output_dir: Path, report: Mapping[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "headline-benign-utility-pathway-audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output_dir / "headline-benign-utility-pathway-audit-cases.csv"
    ).open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "case_key",
            "no_guard_utility",
            "ours_utility",
            "utility_transition",
            "feedback_event_count",
            "observed_pathway",
            "feedback_reason_codes",
            "recovery_states",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for case in report["cases"]:
            writer.writerow(
                {
                    **{field: case[field] for field in fields[:6]},
                    "feedback_reason_codes": ";".join(
                        case["feedback_reason_codes"]
                    ),
                    "recovery_states": ";".join(case["recovery_states"]),
                }
            )

    overall = report["overall"]
    feedback = report["feedback_stratum"]
    no_feedback = report["no_feedback_stratum"]
    discordant = report["discordant"]
    anatomy = report["runtime_feedback_loss_anatomy"]
    grounding = report["literal_grounding_probe"]
    lines = [
        "# E78 Headline Benign-Utility Pathway Audit",
        "",
        "## Scope",
        "",
        "- Frozen capacity-matched benign tasks: 97",
        "- Model calls: 0",
        "- Tool executions: 0",
        "- Official utility labels changed: no",
        "",
        "## Paired Decomposition",
        "",
        (
            f"- Overall: no guard {overall['no_guard_successes']}/97; "
            f"guard {overall['ours_successes']}/97; "
            f"net {overall['net_ours_minus_no_guard']}."
        ),
        (
            f"- Runtime-feedback stratum: {feedback['cases']} cases, "
            f"{feedback['no_guard_successes']}->{feedback['ours_successes']} "
            f"successes, net {feedback['net_ours_minus_no_guard']}."
        ),
        (
            f"- No-feedback stratum: {no_feedback['cases']} cases, "
            f"{no_feedback['no_guard_successes']}->{no_feedback['ours_successes']} "
            f"successes, net {no_feedback['net_ours_minus_no_guard']}."
        ),
        (
            f"- Discordant losses with observed runtime feedback: "
            f"{discordant['losses_with_runtime_feedback']}/"
            f"{discordant['losses']}."
        ),
        "",
        "## Runtime-Feedback Loss Anatomy",
        "",
        (
            f"- Initial-plan construction/coverage reason on "
            f"{anatomy['plan_construction_cases']}/32 losses."
        ),
        (
            f"- Binding/evidence reason on "
            f"{anatomy['binding_or_evidence_cases']}/32 losses."
        ),
        (
            "- Non-exclusive reason-case counts: `"
            + json.dumps(anatomy["reason_case_counts_nonexclusive"], sort_keys=True)
            + "`."
        ),
        (
            f"- Resolver checks in the literal probe: "
            f"{grounding['resolver_check_count']}; loss cases with at least one "
            "resolver value visible in an earlier benign tool result: "
            f"{grounding['loss_cases_with_a_resolver_value_seen_in_prior_tool_output']}."
        ),
        "",
        "## Interpretation",
        "",
        str(report["interpretation"]["conclusion"]),
        "",
        "## Claim Boundary",
        "",
        str(report["claim_boundary"]),
        "",
    ]
    (output_dir / "headline-benign-utility-pathway-audit.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )
    (output_dir / "claim-boundary.md").write_text(
        "# Claim Boundary\n\n" + str(report["claim_boundary"]) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    root = (args.root or find_root(Path(__file__))).resolve()
    output_dir = args.output_dir or (
        root
        / "experiments/security-analysis-ablation-and-overhead/results/"
        "headline-benign-utility-pathway-audit"
    )
    report = build_report(root)
    write_outputs(output_dir, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "overall": report["overall"],
                "feedback_stratum": report["feedback_stratum"],
                "no_feedback_stratum": report["no_feedback_stratum"],
                "runtime_feedback_loss_anatomy": report[
                    "runtime_feedback_loss_anatomy"
                ],
                "literal_grounding_probe": report["literal_grounding_probe"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
