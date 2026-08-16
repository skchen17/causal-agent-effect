"""Decompose the 37 frozen E78 benign losses into engineering-recoverable and
theory-adjacent strata, and bound the achievable benign utility under
systematic relation onboarding plus planner-construction repair.

Deterministic post-hoc analysis of frozen artifacts only: no model calls, no
tool executions, no relabeling of official AgentDojo utility.

Inputs (frozen):
- headline-benign-utility-pathway-audit-cases.csv  (97 capacity-matched cases)
- registered-relation-benign-pilot-v8.json         (16-case frozen pilot)

Strata:
- N_noise: no runtime feedback; loss is model/scoring variation (E84-audit
  pattern), not guard-caused. Treated as symmetric rerun variance.
- ER_relation: a resolver value was literally present in an earlier trusted
  tool result (literal-probe stratum). Split by v8 pilot outcome into
  recovered / runtime-relation-registration-needed / plan-construction-needed.
- EP_planner_construction: only plan parse or tool-coverage findings; planner
  robustness engineering (normalization + bounded repair) is the target.
- A_authority_judgment / A_exact_mismatch: forbidden-field or exact-value
  divergence; mixed stratum containing planner misjudgment and true intent
  ambiguity. Only partially engineering-addressable.
- EB_resolver_no_literal: resolver fill whose value never appears literally in
  trusted context; requires semantic transformation and is theory-adjacent.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[2] / "results" / "headline-benign-utility-pathway-audit"
CONTROLS = {
    "banking/user_task_10",
    "slack/user_task_0",
    "travel/user_task_10",
    "workspace/user_task_1",
}

# Per-stratum recovery-rate assumptions for the ceiling scenarios. These are
# planning assumptions, not measured outcomes; the frozen expanded pilot must
# replace them before any paper claim.
SCENARIOS = {
    "conservative": {"ER": 0.55, "EP": 0.50, "EB": 0.00, "A": 0.00},
    "realistic": {"ER": 0.75, "EP": 0.60, "EB": 0.50, "A": 0.15},
    "optimistic": {"ER": 0.92, "EP": 0.80, "EB": 0.66, "A": 0.43},
}


def main() -> None:
    with open(RESULTS / "headline-benign-utility-pathway-audit-cases.csv") as f:
        rows = list(csv.DictReader(f))
    losses = [r for r in rows if r["utility_transition"] == "1->0"]

    v8 = json.loads((RESULTS / "registered-relation-benign-pilot-v8.json").read_text())
    literal12 = {c["case_key"] for c in v8["cases"]} - CONTROLS
    anatomy = v8["failure_anatomy"]
    runtime_rel_fail = set(anatomy["runtime_relation_failure_cases"])
    plan_con_fail = set(anatomy["plan_construction_failure_cases"])
    recovered_v8 = literal12 - runtime_rel_fail - plan_con_fail

    def classify(row: dict) -> str:
        key = row["case_key"]
        codes = set(row["feedback_reason_codes"].split(";")) if row["feedback_reason_codes"] else set()
        if row["observed_pathway"].startswith("no_runtime_feedback"):
            return "N_noise"
        if key in literal12:
            if key in recovered_v8:
                return "ER_relation_recovered_v8"
            if key in plan_con_fail:
                return "ER_relation_planfix_needed"
            return "ER_relation_register_needed"
        if codes <= {"task_permission_plan_parse_failed", "tool_not_in_initial_permission_plan"}:
            return "EP_planner_construction"
        if "forbidden_field_used" in codes:
            return "A_authority_judgment"
        if "outside_exact_plan" in codes and "resolver_fill_requires_replan" not in codes:
            return "A_exact_mismatch"
        return "EB_resolver_no_literal"

    assignment = {r["case_key"]: classify(r) for r in losses}
    counts = Counter(assignment.values())

    base = sum(1 for r in rows if r["ours_utility"] == "True")
    er = sum(v for k, v in counts.items() if k.startswith("ER_"))
    ep = counts.get("EP_planner_construction", 0)
    eb = counts.get("EB_resolver_no_literal", 0)
    ambiguous = sum(v for k, v in counts.items() if k.startswith("A_"))
    noise = counts.get("N_noise", 0)

    ceilings = {
        name: base + int(er * w["ER"]) + int(ep * w["EP"]) + int(eb * w["EB"]) + int(ambiguous * w["A"])
        for name, w in SCENARIOS.items()
    }

    report = {
        "experiment": "engineering-recovery-ceiling-decomposition",
        "status": "deterministic_frozen_log_analysis",
        "denominator": len(rows),
        "guard_baseline_successes": base,
        "loss_count": len(losses),
        "strata_counts": dict(sorted(counts.items())),
        "strata_cases": {
            c: sorted(k for k, v in assignment.items() if v == c) for c in sorted(counts)
        },
        "aggregates": {
            "engineering_relation_ER": er,
            "engineering_planner_EP": ep,
            "resolver_no_literal_EB": eb,
            "ambiguous_or_authority_A": ambiguous,
            "noise_N": noise,
        },
        "scenario_assumptions": SCENARIOS,
        "recovery_ceilings_of_97": ceilings,
        "claim_boundary": (
            "Deterministic reclassification of frozen E78 logs using the "
            "literal-grounding probe and v8 pilot outcomes. Scenario recovery "
            "rates are planning assumptions, not measurements. Noise cases are "
            "symmetric rerun variance, not recoverable engineering targets. "
            "Official utility labels are unchanged; no model or tool ran."
        ),
    }

    out = RESULTS / "engineering-recovery-ceiling-decomposition.json"
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps(report["recovery_ceilings_of_97"], indent=1))
    print(f"written: {out}")


if __name__ == "__main__":
    main()
