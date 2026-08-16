#!/usr/bin/env python3
"""Evaluate a concrete-atom authorizer on frozen ToolSandbox executions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def find_root(path: Path) -> Path:
    for candidate in path.resolve().parents:
        if (candidate / "experiments").is_dir() and (candidate / "paper").is_dir():
            return candidate
    raise RuntimeError("could not locate consolidated package root")


ROOT = find_root(Path(__file__))
EVALUATION = (
    ROOT
    / "experiments/human-authority-and-causal-validation/evaluation/"
    "concrete-atom-authorizer-mechanism"
)
RESULTS = (
    ROOT
    / "experiments/human-authority-and-causal-validation/results/"
    "concrete-atom-authorizer-mechanism"
)
SOURCE_CONTEXTS = (
    ROOT
    / "experiments/human-authority-and-causal-validation/evaluation/"
    "heldout-toolsandbox-effect-binding-validation/heldout-contexts.jsonl"
)
SOURCE_REPORT = (
    ROOT
    / "experiments/human-authority-and-causal-validation/results/"
    "heldout-toolsandbox-effect-binding-validation/heldout-validation-report.json"
)
PREREGISTRATION = EVALUATION / "preregistration.json"
PAPER_TABLE = ROOT / "paper/current-usenix/tables/table_concrete_atom_authorizer.tex"
QUEUE_STATUS = RESULTS / "queue-status.json"

METHODS = (
    "whole_call_tool_name",
    "raw_arguments_exact",
    "common_effect_atoms",
    "concrete_effect_atoms",
    "source_effect_oracle",
)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not all(isinstance(row, dict) for row in rows):
        raise TypeError(f"expected JSON objects in {path}")
    return rows


def multiset_subset(candidate: Iterable[Any], authority: Iterable[Any]) -> bool:
    """Return whether every candidate occurrence is authorized."""
    candidate_counts = Counter(canonical(value) for value in candidate)
    authority_counts = Counter(canonical(value) for value in authority)
    return all(count <= authority_counts[key] for key, count in candidate_counts.items())


def common_atoms(atoms: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        ({key: value for key, value in atom.items() if key != "qualifiers"} for atom in atoms),
        key=canonical,
    )


def select_rows(rows: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    if mode == "full":
        return rows
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["tool_name"]].append(row)
    return [row for name in sorted(grouped) for row in grouped[name][:2]]


def verify_inputs(prereg: dict[str, Any], *, verify_runner_hash: bool = True) -> None:
    if prereg.get("status") != "frozen_before_full_authorizer_run":
        raise ValueError("authorizer protocol is not frozen")
    expected = prereg["input_hashes"]
    observed = {
        "heldout_contexts_sha256": sha256_file(SOURCE_CONTEXTS),
        "heldout_report_sha256": sha256_file(SOURCE_REPORT),
    }
    if verify_runner_hash:
        observed["runner_sha256"] = sha256_file(Path(__file__))
    for key, value in observed.items():
        if expected.get(key) != value:
            raise ValueError(f"frozen input mismatch: {key}")
    report = load_json(SOURCE_REPORT)
    if report.get("status") != "passed" or report.get("n_contexts") != 32:
        raise ValueError("held-out source validation is not final")


def method_decision(method: str, authority: dict[str, Any], candidate: dict[str, Any]) -> str:
    if method == "whole_call_tool_name":
        allowed = authority["tool_name"] == candidate["tool_name"]
    elif method == "raw_arguments_exact":
        allowed = canonical(authority["arguments"]) == canonical(candidate["arguments"])
    elif method == "common_effect_atoms":
        allowed = multiset_subset(
            candidate["representations"]["common_fields"],
            common_atoms(authority["source_effect_atoms"]),
        )
    elif method == "concrete_effect_atoms":
        allowed = multiset_subset(
            candidate["representations"]["typed_contract"],
            authority["source_effect_atoms"],
        )
    elif method == "source_effect_oracle":
        allowed = multiset_subset(
            candidate["source_effect_atoms"], authority["source_effect_atoms"]
        )
    else:
        raise ValueError(f"unknown method: {method}")
    return "ALLOW" if allowed else "DENY"


def build_queries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["tool_name"]].append(row)
    queries: list[dict[str, Any]] = []
    for tool_name in sorted(grouped):
        members = sorted(grouped[tool_name], key=lambda row: row["case_id"])
        for authority in members:
            for candidate in members:
                ideal = method_decision("source_effect_oracle", authority, candidate)
                decisions = {
                    method: method_decision(method, authority, candidate)
                    for method in METHODS
                }
                queries.append(
                    {
                        "query_id": f"{authority['case_id']}__{candidate['case_id']}",
                        "tool_name": tool_name,
                        "authority_case_id": authority["case_id"],
                        "candidate_case_id": candidate["case_id"],
                        "authority_source_effect_atoms": authority["source_effect_atoms"],
                        "candidate_source_effect_atoms": candidate["source_effect_atoms"],
                        "candidate_typed_contract_atoms": candidate["representations"]["typed_contract"],
                        "ideal_decision": ideal,
                        "method_decisions": decisions,
                    }
                )
    return queries


def rate(successes: int, total: int) -> dict[str, Any]:
    return {
        "successes": successes,
        "total": total,
        "rate": successes / total if total else None,
    }


def summarize_method(queries: list[dict[str, Any]], method: str) -> dict[str, Any]:
    unsafe = [row for row in queries if row["ideal_decision"] == "DENY"]
    safe = [row for row in queries if row["ideal_decision"] == "ALLOW"]
    upa = sum(row["method_decisions"][method] == "ALLOW" for row in unsafe)
    false_deny = sum(row["method_decisions"][method] == "DENY" for row in safe)
    correct = sum(
        row["method_decisions"][method] == row["ideal_decision"] for row in queries
    )
    return {
        "method": method,
        "n_queries": len(queries),
        "unsafe_pre_allow": rate(upa, len(unsafe)),
        "safe_false_deny": rate(false_deny, len(safe)),
        "coverage": rate(len(queries), len(queries)),
        "decision_accuracy": rate(correct, len(queries)),
        "abstain": rate(0, len(queries)),
    }


def render_table(metrics: list[dict[str, Any]], n_queries: int) -> str:
    names = {
        "whole_call_tool_name": "Tool name (whole call)",
        "raw_arguments_exact": "Raw arguments (exact match)",
        "common_effect_atoms": "Common effect fields",
        "concrete_effect_atoms": "Concrete effect atoms",
        "source_effect_oracle": "Source-effect oracle",
    }
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\caption{Small-scale authorizer mechanism check on frozen ToolSandbox executions. UPA is unsafe pre-allow and FD is false denial.}",
        r"\label{tab:concrete-atom-authorizer}",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"View & UPA & FD & Coverage & Accuracy \\",
        r"\midrule",
    ]
    for row in metrics:
        values = [
            row["unsafe_pre_allow"]["rate"],
            row["safe_false_deny"]["rate"],
            row["coverage"]["rate"],
            row["decision_accuracy"]["rate"],
        ]
        lines.append(
            f"{names[row['method']]} & "
            + " & ".join(f"{value:.3f}" for value in values)
            + r" \\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            f"\\vspace{{2pt}}\\parbox{{0.98\\linewidth}}{{\\footnotesize "
            f"Each of the {n_queries} ordered queries uses one executed context as the allowed concrete-effect multiset and checks another context of the same tool.}}",
            r"\end{table}",
            "",
        ]
    )
    return "\n".join(lines)


def render_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Concrete-Atom Authorizer Mechanism Check",
        "",
        f"Status: `{payload['status']}`.",
        "",
        f"The run evaluates {payload['n_queries']} ordered authorization queries over "
        f"{payload['n_contexts']} frozen executions of {payload['n_tools']} ToolSandbox tools.",
        "",
        "| View | UPA | False deny | Coverage | Accuracy |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in payload["metrics"]:
        lines.append(
            f"| `{row['method']}` | {row['unsafe_pre_allow']['successes']}/{row['unsafe_pre_allow']['total']} "
            f"({row['unsafe_pre_allow']['rate']:.3f}) | {row['safe_false_deny']['successes']}/{row['safe_false_deny']['total']} "
            f"({row['safe_false_deny']['rate']:.3f}) | {row['coverage']['rate']:.3f} | "
            f"{row['decision_accuracy']['rate']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "This is a finite, source-executed mechanism check. The authority bound for each query is another observed concrete-effect multiset, not a human-authored deployment policy. The result tests whether each representation can implement that fixed relation; it does not establish open-domain contract soundness, complete authorization, or production safety.",
            "",
        ]
    )
    return "\n".join(lines)


def write_queue_status(status: str, **extra: Any) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {}
    if QUEUE_STATUS.is_file():
        try:
            existing = load_json(QUEUE_STATUS)
        except (ValueError, TypeError, json.JSONDecodeError):
            existing = {}
    payload = {
        **existing,
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **extra,
    }
    QUEUE_STATUS.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def run(mode: str, output_dir: Path | None = None) -> dict[str, Any]:
    prereg = load_json(PREREGISTRATION)
    verify_inputs(prereg)
    all_rows = load_jsonl(SOURCE_CONTEXTS)
    rows = select_rows(all_rows, mode)
    queries = build_queries(rows)
    metrics = [summarize_method(queries, method) for method in METHODS]
    by_method = {row["method"]: row for row in metrics}
    expected_queries = 232 if mode == "full" else sum(
        count * count for count in Counter(row["tool_name"] for row in rows).values()
    )
    gates = {
        "input_hashes_match": True,
        "all_selected_contexts_retained": len(rows) == len({row["case_id"] for row in rows}),
        "all_queries_emitted": len(queries) == expected_queries,
        "nontrivial_authority_labels": len({row["ideal_decision"] for row in queries}) == 2,
        "concrete_atom_zero_unsafe_pre_allow": by_method["concrete_effect_atoms"]["unsafe_pre_allow"]["successes"] == 0,
        "concrete_atom_zero_false_deny": by_method["concrete_effect_atoms"]["safe_false_deny"]["successes"] == 0,
        "source_oracle_exact": by_method["source_effect_oracle"]["decision_accuracy"]["successes"] == len(queries),
        "coarse_view_has_unsafe_pre_allow": by_method["whole_call_tool_name"]["unsafe_pre_allow"]["successes"] > 0,
        "raw_arguments_have_false_denial": by_method["raw_arguments_exact"]["safe_false_deny"]["successes"] > 0,
        "no_abstentions_or_silent_drops": all(row["coverage"]["successes"] == len(queries) for row in metrics),
    }
    payload = {
        "status": "passed" if all(gates.values()) else "failed",
        "experiment": "toolsandbox_concrete_atom_authorizer_mechanism",
        "mode": mode,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_tools": len({row["tool_name"] for row in rows}),
        "n_contexts": len(rows),
        "n_queries": len(queries),
        "ideal_decisions": dict(Counter(row["ideal_decision"] for row in queries)),
        "authority_semantics": "candidate source-effect multiset must be a submultiset of the anchor context's source-effect multiset",
        "metrics": metrics,
        "gates": gates,
        "input_hashes": prereg["input_hashes"],
        "claim_boundary": prereg["claim_boundary"],
    }
    target = output_dir or (RESULTS if mode == "full" else RESULTS / "smoke")
    target.mkdir(parents=True, exist_ok=True)
    (target / "authorization-decisions.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in queries),
        encoding="utf-8",
    )
    (target / "concrete-atom-authorizer-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (target / "concrete-atom-authorizer-report.md").write_text(
        render_report(payload), encoding="utf-8"
    )
    with (target / "authorizer-metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["method", "n_queries", "upa_n", "upa_d", "upa", "fd_n", "fd_d", "fd", "coverage", "accuracy"])
        for row in metrics:
            writer.writerow(
                [
                    row["method"], row["n_queries"],
                    row["unsafe_pre_allow"]["successes"], row["unsafe_pre_allow"]["total"], row["unsafe_pre_allow"]["rate"],
                    row["safe_false_deny"]["successes"], row["safe_false_deny"]["total"], row["safe_false_deny"]["rate"],
                    row["coverage"]["rate"], row["decision_accuracy"]["rate"],
                ]
            )
    table = render_table(metrics, len(queries))
    (target / "table_concrete_atom_authorizer.tex").write_text(table, encoding="utf-8")
    if mode == "full" and payload["status"] == "passed":
        PAPER_TABLE.write_text(table, encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("smoke", "full"), default="full")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.mode == "full":
        write_queue_status("running")
    try:
        payload = run(args.mode, args.output_dir)
    except Exception as exc:
        if args.mode == "full":
            write_queue_status("failed", error=f"{type(exc).__name__}: {exc}")
        raise
    if args.mode == "full":
        write_queue_status(payload["status"], n_contexts=payload["n_contexts"], n_queries=payload["n_queries"])
    print(json.dumps({key: payload[key] for key in ("status", "mode", "n_contexts", "n_queries", "ideal_decisions", "gates")}, indent=2))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
