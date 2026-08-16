from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "paper_package_tool_effect_invariance"


def main() -> None:
    args = parse_args()
    output = (ROOT / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output)
    if args.validate_only:
        validate_package(output)
        print(f"validated {output}")
        return
    if output.exists():
        if not args.force:
            raise SystemExit(f"{output} already exists. Re-run with --force to rebuild it.")
        shutil.rmtree(output)
    builder = PackageBuilder(output)
    builder.build()
    validate_package(output)
    print(f"built and validated {output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the E47 tool-effect invariance paper package.")
    parser.add_argument("--output", default="paper_package_tool_effect_invariance")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args()


class PackageBuilder:
    def __init__(self, output: Path) -> None:
        self.output = output
        self.source_index: list[dict[str, Any]] = []

    def build(self) -> None:
        self.make_dirs()
        copied = self.copy_canonical_artifacts()
        manifests = self.write_manifests()
        tables = self.write_tables()
        failures = self.write_failure_examples()
        self.write_figures()
        self.write_writing_materials()
        self.write_reproducibility(copied, manifests, tables, failures)
        self.write_readme()
        self.copy_source_code()
        self.write_source_index()

    def make_dirs(self) -> None:
        for relative in (
            "manifests",
            "results/canonical",
            "results/legacy_weak_label",
            "tables",
            "figures",
            "audit",
            "failure_examples",
            "writing",
            "reproducibility/source_code",
            "scripts",
            "data",
        ):
            (self.output / relative).mkdir(parents=True, exist_ok=True)

    def copy_canonical_artifacts(self) -> list[dict[str, Any]]:
        artifacts = [
            # E47 summaries and phase reports.
            ("analysis/experiments/E47_tool_effect_fragmentation_crosspaper/README.md", "results/canonical/experiment_readme.md", "phase_overview", "canonical"),
            ("analysis/experiments/E47_tool_effect_fragmentation_crosspaper/phase2_summary.md", "results/canonical/phase2_summary.md", "phase_summary", "canonical"),
            ("analysis/experiments/E47_tool_effect_fragmentation_crosspaper/phase3_summary.md", "results/canonical/phase3_summary.md", "phase_summary", "canonical"),
            ("analysis/experiments/E47_tool_effect_fragmentation_crosspaper/phase4_summary.md", "results/canonical/phase4_summary.md", "phase_summary", "canonical"),
            ("analysis/experiments/E47_tool_effect_fragmentation_crosspaper/phase5_summary.md", "results/canonical/phase5_summary.md", "phase_summary", "canonical"),
            ("analysis/experiments/E47_tool_effect_fragmentation_crosspaper/phase6_summary.md", "results/canonical/phase6_summary.md", "phase_summary", "canonical"),
            ("analysis/results/tool_effect_fragmentation_phase2_unified.json", "results/canonical/tool_effect_fragmentation_phase2_unified.json", "result_summary", "canonical"),
            ("analysis/results/tool_effect_fragmentation_phase2_unified.md", "results/canonical/tool_effect_fragmentation_phase2_unified.md", "result_summary", "canonical"),
            ("analysis/results/tool_effect_fragmentation_phase3_unified.json", "results/canonical/tool_effect_fragmentation_phase3_unified.json", "result_summary", "canonical"),
            ("analysis/results/tool_effect_fragmentation_phase3_unified.md", "results/canonical/tool_effect_fragmentation_phase3_unified.md", "result_summary", "canonical"),
            ("analysis/results/tool_effect_fragmentation_counterfactual_phase4.json", "results/canonical/tool_effect_fragmentation_counterfactual_phase4.json", "counterfactual_lattice", "canonical"),
            ("analysis/results/tool_effect_fragmentation_counterfactual_phase4.md", "results/canonical/tool_effect_fragmentation_counterfactual_phase4.md", "counterfactual_lattice", "canonical"),
            ("analysis/results/tool_effect_fragmentation_phase5_unified.json", "results/canonical/tool_effect_fragmentation_phase5_unified.json", "structured_defense", "canonical"),
            ("analysis/results/tool_effect_fragmentation_phase5_unified.md", "results/canonical/tool_effect_fragmentation_phase5_unified.md", "structured_defense", "canonical"),
            ("analysis/results/tool_effect_fragmentation_phase6_unified.json", "results/canonical/tool_effect_fragmentation_phase6_unified.json", "evidence_consolidation", "canonical"),
            ("analysis/results/tool_effect_fragmentation_phase6_unified.md", "results/canonical/tool_effect_fragmentation_phase6_unified.md", "evidence_consolidation", "canonical"),
            # Main metric reports.
            ("analysis/results/tool_effect_fragmentation_capability_matrix_phase6.json", "results/canonical/tool_effect_fragmentation_capability_matrix_phase6.json", "capability_matrix", "audited_custom_stress"),
            ("analysis/results/tool_effect_fragmentation_capability_matrix_phase6.md", "results/canonical/tool_effect_fragmentation_capability_matrix_phase6.md", "capability_matrix", "audited_custom_stress"),
            ("analysis/results/tool_effect_fragmentation_human_audit_phase6.json", "audit/tool_effect_fragmentation_human_audit_phase6.json", "human_audit", "audited"),
            ("analysis/results/tool_effect_fragmentation_human_audit_phase6.md", "audit/tool_effect_fragmentation_human_audit_phase6.md", "human_audit", "audited"),
            ("data/tool_effect_fragmentation/human_audit_packet_phase6.jsonl", "audit/human_audit_packet_phase6.jsonl", "human_audit_primary", "audited"),
            ("data/tool_effect_fragmentation/human_audit_secondary_phase6.jsonl", "audit/human_audit_secondary_phase6.jsonl", "human_audit_secondary", "audited"),
            ("analysis/results/tool_effect_fragmentation_ipiguard_semantic_phase6.json", "results/canonical/tool_effect_fragmentation_ipiguard_semantic_phase6.json", "semantic_layer", "diagnostic"),
            ("analysis/results/tool_effect_fragmentation_ipiguard_semantic_phase6.md", "results/canonical/tool_effect_fragmentation_ipiguard_semantic_phase6.md", "semantic_layer", "diagnostic"),
            ("analysis/results/tool_effect_fragmentation_camel_miss_decomposition_phase6.json", "results/canonical/tool_effect_fragmentation_camel_miss_decomposition_phase6.json", "camel_miss_decomposition", "corrected_label"),
            ("analysis/results/tool_effect_fragmentation_camel_miss_decomposition_phase6.md", "results/canonical/tool_effect_fragmentation_camel_miss_decomposition_phase6.md", "camel_miss_decomposition", "corrected_label"),
            ("analysis/results/tool_effect_fragmentation_external_pipeline_phase6.json", "results/canonical/tool_effect_fragmentation_external_pipeline_phase6.json", "external_pipeline_status", "feasibility_status"),
            ("analysis/results/tool_effect_fragmentation_external_pipeline_phase6.md", "results/canonical/tool_effect_fragmentation_external_pipeline_phase6.md", "external_pipeline_status", "feasibility_status"),
            # Phase 3/4 method artifacts.
            ("analysis/results/tool_effect_fragmentation_toolsafe_official_stress_phase3.json", "results/canonical/tool_effect_fragmentation_toolsafe_official_stress_phase3.json", "official_checkpoint_custom_stress", "official_checkpoint_custom_stress"),
            ("analysis/results/tool_effect_fragmentation_toolsafe_official_stress_phase3.md", "results/canonical/tool_effect_fragmentation_toolsafe_official_stress_phase3.md", "official_checkpoint_custom_stress", "official_checkpoint_custom_stress"),
            ("analysis/results/tool_effect_fragmentation_safiron_official_stress_phase3.json", "results/canonical/tool_effect_fragmentation_safiron_official_stress_phase3.json", "official_checkpoint_custom_stress", "official_checkpoint_custom_stress"),
            ("analysis/results/tool_effect_fragmentation_safiron_official_stress_phase3.md", "results/canonical/tool_effect_fragmentation_safiron_official_stress_phase3.md", "official_checkpoint_custom_stress", "official_checkpoint_custom_stress"),
            ("analysis/results/tool_effect_fragmentation_counterfactual_phase4_toolsafe.json", "results/canonical/tool_effect_fragmentation_counterfactual_phase4_toolsafe.json", "official_checkpoint_custom_stress", "official_checkpoint_custom_stress"),
            ("analysis/results/tool_effect_fragmentation_counterfactual_phase4_toolsafe.md", "results/canonical/tool_effect_fragmentation_counterfactual_phase4_toolsafe.md", "official_checkpoint_custom_stress", "official_checkpoint_custom_stress"),
            ("analysis/results/tool_effect_fragmentation_counterfactual_phase4_safiron.json", "results/canonical/tool_effect_fragmentation_counterfactual_phase4_safiron.json", "official_checkpoint_custom_stress", "official_checkpoint_custom_stress"),
            ("analysis/results/tool_effect_fragmentation_counterfactual_phase4_safiron.md", "results/canonical/tool_effect_fragmentation_counterfactual_phase4_safiron.md", "official_checkpoint_custom_stress", "official_checkpoint_custom_stress"),
            ("analysis/results/tool_effect_fragmentation_evidence_phase3.json", "results/canonical/tool_effect_fragmentation_evidence_phase3.json", "non_oracle_evidence", "diagnostic"),
            ("analysis/results/tool_effect_fragmentation_evidence_phase3.md", "results/canonical/tool_effect_fragmentation_evidence_phase3.md", "non_oracle_evidence", "diagnostic"),
            ("analysis/results/tool_effect_fragmentation_agentdojo_phase3.json", "results/canonical/tool_effect_fragmentation_agentdojo_phase3.json", "agentdojo_stress", "paper_grade_custom_stress"),
            ("analysis/results/tool_effect_fragmentation_agentdojo_phase3.md", "results/canonical/tool_effect_fragmentation_agentdojo_phase3.md", "agentdojo_stress", "paper_grade_custom_stress"),
            # Phase 5 structured defense artifacts.
            ("analysis/results/tool_effect_fragmentation_ipiguard_phase5.json", "results/canonical/tool_effect_fragmentation_ipiguard_phase5.json", "ipiguard_component", "original_component_custom_stress"),
            ("analysis/results/tool_effect_fragmentation_ipiguard_phase5.md", "results/canonical/tool_effect_fragmentation_ipiguard_phase5.md", "ipiguard_component", "original_component_custom_stress"),
            ("analysis/results/tool_effect_fragmentation_camel_phase5.json", "results/canonical/tool_effect_fragmentation_camel_phase5.json", "camel_component", "original_component_custom_stress"),
            ("analysis/results/tool_effect_fragmentation_camel_phase5.md", "results/canonical/tool_effect_fragmentation_camel_phase5.md", "camel_component", "original_component_custom_stress"),
            ("analysis/results/tool_effect_fragmentation_ipiguard_component_phase5.jsonl", "results/canonical/tool_effect_fragmentation_ipiguard_component_phase5.jsonl", "ipiguard_component_rows", "original_component_custom_stress"),
            ("analysis/results/tool_effect_fragmentation_camel_component_phase5.jsonl", "results/canonical/tool_effect_fragmentation_camel_component_phase5.jsonl", "camel_component_rows", "original_component_custom_stress"),
            # Failure examples.
            ("analysis/results/tool_effect_fragmentation_counterfactual_phase4_failure_examples.json", "failure_examples/tool_effect_fragmentation_counterfactual_phase4_failure_examples.json", "failure_examples", "canonical"),
            ("analysis/results/tool_effect_fragmentation_counterfactual_phase4_failure_examples.md", "failure_examples/tool_effect_fragmentation_counterfactual_phase4_failure_examples.md", "failure_examples", "canonical"),
            ("analysis/results/tool_effect_fragmentation_phase5_failure_examples.json", "failure_examples/tool_effect_fragmentation_phase5_failure_examples.json", "failure_examples", "canonical"),
            ("analysis/results/tool_effect_fragmentation_phase5_failure_examples.md", "failure_examples/tool_effect_fragmentation_phase5_failure_examples.md", "failure_examples", "canonical"),
            ("analysis/results/tool_effect_fragmentation_failure_examples_phase3.json", "failure_examples/tool_effect_fragmentation_failure_examples_phase3.json", "failure_examples", "canonical"),
            ("analysis/results/tool_effect_fragmentation_failure_examples_phase3.md", "failure_examples/tool_effect_fragmentation_failure_examples_phase3.md", "failure_examples", "canonical"),
            # Core data.
            ("data/tool_effect_fragmentation/counterfactual_core_phase4.jsonl", "data/counterfactual_core_phase4.jsonl", "counterfactual_data", "audited_custom_stress"),
            ("data/tool_effect_fragmentation/counterfactual_core_phase4_manifest.json", "data/counterfactual_core_phase4_manifest.json", "counterfactual_data", "audited_custom_stress"),
            ("data/tool_effect_fragmentation/ipiguard_counterfactual_phase5.jsonl", "data/ipiguard_counterfactual_phase5.jsonl", "structured_defense_data", "original_component_custom_stress"),
            ("data/tool_effect_fragmentation/camel_structural_counterfactual_phase5.jsonl", "data/camel_structural_counterfactual_phase5.jsonl", "structured_defense_data", "corrected_label"),
            ("data/tool_effect_fragmentation/ipiguard_semantic_core_phase6.jsonl", "data/ipiguard_semantic_core_phase6.jsonl", "semantic_layer_data", "diagnostic"),
            ("data/tool_effect_fragmentation/ipiguard_phase5_traces.jsonl", "data/ipiguard_phase5_traces.jsonl", "local_pipeline_traces", "local_pipeline_feasibility"),
            ("data/tool_effect_fragmentation/camel_phase5_traces.jsonl", "data/camel_phase5_traces.jsonl", "local_pipeline_traces", "local_pipeline_feasibility"),
            ("data/tool_effect_fragmentation/external_pipeline_phase6_traces.jsonl", "data/external_pipeline_phase6_traces.jsonl", "external_pipeline_status", "feasibility_status"),
        ]
        copied = []
        for source, dest, role, scope in artifacts:
            source_path = ROOT / source
            if not source_path.exists():
                continue
            copied.append(self.copy_file(source_path, self.output / dest, role, scope))

        # Keep original weak-label material only as a clearly marked legacy reference.
        weak_reference = self.write_weak_label_reference()
        copied.append(weak_reference)
        return copied

    def copy_source_code(self) -> None:
        for source in sorted((ROOT / "src/experiments/tool_effect_fragmentation").glob("*.py")):
            self.copy_file(
                source,
                self.output / "reproducibility/source_code/src/experiments/tool_effect_fragmentation" / source.name,
                "source_code",
                "reproducibility",
            )
        for source in sorted((ROOT / "tests").glob("test_tool_effect_fragmentation*.py")):
            self.copy_file(
                source,
                self.output / "reproducibility/source_code/tests" / source.name,
                "test_code",
                "reproducibility",
            )
        self.copy_file(Path(__file__), self.output / "scripts/build_tool_effect_paper_package.py", "package_builder", "reproducibility")

    def copy_file(self, source: Path, dest: Path, role: str, scope: str) -> dict[str, Any]:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        entry = {
            "original_path": rel(source),
            "package_path": rel(dest, self.output),
            "file_size": dest.stat().st_size,
            "sha256": sha256(dest),
            "artifact_role": role,
            "claim_scope": scope,
        }
        self.source_index.append(entry)
        return entry

    def write_weak_label_reference(self) -> dict[str, Any]:
        camel = load_json(ROOT / "analysis/results/tool_effect_fragmentation_camel_miss_decomposition_phase6.json")
        weak = {
            "purpose": "Legacy reference only. The canonical CaMeL no_side_effect_tool labels are corrected to no_external_side_effect.",
            "original_weak_label_reference": camel.get("original_weak_label_reference"),
            "corrected_label_reference": camel.get("corrected_label_reference"),
            "corrected_vs_weak_label_delta": camel.get("corrected_vs_weak_label_delta"),
            "do_not_use_as_canonical": True,
        }
        path = self.output / "results/legacy_weak_label/camel_no_side_effect_original_weak_label_reference.json"
        write_json(path, weak)
        entry = {
            "original_path": "generated_from:analysis/results/tool_effect_fragmentation_camel_miss_decomposition_phase6.json",
            "package_path": rel(path, self.output),
            "file_size": path.stat().st_size,
            "sha256": sha256(path),
            "artifact_role": "legacy_weak_label_reference",
            "claim_scope": "weak_label_legacy",
        }
        self.source_index.append(entry)
        return entry

    def write_manifests(self) -> list[dict[str, Any]]:
        specs = [
            {
                "experiment_name": "AgentDojo tool-surface and held-out-tool stress",
                "stage": "Phase 2/3",
                "source_scripts": ["src/experiments/tool_effect_fragmentation/run_tool_effect_fragmentation_phase2.py", "src/experiments/tool_effect_fragmentation/run_tool_effect_fragmentation_phase3.py"],
                "source_data": ["data/tool_effect_fragmentation/phase3_stress_cases.jsonl", "data/tool_effect_fragmentation/phase3_predictions.jsonl"],
                "output_artifacts": ["analysis/results/tool_effect_fragmentation_agentdojo_phase3.json", "analysis/results/tool_effect_fragmentation_phase3_unified.json"],
                "case_count": jsonl_count(ROOT / "data/tool_effect_fragmentation/phase3_stress_cases.jsonl"),
                "row_count": jsonl_count(ROOT / "data/tool_effect_fragmentation/phase3_predictions.jsonl"),
                "group_count": 24,
                "method_scope_label": "paper_grade_custom_stress",
                "evidence_type": "saved AgentDojo/custom stress",
                "label_status": "custom stress labels; Phase 4/6 audited labels support main counterfactual claims",
                "human_audited": False,
                "known_limitations": "AgentDojo local stress anchor; not a universal benchmark of deployed systems.",
                "paper_section": "Measurement setup and surface-fragmentation baseline",
                "claim_boundary": "Supports tool-surface fragility diagnostics, not original-method failure claims.",
            },
            {
                "experiment_name": "ToolSafe / TS-Guard official checkpoint custom stress",
                "stage": "Phase 3/4",
                "source_scripts": ["src/experiments/tool_effect_fragmentation/phase3_official_stress.py", "src/experiments/tool_effect_fragmentation/phase4_inference.py"],
                "source_data": ["data/tool_effect_fragmentation/counterfactual_core_phase4.jsonl"],
                "output_artifacts": ["analysis/results/tool_effect_fragmentation_toolsafe_official_stress_phase3.json", "analysis/results/tool_effect_fragmentation_counterfactual_phase4_toolsafe.json"],
                "case_count": 528,
                "row_count": 528,
                "group_count": 24,
                "method_scope_label": "official_method_custom_stress",
                "evidence_type": "released checkpoint on E47 inputs",
                "label_status": "audited custom-stress labels for Phase 4 core",
                "human_audited": True,
                "known_limitations": "Not original TS-Guard benchmark reproduction.",
                "paper_section": "Official checkpoint counterfactual results",
                "claim_boundary": "Use as official-checkpoint custom stress, not a general ToolSafe failure claim.",
            },
            {
                "experiment_name": "Safiron official checkpoint custom stress",
                "stage": "Phase 3/4",
                "source_scripts": ["src/experiments/tool_effect_fragmentation/phase3_official_stress.py", "src/experiments/tool_effect_fragmentation/phase4_inference.py"],
                "source_data": ["data/tool_effect_fragmentation/counterfactual_core_phase4.jsonl"],
                "output_artifacts": ["analysis/results/tool_effect_fragmentation_safiron_official_stress_phase3.json", "analysis/results/tool_effect_fragmentation_counterfactual_phase4_safiron.json"],
                "case_count": 528,
                "row_count": 528,
                "group_count": 24,
                "method_scope_label": "official_method_custom_stress",
                "evidence_type": "released checkpoint on E47 inputs",
                "label_status": "audited custom-stress labels for Phase 4 core",
                "human_audited": True,
                "known_limitations": "Not original Safiron benchmark reproduction.",
                "paper_section": "Official checkpoint counterfactual results",
                "claim_boundary": "Use as official-checkpoint custom stress, not a general Safiron failure claim.",
            },
            {
                "experiment_name": "Phase 4 counterfactual tool-effect lattice",
                "stage": "Phase 4",
                "source_scripts": ["src/experiments/tool_effect_fragmentation/run_tool_effect_fragmentation_phase4.py"],
                "source_data": ["data/tool_effect_fragmentation/counterfactual_core_phase4.jsonl"],
                "output_artifacts": ["analysis/results/tool_effect_fragmentation_counterfactual_phase4.json"],
                "case_count": jsonl_count(ROOT / "data/tool_effect_fragmentation/counterfactual_core_phase4.jsonl"),
                "row_count": 528,
                "group_count": 24,
                "method_scope_label": "audited_custom_stress",
                "evidence_type": "strict paired counterfactual core",
                "label_status": "human-audited after Phase 6 corrected-label update",
                "human_audited": True,
                "known_limitations": "Controlled custom stress, not deployed-agent safety validation.",
                "paper_section": "Counterfactual stress design and main results",
                "claim_boundary": "Shows capability gaps under controlled counterfactual axes.",
            },
            {
                "experiment_name": "Phase 5 IPIGuard DAG component stress",
                "stage": "Phase 5",
                "source_scripts": ["src/experiments/tool_effect_fragmentation/run_tool_effect_fragmentation_phase5.py", "src/experiments/tool_effect_fragmentation/phase5_ipiguard_component_worker.py"],
                "source_data": ["data/tool_effect_fragmentation/ipiguard_counterfactual_phase5.jsonl"],
                "output_artifacts": ["analysis/results/tool_effect_fragmentation_ipiguard_phase5.json", "analysis/results/tool_effect_fragmentation_ipiguard_component_phase5.jsonl"],
                "case_count": jsonl_count(ROOT / "data/tool_effect_fragmentation/ipiguard_counterfactual_phase5.jsonl"),
                "row_count": jsonl_count(ROOT / "analysis/results/tool_effect_fragmentation_ipiguard_component_phase5.jsonl"),
                "group_count": 24,
                "method_scope_label": "original_component_custom_stress",
                "evidence_type": "released DAG prompt/parser component",
                "label_status": "custom stress labels; semantic-layer claims separated",
                "human_audited": True,
                "known_limitations": "DAG topology has no realized-effect decision interface.",
                "paper_section": "Structured defense analysis",
                "claim_boundary": "Topology stability is not equivalent to effect-level safety.",
            },
            {
                "experiment_name": "Phase 5 CaMeL structural policy component stress",
                "stage": "Phase 5/6",
                "source_scripts": ["src/experiments/tool_effect_fragmentation/phase5_camel.py", "src/experiments/tool_effect_fragmentation/phase5_camel_component_worker.py"],
                "source_data": ["data/tool_effect_fragmentation/camel_structural_counterfactual_phase5.jsonl"],
                "output_artifacts": ["analysis/results/tool_effect_fragmentation_camel_phase5.json", "analysis/results/tool_effect_fragmentation_camel_miss_decomposition_phase6.json"],
                "case_count": jsonl_count(ROOT / "data/tool_effect_fragmentation/camel_structural_counterfactual_phase5.jsonl"),
                "row_count": jsonl_count(ROOT / "analysis/results/tool_effect_fragmentation_camel_component_phase5.jsonl"),
                "group_count": 6,
                "method_scope_label": "original_component_custom_stress",
                "evidence_type": "generic SecurityPolicyEngine component",
                "label_status": "corrected human-audited labels; no_side_effect_tool fixed",
                "human_audited": True,
                "known_limitations": "Component stress, not full CaMeL generated-code benchmark.",
                "paper_section": "Structured defense analysis and failure taxonomy",
                "claim_boundary": "Misses are custom structural stress findings, not general CaMeL failure claims.",
            },
            {
                "experiment_name": "Phase 5 IPIGuard / CaMeL original-pipeline local-model feasibility",
                "stage": "Phase 5",
                "source_scripts": ["src/experiments/tool_effect_fragmentation/phase5_pipeline_worker.py", "src/experiments/tool_effect_fragmentation/phase5_original_runner.py"],
                "source_data": ["data/tool_effect_fragmentation/ipiguard_phase5_traces.jsonl", "data/tool_effect_fragmentation/camel_phase5_traces.jsonl"],
                "output_artifacts": ["analysis/results/tool_effect_fragmentation_phase5_unified.json"],
                "case_count": jsonl_count(ROOT / "data/tool_effect_fragmentation/ipiguard_phase5_traces.jsonl") + jsonl_count(ROOT / "data/tool_effect_fragmentation/camel_phase5_traces.jsonl"),
                "row_count": jsonl_count(ROOT / "data/tool_effect_fragmentation/ipiguard_phase5_traces.jsonl") + jsonl_count(ROOT / "data/tool_effect_fragmentation/camel_phase5_traces.jsonl"),
                "group_count": None,
                "method_scope_label": "original_pipeline_local_model",
                "evidence_type": "full local-model pipeline feasibility",
                "label_status": "pipeline feasibility/status, not main safety labels",
                "human_audited": False,
                "known_limitations": "Local GGUF model has low no-defense attack success and low utility.",
                "paper_section": "Reproducibility and limitations",
                "claim_boundary": "Do not use as defense-effectiveness evidence.",
            },
            {
                "experiment_name": "Phase 6 human audit",
                "stage": "Phase 6",
                "source_scripts": ["src/experiments/tool_effect_fragmentation/phase6_core.py"],
                "source_data": ["data/tool_effect_fragmentation/human_audit_packet_phase6.jsonl", "data/tool_effect_fragmentation/human_audit_secondary_phase6.jsonl"],
                "output_artifacts": ["analysis/results/tool_effect_fragmentation_human_audit_phase6.json"],
                "case_count": 222,
                "row_count": 278,
                "group_count": None,
                "method_scope_label": "audited_custom_stress",
                "evidence_type": "primary and secondary human audit",
                "label_status": "corrected labels pass upgrade gate",
                "human_audited": True,
                "known_limitations": "Audit validates custom-stress labels, not external deployment validity.",
                "paper_section": "Human audit",
                "claim_boundary": "Model-generated labels alone do not satisfy this gate.",
            },
            {
                "experiment_name": "Phase 6 IPIGuard semantic-layer comparison",
                "stage": "Phase 6",
                "source_scripts": ["src/experiments/tool_effect_fragmentation/run_tool_effect_fragmentation_phase6.py", "src/experiments/tool_effect_fragmentation/phase6_semantic_worker.py"],
                "source_data": ["data/tool_effect_fragmentation/ipiguard_semantic_core_phase6.jsonl"],
                "output_artifacts": ["analysis/results/tool_effect_fragmentation_ipiguard_semantic_phase6.json"],
                "case_count": jsonl_count(ROOT / "data/tool_effect_fragmentation/ipiguard_semantic_core_phase6.jsonl"),
                "row_count": jsonl_count(ROOT / "analysis/results/tool_effect_fragmentation_ipiguard_semantic_phase6.jsonl"),
                "group_count": 24,
                "method_scope_label": "diagnostic",
                "evidence_type": "semantic-layer diagnostic over IPIGuard DAG inputs",
                "label_status": "audited custom-stress expected decisions; oracle row separated",
                "human_audited": True,
                "known_limitations": "Added mapper is not original IPIGuard and not a deployable guard.",
                "paper_section": "Semantic-layer analysis",
                "claim_boundary": "Supports missing semantic layer diagnosis, not solved safety.",
            },
            {
                "experiment_name": "Phase 6 CaMeL unsafe miss decomposition",
                "stage": "Phase 6",
                "source_scripts": ["src/experiments/tool_effect_fragmentation/run_tool_effect_fragmentation_phase6.py"],
                "source_data": ["data/tool_effect_fragmentation/camel_structural_counterfactual_phase5.jsonl"],
                "output_artifacts": ["analysis/results/tool_effect_fragmentation_camel_miss_decomposition_phase6.json"],
                "case_count": 54,
                "row_count": 54,
                "group_count": 6,
                "method_scope_label": "audited_custom_stress",
                "evidence_type": "corrected-label component miss decomposition",
                "label_status": "corrected human-audited labels",
                "human_audited": True,
                "known_limitations": "Component-level custom stress; effect/resource/authorization capabilities not directly evaluable.",
                "paper_section": "Structured defense failure taxonomy",
                "claim_boundary": "Do not claim CaMeL generally fails.",
            },
            {
                "experiment_name": "Non-oracle evidence verifier and oracle / upper-bound comparisons",
                "stage": "Phase 3/4/6",
                "source_scripts": ["src/experiments/tool_effect_fragmentation/phase3_evidence.py", "src/experiments/tool_effect_fragmentation/phase4_methods.py"],
                "source_data": ["data/tool_effect_fragmentation/counterfactual_core_phase4.jsonl"],
                "output_artifacts": ["analysis/results/tool_effect_fragmentation_evidence_phase3.json", "analysis/results/tool_effect_fragmentation_counterfactual_phase4.json"],
                "case_count": 528,
                "row_count": None,
                "group_count": 24,
                "method_scope_label": "diagnostic_or_upper_bound",
                "evidence_type": "non-oracle evidence diagnostic plus oracle upper bounds",
                "label_status": "audited custom-stress labels; oracle rows separated",
                "human_audited": True,
                "known_limitations": "Non-oracle evidence has limited coverage; oracle rows are not deployable.",
                "paper_section": "Evidence grounding and upper-bound analysis",
                "claim_boundary": "Do not present oracle/upper-bound rows as deployable methods.",
            },
        ]
        write_json(self.output / "manifests/all_experiments_manifest.json", specs)
        write_markdown_table(
            self.output / "manifests/all_experiments_manifest.md",
            specs,
            ["experiment_name", "stage", "case_count", "row_count", "group_count", "method_scope_label", "label_status", "human_audited", "paper_section"],
            title="All E47 Paper Experiments Manifest",
        )
        for spec in specs:
            slug = slugify(spec["experiment_name"])
            write_json(self.output / f"manifests/{slug}.json", spec)
            write_kv_markdown(self.output / f"manifests/{slug}.md", spec["experiment_name"], spec)
        return specs

    def write_tables(self) -> dict[str, list[dict[str, Any]]]:
        tables: dict[str, list[dict[str, Any]]] = {}
        tables["main_capability_matrix"] = self.table_main_capability_matrix()
        tables["counterfactual_lattice_summary"] = self.table_counterfactual_lattice()
        tables["official_checkpoint_summary"] = self.table_official_checkpoints()
        tables["structured_defense_summary"] = self.table_structured_defenses()
        tables["human_audit_summary"] = self.table_human_audit()
        tables["claim_scope_table"] = self.table_claim_scopes()
        tables["appendix_corrected_vs_weak_labels"] = self.table_corrected_vs_weak()
        tables["appendix_camel_miss_decomposition"] = self.table_camel_miss_decomposition()
        tables["appendix_ipiguard_consistency_by_variant"] = self.table_ipiguard_by_variant()
        tables["appendix_external_pipeline_feasibility"] = self.table_external_pipeline()
        tables["appendix_failure_case_table"] = self.table_failure_cases()

        write_json(self.output / "tables/paper_tables.json", tables)
        for name, rows in tables.items():
            columns = infer_columns(rows)
            write_table_set(self.output / "tables" / name, rows, columns, title=name.replace("_", " ").title())
        return tables

    def table_main_capability_matrix(self) -> list[dict[str, Any]]:
        matrix = load_json(ROOT / "analysis/results/tool_effect_fragmentation_capability_matrix_phase6.json")
        columns = [
            "method",
            "surface_invariance",
            "effect_sensitivity",
            "authorization_sensitivity",
            "resource_awareness",
            "unsafe_pre_allow",
            "safe_false_deny",
            "abstain_rate",
            "utility_preservation",
            "evidence_grounding",
            "claim_scope",
            "audit_status",
        ]
        return [{column: row.get(column) for column in columns} for row in matrix.get("main_matrix", [])]

    def table_counterfactual_lattice(self) -> list[dict[str, Any]]:
        phase4 = load_json(ROOT / "analysis/results/tool_effect_fragmentation_counterfactual_phase4.json")
        rows = []
        for method, payload in sorted(phase4.get("metrics", {}).get("methods", {}).items()):
            metrics = payload.get("group_metrics", {})
            rows.append(
                {
                    "method": method,
                    "same_effect_consistency": metric_rate(metrics.get("same_effect_decision_consistency")),
                    "same_tool_different_effect_correctness": metric_rate(metrics.get("correct_effect_change_decision_rate")),
                    "authorization_sensitivity": metric_rate(metrics.get("authorization_sensitivity")),
                    "resource_mismatch_error": metric_rate(metrics.get("resource_mismatch_error")),
                    "unsafe_pre_allow": metric_rate(metrics.get("unsafe_pre_allow")),
                    "safe_false_deny": metric_rate(metrics.get("safe_false_deny")),
                    "coverage": metric_rate(metrics.get("coverage")),
                    "claim_scope": scope_for_method(method),
                }
            )
        return rows

    def table_official_checkpoints(self) -> list[dict[str, Any]]:
        phase4 = load_json(ROOT / "analysis/results/tool_effect_fragmentation_counterfactual_phase4.json")
        phase3 = {
            "ts_guard_official_counterfactual_stress": load_json(ROOT / "analysis/results/tool_effect_fragmentation_toolsafe_official_stress_phase3.json"),
            "safiron_official_counterfactual_stress": load_json(ROOT / "analysis/results/tool_effect_fragmentation_safiron_official_stress_phase3.json"),
        }
        rows = []
        for method in ("ts_guard_official_counterfactual_stress", "safiron_official_counterfactual_stress"):
            metrics = phase4.get("metrics", {}).get("methods", {}).get(method, {}).get("group_metrics", {})
            smoke = phase3.get(method, {})
            rows.append(
                {
                    "method": method,
                    "system": smoke.get("system"),
                    "claim_scope": "official_method_custom_stress",
                    "phase3_cases": smoke.get("n_cases"),
                    "phase3_parse_valid": smoke.get("n_parse_valid"),
                    "phase4_same_effect_consistency": metric_rate(metrics.get("same_effect_decision_consistency")),
                    "phase4_effect_change_correctness": metric_rate(metrics.get("correct_effect_change_decision_rate")),
                    "phase4_authorization_sensitivity": metric_rate(metrics.get("authorization_sensitivity")),
                    "phase4_resource_mismatch_error": metric_rate(metrics.get("resource_mismatch_error")),
                    "phase4_unsafe_pre_allow": metric_rate(metrics.get("unsafe_pre_allow")),
                    "phase4_safe_false_deny": metric_rate(metrics.get("safe_false_deny")),
                    "boundary": "released checkpoint on E47 custom stress, not original-paper numeric reproduction",
                }
            )
        return rows

    def table_structured_defenses(self) -> list[dict[str, Any]]:
        phase5 = load_json(ROOT / "analysis/results/tool_effect_fragmentation_phase5_unified.json")
        semantic = load_json(ROOT / "analysis/results/tool_effect_fragmentation_ipiguard_semantic_phase6.json")
        camel = load_json(ROOT / "analysis/results/tool_effect_fragmentation_camel_miss_decomposition_phase6.json")
        ipg = phase5.get("original_component_custom_stress", {}).get("ipiguard_dag_counterfactual", {})
        rows = [
            {
                "method": "ipiguard_topology_only",
                "scope": "original_component_custom_stress",
                "surface_invariance": metric_rate(ipg.get("same_effect_topology_consistency")),
                "effect_sensitivity": metric_rate(ipg.get("same_tool_different_effect_topology_sensitivity")),
                "unsafe_pre_allow": None,
                "safe_false_deny": None,
                "interpretation": "Topology is stable but has no authorization decision interface.",
            }
        ]
        for method, result in semantic.get("methods", {}).items():
            if result.get("decision_metrics") == "not_evaluable":
                continue
            metrics = result.get("metrics", {})
            rows.append(
                {
                    "method": method,
                    "scope": "upper_bound" if method == "oracle_effect_resource_mapper" else "diagnostic",
                    "surface_invariance": metric_rate(metrics.get("same_effect_consistency")),
                    "effect_sensitivity": metric_rate(metrics.get("effect_sensitivity")),
                    "authorization_sensitivity": metric_rate(metrics.get("authorization_sensitivity")),
                    "resource_sensitivity": metric_rate(metrics.get("resource_sensitivity")),
                    "unsafe_pre_allow": metric_rate(metrics.get("unsafe_pre_allow")),
                    "safe_false_deny": metric_rate(metrics.get("safe_false_deny")),
                    "abstain_rate": metric_rate(metrics.get("abstain_rate")),
                    "interpretation": "Added semantic mapper; not original IPIGuard.",
                }
            )
        rows.append(
            {
                "method": "camel_structural_policy",
                "scope": "original_component_custom_stress",
                "surface_invariance": metric_rate(phase5.get("original_component_custom_stress", {}).get("camel_security_policy", {}).get("structural_invariance")),
                "unsafe_blocked": metric_rate(camel.get("unsafe_blocked")),
                "safe_false_deny": metric_rate(camel.get("safe_false_denial")),
                "unsafe_misses": camel.get("unsafe_miss_count"),
                "interpretation": "Stable structural policy component; misses control-dependency violations in custom stress.",
            }
        )
        return rows

    def table_human_audit(self) -> list[dict[str, Any]]:
        audit = load_json(ROOT / "analysis/results/tool_effect_fragmentation_human_audit_phase6.json")
        return [
            {
                "status": audit.get("status"),
                "primary_completed": f"{audit.get('n_primary_completed')}/{audit.get('n_primary')}",
                "secondary_completed": f"{audit.get('n_secondary_completed')}/{audit.get('n_secondary')}",
                "decision_agreement": audit.get("decision_agreement"),
                "effect_agreement": audit.get("effect_agreement"),
                "resource_agreement": audit.get("resource_agreement"),
                "authorization_agreement": audit.get("authorization_agreement"),
                "unresolved_rows": audit.get("unresolved_count"),
                "corrected_label_subset_rows": audit.get("corrected_label_subset_count"),
                "upgrade_gate": audit.get("upgrade_gate"),
            }
        ]

    def table_claim_scopes(self) -> list[dict[str, Any]]:
        rows = [
            ("baseline", "Rule or local-LLM baseline; not a target system result.", "No deployable safety claim."),
            ("paper_grade_custom_stress", "AgentDojo local custom stress anchor.", "Paper-grade for local stress only."),
            ("official_method_custom_stress", "Released checkpoint evaluated on E47 transformed inputs.", "Not original-paper benchmark reproduction."),
            ("original_component_custom_stress", "Released mechanism component evaluated on E47 custom core.", "Component evidence only."),
            ("original_pipeline_local_model", "Full pipeline using local non-paper model.", "Feasibility only when no-defense utility/ASR is low."),
            ("diagnostic", "Added mapper or evidence diagnostic.", "Not original method or deployable guard."),
            ("upper_bound", "Oracle/effect/evidence upper bound.", "Not deployable."),
            ("audited_custom_stress", "Human-audited corrected custom stress labels.", "Valid for E47 counterfactual claims."),
        ]
        return [{"claim_scope": scope, "meaning": meaning, "allowed_use": allowed} for scope, meaning, allowed in rows]

    def table_corrected_vs_weak(self) -> list[dict[str, Any]]:
        return load_json(ROOT / "analysis/results/tool_effect_fragmentation_camel_miss_decomposition_phase6.json").get("corrected_label_appendix_table", [])

    def table_camel_miss_decomposition(self) -> list[dict[str, Any]]:
        camel = load_json(ROOT / "analysis/results/tool_effect_fragmentation_camel_miss_decomposition_phase6.json")
        rows = []
        for category, value in camel.get("misses_by_failure_category", {}).items():
            rows.append({"breakdown": "failure_category", "name": category, "n": value.get("n"), "misses": value.get("misses")})
        for category, value in camel.get("misses_by_effect_class", {}).items():
            rows.append({"breakdown": "effect_class", "name": category, "n": value.get("n"), "misses": value.get("misses")})
        return rows

    def table_ipiguard_by_variant(self) -> list[dict[str, Any]]:
        phase5 = load_json(ROOT / "analysis/results/tool_effect_fragmentation_phase5_unified.json")
        by_variant = phase5.get("original_component_custom_stress", {}).get("ipiguard_dag_counterfactual", {}).get("counterfactual_consistency_by_variant", {})
        rows = []
        for variant, metrics in sorted(by_variant.items()):
            rows.append(
                {
                    "variant": variant,
                    "topology_consistency": metric_rate(metrics.get("topology_consistency")),
                    "exact_dag_consistency": metric_rate(metrics.get("exact_dag_consistency")),
                    "normalized_dag_consistency": metric_rate(metrics.get("normalized_dag_consistency")),
                }
            )
        return rows

    def table_external_pipeline(self) -> list[dict[str, Any]]:
        phase5 = load_json(ROOT / "analysis/results/tool_effect_fragmentation_phase5_unified.json")
        external = load_json(ROOT / "analysis/results/tool_effect_fragmentation_external_pipeline_phase6.json")
        rows = []
        for system, summary in phase5.get("original_pipeline_local_model", {}).items():
            for component, metrics in summary.get("by_component", {}).items():
                rows.append(
                    {
                        "system": system,
                        "component": component,
                        "scope": "original_pipeline_local_model",
                        "n_rows": metrics.get("n_rows"),
                        "runtime_error_rate": metric_rate(metrics.get("runtime_error_rate")),
                        "policy_denial_rate": metric_rate(metrics.get("policy_denial_rate")),
                        "benign_utility": metric_rate(metrics.get("utility_benign")),
                        "attack_utility": metric_rate(metrics.get("utility_under_attack")),
                        "attack_success": metric_rate(metrics.get("attack_success_rate")),
                        "interpretation": "local-model feasibility; not defense-effectiveness evidence",
                    }
                )
        for system, gate in external.get("gates", {}).items():
            rows.append(
                {
                    "system": system,
                    "component": "phase6_external_deepseek_gate",
                    "scope": external.get("claim_scope"),
                    "n_rows": 0,
                    "benign_utility": gate.get("benign_utility"),
                    "successful_attacks": gate.get("successful_attacks"),
                    "passed": gate.get("passed"),
                    "interpretation": external.get("status"),
                }
            )
        return rows

    def table_failure_cases(self) -> list[dict[str, Any]]:
        return curated_failure_examples()

    def write_failure_examples(self) -> list[dict[str, Any]]:
        examples = curated_failure_examples()
        write_json(self.output / "failure_examples/failure_examples.json", examples)
        write_table_set(
            self.output / "failure_examples/failure_examples",
            examples,
            ["source_system", "method", "case_id", "tool_surface", "realized_effect", "resource", "expected_decision", "predicted_decision", "failure_type", "paper_section", "claim_scope"],
            title="Curated Failure Examples",
        )
        return examples

    def write_figures(self) -> None:
        figure_specs = [
            {
                "file": "counterfactual_lattice_design.md",
                "title": "Counterfactual Lattice Design",
                "data": ["data/counterfactual_core_phase4.jsonl", "tables/counterfactual_lattice_summary.csv"],
                "spec": "Four panels: same effect/different surface, same tool/different effect, same effect/different authorization, same effect/different resource. Show expected decision stability or flip for each axis.",
            },
            {
                "file": "capability_coverage_heatmap.md",
                "title": "Capability Coverage Heatmap",
                "data": ["tables/main_capability_matrix.csv"],
                "spec": "Rows are methods; columns are surface invariance, effect sensitivity, authorization sensitivity, resource awareness, unsafe pre-allow inverse, safe false deny inverse, abstain inverse, utility. Use scope annotations beside method names.",
            },
            {
                "file": "failure_mode_taxonomy.md",
                "title": "Failure-Mode Taxonomy",
                "data": ["failure_examples/failure_examples.json", "tables/appendix_camel_miss_decomposition.csv"],
                "spec": "Tree from surface failure to effect-insensitivity, authorization failure, resource binding failure, evidence absence, and control-dependency failure.",
            },
            {
                "file": "ipiguard_semantic_layer_diagram.md",
                "title": "IPIGuard Semantic-Layer Diagram",
                "data": ["tables/structured_defense_summary.csv", "results/canonical/tool_effect_fragmentation_ipiguard_semantic_phase6.json"],
                "spec": "Pipeline diagram: DAG topology -> normalized content DAG -> effect/resource semantic mapper -> authorization decision. Mark topology-only as not decision-evaluable.",
            },
            {
                "file": "camel_control_dependency_failure.md",
                "title": "CaMeL Control-Dependency Failure",
                "data": ["tables/appendix_camel_miss_decomposition.csv", "failure_examples/failure_examples.json"],
                "spec": "Show private tool output controlling a side-effectful action. The evaluated policy component allows it; required policy treats control provenance as authorization-relevant.",
            },
        ]
        write_json(self.output / "figures/figure_specs.json", figure_specs)
        for spec in figure_specs:
            text = [
                f"# {spec['title']}",
                "",
                f"Data references: `{spec['data']}`",
                "",
                spec["spec"],
                "",
                "This is a figure specification. A rendered plot is optional; the referenced tables contain the required data.",
                "",
            ]
            (self.output / "figures" / spec["file"]).write_text("\n".join(text), encoding="utf-8")
        write_markdown_table(self.output / "figures/figure_specs.md", figure_specs, ["title", "data", "spec"], title="Figure Specifications")

    def write_writing_materials(self) -> None:
        write_text(
            self.output / "writing/title_options.md",
            "# Title Options\n\n"
            "1. Tool-Effect Invariance Stress Tests for LLM Agent Safety\n"
            "2. Surface Robustness Is Not Tool-Effect Invariance\n"
            "3. Measuring Joint Effect, Resource, and Authorization Reasoning in LLM Agent Guards\n",
        )
        write_text(
            self.output / "writing/abstract_skeleton.md",
            "# Abstract Skeleton\n\n"
            "LLM agent safety methods must decide whether realized tool effects are authorized, not only whether tool names or traces look benign. "
            "We introduce a counterfactual Tool-Effect Invariance stress package spanning AgentDojo, TS-Guard, Safiron, IPIGuard, and CaMeL-style components. "
            "The measurements show that stronger checkpoint and structural methods are not merely tool-name classifiers, yet none fully covers joint effect-resource-authorization-evidence reasoning. "
            "Human-audited corrected labels support the controlled counterfactual claims; oracle and local-pipeline rows are separated from deployable evidence.\n",
        )
        write_text(
            self.output / "writing/introduction_outline.md",
            "# Introduction Outline\n\n"
            "- Agent safety failures are ultimately about realized effects on resources under an authorization context.\n"
            "- Tool names, schemas, wrappers, planner formats, and trace labels are unstable surfaces.\n"
            "- Surface robustness is necessary but insufficient: a guard must jointly bind effect, resource, authorization, provenance, evidence, and utility.\n"
            "- E47 contributes a stress-test framework, audited counterfactual lattice, cross-method measurements, structured-defense diagnostics, and claim-boundary discipline.\n",
        )
        write_text(
            self.output / "writing/related_work_positioning.md",
            "# Related Work Positioning\n\n"
            "- AgentDojo: benchmark backbone and adversarial task environment.\n"
            "- ToolSafe / TS-Guard and Safiron: checkpoint-style tool or pre-execution safety models.\n"
            "- IPIGuard and CaMeL: structured graph / provenance / capability defenses.\n"
            "- E47 differs by measuring invariance and sensitivity under paired tool-effect counterfactuals rather than reporting only in-distribution attack success.\n",
        )
        write_text(
            self.output / "writing/method_section_outline.md",
            "# Method Section Outline\n\n"
            "- Define realized effect, resource, authorization context, and expected decision.\n"
            "- Present perturbation axes: same effect/surface shift, same tool/effect shift, authorization shift, resource shift, trace/planner/graph format shift.\n"
            "- Define metrics: same-effect consistency, effect-change correctness, authorization sensitivity, resource mismatch error, unsafe pre-allow, safe false deny, abstain/coverage, action-level mismatch.\n"
            "- Define evidence scopes: baseline, official-checkpoint custom stress, component stress, diagnostic, oracle, upper bound, local-pipeline feasibility.\n",
        )
        write_text(
            self.output / "writing/experiment_design.md",
            "# Experiment Design Notes\n\n"
            "Use the audited Phase 4 counterfactual lattice as the central measurement. Use Phase 5/6 structured-defense results to test whether graph/provenance structure alone closes the gap. "
            "Report local-pipeline runs only as feasibility because no-defense attack success and utility are too low for defense-effectiveness claims.\n",
        )
        write_text(
            self.output / "writing/main_results.md",
            "# Main Results Notes\n\n"
            "- Tool-name and schema baselines can look invariant while failing effect/authorization/resource sensitivity.\n"
            "- TS-Guard and Safiron are not merely tool-name classifiers, but their capability profiles differ.\n"
            "- IPIGuard topology is stable but not decision-evaluable for realized effects without a semantic layer.\n"
            "- CaMeL structural policy is stable under synchronized rewrites but misses control-dependency violations in the custom component stress.\n",
        )
        write_text(
            self.output / "writing/structured_defense_section.md",
            "# Structured-Defense Section Notes\n\n"
            "IPIGuard and CaMeL should be discussed as structured defenses that improve format stability, not as complete solutions to effect-resource-authorization reasoning. "
            "The IPIGuard semantic-layer diagnostic and CaMeL control-dependency failures show which layer remains missing.\n",
        )
        write_text(
            self.output / "writing/human_audit_section.md",
            "# Human Audit Section Notes\n\n"
            "The final audit completed 222 primary and 56 secondary rows. Decision, effect, resource, and authorization agreement are all 1.0 after correcting the six CaMeL no-side-effect rows. "
            "The corrected-label subset changes effect taxonomy only; ALLOW/DENY metrics are unchanged.\n",
        )
        write_text(
            self.output / "writing/limitations.md",
            "# Limitations\n\n"
            "- Custom-stress evidence is not original-paper numeric reproduction.\n"
            "- Component stress is not full pipeline safety validation.\n"
            "- Oracle and upper-bound rows are not deployable methods.\n"
            "- Local-pipeline runs have floor effects and should not support defense-effectiveness claims.\n"
            "- Human audit validates labels in the constructed stress tests, not real-world coverage.\n",
        )
        write_text(
            self.output / "writing/ethics_safety_statement.md",
            "# Ethics and Safety Statement\n\n"
            "The package uses saved traces, sandboxed or simulated counterfactuals, dry-run checkpoint inference, and component-level checks. No real side-effectful tools are executed. "
            "Failure examples are intended to improve safety evaluation and should not be used as operational attack guidance.\n",
        )
        write_text(
            self.output / "writing/claim_boundary.md",
            claim_boundary_text(),
        )
        write_text(
            self.output / "writing/contributions.md",
            "# Contribution List\n\n"
            "1. A tool-effect invariance stress-test framework across static, plan, step, trajectory, graph, evidence, and action-decision levels.\n"
            "2. A human-audited counterfactual lattice separating surface invariance from effect, authorization, and resource sensitivity.\n"
            "3. Cross-method measurements showing complementary but incomplete capability profiles.\n"
            "4. Structured-defense diagnostics for IPIGuard-style DAGs and CaMeL-style policies.\n"
            "5. A claim-boundary and reproducibility package separating audited, diagnostic, oracle, and feasibility evidence.\n",
        )

    def write_reproducibility(self, copied: list[dict[str, Any]], manifests: list[dict[str, Any]], tables: dict[str, list[dict[str, Any]]], failures: list[dict[str, Any]]) -> None:
        commands = [
            "python scripts/build_tool_effect_paper_package.py --force",
            "python scripts/build_tool_effect_paper_package.py --validate-only",
            "python -m pytest tests/test_tool_effect_fragmentation_phase4.py tests/test_tool_effect_fragmentation_phase5.py tests/test_tool_effect_fragmentation_phase6.py -q",
        ]
        write_json(
            self.output / "reproducibility/reproducibility_manifest.json",
            {
                "copied_artifacts": len(copied),
                "experiment_manifests": len(manifests),
                "tables": sorted(tables),
                "failure_examples": len(failures),
                "commands": commands,
            },
        )
        write_text(
            self.output / "reproducibility/README.md",
            "# Reproducibility Notes\n\n"
            "Regenerate the package with:\n\n"
            "```bash\npython scripts/build_tool_effect_paper_package.py --force\n```\n\n"
            "Validate an existing package with:\n\n"
            "```bash\npython scripts/build_tool_effect_paper_package.py --validate-only\n```\n\n"
            "The package copies canonical final E47 artifacts. It does not rerun experiments. External repos/checkpoints are required only to regenerate original raw experiments, not to use this paper package. "
            "Official-checkpoint custom stress, component stress, local-pipeline feasibility, diagnostic, oracle, and upper-bound rows are explicitly separated in `tables/claim_scope_table.*`.\n\n"
            "Do not use local-pipeline feasibility as defense-effectiveness evidence when no-defense utility or attack success is low. Do not use oracle or upper-bound rows as deployable methods.\n",
        )
        write_text(
            self.output / "reproducibility/scope_label_guide.md",
            "# Scope Label Guide\n\n"
            + "\n".join(f"- `{row['claim_scope']}`: {row['allowed_use']}" for row in self.table_claim_scopes())
            + "\n",
        )

    def write_readme(self) -> None:
        audit = load_json(ROOT / "analysis/results/tool_effect_fragmentation_human_audit_phase6.json")
        phase6 = load_json(ROOT / "analysis/results/tool_effect_fragmentation_phase6_unified.json")
        text = f"""# Tool-Effect Invariance Paper Package

## Purpose

This package consolidates the E47 Tool-Effect Invariance / Tool-Effect Fragmentation materials for paper writing and reproducibility. It copies canonical corrected/audited artifacts, produces paper-ready tables, records source hashes, and separates audited, custom-stress, diagnostic, oracle, upper-bound, component, and local-pipeline feasibility evidence.

## Directory Overview

- `manifests/`: experiment-stage manifests and source/result mappings.
- `results/`: canonical copied result artifacts plus `legacy_weak_label/`.
- `tables/`: main and appendix tables in JSON/CSV/Markdown.
- `figures/`: figure specifications and data references.
- `audit/`: human audit packets and final audit summary.
- `failure_examples/`: curated examples for paper discussion.
- `writing/`: paper-section notes, claim boundaries, limitations, and ethics statement.
- `reproducibility/`: regeneration/validation notes and source-code snapshot.
- `source_index.json`: traceability map with hashes for copied/generated artifacts.

Scope caveat: this package is **not original-paper numeric reproduction** for ToolSafe/TS-Guard,
Safiron, IPIGuard, or CaMeL. It is an audited/custom-stress and component-stress paper
package unless a specific manifest entry explicitly states otherwise.

## Main Results Summary

- Current defenses are not merely tool-name classifiers: TS-Guard, Safiron, IPIGuard-style DAGs, and CaMeL-style structural policy cover different capability subsets.
- Surface robustness is not enough: methods can resist renaming while failing effect sensitivity, authorization sensitivity, resource binding, provenance/control dependency, evidence grounding, or utility preservation.
- IPIGuard topology is stable but topology-only outputs do not expose realized-effect decisions. Added semantic mappers diagnose the missing layer but are not deployable guards.
- CaMeL structural policy is stable under synchronized rewrites and has low safe false denial, but the custom component stress exposes control-dependency misses.
- Human audit status: `{audit.get('status')}`, upgrade gate `{audit.get('upgrade_gate')}`, corrected-label subset `{audit.get('corrected_label_subset_count')}`.

## Paper-Ready Tables

See `tables/paper_tables.json` plus individual CSV/Markdown files for:

- main capability matrix;
- counterfactual lattice summary;
- official checkpoint summary;
- structured-defense summary;
- human audit summary;
- claim-scope table;
- corrected-label and failure-mode appendix tables.

## Figure Specs

See `figures/figure_specs.md` for the counterfactual lattice, capability heatmap, failure taxonomy, IPIGuard semantic-layer diagram, and CaMeL control-dependency diagram.

## Claim Boundary

{claim_boundary_text()}

## Remaining Optional Work

- Render the figure specs as final plots.
- If needed, regenerate original experiments from external repos/checkpoints; this package does not require that for paper drafting.
- Phase 6 external DeepSeek pipeline status remains `{phase6.get('external_pipeline', {}).get('status', 'unknown')}` and should remain feasibility/status evidence only.

## Recommendation

Ready for paper drafting. The package satisfies the audited corrected-label gate and includes traceable artifacts for each main claim. It remains blocked only for claims that would require original-paper numeric reproduction or deployed-system safety validation.
"""
        write_text(self.output / "README.md", text)

    def write_source_index(self) -> None:
        write_json(self.output / "source_index.json", sorted(self.source_index, key=lambda row: row["package_path"]))


def curated_failure_examples() -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    phase3_examples = load_json(ROOT / "analysis/results/tool_effect_fragmentation_failure_examples_phase3.json", default=[])
    phase4_examples = load_json(ROOT / "analysis/results/tool_effect_fragmentation_counterfactual_phase4_failure_examples.json", default=[])
    phase5_examples = load_json(ROOT / "analysis/results/tool_effect_fragmentation_phase5_failure_examples.json", default={})
    camel = load_json(ROOT / "analysis/results/tool_effect_fragmentation_camel_miss_decomposition_phase6.json")
    semantic = load_json(ROOT / "analysis/results/tool_effect_fragmentation_ipiguard_semantic_phase6.json")

    def add(row: dict[str, Any], *, system: str, method: str, failure_type: str, interpretation: str, section: str, scope: str) -> None:
        examples.append(
            {
                "source_system": system,
                "method": method,
                "case_id": row.get("case_id") or row.get("variant_case_id") or row.get("original_case_id", ""),
                "tool_surface": row.get("tool_surface") or row.get("tool_name") or row.get("variant") or "unknown",
                "realized_effect": row.get("realized_effect") or row.get("effect") or "not_identified",
                "resource": row.get("resource") or "unknown",
                "authorization_context": str(row.get("authorized_effects") or row.get("control_source") or "see source artifact"),
                "expected_decision": row.get("expected_decision") or "N/A",
                "predicted_decision": row.get("predicted_decision") or "N/A",
                "failure_type": failure_type,
                "interpretation": interpretation,
                "paper_section": section,
                "claim_scope": scope,
            }
        )

    first = first_match(phase3_examples, method="tool_name_classifier", failure_type="tool_surface_false_allow")
    if first:
        add(first, system="agentdojo", method="tool_name_classifier", failure_type="tool_surface_false_allow", interpretation="Tool-name baseline allows a same-effect surface-shifted unsafe row.", section="Baseline fragmentation", scope="baseline")
    first = first_match(phase4_examples, method="ts_guard_official_counterfactual_stress", failure_type="same_tool_different_effect_failure")
    if first:
        add(first, system="toolsafe", method="ts_guard_official_counterfactual_stress", failure_type="same_tool_different_effect_failure", interpretation="Official checkpoint misses a visible effect-changing counterfactual in at least one case.", section="Official checkpoint stress", scope="official_method_custom_stress")
    first = first_match(phase4_examples, method="safiron_official_counterfactual_stress", failure_type="authorization_flip_failure")
    if not first:
        first = first_match(phase4_examples, method="safiron_official_counterfactual_stress", failure_type="resource_mismatch_failure")
    if first:
        add(first, system="safiron", method="safiron_official_counterfactual_stress", failure_type=first.get("failure_type", "authorization_or_resource_failure"), interpretation="Safiron shows weak authorization/resource sensitivity under the paired lattice.", section="Official checkpoint stress", scope="official_method_custom_stress")
    ipg = (phase5_examples.get("ipiguard") or [{}])[0]
    add(ipg, system="ipiguard", method="ipiguard_topology_only", failure_type="topology_only_no_effect_decision", interpretation="DAG topology is stable, but topology-only output cannot make realized-effect authorization decisions.", section="Structured defense analysis", scope="original_component_custom_stress")
    local = semantic.get("methods", {}).get("local_qwen_effect_resource_mapper", {}).get("hidden_label_row_metrics", {})
    add(
        {
            "case_id": "ipiguard_semantic_layer_summary",
            "expected_decision": "mixed",
            "predicted_decision": "unsafe_pre_allow_rate=" + str(metric_rate(local.get("unsafe_pre_allow"))),
            "effect": "semantic_mapper_tradeoff",
        },
        system="ipiguard",
        method="local_qwen_effect_resource_mapper",
        failure_type="semantic_mapper_tradeoff",
        interpretation="Local-Qwen semantic mapper improves effect sensitivity but still has unsafe pre-allow and weak resource sensitivity.",
        section="Semantic-layer analysis",
        scope="diagnostic",
    )
    for row in camel.get("control_dependency_failure_examples", [])[:3]:
        add(row, system="camel", method="camel_structural_policy", failure_type="control_dependency_violation", interpretation=row.get("failure_reason", ""), section="Structured defense failure taxonomy", scope="original_component_custom_stress")
    evidence = first_match(phase4_examples, method="non_oracle_saved_evidence_verifier")
    add(
        evidence or {"case_id": "non_oracle_evidence_summary", "expected_decision": "mixed", "predicted_decision": "ABSTAIN", "realized_effect": "coverage_limited"},
        system="agentdojo",
        method="non_oracle_saved_evidence_verifier",
        failure_type="abstain_coverage_limitation",
        interpretation="Non-oracle evidence verifier abstains when observable evidence is missing; useful diagnostic, not complete guard.",
        section="Evidence grounding",
        scope="diagnostic",
    )
    oracle = first_match(phase4_examples, method="effect_resource_oracle")
    add(
        oracle or {"case_id": "effect_resource_oracle_summary", "expected_decision": "all", "predicted_decision": "correct", "realized_effect": "upper_bound"},
        system="counterfactual_core",
        method="effect_resource_oracle",
        failure_type="upper_bound_success",
        interpretation="Oracle/effect-resource upper bound succeeds by construction and is not deployable.",
        section="Upper bounds",
        scope="upper_bound",
    )
    return examples


def first_match(rows: Any, **criteria: str) -> dict[str, Any] | None:
    if not isinstance(rows, list):
        return None
    for row in rows:
        if all(row.get(key) == value for key, value in criteria.items()):
            return row
    return None


def validate_package(output: Path) -> None:
    required = [
        "README.md",
        "source_index.json",
        "manifests/all_experiments_manifest.json",
        "manifests/all_experiments_manifest.md",
        "tables/paper_tables.json",
        "tables/main_capability_matrix.md",
        "tables/main_capability_matrix.csv",
        "tables/counterfactual_lattice_summary.md",
        "tables/official_checkpoint_summary.md",
        "tables/structured_defense_summary.md",
        "tables/human_audit_summary.md",
        "tables/claim_scope_table.md",
        "tables/appendix_corrected_vs_weak_labels.md",
        "tables/appendix_camel_miss_decomposition.md",
        "tables/appendix_ipiguard_consistency_by_variant.md",
        "tables/appendix_external_pipeline_feasibility.md",
        "tables/appendix_failure_case_table.md",
        "figures/figure_specs.md",
        "audit/human_audit_packet_phase6.jsonl",
        "audit/human_audit_secondary_phase6.jsonl",
        "audit/tool_effect_fragmentation_human_audit_phase6.json",
        "failure_examples/failure_examples.json",
        "writing/claim_boundary.md",
        "reproducibility/README.md",
        "reproducibility/scope_label_guide.md",
    ]
    missing = [path for path in required if not (output / path).exists()]
    if missing:
        raise SystemExit(f"missing package artifacts: {missing}")

    audit = load_json(output / "audit/tool_effect_fragmentation_human_audit_phase6.json")
    if audit.get("upgrade_gate") is not True:
        raise SystemExit("human audit upgrade gate is not true")
    camel = load_json(output / "results/canonical/tool_effect_fragmentation_camel_miss_decomposition_phase6.json")
    if camel.get("corrected_vs_weak_label_delta", {}).get("decision_metric_changed") is not False:
        raise SystemExit("CaMeL corrected-label decision metrics changed unexpectedly")
    if not (output / "results/legacy_weak_label/camel_no_side_effect_original_weak_label_reference.json").exists():
        raise SystemExit("legacy weak-label reference is missing")

    source_index = load_json(output / "source_index.json")
    for row in source_index:
        path = output / row["package_path"]
        if not path.exists():
            raise SystemExit(f"source_index package path missing: {row['package_path']}")
        if sha256(path) != row["sha256"]:
            raise SystemExit(f"source_index hash mismatch: {row['package_path']}")

    scopes = read_csv(output / "tables/claim_scope_table.csv")
    if not any(row.get("claim_scope") == "upper_bound" for row in scopes):
        raise SystemExit("claim scope table lacks upper_bound row")
    if not any(row.get("claim_scope") == "original_pipeline_local_model" for row in scopes):
        raise SystemExit("claim scope table lacks local-pipeline feasibility row")

    readme = (output / "README.md").read_text(encoding="utf-8")
    if "Ready for paper drafting" not in readme:
        raise SystemExit("README does not state paper drafting readiness")
    if "not original-paper numeric reproduction" not in readme:
        raise SystemExit("README lacks original-paper reproduction caveat")


def write_table_set(base: Path, rows: list[dict[str, Any]], columns: list[str], title: str) -> None:
    write_json(base.with_suffix(".json"), rows)
    write_csv(base.with_suffix(".csv"), rows, columns)
    write_markdown_table(base.with_suffix(".md"), rows, columns, title=title)


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: csv_cell(row.get(column)) for column in columns})


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_markdown_table(path: Path, rows: list[dict[str, Any]], columns: list[str], *, title: str) -> None:
    lines = [f"# {title}", "", "| " + " | ".join(columns) + " |", "|" + "|".join(["---"] * len(columns)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(md_cell(row.get(column)) for column in columns) + " |")
    lines.append("")
    write_text(path, "\n".join(lines))


def write_kv_markdown(path: Path, title: str, payload: dict[str, Any]) -> None:
    lines = [f"# {title}", ""]
    for key, value in payload.items():
        lines.append(f"- **{key}**: `{csv_cell(value)}`")
    lines.append("")
    write_text(path, "\n".join(lines))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def jsonl_count(path: Path) -> int | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def metric_rate(value: Any) -> float | int | None:
    if isinstance(value, dict):
        return value.get("rate")
    if isinstance(value, (float, int)):
        return value
    return None


def csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def md_cell(value: Any) -> str:
    text = csv_cell(value)
    return text.replace("|", "\\|").replace("\n", " ")


def infer_columns(rows: list[dict[str, Any]]) -> list[str]:
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    return columns or ["empty"]


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


def slugify(text: str) -> str:
    allowed = []
    for char in text.lower():
        if char.isalnum():
            allowed.append(char)
        elif char in {" ", "-", "/", "_"}:
            allowed.append("_")
    return "_".join(part for part in "".join(allowed).split("_") if part)


def scope_for_method(method: str) -> str:
    if method in {"effect_resource_oracle", "execution_evidence_upper_bound", "oracle_effect_resource_mapper"}:
        return "upper_bound"
    if method in {"ts_guard_official_counterfactual_stress", "safiron_official_counterfactual_stress"}:
        return "official_method_custom_stress"
    if method.startswith("ipiguard") or method.startswith("camel"):
        return "original_component_custom_stress"
    if "qwen" in method or method.endswith("mapper"):
        return "diagnostic" if "mapper" in method else "baseline"
    return "baseline"


def claim_boundary_text() -> str:
    return """Allowed claims:

- Weak tool-surface baselines overestimate safety under held-out or counterfactual shifts.
- Official checkpoints are not merely tool-name classifiers.
- Simple tool rename robustness does not imply tool-effect invariance.
- TS-Guard, Safiron, IPIGuard, and CaMeL cover different subsets of the joint safety decision problem.
- IPIGuard DAG topology is stable but needs an effect/resource semantic layer for effect-level decision sensitivity.
- CaMeL structural policy is stable in the tested component but misses control-dependency violations in the custom stress.
- Human audit supports the corrected counterfactual labels under the pre-registered thresholds.
- Evidence-grounded or effect/resource-aware layers can help diagnose missing capabilities, but current non-oracle versions are not complete deployable guards.

Disallowed claims:

- Do not claim full original-paper benchmark reproduction.
- Do not claim ToolSafe, Safiron, IPIGuard, or CaMeL generally fail.
- Do not claim graph, provenance, or structural defenses generally fail.
- Do not claim execution evidence is a complete deployable solution.
- Do not claim LLMs do not understand tools at all.
- Do not treat local-model pipeline feasibility as defense-effectiveness evidence.
- Do not treat oracle or upper-bound rows as deployable methods.
- Do not treat artifact-completion gates as safety-acceptance gates.
"""


if __name__ == "__main__":
    main()
