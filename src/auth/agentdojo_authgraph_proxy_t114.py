"""T114 AuthGraph-style proxy over AgentDojo logs.

This script does not run a model. It reads AgentDojo JSON logs produced by
T112 and simulates two clean-authorization/provenance alignment proxies:

1. tool_sequence_proxy: allow an attacked trajectory only if its tool-name
   sequence exactly matches the clean no-injection trajectory for the same
   user task.
2. tool_arg_alignment_proxy: allow only if both tool names and serialized
   arguments exactly match the clean trajectory.

This is not the AuthGraph authors' implementation. It is a deliberately
transparent proxy baseline for the same high-level idea: compare an
authorization graph derived from clean user intent against an execution graph
observed under attack.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROXY_METHODS = ("tool_sequence_proxy_v1", "tool_arg_alignment_proxy_v1")


@dataclass(frozen=True)
class ParsedLog:
    path: Path
    pipeline: str
    suite: str
    user_task_id: str | None
    injection_task_id: str | None
    attack_type: str
    utility: bool
    security: bool
    calls: list[dict[str, Any]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logdir", default="runs/agentdojo_t112_pilot_deepseek_direct")
    parser.add_argument("--attack", default="direct")
    parser.add_argument("--pipeline", action="append", default=[])
    parser.add_argument("--suite", action="append", default=[])
    parser.add_argument("--output", default="analysis/results/agentdojo_authgraph_proxy_t114_v1.json")
    parser.add_argument("--output-md", default="analysis/results/agentdojo_authgraph_proxy_t114_v1.md")
    return parser.parse_args()


def normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): normalize(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, list):
        return [normalize(v) for v in value]
    return value


def call_signature(call: dict[str, Any]) -> str:
    return json.dumps(
        {
            "function": call["function"],
            "args": normalize(call.get("args", {})),
        },
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )


def extract_calls(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for message in messages:
        if message.get("role") != "assistant":
            continue
        for tool_call in message.get("tool_calls") or []:
            calls.append(
                {
                    "function": tool_call.get("function"),
                    "args": normalize(tool_call.get("args") or {}),
                }
            )
    return calls


def parse_log(path: Path, root: Path) -> ParsedLog:
    data = json.loads(path.read_text(encoding="utf-8"))
    rel = path.relative_to(root)
    pipeline = rel.parts[0]
    return ParsedLog(
        path=path,
        pipeline=pipeline,
        suite=str(data.get("suite_name")),
        user_task_id=data.get("user_task_id"),
        injection_task_id=data.get("injection_task_id"),
        attack_type=str(data.get("attack_type") or "none"),
        utility=bool(data.get("utility")),
        security=bool(data.get("security")),
        calls=extract_calls(data.get("messages") or []),
    )


def load_logs(root: Path, pipelines: list[str], suites: list[str], attack: str) -> tuple[dict[tuple[str, str, str], ParsedLog], list[ParsedLog]]:
    clean: dict[tuple[str, str, str], ParsedLog] = {}
    attacked: list[ParsedLog] = []
    pipeline_filter = set(pipelines)
    suite_filter = set(suites)
    for path in sorted(root.glob("*/*/*/*/*.json")):
        try:
            record = parse_log(path, root)
        except (json.JSONDecodeError, KeyError, IndexError):
            continue
        if pipeline_filter and record.pipeline not in pipeline_filter:
            continue
        if suite_filter and record.suite not in suite_filter:
            continue
        if record.user_task_id is None:
            continue
        if record.attack_type == "none" and record.injection_task_id is None:
            clean[(record.pipeline, record.suite, record.user_task_id)] = record
        elif record.attack_type == attack and record.injection_task_id is not None:
            attacked.append(record)
    return clean, attacked


def decide(method: str, clean_calls: list[dict[str, Any]], actual_calls: list[dict[str, Any]]) -> tuple[bool, str]:
    clean_tools = [call["function"] for call in clean_calls]
    actual_tools = [call["function"] for call in actual_calls]
    if method == "tool_sequence_proxy_v1":
        if actual_tools == clean_tools:
            return True, "tool_sequence_matches_clean"
        return False, first_mismatch_reason(clean_tools, actual_tools, compare="tool")
    if method == "tool_arg_alignment_proxy_v1":
        clean_sigs = [call_signature(call) for call in clean_calls]
        actual_sigs = [call_signature(call) for call in actual_calls]
        if actual_sigs == clean_sigs:
            return True, "tool_and_args_match_clean"
        return False, first_mismatch_reason(clean_sigs, actual_sigs, compare="tool_args")
    raise ValueError(f"Unknown proxy method: {method}")


def first_mismatch_reason(expected: list[str], actual: list[str], compare: str) -> str:
    for idx, (exp, act) in enumerate(zip(expected, actual)):
        if exp != act:
            return f"{compare}_mismatch_at_{idx}"
    if len(actual) < len(expected):
        return f"{compare}_missing_suffix"
    if len(actual) > len(expected):
        return f"{compare}_extra_suffix"
    return f"{compare}_unknown_mismatch"


def evaluate(root: Path, pipelines: list[str], suites: list[str], attack: str) -> dict[str, Any]:
    clean_logs, attacked_logs = load_logs(root, pipelines, suites, attack)
    rows: list[dict[str, Any]] = []
    missing_clean: list[dict[str, Any]] = []
    for actual in attacked_logs:
        key = (actual.pipeline, actual.suite, actual.user_task_id or "")
        clean = clean_logs.get(key)
        if clean is None:
            missing_clean.append(
                {
                    "pipeline": actual.pipeline,
                    "suite": actual.suite,
                    "user_task_id": actual.user_task_id,
                    "injection_task_id": actual.injection_task_id,
                    "path": str(actual.path),
                }
            )
            continue
        for method in PROXY_METHODS:
            allowed, reason = decide(method, clean.calls, actual.calls)
            rows.append(
                {
                    "method": method,
                    "pipeline": actual.pipeline,
                    "suite": actual.suite,
                    "user_task_id": actual.user_task_id,
                    "injection_task_id": actual.injection_task_id,
                    "baseline_utility_under_attack": actual.utility,
                    "baseline_attack_success": actual.security,
                    "proxy_decision": "allow" if allowed else "deny",
                    "proxy_utility_under_attack": bool(actual.utility and allowed),
                    "proxy_attack_success": bool(actual.security and allowed),
                    "deny_reason": reason if not allowed else None,
                    "clean_calls": clean.calls,
                    "actual_calls": actual.calls,
                }
            )
    return {
        "schema_version": "agentdojo_authgraph_proxy_t114_v1",
        "claim_boundary": "AuthGraph-style proxy over AgentDojo logs; not the AuthGraph authors' implementation and not a learned graph model",
        "logdir": str(root),
        "attack": attack,
        "proxy_methods": list(PROXY_METHODS),
        "n_clean_logs": len(clean_logs),
        "n_attacked_logs": len(attacked_logs),
        "n_evaluated_rows": len(rows),
        "missing_clean": missing_clean,
        "summary_by_pipeline_suite": summarize(rows, keys=("method", "pipeline", "suite")),
        "summary_by_method": summarize(rows, keys=("method",)),
        "rows": rows,
    }


def summarize(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in keys)].append(row)
    out = []
    for key_values, group in sorted(grouped.items(), key=lambda item: item[0]):
        n = len(group)
        baseline_asr = sum(r["baseline_attack_success"] for r in group)
        baseline_aur = sum(r["baseline_utility_under_attack"] for r in group)
        proxy_asr = sum(r["proxy_attack_success"] for r in group)
        proxy_aur = sum(r["proxy_utility_under_attack"] for r in group)
        deny = sum(r["proxy_decision"] == "deny" for r in group)
        prevented_attack = sum(
            r["proxy_decision"] == "deny" and r["baseline_attack_success"] for r in group
        )
        denied_successful_nonattack = sum(
            r["proxy_decision"] == "deny"
            and r["baseline_utility_under_attack"]
            and not r["baseline_attack_success"]
            for r in group
        )
        record = {key: value for key, value in zip(keys, key_values)}
        record.update(
            {
                "n": n,
                "baseline_A_UR": baseline_aur / n if n else math.nan,
                "baseline_ASR": baseline_asr / n if n else math.nan,
                "proxy_A_UR": proxy_aur / n if n else math.nan,
                "proxy_ASR": proxy_asr / n if n else math.nan,
                "deny_rate": deny / n if n else math.nan,
                "prevented_attack_count": f"{prevented_attack}/{n}",
                "denied_successful_nonattack_count": f"{denied_successful_nonattack}/{n}",
                "baseline_A_UR_count": f"{baseline_aur}/{n}",
                "baseline_ASR_count": f"{baseline_asr}/{n}",
                "proxy_A_UR_count": f"{proxy_aur}/{n}",
                "proxy_ASR_count": f"{proxy_asr}/{n}",
            }
        )
        out.append(record)
    return out


def write_report(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# T114 AgentDojo AuthGraph-Style Proxy",
        "",
        "## Scope",
        "",
        "- Reads existing AgentDojo JSON logs; does not call a model.",
        "- Clean no-injection trajectory is treated as the authorization graph.",
        "- Attacked trajectory is treated as the execution/provenance graph.",
        "- This is a proxy baseline, not the AuthGraph authors' implementation.",
        "",
        "## Aggregate Results",
        "",
        "| method | n | baseline A.UR | baseline ASR | proxy A.UR | proxy ASR | deny rate | prevented attack | denied successful nonattack |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["summary_by_method"]:
        lines.append(
            f"| {row['method']} | {row['n']} | {row['baseline_A_UR']:.4f} | {row['baseline_ASR']:.4f} | "
            f"{row['proxy_A_UR']:.4f} | {row['proxy_ASR']:.4f} | {row['deny_rate']:.4f} | "
            f"{row['prevented_attack_count']} | {row['denied_successful_nonattack_count']} |"
        )
    lines.extend(
        [
            "",
            "## Per Suite",
            "",
            "| method | pipeline | suite | n | baseline A.UR | baseline ASR | proxy A.UR | proxy ASR | deny rate |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["summary_by_pipeline_suite"]:
        lines.append(
            f"| {row['method']} | {row['pipeline']} | {row['suite']} | {row['n']} | "
            f"{row['baseline_A_UR']:.4f} | {row['baseline_ASR']:.4f} | "
            f"{row['proxy_A_UR']:.4f} | {row['proxy_ASR']:.4f} | {row['deny_rate']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- A lower proxy ASR is useful only if proxy A.UR does not collapse.",
            "- Denying a mismatched attacked trajectory is not equivalent to safely replaying a clean trajectory.",
            "- This proxy tests whether simple clean-plan alignment is already enough; it does not provide AuthGraph's full graph semantics.",
        ]
    )
    if payload["missing_clean"]:
        lines.extend(["", "## Missing Clean Logs", "", f"- Missing clean rows: {len(payload['missing_clean'])}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    payload = evaluate(Path(args.logdir), args.pipeline, args.suite, args.attack)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    write_report(payload, Path(args.output_md))
    print(f"Wrote T114 JSON to {args.output}")
    print(f"Wrote T114 report to {args.output_md}")


if __name__ == "__main__":
    main()
