#!/usr/bin/env python3
"""Run registration and descriptor-blind evaluation on pinned MCP tools."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

IMPORT_ROOT = Path(__file__).resolve().parents[3]
if str(IMPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(IMPORT_ROOT))

from shared.compatibility.scripts.third_party_authorization_interface_validation.descriptor_compiler import (
    compile_descriptor, initial_descriptors,
)
from shared.compatibility.scripts.third_party_authorization_interface_validation.evaluation_generator import generate_evaluation_rows
from shared.compatibility.scripts.third_party_authorization_interface_validation.policy import authority_manifest, authorize_all
from shared.compatibility.scripts.third_party_authorization_interface_validation.registration_generator import generate_registration_rows
from shared.compatibility.scripts.third_party_authorization_interface_validation.representations import (
    canonical, diagnostic_effects, representation_keys,
)
from shared.compatibility.scripts.third_party_authorization_interface_validation.scenario_data import TOOL_SOURCES
from shared.compatibility.scripts.third_party_authorization_interface_validation.source_oracle import source_effects
from shared.compatibility.scripts.third_party_authorization_interface_validation.sources import ROOT, SOURCES, discover_schemas, execute


EVAL = ROOT / "experiments/human-authority-and-causal-validation/evaluation/third-party-authorization-interface-validation"
RESULTS = ROOT / "experiments/human-authority-and-causal-validation/results/third-party-authorization-interface-validation"
REPRESENTATIONS = ("tool_name", "raw_call", "state_aware_raw_call", "common_field", "typed_effect", "source_effect_oracle")
SOURCE_CONFIG = {
    "filesystem": {
        "path": SOURCES / "modelcontextprotocol-servers", "license": "MIT", "license_evidence": "LICENSE",
        "implementation": ["src/filesystem/index.ts", "src/filesystem/package.json"],
        "url": "https://github.com/modelcontextprotocol/servers.git",
    },
    "sqlite": {
        "path": SOURCES / "mcp-sqlite", "license": "MIT", "license_evidence": "LICENSE",
        "implementation": ["mcp-sqlite-server.js", "package.json"],
        "url": "https://github.com/jparkerweb/mcp-sqlite.git",
    },
    "memory": {
        "path": SOURCES / "simple-memory-mcp", "license": "MIT",
        "license_evidence": "package.json and README; repository has no standalone LICENSE file",
        "implementation": ["index.js", "package.json"],
        "url": "https://github.com/AojdevStudio/simple-memory-mcp.git",
    },
}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_json(value: Any) -> str:
    return sha_bytes(canonical(value).encode())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def git(path: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()


def source_manifest() -> dict[str, Any]:
    schemas = discover_schemas()
    values = []
    for source, config in SOURCE_CONFIG.items():
        selected = sorted((tool for tool in schemas[source] if tool["name"] in TOOL_SOURCES), key=lambda item: item["name"])
        implementation_hashes = {name: sha_bytes((config["path"] / name).read_bytes()) for name in config["implementation"]}
        values.append({
            "source": source, "public_url": config["url"], "commit": git(config["path"], "rev-parse", "HEAD"),
            "git_clean": git(config["path"], "status", "--short") == "", "license": config["license"],
            "license_evidence": config["license_evidence"], "implementation_hashes": implementation_hashes,
            "implementation_hash": sha_json(implementation_hashes), "selected_tool_names": [tool["name"] for tool in selected],
            "selected_schema_hash": sha_json(selected), "selected_schemas": selected,
            "sandboxing": "fresh local disposable fixture per invocation; no network or external side effect",
        })
    return {"sources": values, "all_preflight_passed": all(item["git_clean"] for item in values)}


def execute_rows(rows: list[dict[str, Any]], descriptors: dict[str, dict[str, Any]], *, phase: str) -> list[dict[str, Any]]:
    output = []
    for index, context in enumerate(rows, 1):
        executed = {**context, **execute(context)}
        try:
            source = source_effects(executed)
        except Exception as exc:
            source = []
            executed["source_oracle_error"] = f"{type(exc).__name__}:{exc}"
        try:
            typed = compile_descriptor(descriptors[context["tool_name"]], executed)
            compile_error = None
        except Exception as exc:
            typed, compile_error = [], f"{type(exc).__name__}:{exc}"
        executed.update({
            "source_effects": source, "typed_effects": typed, "descriptor_compile_error": compile_error,
            "descriptor_exact_match": compile_error is None and source == typed,
            "descriptor_hash": sha_json(descriptors[context["tool_name"]]), "ordinal": index, "execution_phase": phase,
        })
        output.append(executed)
    return output


def collision_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for representation in REPRESENTATIONS:
        cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            cells[row["representation_keys"][representation]].append(row)
        mixed = [values for values in cells.values() if len({row["ideal_decision"] for row in values}) > 1]
        separating = sum(
            sum(row["ideal_decision"] == "ALLOW" for row in values) *
            sum(row["ideal_decision"] == "DENY" for row in values)
            for values in mixed
        )
        output.append({
            "representation": representation, "n_contexts": len(rows), "n_cells": len(cells),
            "mixed_cells": len(mixed), "separating_pairs": separating,
            "max_cell_size": max(map(len, cells.values())),
        })
    return output


def decision_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for representation in REPRESENTATIONS:
        decisions = [row["monitor_decisions"][representation] for row in rows]
        ideal = [row["ideal_decision"] for row in rows]
        ideal_deny, ideal_allow = ideal.count("DENY"), ideal.count("ALLOW")
        unsafe = sum(a == "DENY" and b == "ALLOW" for a, b in zip(ideal, decisions))
        false_deny = sum(a == "ALLOW" and b == "DENY" for a, b in zip(ideal, decisions))
        abstain = decisions.count("ABSTAIN")
        output.append({
            "representation": representation, "n_contexts": len(rows),
            "unsafe_allow_n": unsafe, "unsafe_allow_denom": ideal_deny,
            "unsafe_allow_rate": unsafe / ideal_deny if ideal_deny else 0.0,
            "false_deny_n": false_deny, "false_deny_denom": ideal_allow,
            "false_deny_rate": false_deny / ideal_allow if ideal_allow else 0.0,
            "abstain_n": abstain, "abstain_rate": abstain / len(rows),
            "coverage": (len(rows) - abstain) / len(rows),
            "decision_accuracy": sum(a == b for a, b in zip(ideal, decisions)) / len(rows),
        })
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="replace this experiment's generated artifacts")
    args = parser.parse_args()
    EVAL.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    sources = source_manifest()
    if not sources["all_preflight_passed"]:
        write_json(RESULTS / "rejection_report.json", sources)
        raise SystemExit("third-party source preflight failed")

    registration_contexts = generate_registration_rows()
    evaluation_contexts = generate_evaluation_rows()
    descriptors_list = initial_descriptors()
    descriptors = {item["tool_name"]: item for item in descriptors_list}
    harness_files = [
        Path(__file__),
        ROOT / "shared/compatibility/scripts/third_party_authorization_interface_validation/registration_generator.py",
        ROOT / "shared/compatibility/scripts/third_party_authorization_interface_validation/evaluation_generator.py",
        ROOT / "shared/compatibility/scripts/third_party_authorization_interface_validation/scenario_data.py",
        ROOT / "shared/compatibility/scripts/third_party_authorization_interface_validation/source_oracle.py",
        ROOT / "shared/compatibility/scripts/third_party_authorization_interface_validation/descriptor_compiler.py",
        ROOT / "shared/compatibility/scripts/third_party_authorization_interface_validation/policy.py",
        ROOT / "shared/compatibility/scripts/third_party_authorization_interface_validation/representations.py",
        ROOT / "shared/compatibility/scripts/third_party_authorization_interface_validation/sources.py",
        ROOT / "shared/compatibility/scripts/third_party_authorization_interface_validation/mcp_client.py",
    ]
    protocol = {
        "protocol": "third-party-authorization-interface-validation-v3",
        "registration_pairs_per_tool": 12, "registration_executions": len(registration_contexts),
        "evaluation_contexts_per_tool": 24, "post_freeze_executions": len(evaluation_contexts),
        "tool_count": len(TOOL_SOURCES), "registration_context_hash": sha_json(registration_contexts),
        "evaluation_context_hash": sha_json(evaluation_contexts), "descriptor_v1_hash": sha_json(descriptors_list),
        "source_manifest_hash": sha_json(sources), "policy_hash": sha_json(authority_manifest()),
        "harness_source_hashes": {str(path.relative_to(ROOT)): sha_bytes(path.read_bytes()) for path in harness_files},
        "generator_isolation": "evaluation generator imports neither descriptor, policy, oracle, nor registration outcomes",
        "refinement_provenance": {"rule_generated": len(descriptors_list), "llm_seeded": 0,
                                  "ai_assisted_edit": 0, "human_edit": 0, "human_refinements": 0},
    }
    protocol["protocol_hash"] = sha_json(protocol)
    manifest_path = EVAL / "protocol_manifest.json"
    if manifest_path.exists() and not args.force:
        old = json.loads(manifest_path.read_text())
        if old != protocol:
            raise SystemExit("protocol drift; use a new version, do not overwrite frozen artifacts")
    write_json(manifest_path, protocol)
    write_json(EVAL / "source_manifest.json", sources)
    write_json(EVAL / "authority_manifest.json", authority_manifest())
    write_json(EVAL / "descriptors_v1.json", {"descriptors": descriptors_list})
    write_jsonl(EVAL / "registration_contexts.jsonl", registration_contexts)
    write_jsonl(EVAL / "post_freeze_contexts.jsonl", evaluation_contexts)

    registration = execute_rows(registration_contexts, descriptors, phase="registration")
    write_jsonl(RESULTS / "registration_source_executions.jsonl", registration)
    registration_failures = [row for row in registration if not row["descriptor_exact_match"]]
    write_jsonl(RESULTS / "registration_failures.jsonl", registration_failures)

    evaluation = execute_rows(evaluation_contexts, descriptors, phase="post_freeze-evaluation")
    manifest = authority_manifest()
    decision_rows = []
    for row in evaluation:
        ideal, ideal_reasons = authorize_all(row["source_effects"], manifest, partial=False, inventory_complete=True)
        keys = representation_keys(row, row["typed_effects"], row["source_effects"])
        monitor_decisions, monitor_reasons = {}, {}
        for name in REPRESENTATIONS:
            effects, complete = diagnostic_effects(name, row, descriptors[row["tool_name"]],
                                                   row["typed_effects"], row["source_effects"])
            decision, reasons = authorize_all(effects, manifest, partial=True, inventory_complete=complete)
            monitor_decisions[name], monitor_reasons[name] = decision, reasons
        decision_rows.append({
            **row, "ideal_decision": ideal, "ideal_reasons": ideal_reasons, "representation_keys": keys,
            "monitor_decisions": monitor_decisions, "monitor_reasons": monitor_reasons,
        })
    write_jsonl(RESULTS / "post_freeze_source_executions.jsonl", evaluation)
    write_jsonl(RESULTS / "post_freeze_authorization_rows.jsonl", decision_rows)
    collisions, decisions = collision_metrics(decision_rows), decision_metrics(decision_rows)

    with (RESULTS / "representation_collision_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(collisions[0]))
        writer.writeheader(); writer.writerows(collisions)
    with (RESULTS / "authorization_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(decisions[0]))
        writer.writeheader(); writer.writerows(decisions)

    post_failures = [row for row in decision_rows if not row["descriptor_exact_match"]]
    write_jsonl(RESULTS / "post_freeze_descriptor_failures.jsonl", post_failures)
    by_source = Counter(row["source"] for row in decision_rows)
    report = {
        "status": "passed" if len(registration) == 264 and len(evaluation) == 264 and
                                  not any(row.get("execution_error") or row.get("source_oracle_error") for row in registration + evaluation)
                                  else "failed",
        "protocol_hash": protocol["protocol_hash"], "n_tools": len(TOOL_SOURCES),
        "n_registration_executions": len(registration), "n_post_freeze_contexts": len(evaluation),
        "contexts_by_source": dict(by_source), "registration_descriptor_failures": len(registration_failures),
        "post_freeze_descriptor_failures": len(post_failures), "descriptor_exact_match_rate":
            sum(row["descriptor_exact_match"] for row in evaluation) / len(evaluation),
        "collision_metrics": collisions, "authorization_metrics": decisions,
        "human_refinements": 0, "post_freeze_failures_preserved": True,
        "claim_boundary": "Independent implementations and descriptor-blind frozen contexts provide finite-domain falsification or bounded conformance evidence; zero collisions are not open-world certification.",
    }
    write_json(RESULTS / "third_party_validation_report.json", report)
    lines = [
        "# Third-Party Authorization-Interface Validation", "",
        f"Status: `{report['status']}`. Eleven tools from three pinned public MCP implementations were executed in disposable local fixtures.", "",
        f"Registration used {len(registration)} executions; post-freeze evaluation used {len(evaluation)} disjoint contexts. Human refinements: 0.", "",
        "## Collision Results", "", "| Representation | Cells | Mixed cells | Separating pairs |", "|---|---:|---:|---:|",
    ]
    lines += [f"| {m['representation']} | {m['n_cells']} | {m['mixed_cells']} | {m['separating_pairs']} |" for m in collisions]
    lines += ["", "## Diagnostic Authorization", "", "| Representation | UPA | False denial | Coverage | Accuracy |", "|---|---:|---:|---:|---:|"]
    lines += [f"| {m['representation']} | {m['unsafe_allow_rate']:.3f} | {m['false_deny_rate']:.3f} | {m['coverage']:.3f} | {m['decision_accuracy']:.3f} |" for m in decisions]
    lines += ["", "The state-aware and raw-call authorization rows use disclosed, static request adapters. Collision counts are the pure observation-interface result.", ""]
    (RESULTS / "third_party_validation_report.md").write_text("\n".join(lines), encoding="utf-8")
    table = ["\\begin{tabular}{lrrr}", "\\toprule", "Interface & Cells & Mixed & Separating pairs \\\\", "\\midrule"]
    table += [f"{m['representation'].replace('_', ' ')} & {m['n_cells']} & {m['mixed_cells']} & {m['separating_pairs']} \\\\" for m in collisions[:-1]]
    table += ["\\bottomrule", "\\end{tabular}"]
    (RESULTS / "table_third_party_validation.tex").write_text("\n".join(table) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
