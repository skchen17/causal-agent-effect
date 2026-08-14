#!/usr/bin/env python3
"""Compare raw-field and effect-semantic views under fixed finite policies."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "paper/current-usenix").is_dir()
)
EVAL = ROOT / (
    "experiments/security-analysis-ablation-and-overhead/evaluation/"
    "atom-vs-field-semantic-attribution"
)
OUT = ROOT / (
    "experiments/security-analysis-ablation-and-overhead/results/"
    "atom-vs-field-semantic-attribution"
)
PROTOCOL = EVAL / "protocol.json"
MECHANISM_SCRIPT = ROOT / "shared/compatibility/scripts/run_representation_mechanism_attribution.py"
RAW_REGISTRY = ROOT / (
    "experiments/security-analysis-ablation-and-overhead/evaluation/"
    "strict-atom-representation-attribution/raw-schema-field-registry.jsonl"
)
VALIDATED_REGISTRY = ROOT / (
    "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/"
    "registered-effect-diff-descriptors.jsonl"
)

REPRESENTATIONS = (
    "tool_name",
    "raw_call_exact",
    "raw_field_leaf_set",
    "pre_validation_common_effects",
    "validated_typed_atoms",
    "source_effect_oracle",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def load_mechanism():
    spec = importlib.util.spec_from_file_location("atom_field_base_mechanism", MECHANISM_SCRIPT)
    if not spec or not spec.loader:
        raise RuntimeError("cannot load representation mechanism module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_protocol() -> dict[str, Any]:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if protocol.get("status") != "frozen_before_execution":
        raise RuntimeError("protocol is not frozen before execution")
    for relative, expected in protocol["source_sha256"].items():
        path = ROOT / relative
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"frozen source mismatch: {relative}")
    if tuple(protocol["representations"]) != REPRESENTATIONS:
        raise RuntimeError("representation set drifted from protocol")
    return protocol


def flatten_leaves(value: Any, path: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        rows: list[dict[str, Any]] = []
        for key in sorted(value):
            rows.extend(flatten_leaves(value[key], (*path, str(key))))
        return rows
    if isinstance(value, list):
        rows = []
        for index, item in enumerate(value):
            rows.extend(flatten_leaves(item, (*path, str(index))))
        if not value:
            rows.append({"field": path[0] if path else "", "path": list(path), "value": []})
        return rows
    return [{"field": path[0] if path else "", "path": list(path), "value": value}]


def add_views(context: dict[str, Any]) -> dict[str, Any]:
    existing = context["representations"]
    arguments = context["arguments"]
    context["representations"] = {
        "tool_name": context["tool_name"],
        "raw_call_exact": {"tool_name": context["tool_name"], "arguments": arguments},
        "raw_field_leaf_set": flatten_leaves(arguments),
        "pre_validation_common_effects": existing["common_effect_tuple"],
        "validated_typed_atoms": existing["typed_effect_occurrence"],
        "source_effect_oracle": existing["source_full_effect"],
    }
    return context


def field_set_control() -> dict[str, Any]:
    raw_rows = read_jsonl(RAW_REGISTRY)
    validated_rows = [row for row in read_jsonl(VALIDATED_REGISTRY) if row.get("registered")]
    raw = {row["tool_name"]: sorted(row["security_fields"]) for row in raw_rows}
    validated = {row["tool_name"]: sorted(row["security_fields"]) for row in validated_rows}
    mismatches = {
        tool: {"raw": raw.get(tool), "validated": validated.get(tool)}
        for tool in sorted(set(raw) | set(validated))
        if raw.get(tool) != validated.get(tool)
    }
    report = {
        "status": "passed" if not mismatches else "failed",
        "n_tools_raw": len(raw),
        "n_tools_validated": len(validated),
        "n_fields_raw": sum(len(fields) for fields in raw.values()),
        "n_fields_validated": sum(len(fields) for fields in validated.values()),
        "same_tool_and_field_sets": not mismatches,
        "mismatches": mismatches,
        "interpretation": (
            "Both conditions retain the same schema fields; differences in the finite "
            "semantic experiment cannot be attributed to deleting fields."
        ),
    }
    if report["status"] != "passed" or report["n_tools_raw"] != 25 or report["n_fields_raw"] != 67:
        raise RuntimeError(f"field-set control failed: {report}")
    return report


def as_counter(view: Any) -> Counter[str]:
    values = view if isinstance(view, list) else [view]
    return Counter(canonical(value) for value in values)


def contained(candidate: Counter[str], anchor: Counter[str]) -> bool:
    return all(count <= anchor[item] for item, count in candidate.items())


def view_decision(representation: str, anchor: dict[str, Any], candidate: dict[str, Any]) -> bool:
    if representation == "tool_name":
        return anchor["tool_name"] == candidate["tool_name"]
    a_view = anchor["representations"][representation]
    c_view = candidate["representations"][representation]
    if representation == "raw_call_exact":
        return canonical(a_view) == canonical(c_view)
    return contained(as_counter(c_view), as_counter(a_view))


def ideal_decision(anchor: dict[str, Any], candidate: dict[str, Any]) -> bool:
    return contained(as_counter(candidate["source_atoms"]), as_counter(anchor["source_atoms"]))


def ordered_authorizer(contexts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for context in contexts:
        grouped[(context["dataset"], context["tool_name"])].append(context)
    decisions: list[dict[str, Any]] = []
    for (dataset, tool), rows in sorted(grouped.items()):
        for anchor in rows:
            for candidate in rows:
                ideal = ideal_decision(anchor, candidate)
                for representation in REPRESENTATIONS:
                    observed = view_decision(representation, anchor, candidate)
                    decisions.append(
                        {
                            "dataset": dataset,
                            "tool_name": tool,
                            "anchor_id": anchor["context_id"],
                            "candidate_id": candidate["context_id"],
                            "representation": representation,
                            "ideal_allow": ideal,
                            "observed_allow": observed,
                            "unsafe_pre_allow": observed and not ideal,
                            "false_deny": ideal and not observed,
                            "correct": observed == ideal,
                        }
                    )
    metrics = []
    for (dataset, representation), rows in sorted(
        _groups(decisions, lambda row: (row["dataset"], row["representation"])).items()
    ):
        safe = sum(row["ideal_allow"] for row in rows)
        unsafe = len(rows) - safe
        upa = sum(row["unsafe_pre_allow"] for row in rows)
        fd = sum(row["false_deny"] for row in rows)
        metrics.append(
            {
                "dataset": dataset,
                "representation": representation,
                "n_queries": len(rows),
                "n_authorized": safe,
                "n_unauthorized": unsafe,
                "unsafe_pre_allow": upa,
                "upa_rate": upa / unsafe if unsafe else 0.0,
                "false_deny": fd,
                "false_deny_rate": fd / safe if safe else 0.0,
                "coverage": 1.0,
                "decision_accuracy": sum(row["correct"] for row in rows) / len(rows),
            }
        )
    return decisions, metrics


def _groups(rows: list[dict[str, Any]], key):
    grouped = defaultdict(list)
    for row in rows:
        grouped[key(row)].append(row)
    return grouped


def atom_agreement(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for representation in ("pre_validation_common_effects", "validated_typed_atoms", "source_effect_oracle"):
        for dataset, rows in sorted(_groups(contexts, lambda row: row["dataset"]).items()):
            exact = sum(
                as_counter(row["representations"][representation]) == as_counter(row["source_atoms"])
                for row in rows
            )
            count_match = sum(
                len(row["representations"][representation]) == len(row["source_atoms"])
                for row in rows
            )
            results.append(
                {
                    "dataset": dataset,
                    "representation": representation,
                    "n_contexts": len(rows),
                    "exact_set_match": exact,
                    "exact_set_match_rate": exact / len(rows),
                    "atom_count_match": count_match,
                    "atom_count_match_rate": count_match / len(rows),
                }
            )
    return results


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Atom-vs-Field Semantic Attribution",
        "",
        "This finite experiment holds source effects, policy predicates, retained schema fields, and decision semantics fixed. Only the monitor representation changes.",
        "",
        "## Field-set control",
        "",
        f"Raw and validated registries contain the same {report['field_set_control']['n_tools_raw']} tools and {report['field_set_control']['n_fields_raw']} fields: `{report['field_set_control']['same_tool_and_field_sets']}`.",
        "",
        "## Ordered-authorizer results",
        "",
        "| Dataset | Representation | Queries | UPA | False deny | Accuracy |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in report["ordered_authorizer_metrics"]:
        lines.append(
            f"| {row['dataset']} | {row['representation']} | {row['n_queries']} | "
            f"{row['unsafe_pre_allow']}/{row['n_unauthorized']} ({row['upa_rate']:.3f}) | "
            f"{row['false_deny']}/{row['n_authorized']} ({row['false_deny_rate']:.3f}) | "
            f"{row['decision_accuracy']:.3f} |"
        )
    lines += [
        "",
        "## Interpretation rule",
        "",
        "Validated atoms provide independent value only where they improve authorization separation or the UPA/false-denial frontier relative to representations with the same retained fields. A stricter result with worse false denial is reported as a tradeoff, not dominance.",
        "",
        "The pre-validation common-effect view is a deterministic coarse candidate, not a verbatim LLM output. The source oracle is used only for scoring.",
        "",
    ]
    return "\n".join(lines)


def run(*, output_dir: Path = OUT, smoke: bool = False) -> dict[str, Any]:
    protocol = verify_protocol()
    mechanism = load_mechanism()
    field_control = field_set_control()
    contexts = [add_views(row) for row in mechanism.normalize_agentdojo() + mechanism.normalize_toolsandbox()]
    if len(contexts) != protocol["acceptance"]["required_contexts"]:
        raise RuntimeError(f"expected 88 contexts, found {len(contexts)}")
    if smoke:
        selected = []
        for dataset, rows in sorted(_groups(contexts, lambda row: row["dataset"]).items()):
            selected.extend(rows[: min(8, len(rows))])
        contexts = selected

    policies, policy_generation = mechanism.generate_policies(contexts)
    policy_results = []
    witnesses = []
    for policy in policies:
        scoped = mechanism.contexts_for_policy(contexts, policy)
        for representation in REPRESENTATIONS:
            result, found = mechanism.analyze_policy_representation(policy, representation, scoped)
            policy_results.append(result)
            witnesses.extend(found)
    policy_aggregates = mechanism.aggregate_results(policy_results)
    decisions, authorizer_metrics = ordered_authorizer(contexts)
    agreements = atom_agreement(contexts)

    source_rows = [row for row in authorizer_metrics if row["representation"] == "source_effect_oracle"]
    validated_rows = [row for row in policy_aggregates if row["representation"] == "validated_typed_atoms"]
    if any(row["unsafe_pre_allow"] or row["false_deny"] for row in source_rows):
        raise RuntimeError("source oracle failed ordered-authorizer exactness")
    if any(row["minimum_deterministic_error_rate"] for row in validated_rows):
        raise RuntimeError("validated atoms have a collision under an exercised finite policy")

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "report_json": output_dir / "atom-vs-field-report.json",
        "report_md": output_dir / "atom-vs-field-report.md",
        "policy_metrics": output_dir / "policy-representation-metrics.csv",
        "authorizer_metrics": output_dir / "ordered-authorizer-metrics.csv",
        "decisions": output_dir / "ordered-authorizer-decisions.jsonl",
        "witnesses": output_dir / "ambiguity-witnesses.jsonl",
        "field_control": output_dir / "field-set-control.json",
        "atom_agreement": output_dir / "atom-agreement.csv",
    }
    write_csv(paths["policy_metrics"], policy_results)
    write_csv(paths["authorizer_metrics"], authorizer_metrics)
    write_jsonl(paths["decisions"], decisions)
    write_jsonl(paths["witnesses"], witnesses)
    write_csv(paths["atom_agreement"], agreements)
    paths["field_control"].write_text(json.dumps(field_control, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = {
        "experiment": "atom_vs_field_semantic_attribution",
        "mode": "smoke" if smoke else "full",
        "status": "passed",
        "protocol_sha256": sha256(PROTOCOL),
        "n_contexts": len(contexts),
        "field_set_control": field_control,
        "policy_generation": policy_generation,
        "n_policy_result_rows": len(policy_results),
        "n_ordered_decision_rows": len(decisions),
        "n_ambiguity_witnesses": len(witnesses),
        "policy_aggregates": policy_aggregates,
        "ordered_authorizer_metrics": authorizer_metrics,
        "atom_agreement": agreements,
        "negative_result_policy": "No atom-advantage threshold is required; all complete outcomes are retained.",
        "claim_boundary": protocol["claim_boundary"],
        "outputs": {name: str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path) for name, path in paths.items()},
    }
    paths["report_json"].write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["report_md"].write_text(build_markdown(report), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("smoke", "full"), default="full")
    parser.add_argument("--output-dir", type=Path, default=OUT)
    args = parser.parse_args()
    report = run(output_dir=args.output_dir, smoke=args.mode == "smoke")
    print(json.dumps({key: report[key] for key in ("status", "mode", "n_contexts", "n_policy_result_rows", "n_ordered_decision_rows")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
