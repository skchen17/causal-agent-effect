#!/usr/bin/env python3
"""Fail-fast finalize for the strict atom representation attribution protocol.

CLI contract (protocol section 10, item 6):

    finalize-strict-attribution.py --require-complete --require-paired

Reads the per-variant ``paired-case-results.jsonl`` run records (protocol
section 6), applies the fail-fast gates of protocol section 11 (completeness,
null-discipline/integrity, pairing, frozen-input hash consistency), computes
the section 7 metrics (ASR, benign/attack utility, runtime decomposition) and
the section 2.2 paired statistics (exact McNemar with Holm correction, paired
bootstrap with fixed seed), and writes read-only reproducible outputs:

    results/strict-atom-representation-attribution/
        report.json                 full machine-readable report
        paired-statistics.json      paired ASR/utility comparisons
        paired-statistics.csv       flat comparison table
        failure-examples.jsonl      every error/runtime-failure row
        report.md                   human-readable summary

Exit codes: 0 = all requested gates passed; 1 = a requested gate failed;
2 = input discovery problem (protocol not frozen, results unparsable, ...).
Missing official outputs are never defaulted to 0 (protocol section 6).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
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
EXPERIMENT_ROOT = ROOT / "experiments/security-analysis-ablation-and-overhead"
EVAL_DIR = EXPERIMENT_ROOT / "evaluation/strict-atom-representation-attribution"
SOURCE_DIR = EXPERIMENT_ROOT / "source/strict-atom-representation-attribution"
RUNS_BASE = EXPERIMENT_ROOT / "runs/strict-atom-representation-attribution/qwen32"
RESULTS_DIR = EXPERIMENT_ROOT / "results/strict-atom-representation-attribution"

SCOPE_MANIFEST = {
    "smoke": ("smoke-subset.jsonl", 16),
    "full": ("all-official-cases.jsonl", 726),
    "stability": ("stability-subset.jsonl", 160),
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fail-fast finalize for the strict atom attribution protocol."
    )
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="fail (exit 1) unless every variant has every expected case exactly once",
    )
    parser.add_argument(
        "--require-paired",
        action="store_true",
        help="fail (exit 1) unless the four variants pair on identical case keys "
        "with consistent frozen-input hashes and pass integrity gates",
    )
    parser.add_argument("--scope", choices=("smoke", "full", "stability"), default="full")
    parser.add_argument("--repeat-index", type=int, default=0)
    parser.add_argument(
        "--runs-base",
        default=str(RUNS_BASE),
        help="base directory containing <variant>/repeat-<n>/paired-case-results.jsonl",
    )
    parser.add_argument("--output-dir", default=str(RESULTS_DIR))
    parser.add_argument("--bootstrap-n", type=int, default=None)
    parser.add_argument("--bootstrap-seed", type=int, default=None)
    return parser.parse_args(argv)


def rel_to_root(path: Path) -> str:
    """Best-effort path display relative to the workspace root."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_finalize_module() -> Any:
    path = SOURCE_DIR / "finalize.py"
    spec = importlib.util.spec_from_file_location("strict_attribution_finalize", path)
    assert spec is not None and spec.loader is not None, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["strict_attribution_finalize"] = module
    spec.loader.exec_module(module)
    return module


def load_expected_keys(scope: str) -> list[str]:
    manifest_name, expected_count = SCOPE_MANIFEST[scope]
    path = EVAL_DIR / manifest_name
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != expected_count:
        raise ValueError(
            f"{manifest_name}: expected {expected_count} cases, got {len(rows)}"
        )
    return [row["case_key"] for row in rows]


def run_dir(args: argparse.Namespace, variant: str) -> Path:
    return Path(args.runs_base) / variant / f"repeat-{args.repeat_index}"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_statistics_csv(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for control, comparison in sorted(report.get("paired_asr", {}).items()):
        rows.append(
            {
                "comparison": "asr",
                "reference": comparison.get("reference"),
                "control": control,
                "n_pairs": comparison.get("n_pairs"),
                "discordant_control_only": comparison.get("discordant_b_x_only"),
                "discordant_reference_only": comparison.get("discordant_c_y_only"),
                "observed_diff": None,
                "ci_lower": None,
                "ci_upper": None,
                "noninferior": None,
                "p_value": comparison.get("p_value"),
                "p_value_holm": comparison.get("p_value_holm"),
            }
        )
    for control, block in sorted(report.get("paired_utility", {}).items()):
        for metric in ("benign_utility", "attack_utility"):
            comparison = block.get(metric, {})
            rows.append(
                {
                    "comparison": metric,
                    "reference": "validated_atom_fields",
                    "control": control,
                    "n_pairs": comparison.get("n_pairs"),
                    "discordant_control_only": None,
                    "discordant_reference_only": None,
                    "observed_diff": comparison.get("observed_diff"),
                    "ci_lower": comparison.get("ci_lower"),
                    "ci_upper": comparison.get("ci_upper"),
                    "noninferior": comparison.get("noninferior"),
                    "p_value": None,
                    "p_value_holm": None,
                }
            )
    fieldnames = [
        "comparison",
        "reference",
        "control",
        "n_pairs",
        "discordant_control_only",
        "discordant_reference_only",
        "observed_diff",
        "ci_lower",
        "ci_upper",
        "noninferior",
        "p_value",
        "p_value_holm",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def collect_failure_examples(
    results_by_variant: dict[str, dict[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for variant, rows in results_by_variant.items():
        for key, row in rows.items():
            if row.get("runtime_error") or not row.get("run_completed"):
                examples.append(
                    {
                        "variant": variant,
                        "case_key": key,
                        "run_completed": row.get("run_completed"),
                        "scorer_completed": row.get("scorer_completed"),
                        "runtime_error": row.get("runtime_error"),
                        "suite": row.get("suite"),
                        "mode": row.get("mode"),
                    }
                )
    examples.sort(key=lambda item: (item["variant"], item["case_key"]))
    return examples


def _fmt(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def render_report_md(report: dict[str, Any]) -> str:
    lines = [
        "# Strict atom representation attribution — finalized report",
        "",
        f"- protocol_id: `{report.get('protocol_id')}`",
        f"- run_id: `{report.get('run_id')}`",
        f"- scope: `{report.get('scope')}`",
        f"- repeat_index: {report.get('repeat_index')}",
        f"- reference variant: `{report.get('reference_variant')}`",
        f"- expected cases: {report.get('expected_n_cases')}",
        f"- generated_at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Fail-fast gates",
        "",
        f"passed: **{report['fail_fast']['passed']}** "
        f"({report['fail_fast']['n_errors']} errors)",
        "",
    ]
    if report["fail_fast"]["errors"]:
        lines.append("Errors (truncated to 200):")
        lines.extend(f"- {error}" for error in report["fail_fast"]["errors"])
        lines.append("")
    lines += ["## Per-variant metrics", ""]
    lines.append(
        "| variant | n_cases | ASR | benign utility | attack utility | "
        "completeness | ALLOW | DENY | ABSTAIN | NEEDS_REPLAN | override |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for variant, metrics in sorted(report.get("per_variant_metrics", {}).items()):
        runtime = metrics.get("runtime", {})
        lines.append(
            "| {variant} | {n} | {asr} | {bu} | {au} | {comp} | {allow} | {deny} "
            "| {abstain} | {replan} | {override} |".format(
                variant=variant,
                n=metrics.get("n_cases"),
                asr=_fmt(metrics.get("asr")),
                bu=_fmt(metrics.get("benign_utility")),
                au=_fmt(metrics.get("attack_utility")),
                comp=_fmt(metrics.get("run_completeness")),
                allow=runtime.get("n_allow"),
                deny=runtime.get("n_deny"),
                abstain=runtime.get("n_abstain"),
                replan=runtime.get("n_needs_replan"),
                override=runtime.get("n_uncertainty_override"),
            )
        )
    lines += ["", "## Paired comparisons (V3 vs controls)", ""]
    for control, comparison in sorted(report.get("paired_asr", {}).items()):
        lines.append(
            "- ASR vs `{control}`: b={b}, c={c}, p={p}, p_holm={ph}".format(
                control=control,
                b=comparison.get("discordant_b_x_only"),
                c=comparison.get("discordant_c_y_only"),
                p=_fmt(comparison.get("p_value")),
                ph=_fmt(comparison.get("p_value_holm")),
            )
        )
    for control, block in sorted(report.get("paired_utility", {}).items()):
        for metric in ("benign_utility", "attack_utility"):
            comparison = block.get(metric, {})
            lines.append(
                "- {metric} vs `{control}`: diff={diff}, 95% CI [{lo}, {hi}], "
                "noninferior(-0.05)={ni}".format(
                    metric=metric,
                    control=control,
                    diff=_fmt(comparison.get("observed_diff")),
                    lo=_fmt(comparison.get("ci_lower")),
                    hi=_fmt(comparison.get("ci_upper")),
                    ni=comparison.get("noninferior"),
                )
            )
    lines.append("")
    lines.append(
        "NOTE: headline denominators are the full-protocol totals (ASR and attack "
        "utility / 629, benign utility / 97) per protocol section 7.1; smoke and "
        "stability scopes are wiring/stability checks and must not enter the paper."
    )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    finalize = load_finalize_module()

    protocol_path = EVAL_DIR / "protocol.json"
    if not protocol_path.exists():
        print(json.dumps({"status": "refused", "errors": ["protocol.json missing"]}))
        return 2
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol.get("status") != "protocol-frozen":
        print(
            json.dumps(
                {
                    "status": "refused",
                    "errors": [f"protocol status {protocol.get('status')!r}, not frozen"],
                }
            )
        )
        return 2
    protocol_id = sha256_of(protocol_path)[:16]

    discovery_errors: list[str] = []
    results_by_variant: dict[str, dict[str, dict[str, Any]]] = {}
    for variant in finalize.MAIN_VARIANTS:
        path = run_dir(args, variant) / "paired-case-results.jsonl"
        rows, errors = finalize.load_results_jsonl(path)
        if errors:
            discovery_errors.extend(errors)
        if rows:
            results_by_variant[variant] = rows

    try:
        expected_keys = load_expected_keys(args.scope)
    except (ValueError, FileNotFoundError, OSError) as exc:
        print(json.dumps({"status": "refused", "errors": [str(exc)]}))
        return 2

    if discovery_errors and args.require_complete:
        print(
            json.dumps(
                {"status": "failed", "stage": "discovery", "errors": discovery_errors},
                indent=2,
            )
        )
        return 1

    report = finalize.build_report(
        results_by_variant,
        expected_keys,
        protocol_id=protocol_id,
        run_id=f"qwen32/scope={args.scope}/repeat-{args.repeat_index}",
        repeat_index=args.repeat_index,
        bootstrap_n=args.bootstrap_n,
        bootstrap_seed=args.bootstrap_seed,
    )
    report["scope"] = args.scope
    report["runs_base"] = rel_to_root(Path(args.runs_base))

    completeness_gate = len(results_by_variant) == len(finalize.MAIN_VARIANTS) and all(
        not finalize.completeness_errors(
            results_by_variant.get(variant, {}), expected_keys, variant
        )
        for variant in finalize.MAIN_VARIANTS
    )
    pairing_gate = not finalize.pairing_errors(results_by_variant, expected_keys)
    hash_gate = not finalize.hash_consistency_errors(results_by_variant)
    integrity_gate = not any(
        finalize.integrity_errors(rows, variant)
        for variant, rows in results_by_variant.items()
    )

    output_dir = Path(args.output_dir)
    write_json(output_dir / "report.json", report)
    write_json(
        output_dir / "paired-statistics.json",
        {
            "paired_asr": report["paired_asr"],
            "paired_utility": report["paired_utility"],
            "bootstrap_defaults": {
                "n_boot": finalize.stats.BOOTSTRAP_N,
                "seed": finalize.stats.BOOTSTRAP_SEED,
                "ci_level": finalize.stats.CI_LEVEL,
            },
        },
    )
    write_statistics_csv(output_dir / "paired-statistics.csv", report)
    failure_examples = collect_failure_examples(results_by_variant)
    with (output_dir / "failure-examples.jsonl").open("w", encoding="utf-8") as handle:
        for example in failure_examples:
            handle.write(json.dumps(example, sort_keys=True) + "\n")
    (output_dir / "report.md").write_text(render_report_md(report), encoding="utf-8")

    complete_passed = completeness_gate and not discovery_errors
    paired_passed = (
        pairing_gate and hash_gate and integrity_gate and report["fail_fast"]["passed"]
    )
    gate_failed = False
    if args.require_complete and not complete_passed:
        gate_failed = True
    if args.require_paired and not paired_passed:
        gate_failed = True

    summary = {
        "status": "failed" if gate_failed else "passed",
        "scope": args.scope,
        "repeat_index": args.repeat_index,
        "protocol_id": protocol_id,
        "gates": {
            "require_complete": {
                "requested": args.require_complete,
                "passed": complete_passed,
            },
            "require_paired": {
                "requested": args.require_paired,
                "passed": paired_passed,
            },
        },
        "fail_fast_errors": report["fail_fast"]["n_errors"],
        "failure_examples": len(failure_examples),
        "outputs": {
            name: rel_to_root(output_dir / name)
            for name in (
                "report.json",
                "paired-statistics.json",
                "paired-statistics.csv",
                "failure-examples.jsonl",
                "report.md",
            )
        },
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if gate_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
