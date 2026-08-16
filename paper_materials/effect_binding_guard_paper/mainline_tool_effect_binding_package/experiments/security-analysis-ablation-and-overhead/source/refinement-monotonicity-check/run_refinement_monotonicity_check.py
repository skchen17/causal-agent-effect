#!/usr/bin/env python3
"""T1: refinement monotonicity and bounded-termination trajectory check.

Instantiates the T1 theorem draft (registered-refinement monotonic
termination) on the frozen 56-call AgentDojo finite domain. The authority
family and the separating-pair/representation-signature decision procedure are
those of E2 (policy-family-sensitivity), so the trajectory computed here is
comparable with the E2 grid row-by-row.

Inputs (read-only, frozen):
  - experiments/human-authority-and-causal-validation/results/
      finite-domain-effect-binding-validation/finite-contexts.jsonl
  - experiments/human-authority-and-causal-validation/results/
      finite-domain-effect-binding-validation/finite-domain-validation-report.json
      (baseline separating-pair counts for cross-checks)

What is checked
  1. Lattice construction.  A refinement lattice is generated over the subset
     lattice of the five typed qualifier roles (date/subject/recurrence/
     payload/visibility): representation rho_K keeps exactly the qualifier
     roles in K and erases the rest using the E2 deletion operations.  K=() is
     the coarse end (no qualifier, expected to reproduce the frozen common-
     contract baseline of 118 separating pairs); K=(all) is the reviewed typed
     contract (zero separating pairs).
  2. Order preservation (T1(a)).  For every edge K ⊂ K' of the subset lattice:
     (i)  rho_{K'} refines rho_K: equal fine signatures imply equal coarse
          signatures on every context pair (cell nesting);
     (ii) separating pairs are monotone non-increasing along the edge
          (instance of Prop. Trusted evidence refinement);
     (iii) ambiguous-cell authorized-member lower bound is monotone
          non-increasing (instance of Prop. Ambiguous-cell lower bound).
  3. Termination (T1(b)).  A deterministic 5-step trajectory adds one qualifier
     role per step from () to (all).  The script reports, per step, the number
     of representation cells, separating pairs, mixed cells, and the
     ambiguous-cell lower bound, and asserts trajectory length <= |D|-1
     (partition lattice bound) and arrival at a fixed point (zero separating
     pairs, i.e. authorization sufficiency on D).
  4. Collision-count monotonicity (T1(c)).  Separating-pair count and the
     ambiguous-cell lower bound are both non-increasing along the trajectory
     and along every lattice edge, consistent with the Ambiguous-cell lower
     bound.
  5. E2 cross-checks.  Single-qualifier deletions from the typed contract must
     reproduce the E2 power-set grid values (16/16/16/8/4 separating pairs),
     and the erased end must reproduce the frozen common-contract baseline.

Deterministic, CPU-only, stdlib-only.  No input file is modified.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import platform
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]

AGENTDOJO_CONTEXTS = (
    ROOT
    / "experiments/human-authority-and-causal-validation/results/"
    "finite-domain-effect-binding-validation/finite-contexts.jsonl"
)
AGENTDOJO_BASELINE_REPORT = (
    ROOT
    / "experiments/human-authority-and-causal-validation/results/"
    "finite-domain-effect-binding-validation/finite-domain-validation-report.json"
)
RESULTS = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "refinement-monotonicity-check"
)
REPORT_JSON = RESULTS / "refinement-monotonicity-report.json"
REPORT_MD = RESULTS / "refinement-monotonicity-report.md"

QUALIFIERS: tuple[str, ...] = ("date", "subject", "recurrence", "payload", "visibility")
# Deterministic coarse-to-fine addition order for the recorded trajectory.
TRAJECTORY_ORDER: tuple[str, ...] = QUALIFIERS

DELETED_FIELD_MARKER = "__DELETED__"
MASKED_PAYLOAD_RESOURCE = "payload:*"

# E2 power-set grid values (agentdojo_finite_domain): deleting exactly one
# qualifier role from the typed contract creates this many separating pairs.
E2_POWER_SET_DELETION_EXPECTED: dict[str, int] = {
    "date": 16,
    "subject": 16,
    "recurrence": 16,
    "payload": 8,
    "visibility": 4,
}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# ---------------------------------------------------------------------------
# Domain adapter (AgentDojo 56-call finite domain, frozen, read-only)
# ---------------------------------------------------------------------------


def load_agentdojo_contexts() -> list[dict[str, Any]]:
    contexts = []
    for row in read_jsonl(AGENTDOJO_CONTEXTS):
        contexts.append(
            {
                "context_id": row["context_id"],
                "tool_instance_key": row["tool_instance_key"],
                "effects": row["source_effects"],
                # Authorization-family signature: the power-set family's
                # projection of the source-effect multiset (same decision
                # procedure as E2).  Two contexts with equal family signatures
                # are authorization-equivalent under the declared family.
                "family_signature": canonical(row["source_effects"]),
                "typed_atoms": row["representations"]["reviewed_typed_contract"],
            }
        )
    return contexts


# ---------------------------------------------------------------------------
# Representation lattice over qualifier-role subsets
# ---------------------------------------------------------------------------


def atom_after_deletion(atom: dict[str, Any], qualifier: str) -> dict[str, Any]:
    """E2 deletion operation (kept verbatim for comparability)."""
    result = copy.deepcopy(atom)
    if qualifier == "visibility":
        result["visibility"] = DELETED_FIELD_MARKER
        return result
    qualifier_drops: dict[str, set[str]] = {
        "date": {"date"},
        "subject": {"subject"},
        "recurrence": {"recurring"},
        "payload": {"content", "filename"},
    }
    drops = qualifier_drops.get(qualifier, set())
    if drops and result.get("qualifiers"):
        for key in drops:
            result["qualifiers"].pop(key, None)
    if qualifier == "payload" and isinstance(result.get("resource"), str):
        if result["resource"].startswith("payload:"):
            result["resource"] = MASKED_PAYLOAD_RESOURCE
    return result


def representation_with_kept(
    atoms: list[dict[str, Any]], kept: frozenset[str]
) -> list[dict[str, Any]]:
    """Keep exactly the qualifier roles in `kept`, erase the rest.

    Erasing is applied per role with the E2 deletion operations; the per-role
    operations touch disjoint fields and are idempotent, so the result is
    independent of application order.
    """
    result = copy.deepcopy(atoms)
    for qualifier in QUALIFIERS:
        if qualifier not in kept:
            result = [atom_after_deletion(atom, qualifier) for atom in result]
    return sorted(result, key=canonical)


def representation_signatures(
    contexts: list[dict[str, Any]], kept: frozenset[str]
) -> dict[str, str]:
    return {
        context["context_id"]: canonical(
            representation_with_kept(context["typed_atoms"], kept)
        )
        for context in contexts
    }


def common_contract_signatures(contexts: list[dict[str, Any]]) -> dict[str, str]:
    """E2 common-contract semantics: strip the entire qualifiers key.

    Used only as an independent frozen-baseline reproduction check (the E2
    run_validations path); it is deliberately not a lattice vertex, whose
    erased end additionally applies the E2 visibility/payload deletion
    operations.
    """
    return {
        context["context_id"]: canonical(
            sorted(
                (
                    {k: v for k, v in atom.items() if k != "qualifiers"}
                    for atom in context["typed_atoms"]
                ),
                key=canonical,
            )
        )
        for context in contexts
    }


def cell_metrics(
    contexts: list[dict[str, Any]], kept: frozenset[str]
) -> dict[str, Any]:
    """Separating pairs, cells, mixed cells, and the ambiguous-cell lower bound.

    Separating pair: equal representation signature, different family
    signature (authorization-separating collision under the power-set family).
    Ambiguous-cell lower bound: sum over representation cells of
    (cell size - largest family-class size); the minimum number of authorized
    members a sound monitor must withhold from mixed cells.  This is the
    cell-count counterpart of Prop. Ambiguous-cell lower bound.
    """
    rep = representation_signatures(contexts, kept)
    cells: dict[str, list[str]] = defaultdict(list)
    for context in contexts:
        cells[rep[context["context_id"]]].append(context["context_id"])

    family = {context["context_id"]: context["family_signature"] for context in contexts}

    separating_pairs = 0
    mixed_cells = 0
    ambiguous_lower_bound = 0
    for members in cells.values():
        if len(members) < 2:
            continue
        class_sizes: dict[str, int] = defaultdict(int)
        for member in members:
            class_sizes[family[member]] += 1
        if len(class_sizes) > 1:
            mixed_cells += 1
        ambiguous_lower_bound += len(members) - max(class_sizes.values())
        for left, right in itertools.combinations(members, 2):
            if family[left] != family[right]:
                separating_pairs += 1

    return {
        "kept": sorted(kept),
        "representation_cells": len(cells),
        "separating_pairs": separating_pairs,
        "mixed_cells": mixed_cells,
        "ambiguous_cell_lower_bound": ambiguous_lower_bound,
    }


def refinement_edge_check(
    contexts: list[dict[str, Any]],
    coarse: frozenset[str],
    fine: frozenset[str],
) -> dict[str, Any]:
    """Verify rho_fine refines rho_coarse on every context pair."""
    coarse_rep = representation_signatures(contexts, coarse)
    fine_rep = representation_signatures(contexts, fine)
    violations = []
    for left, right in itertools.combinations(contexts, 2):
        if fine_rep[left["context_id"]] == fine_rep[right["context_id"]]:
            if (
                coarse_rep[left["context_id"]]
                != coarse_rep[right["context_id"]]
            ):
                violations.append(
                    [left["context_id"], right["context_id"]]
                )
    return {
        "coarse": sorted(coarse),
        "fine": sorted(fine),
        "refinement_violations": violations,
        "is_refinement": not violations,
    }


# ---------------------------------------------------------------------------
# Cross-checks against frozen baselines
# ---------------------------------------------------------------------------


def read_baseline_separating_pairs(report_path: Path, representation: str) -> int:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    for row in report["representations"]:
        if row["representation"] == representation:
            return row["authorization_separating_pairs"]
    raise KeyError(f"{representation} missing from {report_path.name}")


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# T1 Refinement-Monotonicity Trajectory Check Report",
        "",
        "## Runbook",
        "",
        f"- Script: `{report['script']}`",
        "- Command: `python3 experiments/security-analysis-ablation-and-overhead/"
        "source/refinement-monotonicity-check/run_refinement_monotonicity_check.py`",
        "- Inputs (read-only, frozen):",
        f"  - `{report['inputs']['contexts']['path']}` (sha256 "
        f"`{report['inputs']['contexts']['sha256'][:16]}...`), "
        f"{report['inputs']['contexts']['n_contexts']} contexts",
        f"  - `{report['inputs']['baseline_report']['path']}`",
        "- Dependencies: Python standard library only; CPU-only; no network.",
        f"- Python: {report['environment']['python']}",
        "",
        "## Definitions",
        "",
        "- Refinement lattice: representation $\\\\rho_K$ keeps exactly the "
        "qualifier roles in $K\\\\subseteq"
        "\\{\\textsf{date},\\textsf{subject},\\textsf{recurrence},"
        "\\textsf{payload},\\textsf{visibility}\\}$ and erases the rest "
        "with the E2 deletion operations. The lattice is the subset lattice "
        "of the five roles (32 vertices, ordered by inclusion).",
        "- Separating pairs: context pairs with identical representation "
        "signature and different authority-family signatures (same decision "
        "procedure as E2 under the power-set family).",
        "- Order preservation (T1(a)): $\\\\rho_{K'}$ refines $\\\\rho_K$ "
        "when $K'\\supset K$ (fine equality implies coarse equality on every "
        "pair), and separating pairs are monotone non-increasing along every "
        "lattice edge.",
        "- Termination (T1(b)): the recorded coarse-to-fine trajectory has "
        "bounded length $\\leq |D|-1$ and reaches a fixed point (zero "
        "separating pairs).",
        "- Collision monotonicity (T1(c)): separating-pair count and the "
        "ambiguous-cell lower bound are non-increasing along the trajectory.",
        "- Ambiguous-cell lower bound: $\\\\sum_{\\\\text{cells}}"
        "(|\\text{cell}|-\\max_{\\\\text{class}}|\\text{cell}\\cap"
        "\\text{class}|)$, the minimum number of authorized members a sound "
        "monitor must withhold from mixed representation cells.",
        "",
        "## Domain",
        "",
        f"- {report['domain']['name']}: {report['domain']['n_contexts']} "
        "contexts; frozen input hash recorded above.",
        "",
        "## Baseline cross-checks",
        "",
        "Representation-semantics note: the lattice erased end $\\rho_{\\emptyset}$ "
        "applies all five E2 deletion operations (qualifier sub-keys dropped, "
        "payload resource masked, visibility set to a constant), whereas the "
        "E2 common-contract baseline strips only the entire qualifiers key. "
        "These are two different coarse representations; both converge to the "
        "same typed end. The script therefore reproduces the common baseline "
        "independently (below) rather than conflating it with a lattice vertex.",
        "",
        "| Check | Observed | Expected | Passed |",
        "|---|---|---|:---:|",
    ]
    for row in report["validations"]:
        lines.append(
            f"| {row['check']} | {row['observed']} | {row['expected']} | "
            f"{'yes' if row['passed'] else 'no'} |"
        )
    lines.append("")

    lines.extend(
        [
            "## Recorded refinement trajectory (coarse to fine, 5 steps)",
            "",
            "| Step | Qualifier added | Rep cells | Separating pairs | "
            "Mixed cells | Ambiguous-cell LB | Strict |",
            "|---|---|---:|---:|---:|---:|:---:|",
        ]
    )
    for row in report["trajectory"]:
        lines.append(
            f"| {row['step']} | {row['added'] or '(baseline)'} | "
            f"{row['representation_cells']} | {row['separating_pairs']} | "
            f"{row['mixed_cells']} | {row['ambiguous_cell_lower_bound']} | "
            f"{'yes' if row['strict_improvement'] else 'no'} |"
        )
    lines.append("")
    lines.extend(
        [
            "## Trajectory assertions (T1(a) order preservation along the trajectory)",
            "",
            "| Step | Refinement holds | SP non-increasing | Cells non-decreasing |",
            "|---|---|---:|---:|",
        ]
    )
    for row in report["trajectory_assertions"]:
        lines.append(
            f"| {row['step']} | "
            f"{'yes' if row['refinement_holds'] else 'no'} | "
            f"{'yes' if row['sp_monotone'] else 'no'} | "
            f"{'yes' if row['cells_monotone'] else 'no'} |"
        )
    lines.append("")

    lattice = report["lattice"]
    lines.extend(
        [
            "## Full-lattice edge checks (T1(a) on every subset-lattice edge)",
            "",
            f"- Vertices: {lattice['vertices']} (all subsets of the five "
            "qualifier roles).",
            f"- Comparable pairs checked: {lattice['comparable_pairs']}.",
            f"- Refinement violations: {lattice['refinement_violations']} "
            "(expect 0).",
            f"- Edges with non-monotone separating pairs: "
            f"{lattice['sp_monotone_violations']} (expect 0).",
            f"- Edges with non-monotone ambiguous-cell lower bound: "
            f"{lattice['lb_monotone_violations']} (expect 0).",
            "",
        ]
    )

    termination = report["termination"]
    lines.extend(
        [
            "## Termination (T1(b))",
            "",
            f"- Trajectory length: {termination['trajectory_length']} "
            f"(bound |D|-1 = {termination['partition_bound']}).",
            f"- Length within bound: "
            f"{'yes' if termination['within_bound'] else 'no'}.",
            f"- Fixed point reached (zero separating pairs): "
            f"{'yes' if termination['fixed_point_reached'] else 'no'}.",
            f"- Cycle-free: {'yes' if termination['cycle_free'] else 'no'} "
            "(each subset vertex visited at most once).",
            "",
            "## Collision monotonicity (T1(c))",
            "",
            f"- Separating pairs non-increasing along trajectory: "
            f"{'yes' if report['collision_monotonicity']['sp_trajectory'] else 'no'}.",
            f"- Ambiguous-cell lower bound non-increasing along trajectory: "
            f"{'yes' if report['collision_monotonicity']['lb_trajectory'] else 'no'}.",
            "",
            "## E2 cross-checks",
            "",
            "| Single-role deletion from typed contract | Observed SP | "
            "E2 power-set grid SP | Passed |",
            "|---|---|---|:---:|",
        ]
    )
    for row in report["e2_cross_checks"]:
        lines.append(
            f"| {row['role']} | {row['observed']} | {row['expected']} | "
            f"{'yes' if row['passed'] else 'no'} |"
        )
    lines.append("")

    lines.extend(
        [
            "## Conclusion",
            "",
            f"Status: `{report['status']}`.",
            "",
            "Interpretation: on the frozen 56-call domain, the lattice "
            "instantiation satisfies order preservation, bounded "
            "termination, and collision-count monotonicity. This is an "
            "execution-grounded instance of the T1 theorem draft; it is not "
            "an open-domain certificate. The trajectory is policy-relative "
            "(power-set authority family, E2 decision procedure, frozen "
            "oracle).",
            "",
        ]
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run() -> dict[str, Any]:
    contexts = load_agentdojo_contexts()
    if len(contexts) != 56:
        raise ValueError("AgentDojo frozen domain must contain 56 contexts")

    baseline_common = read_baseline_separating_pairs(
        AGENTDOJO_BASELINE_REPORT, "reviewed_common_contract"
    )
    baseline_typed = read_baseline_separating_pairs(
        AGENTDOJO_BASELINE_REPORT, "reviewed_typed_contract"
    )

    all_roles = frozenset(QUALIFIERS)
    empty: frozenset[str] = frozenset()

    # ---- recorded coarse-to-fine trajectory --------------------------------
    trajectory = []
    trajectory_assertions = []
    trajectory_kept_sets = [empty]
    prev = empty
    prev_metrics = cell_metrics(contexts, prev)
    trajectory.append(
        {
            "step": 0,
            "added": None,
            **{k: v for k, v in prev_metrics.items() if k != "kept"},
            "strict_improvement": False,
        }
    )
    for step, role in enumerate(TRAJECTORY_ORDER, start=1):
        curr = frozenset(prev | {role})
        trajectory_kept_sets.append(curr)
        curr_metrics = cell_metrics(contexts, curr)
        edge = refinement_edge_check(contexts, coarse=prev, fine=curr)
        sp_monotone = curr_metrics["separating_pairs"] <= prev_metrics["separating_pairs"]
        cells_monotone = (
            curr_metrics["representation_cells"] >= prev_metrics["representation_cells"]
        )
        strict = (
            curr_metrics["separating_pairs"] < prev_metrics["separating_pairs"]
            or curr_metrics["representation_cells"] > prev_metrics["representation_cells"]
        )
        trajectory.append(
            {
                "step": step,
                "added": role,
                **{k: v for k, v in curr_metrics.items() if k != "kept"},
                "strict_improvement": strict,
            }
        )
        trajectory_assertions.append(
            {
                "step": step,
                "added": role,
                "refinement_holds": edge["is_refinement"],
                "sp_monotone": sp_monotone,
                "cells_monotone": cells_monotone,
            }
        )
        prev, prev_metrics = curr, curr_metrics

    # ---- full-lattice edge checks -------------------------------------------
    subsets = [
        frozenset(q for i, q in enumerate(QUALIFIERS) if mask & (1 << i))
        for mask in range(1 << len(QUALIFIERS))
    ]
    comparable_pairs = 0
    refinement_violations = 0
    sp_monotone_violations = 0
    lb_monotone_violations = 0
    for coarse, fine in itertools.combinations(subsets, 2):
        if not coarse < fine:
            continue
        comparable_pairs += 1
        edge = refinement_edge_check(contexts, coarse, fine)
        coarse_metrics = cell_metrics(contexts, coarse)
        fine_metrics = cell_metrics(contexts, fine)
        refinement_violations += len(edge["refinement_violations"])
        if fine_metrics["separating_pairs"] > coarse_metrics["separating_pairs"]:
            sp_monotone_violations += 1
        if (
            fine_metrics["ambiguous_cell_lower_bound"]
            > coarse_metrics["ambiguous_cell_lower_bound"]
        ):
            lb_monotone_violations += 1

    # ---- termination ---------------------------------------------------------
    final_metrics = cell_metrics(contexts, all_roles)
    trajectory_length = len(TRAJECTORY_ORDER)
    partition_bound = len(contexts) - 1
    fixed_point_reached = final_metrics["separating_pairs"] == 0

    # ---- E2 cross-checks -----------------------------------------------------
    e2_cross_checks = []
    for role in QUALIFIERS:
        deleted = cell_metrics(contexts, all_roles - {role})
        expected = E2_POWER_SET_DELETION_EXPECTED[role]
        e2_cross_checks.append(
            {
                "role": role,
                "observed": deleted["separating_pairs"],
                "expected": expected,
                "passed": deleted["separating_pairs"] == expected,
            }
        )

    # Independent reproduction of the E2 common-contract baseline (strip the
    # entire qualifiers key; no visibility constant, no payload masking).
    common_rep = common_contract_signatures(contexts)
    common_family = {
        context["context_id"]: context["family_signature"]
        for context in contexts
    }
    common_sp = 0
    for left, right in itertools.combinations(contexts, 2):
        if (
            common_rep[left["context_id"]] == common_rep[right["context_id"]]
            and common_family[left["context_id"]] != common_family[right["context_id"]]
        ):
            common_sp += 1

    # ---- collision monotonicity (T1(c)) -------------------------------------
    sp_sequence = [row["separating_pairs"] for row in trajectory]
    lb_sequence = [row["ambiguous_cell_lower_bound"] for row in trajectory]

    validations = [
        {
            "check": (
                "common-contract semantics (entire qualifiers key stripped, "
                "E2 baseline path) reproduce the frozen common-contract "
                "separating-pair baseline"
            ),
            "observed": common_sp,
            "expected": baseline_common,
            "passed": common_sp == baseline_common,
        },
        {
            "check": (
                "typed end (all qualifier roles kept) reproduces the frozen "
                "typed-contract zero-separating-pair baseline"
            ),
            "observed": final_metrics["separating_pairs"],
            "expected": baseline_typed,
            "passed": final_metrics["separating_pairs"] == baseline_typed,
        },
        {
            "check": (
                "trajectory separates pairs monotonically non-increasing "
                "(T1(a) instance)"
            ),
            "observed": sp_sequence,
            "expected": "non-increasing",
            "passed": all(
                left >= right
                for left, right in zip(sp_sequence, sp_sequence[1:])
            ),
        },
        {
            "check": (
                "ambiguous-cell lower bound monotonically non-increasing "
                "along trajectory (Ambiguous-cell lower bound instance)"
            ),
            "observed": lb_sequence,
            "expected": "non-increasing",
            "passed": all(
                left >= right
                for left, right in zip(lb_sequence, lb_sequence[1:])
            ),
        },
        {
            "check": (
                "refinement holds on every subset-lattice edge "
                "(fine equality implies coarse equality)"
            ),
            "observed": f"{refinement_violations} violations over "
            f"{comparable_pairs} comparable pairs",
            "expected": 0,
            "passed": refinement_violations == 0,
        },
        {
            "check": "separating pairs monotone on every lattice edge",
            "observed": f"{sp_monotone_violations} violations over "
            f"{comparable_pairs} comparable pairs",
            "expected": 0,
            "passed": sp_monotone_violations == 0,
        },
        {
            "check": "ambiguous-cell lower bound monotone on every lattice edge",
            "observed": f"{lb_monotone_violations} violations over "
            f"{comparable_pairs} comparable pairs",
            "expected": 0,
            "passed": lb_monotone_violations == 0,
        },
        {
            "check": "trajectory length within the partition-lattice bound |D|-1",
            "observed": trajectory_length,
            "expected": f"<= {partition_bound}",
            "passed": trajectory_length <= partition_bound,
        },
        {
            "check": "trajectory reaches a fixed point (zero separating pairs)",
            "observed": final_metrics["separating_pairs"],
            "expected": 0,
            "passed": fixed_point_reached,
        },
    ]
    e2_checks_passed = all(row["passed"] for row in e2_cross_checks)

    report = {
        "experiment": "t1_refinement_monotonicity_trajectory_check",
        "status": (
            "passed"
            if all(row["passed"] for row in validations) and e2_checks_passed
            else "failed"
        ),
        "script": str(Path(__file__).resolve().relative_to(ROOT)),
        "inputs": {
            "contexts": {
                "path": str(AGENTDOJO_CONTEXTS.relative_to(ROOT)),
                "sha256": sha256_file(AGENTDOJO_CONTEXTS),
                "n_contexts": len(contexts),
            },
            "baseline_report": {
                "path": str(AGENTDOJO_BASELINE_REPORT.relative_to(ROOT)),
                "sha256": sha256_file(AGENTDOJO_BASELINE_REPORT),
            },
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "domain": {"name": "agentdojo_finite_domain", "n_contexts": len(contexts)},
        "qualifiers": list(QUALIFIERS),
        "trajectory_order": list(TRAJECTORY_ORDER),
        "trajectory": trajectory,
        "trajectory_assertions": trajectory_assertions,
        "lattice": {
            "vertices": len(subsets),
            "comparable_pairs": comparable_pairs,
            "refinement_violations": refinement_violations,
            "sp_monotone_violations": sp_monotone_violations,
            "lb_monotone_violations": lb_monotone_violations,
        },
        "termination": {
            "trajectory_length": trajectory_length,
            "partition_bound": partition_bound,
            "within_bound": trajectory_length <= partition_bound,
            "fixed_point_reached": fixed_point_reached,
            "cycle_free": len({s for s in trajectory_kept_sets}) == len(trajectory_kept_sets),
        },
        "collision_monotonicity": {
            "sp_trajectory": all(
                left >= right for left, right in zip(sp_sequence, sp_sequence[1:])
            ),
            "lb_trajectory": all(
                left >= right for left, right in zip(lb_sequence, lb_sequence[1:])
            ),
        },
        "e2_cross_checks": e2_cross_checks,
        "representation_semantics_note": (
            "The lattice erased end rho_empty applies all five E2 deletion "
            "operations (qualifier sub-keys dropped, payload resource masked, "
            "visibility set to a constant), while the E2 common-contract "
            "baseline strips only the entire qualifiers key. They are distinct "
            "coarse representations; both converge to the same typed end. The "
            "common baseline is reproduced independently as a sanity check."
        ),
        "validations": validations,
        "claim_boundary_scope": (
            "Deterministic recomputation over the frozen 56-call AgentDojo "
            "finite domain with the E2 power-set authority family, the E2 "
            "representation-signature decision procedure, and source-hash-"
            "bound effect data. The qualifier lattice is declared before "
            "metric computation. Results do not extend to open tool domains, "
            "unenumerated calls, other authority families, or refinement "
            "steps outside the restricted contract language."
        ),
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    REPORT_MD.write_text(render_markdown(report), encoding="utf-8")
    return report


def main() -> int:
    report = run()
    print(
        json.dumps(
            {
                "status": report["status"],
                "trajectory_sp": [
                    row["separating_pairs"] for row in report["trajectory"]
                ],
                "trajectory_lb": [
                    row["ambiguous_cell_lower_bound"] for row in report["trajectory"]
                ],
                "lattice": report["lattice"],
                "termination": report["termination"],
                "collision_monotonicity": report["collision_monotonicity"],
                "e2_cross_checks": report["e2_cross_checks"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
