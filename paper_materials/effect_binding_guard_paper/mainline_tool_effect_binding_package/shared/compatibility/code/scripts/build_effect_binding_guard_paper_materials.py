from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "paper_materials/effect_binding_guard_paper"
LARGE_FILE_BYTES = 2_000_000
CLAIM_BOUNDARY = (
    "controlled custom-stress robustness and method-feasibility evidence only; "
    "not production safety, not a complete permission system, not original-paper "
    "benchmark reproduction, and not a real-world deployment safety certificate"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build E51 Effect-Binding Guard paper materials package.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--large-file-bytes", type=int, default=LARGE_FILE_BYTES)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = Path(args.output)
    if not output.is_absolute():
        output = (ROOT / output).resolve()
    if args.validate_only:
        validate_package(output)
        print(f"validated {output}")
        return
    if output.exists():
        if not args.force:
            raise SystemExit(f"{output} exists; rerun with --force to rebuild")
        shutil.rmtree(output)
    builder = PackageBuilder(output, large_file_bytes=args.large_file_bytes)
    builder.build()
    validate_package(output)
    print(f"built {output}")


class PackageBuilder:
    def __init__(self, output: Path, *, large_file_bytes: int) -> None:
        self.output = output
        self.large_file_bytes = large_file_bytes
        self.inventory: list[dict[str, Any]] = []

    def build(self) -> None:
        self.make_dirs()
        self.collect_artifacts()
        self.write_inventory()
        self.write_code_index()
        self.write_data_index()
        table_payloads = self.write_tables()
        self.write_figures()
        self.write_summaries(table_payloads)
        self.write_reproduction()
        self.write_claim_boundary(table_payloads)
        self.write_failure_examples()
        self.write_e55_materials()
        self.write_readme(table_payloads)
        self.write_package_checklist()

    def make_dirs(self) -> None:
        for relative in (
            "code_index/source_files",
            "data_index/source_files",
            "results/source_artifacts",
            "tables",
            "figures",
            "summaries",
            "reproduction",
            "claim_boundary",
            "failure_examples",
            "appendix/source_artifacts",
            "e55_precommit_authz",
            "ndss_candidate",
        ):
            (self.output / relative).mkdir(parents=True, exist_ok=True)

    def collect_artifacts(self) -> None:
        for spec in artifact_specs():
            source = ROOT / spec["path"]
            self.add_artifact(source, spec)
        for source in discovered_code_files():
            self.add_artifact(
                source,
                {
                    "path": rel(source),
                    "artifact_type": "code",
                    "experiment_phase": phase_for_path(source),
                    "paper_role": "reproduction",
                    "description": "Relevant implementation source file.",
                    "required_for_reproduction": True,
                    "contains_oracle_or_labels": False,
                    "safe_to_cite_as_deployable_result": False,
                },
            )

    def add_artifact(self, source: Path, spec: dict[str, Any]) -> None:
        exists = source.exists()
        artifact_type = spec.get("artifact_type") or artifact_type_for_path(source)
        dest = self.package_destination(source, artifact_type)
        entry = {
            "source_path": spec["path"],
            "package_path": rel(dest, self.output),
            "artifact_type": artifact_type,
            "experiment_phase": spec.get("experiment_phase") or phase_for_path(source),
            "paper_role": spec.get("paper_role", "diagnostic"),
            "description": spec.get("description", ""),
            "required_for_reproduction": bool(spec.get("required_for_reproduction", False)),
            "contains_oracle_or_labels": bool(spec.get("contains_oracle_or_labels", False)),
            "safe_to_cite_as_deployable_result": bool(spec.get("safe_to_cite_as_deployable_result", False)),
            "exists": exists,
            "copy_mode": "missing",
            "file_size": None,
            "sha256": None,
            "symlink_target": None,
        }
        if exists:
            dest.parent.mkdir(parents=True, exist_ok=True)
            size = source.stat().st_size
            entry["file_size"] = size
            entry["sha256"] = sha256(source)
            if size > self.large_file_bytes:
                target = os.path.relpath(source, start=dest.parent)
                dest.symlink_to(target)
                entry["copy_mode"] = "relative_symlink"
                entry["symlink_target"] = target
            else:
                shutil.copy2(source, dest)
                entry["copy_mode"] = "copy"
        self.inventory.append(entry)

    def package_destination(self, source: Path, artifact_type: str) -> Path:
        safe_name = rel(source).replace("/", "__")
        if artifact_type in {"code", "test", "script"}:
            return self.output / "code_index/source_files" / safe_name
        if artifact_type == "data":
            return self.output / "data_index/source_files" / safe_name
        if artifact_type in {"result_json", "result_md", "table", "figure"}:
            return self.output / "results/source_artifacts" / safe_name
        return self.output / "appendix/source_artifacts" / safe_name

    def write_inventory(self) -> None:
        write_json(self.output / "artifact_inventory.json", self.inventory)
        rows = [
            [
                "Source",
                "Package",
                "Type",
                "Phase",
                "Role",
                "Repro",
                "Oracle/Labels",
                "Deployable Cite",
                "Mode",
                "Description",
            ]
        ]
        for item in self.inventory:
            rows.append(
                [
                    item["source_path"],
                    item["package_path"],
                    item["artifact_type"],
                    item["experiment_phase"],
                    item["paper_role"],
                    str(item["required_for_reproduction"]),
                    str(item["contains_oracle_or_labels"]),
                    str(item["safe_to_cite_as_deployable_result"]),
                    item["copy_mode"],
                    item["description"],
                ]
            )
        write_markdown_table(self.output / "artifact_inventory.md", "Artifact Inventory", rows)

    def write_code_index(self) -> None:
        code_rows = [item for item in self.inventory if item["artifact_type"] in {"code", "test", "script"}]
        payload = []
        for item in sorted(code_rows, key=lambda row: row["source_path"]):
            payload.append(
                {
                    "path": item["source_path"],
                    "experiment_phase": item["experiment_phase"],
                    "role": item["paper_role"],
                    "description": code_description(item["source_path"]),
                    "command": command_for_code(item["source_path"]),
                    "inputs": inputs_for_code(item["source_path"]),
                    "outputs": outputs_for_code(item["source_path"]),
                    "scope": scope_for_code(item["source_path"]),
                }
            )
        write_json(self.output / "code_index/code_index.json", payload)
        lines = ["# Code Index", ""]
        for row in payload:
            lines.extend(
                [
                    f"## `{row['path']}`",
                    "",
                    f"- Phase: `{row['experiment_phase']}`",
                    f"- Scope: `{row['scope']}`",
                    f"- What it does: {row['description']}",
                    f"- Command: `{row['command']}`",
                    f"- Inputs: {row['inputs']}",
                    f"- Outputs: {row['outputs']}",
                    "",
                ]
            )
        write_text(self.output / "code_index/code_index.md", "\n".join(lines))

    def write_data_index(self) -> None:
        data_items = [item for item in self.inventory if item["artifact_type"] == "data"]
        payload = []
        for item in sorted(data_items, key=lambda row: row["source_path"]):
            source = ROOT / item["source_path"]
            payload.append(dataset_summary(source, item))
        write_json(self.output / "data_index/data_index.json", payload)
        rows = [["Dataset", "Rows", "Phase", "Use", "Audit Status", "Label Provenance", "Oracle/Leakage Risk", "Role"]]
        for row in payload:
            rows.append(
                [
                    row["path"],
                    str(row["row_count"]),
                    row["experiment_phase"],
                    row["usage"],
                    row["audit_status"],
                    row["label_provenance"],
                    row["oracle_or_leakage_risk"],
                    row["paper_role"],
                ]
            )
        write_markdown_table(self.output / "data_index/data_index.md", "Data Index", rows)

    def write_tables(self) -> dict[str, list[dict[str, Any]]]:
        tables = {
            "e47_measurement_existing_defenses": table_e47_measurement(),
            "e48_main_method": table_e48_main(),
            "e48_source_specific": table_e48_source_specific(),
            "e49_learned_calibrator_diagnostic": table_e49_diagnostic(),
            "e50_robustness": table_e50_robustness(),
            "e55_precommit_authorization": table_e55_precommit_authz(),
            "final_capability_matrix": table_final_capability(),
        }
        for name, rows in tables.items():
            write_table_bundle(self.output / "tables", name, rows)
        return tables

    def write_figures(self) -> None:
        figure_specs = {
            "figure_1_problem_setup.md": "Show an agent task, available tools, candidate action, and realized effect/resource/authorization/provenance tuple.",
            "figure_2_counterfactual_lattice.md": "Depict the Phase 4 paired counterfactual lattice: same effect with surface shifts, same tool with effect changes, resource changes, and authorization flips.",
            "figure_3_effect_binding_guard_pipeline.md": "Pipeline: non-oracle input views -> tuple inference -> multi-view disagreement -> selective evidence fallback -> provenance overlay -> ALLOW/DENY/ABSTAIN.",
            "figure_4_safety_coverage_tradeoff.md": "Use E50 threshold/risk-coverage data to plot unsafe pre-allow and safe false deny against coverage.",
            "figure_5_failure_modes.md": "Taxonomy of residual failures: resource alias, broad/narrow authorization, draft-vs-commit, evidence unavailable, provenance uncertainty, over-abstention.",
        }
        existing_data = [
            "analysis/results/e50_risk_coverage_curves.json",
            "analysis/results/e50_threshold_sensitivity.json",
            "analysis/results/tool_effect_fragmentation_counterfactual_phase4.json",
        ]
        for filename, description in figure_specs.items():
            write_text(
                self.output / "figures" / filename,
                f"# {filename.removesuffix('.md').replace('_', ' ').title()}\n\n"
                f"Purpose: {description}\n\n"
                "Data references:\n"
                + "\n".join(f"- `{path}`" for path in existing_data if (ROOT / path).exists())
                + "\n\nNo new plot is generated by E51; this file is a deterministic figure specification.\n",
            )
        write_json(
            self.output / "figures/figure_specs.json",
            [{"file": key, "description": value, "data_references": existing_data} for key, value in figure_specs.items()],
        )

    def write_summaries(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        metrics = key_metrics()
        summaries = {
            "00_executive_summary.md": executive_summary(metrics),
            "01_motivation_and_measurement.md": motivation_summary(metrics),
            "02_method_effect_binding_guard.md": method_summary(),
            "03_main_results_e48.md": e48_summary(metrics),
            "04_learned_calibration_e49.md": e49_summary(metrics),
            "05_robustness_e50.md": e50_summary(metrics),
            "06_failure_taxonomy.md": failure_taxonomy_summary(),
            "07_claim_boundary_and_limitations.md": claim_boundary_summary(),
            "08_paper_outline.md": paper_outline_summary(),
            "09_precommit_authorization_e55.md": e55_summary(metrics),
        }
        for name, text in summaries.items():
            write_text(self.output / "summaries" / name, text)

    def write_reproduction(self) -> None:
        files = {
            "reproduce_e48.md": (
                "# Reproduce E48\n\n"
                "Commands:\n\n"
                "```bash\n"
                "python -m src.experiments.effect_binding_guard.local_qwen --resume --max-tokens 192\n"
                "python -m src.experiments.effect_binding_guard.run_e48 --bootstrap-iters 2000\n"
                "```\n\n"
                "Expected key outputs: `analysis/results/e48_tuple_guard_results.json`, `analysis/results/e48_local_qwen_tuple_predictions.jsonl`.\n"
                "Local-Qwen inference requires the local GGUF/OpenAI-compatible setup used by E48; if predictions already contain exactly 822 unique rows, rerun only `run_e48`.\n"
            ),
            "reproduce_e49.md": (
                "# Reproduce E49\n\n"
                "Commands:\n\n"
                "```bash\n"
                "python -m src.experiments.effect_binding_calibrator.run_e49 --bootstrap-iters 2000\n"
                "```\n\n"
                "Expected key outputs: `analysis/results/e49_learned_fusion_results.json`, `data/e49_effect_binding_fusion_features.jsonl`.\n"
                "E49 is diagnostic only and must not replace the E48 hard guard as the main method.\n"
            ),
            "reproduce_e50.md": (
                "# Reproduce E50\n\n"
                "Commands:\n\n"
                "```bash\n"
                "python -m src.experiments.effect_binding_guard.run_e50 --bootstrap-iters 2000\n"
                "```\n\n"
                "Expected key outputs: `analysis/results/e50_hard_guard_robustness_results.json`, `data/e50_resource_authorization_stress.jsonl`, `data/e50_control_provenance_stress.jsonl`.\n"
            ),
            "reproduce_e55.md": (
                "# Reproduce E55\n\n"
                "Commands:\n\n"
                "```bash\n"
                "python -m src.experiments.effect_binding_guard.e55_precommit_authz.run_e55 --output analysis/results/e55_precommit_authz_results.json\n"
                "```\n\n"
                "Expected key outputs: `data/e55_precommit_authz_dataset.jsonl`, `analysis/results/e55_precommit_authz_results.json`, and `paper_materials/effect_binding_guard_paper/e55_precommit_authz/`.\n"
                "E55 is deterministic, local-only, does not call models, and does not execute real external side effects.\n"
            ),
            "environment_notes.md": (
                "# Environment Notes\n\n"
                "- E51 itself does not require GPU, model inference, external APIs, or real tool execution.\n"
                "- E48 local-Qwen prediction regeneration requires the local GGUF setup documented in the E48 experiment README.\n"
                "- Do not merge partial local-Qwen shards unless the final file has exactly 822 unique case IDs.\n"
                "- E47 official-checkpoint custom stress results are custom-stress evaluations, not original-paper benchmark reproduction.\n"
                "- E55 uses deterministic mock pre-commit tools and explicit authorization contexts; it is not production or SaaS validation.\n"
            ),
        }
        for name, content in files.items():
            write_text(self.output / "reproduction" / name, content)

    def write_claim_boundary(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        allowed = [
            "The package supports a controlled custom-stress measurement and method-feasibility paper.",
            "Existing defenses are not merely tool-name classifiers, but joint effect/resource/authorization/provenance reasoning remains weak.",
            "The hard Effect-Binding Guard improves the custom-stress safety/coverage tradeoff relative to individual hard modules.",
            "Resource/authorization binding remains the primary bottleneck in E50.",
            "E55 supports a narrow local claim that explicit authorization infrastructure can improve coverage while preserving low unsafe pre-allow on deterministic mock pre-commit schemas.",
        ]
        disallowed = [
            "Do not claim production safety.",
            "Do not claim a complete permission system.",
            "Do not claim original-paper benchmark reproduction for all compared systems.",
            "Do not claim real-world deployment safety certification.",
            "Do not promote E49 learned calibration to the main method.",
            "Do not mix oracle/upper-bound rows with deployable non-oracle methods.",
        ]
        write_text(self.output / "claim_boundary/allowed_claims.md", "# Allowed Claims\n\n" + "\n".join(f"- {x}" for x in allowed) + "\n")
        write_text(self.output / "claim_boundary/disallowed_claims.md", "# Disallowed Claims\n\n" + "\n".join(f"- {x}" for x in disallowed) + "\n")
        scope_rows = [
            {"scope_label": "baseline", "meaning": "Non-method baseline or simple proxy."},
            {"scope_label": "official-checkpoint custom stress", "meaning": "Released checkpoint on E47/E48 custom stress, not original benchmark reproduction."},
            {"scope_label": "component custom stress", "meaning": "Original component or policy logic under custom structural stress."},
            {"scope_label": "original-pipeline local-model feasibility", "meaning": "Pipeline compatibility with local model, not original-paper numeric reproduction."},
            {"scope_label": "method-feasibility custom stress", "meaning": "E48/E50 hard guard under controlled custom stress."},
            {"scope_label": "diagnostic", "meaning": "Mechanism or negative diagnostic, not a main method claim."},
            {"scope_label": "oracle", "meaning": "Uses gold labels or otherwise non-deployable information."},
            {"scope_label": "upper bound", "meaning": "Non-deployable upper-bound comparison."},
            {"scope_label": "evaluation-only controlled stress", "meaning": "Constructed stress data requiring audit before main audited claims."},
        ]
        write_rows_csv(self.output / "claim_boundary/result_scope_map.csv", scope_rows)
        write_text(
            self.output / "claim_boundary/scope_labels.md",
            "# Scope Labels\n\n" + "\n".join(f"- `{row['scope_label']}`: {row['meaning']}" for row in scope_rows) + "\n",
        )

    def write_failure_examples(self) -> None:
        examples = load_failure_examples()
        grouped: dict[str, list[dict[str, Any]]] = {
            "full_guard_false_allows": [],
            "full_guard_false_denies": [],
            "resource_auth_failures": [],
            "control_provenance_cases": [],
            "evidence_failures": [],
            "ipiguard_semantic_failures": [],
        }
        for ex in examples:
            method = str(ex.get("method", ""))
            failure_type = str(ex.get("failure_type", ""))
            source = str(ex.get("source") or ex.get("source_scope", ""))
            axis = str(ex.get("counterfactual_axis", ""))
            if method == "effect_binding_guard_full" and failure_type == "false_allow":
                grouped["full_guard_false_allows"].append(ex)
            if method == "effect_binding_guard_full" and failure_type == "false_deny":
                grouped["full_guard_false_denies"].append(ex)
            if "resource" in axis or "auth" in axis or source == "e50_resource_authorization_stress":
                grouped["resource_auth_failures"].append(ex)
            if "provenance" in axis or source in {"camel", "e50_control_provenance_stress"}:
                grouped["control_provenance_cases"].append(ex)
            if "evidence" in failure_type or "evidence" in str(ex.get("likely_reason", "")):
                grouped["evidence_failures"].append(ex)
            if source == "ipiguard":
                grouped["ipiguard_semantic_failures"].append(ex)
        for name, rows in grouped.items():
            write_failure_file(self.output / "failure_examples" / f"{name}.md", name, rows[:12])
        write_json(self.output / "failure_examples/curated_failure_examples.json", grouped)

    def write_e55_materials(self) -> None:
        result_path = ROOT / "analysis/results/e55_precommit_authz_results.json"
        if not result_path.exists():
            write_text(
                self.output / "e55_precommit_authz/README.md",
                "# E55 Pre-Commit Authorization Materials\n\nE55 artifacts were not present when this package was built.\n",
            )
            return
        result = load_json(result_path)
        failures_path = ROOT / "analysis/results/e55_precommit_authz_failure_examples.json"
        failures = load_json(failures_path) if failures_path.exists() else []
        base = self.output / "e55_precommit_authz"
        source_summary = ROOT / "analysis/results/e55_precommit_authz_results.md"
        files = {
            "README.md": e55_package_readme(result),
            "e55_summary.md": source_summary.read_text(encoding="utf-8") if source_summary.exists() else e55_summary(key_metrics()),
            "e55_main_table.md": e55_main_table_markdown(result),
            "e55_slice_table.md": e55_slice_table_markdown(result),
            "e55_authorization_model.md": e55_authorization_model_text(),
            "e55_failure_taxonomy.md": e55_failure_taxonomy_text(failures),
            "e55_review_response_notes.md": e55_review_response_notes_text(result),
            "e55_paper_patch_plan.md": e55_paper_patch_plan_text(result),
        }
        for name, text in files.items():
            write_text(base / name, text)
        write_text(self.output / "ndss_candidate/e55_integration_plan.md", e55_paper_patch_plan_text(result))
        e56_report = ROOT / "analysis/results/e56_final_report.md"
        if e56_report.exists():
            write_text(base / "e56_final_report.md", e56_report.read_text(encoding="utf-8"))
            write_text(self.output / "ndss_candidate/e56_final_report.md", e56_report.read_text(encoding="utf-8"))
        self.write_ndss_candidate_if_e56_available()
        self.write_e57_materials_if_available()

    def write_e57_materials_if_available(self) -> None:
        base = self.output / "e55_precommit_authz"
        e57_summary = ROOT / "analysis/results/e57_validity_checks_report.md"
        e57_report_json = ROOT / "analysis/results/e57_validity_checks_report.json"
        e57_claim = ROOT / "analysis/results/e57_claim_boundary.md"
        e57_ndss = ROOT / "paper_materials/effect_binding_guard_paper/ndss_candidate/e57_integration_plan.md"
        if e57_summary.exists():
            write_text(base / "e57_validity_checks_summary.md", e57_summary.read_text(encoding="utf-8"))
        if e57_claim.exists():
            write_text(base / "e57_claim_boundary.md", e57_claim.read_text(encoding="utf-8"))
        if e57_ndss.exists():
            write_text(self.output / "ndss_candidate/e57_integration_plan.md", e57_ndss.read_text(encoding="utf-8"))
        elif e57_report_json.exists():
            write_text(self.output / "ndss_candidate/e57_integration_plan.md", e57_ndss_plan_text(load_json(e57_report_json)))

    def write_ndss_candidate_if_e56_available(self) -> None:
        strict_path = ROOT / "analysis/results/e55_precommit_authz_results_strict.json"
        audit_path = ROOT / "analysis/results/e55_decision_path_audit.json"
        sanity_path = ROOT / "analysis/results/e55_sanity_checks.json"
        ablation_path = ROOT / "analysis/results/e55_precommit_authz_ablation_table.csv"
        slice_path = ROOT / "analysis/results/e55_precommit_authz_slice_metrics.csv"
        if not all(path.exists() for path in (strict_path, audit_path, sanity_path, ablation_path, slice_path)):
            return
        if self.output.resolve() != DEFAULT_OUTPUT.resolve():
            write_text(
                self.output / "ndss_candidate/README.md",
                "# NDSS Candidate\n\nE56 artifacts exist, but automatic NDSS candidate regeneration is only enabled for the default package path.\n",
            )
            return
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from src.experiments.effect_binding_guard.e55_precommit_authz.e56_audit import write_ndss_candidate

        write_ndss_candidate(
            load_json(strict_path),
            read_csv_dicts(ablation_path),
            read_csv_dicts(slice_path),
            load_json(audit_path),
            load_json(sanity_path),
        )
        e56_report = ROOT / "analysis/results/e56_final_report.md"
        if e56_report.exists():
            write_text(self.output / "ndss_candidate/e56_final_report.md", e56_report.read_text(encoding="utf-8"))

    def write_readme(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        metrics = key_metrics()
        text = f"""# Effect-Binding Guard Paper Materials

This package consolidates code references, datasets, result artifacts, paper-ready tables, failure examples, reproduction notes, and writing summaries for the Tool-Effect Binding / Counterfactual Effect-Binding Guard paper.

## Recommended Paper Framing

The paper should be framed as a measurement plus method-feasibility study. Existing LLM-agent safety defenses are not merely tool-name classifiers, but they still struggle with joint reasoning over realized effect, resource, authorization context, provenance/control dependency, evidence, and utility. The hard Effect-Binding Guard explicitly infers `(effect, resource, authorization_match, provenance_risk)` and uses multi-view disagreement, selective evidence fallback, and a control-provenance overlay.

## Main Results

- E48 hard guard: UPA `{metrics['e48_full_upa']}`, FDeny `{metrics['e48_full_fdeny']}`, coverage `{metrics['e48_full_coverage']}`.
- E50 source-balanced hard guard: mean UPA `{metrics['e50_source_balanced_upa']}`, mean coverage `{metrics['e50_source_balanced_coverage']}`.
- E50 resource/auth stress: UPA `{metrics['e50_resource_auth_upa']}`; this is the main unresolved bottleneck.
- E50 expanded provenance stress: UPA `{metrics['e50_provenance_upa']}`, FDeny `{metrics['e50_provenance_fdeny']}`, coverage `{metrics['e50_provenance_coverage']}`.
- E55 pre-commit authorization: existing hard guard coverage `{metrics['e55_existing_coverage']}`, authorization-aware guard coverage `{metrics['e55_authz_coverage']}`, authorization-aware UPA `{metrics['e55_authz_upa']}`.
- E49 learned calibration is diagnostic only and is not the main method.

## Where To Look

- Tables: `tables/`
- Code references: `code_index/code_index.md`
- Data references: `data_index/data_index.md`
- Claim boundary: `claim_boundary/`
- Writing summaries: `summaries/`
- Reproduction notes: `reproduction/`
- Failure examples: `failure_examples/`

## Claim Boundary

{CLAIM_BOUNDARY}.
"""
        write_text(self.output / "README.md", text)

    def write_package_checklist(self) -> None:
        # Create the file before checking so the checklist can include itself.
        write_text(self.output / "package_checklist.md", "# Package Checklist\n\n")
        checks = package_checks(self.output, self.inventory)
        lines = ["# Package Checklist", ""]
        for key, value in checks.items():
            lines.append(f"- `{key}`: `{value}`")
        write_text(self.output / "package_checklist.md", "\n".join(lines) + "\n")


def artifact_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for path in [
        "analysis/results/tool_effect_fragmentation_capability_matrix_phase6.json",
        "analysis/results/tool_effect_fragmentation_capability_matrix_phase6.md",
        "analysis/results/tool_effect_fragmentation_counterfactual_phase4.json",
        "analysis/results/tool_effect_fragmentation_counterfactual_phase4.md",
        "analysis/results/tool_effect_fragmentation_counterfactual_phase4_toolsafe.json",
        "analysis/results/tool_effect_fragmentation_counterfactual_phase4_safiron.json",
        "analysis/results/tool_effect_fragmentation_ipiguard_semantic_phase6.json",
        "analysis/results/tool_effect_fragmentation_camel_miss_decomposition_phase6.json",
        "analysis/results/tool_effect_fragmentation_human_audit_phase6.json",
        "analysis/results/tool_effect_fragmentation_phase5_unified.json",
        "analysis/results/tool_effect_fragmentation_phase6_unified.json",
        "analysis/results/e48_tuple_guard_results.json",
        "analysis/results/e48_tuple_guard_results.md",
        "analysis/results/e48_local_qwen_tuple_predictions.jsonl",
        "analysis/results/e48_failure_examples.json",
        "analysis/results/e49_learned_fusion_results.json",
        "analysis/results/e49_learned_fusion_results.md",
        "analysis/results/e49_stress_results.json",
        "analysis/results/e49_failure_examples.json",
        "analysis/results/e50_hard_guard_robustness_results.json",
        "analysis/results/e50_final_summary.md",
        "analysis/results/e50_ablation_table.json",
        "analysis/results/e50_source_balanced_splits.json",
        "analysis/results/e50_leave_one_source_out.json",
        "analysis/results/e50_resource_authorization_stress.json",
        "analysis/results/e50_control_provenance_stress.json",
        "analysis/results/e50_failure_examples.json",
        "analysis/results/e50_capability_matrix_final.csv",
        "analysis/results/e55_precommit_authz_results.json",
        "analysis/results/e55_precommit_authz_results.md",
        "analysis/results/e55_precommit_authz_tables.md",
        "analysis/results/e55_precommit_authz_slice_metrics.csv",
        "analysis/results/e55_precommit_authz_failure_examples.json",
        "analysis/results/e55_precommit_authz_leakage_audit.json",
        "analysis/results/e55_precommit_authz_claim_boundary.md",
        "analysis/results/e55_precommit_authz_predictions.jsonl",
        "analysis/results/e55_precommit_authz_results_strict.json",
        "analysis/results/e55_precommit_authz_results_strict.md",
        "analysis/results/e55_decision_path_audit.json",
        "analysis/results/e55_decision_path_audit.md",
        "analysis/results/e55_precommit_authz_ablation_table.md",
        "analysis/results/e55_precommit_authz_ablation_table.csv",
        "analysis/results/e55_precommit_authz_slice_table.md",
        "analysis/results/e55_sanity_checks.json",
        "analysis/results/e55_sanity_checks.md",
        "analysis/results/e55_spot_audit_packet.jsonl",
        "analysis/results/e55_spot_audit_packet.md",
        "analysis/results/e56_anonymity_scan.json",
        "analysis/results/e56_anonymity_scan.md",
        "analysis/results/e56_final_report.json",
        "analysis/results/e56_final_report.md",
        "analysis/results/e57_validity_checks_report.json",
        "analysis/results/e57_validity_checks_report.md",
        "analysis/results/e57_resource_perturbation_results.json",
        "analysis/results/e57_reference_authorizer_agreement.json",
        "analysis/results/e57_spot_audit_packet.jsonl",
        "analysis/results/e57_spot_audit_summary.md",
        "analysis/results/e57_claim_boundary.md",
    ]:
        specs.append(
            {
                "path": path,
                "artifact_type": artifact_type_for_path(ROOT / path),
                "experiment_phase": phase_for_path(ROOT / path),
                "paper_role": role_for_path(path),
                "description": description_for_path(path),
                "required_for_reproduction": path.startswith("analysis/results/e48")
                or path.startswith("analysis/results/e50")
                or path.startswith("analysis/results/tool_effect_fragmentation_counterfactual_phase4"),
                "contains_oracle_or_labels": contains_labels_or_oracle(path),
                "safe_to_cite_as_deployable_result": safe_deployable_cite(path),
            }
        )
    for path in [
        "data/tool_effect_fragmentation/counterfactual_core_phase4.jsonl",
        "data/tool_effect_fragmentation/ipiguard_semantic_core_phase6.jsonl",
        "data/tool_effect_fragmentation/camel_structural_counterfactual_phase5.jsonl",
        "data/tool_effect_fragmentation/human_audit_packet_phase6.jsonl",
        "data/tool_effect_fragmentation/human_audit_secondary_phase6.jsonl",
        "data/e48_effect_binding_unified.jsonl",
        "data/e48_effect_binding_pairs.jsonl",
        "data/e49_effect_binding_fusion_features.jsonl",
        "data/e49_resource_authorization_stress.jsonl",
        "data/e49_control_provenance_stress.jsonl",
        "data/e50_resource_authorization_stress.jsonl",
        "data/e50_control_provenance_stress.jsonl",
        "data/e55_precommit_authz_dataset.jsonl",
        "data/e55_precommit_authz_schema.md",
        "data/e55_precommit_authz_generation_report.md",
    ]:
        specs.append(
            {
                "path": path,
                "artifact_type": "data",
                "experiment_phase": phase_for_path(ROOT / path),
                "paper_role": role_for_path(path),
                "description": description_for_path(path),
                "required_for_reproduction": True,
                "contains_oracle_or_labels": True,
                "safe_to_cite_as_deployable_result": False,
            }
        )
    for path in [
        "analysis/experiments/E47_tool_effect_fragmentation_crosspaper/README.md",
        "analysis/experiments/E48_counterfactual_effect_binding_guard/README.md",
        "analysis/experiments/E49_learned_effect_binding_calibrator/README.md",
        "analysis/experiments/E50_hard_effect_binding_guard_robustness/README.md",
        "analysis/experiments/E51_effect_binding_guard_paper_materials/README.md",
        "analysis/experiments/E55_precommit_authz/README.md",
        "analysis/experiments/E56_e55_audit_ndss_integration/README.md",
        "analysis/experiments/E57_e55_independent_validity_checks/README.md",
    ]:
        specs.append(
            {
                "path": path,
                "artifact_type": "result_md",
                "experiment_phase": phase_for_path(ROOT / path),
                "paper_role": "experiment_readme",
                "description": "Experiment README with purpose, results, and claim boundary.",
                "required_for_reproduction": False,
                "contains_oracle_or_labels": False,
                "safe_to_cite_as_deployable_result": False,
            }
        )
    return specs


def discovered_code_files() -> list[Path]:
    patterns = [
        "src/experiments/tool_effect_fragmentation/*.py",
        "src/experiments/effect_binding_guard/*.py",
        "src/experiments/effect_binding_guard/e55_precommit_authz/*.py",
        "src/experiments/effect_binding_calibrator/*.py",
        "tests/test_tool_effect_fragmentation_phase4.py",
        "tests/test_tool_effect_fragmentation_phase5.py",
        "tests/test_tool_effect_fragmentation_phase6.py",
        "tests/test_effect_binding_guard_e48.py",
        "tests/test_effect_binding_calibrator_e49.py",
        "tests/test_effect_binding_guard_e50.py",
        "tests/test_effect_binding_guard_e55_precommit_authz.py",
        "tests/test_effect_binding_guard_e56_audit.py",
        "tests/test_effect_binding_guard_e57_validity.py",
        "scripts/build_tool_effect_paper_package.py",
        "scripts/build_effect_binding_guard_paper_materials.py",
    ]
    out = []
    for pattern in patterns:
        out.extend(path for path in ROOT.glob(pattern) if path.is_file() and "__pycache__" not in str(path))
    return sorted(set(out))


def table_e47_measurement() -> list[dict[str, Any]]:
    data = load_json(ROOT / "analysis/results/tool_effect_fragmentation_capability_matrix_phase6.json")
    rows = []
    for row in data.get("main_matrix", []):
        rows.append(
            pick(
                row,
                [
                    "method",
                    "claim_scope",
                    "surface_invariance",
                    "effect_sensitivity",
                    "authorization_sensitivity",
                    "resource_awareness",
                    "unsafe_pre_allow",
                    "safe_false_deny",
                    "coverage",
                    "evidence_grounding",
                ],
            )
        )
    return rows


def table_e48_main() -> list[dict[str, Any]]:
    data = load_json(ROOT / "analysis/results/e48_tuple_guard_results.json")
    methods = [
        "rule_tuple_guard",
        "local_qwen_tuple_guard",
        "multi_view_disagreement_guard",
        "evidence_gated_selective_guard",
        "control_provenance_minimal_check",
        "effect_binding_guard_full",
        "always_use_evidence",
    ]
    rows = []
    for method in methods:
        if method not in data["methods"]:
            continue
        overall = data["methods"][method]["overall"]
        rows.append(metric_row(method, overall, extra={"claim_scope": "method-feasibility custom stress"}))
    return rows


def table_e48_source_specific() -> list[dict[str, Any]]:
    data = load_json(ROOT / "analysis/results/e48_tuple_guard_results.json")
    full = data["methods"]["effect_binding_guard_full"]
    rows = [
        metric_row("held_out_test_full_guard", full["by_split"]["test"], extra={"scope": "legacy_hashed_test_no_camel"}),
        metric_row("human_audited_subset", full["human_audited_rows"], extra={"scope": "audited_subset"}),
    ]
    if "ipiguard" in full["by_source"]:
        rows.append(metric_row("ipiguard_semantic_core", full["by_source"]["ipiguard"], extra={"scope": "source_specific"}))
    if "camel" in full["by_source"]:
        rows.append(metric_row("camel_provenance_core", full["by_source"]["camel"], extra={"scope": "source_specific"}))
    return rows


def table_e49_diagnostic() -> list[dict[str, Any]]:
    data = load_json(ROOT / "analysis/results/e49_learned_fusion_results.json")
    summary = data.get("strong_gate_summary", {}).get("source_balanced_alpha_0_10", {})
    rows = [
        {
            "method": "learned_logistic_calibrator_source_balanced",
            "unsafe_pre_allow": summary.get("learned_mean_unsafe_pre_allow"),
            "safe_false_deny": summary.get("learned_mean_safe_false_deny"),
            "coverage": summary.get("learned_mean_coverage"),
            "claim_scope": "diagnostic_not_main_method",
            "interpretation": "Higher coverage but higher UPA than hard guard.",
        },
        {
            "method": "hard_full_guard_same_splits",
            "unsafe_pre_allow": summary.get("hard_mean_unsafe_pre_allow"),
            "safe_false_deny": summary.get("hard_mean_safe_false_deny"),
            "coverage": summary.get("hard_mean_coverage"),
            "claim_scope": "main_hard_baseline",
            "interpretation": "Safer baseline retained as main method.",
        },
    ]
    stress = data.get("strong_gate_summary", {}).get("stress_coverage", {})
    stress_path = ROOT / "analysis/results/e49_resource_authorization_stress.json"
    stress_data = load_json(stress_path) if stress_path.exists() else {}
    learned_stress = stress_data.get("learned_calibrator", {})
    rows.append(
        {
            "method": "e49_resource_auth_stress",
            "unsafe_pre_allow": rate(learned_stress.get("unsafe_pre_allow")),
            "safe_false_deny": rate(learned_stress.get("safe_false_deny")),
            "coverage": rate(learned_stress.get("coverage")) or stress.get("resource_authorization"),
            "claim_scope": "negative_diagnostic",
            "interpretation": "Resource/auth stress fails; learned calibration is appendix only.",
        }
    )
    return rows


def table_e50_robustness() -> list[dict[str, Any]]:
    data = load_json(ROOT / "analysis/results/e50_hard_guard_robustness_results.json")
    rows = []
    full = data["reproduced_e48_main_table"]["methods"]["effect_binding_guard_full"]["overall"]
    rows.append(metric_row("e48_reproduction_full_guard", full, extra={"scope": "main_reproduction"}))
    agg = data["source_balanced"]["aggregate_fixed_policy"]
    rows.append(
        {
            "method": "source_balanced_fixed_policy_mean",
            "unsafe_pre_allow": agg["unsafe_pre_allow"]["mean"],
            "safe_false_deny": agg["safe_false_deny"]["mean"],
            "coverage": agg["coverage"]["mean"],
            "abstain": agg["abstain_rate"]["mean"],
            "claim_scope": "robustness_audit",
        }
    )
    for record in data["leave_one_source_out"]["records"]:
        overall = record["fixed_policy_results"]["effect_binding_guard_full"]["overall"]
        rows.append(metric_row(record["split"]["name"], overall, extra={"scope": "LOSO"}))
    rows.append(metric_row("resource_authorization_stress", data["resource_authorization_stress"]["methods"]["effect_binding_guard_full"]["overall"], extra={"scope": "evaluation_only_controlled_stress"}))
    rows.append(metric_row("expanded_control_provenance_stress", data["control_provenance_stress"]["methods"]["effect_binding_guard_full"]["overall"], extra={"scope": "evaluation_only_controlled_stress"}))
    return rows


def table_e55_precommit_authz() -> list[dict[str, Any]]:
    path = ROOT / "analysis/results/e55_precommit_authz_results.json"
    if not path.exists():
        return []
    data = load_json(path)
    methods = [
        "existing_hard_effect_binding_guard",
        "authz_aware_effect_binding_guard",
        "authz_aware_no_alias_resolution",
        "authz_aware_no_multi_resource_expansion",
        "authz_aware_no_operation_mode",
        "authz_aware_no_provenance_overlay",
        "authz_aware_no_evidence_fallback",
    ]
    rows = []
    for method in methods:
        if method not in data.get("methods", {}):
            continue
        overall = data["methods"][method]["overall"]
        rows.append(
            {
                "method": method,
                "unsafe_pre_allow": rate(overall.get("unsafe_pre_allow")),
                "safe_false_deny": rate(overall.get("safe_false_deny")),
                "coverage": rate(overall.get("coverage")),
                "abstain": rate(overall.get("abstain_rate")),
                "decision_accuracy": rate(overall.get("decision_accuracy")),
                "atom_expansion_exact_match": rate(overall.get("atom_expansion_exact_match")),
                "claim_scope": "controlled local mock pre-commit mediation",
            }
        )
    return rows


def table_final_capability() -> list[dict[str, Any]]:
    rows = table_e47_measurement()
    e48 = load_json(ROOT / "analysis/results/e48_tuple_guard_results.json")["methods"]["effect_binding_guard_full"]
    rows.append(
        {
            "method": "E48 hard Effect-Binding Guard",
            "claim_scope": "method-feasibility custom stress",
            "surface_invariance": rate(e48["pair_metrics"]["same_effect_or_status_consistency"]),
            "effect_sensitivity": rate(e48["pair_metrics"]["effect_sensitivity"]),
            "authorization_sensitivity": rate(e48["pair_metrics"]["authorization_match_sensitivity"]),
            "resource_awareness": rate(e48["pair_metrics"]["resource_sensitivity"]),
            "unsafe_pre_allow": rate(e48["overall"]["unsafe_pre_allow"]),
            "safe_false_deny": rate(e48["overall"]["safe_false_deny"]),
            "coverage": rate(e48["overall"]["coverage"]),
            "evidence_grounding": "selective non-oracle evidence fallback",
        }
    )
    e49 = table_e49_diagnostic()[0]
    rows.append(
        {
            "method": "E49 learned calibrator",
            "claim_scope": "diagnostic_not_main_method",
            "surface_invariance": None,
            "effect_sensitivity": None,
            "authorization_sensitivity": None,
            "resource_awareness": None,
            "unsafe_pre_allow": e49["unsafe_pre_allow"],
            "safe_false_deny": e49["safe_false_deny"],
            "coverage": e49["coverage"],
            "evidence_grounding": "learned fusion diagnostic; not main method",
        }
    )
    e55_path = ROOT / "analysis/results/e55_precommit_authz_results.json"
    if e55_path.exists():
        e55 = load_json(e55_path)["methods"]["authz_aware_effect_binding_guard"]["overall"]
        rows.append(
            {
                "method": "E55 authorization-aware pre-commit guard",
                "claim_scope": "controlled local mock pre-commit mediation",
                "surface_invariance": None,
                "effect_sensitivity": rate(e55.get("effect_accuracy")),
                "authorization_sensitivity": rate(e55.get("authorization_accuracy")),
                "resource_awareness": rate(e55.get("resource_authorization_accuracy")),
                "unsafe_pre_allow": rate(e55.get("unsafe_pre_allow")),
                "safe_false_deny": rate(e55.get("safe_false_deny")),
                "coverage": rate(e55.get("coverage")),
                "evidence_grounding": "explicit authorization context plus deterministic mock atom expansion",
            }
        )
    return rows


def metric_row(method: str, metrics: dict[str, Any], *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    row = {
        "method": method,
        "unsafe_pre_allow": rate(metrics.get("unsafe_pre_allow")),
        "safe_false_deny": rate(metrics.get("safe_false_deny")),
        "coverage": rate(metrics.get("coverage")),
        "abstain": rate(metrics.get("abstain_rate")),
        "effect_accuracy": rate(metrics.get("effect_accuracy")),
        "resource_accuracy": rate(metrics.get("resource_accuracy")),
        "authorization_accuracy": rate(metrics.get("authorization_accuracy")),
        "provenance_accuracy": rate(metrics.get("provenance_accuracy")),
    }
    if extra:
        row.update(extra)
    return row


def load_failure_examples() -> list[dict[str, Any]]:
    examples = []
    for path in [
        ROOT / "analysis/results/e50_failure_examples.json",
        ROOT / "analysis/results/e48_failure_examples.json",
        ROOT / "analysis/results/e55_precommit_authz_failure_examples.json",
        ROOT / "analysis/results/tool_effect_fragmentation_counterfactual_phase4_failure_examples.json",
        ROOT / "analysis/results/tool_effect_fragmentation_phase5_failure_examples.json",
    ]:
        if not path.exists():
            continue
        data = load_json(path)
        examples.extend(extract_dict_examples(data))
    return examples


def extract_dict_examples(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        if "failure_type" in value or "case_id" in value or "variant_case_id" in value:
            return [value]
        rows: list[dict[str, Any]] = []
        for child in value.values():
            rows.extend(extract_dict_examples(child))
        return rows
    if isinstance(value, list):
        rows = []
        for item in value:
            rows.extend(extract_dict_examples(item))
        return rows
    return []


def executive_summary(metrics: dict[str, Any]) -> str:
    return f"""# Executive Summary

This package supports a measurement plus method-feasibility paper about tool-effect binding in LLM-agent safety. The central finding is that current defenses can be more than tool-name classifiers, yet still fail to stably bind realized effects to resources, authorization context, provenance/control dependency, and available evidence.

The proposed hard Effect-Binding Guard explicitly infers `(effect, resource, authorization_match, provenance_risk)` from label-hidden non-oracle views, then uses multi-view disagreement, selective evidence fallback, and a control-provenance overlay to produce `ALLOW / DENY / ABSTAIN`.

Core numbers:

- E48 full guard: UPA `{metrics['e48_full_upa']}`, FDeny `{metrics['e48_full_fdeny']}`, coverage `{metrics['e48_full_coverage']}`.
- E50 source-balanced mean: UPA `{metrics['e50_source_balanced_upa']}`, coverage `{metrics['e50_source_balanced_coverage']}`.
- E50 resource/auth stress: UPA `{metrics['e50_resource_auth_upa']}`; this is the dominant unresolved bottleneck.
- E50 expanded provenance stress: UPA `{metrics['e50_provenance_upa']}`, FDeny `{metrics['e50_provenance_fdeny']}`, coverage `{metrics['e50_provenance_coverage']}`.
- E55 local pre-commit authorization: authorization-aware UPA `{metrics['e55_authz_upa']}`, FDeny `{metrics['e55_authz_fdeny']}`, coverage `{metrics['e55_authz_coverage']}`.

Claim boundary: {CLAIM_BOUNDARY}.
"""


def motivation_summary(metrics: dict[str, Any]) -> str:
    return """# Motivation And Measurement

E47 establishes the measurement problem: same realized effects can be expressed through different tool names, schemas, wrappers, plans, traces, or graph formats. Existing defenses and structural methods are not reducible to trivial tool-name classifiers, but the measurement suite shows that surface robustness alone is insufficient.

The paper should motivate a stronger target: safety monitors must reason jointly about the realized effect, affected resource, task authorization, provenance/control dependency, and available execution evidence. This motivates the E48 hard Effect-Binding Guard and the E50 robustness audit.
"""


def method_summary() -> str:
    return """# Method: Effect-Binding Guard

The guard is a hard, explicit tuple-binding monitor. It receives label-hidden, non-oracle deployable inputs and predicts `(effect, resource, authorization_match, provenance_risk)`.

Main components:

- Rule tuple parser: extracts visible effect/resource/authorization/provenance signals.
- Local-Qwen tuple view: one non-oracle model-based tuple prediction where available.
- Multi-view disagreement: compares tool, schema, plan/call, masked-tool, canonical summary, evidence, and model tuple views.
- Selective evidence fallback: consults non-oracle saved/simulated evidence only when the base view is uncertain or conflicting.
- Control-provenance overlay: denies private control of side-effectful actions and abstains on unresolved untrusted/unknown control.
- Hard policy: outputs `ALLOW`, `DENY`, or `ABSTAIN`.

The method is not a complete permission system and does not claim production readiness.
"""


def e48_summary(metrics: dict[str, Any]) -> str:
    return f"""# E48 Main Results

E48 builds an 822-row label-hidden unified dataset with 6,840 diagnostic pairs. Local-Qwen tuple prediction covers 822 rows with parse-valid rate around 0.995. Deployable-input leakage is zero.

Main full-guard metrics:

- UPA `{metrics['e48_full_upa']}`
- FDeny `{metrics['e48_full_fdeny']}`
- coverage `{metrics['e48_full_coverage']}`
- effect accuracy `{metrics['e48_effect_acc']}`
- resource accuracy `{metrics['e48_resource_acc']}`
- authorization accuracy `{metrics['e48_auth_acc']}`
- provenance accuracy `{metrics['e48_prov_acc']}`

The strongest claim is method-feasibility under controlled custom stress.
"""


def e49_summary(metrics: dict[str, Any]) -> str:
    return f"""# E49 Learned Calibration Diagnostic

E49 tests whether a lightweight learned calibrator over non-oracle tuple/view features improves the hard guard. It improves coverage but increases unsafe pre-allow relative to the hard guard under source-balanced evaluation.

- Learned mean UPA `{metrics['e49_learned_upa']}`
- Hard guard same-split mean UPA `{metrics['e49_hard_upa']}`
- Learned mean coverage `{metrics['e49_learned_coverage']}`
- Hard guard mean coverage `{metrics['e49_hard_coverage']}`

Conclusion: E49 is diagnostic/negative evidence. It is not the main method and must not be promoted over the E48/E50 hard guard.
"""


def e50_summary(metrics: dict[str, Any]) -> str:
    return f"""# E50 Robustness

E50 audits the E48 hard guard without introducing a new learned method.

- E48 reproduction: UPA `{metrics['e48_full_upa']}`, FDeny `{metrics['e48_full_fdeny']}`, coverage `{metrics['e48_full_coverage']}`.
- Source-balanced mean: UPA `{metrics['e50_source_balanced_upa']}`, FDeny `{metrics['e50_source_balanced_fdeny']}`, coverage `{metrics['e50_source_balanced_coverage']}`.
- LOSO is mixed: CaMeL is safe but lower coverage; IPIGuard remains the weakest source.
- Resource/auth stress: UPA `{metrics['e50_resource_auth_upa']}`.
- Expanded provenance stress: UPA `{metrics['e50_provenance_upa']}` but FDeny `{metrics['e50_provenance_fdeny']}` and coverage `{metrics['e50_provenance_coverage']}`.

Interpretation: E50 strengthens hard guard robustness but makes resource/authorization binding the central remaining bottleneck and limitation.
"""


def failure_taxonomy_summary() -> str:
    return """# Failure Taxonomy

Residual failures should be grouped as:

- Resource alias and near-resource mismatch.
- Broad vs narrow authorization scope.
- Partial authorization and missing authorization.
- Draft/no-effect vs commit side effects.
- Extra recipient, CC, BCC, public-link, or out-of-scope target.
- Evidence unavailable or insufficient evidence.
- Unknown or untrusted provenance causing abstention.
- Safe false denial under broad provenance stress.
- IPIGuard semantic/resource failures and topology-only blind spots.

Use curated examples in `failure_examples/` and avoid long raw logs unless needed for an appendix.
"""


def claim_boundary_summary() -> str:
    return f"""# Claim Boundary And Limitations

Allowed: controlled custom-stress robustness and method-feasibility evidence.

Disallowed:

- Production safety.
- Complete permission system.
- Real-world deployment safety certificate.
- Original-paper benchmark reproduction for all systems.
- Universal generalization.
- Oracle-free perfect effect/resource inference.
- Learned calibrator as the main method.

Resource/authorization binding remains a major unsolved bottleneck. E50 stress results must be presented as evidence of that bottleneck.

Summary boundary: {CLAIM_BOUNDARY}.
"""


def paper_outline_summary() -> str:
    return """# Paper Outline

## Title Options

- Counterfactual Effect Binding for LLM-Agent Tool Safety
- Measuring and Mitigating Tool-Effect Fragmentation in LLM Agents
- Beyond Tool Names: Counterfactual Effect Binding for Agent Safety

## Abstract Skeleton

Problem: LLM-agent safety monitors often evaluate tool calls through surface forms, but safety depends on realized effects, resources, authorization, and provenance.

Method: Introduce a counterfactual stress-test framework and a hard Effect-Binding Guard that binds candidate actions into explicit tuples and uses disagreement, evidence fallback, and provenance checks.

Results: E47 shows residual gaps in existing methods; E48/E50 show hard-guard feasibility and robustness; E49 shows learned calibration is not yet safer.

Limits: controlled custom stress, not production safety; resource/authorization binding remains the key bottleneck.

## Sections

1. Introduction: effect-level safety target and counterfactual motivation.
2. Related Work: agent safety, prompt-injection defenses, tool-use guardrails, provenance/control-flow systems, OOD and invariance.
3. Stress-Test Framework: E47 counterfactual axes and scope labels.
4. Effect-Binding Guard: tuple inference, disagreement, evidence fallback, provenance overlay.
5. Evaluation: E47 measurement, E48 feasibility, E49 diagnostic, E50 robustness.
6. Failure Analysis: resource/auth, evidence, provenance, and source shift.
7. Limitations and Ethics.
"""


def e55_summary(metrics: dict[str, Any]) -> str:
    return f"""# E55 Pre-Commit Authorization Binding

E55 is a deterministic local-only pre-commit mediation experiment designed to test whether explicit authorization infrastructure reduces the E50 resource/authorization bottleneck. It builds 600 rows across email, calendar, file sharing, Slack-like workspace, and transaction-like API domains, using realistic mock tool schemas and no real external side effects.

Main comparison:

- Existing hard guard: UPA `{metrics['e55_existing_upa']}`, FDeny `{metrics['e55_existing_fdeny']}`, coverage `{metrics['e55_existing_coverage']}`.
- Authorization-aware guard: UPA `{metrics['e55_authz_upa']}`, FDeny `{metrics['e55_authz_fdeny']}`, coverage `{metrics['e55_authz_coverage']}`.

Interpretation: E55 can be used as NDSS review-response evidence that explicit authorization contexts, atom expansion, alias resolution, operation mode, provenance overlay, and evidence fallback are useful infrastructure for resource/auth binding. It should not be presented as independent deployment validation because the guard and labels share deterministic mock schemas and authorization contracts.
"""


def key_metrics() -> dict[str, Any]:
    e48 = load_json(ROOT / "analysis/results/e48_tuple_guard_results.json")
    e49 = load_json(ROOT / "analysis/results/e49_learned_fusion_results.json")
    e50 = load_json(ROOT / "analysis/results/e50_hard_guard_robustness_results.json")
    e48_full = e48["methods"]["effect_binding_guard_full"]["overall"]
    e49_summary_data = e49["strong_gate_summary"]["source_balanced_alpha_0_10"]
    e50_agg = e50["source_balanced"]["aggregate_fixed_policy"]
    resauth = e50["resource_authorization_stress"]["methods"]["effect_binding_guard_full"]["overall"]
    prov = e50["control_provenance_stress"]["methods"]["effect_binding_guard_full"]["overall"]
    e55_path = ROOT / "analysis/results/e55_precommit_authz_results.json"
    e55 = load_json(e55_path) if e55_path.exists() else {}
    e55_existing = e55.get("methods", {}).get("existing_hard_effect_binding_guard", {}).get("overall", {})
    e55_authz = e55.get("methods", {}).get("authz_aware_effect_binding_guard", {}).get("overall", {})
    return {
        "e48_full_upa": rate(e48_full["unsafe_pre_allow"]),
        "e48_full_fdeny": rate(e48_full["safe_false_deny"]),
        "e48_full_coverage": rate(e48_full["coverage"]),
        "e48_effect_acc": rate(e48_full["effect_accuracy"]),
        "e48_resource_acc": rate(e48_full["resource_accuracy"]),
        "e48_auth_acc": rate(e48_full["authorization_accuracy"]),
        "e48_prov_acc": rate(e48_full["provenance_accuracy"]),
        "e49_learned_upa": e49_summary_data["learned_mean_unsafe_pre_allow"],
        "e49_hard_upa": e49_summary_data["hard_mean_unsafe_pre_allow"],
        "e49_learned_coverage": e49_summary_data["learned_mean_coverage"],
        "e49_hard_coverage": e49_summary_data["hard_mean_coverage"],
        "e50_source_balanced_upa": e50_agg["unsafe_pre_allow"]["mean"],
        "e50_source_balanced_fdeny": e50_agg["safe_false_deny"]["mean"],
        "e50_source_balanced_coverage": e50_agg["coverage"]["mean"],
        "e50_resource_auth_upa": rate(resauth["unsafe_pre_allow"]),
        "e50_provenance_upa": rate(prov["unsafe_pre_allow"]),
        "e50_provenance_fdeny": rate(prov["safe_false_deny"]),
        "e50_provenance_coverage": rate(prov["coverage"]),
        "e55_existing_upa": rate(e55_existing.get("unsafe_pre_allow")),
        "e55_existing_fdeny": rate(e55_existing.get("safe_false_deny")),
        "e55_existing_coverage": rate(e55_existing.get("coverage")),
        "e55_authz_upa": rate(e55_authz.get("unsafe_pre_allow")),
        "e55_authz_fdeny": rate(e55_authz.get("safe_false_deny")),
        "e55_authz_coverage": rate(e55_authz.get("coverage")),
    }


def dataset_summary(source: Path, item: dict[str, Any]) -> dict[str, Any]:
    rows = read_jsonl_safe(source) if source.suffix == ".jsonl" and source.exists() else []
    fields = sorted({key for row in rows[:50] if isinstance(row, dict) for key in row})
    label_status = "construction labels"
    audit_status = "not audited"
    if "human_audit" in str(source):
        label_status = "human audit annotations"
        audit_status = "human audited"
    elif "e48" in str(source):
        label_status = "audit-gated plus audited subset labels"
        audit_status = "mixed audited/custom construction"
    elif "e50" in str(source):
        label_status = "controlled stress construction labels"
        audit_status = "audit required"
    elif "phase4" in str(source) or "phase6" in str(source):
        label_status = "audited custom-stress labels where applicable"
        audit_status = "audited/custom"
    return {
        "path": item["source_path"],
        "row_count": len(rows) if rows else json_count(source),
        "fields": fields,
        "experiment_phase": item["experiment_phase"],
        "paper_role": item["paper_role"],
        "label_provenance": label_status,
        "audit_status": audit_status,
        "oracle_or_leakage_risk": "contains labels/oracle fields; use only outside deployable input" if item["contains_oracle_or_labels"] else "low",
        "usage": usage_for_data(source),
    }


def code_description(path: str) -> str:
    mapping = {
        "run_e48.py": "Build and evaluate E48 Counterfactual Effect-Binding Guard.",
        "run_e49.py": "Run learned fusion/calibration diagnostics over E48 tuple features.",
        "run_e50.py": "Run E50 hard-guard robustness, ablations, stress sets, and summaries.",
        "run_e55.py": "Run E55 deterministic local pre-commit authorization binding evaluation.",
        "e56_audit.py": "Run E56 E55 strict replay, decision-path audit, NDSS rebuild, and anonymity scan.",
        "e57_validity_checks.py": "Run E57 resource perturbation, independent reference authorizer, and spot-audit validity checks.",
        "reference_authorizer.py": "Independent E57 authorizer implementation used for E55 label consistency checks.",
        "local_qwen.py": "Run or parse Local-Qwen tuple predictions for E48.",
        "guards.py": "Hard tuple guard primitives: rule tuple, views, evidence fallback, provenance overlay.",
        "metrics.py": "Wilson, row-level, pairwise, group-bootstrap metrics.",
        "dataset.py": "Build E48 unified label-hidden dataset from E47 artifacts.",
    }
    return next((desc for key, desc in mapping.items() if path.endswith(key)), "Relevant experiment, utility, or test code for E47-E50.")


def command_for_code(path: str) -> str:
    if path.endswith("run_e48.py"):
        return "python -m src.experiments.effect_binding_guard.run_e48 --bootstrap-iters 2000"
    if path.endswith("local_qwen.py"):
        return "python -m src.experiments.effect_binding_guard.local_qwen --resume --max-tokens 192"
    if path.endswith("run_e49.py"):
        return "python -m src.experiments.effect_binding_calibrator.run_e49 --bootstrap-iters 2000"
    if path.endswith("run_e50.py"):
        return "python -m src.experiments.effect_binding_guard.run_e50 --bootstrap-iters 2000"
    if path.endswith("run_e55.py"):
        return "python -m src.experiments.effect_binding_guard.e55_precommit_authz.run_e55 --output analysis/results/e55_precommit_authz_results.json"
    if path.endswith("e57_validity_checks.py"):
        return "python -m src.experiments.effect_binding_guard.e55_precommit_authz.e57_validity_checks"
    if "test_" in path:
        return "python -m pytest <this test> -q"
    if "run_tool_effect_fragmentation_phase4.py" in path:
        return "python -m src.experiments.tool_effect_fragmentation.run_tool_effect_fragmentation_phase4"
    if "run_tool_effect_fragmentation_phase5.py" in path:
        return "python -m src.experiments.tool_effect_fragmentation.run_tool_effect_fragmentation_phase5"
    if "run_tool_effect_fragmentation_phase6.py" in path:
        return "python -m src.experiments.tool_effect_fragmentation.run_tool_effect_fragmentation_phase6"
    return "needs verification"


def inputs_for_code(path: str) -> str:
    if "effect_binding_guard" in path:
        if "e55_precommit_authz" in path:
            return "E55 mock tool schemas and authorization contexts."
        return "E47 Phase4/Phase5/Phase6 artifacts and E48 unified rows."
    if "effect_binding_calibrator" in path:
        return "E48 rows, E48 Local-Qwen tuple predictions, E48 hard guard predictions."
    if "tool_effect_fragmentation" in path:
        return "E47 custom stress cases, official checkpoint outputs, and component traces."
    return "See source file."


def outputs_for_code(path: str) -> str:
    if path.endswith("run_e50.py"):
        return "analysis/results/e50_*.{json,md,csv} and data/e50_*.jsonl."
    if path.endswith("run_e55.py"):
        return "analysis/results/e55_precommit_authz_* and data/e55_precommit_authz_*."
    if path.endswith("e57_validity_checks.py"):
        return "analysis/results/e57_* and paper_materials/effect_binding_guard_paper/e55_precommit_authz/e57_*."
    if path.endswith("run_e48.py"):
        return "analysis/results/e48_tuple_guard_results.{json,md}."
    if path.endswith("run_e49.py"):
        return "analysis/results/e49_* and data/e49_*."
    return "See source file or test target."


def scope_for_code(path: str) -> str:
    if "run_e49" in path or "effect_binding_calibrator" in path:
        return "diagnostic appendix"
    if "e55_precommit_authz" in path:
        return "pre-commit authorization diagnostic"
    if "run_e48" in path or "run_e50" in path or "effect_binding_guard" in path:
        return "main method / robustness"
    if "tool_effect_fragmentation" in path:
        return "measurement framework"
    return "supporting code"


def artifact_type_for_path(path: Path) -> str:
    text = str(path)
    if "/tests/" in text or text.startswith("tests/"):
        return "test"
    if text.endswith(".py"):
        return "code" if "/src/" in text or text.startswith("src/") else "script"
    if text.endswith(".jsonl"):
        return "data" if "/data/" in text or text.startswith("data/") else "result_json"
    if text.endswith(".json"):
        return "result_json"
    if text.endswith(".md"):
        return "result_md"
    if text.endswith(".csv"):
        return "table"
    if text.endswith((".png", ".pdf", ".svg")):
        return "figure"
    return "appendix"


def phase_for_path(path: Path) -> str:
    text = str(path).lower()
    for phase in ("e47", "e48", "e49", "e50", "e55", "e56", "e57"):
        if phase in text:
            return phase.upper()
    if "phase4" in text or "phase5" in text or "phase6" in text or "tool_effect_fragmentation" in text:
        return "E47"
    if "effect_binding_guard" in text:
        return "E48/E50"
    if "effect_binding_calibrator" in text:
        return "E49"
    return "other"


def role_for_path(path: str) -> str:
    text = path.lower()
    if "capability_matrix" in text:
        return "main result"
    if "failure" in text:
        return "failure analysis"
    if "audit" in text:
        return "audit"
    if "e57" in text:
        return "validity check"
    if "oracle" in text or "upper_bound" in text:
        return "upper bound"
    if "e49" in text:
        return "diagnostic"
    if "e55" in text:
        return "pre-commit authorization diagnostic"
    if "e50" in text:
        return "robustness"
    if "e48" in text:
        return "main method"
    if "toolsafe" in text or "safiron" in text:
        return "baseline"
    return "appendix"


def description_for_path(path: str) -> str:
    name = Path(path).name
    if "e57" in path:
        return "E57 independent validity-check artifact for E55."
    if "e56" in path:
        return "E56 E55 strict audit and NDSS integration artifact."
    if "e55" in path:
        return "E55 local pre-commit authorization binding artifact."
    if "e50" in path:
        return "E50 hard guard robustness artifact."
    if "e49" in path:
        return "E49 learned calibration diagnostic artifact."
    if "e48" in path:
        return "E48 hard Effect-Binding Guard feasibility artifact."
    if "capability_matrix" in path:
        return "Cross-method capability matrix."
    if "counterfactual_phase4" in path:
        return "E47 Phase4 counterfactual lattice or method output."
    if "ipiguard" in path:
        return "IPIGuard topology/semantic/component artifact."
    if "camel" in path:
        return "CaMeL structural/provenance artifact."
    return f"Relevant paper artifact: {name}."


def contains_labels_or_oracle(path: str) -> bool:
    text = path.lower()
    return any(token in text for token in ("data/", "audit", "oracle", "upper_bound", "pairs", "stress", "predictions"))


def safe_deployable_cite(path: str) -> bool:
    text = path.lower()
    return ("e48_tuple_guard_results" in text or "e50_hard_guard" in text or "e55_precommit_authz_results" in text) and "oracle" not in text


def usage_for_data(path: Path) -> str:
    text = str(path)
    if "e55_precommit_authz" in text:
        return "evaluation for local mock pre-commit authorization binding"
    if "e49_effect_binding_fusion_features" in text:
        return "training/evaluation for diagnostic learned calibrator"
    if "e50" in text:
        return "evaluation-only controlled stress"
    if "e48_effect_binding" in text:
        return "main method evaluation and diagnostics"
    if "human_audit" in text:
        return "audit"
    return "measurement/evaluation"


def write_table_bundle(base: Path, name: str, rows: list[dict[str, Any]]) -> None:
    write_json(base / f"{name}.json", rows)
    write_rows_csv(base / f"{name}.csv", rows)
    if rows:
        columns = list(rows[0].keys())
    else:
        columns = ["empty"]
    table = [columns] + [[format_cell(row.get(col)) for col in columns] for row in rows]
    write_markdown_table(base / f"{name}.md", name.replace("_", " ").title(), table)


def write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = sorted({key for row in rows for key in row}) if rows else ["empty"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: format_cell(row.get(key)) for key in columns})


def read_csv_dicts(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_markdown_table(path: Path, title: str, rows: list[list[str]]) -> None:
    lines = [f"# {title}", ""]
    if not rows:
        lines.append("_No rows._")
    else:
        header = rows[0]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join("---" for _ in header) + " |")
        for row in rows[1:]:
            lines.append("| " + " | ".join(str(cell).replace("|", "/") for cell in row) + " |")
    write_text(path, "\n".join(lines) + "\n")


def write_failure_file(path: Path, title: str, rows: list[dict[str, Any]]) -> None:
    lines = [f"# {title.replace('_', ' ').title()}", ""]
    if not rows:
        lines.append("_No representative examples found in existing artifacts._")
    for row in rows:
        lines.extend(
            [
                f"## `{row.get('case_id', row.get('id', 'unknown'))}`",
                "",
                f"- Source: `{row.get('source', row.get('source_scope', 'unknown'))}`",
                f"- Method: `{row.get('method', 'unknown')}`",
                f"- Expected: `{row.get('expected_decision', row.get('expected', 'unknown'))}`",
                f"- Predicted: `{row.get('predicted_decision', row.get('predicted', 'unknown'))}`",
                f"- Failure type: `{row.get('failure_type', 'unknown')}`",
                f"- Reason: {row.get('likely_reason', row.get('interpretation', 'not specified'))}",
                f"- Candidate/action: `{shorten(row.get('candidate_action_summary', row.get('tool_surface', 'not included')))}`",
                "",
            ]
        )
    write_text(path, "\n".join(lines))


def e55_package_readme(result: dict[str, Any]) -> str:
    interp = result.get("interpretation", {})
    return f"""# E55 Pre-Commit Authorization Materials

This folder contains paper-ready E55 materials for the Effect-Binding Guard paper package.

- Outcome: `{interp.get('outcome')}`
- Interpretation: {interp.get('summary')}
- Scope: controlled local mock pre-commit mediation.
- Boundary: no real APIs, no real side effects, no production-safety proof, and no original-paper benchmark reproduction.

Use this material as NDSS review-response support for the resource/authorization bottleneck identified in E50.
"""


def e55_main_table_markdown(result: dict[str, Any]) -> str:
    methods = [
        "existing_hard_effect_binding_guard",
        "authz_aware_effect_binding_guard",
        "authz_aware_no_alias_resolution",
        "authz_aware_no_multi_resource_expansion",
        "authz_aware_no_operation_mode",
        "authz_aware_no_provenance_overlay",
        "authz_aware_no_evidence_fallback",
    ]
    lines = ["# E55 Main Table", "", "| Method | UPA | FDeny | Coverage | Abstain | Decision Acc | Atom Exact |", "|---|---:|---:|---:|---:|---:|---:|"]
    for method in methods:
        if method not in result.get("methods", {}):
            continue
        overall = result["methods"][method]["overall"]
        lines.append(
            f"| {method} | {format_metric(overall.get('unsafe_pre_allow'))} | {format_metric(overall.get('safe_false_deny'))} | {format_metric(overall.get('coverage'))} | {format_metric(overall.get('abstain_rate'))} | {format_metric(overall.get('decision_accuracy'))} | {format_metric(overall.get('atom_expansion_exact_match'))} |"
        )
    return "\n".join(lines) + "\n"


def e55_slice_table_markdown(result: dict[str, Any]) -> str:
    lines = ["# E55 Slice Table", "", "| Method | Slice | UPA | FDeny | Coverage | Atom Exact |", "|---|---|---:|---:|---:|---:|"]
    for method in ("existing_hard_effect_binding_guard", "authz_aware_effect_binding_guard"):
        for slice_name, metrics in result.get("methods", {}).get(method, {}).get("by_slice", {}).items():
            lines.append(
                f"| {method} | {slice_name} | {format_metric(metrics.get('unsafe_pre_allow'))} | {format_metric(metrics.get('safe_false_deny'))} | {format_metric(metrics.get('coverage'))} | {format_metric(metrics.get('atom_expansion_exact_match'))} |"
            )
    return "\n".join(lines) + "\n"


def e55_authorization_model_text() -> str:
    return """# E55 Authorization Model

E55 models pre-commit mediation as explicit authorization checking over effect-resource-operation atoms.

The deployable guard path receives only visible tool schema/arguments, task authorization context, non-oracle evidence summaries, and provenance/control-source metadata. It recomputes atoms from the visible call and checks whether every affected recipient, attendee, file, channel, account, visibility, operation mode, and provenance source is covered by the task authorization.

Default policy: all atoms must be authorized. Unknown canonicalization or insufficient evidence causes `ABSTAIN`; hard provenance violations cause `DENY`.
"""


def e55_failure_taxonomy_text(failures: list[dict[str, Any]]) -> str:
    counts = Counter(item.get("failure_type", "unknown") for item in failures)
    lines = ["# E55 Failure Taxonomy", "", f"Failure example counts: `{dict(counts)}`", ""]
    for item in failures[:20]:
        lines.append(
            f"- `{item.get('failure_type')}` / `{item.get('method')}` / `{item.get('case_id')}`: expected `{item.get('expected_decision')}`, predicted `{item.get('predicted_decision')}`."
        )
    return "\n".join(lines) + "\n"


def e55_review_response_notes_text(result: dict[str, Any]) -> str:
    return f"""# E55 Review Response Notes

## What concrete information must a pre-commit mediator provide?

Typed authorization context, resource aliases, operation mode, multi-resource expansion surface, provenance/control-source metadata, and enough non-oracle evidence to canonicalize opaque resources.

## Does this solve deployment safety?

No. E55 is a deterministic local mock evaluation. It tests whether explicit authorization infrastructure addresses the E50 bottleneck under controlled schemas; it does not validate production SaaS, browser, banking, messaging, or filesystem behavior.

## Why is this useful despite the controlled setup?

The ablations isolate which infrastructure pieces matter: alias resolution, multi-resource expansion, operation-mode binding, provenance overlay, and evidence fallback. The correct reviewer-facing claim is that these pieces are necessary engineering structure for effect binding, not that the current prototype generalizes universally.

Outcome: `{result.get('interpretation', {}).get('outcome')}`.
"""


def e55_paper_patch_plan_text(result: dict[str, Any]) -> str:
    outcome = result.get("interpretation", {}).get("outcome")
    if outcome == "Outcome A":
        recommendation = "Add E55 as a dedicated realistic pre-commit mediation results section and cautiously strengthen the defense framing."
    elif outcome == "Outcome B":
        recommendation = "Use E55 as central review-response evidence that explicit authorization infrastructure improves the E50 bottleneck, while framing the system as a controlled prototype."
    else:
        recommendation = "Use E55 as measurement/failure-analysis evidence and do not strengthen the method claim."
    return f"""# E55 NDSS Integration Plan

Recommended integration: {recommendation}

Patch plan:

- Add a short subsection after E50 resource/auth stress explaining the E55 local pre-commit setup.
- Report the main existing-hard-guard vs authorization-aware comparison and the ablation table.
- Keep the core limitation that labels and the guard share deterministic mock authorization contracts.
- Do not claim production safety, complete permission-system coverage, or original-paper benchmark reproduction.
"""


def e57_ndss_plan_text(report: dict[str, Any]) -> str:
    return f"""# E57 NDSS Integration Plan

Recommended short addition.

## Results / Finding 6

Add: "A deterministic resource-name perturbation and independent reference-authorizer check produced stable decisions / high agreement, reducing but not eliminating concern that the result is a naming-template artifact."

Use exact values:

- Perturbation stability passed: `{report.get('perturbation_stability_passed')}`.
- Authz-aware UPA delta: `{report.get('perturbation', {}).get('authz_aware_upa_delta')}`.
- Authz-aware coverage delta: `{report.get('perturbation', {}).get('authz_aware_coverage_delta')}`.
- Reference-authorizer decision agreement: `{report.get('reference_authorizer', {}).get('decision_agreement')}`.
- Spot-audit packet rows: `{report.get('spot_audit', {}).get('n_rows')}`.

## Limitations

Add: "These checks reduce lexical and implementation-coupling concerns, but E55 remains controlled contract evidence because both the labels and guard operate under the same explicit mock authorization contract."

## Appendix

Add the perturbation result table, reference-authorizer agreement table, and spot-audit packet description.
"""


def package_checks(output: Path, inventory: list[dict[str, Any]]) -> dict[str, bool]:
    required_files = [
        "README.md",
        "artifact_inventory.json",
        "artifact_inventory.md",
        "code_index/code_index.md",
        "code_index/code_index.json",
        "data_index/data_index.md",
        "data_index/data_index.json",
        "summaries/00_executive_summary.md",
        "summaries/07_claim_boundary_and_limitations.md",
        "reproduction/reproduce_e48.md",
        "claim_boundary/allowed_claims.md",
        "claim_boundary/disallowed_claims.md",
        "e55_precommit_authz/README.md",
        "package_checklist.md",
    ]
    checks = {
        "required_files_exist": all((output / path).exists() for path in required_files),
        "required_files_non_empty": all((output / path).exists() and (output / path).stat().st_size > 0 for path in required_files),
        "inventory_non_empty": bool(inventory),
        "inventory_paths_resolve": all(resolve_inventory_entry(output, item) for item in inventory),
        "claim_boundary_in_readme": "production safety" in (output / "README.md").read_text(encoding="utf-8"),
        "e49_not_main_method": "not the main method" in (output / "summaries/04_learned_calibration_e49.md").read_text(encoding="utf-8").lower(),
        "resource_auth_bottleneck_stated": "bottleneck" in (output / "summaries/05_robustness_e50.md").read_text(encoding="utf-8").lower(),
    }
    if (ROOT / "analysis/results/e55_precommit_authz_results.json").exists():
        checks["e55_materials_preserved"] = (output / "e55_precommit_authz/e55_summary.md").exists() and (
            output / "ndss_candidate/e55_integration_plan.md"
        ).exists()
    return checks


def validate_package(output: Path) -> None:
    if not output.exists():
        raise SystemExit(f"missing package: {output}")
    inventory_path = output / "artifact_inventory.json"
    if not inventory_path.exists():
        raise SystemExit("missing artifact_inventory.json")
    inventory = load_json(inventory_path)
    checks = package_checks(output, inventory)
    failed = [key for key, value in checks.items() if not value]
    if failed:
        raise SystemExit(f"package validation failed: {failed}")


def resolve_inventory_entry(output: Path, item: dict[str, Any]) -> bool:
    if not item.get("exists"):
        return True
    path = output / item["package_path"]
    if not path.exists():
        return False
    if path.is_symlink():
        target = os.readlink(path)
        if os.path.isabs(target):
            return False
        return (path.parent / target).exists()
    return path.stat().st_size > 0


def read_jsonl_safe(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                rows.append(value)
    return rows


def json_count(path: Path) -> int | None:
    if not path.exists():
        return None
    if path.suffix == ".json":
        data = load_json(path)
        if isinstance(data, list):
            return len(data)
        if isinstance(data, dict):
            for key in ("rows", "methods", "main_matrix"):
                if isinstance(data.get(key), list):
                    return len(data[key])
    return None


def rate(metric: Any) -> Any:
    if isinstance(metric, dict):
        return metric.get("rate")
    return metric


def pick(row: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {key: row.get(key) for key in keys}


def format_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def format_metric(metric: Any) -> str:
    value = rate(metric)
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def shorten(value: Any, limit: int = 240) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path, base: Path = ROOT) -> str:
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
