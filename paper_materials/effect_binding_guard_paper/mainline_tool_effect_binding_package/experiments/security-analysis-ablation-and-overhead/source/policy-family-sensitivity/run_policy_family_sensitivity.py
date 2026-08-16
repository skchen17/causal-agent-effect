#!/usr/bin/env python3
"""E2: coarse policy-family and qualifier-deletion sensitivity analysis.

Reads two frozen, read-only context artifacts:
  - AgentDojo 56-call finite domain (118 separating pairs under the common
    contract, zero under the reviewed typed contract), and
  - ToolSandbox 32-context held-out domain (41 separating pairs under the
    common fields, zero under the pre-registered typed contract).

For each authority family (power-set baseline, effect-kind aggregation,
resource aggregation, count truncation {0,1,>=2}) and each qualifier-role
deletion (none/date/subject/recurrence/payload/visibility), it recomputes:
  - retained separating pairs: same representation, family-separable effects;
  - redundant pairs: same representation, different full effects that the
    family cannot express (family projection identical);
  - overpartition cells: family-effect classes split by the representation;
  - false-rejection pairs: family-equivalent contexts with different
    representation signatures.

Deterministic, CPU-only, stdlib-only. No input file is modified.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import itertools
import json
import platform
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable


ROOT = Path(__file__).resolve().parents[4]

AGENTDOJO_CONTEXTS = (
    ROOT
    / "experiments/human-authority-and-causal-validation/results/"
    "finite-domain-effect-binding-validation/finite-contexts.jsonl"
)
TOOLSANDBOX_CONTEXTS = (
    ROOT
    / "experiments/human-authority-and-causal-validation/evaluation/"
    "heldout-toolsandbox-effect-binding-validation/heldout-contexts.jsonl"
)
AGENTDOJO_BASELINE_REPORT = (
    ROOT
    / "experiments/human-authority-and-causal-validation/results/"
    "finite-domain-effect-binding-validation/finite-domain-validation-report.json"
)
TOOLSANDBOX_BASELINE_REPORT = (
    ROOT
    / "experiments/human-authority-and-causal-validation/results/"
    "heldout-toolsandbox-effect-binding-validation/heldout-validation-report.json"
)
RESULTS = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "policy-family-sensitivity"
)
REPORT_JSON = RESULTS / "policy-family-sensitivity-report.json"
REPORT_MD = RESULTS / "policy-family-sensitivity-report.md"
GRID_CSV = RESULTS / "policy-family-sensitivity-grid.csv"

FAMILIES: tuple[str, ...] = (
    "power_set",
    "effect_kind",
    "resource",
    "count_truncated",
)
QUALIFIERS: tuple[str, ...] = (
    "none",
    "date",
    "subject",
    "recurrence",
    "payload",
    "visibility",
)
DELETION_ROLES: tuple[str, ...] = QUALIFIERS[1:]

MASKED_PAYLOAD_RESOURCE = "payload:*"
DELETED_FIELD_MARKER = "__DELETED__"

FAMILY_ENUMERATION_PRINCIPLE = (
    "The four authority families are the images of the paper's submultiset "
    "authority construction under a pre-enumerated lattice of occurrence "
    "projections: identity (power-set baseline), effect-name quotient, "
    "resource quotient, and the {0,1,>=2} count truncation of the "
    "effect-name quotient. Each family contains every submultiset of every "
    "observed projected effect multiset, so the families are closed under "
    "submultisets by construction. The set is fixed before any metric is "
    "computed; it is not selected from observed redundancy rates."
)

QUALIFIER_ROLE_MAPPING = {
    "agentdojo_finite_domain": {
        "date": {
            "operation": "drop qualifier keys {'date'}",
            "instantiated_by": ["banking/schedule_transaction qualifiers.date"],
        },
        "subject": {
            "operation": "drop qualifier keys {'subject'}",
            "instantiated_by": ["banking/schedule_transaction qualifiers.subject"],
        },
        "recurrence": {
            "operation": "drop qualifier keys {'recurring'}",
            "instantiated_by": ["banking/schedule_transaction qualifiers.recurring"],
        },
        "payload": {
            "operation": (
                "drop qualifier keys {'content', 'filename'}; mask "
                "'payload:<digest>' resources to 'payload:*'"
            ),
            "instantiated_by": [
                "workspace/create_file qualifiers.content/filename",
                "slack/send_direct_message payload-digest resource",
            ],
        },
        "visibility": {
            "operation": "replace atom visibility with '__DELETED__'",
            "instantiated_by": ["workspace/share_file permission visibility"],
        },
    },
    "toolsandbox_heldout": {
        "date": {
            "operation": "drop qualifier keys {'reminder_timestamp'}",
            "instantiated_by": ["add_reminder qualifiers.reminder_timestamp"],
        },
        "subject": {
            "operation": "no-op (role not instantiated by the five held-out tools)",
            "instantiated_by": [],
        },
        "recurrence": {
            "operation": "no-op (role not instantiated by the five held-out tools)",
            "instantiated_by": [],
        },
        "payload": {
            "operation": (
                "drop qualifier keys {'name', 'relationship', 'is_self', "
                "'removed_contact_identity', 'content'}"
            ),
            "instantiated_by": [
                "add_contact qualifiers.name/relationship/is_self",
                "remove_contact qualifiers.removed_contact_identity",
                "add_reminder qualifiers.content",
            ],
        },
        "visibility": {
            "operation": "replace atom visibility with '__DELETED__'",
            "instantiated_by": [],
        },
    },
}

CLAIM_LOW_REDUNDANCY = (
    "Low redundancy (direction 2): under every tested coarser family, "
    "deleting non-vacuous qualifiers still created authorization-separating "
    "collisions. The typed qualifiers remain operationally necessary across "
    "the tested family lattice, not only under the power-set family. This "
    "counters the claim that the contract is a serialization of the state "
    "difference whose qualifiers become dispensable once authority is "
    "aggregated."
)
CLAIM_HIGH_REDUNDANCY = (
    "High redundancy (direction 1): under the coarser families, most or all "
    "collisions created by qualifier deletion are policy-invisible "
    "(redundant pairs). Qualifier necessity is therefore representation-"
    "relative: the paper's qualifier-necessity claim is scoped to the "
    "declared power-set authority family, and the coarser families quantify "
    "which effect details those policies cannot express. This is positive "
    "evidence that the representation is policy-relative rather than a "
    "fixed serialization."
)
CLAIM_MIXED = (
    "Mixed: qualifier necessity varies by qualifier role and family; see the "
    "per-role verdict rows. Necessity claims are scoped to the "
    "domain-qualifier-family cells marked 'necessary'; cells marked "
    "'redundant' delimit where the coarser family cannot express the "
    "distinction."
)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# ---------------------------------------------------------------------------
# Domain adapters (frozen inputs, read-only)
# ---------------------------------------------------------------------------


def load_agentdojo_contexts() -> list[dict[str, Any]]:
    contexts = []
    for row in read_jsonl(AGENTDOJO_CONTEXTS):
        contexts.append(
            {
                "context_id": row["context_id"],
                "tool_instance_key": row["tool_instance_key"],
                "effects": row["source_effects"],
                "full_effect_signature": row["source_effect_signature"],
                "typed_atoms": row["representations"]["reviewed_typed_contract"],
                "resource_field": "resource",
            }
        )
    return contexts


def load_toolsandbox_contexts() -> list[dict[str, Any]]:
    contexts = []
    for row in read_jsonl(TOOLSANDBOX_CONTEXTS):
        contexts.append(
            {
                "context_id": row["case_id"],
                "tool_instance_key": row["tool_name"],
                "effects": row["source_effect_atoms"],
                "full_effect_signature": digest(row["source_effect_atoms"]),
                "typed_atoms": row["representations"]["typed_contract"],
                "resource_field": "resource_id",
            }
        )
    return contexts


# ---------------------------------------------------------------------------
# Authority families: projections of source-effect multisets
# ---------------------------------------------------------------------------


def family_projection(
    family: str, effects: list[dict[str, Any]], resource_field: str
) -> Any:
    """Project an effect multiset to the granularity the family can express."""
    if family == "power_set":
        return effects
    if family == "effect_kind":
        return sorted(effect["effect"] for effect in effects)
    if family == "resource":
        return sorted(str(effect[resource_field]) for effect in effects)
    if family == "count_truncated":
        counts = Counter(effect["effect"] for effect in effects)
        return sorted(
            [effect_name, "1" if count == 1 else "ge2"]
            for effect_name, count in counts.items()
        )
    raise ValueError(f"unknown authority family: {family}")


def separability_ceiling_pairs(
    contexts: list[dict[str, Any]], family: str
) -> dict[str, Any]:
    """Domain-level ceiling: which effect pairs the family can separate at all."""
    separable = 0
    different_effects = 0
    for left, right in itertools.combinations(contexts, 2):
        if left["full_effect_signature"] == right["full_effect_signature"]:
            continue
        different_effects += 1
        left_projection = family_projection(
            family, left["effects"], left["resource_field"]
        )
        right_projection = family_projection(
            family, right["effects"], right["resource_field"]
        )
        if canonical(left_projection) != canonical(right_projection):
            separable += 1
    return {
        "different_effect_pairs": different_effects,
        "family_separable_pairs": separable,
        "separability_ceiling": (
            separable / different_effects if different_effects else None
        ),
    }


# ---------------------------------------------------------------------------
# Qualifier-role deletion on the typed-contract representation
# ---------------------------------------------------------------------------


def atom_after_deletion(atom: dict[str, Any], qualifier: str) -> dict[str, Any]:
    result = copy.deepcopy(atom)
    if qualifier == "none":
        return result
    if qualifier == "visibility":
        result["visibility"] = DELETED_FIELD_MARKER
        return result
    qualifier_drops: dict[str, set[str]] = {}
    payload_mask = False
    if "resource" in result:  # AgentDojo atom schema
        qualifier_drops = {
            "date": {"date"},
            "subject": {"subject"},
            "recurrence": {"recurring"},
            "payload": {"content", "filename"},
        }
        payload_mask = qualifier == "payload"
    else:  # ToolSandbox atom schema (resource_id)
        qualifier_drops = {
            "date": {"reminder_timestamp"},
            "subject": set(),
            "recurrence": set(),
            "payload": {
                "name",
                "relationship",
                "is_self",
                "removed_contact_identity",
                "content",
            },
        }
    drops = qualifier_drops.get(qualifier, set())
    if drops and result.get("qualifiers"):
        for key in drops:
            result["qualifiers"].pop(key, None)
    if payload_mask and isinstance(result.get("resource"), str):
        if result["resource"].startswith("payload:"):
            result["resource"] = MASKED_PAYLOAD_RESOURCE
    return result


def representation_after_deletion(
    atoms: list[dict[str, Any]], qualifier: str
) -> list[dict[str, Any]]:
    return sorted(
        (atom_after_deletion(atom, qualifier) for atom in atoms),
        key=canonical,
    )


def representation_is_vacuous(
    contexts: list[dict[str, Any]], qualifier: str
) -> bool:
    """True when the deletion changes no context's representation signature."""
    for context in contexts:
        baseline = canonical(context["typed_atoms"])
        deleted = canonical(
            representation_after_deletion(context["typed_atoms"], qualifier)
        )
        if baseline != deleted:
            return False
    return True


# ---------------------------------------------------------------------------
# Sensitivity metrics
# ---------------------------------------------------------------------------


def representation_signatures(
    contexts: list[dict[str, Any]], qualifier: str
) -> dict[str, str]:
    return {
        context["context_id"]: canonical(
            representation_after_deletion(context["typed_atoms"], qualifier)
        )
        for context in contexts
    }


def compute_metrics(
    contexts: list[dict[str, Any]], family: str, qualifier: str
) -> dict[str, Any]:
    rep_signature = representation_signatures(contexts, qualifier)
    family_signature = {
        context["context_id"]: canonical(
            family_projection(family, context["effects"], context["resource_field"])
        )
        for context in contexts
    }

    separating_pairs = 0
    redundant_pairs = 0
    false_rejection_pairs = 0
    for left, right in itertools.combinations(contexts, 2):
        same_rep = (
            rep_signature[left["context_id"]] == rep_signature[right["context_id"]]
        )
        same_family = (
            family_signature[left["context_id"]]
            == family_signature[right["context_id"]]
        )
        if same_rep and not same_family:
            separating_pairs += 1
        elif same_rep and same_family:
            if left["full_effect_signature"] != right["full_effect_signature"]:
                redundant_pairs += 1
        if same_family and not same_rep:
            false_rejection_pairs += 1

    family_cells: dict[str, set[str]] = defaultdict(set)
    for context in contexts:
        family_cells[family_signature[context["context_id"]]].add(
            rep_signature[context["context_id"]]
        )
    overpartition_cells = sum(
        1 for signatures in family_cells.values() if len(signatures) > 1
    )

    collision_pairs = separating_pairs + redundant_pairs
    return {
        "representation_cells": len(set(rep_signature.values())),
        "family_effect_cells": len(family_cells),
        "separating_pairs": separating_pairs,
        "redundant_pairs": redundant_pairs,
        "collision_pairs": collision_pairs,
        "redundancy_rate": (
            redundant_pairs / collision_pairs if collision_pairs else None
        ),
        "overpartition_cells": overpartition_cells,
        "false_rejection_pairs": false_rejection_pairs,
    }


# ---------------------------------------------------------------------------
# Baseline reproduction checks (guard against silent metric drift)
# ---------------------------------------------------------------------------


def read_baseline_separating_pairs(report_path: Path, representation: str) -> int:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    for row in report["representations"]:
        if row["representation"] == representation:
            return row["authorization_separating_pairs"]
    raise KeyError(f"{representation} missing from {report_path.name}")


def run_validations(
    domains: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    validations: list[dict[str, Any]] = []

    for domain, contexts in domains.items():
        metrics = compute_metrics(contexts, "power_set", "none")
        validations.append(
            {
                "check": (
                    "typed contract is an exact partition under the power-set "
                    "family with no deletion (reproduces the zero-collision "
                    "baseline)"
                ),
                "domain": domain,
                "observed": {
                    "separating_pairs": metrics["separating_pairs"],
                    "overpartition_cells": metrics["overpartition_cells"],
                    "false_rejection_pairs": metrics["false_rejection_pairs"],
                    "representation_cells": metrics["representation_cells"],
                },
                "expected": {
                    "separating_pairs": 0,
                    "overpartition_cells": 0,
                    "false_rejection_pairs": 0,
                },
                "passed": (
                    metrics["separating_pairs"] == 0
                    and metrics["overpartition_cells"] == 0
                    and metrics["false_rejection_pairs"] == 0
                ),
            }
        )

    expected_common = {
        "agentdojo_finite_domain": read_baseline_separating_pairs(
            AGENTDOJO_BASELINE_REPORT, "reviewed_common_contract"
        ),
        "toolsandbox_heldout": read_baseline_separating_pairs(
            TOOLSANDBOX_BASELINE_REPORT, "common_fields"
        ),
    }
    for domain, contexts in domains.items():
        # Drop the entire qualifier map (no visibility/payload-resource
        # masking): this must reproduce the frozen common-contract baseline.
        stripped = [
            {
                **context,
                "typed_atoms": [
                    {k: v for k, v in atom.items() if k != "qualifiers"}
                    for atom in context["typed_atoms"]
                ],
            }
            for context in contexts
        ]
        metrics = compute_metrics(stripped, "power_set", "none")
        validations.append(
            {
                "check": (
                    "dropping all qualifiers reproduces the frozen "
                    "common-contract separating-pair baseline"
                ),
                "domain": domain,
                "observed": {"separating_pairs": metrics["separating_pairs"]},
                "expected": {"separating_pairs": expected_common[domain]},
                "passed": metrics["separating_pairs"] == expected_common[domain],
            }
        )

    # Vacuous deletions must leave every family's metrics unchanged.
    metric_keys = (
        "representation_cells",
        "separating_pairs",
        "redundant_pairs",
        "overpartition_cells",
        "false_rejection_pairs",
    )
    for domain, contexts in domains.items():
        for qualifier in DELETION_ROLES:
            if not representation_is_vacuous(contexts, qualifier):
                continue
            mismatched_families = []
            for family in FAMILIES:
                baseline = compute_metrics(contexts, family, "none")
                deleted = compute_metrics(contexts, family, qualifier)
                if any(baseline[key] != deleted[key] for key in metric_keys):
                    mismatched_families.append(family)
            validations.append(
                {
                    "check": (
                        f"vacuous deletion '{qualifier}' leaves all family "
                        "metrics unchanged"
                    ),
                    "domain": domain,
                    "observed": {"mismatched_families": mismatched_families},
                    "expected": {"mismatched_families": []},
                    "passed": not mismatched_families,
                }
            )
    return validations


# ---------------------------------------------------------------------------
# Verdicts and claim boundary selection
# ---------------------------------------------------------------------------


def classify_cell(metrics: dict[str, Any], vacuous: bool) -> str:
    if vacuous:
        return "vacuous"
    if metrics["separating_pairs"] > 0:
        return "necessary"
    if metrics["redundant_pairs"] > 0:
        return "redundant"
    return "no_effect"


def build_verdicts(
    grid_rows: list[dict[str, Any]],
    vacuous: dict[str, dict[str, bool]],
) -> list[dict[str, Any]]:
    verdicts = []
    for domain, per_role in vacuous.items():
        for qualifier, is_vacuous in per_role.items():
            cells = {
                row["family"]: row
                for row in grid_rows
                if row["domain"] == domain and row["qualifier"] == qualifier
            }
            statuses = {
                family: classify_cell(cells[family], is_vacuous)
                for family in FAMILIES
            }
            if is_vacuous:
                summary = "vacuous"
            elif all(
                statuses[family] == "necessary" for family in FAMILIES
            ):
                summary = "necessary_under_all_families"
            elif (
                statuses["power_set"] == "necessary"
                and all(
                    statuses[family] in {"redundant", "no_effect"}
                    for family in FAMILIES
                    if family != "power_set"
                )
            ):
                summary = "necessary_only_under_power_set"
            elif all(
                statuses[family] in {"redundant", "no_effect", "vacuous"}
                for family in FAMILIES
            ):
                summary = "never_necessary_under_tested_families"
            else:
                summary = "mixed"
            verdicts.append(
                {
                    "domain": domain,
                    "qualifier": qualifier,
                    "vacuous": is_vacuous,
                    "status_by_family": statuses,
                    "summary": summary,
                }
            )
    return verdicts


def select_claim_boundary(
    verdicts: list[dict[str, Any]], grid_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    active = [row for row in verdicts if not row["vacuous"]]
    if active and all(
        row["summary"] == "necessary_under_all_families" for row in active
    ):
        direction, claim = "low_redundancy", CLAIM_LOW_REDUNDANCY
    elif active and all(
        row["summary"]
        in {"necessary_only_under_power_set", "never_necessary_under_tested_families"}
        for row in active
    ):
        direction, claim = "high_redundancy", CLAIM_HIGH_REDUNDANCY
    else:
        direction, claim = "mixed", CLAIM_MIXED

    # Data-driven observed summary (computed, never pre-filled).
    deletion_rows = [row for row in grid_rows if row["qualifier"] != "none"]
    power_set_rows = [row for row in deletion_rows if row["family"] == "power_set"]
    coarse_rows = [row for row in deletion_rows if row["family"] != "power_set"]
    necessary_power_set = sum(
        row["status"] == "necessary" for row in power_set_rows
    )
    non_vacuous_coarse = [row for row in coarse_rows if not row["vacuous"]]
    fully_redundant_coarse = sum(
        row["status"] == "redundant" and row["redundancy_rate"] == 1.0
        for row in non_vacuous_coarse
    )
    partial_coarse = [
        {
            "domain": row["domain"],
            "family": row["family"],
            "qualifier": row["qualifier"],
            "separating_pairs": row["separating_pairs"],
            "redundant_pairs": row["redundant_pairs"],
            "redundancy_rate": row["redundancy_rate"],
        }
        for row in non_vacuous_coarse
        if row["status"] == "necessary"
    ]
    observed_summary = (
        f"Across both domains, {necessary_power_set} of {len(power_set_rows)} "
        f"non-baseline power-set deletion rows create authorization-separating "
        f"collisions (the remainder are vacuous or no-effect); among "
        f"{len(non_vacuous_coarse)} non-vacuous deletion rows under the three "
        f"coarser families, {fully_redundant_coarse} have redundancy rate "
        f"1.000. Exceptions with residual separating pairs under a coarser "
        f"family: {json.dumps(partial_coarse, sort_keys=True)}."
    )
    return {
        "direction": direction,
        "selected_claim_boundary": claim,
        "observed_summary": observed_summary,
        "necessary_under_power_set_rows": necessary_power_set,
        "power_set_deletion_rows": len(power_set_rows),
        "fully_redundant_coarse_rows": fully_redundant_coarse,
        "non_vacuous_coarse_rows": len(non_vacuous_coarse),
        "coarse_cells_with_residual_separation": partial_coarse,
        "low_redundancy_template": CLAIM_LOW_REDUNDANCY,
        "high_redundancy_template": CLAIM_HIGH_REDUNDANCY,
        "mixed_template": CLAIM_MIXED,
    }


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

GRID_COLUMNS = (
    "domain",
    "family",
    "qualifier",
    "representation_cells",
    "separating_pairs",
    "redundant_pairs",
    "collision_pairs",
    "redundancy_rate",
    "overpartition_cells",
    "false_rejection_pairs",
    "vacuous",
    "status",
)


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# E2 Policy-Family × Qualifier-Deletion Sensitivity Report",
        "",
        "## Runbook",
        "",
        f"- Script: `{report['script']}`",
        "- Command: `python3 experiments/security-analysis-ablation-and-overhead/"
        "source/policy-family-sensitivity/run_policy_family_sensitivity.py`",
        "- Inputs (read-only, frozen):",
        f"  - `{report['inputs']['agentdojo_finite_domain']['path']}`",
        f"  - `{report['inputs']['toolsandbox_heldout']['path']}`",
        "- Dependencies: Python standard library only; CPU-only; no network.",
        f"- Python: {report['environment']['python']}",
        "",
        "## Definitions",
        "",
        "- Retained separating pairs: context pairs with identical "
        "post-deletion representations whose source effects remain separable "
        "by some authority in the family (authorization-separating "
        "collisions created or retained by the deletion).",
        "- Redundant pairs: context pairs with identical representations and "
        "different full source effects that the family cannot express "
        "(identical family projection); the distinction is policy-invisible "
        "under that family.",
        "- Overpartition cells: family-equivalence classes split into more "
        "than one representation signature.",
        "- False-rejection pairs: family-equivalent context pairs with "
        "different representation signatures (signature-bound authority "
        "would treat identically authorized calls differently).",
        "- Vacuous: the deletion changes no representation signature in the "
        "domain.",
        "",
        "## Family enumeration principle (table note)",
        "",
        FAMILY_ENUMERATION_PRINCIPLE,
        "",
        "## Qualifier-role mapping",
        "",
    ]
    for domain, roles in report["qualifier_role_mapping"].items():
        lines.append(f"### {domain}")
        lines.append("")
        lines.append("| Qualifier role | Deletion operation | Instantiated by |")
        lines.append("|---|---|---|")
        for qualifier, spec in roles.items():
            instantiated = "; ".join(spec["instantiated_by"]) or "(none)"
            lines.append(
                f"| {qualifier} | {spec['operation']} | {instantiated} |"
            )
        lines.append("")

    for domain in report["domains"]:
        lines.extend(
            [
                f"## Sensitivity table: {domain}",
                "",
                "| Family | Qualifier deleted | Rep cells | Separating | "
                "Redundant | Redundancy rate | Overpartition cells | "
                "False rejections | Status |",
                "|---|---|---:|---:|---:|---:|---:|---:|---|",
            ]
        )
        for row in report["grid_rows"]:
            if row["domain"] != domain:
                continue
            rate = (
                "NA" if row["redundancy_rate"] is None
                else f"{row['redundancy_rate']:.3f}"
            )
            lines.append(
                f"| {row['family']} | {row['qualifier']} | "
                f"{row['representation_cells']} | {row['separating_pairs']} | "
                f"{row['redundant_pairs']} | {rate} | "
                f"{row['overpartition_cells']} | "
                f"{row['false_rejection_pairs']} | {row['status']} |"
            )
        lines.append("")
        lines.append(f"### Family separability ceilings: {domain}")
        lines.append("")
        lines.append("| Family | Different-effect pairs | Family-separable | Ceiling |")
        lines.append("|---|---:|---:|---:|")
        for family, summary in report["family_summary"][domain].items():
            ceiling = summary["separability_ceiling"]
            ceiling_text = "NA" if ceiling is None else f"{ceiling:.3f}"
            lines.append(
                f"| {family} | {summary['different_effect_pairs']} | "
                f"{summary['family_separable_pairs']} | {ceiling_text} |"
            )
        lines.append("")

    lines.extend(["## Baseline reproduction checks", ""])
    lines.append("| Check | Domain | Observed | Expected | Passed |")
    lines.append("|---|---|---|---|:---:|")
    for row in report["validations"]:
        lines.append(
            f"| {row['check']} | {row['domain']} | "
            f"{json.dumps(row['observed'], sort_keys=True)} | "
            f"{json.dumps(row['expected'], sort_keys=True)} | "
            f"{'yes' if row['passed'] else 'no'} |"
        )
    lines.append("")

    lines.extend(["## Per-qualifier verdicts", ""])
    lines.append("| Domain | Qualifier | Vacuous | Verdict |")
    lines.append("|---|---|:---:|---|")
    for row in report["verdicts"]:
        lines.append(
            f"| {row['domain']} | {row['qualifier']} | "
            f"{'yes' if row['vacuous'] else 'no'} | {row['summary']} |"
        )
    lines.append("")

    claim = report["claim_boundary"]
    lines.extend(
        [
            "## Claim boundary (both directions pre-registered)",
            "",
            f"Selected direction from the observed grid: `{claim['direction']}`.",
            "",
            f"> {claim['selected_claim_boundary']}",
            "",
            f"Observed summary: {claim['observed_summary']}",
            "",
            "Templates (both retained regardless of direction):",
            "",
            f"- Low redundancy: {claim['low_redundancy_template']}",
            f"- High redundancy: {claim['high_redundancy_template']}",
            f"- Mixed: {claim['mixed_template']}",
            "",
            "## Claim boundary (fixed scope)",
            "",
            report["claim_boundary_scope"],
            "",
        ]
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run() -> dict[str, Any]:
    domains: dict[str, list[dict[str, Any]]] = {
        "agentdojo_finite_domain": load_agentdojo_contexts(),
        "toolsandbox_heldout": load_toolsandbox_contexts(),
    }
    if len(domains["agentdojo_finite_domain"]) != 56:
        raise ValueError("AgentDojo frozen domain must contain 56 contexts")
    if len(domains["toolsandbox_heldout"]) != 32:
        raise ValueError("ToolSandbox frozen domain must contain 32 contexts")

    inputs = {
        "agentdojo_finite_domain": {
            "path": str(AGENTDOJO_CONTEXTS.relative_to(ROOT)),
            "sha256": sha256_file(AGENTDOJO_CONTEXTS),
            "n_contexts": len(domains["agentdojo_finite_domain"]),
        },
        "toolsandbox_heldout": {
            "path": str(TOOLSANDBOX_CONTEXTS.relative_to(ROOT)),
            "sha256": sha256_file(TOOLSANDBOX_CONTEXTS),
            "n_contexts": len(domains["toolsandbox_heldout"]),
        },
    }

    vacuous = {
        domain: {
            qualifier: representation_is_vacuous(contexts, qualifier)
            for qualifier in DELETION_ROLES
        }
        for domain, contexts in domains.items()
    }

    grid_rows: list[dict[str, Any]] = []
    for domain, contexts in domains.items():
        for family in FAMILIES:
            for qualifier in QUALIFIERS:
                metrics = compute_metrics(contexts, family, qualifier)
                is_vacuous = qualifier != "none" and vacuous[domain][qualifier]
                grid_rows.append(
                    {
                        "domain": domain,
                        "family": family,
                        "qualifier": qualifier,
                        **metrics,
                        "vacuous": is_vacuous,
                        "status": classify_cell(metrics, is_vacuous),
                    }
                )

    coverage = {
        "domains": sorted(domains),
        "families": list(FAMILIES),
        "qualifiers": list(QUALIFIERS),
        "expected_rows": len(domains) * len(FAMILIES) * len(QUALIFIERS),
        "observed_rows": len(grid_rows),
        "complete": len(grid_rows)
        == len(domains) * len(FAMILIES) * len(QUALIFIERS),
    }
    if not coverage["complete"]:
        raise ValueError("family x qualifier grid is incomplete")

    family_summary = {
        domain: {
            family: separability_ceiling_pairs(contexts, family)
            for family in FAMILIES
        }
        for domain, contexts in domains.items()
    }
    validations = run_validations(domains)
    verdicts = build_verdicts(grid_rows, vacuous)
    claim_boundary = select_claim_boundary(verdicts, grid_rows)

    report = {
        "experiment": "e2_policy_family_qualifier_deletion_sensitivity",
        "status": "passed" if all(row["passed"] for row in validations) else "failed",
        "domains": sorted(domains),
        "script": str(Path(__file__).resolve().relative_to(ROOT)),
        "inputs": inputs,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "families": list(FAMILIES),
        "qualifiers": list(QUALIFIERS),
        "family_enumeration_principle": FAMILY_ENUMERATION_PRINCIPLE,
        "qualifier_role_mapping": QUALIFIER_ROLE_MAPPING,
        "coverage": coverage,
        "family_summary": family_summary,
        "grid_rows": grid_rows,
        "validations": validations,
        "verdicts": verdicts,
        "claim_boundary": claim_boundary,
        "claim_boundary_scope": (
            "Deterministic recomputation over two frozen finite domains with "
            "source-hash-bound effect oracles. Separability is defined "
            "relative to the declared family's projection of source-effect "
            "multisets; the families are declared before metric computation. "
            "Results do not extend to unenumerated calls, open tool domains, "
            "deployment policy languages, or families outside the "
            "enumerated lattice."
        ),
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with GRID_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(GRID_COLUMNS), extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(grid_rows)
    REPORT_MD.write_text(render_markdown(report), encoding="utf-8")
    return report


def main() -> int:
    report = run()
    print(
        json.dumps(
            {
                "status": report["status"],
                "coverage": report["coverage"],
                "claim_boundary_direction": report["claim_boundary"]["direction"],
                "verdicts": [
                    {
                        "domain": row["domain"],
                        "qualifier": row["qualifier"],
                        "summary": row["summary"],
                    }
                    for row in report["verdicts"]
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
