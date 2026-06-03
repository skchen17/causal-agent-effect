"""T120 summary and paired comparisons for AgentDojo Strong+Max experiments."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


OFFICIAL_DEFENSES = {
    "repeat_user_prompt",
    "spotlighting_with_delimiting",
    "transformers_pi_detector",
    "tool_filter_deepseek",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-json", default="analysis/results/agentdojo_strongmax_matrix_t118.json")
    parser.add_argument("--baseline-shard-dir", default="analysis/results/agentdojo_t118_strongmax_shards")
    parser.add_argument("--fc-json", default="analysis/results/agentdojo_fc_guard_t119.json")
    parser.add_argument(
        "--fc-shard-dir",
        action="append",
        default=[],
        help="FC-Guard shard directory. May be provided multiple times for main and ablation runs.",
    )
    parser.add_argument(
        "--authgraph-json",
        action="append",
        default=[],
        help="Optional T114 AuthGraph-style proxy JSON for side-by-side summary reporting.",
    )
    parser.add_argument("--output", default="analysis/results/agentdojo_strongmax_fc_guard_summary_t120.json")
    parser.add_argument("--output-md", default="analysis/results/agentdojo_strongmax_fc_guard_summary_t120.md")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_baseline_shards(shard_dir: Path) -> list[dict[str, Any]]:
    if not shard_dir.exists():
        return []
    shards = []
    for path in sorted(shard_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if data.get("schema_version") == "agentdojo_strongmax_setting_t118_v1":
            data["_path"] = str(path)
            shards.append(data)
    return shards


def load_fc_shards(shard_dir: Path) -> list[dict[str, Any]]:
    if not shard_dir.exists():
        return []
    shards = []
    for path in sorted(shard_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if data.get("schema_version") in {
            "agentdojo_fc_guard_setting_t119_v1",
            "agentdojo_fc_guard_setting_t119_v2",
        }:
            data["_path"] = str(path)
            shards.append(data)
    return shards


def load_authgraph_summaries(paths: list[str]) -> list[dict[str, Any]]:
    rows = []
    for path_str in paths:
        path = Path(path_str)
        data = load_json(path)
        if not data or data.get("schema_version") != "agentdojo_authgraph_proxy_t114_v1":
            continue
        for row in data.get("summary_by_method", []):
            copied = dict(row)
            copied["source"] = path_str
            rows.append(copied)
    return rows


def wilson(successes: int, total: int, z: float = 1.96) -> dict[str, float | int]:
    if total <= 0:
        return {"successes": successes, "total": total, "rate": math.nan, "lo": math.nan, "hi": math.nan}
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denom
    return {"successes": successes, "total": total, "rate": p, "lo": max(0.0, center - half), "hi": min(1.0, center + half)}


def baseline_case_index(shards: list[dict[str, Any]]) -> dict[tuple[str, str, str, str, str], dict[str, Any]]:
    out = {}
    for shard in shards:
        for case in shard.get("cases", []):
            key = (
                shard["defense"],
                shard["suite"],
                shard["attack"],
                case["user_task_id"],
                case["injection_task_id"],
            )
            out[key] = {
                "attack_success": bool(case["attack_success"]),
                "utility_under_attack": bool(case["utility_under_attack"]),
                "shard": shard.get("_path"),
            }
    return out


def fc_case_index(
    fc: dict[str, Any] | None,
    fc_shards: list[dict[str, Any]],
) -> dict[tuple[str, str, str, str, str], dict[str, Any]]:
    out = {}
    rows = []
    if fc:
        rows.extend(fc.get("rows", []))
    for shard in fc_shards:
        rows.extend(shard.get("rows", []))
    for row in rows:
        key = (
            row["method"],
            row["suite"],
            row["attack"],
            row["user_task_id"],
            row["injection_task_id"],
        )
        out[key] = row
    return out


def choose_best_official(shards: list[dict[str, Any]]) -> dict[tuple[str, str], str]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for shard in shards:
        if shard["defense"] not in OFFICIAL_DEFENSES:
            continue
        grouped[(shard["suite"], shard["attack"], shard["defense"])].append(shard)
    by_suite_attack: dict[tuple[str, str], list[tuple[str, float, int]]] = defaultdict(list)
    for (suite, attack, defense), group in grouped.items():
        n = sum(row.get("n_attacked", 0) for row in group)
        successes = sum(row.get("ASR_ci", {}).get("successes", 0) for row in group)
        rate = successes / n if n else math.inf
        by_suite_attack[(suite, attack)].append((defense, rate, n))
    out = {}
    for key, values in by_suite_attack.items():
        values = [value for value in values if value[2] > 0]
        if values:
            out[key] = sorted(values, key=lambda item: (item[1], item[0]))[0][0]
    return out


def paired_counts(
    *,
    baseline_cases: dict[tuple[str, str, str, str, str], dict[str, Any]],
    fc_cases: dict[tuple[str, str, str, str, str], dict[str, Any]],
    defense_selector: str,
    best_official: dict[tuple[str, str], str],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[tuple[dict[str, Any], dict[str, Any], str]]] = defaultdict(list)
    for (method, suite, attack, user_task_id, injection_task_id), fc_row in fc_cases.items():
        defense = defense_selector
        if defense_selector == "best_official":
            defense = best_official.get((suite, attack), "")
            if not defense:
                continue
        base = baseline_cases.get((defense, suite, attack, user_task_id, injection_task_id))
        if base is None:
            continue
        grouped[(method, defense_selector)].append((base, fc_row, defense))

    out = []
    for (method, comparison), pairs in sorted(grouped.items()):
        n = len(pairs)
        baseline_success = sum(base["attack_success"] for base, _row, _defense in pairs)
        baseline_utility = sum(base["utility_under_attack"] for base, _row, _defense in pairs)
        fc_success = sum(row["attack_success"] for _base, row, _defense in pairs)
        fc_utility = sum(row.get("utility_under_attack", False) for _base, row, _defense in pairs)
        fc_u_commit = sum(row.get("U_Commit", False) for _base, row, _defense in pairs)
        baseline_only = sum(base["attack_success"] and not row["attack_success"] for base, row, _defense in pairs)
        fc_only = sum((not base["attack_success"]) and row["attack_success"] for base, row, _defense in pairs)
        both = sum(base["attack_success"] and row["attack_success"] for base, row, _defense in pairs)
        neither = sum((not base["attack_success"]) and (not row["attack_success"]) for base, row, _defense in pairs)
        fc_fdeny = sum(row.get("FDeny", False) for _base, row, _defense in pairs)
        fc_abstain = sum(row.get("abstained", False) for _base, row, _defense in pairs)
        fc_replay_error = sum(bool(row.get("replay_errors")) for _base, row, _defense in pairs)
        fc_unsafe_before_block = sum(row.get("unsafe_before_block", False) for _base, row, _defense in pairs)
        fc_precommit_block = sum(row.get("precommit_blocked", False) for _base, row, _defense in pairs)
        out.append(
            {
                "method": method,
                "comparison": comparison,
                "n_pairs": n,
                "baseline_ASR": baseline_success / n if n else math.nan,
                "baseline_A_UR": baseline_utility / n if n else math.nan,
                "fc_ASR": fc_success / n if n else math.nan,
                "fc_A_UR": fc_utility / n if n else math.nan,
                "fc_U_Commit": fc_u_commit / n if n else math.nan,
                "delta_ASR_baseline_minus_fc": (baseline_success - fc_success) / n if n else math.nan,
                "baseline_only_prevented": baseline_only,
                "fc_only_regressions": fc_only,
                "both_attack_success": both,
                "neither_attack_success": neither,
                "fc_FDeny": fc_fdeny / n if n else math.nan,
                "fc_Abstain": fc_abstain / n if n else math.nan,
                "fc_Coverage": 1 - fc_abstain / n if n else math.nan,
                "fc_Replay_Error": fc_replay_error / n if n else math.nan,
                "fc_Unsafe_Before_Block": fc_unsafe_before_block / n if n else math.nan,
                "fc_Precommit_Block": fc_precommit_block / n if n else math.nan,
                "baseline_ASR_ci": wilson(baseline_success, n),
                "baseline_A_UR_ci": wilson(baseline_utility, n),
                "fc_ASR_ci": wilson(fc_success, n),
                "fc_A_UR_ci": wilson(fc_utility, n),
                "fc_U_Commit_ci": wilson(fc_u_commit, n),
                "fc_FDeny_ci": wilson(fc_fdeny, n),
                "fc_Abstain_ci": wilson(fc_abstain, n),
                "fc_Coverage_ci": wilson(n - fc_abstain, n),
                "fc_Replay_Error_ci": wilson(fc_replay_error, n),
                "fc_Unsafe_Before_Block_ci": wilson(fc_unsafe_before_block, n),
                "fc_Precommit_Block_ci": wilson(fc_precommit_block, n),
            }
        )
    return out


def main() -> None:
    args = parse_args()
    fc_shard_dirs = args.fc_shard_dir or ["analysis/results/agentdojo_t119_fc_guard_shards"]
    baseline = load_json(Path(args.baseline_json))
    fc = load_json(Path(args.fc_json))
    shards = load_baseline_shards(Path(args.baseline_shard_dir))
    fc_shards = []
    for shard_dir in fc_shard_dirs:
        fc_shards.extend(load_fc_shards(Path(shard_dir)))
    base_cases = baseline_case_index(shards)
    fc_cases = fc_case_index(fc, fc_shards)
    best_official = choose_best_official(shards)
    authgraph_summaries = load_authgraph_summaries(args.authgraph_json)
    paired = []
    for comparison in ("none", "best_official"):
        paired.extend(
            paired_counts(
                baseline_cases=base_cases,
                fc_cases=fc_cases,
                defense_selector=comparison,
                best_official=best_official,
            )
        )

    payload = {
        "schema_version": "agentdojo_strongmax_fc_guard_summary_t120_v1",
        "baseline_json": args.baseline_json,
        "baseline_shard_dir": args.baseline_shard_dir,
        "fc_json": args.fc_json,
        "fc_shard_dirs": fc_shard_dirs,
        "authgraph_json": args.authgraph_json,
        "baseline_loaded": baseline is not None,
        "fc_loaded": fc is not None,
        "n_baseline_shards": len(shards),
        "n_fc_shards": len(fc_shards),
        "n_baseline_cases": len(base_cases),
        "n_fc_cases": len(fc_cases),
        "authgraph_proxy_summary_by_method": authgraph_summaries,
        "best_official_by_suite_attack": [
            {"suite": suite, "attack": attack, "defense": defense}
            for (suite, attack), defense in sorted(best_official.items())
        ],
        "baseline_summary": baseline.get("summary_by_setting", []) if baseline else [],
        "fc_summary_by_method": fc.get("summary_by_method", []) if fc else [],
        "paired_comparisons": paired,
        "claim_boundary": "Summary only compares cases present in both baseline shards and FC-Guard rows.",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(payload, Path(args.output_md))
    print(f"Wrote T120 JSON to {args.output}")
    print(f"Wrote T120 report to {args.output_md}")


def write_report(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# T120 AgentDojo Strong+Max / FC-Guard Summary",
        "",
        "## Loaded Artifacts",
        "",
        f"- Baseline JSON loaded: `{payload['baseline_loaded']}`",
        f"- FC JSON loaded: `{payload['fc_loaded']}`",
        f"- Baseline shards: `{payload['n_baseline_shards']}`",
        f"- FC shards: `{payload['n_fc_shards']}`",
        f"- Baseline case records: `{payload['n_baseline_cases']}`",
        f"- FC case records: `{payload['n_fc_cases']}`",
        "",
        "## Paired Comparisons",
        "",
        "| method | comparison | n | baseline A.UR | baseline ASR | FC A.UR | FC ASR | U-Commit | FDeny | Abstain | Coverage | Replay err | prevented | regressions |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["paired_comparisons"]:
        lines.append(
            f"| {row['method']} | {row['comparison']} | {row['n_pairs']} | "
            f"{row['baseline_A_UR']:.4f} | {row['baseline_ASR']:.4f} | "
            f"{row['fc_A_UR']:.4f} | {row['fc_ASR']:.4f} | {row['fc_U_Commit']:.4f} | "
            f"{row['fc_FDeny']:.4f} | {row['fc_Abstain']:.4f} | {row['fc_Coverage']:.4f} | "
            f"{row['fc_Replay_Error']:.4f} | {row['baseline_only_prevented']} | {row['fc_only_regressions']} |"
        )
    if not payload["paired_comparisons"]:
        lines.extend(["", "No paired comparisons were available. Run T118 shards and T119 rows on matching suites/attacks/cases first."])
    if payload.get("authgraph_proxy_summary_by_method"):
        lines.extend(
            [
                "",
                "## AuthGraph-Style Proxy Reference",
                "",
                "| method | n | proxy A.UR | proxy ASR | deny rate | source |",
                "| --- | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for row in payload["authgraph_proxy_summary_by_method"]:
            lines.append(
                f"| {row['method']} | {row['n']} | {row['proxy_A_UR']:.4f} | "
                f"{row['proxy_ASR']:.4f} | {row['deny_rate']:.4f} | {row['source']} |"
            )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- `best_official` is selected from completed official-defense shards by lowest ASR for the same suite and attack.",
            "- This summary does not fill missing attacks, defenses, or suites; absent cells remain absent.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
