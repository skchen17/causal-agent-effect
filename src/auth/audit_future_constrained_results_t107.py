"""T107 audit for future-constrained CEG-Auth prototype results.

The audit converts T102-T106 outputs into paper-facing evidence records with
counts, Wilson confidence intervals, artifact sources, and claim boundaries.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit T102-T106 future-constrained results.")
    parser.add_argument("--t102", default="analysis/results/future_constraint_compiler_eval_t102_v1.json")
    parser.add_argument("--t103", default="analysis/results/future_shadow_replay_t103_v1.json")
    parser.add_argument("--t104", default="analysis/results/precommit_blocking_t104_v1.json")
    parser.add_argument("--t105", default="analysis/results/shadow_real_divergence_t105_v1.json")
    parser.add_argument("--t106", default="analysis/results/efficiency_t106_v1.json")
    parser.add_argument("--output", default="analysis/results/future_constrained_audit_t107_v1.json")
    parser.add_argument("--output-md", default="analysis/results/future_constrained_audit_t107_v1.md")
    return parser.parse_args()


def load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + (z * z) / n
    center = (p + (z * z) / (2 * n)) / denom
    margin = z * ((p * (1 - p) / n + (z * z) / (4 * n * n)) ** 0.5) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def metric_record(source: str, metric: str, k: int, n: int, direction: str, interpretation: str) -> dict[str, Any]:
    lo, hi = wilson(k, n)
    return {
        "source": source,
        "metric": metric,
        "count": k,
        "n": n,
        "rate": k / n if n else 0.0,
        "wilson95_low": lo,
        "wilson95_high": hi,
        "direction": direction,
        "interpretation": interpretation,
    }


def audit_t102(path: str, obj: dict[str, Any]) -> list[dict[str, Any]]:
    rows = obj["row_metrics"]
    n = len(rows)
    return [
        metric_record(path, "schema_validity", sum(r["schema_valid"] for r in rows), n, "higher_better", "Future-constraint records satisfy required schema."),
        metric_record(path, "constraint_soundness", sum(r["constraint_sound"] for r in rows), n, "higher_better", "Validator finds no over-permissive constraint under gold/rule envelope."),
        metric_record(path, "decision_accuracy", sum(r["decision_correct"] for r in rows), n, "higher_better", "Rule compiler matches gold allow/reject labels on T102 local synthetic pairs."),
        metric_record(path, "over_permission_error", sum(r["over_permissive"] for r in rows), n, "lower_better", "Unauthorized intents incorrectly allowed by compiler."),
        metric_record(path, "over_restriction_error", sum(r["over_restrictive"] for r in rows), n, "lower_better", "Authorized intents incorrectly rejected by compiler."),
    ]


def audit_t103(path: str, obj: dict[str, Any]) -> list[dict[str, Any]]:
    s = obj["summary"]
    unauth_n = int(s["unauthorized_n"])
    auth_n = int(s["authorized_n"])
    dev_n = int(s["deviation_challenge_n"])
    return [
        metric_record(path, "unauthorized_block_rate", round(s["pre_effect_block_rate_unauthorized"] * unauth_n), unauth_n, "higher_better", "Unauthorized intents blocked by staged shadow/replay pipeline."),
        metric_record(path, "unauthorized_committed_action_rate", round(s["unauthorized_committed_action_rate"] * unauth_n), unauth_n, "lower_better", "Unauthorized intents that still committed unauthorized effects."),
        metric_record(path, "authorized_false_denial_rate", round(s["authorized_false_denial_rate"] * auth_n), auth_n, "lower_better", "Authorized intents blocked by the staged prototype."),
        metric_record(path, "deviation_block_rate", round(s["deviation_precommit_block_rate"] * dev_n), dev_n, "higher_better", "Injected authorized-path deviations blocked by prefix guard."),
    ]


def audit_t104(path: str, obj: dict[str, Any]) -> list[dict[str, Any]]:
    s = obj["summary"]
    unauth_n = int(s["unauthorized_n"])
    auth_n = int(s["authorized_n"])
    return [
        metric_record(path, "pre_effect_block_rate_unauthorized", round(s["pre_effect_block_rate_unauthorized"] * unauth_n), unauth_n, "higher_better", "Unauthorized T104 cases blocked before staged commit."),
        metric_record(path, "unauthorized_committed_action_rate", round(s["unauthorized_committed_action_rate"] * unauth_n), unauth_n, "lower_better", "Unauthorized T104 cases that committed unauthorized effects."),
        metric_record(path, "authorized_false_denial_rate", round(s["authorized_false_denial_rate"] * auth_n), auth_n, "lower_better", "Authorized T104 cases blocked by commit boundary."),
        metric_record(path, "authorized_commit_rate", round(s["authorized_commit_rate"] * auth_n), auth_n, "higher_better", "Authorized T104 cases that committed staged allowed effects."),
    ]


def audit_t105(path: str, obj: dict[str, Any]) -> list[dict[str, Any]]:
    s = obj["summary"]
    faithful_n = int(s["faithful_n"])
    unsafe_n = int(s["unsafe_n"])
    return [
        metric_record(path, "faithful_allow_rate", round(s["faithful_allow_rate"] * faithful_n), faithful_n, "higher_better", "Faithful substitutions allowed under the same future constraint."),
        metric_record(path, "unsafe_nonallow_rate", round(s["unsafe_nonallow_rate"] * unsafe_n), unsafe_n, "higher_better", "Unsafe substitutions denied or abstained before commit."),
        metric_record(path, "unsafe_deny_rate", round(s["unsafe_deny_rate"] * unsafe_n), unsafe_n, "context", "Unsafe substitutions hard-denied by current guard."),
        metric_record(path, "unsafe_abstain_rate", round(s["unsafe_abstain_rate"] * unsafe_n), unsafe_n, "context", "Unsafe substitutions routed to abstain by current guard."),
    ]


def audit_t106(path: str, obj: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "source": path,
            "stage": row["stage"],
            "n": row["n"],
            "mean_ms": row["mean_ms"],
            "median_ms": row["median_ms"],
            "p95_ms": row["p95_ms"],
            "max_ms": row["max_ms"],
            "interpretation": "Local deterministic Python prototype timing only; excludes LLM/provider/browser/human review.",
        }
        for row in obj["timings"]
    ]


def claim_register() -> list[dict[str, Any]]:
    return [
        {
            "claim": "The future-constrained pipeline is implementable end-to-end in a local staged prototype.",
            "status": "supported_for_local_prototype",
            "evidence": ["T102", "T103", "T104", "T105", "T106"],
            "boundary": "Does not imply provider-backed or deployed-runtime safety.",
        },
        {
            "claim": "Compiled future constraints can avoid over-permission on the current T102 dataset.",
            "status": "supported_only_for_rule_gold_envelope",
            "evidence": ["T102"],
            "boundary": "Not yet evidence for LLM compiler reliability or natural task authorization extraction.",
        },
        {
            "claim": "Trace-locked replay and prefix guards can block constructed unauthorized deviations before staged commit.",
            "status": "supported_for_constructed_local_cases",
            "evidence": ["T103", "T104", "T105"],
            "boundary": "Requires mediation, staging, and observable effects; no live external side effects tested.",
        },
        {
            "claim": "The method is deploy-ready for real providers, SaaS messaging, or HTTP browser automation.",
            "status": "not_supported",
            "evidence": [],
            "boundary": "Requires T109/T111-style real boundary and external-validity experiments.",
        },
        {
            "claim": "The current results prove superiority over existing agent-security defenses.",
            "status": "not_supported",
            "evidence": [],
            "boundary": "Requires T110 ablations and faithful baselines.",
        },
    ]


def md_table(rows: list[tuple[Any, ...]], headers: list[str]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(out)


def write_report(path: Path, result: dict[str, Any]) -> None:
    metric_rows = []
    for row in result["rate_metrics"]:
        metric_rows.append(
            (
                row["source"].split("/")[-1],
                row["metric"],
                f"{row['count']}/{row['n']}",
                f"{row['rate']:.4f}",
                f"[{row['wilson95_low']:.4f}, {row['wilson95_high']:.4f}]",
                row["direction"],
            )
        )
    timing_rows = []
    for row in result["timing_metrics"]:
        timing_rows.append(
            (
                row["stage"],
                row["n"],
                f"{row['mean_ms']:.4f}",
                f"{row['median_ms']:.4f}",
                f"{row['p95_ms']:.4f}",
                f"{row['max_ms']:.4f}",
            )
        )
    claim_rows = []
    for row in result["claim_register"]:
        claim_rows.append((row["claim"], row["status"], row["boundary"]))
    text = "\n\n".join(
        [
            "# T107 Future-Constrained Result Audit",
            "## Rate Metrics",
            md_table(metric_rows, ["source", "metric", "count/n", "rate", "Wilson 95% CI", "direction"]),
            "## Timing Metrics",
            md_table(timing_rows, ["stage", "n", "mean_ms", "median_ms", "p95_ms", "max_ms"]),
            "## Claim Register",
            md_table(claim_rows, ["claim", "status", "boundary"]),
            "## Paper-Use Guidance",
            (
                "Use T102-T106 as controlled local prototype evidence. Do not describe these "
                "results as deployed-agent validation, provider-backed safety, HTTP browser "
                "automation, SaaS messaging protection, or superiority over existing defenses. "
                "Main-conference claims require T108 non-gold compiler stress, T109 real local "
                "side-effect boundaries, T110 ablations/baselines, and T111 external validity."
            ),
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    t102 = load_json(args.t102)
    t103 = load_json(args.t103)
    t104 = load_json(args.t104)
    t105 = load_json(args.t105)
    t106 = load_json(args.t106)

    rate_metrics = []
    rate_metrics.extend(audit_t102(args.t102, t102))
    rate_metrics.extend(audit_t103(args.t103, t103))
    rate_metrics.extend(audit_t104(args.t104, t104))
    rate_metrics.extend(audit_t105(args.t105, t105))

    result = {
        "dataset": "future_constrained_audit_t107_v1",
        "rate_metrics": rate_metrics,
        "timing_metrics": audit_t106(args.t106, t106),
        "claim_register": claim_register(),
        "artifact_sources": {
            "T102": args.t102,
            "T103": args.t103,
            "T104": args.t104,
            "T105": args.t105,
            "T106": args.t106,
        },
    }
    write_json(Path(args.output), result)
    write_report(Path(args.output_md), result)
    print(f"Wrote T107 audit JSON to {args.output}")
    print(f"Wrote T107 audit report to {args.output_md}")


if __name__ == "__main__":
    main()
