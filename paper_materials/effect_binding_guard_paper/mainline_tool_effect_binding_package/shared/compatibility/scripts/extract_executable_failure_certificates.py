#!/usr/bin/env python3
"""Deterministically extract executable authorization-interface failures."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[3]
FINITE = ROOT / "experiments/human-authority-and-causal-validation/results/finite-domain-effect-binding-validation"
STATE = ROOT / "experiments/human-authority-and-causal-validation/results/state-aware-authority-interface"
OUT = ROOT / "experiments/human-authority-and-causal-validation/results/executable-failure-certificates"


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _pre_state_summary(context: dict[str, Any]) -> dict[str, Any]:
    changes = []
    for delta in context.get("observed_state_delta", [])[:4]:
        before = delta.get("before")
        changes.append({
            "path": delta.get("path"),
            "before_sha256": hashlib.sha256(canonical(before).encode()).hexdigest(),
            "before_preview": canonical(before)[:160],
        })
    return {"fixture_source_sha256": context["function_source_sha256"], "referenced_paths": changes}


def _finite_certificate(category: str, witness: dict[str, Any], contexts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    first = contexts[witness["authorized_context_id"]]
    second = contexts[witness["rejected_context_id"]]
    refined_first = first["representations"]["source_full_effect"]
    refined_second = second["representations"]["source_full_effect"]
    return {
        "certificate_id": f"certificate-{category}", "category": category,
        "dataset": "finite_source_executed_56", "tool": first["tool_name"],
        "pre_state_summary_u": _pre_state_summary(first), "pre_state_summary_v": _pre_state_summary(second),
        "call_u": first["args"], "call_v": second["args"],
        "source_effect_u": witness["authorized_effects"], "source_effect_v": witness["rejected_effects"],
        "policy_separation": {"authority_bound": witness["authority_bound"], "relation": witness["witness_property"]},
        "ideal_decision_u": "ALLOW", "ideal_decision_v": "DENY",
        "coarse_representation_name": witness["representation"],
        "coarse_representation_u": witness["shared_representation"],
        "coarse_representation_v": witness["shared_representation"],
        "refined_representation_name": "source_full_effect",
        "refined_representation_u": refined_first, "refined_representation_v": refined_second,
        "source_row_u": witness["authorized_context_id"], "source_row_v": witness["rejected_context_id"],
    }


def _select_finite(witnesses: list[dict[str, Any]], contexts: dict[str, dict[str, Any]],
                   predicate: Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], bool]) -> dict[str, Any]:
    candidates = []
    for witness in witnesses:
        first, second = contexts[witness["authorized_context_id"]], contexts[witness["rejected_context_id"]]
        if predicate(witness, first, second):
            candidates.append(witness)
    if not candidates:
        raise RuntimeError("no finite witness matched a frozen certificate category")
    return sorted(candidates, key=lambda row: (row["authorized_context_id"], row["rejected_context_id"], row["representation"]))[0]


def _state_pair(category: str, representation: str, pair_filter: Callable[[dict[str, Any], dict[str, Any]], bool]) -> dict[str, Any]:
    evaluated = {row["case_id"]: row for row in read_jsonl(STATE / "source-executions.jsonl")}
    rows = [row for row in read_jsonl(STATE / "representation-rows.jsonl") if row["representation"] == representation]
    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        cells[row["representation_key"]].append(row)
    candidates = []
    for key, members in cells.items():
        allows = [row for row in members if row["ideal_decision"] == "ALLOW"]
        denies = [row for row in members if row["ideal_decision"] == "DENY"]
        for allow in allows:
            for deny in denies:
                first, second = evaluated[allow["case_id"]], evaluated[deny["case_id"]]
                if first["source_transitions"] != second["source_transitions"] and pair_filter(first, second):
                    candidates.append((allow["case_id"], deny["case_id"], key, first, second))
    if not candidates:
        raise RuntimeError(f"no state-aware witness for {category}")
    allow_id, deny_id, shared, first, second = sorted(candidates, key=lambda item: item[:2])[0]
    return {
        "certificate_id": f"certificate-{category}", "category": category,
        "dataset": "protocol_separated_authority_1024", "tool": first["tool_name"],
        "pre_state_summary_u": {"sha256": first["pre_state_sha256"], "state": first["pre_state"]},
        "pre_state_summary_v": {"sha256": second["pre_state_sha256"], "state": second["pre_state"]},
        "call_u": first["arguments"], "call_v": second["arguments"],
        "source_effect_u": first["source_transitions"], "source_effect_v": second["source_transitions"],
        "policy_separation": {"authority_context_u": first["authority_context"], "authority_context_v": second["authority_context"], "relation": "shared explicit-authority engine returns different ideal decisions"},
        "ideal_decision_u": first["ideal_decision"], "ideal_decision_v": second["ideal_decision"],
        "coarse_representation_name": representation,
        "coarse_representation_u": json.loads(shared), "coarse_representation_v": json.loads(shared),
        "refined_representation_name": "validated_typed_effects",
        "refined_representation_u": first["typed_effects"], "refined_representation_v": second["typed_effects"],
        "source_row_u": allow_id, "source_row_v": deny_id,
    }


def validate(certificate: dict[str, Any]) -> None:
    if canonical(certificate["source_effect_u"]) == canonical(certificate["source_effect_v"]):
        raise AssertionError(f"source semantics equal: {certificate['certificate_id']}")
    if certificate["ideal_decision_u"] == certificate["ideal_decision_v"]:
        raise AssertionError(f"policy does not separate: {certificate['certificate_id']}")
    if canonical(certificate["coarse_representation_u"]) != canonical(certificate["coarse_representation_v"]):
        raise AssertionError(f"coarse representation differs: {certificate['certificate_id']}")
    if canonical(certificate["refined_representation_u"]) == canonical(certificate["refined_representation_v"]):
        raise AssertionError(f"refined representation fails to separate: {certificate['certificate_id']}")


def run() -> dict[str, Any]:
    contexts = {row["context_id"]: row for row in read_jsonl(FINITE / "finite-contexts.jsonl")}
    witnesses = read_jsonl(FINITE / "authorization-separating-witnesses.jsonl")
    source_effect = [row for row in witnesses if row["representation"] == "source_effect_only"]
    certificates = [
        _finite_certificate("target-principal", _select_finite(source_effect, contexts,
            lambda _w, a, b: a["tool_name"] == "add_calendar_event_participants" and len(a["args"]["participants"]) == len(b["args"]["participants"]) == 1), contexts),
        _state_pair("compound-effects", "canonical_raw_arguments",
                    lambda a, b: len(a["source_transitions"]) != len(b["source_transitions"])),
        _finite_certificate("qualifier-recurrence", _select_finite(source_effect, contexts,
            lambda _w, a, b: a["tool_name"] == "schedule_transaction" and a["args"].get("recurring") != b["args"].get("recurring")), contexts),
        _state_pair("state-dependent", "canonical_raw_arguments",
                    lambda a, b: a["argument_group_id"] == b["argument_group_id"] and a["pre_state_sha256"] != b["pre_state_sha256"] and len(a["source_transitions"]) == len(b["source_transitions"])),
        _finite_certificate("repeated-effects", _select_finite(source_effect, contexts,
            lambda _w, a, b: a["tool_name"] == "add_calendar_event_participants" and (len(set(a["args"]["participants"])) != len(a["args"]["participants"]) or len(set(b["args"]["participants"])) != len(b["args"]["participants"]))), contexts),
        _finite_certificate("resource-authority-qualifier", _select_finite(source_effect, contexts,
            lambda _w, a, b: a["tool_name"] == "share_file" and a["args"].get("permission") != b["args"].get("permission")), contexts),
    ]
    for certificate in certificates:
        validate(certificate)
    OUT.mkdir(parents=True, exist_ok=True)
    write_jsonl(OUT / "failure-certificates.jsonl", certificates)
    with (OUT / "failure-certificates.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["certificate_id", "category", "dataset", "tool", "source_row_u", "source_row_v", "coarse_representation_name", "refined_representation_name"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows({key: row[key] for key in fields} for row in certificates)
    lines = ["# Executable Authorization-Interface Failure Certificates", "", "Each row satisfies `source differs AND policy differs AND coarse representation is equal`.", "", "| Category | Tool | Coarse interface | Rows |", "|---|---|---|---|"]
    for row in certificates:
        lines.append(f"| {row['category']} | `{row['tool']}` | `{row['coarse_representation_name']}` | `{row['source_row_u']}` / `{row['source_row_v']}` |")
    (OUT / "failure-certificates.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    paper_rows = [next(row for row in certificates if row["category"] == "compound-effects"), next(row for row in certificates if row["category"] == "state-dependent")]
    tex = ["\\begin{table}[t]", "\\centering", "\\scriptsize", "\\caption{Executable failure certificates for coarse authorization interfaces.}", "\\label{tab:failure-certificates}", "\\begin{tabular}{llll}", "\\toprule", "Cause & Tool & Colliding view & Restored distinction \\\\", "\\midrule"]
    labels = {"compound-effects": "Compound effects", "state-dependent": "Pre-state dependence"}
    for row in paper_rows:
        tex.append(f"{labels[row['category']]} & \\texttt{{{row['tool']}}} & {row['coarse_representation_name'].replace('_', ' ')} & typed effects \\\\")
    tex += ["\\bottomrule", "\\end{tabular}", "\\end{table}", ""]
    (OUT / "table_failure_certificates.tex").write_text("\n".join(tex), encoding="utf-8")
    report = {
        "experiment": "executable_failure_certificates", "status": "passed",
        "n_certificates": len(certificates), "categories": [row["category"] for row in certificates],
        "selection": "frozen category predicates followed by lexicographic first match",
        "validation": "all rows satisfy source difference, policy separation, coarse equality, and refined distinction",
    }
    write_json(OUT / "report.json", report)
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
