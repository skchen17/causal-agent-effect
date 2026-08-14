#!/usr/bin/env python3
"""Reproduce and validate the fixed DeepSeek guard-repair evidence.

This script does not invoke a model or rerun AgentDojo. It rebuilds analysis
reports from saved task logs, verifies the frozen C1f source hashes, and emits a
fail-fast reproduction status plus a compact final evidence report.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "paper").is_dir() and (parent / "experiments").is_dir()
)
SCRIPT_DIR = Path(__file__).resolve().parent
OUT = ROOT / "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard"
EVAL = ROOT / "experiments/intent-bound-runtime-guard/evaluation/counterfactual-atom-envelope-guard"
RUNS = ROOT / "experiments/intent-bound-runtime-guard/runs/counterfactual-atom-envelope-guard"
FREEZE = EVAL / "c1f_frozen_candidate_2026-08-08.json"

ANALYZERS = (
    ("analyze_deepseek_confirmation.py", 0),
    # The ladder returns 1 when its deliberately less-strict C1d candidate
    # fails the joint gate. Preserving that negative result is required.
    ("analyze_deepseek_guard_ladder.py", 2),
    ("analyze_deepseek_c1f_regression.py", 0),
    ("analyze_deepseek_strong_baselines.py", 0),
)

STATUS_SPECS = {
    "no_guard_attack": ("deepseek-confirmation-no_guard-attack-r1", 629),
    "c1b_attack": ("deepseek-confirmation-c1b-attack-r1", 629),
    "c1f_benign": ("deepseek-confirmation-c1f-benign-r1", 97),
    "c1f_attack": ("deepseek-confirmation-c1f-attack-r1", 629),
    "repeat_user_prompt_benign": (
        "deepseek-confirmation-repeat_user_prompt-benign-r1",
        97,
    ),
    "repeat_user_prompt_attack": (
        "deepseek-confirmation-repeat_user_prompt-attack-r1",
        629,
    ),
    "spotlighting_benign": ("deepseek-confirmation-spotlighting-benign-r1", 97),
    "spotlighting_attack": ("deepseek-confirmation-spotlighting-attack-r1", 629),
}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_analyzers() -> list[dict[str, Any]]:
    rows = []
    for name, expected_returncode in ANALYZERS:
        path = SCRIPT_DIR / name
        if not path.exists():
            raise FileNotFoundError(path)
        completed = subprocess.run(
            [sys.executable, str(path)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        rows.append(
            {
                "script": str(path.relative_to(ROOT)),
                "returncode": completed.returncode,
                "expected_returncode": expected_returncode,
                "stderr_tail": completed.stderr[-2000:],
            }
        )
        if completed.returncode != expected_returncode:
            raise RuntimeError(
                f"analysis returned an unexpected status: {name}\n"
                f"expected={expected_returncode}, observed={completed.returncode}\n"
                f"stdout:\n{completed.stdout[-4000:]}"
                f"\nstderr:\n{completed.stderr[-4000:]}"
            )
    return rows


def verify_freeze() -> list[dict[str, Any]]:
    frozen = read_json(FREEZE)
    rows = []
    for label, artifact in sorted(frozen["source_artifacts"].items()):
        path = ROOT / artifact["path"]
        if not path.exists():
            raise FileNotFoundError(path)
        observed = sha256(path)
        expected = artifact["sha256"]
        row = {
            "label": label,
            "path": artifact["path"],
            "expected_sha256": expected,
            "observed_sha256": observed,
            "matched": observed == expected,
        }
        rows.append(row)
        if not row["matched"]:
            raise RuntimeError(f"frozen source hash changed: {artifact['path']}")
    return rows


def verify_run_statuses() -> dict[str, Any]:
    rows = {}
    for label, (directory, expected) in STATUS_SPECS.items():
        path = RUNS / directory / "confirmation_status.json"
        data = read_json(path)
        metrics = data.get("metrics", {})
        row = {
            "path": str(path.relative_to(ROOT)),
            "status": data.get("status"),
            "expected_total": expected,
            "recorded_total": metrics.get("n"),
            "errors": metrics.get("errors"),
        }
        rows[label] = row
        if row["status"] != "passed":
            raise RuntimeError(f"run did not pass: {label}")
        if row["recorded_total"] != expected:
            raise RuntimeError(f"unexpected result count for {label}: {row}")
        if row["errors"] != 0:
            raise RuntimeError(f"run contains errors: {label}")
    return rows


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def build_final_report() -> dict[str, Any]:
    c1b = read_json(OUT / "deepseek_c1b_joint_confirmation.json")
    ladder = read_json(OUT / "deepseek_guard_ladder_confirmation.json")
    c1f = read_json(OUT / "deepseek_c1f_structured_provenance_regression.json")
    baselines = read_json(OUT / "deepseek_same_model_strong_baselines.json")

    require(c1b["joint_gate_passed"], "C1b joint gate did not pass")
    require(not ladder["joint_gate_passed"], "C1d negative result unexpectedly changed")
    require(c1f["joint_gate_passed"], "C1f joint gate did not pass")
    require(
        c1f["attack_audit"]["executed_without_allow"] == 0,
        "C1f contains execution without ALLOW",
    )
    require(c1f["attack_audit"]["runtime_llm_calls"] == 0, "C1f called an LLM at runtime")
    require(not baselines["sota_established"], "unsupported SOTA status")

    methods = baselines["methods"]
    c1f_official = methods["c1f"]["official_attack"]
    no_guard_official = methods["no_guard"]["official_attack"]
    spotlight_official = methods["spotlighting"]["official_attack"]
    return {
        "experiment": "DeepSeek counterfactual atom-envelope guard final evidence",
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "deepseek-v4-flash",
        "benchmark": "AgentDojo v1.1.2 sandbox",
        "selected_candidate": "C1f strict atom envelope with structured provenance",
        "candidate_ladder": {
            "c1b": {
                "role": "pre-repair confirmatory candidate",
                "joint_gate_passed": c1b["joint_gate_passed"],
                "official_attack_successes": c1b["attack"]["c1b_attack_successes"],
                "attack_utility": c1b["attack"]["c1b_attack_utility"],
            },
            "c1d": {
                "role": "less strict negative candidate",
                "joint_gate_passed": ladder["joint_gate_passed"],
                "official_attack_successes": ladder["c1d"]["attack"]["guard_attack_successes"],
                "attack_utility": ladder["c1d"]["attack"]["guard_attack_utility"],
                "failure": "role-sensitive relaxation admitted two official attack goals",
            },
            "c1f": {
                "role": "post-confirmation structured-provenance repair",
                "joint_gate_passed": c1f["joint_gate_passed"],
                "official_attack_successes": c1f_official["attack_successes"],
                "attack_utility": c1f_official["utility_successes"],
                "known_regression_excluded_from_confirmation": True,
            },
        },
        "benign_utility": {
            "no_guard_four_repetition_mean": methods["no_guard"]["benign"]["mean_utility"],
            "c1b_four_repetition_mean": c1b["benign"]["c1b_mean_utility"],
            "difference": c1b["benign"]["mean_difference"],
            "one_sided_clustered_lower_95": c1b["benign"]["cluster_bootstrap"][
                "one_sided_lower_95"
            ],
            "noninferiority_margin": c1b["benign"]["noninferiority_margin"],
            "noninferiority_passed": c1b["benign"]["noninferiority_passed"],
            "c1f_sanity_run": c1f["c1f_benign_sanity"]["utility_successes"],
            "c1f_sanity_denominator": c1f["c1f_benign_sanity"]["n"],
            "c1f_direct_denies": c1f["c1f_benign_sanity"]["audit"]["deny"],
            "c1f_direct_abstains": c1f["c1f_benign_sanity"]["audit"]["abstain"],
            "evidence_scope": (
                "The four-repetition non-inferiority test is C1b evidence. C1f has one "
                "benign sanity run and inherits the C1b path only because its sole change "
                "is structured untrusted-provenance extraction, absent on audited benign paths."
            ),
        },
        "security": {
            "official_n": c1f_official["n"],
            "no_guard_attack_successes": no_guard_official["attack_successes"],
            "c1f_attack_successes": c1f_official["attack_successes"],
            "official_result_role": (
                "Regression-inclusive descriptive comparison; it contains the known case "
                "used to develop the C1f structured-provenance repair."
            ),
            "post_repair_confirmation_n": c1f["post_repair_confirmation_keys"]["n"],
            "post_repair_no_guard_attack_successes": c1f[
                "post_repair_confirmation_keys"
            ]["no_guard_attack_successes"],
            "post_repair_c1f_attack_successes": c1f["post_repair_confirmation_keys"][
                "c1f_attack_successes"
            ],
            "scope_aligned_confirmation_n": c1f["scope_aligned_effectful_attack_keys"]["n"],
            "scope_aligned_no_guard_attack_successes": c1f[
                "scope_aligned_effectful_attack_keys"
            ]["no_guard_attack_successes"],
            "scope_aligned_c1f_attack_successes": c1f[
                "scope_aligned_effectful_attack_keys"
            ]["c1f_attack_successes"],
            "scope_aligned_exact_one_sided_mcnemar_p": c1f[
                "scope_aligned_effectful_attack_keys"
            ]["exact_mcnemar_one_sided_p"],
            "same_model_scope_diagnostic_n": methods["c1f"]["scope_aligned_attack"]["n"],
            "c1f_precommit_checks": c1f["attack_audit"]["precommit_checks"],
            "c1f_denies": c1f["attack_audit"]["deny"],
            "c1f_abstains": c1f["attack_audit"]["abstain"],
            "executed_without_allow": c1f["attack_audit"]["executed_without_allow"],
            "runtime_llm_calls": c1f["attack_audit"]["runtime_llm_calls"],
        },
        "same_model_baselines": {
            name: {
                "benign_utility": row["benign"]["mean_utility"],
                "attack_successes": row["official_attack"]["attack_successes"],
                "attack_n": row["official_attack"]["n"],
                "attack_utility": row["official_attack"]["utility_successes"],
            }
            for name, row in methods.items()
        },
        "comparative_interpretation": {
            "security": "C1f and spotlighting tie at zero official attack successes.",
            "utility": (
                f"C1f attack utility is {c1f_official['utility_successes']}/629; "
                f"spotlighting is {spotlight_official['utility_successes']}/629."
            ),
            "c1f_attack_utility_discordance": methods["c1f"][
                "paired_attack_utility_vs_no_guard"
            ],
            "distinct_evidence": (
                "C1f supplies deterministic precommit decisions and atom-level audit rows; "
                "the prompting baseline does not establish that mechanism."
            ),
            "sota_established": False,
        },
        "implementation_finding": (
            "The C1d failure exposed a concrete implementation bug: provenance extraction "
            "ignored structured Pydantic-like tool outputs. C1f traverses structured records "
            "before checking untrusted control influence."
        ),
        "claim_boundary": (
            "The evidence supports same-model AgentDojo sandbox security improvement. C1b "
            "passes four-run benign non-inferiority; C1f has a one-run benign sanity check "
            "and an explicit path-equivalence argument for its structured-provenance-only "
            "change. The evidence does not "
            "establish SOTA, adaptive-attack robustness, general trajectory safety, output-"
            "only protection, or production safety."
        ),
    }


def write_final_markdown(report: dict[str, Any]) -> None:
    benign = report["benign_utility"]
    security = report["security"]
    baselines = report["same_model_baselines"]
    lines = [
        "# Final DeepSeek Guard-Repair Evidence",
        "",
        "## Result",
        "",
        f"- Selected candidate: `{report['selected_candidate']}`.",
        f"- C1b benign non-inferiority: `{benign['noninferiority_passed']}`; four-run mean "
        f"difference `+{benign['difference']:.4f}`, one-sided clustered 95% lower bound "
        f"`{benign['one_sided_clustered_lower_95']:.4f}` against margin "
        f"`{benign['noninferiority_margin']:.2f}`.",
        f"- C1f benign sanity run: `{benign['c1f_sanity_run']}/{benign['c1f_sanity_denominator']}` "
        f"with `{benign['c1f_direct_denies']}` direct denies and "
        f"`{benign['c1f_direct_abstains']}` abstains.",
        f"- Regression-inclusive official-key comparison: no guard "
        f"`{security['no_guard_attack_successes']}/{security['official_n']}`, C1f "
        f"`{security['c1f_attack_successes']}/{security['official_n']}`.",
        f"- Post-repair confirmation excluding the known repair case: no guard "
        f"`{security['post_repair_no_guard_attack_successes']}/{security['post_repair_confirmation_n']}`, "
        f"C1f `{security['post_repair_c1f_attack_successes']}/{security['post_repair_confirmation_n']}`.",
        f"- Scope-aligned confirmation, also excluding 20 output-only goals: no guard "
        f"`{security['scope_aligned_no_guard_attack_successes']}/{security['scope_aligned_confirmation_n']}`, "
        f"C1f `{security['scope_aligned_c1f_attack_successes']}/{security['scope_aligned_confirmation_n']}`, "
        f"exact one-sided McNemar `p={security['scope_aligned_exact_one_sided_mcnemar_p']}`.",
        f"- Runtime audit: `{security['c1f_precommit_checks']}` checks, "
        f"`{security['c1f_denies']}` denies, `{security['c1f_abstains']}` abstains, "
        f"`{security['executed_without_allow']}` executions without ALLOW, and "
        f"`{security['runtime_llm_calls']}` runtime LLM calls.",
        "",
        "## Same-Model Comparison",
        "",
        "| Method | Benign utility | Attack success | Attack utility |",
        "|---|---:|---:|---:|",
    ]
    for name, row in baselines.items():
        lines.append(
            f"| `{name}` | {row['benign_utility']:.3f} | "
            f"{row['attack_successes']}/{row['attack_n']} | "
            f"{row['attack_utility']}/{row['attack_n']} |"
        )
    lines.extend(
        [
            "",
            "C1f and spotlighting tie on observed official attack success. Spotlighting has "
            "higher attack-task utility in this run. The C1f-specific evidence is its "
            "deterministic atom-level precommit mediation and complete audit trail, not a "
            "claim of numerical superiority over spotlighting.",
            "",
            f"The C1f/no-guard attack-utility difference is not a single block count: "
            f"`{report['comparative_interpretation']['c1f_attack_utility_discordance']['no_guard_only_successes']}` "
            f"tasks succeeded only without the guard and "
            f"`{report['comparative_interpretation']['c1f_attack_utility_discordance']['method_only_successes']}` "
            "succeeded only with C1f. This paired churn means the net difference cannot be "
            "attributed entirely to direct guard denials.",
            "",
            "## Candidate Ladder",
            "",
            "C1b passed the original joint gate. The less strict C1d variant increased "
            "attack-task utility but admitted two official attack goals and therefore failed "
            "the security gate. One failure exposed dropped provenance in a structured "
            "calendar output. C1f combines C1b's strict field treatment with structured-output "
            "provenance extraction. The known repair case is retained as regression evidence "
            "and excluded from post-repair confirmatory statistics.",
            "",
            "## Claim Boundary",
            "",
            report["claim_boundary"],
            "",
        ]
    )
    (OUT / "final_guard_repair_report_2026-08-08.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    analyzers = run_analyzers()
    hashes = verify_freeze()
    statuses = verify_run_statuses()
    final = build_final_report()
    final_path = OUT / "final_guard_repair_report_2026-08-08.json"
    final_path.write_text(json.dumps(final, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_final_markdown(final)

    status = {
        "experiment": "DeepSeek guard-repair saved-artifact reproduction",
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_calls": 0,
        "analyzers": analyzers,
        "frozen_source_hashes": hashes,
        "run_statuses": statuses,
        "required_reports": [
            str((OUT / name).relative_to(ROOT))
            for name in (
                "deepseek_c1b_joint_confirmation.json",
                "deepseek_guard_ladder_confirmation.json",
                "deepseek_c1f_structured_provenance_regression.json",
                "deepseek_same_model_strong_baselines.json",
                "final_guard_repair_report_2026-08-08.json",
            )
        ],
        "claim_boundary": final["claim_boundary"],
    }
    (OUT / "reproduction_status_2026-08-08.json").write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": status["status"], "final_report": str(final_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
