#!/usr/bin/env python3
"""Decision-level validation against a mechanically separated native oracle."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.compatibility.scripts.third_party_authorization_interface_validation.descriptor_compiler import (
    compile_descriptor, initial_descriptors,
)
from shared.compatibility.scripts.third_party_authorization_interface_validation.descriptor_mutations import (
    compile_mutant, mutation_manifest,
)
from shared.compatibility.scripts.third_party_authorization_interface_validation.native_delta_oracle import native_deltas
from shared.compatibility.scripts.third_party_authorization_interface_validation.native_policy import authorize_native
from shared.compatibility.scripts.third_party_authorization_interface_validation.policy import authorize_all


ROOT = REPO_ROOT
OLD_EVAL = ROOT / "experiments/human-authority-and-causal-validation/evaluation/third-party-authorization-interface-validation"
OLD_RESULTS = ROOT / "experiments/human-authority-and-causal-validation/results/third-party-authorization-interface-validation"
EVAL = ROOT / "experiments/human-authority-and-causal-validation/evaluation/native-delta-mechanical-validation"
RESULTS = ROOT / "experiments/human-authority-and-causal-validation/results/native-delta-mechanical-validation"


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha_value(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _forbidden_imports(path: Path, forbidden: set[str]) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return sorted(item for item in imports if any(name in item for name in forbidden))


def evaluate_original(rows: list[dict[str, Any]], descriptors: dict[str, dict[str, Any]],
                      manifest: dict[str, Any], phase: str) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        deltas = native_deltas(row)
        native_decision, native_reasons = authorize_native(row, deltas, manifest)
        try:
            typed = compile_descriptor(descriptors[row["tool_name"]], row)
            typed_decision, typed_reasons = authorize_all(typed, manifest, partial=False, inventory_complete=True)
            error = None
        except Exception as exc:
            typed, typed_decision, typed_reasons = [], "ABSTAIN", ["compile_failure"]
            error = f"{type(exc).__name__}:{exc}"
        output.append({
            "case_id": row["case_id"], "phase": phase, "tool_name": row["tool_name"], "source": row["source"],
            "native_deltas": deltas, "native_decision": native_decision, "native_reasons": native_reasons,
            "typed_decision": typed_decision, "typed_reasons": typed_reasons,
            "typed_compile_error": error, "decision_match": native_decision == typed_decision,
        })
    return output


def evaluate_mutants(registration: list[dict[str, Any]], evaluation: list[dict[str, Any]],
                     descriptors: dict[str, dict[str, Any]], manifest: dict[str, Any],
                     mutants: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summaries, certificates = [], []
    for mutant in mutants:
        tool = mutant["tool_name"]
        outcomes: dict[str, list[dict[str, Any]]] = {"registration": [], "evaluation": []}
        for phase, rows in (("registration", registration), ("evaluation", evaluation)):
            for row in rows:
                if row["tool_name"] != tool:
                    continue
                native, _ = authorize_native(row, native_deltas(row), manifest)
                try:
                    effects = compile_mutant(descriptors[tool], row, mutant["operator"])
                    decision, reasons = authorize_all(effects, manifest, partial=False, inventory_complete=True)
                    error = None
                except Exception as exc:
                    decision, reasons = "ABSTAIN", ["compile_failure"]
                    error = f"{type(exc).__name__}:{exc}"
                outcomes[phase].append({
                    "case_id": row["case_id"], "native_decision": native, "mutant_decision": decision,
                    "decision_mismatch": native != decision, "compile_error": error, "reasons": reasons,
                })
        registration_failures = [row for row in outcomes["registration"] if row["decision_mismatch"]]
        evaluation_failures = [row for row in outcomes["evaluation"] if row["decision_mismatch"]]
        status = ("killed_registration" if registration_failures else
                  "escaped_to_heldout" if evaluation_failures else "equivalent_in_frozen_domain")
        summary = {
            **mutant, "status": status, "registration_cases": len(outcomes["registration"]),
            "registration_failures": len(registration_failures), "evaluation_cases": len(outcomes["evaluation"]),
            "evaluation_failures": len(evaluation_failures),
        }
        summaries.append(summary)
        if registration_failures or evaluation_failures:
            first = (registration_failures or evaluation_failures)[0]
            certificates.append({
                "mutant_id": mutant["mutant_id"], "operator": mutant["operator"], "tool_name": tool,
                "detected_phase": "registration" if registration_failures else "evaluation",
                **first,
            })
    return summaries, certificates


def main() -> int:
    EVAL.mkdir(parents=True, exist_ok=True); RESULTS.mkdir(parents=True, exist_ok=True)
    descriptors_list = initial_descriptors()
    descriptors = {item["tool_name"]: item for item in descriptors_list}
    mutants = mutation_manifest(descriptors_list)
    registration = read_jsonl(OLD_RESULTS / "registration_source_executions.jsonl")
    evaluation = read_jsonl(OLD_RESULTS / "post_freeze_source_executions.jsonl")
    manifest = json.loads((OLD_EVAL / "authority_manifest.json").read_text(encoding="utf-8"))

    native_path = ROOT / "shared/compatibility/scripts/third_party_authorization_interface_validation/native_delta_oracle.py"
    native_policy_path = ROOT / "shared/compatibility/scripts/third_party_authorization_interface_validation/native_policy.py"
    compiler_path = ROOT / "shared/compatibility/scripts/third_party_authorization_interface_validation/descriptor_compiler.py"
    isolation = {
        "native_oracle_forbidden_imports": _forbidden_imports(native_path, {"descriptor", "policy", "representations"}),
        "native_policy_forbidden_imports": _forbidden_imports(native_policy_path, {"descriptor", "source_oracle", "representations"}),
        "compiler_forbidden_imports": _forbidden_imports(compiler_path, {"native_delta", "native_policy", "source_oracle"}),
    }
    protocol = {
        "protocol": "native-delta-mechanical-validation-v1",
        "old_registration_sha256": sha(OLD_RESULTS / "registration_source_executions.jsonl"),
        "old_evaluation_sha256": sha(OLD_RESULTS / "post_freeze_source_executions.jsonl"),
        "old_context_manifest_sha256": sha(OLD_EVAL / "protocol_manifest.json"),
        "authority_manifest_sha256": sha(OLD_EVAL / "authority_manifest.json"),
        "descriptor_sha256": sha_value(descriptors_list), "mutation_manifest_sha256": sha_value(mutants),
        "source_hashes": {str(path.relative_to(ROOT)): sha(path) for path in (native_path, native_policy_path, compiler_path,
            ROOT / "shared/compatibility/scripts/third_party_authorization_interface_validation/descriptor_mutations.py",
            Path(__file__))},
        "mechanical_isolation": isolation,
        "human_descriptor_authorship": False,
        "claim_boundary": "Mechanically separated same-project conformance, not independent semantic certification.",
    }
    protocol["protocol_hash"] = sha_value(protocol)
    write_json(EVAL / "protocol_manifest.json", protocol)
    write_json(EVAL / "mutation_manifest.json", {"mutants": mutants, "sha256": sha_value(mutants)})

    registration_rows = evaluate_original(registration, descriptors, manifest, "registration")
    evaluation_rows = evaluate_original(evaluation, descriptors, manifest, "evaluation")
    mutant_rows, certificates = evaluate_mutants(registration, evaluation, descriptors, manifest, mutants)
    write_jsonl(RESULTS / "native_decision_rows.jsonl", registration_rows + evaluation_rows)
    write_jsonl(RESULTS / "mutant_results.jsonl", mutant_rows)
    write_jsonl(RESULTS / "mutation_failure_certificates.jsonl", certificates)

    counts = {name: sum(row["status"] == name for row in mutant_rows) for name in
              ("killed_registration", "escaped_to_heldout", "equivalent_in_frozen_domain")}
    report = {
        "status": "passed" if len(registration_rows) == 264 and len(evaluation_rows) == 264 and
                  not any(isolation.values()) else "failed",
        "protocol_hash": protocol["protocol_hash"], "registration_contexts": len(registration_rows),
        "evaluation_contexts": len(evaluation_rows), "registration_decision_agreement":
            sum(row["decision_match"] for row in registration_rows) / len(registration_rows),
        "evaluation_decision_agreement": sum(row["decision_match"] for row in evaluation_rows) / len(evaluation_rows),
        "compile_failures": sum(row["typed_compile_error"] is not None for row in registration_rows + evaluation_rows),
        "n_mutants": len(mutant_rows), "mutation_outcomes": counts,
        "registration_detection_rate_among_non_equivalent": counts["killed_registration"] /
            max(1, counts["killed_registration"] + counts["escaped_to_heldout"]),
        "mechanical_isolation": isolation, "all_rows_retained": True,
        "claim_boundary": protocol["claim_boundary"],
    }
    write_json(RESULTS / "native_delta_validation_report.json", report)
    with (RESULTS / "mutation_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(mutant_rows[0])); writer.writeheader(); writer.writerows(mutant_rows)
    (RESULTS / "native_delta_validation_report.md").write_text(
        "# Native-Delta Mechanical Validation\n\n"
        f"Status: `{report['status']}`. Registration/evaluation decision agreement: "
        f"`{report['registration_decision_agreement']:.3f}` / `{report['evaluation_decision_agreement']:.3f}`.\n\n"
        f"Mutants: `{report['n_mutants']}`; outcomes: `{counts}`.\n\n"
        "This is mechanically separated, same-project bounded conformance, not independent authorship.\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
