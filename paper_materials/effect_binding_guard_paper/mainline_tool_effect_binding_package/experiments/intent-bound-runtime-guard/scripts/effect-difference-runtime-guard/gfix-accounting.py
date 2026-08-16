"""Paired accounting + preregistered judgment for the generalized-fix (G') experiment.

Inputs (all preregistered paths):
  G' rep1/rep2 run dirs, N pilot record + N rep2 logdir,
  pilot paired accounting (G, N), preregistration JSON.

Judgment follows gfix_preregistration_2026-08-07.json judgment_criteria 1-5.
This script only reads; it never modifies any run directory.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RUNS = ROOT / "experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard"
EVAL = ROOT / "experiments/intent-bound-runtime-guard/evaluation/effect-difference-runtime-guard"
PILOT = RUNS / "recovery-normalization-qwen32-pilot-36-allow-with-trail-deepseek-iffix-20260807"

REP_DIRS = {
    "rep1": RUNS / "recovery-normalization-qwen32-pilot-36-allow-with-trail-deepseek-gfix-20260807-r1",
    "rep2": RUNS / "recovery-normalization-qwen32-pilot-36-allow-with-trail-deepseek-gfix-20260807-r2",
}
NREP2_LOGDIR = RUNS / "deepseek-noguard-rep2-20260807/agentdojo_logs/local"
DESCRIPTORS = ROOT / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/registered-effect-diff-descriptors.jsonl"


def msg_text(m):
    c = m.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(p.get("content", "") for p in c if isinstance(p, dict))
    return ""


def scan_benign_logdir(logdir: Path, cases: list[str]) -> dict[str, bool]:
    out = {}
    for case in cases:
        suite, task = case.split("/")
        p = logdir / suite / task / "none" / "none.json"
        if not p.exists():
            out[case] = False  # missing log counts as failure (fail-closed)
            continue
        d = json.loads(p.read_text())
        out[case] = bool(d.get("utility"))
    return out


def executed_effectful_calls(log_path: Path, effectful: set[str]) -> Counter:
    """Executed = a tool response message exists for the call (agentdojo log
    records a role='tool' message with the serialized tool_call)."""
    import ast

    d = json.loads(log_path.read_text())
    executed: Counter = Counter()
    for m in d["messages"]:
        if m.get("role") != "tool":
            continue
        raw_call = m.get("tool_call")
        fn = None
        if isinstance(raw_call, dict):
            fn = raw_call.get("function")
        elif isinstance(raw_call, str):
            try:
                fn = ast.literal_eval(raw_call).get("function")
            except (ValueError, SyntaxError, AttributeError):
                fn = None
        if isinstance(fn, str) and fn in effectful:
            executed[fn] += 1
    return executed


def audit_allow_counts(audit_path: Path) -> dict[str, Counter]:
    """query_hash -> Counter(tool_name) of ALLOW precommit checks."""
    allows: dict[str, Counter] = {}
    for line in audit_path.open():
        d = json.loads(line)
        if d.get("event") == "precommit_check" and d.get("decision") == "ALLOW":
            allows.setdefault(d["query_hash"], Counter())[d["tool_name"]] += 1
    return allows


def reconcile(rep_dir: Path, cases: list[str], task_text: dict[str, str], effectful: set[str]) -> dict:
    """Authoritative reconciliation (same criterion as the pilot report):
    every execution_attempted=True precommit_check event must carry decision
    ALLOW. Cross-check: executed effectful calls observed in the logs must be
    covered by ALLOW checks for the same case/tool."""
    h2c = {hashlib.sha256(t.encode()).hexdigest(): c for c, t in task_text.items()}
    attempted = 0
    attempted_without_allow = []
    allows: dict[str, Counter] = {}
    for line in (rep_dir / "runtime_audit.jsonl").open():
        d = json.loads(line)
        if d.get("event") != "precommit_check":
            continue
        if d.get("decision") == "ALLOW":
            allows.setdefault(d["query_hash"], Counter())[d["tool_name"]] += 1
        if d.get("execution_attempted"):
            attempted += 1
            if d.get("decision") != "ALLOW":
                attempted_without_allow.append(
                    {"case": h2c.get(d["query_hash"], "<unmapped>"), "tool": d.get("tool_name"), "decision": d.get("decision")}
                )
    log_coverage = []
    for case in cases:
        suite, task = case.split("/")
        p = rep_dir / "agentdojo_logs" / "local-ours_e77_effect_diff_runtime" / suite / task / "none" / "none.json"
        if not p.exists():
            continue
        executed = executed_effectful_calls(p, effectful)
        qh = hashlib.sha256(task_text[case].encode()).hexdigest()
        allowed = allows.get(qh, Counter())
        for tool_name, count in executed.items():
            if allowed.get(tool_name, 0) < count:
                log_coverage.append({"case": case, "tool": tool_name, "executed": count, "allow_checks": allowed.get(tool_name, 0)})
    return {
        "executed_attempted_checks_total": attempted,
        "attempted_without_allow": len(attempted_without_allow),
        "attempted_without_allow_detail": attempted_without_allow,
        "log_coverage_gaps": log_coverage,
        "passed": not attempted_without_allow,
    }


def revision_mechanics(rep_dir: Path) -> dict:
    """M4 mechanism observables: revision events, raw_output prefixes, repair counts."""
    out = {"revision_events": 0, "revision_invalid": 0, "repair_attempted_events": 0}
    raw_prefixes: Counter = Counter()
    repair_counts: Counter = Counter()
    cache_path = rep_dir / "plan_cache.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    for entry in cache.values():
        diag = entry.get("diagnostic", {})
        if "revision_parse_errors" in diag or entry.get("revision") is not None:
            raw_prefixes[diag.get("raw_output_prefix", "")[:2] or "<empty>"] += 1
            if "repair_attempts" in diag:
                repair_counts[diag.get("repair_attempts", 0)] += 1
                if diag.get("repair_attempted"):
                    out["repair_attempted_events"] += 1
    for line in (rep_dir / "runtime_audit.jsonl").open():
        d = json.loads(line)
        if d.get("event") == "plan_revision":
            out["revision_events"] += 1
            if d.get("recovery_state") == "REVISION_INVALID":
                out["revision_invalid"] += 1
    out["cache_revision_raw_prefix_distribution"] = dict(raw_prefixes)
    out["cache_revision_repair_attempts_distribution"] = {str(k): v for k, v in sorted(repair_counts.items())}
    out["revision_not_object_rate"] = (
        out["revision_invalid"] / out["revision_events"] if out["revision_events"] else None
    )
    return out


def main() -> int:
    prereg = json.loads((EVAL / "gfix_preregistration_2026-08-07.json").read_text())
    cases = sorted(set(prereg["manifest_case_lists"]["control"]) | set(prereg["manifest_case_lists"]["target"]))
    control = set(prereg["manifest_case_lists"]["control"])
    whitelist = set(prereg["whitelist"]["union_flip_candidates"])

    pilot = json.loads((PILOT / "paired_accounting_deepseek_pilot.json").read_text())
    G_pilot, N_pilot = pilot["G"], pilot["N"]
    n_record = json.loads((PILOT / "condition_N_execution_record.json").read_text())
    assert n_record["n_utility_true"] == sum(N_pilot.values())

    # task text for reconciliation mapping (from pilot G logs, identical tasks)
    task_text = {}
    for case in cases:
        suite, task = case.split("/")
        d = json.loads((PILOT / "agentdojo_logs/local-ours_e77_effect_diff_runtime" / suite / task / "none" / "none.json").read_text())
        users = [m for m in d["messages"] if m.get("role") == "user"]
        task_text[case] = msg_text(users[0])

    effectful = {json.loads(l)["tool_name"] for l in DESCRIPTORS.open()}

    results: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "preregistration_sha256": hashlib.sha256((EVAL / "gfix_preregistration_2026-08-07.json").read_bytes()).hexdigest(),
    }

    gprime: dict[str, dict[str, bool]] = {}
    recon: dict[str, dict] = {}
    mechanics: dict[str, dict] = {}
    for rep, rep_dir in REP_DIRS.items():
        gprime[rep] = scan_benign_logdir(rep_dir / "agentdojo_logs" / "local-ours_e77_effect_diff_runtime", cases)
        recon[rep] = reconcile(rep_dir, cases, task_text, effectful)
        mechanics[rep] = revision_mechanics(rep_dir)
    results["Gprime"] = {rep: {"n_true": sum(v.values()), "per_case": v} for rep, v in gprime.items()}
    results["reconciliation"] = recon
    results["revision_mechanics"] = mechanics

    n_rep2 = scan_benign_logdir(NREP2_LOGDIR, cases)
    results["N"] = {
        "pilot": {"n_true": sum(N_pilot.values()), "source": str(PILOT.name)},
        "rep2": {"n_true": sum(n_rep2.values()), "per_case": n_rep2},
        "mean_n_true": (sum(N_pilot.values()) + sum(n_rep2.values())) / 2,
    }

    # primary metric
    mean_gprime = sum(sum(gprime[rep].values()) for rep in gprime) / len(gprime)
    mean_n = results["N"]["mean_n_true"]
    diff = mean_gprime - mean_n
    baseline_diff = sum(G_pilot.values()) - sum(N_pilot.values())
    noise_band = prereg["noise_band"]["value"]
    results["primary_metric"] = {
        "mean_Gprime": mean_gprime,
        "mean_N": mean_n,
        "mean_Gprime_minus_N": diff,
        "baseline_G_minus_N_pilot": baseline_diff,
        "noise_band": noise_band,
        "delta_from_baseline": abs(diff - baseline_diff),
        "noise_verdict": (
            "INCONCLUSIVE_NOISE_BAND"
            if abs(diff - baseline_diff) < noise_band
            else ("OUTSIDE_NOISE_BAND_GAIN" if diff > baseline_diff else "OUTSIDE_NOISE_BAND_LOSS")
        ),
    }

    # criterion 2: control retention in both reps
    control_regressions = {
        rep: sorted(c for c in control if not gprime[rep][c]) for rep in gprime
    }
    results["control_retention"] = {
        "per_rep_regressions": control_regressions,
        "passed": all(not v for v in control_regressions.values()),
    }

    # criterion 1: whitelist attribution (per rep; flip = G' success where pilot G failed and pilot N succeeded)
    attribution = {}
    for rep in gprime:
        flips = sorted(
            c for c in cases
            if gprime[rep][c] and not G_pilot[c] and N_pilot[c]
        )
        outside = sorted(c for c in flips if c not in whitelist)
        attribution[rep] = {
            "flips_fail_to_pass_vs_pilotG": flips,
            "inside_whitelist": sorted(c for c in flips if c in whitelist),
            "outside_whitelist": outside,
            "passed": not outside,
        }
        # also record whitelist cases that did NOT flip (mechanism evidence)
        attribution[rep]["whitelist_not_flipped"] = sorted(
            c for c in whitelist if not G_pilot[c] and not gprime[rep][c]
        )
    results["whitelist_attribution"] = attribution

    # overall judgment
    judgments = {
        "criterion1_whitelist_attribution": all(attribution[r]["passed"] for r in attribution),
        "criterion2_control_retention": results["control_retention"]["passed"],
        "criterion3_noise_band": results["primary_metric"]["noise_verdict"],
        "criterion4_reconciliation": all(recon[r]["passed"] for r in recon),
        "criterion5_m4_mechanism": mechanics,
    }
    results["judgment"] = judgments
    out_path = ROOT / "audit/gfix-20260807/gfix_accounting_2026-08-07.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(
        {
            "primary_metric": results["primary_metric"],
            "control_retention": results["control_retention"]["passed"],
            "reconciliation": {r: recon[r]["passed"] for r in recon},
            "attribution_outside_whitelist": {r: attribution[r]["outside_whitelist"] for r in attribution},
            "written": str(out_path),
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
