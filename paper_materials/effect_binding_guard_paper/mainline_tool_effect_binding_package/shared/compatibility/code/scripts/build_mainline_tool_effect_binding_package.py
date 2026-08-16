#!/usr/bin/env python3
"""Build the mainline Tool-Effect Binding paper-materials package.

This utility copies/references existing paper materials, experiment artifacts,
code, tests, audits, and writing support into one clean folder for later paper
writing. It does not rerun experiments, call APIs/models, rewrite the paper, or
modify canonical outputs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
PAPER_ROOT = ROOT / "paper_materials/effect_binding_guard_paper"
TARGET = PAPER_ROOT / "mainline_tool_effect_binding_package"
OLD_E47_PACKAGE = ROOT / "paper_package_tool_effect_invariance"

REQUIRED_DIRS = [
    "paper_drafts",
    "method_materials",
    "data",
    "results",
    "code",
    "tests",
    "tables",
    "figures",
    "audit",
    "reproduction",
    "manifests",
    "logs",
]

REQUIRED_TOP_FILES = [
    "README.md",
    "PACKAGE_SUMMARY.md",
    "MISSING_FILES.md",
    "build_status.md",
    "warnings.md",
    "MAINLINE_CLAIM_BOUNDARY.md",
    "WRITING_NEXT_STEPS.md",
    "manifests/manifest.json",
    "manifests/manifest.csv",
    "manifests/manifest.md",
    "tables/table1_existing_defenses_capability_matrix.csv",
    "tables/table1_existing_defenses_capability_matrix.md",
    "tables/table2_reference_hard_guard.csv",
    "tables/table2_reference_hard_guard.md",
    "tables/table3_resource_auth_bottleneck.csv",
    "tables/table3_resource_auth_bottleneck.md",
    "tables/table4_precommit_authz_prototype.csv",
    "tables/table4_precommit_authz_prototype.md",
    "tables/table5_e55_ablation.csv",
    "tables/table5_e55_ablation.md",
    "tables/table6_e57_validity_checks.csv",
    "tables/table6_e57_validity_checks.md",
    "tables/appendix_materials_index.md",
]

PACKAGE_EXTENSIONS = {
    ".bib",
    ".csv",
    ".json",
    ".jsonl",
    ".md",
    ".pdf",
    ".png",
    ".py",
    ".sh",
    ".svg",
    ".tex",
    ".txt",
    ".yaml",
    ".yml",
}

TEXT_EXTENSIONS = PACKAGE_EXTENSIONS - {".pdf", ".png"}
SKIP_DIR_NAMES = {"__pycache__", ".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", "node_modules", "models"}
SKIP_SUFFIXES = {".aux", ".bbl", ".blg", ".fdb_latexmk", ".fls", ".log", ".out", ".pyc", ".synctex.gz", ".toc"}

EXPECTED_PATHS = [
    "paper_package_tool_effect_invariance/paper_draft/main.tex",
    "paper_package_tool_effect_invariance/paper_draft/main.pdf",
    "paper_package_tool_effect_invariance/tables/main_capability_matrix.csv",
    "paper_package_tool_effect_invariance/tables/official_checkpoint_summary.csv",
    "paper_package_tool_effect_invariance/tables/structured_defense_summary.csv",
    "paper_materials/effect_binding_guard_paper/ndss_candidate/main.tex",
    "paper_materials/effect_binding_guard_paper/ndss_candidate/main.pdf",
    "paper_materials/effect_binding_guard_paper/ndss_candidate/references.bib",
    "paper_materials/effect_binding_guard_paper/ndss_candidate_pre_e56_backup",
    "paper_materials/effect_binding_guard_paper/draft_polished",
    "analysis/results/e48_tuple_guard_results.json",
    "analysis/results/e50_hard_guard_robustness_results.json",
    "analysis/results/e55_precommit_authz_results_strict.json",
    "analysis/results/e55_decision_path_audit.json",
    "analysis/results/e56_final_report.json",
    "analysis/results/e57_validity_checks_report.json",
    "data/tool_effect_fragmentation/counterfactual_core_phase4.jsonl",
    "data/e48_effect_binding_unified.jsonl",
    "data/e48_effect_binding_pairs.jsonl",
    "data/e55_precommit_authz_dataset.jsonl",
    "src/experiments/tool_effect_fragmentation/run_tool_effect_fragmentation_phase4.py",
    "src/experiments/effect_binding_guard/run_e48.py",
    "src/experiments/effect_binding_guard/run_e50.py",
    "src/experiments/effect_binding_calibrator",
    "src/experiments/effect_binding_guard/e55_precommit_authz/run_e55.py",
    "src/experiments/effect_binding_guard/e55_precommit_authz/e56_audit.py",
    "src/experiments/effect_binding_guard/e55_precommit_authz/e57_validity_checks.py",
    "tests/test_tool_effect_fragmentation_phase4.py",
    "tests/test_effect_binding_guard_e48.py",
    "tests/test_effect_binding_guard_e50.py",
    "tests/test_effect_binding_guard_e55_precommit_authz.py",
    "tests/test_effect_binding_guard_e56_audit.py",
    "tests/test_effect_binding_guard_e57_validity.py",
]


@dataclass(frozen=True)
class Candidate:
    source: Path
    section: str
    experiment_tag: str
    role: str
    claim_scope: str
    notes: str = ""


@dataclass
class ManifestEntry:
    package_path: str
    original_path: str
    experiment_tag: str
    file_type: str
    role: str
    copied_or_referenced: str
    claim_scope: str
    notes: str
    size_bytes: int
    sha256: str


@dataclass
class CoreNumber:
    metric: str
    display_value: str
    source_value: str
    source_file: str
    key_path: str
    source_type: str
    claim_scope: str
    safe_wording: str
    notes: str = ""


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def md_table(headers: list[str], rows: Iterable[Iterable[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(x).replace("\n", " ") for x in row) + " |")
    return "\n".join(out)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def should_skip(path: Path) -> bool:
    if is_inside(path, TARGET):
        return True
    if any(part in SKIP_DIR_NAMES for part in path.parts):
        return True
    if path.suffix in SKIP_SUFFIXES:
        return True
    if path.suffix and path.suffix.lower() not in PACKAGE_EXTENSIONS:
        return True
    return False


def infer_tag(path: Path) -> str:
    text = rel(path).lower()
    if "tool_effect_fragmentation" in text or "paper_package_tool_effect_invariance" in text:
        return "E47"
    for tag in ["e57", "e56", "e55", "e50", "e49", "e48"]:
        if tag in text:
            return tag.upper()
    if "ndss" in text or "paper_materials" in text:
        return "paper"
    return "support"


def dest_rel(path: Path, section: str) -> Path:
    original = Path(rel(path))
    if original.parts and original.parts[0] == "paper_package_tool_effect_invariance":
        return Path(*original.parts[1:])
    if original.parts[:2] == ("paper_materials", "effect_binding_guard_paper"):
        return Path(*original.parts[2:])
    return original


def add_file(candidates: list[Candidate], path: Path, section: str, role: str, claim_scope: str, tag: str | None = None, notes: str = "") -> None:
    if not path.exists() or not path.is_file() or should_skip(path):
        return
    candidates.append(Candidate(path, section, tag or infer_tag(path), role, claim_scope, notes))


def add_tree(candidates: list[Candidate], root: Path, section: str, role: str, claim_scope: str, tag: str | None = None, notes: str = "") -> None:
    if not root.exists():
        return
    if root.is_file():
        add_file(candidates, root, section, role, claim_scope, tag, notes)
        return
    for path in sorted(root.rglob("*")):
        add_file(candidates, path, section, role, claim_scope, tag, notes)


def add_glob(candidates: list[Candidate], pattern: str, section: str, role: str, claim_scope: str, tag: str | None = None, notes: str = "") -> None:
    for path in sorted(ROOT.glob(pattern)):
        add_tree(candidates, path, section, role, claim_scope, tag, notes)


def discover_candidates() -> list[Candidate]:
    candidates: list[Candidate] = []

    # Paper drafts and writing sources.
    add_tree(candidates, OLD_E47_PACKAGE / "paper_draft", "paper_drafts", "E47 paper draft", "controlled measurement draft; not final submission", "E47")
    add_tree(candidates, PAPER_ROOT / "ndss_candidate", "paper_drafts", "current NDSS candidate", "2-page compact candidate; not submission-ready", "paper")
    for subdir in ["draft", "draft_polished", "writing_package_e58", "summaries", "claim_boundary", "e55_precommit_authz"]:
        add_tree(candidates, PAPER_ROOT / subdir, "paper_drafts", "Effect-Binding paper material", "paper writing support", "paper")

    # Method materials.
    add_tree(candidates, OLD_E47_PACKAGE / "writing", "method_materials", "E47 writing/method notes", "controlled measurement and claim-boundary material", "E47")
    add_tree(candidates, OLD_E47_PACKAGE / "manifests", "method_materials", "E47 experiment manifest", "custom stress scope manifest", "E47")
    add_tree(candidates, PAPER_ROOT / "writing_package_e58", "method_materials", "E58 writing package source", "source-of-truth numbers and writing briefs", "paper")
    add_tree(candidates, PAPER_ROOT / "summaries", "method_materials", "Effect-Binding writing summary", "paper writing support", "paper")

    # Data.
    add_tree(candidates, OLD_E47_PACKAGE / "data", "data", "E47 package data", "custom stress data", "E47")
    add_tree(candidates, ROOT / "data/tool_effect_fragmentation", "data", "E47 tool-effect fragmentation data", "custom stress data", "E47")
    for pattern in ["data/e48_*", "data/e49_*", "data/e50_*", "data/e55_*"]:
        add_glob(candidates, pattern, "data", "Effect-Binding data/stress set", "controlled/custom stress data")

    # Results.
    add_tree(candidates, OLD_E47_PACKAGE / "results", "results", "E47 package canonical results", "custom stress result", "E47")
    for prefix in ["tool_effect_fragmentation*", "e48_*", "e49_*", "e50_*", "e55_*", "e56_*", "e57_*"]:
        add_glob(candidates, f"analysis/results/{prefix}", "results", "experiment result", "controlled/custom stress result")

    # Code.
    add_tree(candidates, ROOT / "src/experiments/tool_effect_fragmentation", "code", "E47 implementation", "custom stress implementation", "E47")
    add_tree(candidates, ROOT / "src/experiments/effect_binding_guard", "code", "E48/E50/E55/E56/E57 implementation", "mainline method/prototype implementation", "E48-E57")
    add_tree(candidates, ROOT / "src/experiments/effect_binding_calibrator", "code", "E49 diagnostic implementation", "diagnostic appendix only", "E49")
    for script in [
        "scripts/build_tool_effect_paper_package.py",
        "scripts/build_effect_binding_guard_paper_materials.py",
        "scripts/build_effect_binding_writing_package_e58.py",
        "scripts/build_e58_consolidated_package.py",
        "scripts/build_mainline_tool_effect_binding_package.py",
        "scripts/run_e47_phase5_full.sh",
        "scripts/status_e47_phase5_full.sh",
    ]:
        add_file(candidates, ROOT / script, "code", "builder or reproduction helper", "packaging/reproduction support")

    # Tests.
    for pattern in ["tests/test_tool_effect_fragmentation*.py", "tests/test_effect_binding*.py"]:
        add_glob(candidates, pattern, "tests", "relevant validation test", "test support")

    # Tables, figures, audit, reproduction.
    add_tree(candidates, OLD_E47_PACKAGE / "tables", "tables", "E47 paper-ready table", "custom stress table", "E47")
    add_tree(candidates, PAPER_ROOT / "tables", "tables", "Effect-Binding table", "paper table", "paper")
    add_tree(candidates, OLD_E47_PACKAGE / "figures", "figures", "E47 figure spec", "figure plan/spec", "E47")
    add_tree(candidates, PAPER_ROOT / "figures", "figures", "Effect-Binding figure spec", "figure plan/spec", "paper")
    add_tree(candidates, OLD_E47_PACKAGE / "audit", "audit", "E47 human audit material", "audit material", "E47")
    add_tree(candidates, OLD_E47_PACKAGE / "failure_examples", "audit", "E47 failure example", "failure analysis", "E47")
    add_tree(candidates, PAPER_ROOT / "failure_examples", "audit", "Effect-Binding failure example", "failure analysis", "paper")
    for pattern in ["analysis/results/e55_*audit*", "analysis/results/e55_*strict*", "analysis/results/e56_*", "analysis/results/e57_*", "analysis/results/tool_effect_fragmentation_human_audit_phase6.*", "data/tool_effect_fragmentation/human_audit*"]:
        add_glob(candidates, pattern, "audit", "audit/validity artifact", "audit material")
    add_tree(candidates, OLD_E47_PACKAGE / "reproducibility", "reproduction", "E47 reproducibility material", "reproduction support", "E47")
    add_tree(candidates, PAPER_ROOT / "reproduction", "reproduction", "Effect-Binding reproduction material", "reproduction support", "paper")

    return candidates


def copy_or_reference(candidate: Candidate, threshold_bytes: int) -> ManifestEntry:
    src = candidate.source
    size = src.stat().st_size
    digest = sha256(src)
    target_rel = Path(candidate.section) / dest_rel(src, candidate.section)
    dest = TARGET / target_rel
    if size <= threshold_bytes:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        action = "copied"
        package_path = rel(dest)
    else:
        ref_dest = dest.with_suffix(dest.suffix + ".reference.txt")
        ref_dest.parent.mkdir(parents=True, exist_ok=True)
        write_text(ref_dest, f"# Reference-Only Large File\n\nOriginal path: `{rel(src)}`\n\nSize bytes: `{size}`\n\nSHA256: `{digest}`\n")
        action = "referenced"
        package_path = rel(ref_dest)
    return ManifestEntry(package_path, rel(src), candidate.experiment_tag, src.suffix.lower().lstrip(".") or "file", candidate.role, action, candidate.claim_scope, candidate.notes, size, digest)


def read_json(path: str) -> Any | None:
    p = ROOT / path
    if not p.exists():
        return None
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_path(obj: Any, key_path: str) -> Any:
    cur = obj
    for part in key_path.split("."):
        if isinstance(cur, dict):
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit():
            cur = cur[int(part)]
        else:
            raise KeyError(key_path)
    return cur


def display_value(value: Any, decimals: int = 3) -> str:
    if isinstance(value, bool):
        return "passed" if value else "failed"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.{decimals}f}"
    return str(value)


def add_core(core: list[CoreNumber], metric: str, source_file: str, key_path: str, scope: str, wording: str, decimals: int = 3) -> None:
    data = read_json(source_file)
    source_type = "existing_result_file"
    notes = ""
    value: Any = ""
    if data is None:
        source_type = "missing"
        notes = "Source file missing."
    else:
        try:
            value = get_path(data, key_path)
        except Exception as exc:  # noqa: BLE001
            source_type = "missing_key"
            notes = f"Missing key: {exc}"
    core.append(CoreNumber(metric, display_value(value, decimals) if value != "" else "", str(value), source_file, key_path, source_type, scope, wording, notes))


def add_domain_count(core: list[CoreNumber]) -> None:
    source_file = "analysis/results/e55_precommit_authz_results_strict.json"
    data = read_json(source_file)
    try:
        counts = get_path(data, "dataset.domain_counts") if data else {}
        value = len(counts)
        source_type = "existing_result_file"
        notes = "Derived by counting dataset.domain_counts keys."
    except Exception as exc:  # noqa: BLE001
        value = ""
        source_type = "missing_key"
        notes = f"Could not derive domain count: {exc}"
    core.append(CoreNumber("E55 domain count", str(value), str(value), source_file, "dataset.domain_counts", source_type, "controlled local contract evidence", "E55 covers five deterministic local mock domains.", notes))


def collect_core_numbers() -> list[CoreNumber]:
    core: list[CoreNumber] = []
    e48 = "analysis/results/e48_tuple_guard_results.json"
    e50 = "analysis/results/e50_hard_guard_robustness_results.json"
    e55 = "analysis/results/e55_precommit_authz_results_strict.json"
    e55_sensitivity = "analysis/results/e55_human_corrected_sensitivity.json"
    e55_v2 = "analysis/results/e55_v2_precommit_authz_results_strict.json"
    e55_audit = "analysis/results/e55_decision_path_audit.json"
    e56 = "analysis/results/e56_final_report.json"
    e57 = "analysis/results/e57_validity_checks_report.json"
    e57_v2 = "analysis/results/e57_v2_validity_checks_report.json"

    add_core(core, "E48 hard guard UPA", e48, "methods.effect_binding_guard_full.overall.unsafe_pre_allow.rate", "E48 hard guard custom stress", "Reference hard guard has low but nonzero unsafe pre-allow.")
    add_core(core, "E48 hard guard FDeny", e48, "methods.effect_binding_guard_full.overall.safe_false_deny.rate", "E48 hard guard custom stress", "Reference hard guard has measurable false denial.")
    add_core(core, "E48 hard guard coverage", e48, "methods.effect_binding_guard_full.overall.coverage.rate", "E48 hard guard custom stress", "Reference hard guard has high coverage on E48.")
    add_core(core, "Held-out UPA", e48, "methods.effect_binding_guard_full.by_split.test.unsafe_pre_allow.rate", "held-out diagnostic", "Held-out split UPA must be reported separately.")
    add_core(core, "Held-out FDeny", e48, "methods.effect_binding_guard_full.by_split.test.safe_false_deny.rate", "held-out diagnostic", "Held-out split false denial is nonzero.")
    add_core(core, "Held-out coverage", e48, "methods.effect_binding_guard_full.by_split.test.coverage.rate", "held-out diagnostic", "Held-out split coverage is high.")
    add_core(core, "Source-balanced UPA", e50, "source_balanced.aggregate_fixed_policy.unsafe_pre_allow.mean", "E50 robustness audit", "Source-balanced robustness preserves nonzero unsafe pre-allow.")
    add_core(core, "Source-balanced FDeny", e50, "source_balanced.aggregate_fixed_policy.safe_false_deny.mean", "E50 robustness audit", "Source-balanced robustness preserves nonzero false denial.")
    add_core(core, "Source-balanced coverage", e50, "source_balanced.aggregate_fixed_policy.coverage.mean", "E50 robustness audit", "Source-balanced robustness preserves high coverage.")
    add_core(core, "E50 resource/auth stress UPA", e50, "resource_authorization_stress.methods.effect_binding_guard_full.overall.unsafe_pre_allow.rate", "negative controlled stress", "Resource/authorization binding is the central hard-guard bottleneck.")
    add_core(core, "E50 resource/auth stress coverage", e50, "resource_authorization_stress.methods.effect_binding_guard_full.overall.coverage.rate", "negative controlled stress", "The resource/auth bottleneck is not only abstention.")
    add_core(core, "E50 provenance stress UPA", e50, "control_provenance_stress.methods.effect_binding_guard_full.overall.unsafe_pre_allow.rate", "controlled provenance stress", "Provenance overlay blocks unsafe pre-allow in this controlled stress.")
    add_core(core, "E50 provenance stress FDeny", e50, "control_provenance_stress.methods.effect_binding_guard_full.overall.safe_false_deny.rate", "controlled provenance stress", "Provenance overlay has a utility cost.")
    add_core(core, "E50 provenance stress coverage", e50, "control_provenance_stress.methods.effect_binding_guard_full.overall.coverage.rate", "controlled provenance stress", "Provenance stress is coverage-limited.")
    add_core(core, "E55 rows", e55, "dataset.n_rows", "controlled local contract evidence", "E55 contains 600 deterministic local mock rows.", decimals=0)
    add_domain_count(core)
    add_core(core, "E55 existing hard guard UPA", e55, "methods.existing_hard_effect_binding_guard.overall.unsafe_pre_allow.rate", "E55 baseline", "Existing hard guard leaves unsafe pre-allow in E55.")
    add_core(core, "E55 existing hard guard FDeny", e55, "methods.existing_hard_effect_binding_guard.overall.safe_false_deny.rate", "E55 baseline", "Existing hard guard avoids false denial but abstains heavily.")
    add_core(core, "E55 existing hard guard coverage", e55, "methods.existing_hard_effect_binding_guard.overall.coverage.rate", "E55 baseline", "Existing hard guard has low coverage.")
    add_core(core, "E55 existing hard guard abstain", e55, "methods.existing_hard_effect_binding_guard.overall.abstain_rate.rate", "E55 baseline", "Existing hard guard is abstention-heavy.")
    add_core(core, "E55 authz-aware guard UPA", e55, "methods.authz_aware_effect_binding_guard.overall.unsafe_pre_allow.rate", "controlled local contract evidence", "Authorization-aware guard eliminates unsafe pre-allow in E55.")
    add_core(core, "E55 authz-aware guard FDeny", e55, "methods.authz_aware_effect_binding_guard.overall.safe_false_deny.rate", "controlled local contract evidence", "Authorization-aware guard does not falsely deny safe E55 rows.")
    add_core(core, "E55 authz-aware guard coverage", e55, "methods.authz_aware_effect_binding_guard.overall.coverage.rate", "controlled local contract evidence", "Authorization-aware guard has high E55 coverage.")
    add_core(core, "E55 authz-aware guard abstain", e55, "methods.authz_aware_effect_binding_guard.overall.abstain_rate.rate", "controlled local contract evidence", "Authorization-aware guard has limited E55 abstention.")
    add_core(core, "E55 corrected authz-aware UPA", e55_sensitivity, "full_600_minimal_correction.minimal_human_corrected_labels.authz_aware_effect_binding_guard.unsafe_pre_allow.rate", "corrected-label sensitivity", "Human-corrected sensitivity preserves zero unsafe pre-allow.")
    add_core(core, "E55 corrected authz-aware FDeny", e55_sensitivity, "full_600_minimal_correction.minimal_human_corrected_labels.authz_aware_effect_binding_guard.safe_false_deny.rate", "corrected-label sensitivity", "Human-corrected sensitivity introduces a small false-denial rate.")
    add_core(core, "E55 corrected authz-aware coverage", e55_sensitivity, "full_600_minimal_correction.minimal_human_corrected_labels.authz_aware_effect_binding_guard.coverage.rate", "corrected-label sensitivity", "Human-corrected sensitivity preserves original coverage.")
    add_core(core, "E55-v2 authz-aware UPA", e55_v2, "methods.authz_aware_effect_binding_guard.overall.unsafe_pre_allow.rate", "corrected rerun", "E55-v2 corrected rerun keeps unsafe pre-allow at zero.")
    add_core(core, "E55-v2 authz-aware FDeny", e55_v2, "methods.authz_aware_effect_binding_guard.overall.safe_false_deny.rate", "corrected rerun", "E55-v2 corrected rerun keeps false denial at zero.")
    add_core(core, "E55-v2 authz-aware coverage", e55_v2, "methods.authz_aware_effect_binding_guard.overall.coverage.rate", "corrected rerun", "E55-v2 coverage is lower after removing unknown-resource fallback.")
    add_core(core, "E55 no multi-resource UPA", e55, "methods.authz_aware_no_multi_resource_expansion.overall.unsafe_pre_allow.rate", "E55 ablation", "Multi-resource expansion is necessary in E55.")
    add_core(core, "E55 no operation mode UPA", e55, "methods.authz_aware_no_operation_mode.overall.unsafe_pre_allow.rate", "E55 ablation", "Operation-mode binding is necessary in E55.")
    add_core(core, "E55 no provenance UPA", e55, "methods.authz_aware_no_provenance_overlay.overall.unsafe_pre_allow.rate", "E55 ablation", "Provenance overlay contributes safety in E55.")
    add_core(core, "E55 no alias FDeny", e55, "methods.authz_aware_no_alias_resolution.overall.safe_false_deny.rate", "E55 ablation", "Alias resolution protects utility in E55.")
    add_core(core, "E56 decision-path audit", e55_audit, "passed", "audit evidence", "Decision-path audit passed.")
    add_core(core, "E56 strict replay", e56, "strict_mode_passed", "audit evidence", "Strict label-hidden replay passed.")
    add_core(core, "E57 perturbation stability", e57, "perturbation_stability_passed", "validity diagnostic", "Resource-name perturbation stability passed.")
    add_core(core, "E57 UPA delta", e57, "perturbation.authz_aware_upa_delta", "validity diagnostic", "Perturbation did not change UPA.")
    add_core(core, "E57 coverage delta", e57, "perturbation.authz_aware_coverage_delta", "validity diagnostic", "Perturbation did not change coverage.")
    add_core(core, "E57 changed decisions", e57, "perturbation.changed_decision_count", "validity diagnostic", "Perturbation changed zero decisions.", decimals=0)
    add_core(core, "E57 reference decision agreement", e57, "reference_authorizer.decision_agreement", "validity diagnostic", "Independent reference authorizer agrees on decisions.")
    add_core(core, "E57 atom count agreement", e57, "reference_authorizer.atom_count_agreement", "validity diagnostic", "Independent reference authorizer agrees on atom counts.")
    add_core(core, "E57 atom resource-set agreement", e57, "reference_authorizer.atom_resource_set_agreement", "validity diagnostic", "Independent reference authorizer agrees on atom resource sets.")
    add_core(core, "E57 spot-audit rows", e57, "spot_audit.n_rows", "inspection packet", "E57 generated a 60-row spot-audit packet.", decimals=0)
    add_core(core, "E57-v2 perturbation stability", e57_v2, "perturbation_stability_passed", "corrected-rerun validity diagnostic", "E55-v2 resource-name perturbation stability passed.")
    add_core(core, "E57-v2 UPA delta", e57_v2, "perturbation.authz_aware_upa_delta", "corrected-rerun validity diagnostic", "E55-v2 perturbation did not change UPA.")
    add_core(core, "E57-v2 coverage delta", e57_v2, "perturbation.authz_aware_coverage_delta", "corrected-rerun validity diagnostic", "E55-v2 perturbation did not change coverage.")
    add_core(core, "E57-v2 changed decisions", e57_v2, "perturbation.changed_decision_count", "corrected-rerun validity diagnostic", "E55-v2 perturbation changed zero decisions.", decimals=0)
    add_core(core, "E57-v2 reference decision agreement", e57_v2, "reference_authorizer.decision_agreement", "corrected-rerun validity diagnostic", "E55-v2 reference authorizer agrees on decisions.")
    add_core(core, "E57-v2 atom count agreement", e57_v2, "reference_authorizer.atom_count_agreement", "corrected-rerun validity diagnostic", "E55-v2 reference authorizer agrees on atom counts.")
    add_core(core, "E57-v2 atom resource-set agreement", e57_v2, "reference_authorizer.atom_resource_set_agreement", "corrected-rerun validity diagnostic", "E55-v2 reference authorizer agrees on atom resource sets.")
    add_core(core, "E57-v2 spot-audit rows", e57_v2, "spot_audit.n_rows", "corrected-rerun inspection packet", "E57-v2 generated a 60-row spot-audit packet.", decimals=0)
    return core


def write_core_tables(core: list[CoreNumber]) -> None:
    fields = ["metric", "display_value", "source_value", "source_file", "key_path", "source_type", "claim_scope", "safe_wording", "notes"]
    rows = [c.__dict__ for c in core]

    def emit(name: str, metrics: list[str]) -> None:
        part = [c for c in core if c.metric in metrics]
        write_csv(TARGET / f"tables/{name}.csv", [c.__dict__ for c in part], fields)
        write_text(TARGET / f"tables/{name}.md", f"# {name.replace('_', ' ').title()}\n\n" + md_table(["Metric", "Value", "Scope", "Source"], [[c.metric, c.display_value, c.claim_scope, c.source_file] for c in part]))

    emit("table2_reference_hard_guard", ["E48 hard guard UPA", "E48 hard guard FDeny", "E48 hard guard coverage", "Held-out UPA", "Held-out FDeny", "Held-out coverage", "Source-balanced UPA", "Source-balanced FDeny", "Source-balanced coverage"])
    emit("table3_resource_auth_bottleneck", ["E50 resource/auth stress UPA", "E50 resource/auth stress coverage", "E50 provenance stress UPA", "E50 provenance stress FDeny", "E50 provenance stress coverage"])
    emit("table4_precommit_authz_prototype", ["E55 rows", "E55 domain count", "E55 existing hard guard UPA", "E55 existing hard guard FDeny", "E55 existing hard guard coverage", "E55 existing hard guard abstain", "E55 authz-aware guard UPA", "E55 authz-aware guard FDeny", "E55 authz-aware guard coverage", "E55 authz-aware guard abstain", "E55 corrected authz-aware UPA", "E55 corrected authz-aware FDeny", "E55 corrected authz-aware coverage", "E55-v2 authz-aware UPA", "E55-v2 authz-aware FDeny", "E55-v2 authz-aware coverage", "E56 decision-path audit", "E56 strict replay"])
    emit("table5_e55_ablation", ["E55 no multi-resource UPA", "E55 no operation mode UPA", "E55 no provenance UPA", "E55 no alias FDeny"])
    emit("table6_e57_validity_checks", ["E57 perturbation stability", "E57 UPA delta", "E57 coverage delta", "E57 changed decisions", "E57 reference decision agreement", "E57 atom count agreement", "E57 atom resource-set agreement", "E57 spot-audit rows", "E57-v2 perturbation stability", "E57-v2 UPA delta", "E57-v2 coverage delta", "E57-v2 changed decisions", "E57-v2 reference decision agreement", "E57-v2 atom count agreement", "E57-v2 atom resource-set agreement", "E57-v2 spot-audit rows"])

    cap_src = ROOT / "paper_package_tool_effect_invariance/tables/main_capability_matrix.csv"
    cap_rows = []
    if cap_src.exists():
        with cap_src.open("r", encoding="utf-8", newline="") as f:
            cap_rows = list(csv.DictReader(f))
    if cap_rows:
        write_csv(TARGET / "tables/table1_existing_defenses_capability_matrix.csv", cap_rows, list(cap_rows[0].keys()))
        preview = [[row.get(k, "") for k in list(cap_rows[0].keys())[:6]] for row in cap_rows[:30]]
        write_text(TARGET / "tables/table1_existing_defenses_capability_matrix.md", "# Existing Defenses Capability Matrix\n\nSource: `paper_package_tool_effect_invariance/tables/main_capability_matrix.csv`\n\n" + md_table(list(cap_rows[0].keys())[:6], preview))
    else:
        write_text(TARGET / "tables/table1_existing_defenses_capability_matrix.md", "# Existing Defenses Capability Matrix\n\nMissing source table.")
        write_csv(TARGET / "tables/table1_existing_defenses_capability_matrix.csv", [], ["missing"])

    appendices = sorted((ROOT / "paper_package_tool_effect_invariance/tables").glob("appendix_*")) + sorted((PAPER_ROOT / "tables").glob("*"))
    write_text(TARGET / "tables/appendix_materials_index.md", "# Appendix Materials Index\n\n" + md_table(["Source path"], [[rel(p)] for p in appendices if p.is_file()]))


def write_manifest(entries: list[ManifestEntry]) -> None:
    fields = ["package_path", "original_path", "experiment_tag", "file_type", "role", "copied_or_referenced", "claim_scope", "notes", "size_bytes", "sha256"]
    rows = [e.__dict__ for e in entries]
    write_text(TARGET / "manifests/manifest.json", json.dumps(rows, indent=2, ensure_ascii=False))
    write_csv(TARGET / "manifests/manifest.csv", rows, fields)
    write_text(TARGET / "manifests/manifest.md", "# Mainline Package Manifest\n\n" + md_table(fields, [[getattr(e, f) for f in fields] for e in entries[:300]]) + ("\n\n_Manifest truncated in Markdown; use JSON/CSV for full list._" if len(entries) > 300 else ""))


def pdf_pages(path: Path) -> str:
    if not path.exists():
        return "missing"
    try:
        proc = subprocess.run(["pdfinfo", str(path)], cwd=ROOT, text=True, capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return "unknown_pdfinfo_unavailable"
    if proc.returncode != 0:
        return "unknown_pdfinfo_failed"
    for line in proc.stdout.splitlines():
        if line.startswith("Pages:"):
            return line.split(":", 1)[1].strip()
    return "unknown_no_pages_field"


def build_status() -> dict[str, Any]:
    ndss = PAPER_ROOT / "ndss_candidate"
    main = ndss / "main.tex"
    text = main.read_text(encoding="utf-8", errors="replace") if main.exists() else ""
    return {
        "main_tex_exists": main.exists(),
        "main_tex_line_count": len(text.splitlines()) if text else 0,
        "included_sections": re.findall(r"\\input\{([^}]+)\}", text),
        "main_pdf_exists": (ndss / "main.pdf").exists(),
        "main_pdf_pages": pdf_pages(ndss / "main.pdf"),
        "pre_e56_backup_exists": (PAPER_ROOT / "ndss_candidate_pre_e56_backup").exists(),
        "draft_polished_exists": (PAPER_ROOT / "draft_polished").exists(),
    }


def missing_paths() -> list[dict[str, str]]:
    out = []
    for item in EXPECTED_PATHS:
        if not (ROOT / item).exists():
            out.append({"path": item, "reason": "expected mainline material not found"})
    return out


def warning_lines(entries: list[ManifestEntry], missing: list[dict[str, str]], status: dict[str, Any]) -> list[str]:
    warnings = ["Packaging only: no experiments, model/API calls, paper rewrites, result edits, or real external side effects; no production-safety claim."]
    if status["main_pdf_pages"] == "2":
        warnings.append("NDSS candidate `main.pdf` is 2 pages; this is a build/material blocker, not a submission-ready paper.")
    if not status["pre_e56_backup_exists"]:
        warnings.append("`ndss_candidate_pre_e56_backup/` is missing.")
    if not status["draft_polished_exists"]:
        warnings.append("`draft_polished/` is missing.")
    for row in missing:
        warnings.append(f"Missing expected material: `{row['path']}`.")

    samples = []
    for entry in entries:
        p = ROOT / entry.package_path
        if entry.copied_or_referenced != "copied" or p.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if re.search(r"/data/CSK|/home/user|sk-[A-Za-z0-9_-]{12,}", text):
            samples.append(entry.package_path)
        if len(samples) >= 20:
            break
    if samples:
        warnings.append("Potential absolute-path or secret-like text patterns require review:\n" + "\n".join(f"- `{s}`" for s in samples))
    return warnings


def write_top_files(entries: list[ManifestEntry], core: list[CoreNumber], missing: list[dict[str, str]], status: dict[str, Any], warnings: list[str]) -> None:
    copied = sum(e.copied_or_referenced == "copied" for e in entries)
    referenced = sum(e.copied_or_referenced == "referenced" for e in entries)
    core_issues = [c for c in core if c.source_type in {"missing", "missing_key"}]

    write_text(TARGET / "README.md", f"""# Mainline Tool-Effect Binding Package

This folder collects the current mainline Tool-Effect Binding / Effect-Binding Guard code, data, results, audits, draft materials, tables, figures, and reproduction notes for later paper writing.

- Copied files: `{copied}`
- Referenced files: `{referenced}`
- Missing expected materials: `{len(missing)}`
- Core-number issues: `{len(core_issues)}`
- Current NDSS PDF pages: `{status['main_pdf_pages']}`

Use this as the main writing-source folder. It is not a new experiment and not a final manuscript.
""")
    write_text(TARGET / "PACKAGE_SUMMARY.md", f"""# Package Summary

## Counts

- Manifest entries: `{len(entries)}`
- Copied files: `{copied}`
- Referenced files: `{referenced}`
- Missing expected materials: `{len(missing)}`
- Core-number issues: `{len(core_issues)}`

## Main Use

Single source folder for writing, checking claims, locating experiments, and preparing a future full NDSS paper draft.
""")
    write_text(TARGET / "MISSING_FILES.md", "# Missing Files\n\n" + (md_table(["Path", "Reason"], [[m["path"], m["reason"]] for m in missing]) if missing else "No expected mainline material is missing.") + "\n\n## Core Number Issues\n\n" + (md_table(["Metric", "Source type", "Source", "Key", "Notes"], [[c.metric, c.source_type, c.source_file, c.key_path, c.notes] for c in core_issues]) if core_issues else "All required core numbers were located in existing artifacts or derived from existing fields."))
    write_text(TARGET / "build_status.md", f"""# Build Status

E58 mainline package did not compile or rewrite the paper; it inspected existing artifacts only.

- `main.tex` exists: `{status['main_tex_exists']}`
- `main.tex` line count: `{status['main_tex_line_count']}`
- Included sections: `{', '.join(status['included_sections']) or 'none detected'}`
- `main.pdf` exists: `{status['main_pdf_exists']}`
- Current `main.pdf` pages: `{status['main_pdf_pages']}`
- `ndss_candidate_pre_e56_backup/` exists: `{status['pre_e56_backup_exists']}`
- `draft_polished/` exists: `{status['draft_polished_exists']}`

Current 2-page PDF must be treated as a compact candidate, not a submission-ready paper.
""")
    write_text(TARGET / "warnings.md", "# Warnings\n\n" + "\n\n".join(f"- {w}" for w in warnings))
    write_text(TARGET / "MAINLINE_CLAIM_BOUNDARY.md", """# Mainline Claim Boundary

## Allowed

- Controlled counterfactual measurement.
- Reference monitor / feasibility probe.
- Local mock pre-commit authorization prototype.
- Explicit authorization infrastructure helps under a controlled contract.
- Resource/auth remains a central bottleneck without that infrastructure.
- E56/E57 reduce leakage, lexical-template, and implementation-coupling concerns.
- E49 is diagnostic appendix material only.

## Disallowed

- Production safety.
- Real SaaS/browser/banking/email validation.
- Complete permission-system correctness.
- Original-paper benchmark reproduction.
- Deployment generalization.
- Safety certificate or universal prompt-injection defense.

## Placement

Repeat this boundary in abstract/introduction, method scope, limitations, and artifact notes.
""")
    write_text(TARGET / "WRITING_NEXT_STEPS.md", """# Writing Next Steps

1. Use this package to rebuild a full NDSS paper draft, not the current 2-page compact candidate.
2. Put E50 resource/auth bottleneck in the main results, not only appendix.
3. Present E55/E56/E57 as controlled local authorization infrastructure evidence.
4. Keep E49 as diagnostic appendix only.
5. Review warnings for absolute local paths/anonymity issues before external release.
6. Use `tables/` as the initial main-table source, then trace every number through `manifests/manifest.csv`.
""")
    write_text(TARGET / "reproduction/README.md", """# Reproduction Notes

No command in this package is run by the builder. Suggested inspection/rerun order:

```bash
python -m src.experiments.effect_binding_guard.run_e48
python -m src.experiments.effect_binding_guard.run_e50 --bootstrap-iters 2000
python -m src.experiments.effect_binding_guard.e55_precommit_authz.run_e55 --strict-label-hidden --output analysis/results/e55_precommit_authz_results_strict.json
python -m src.experiments.effect_binding_guard.e55_precommit_authz.e57_validity_checks
```

E55/E57 are local deterministic mock pre-commit experiments and do not execute real external side effects. E48 local-Qwen prediction regeneration requires local model infrastructure; package building does not.
""")


def validate_package() -> list[str]:
    errors = []
    if not TARGET.exists():
        return [f"Target missing: {rel(TARGET)}"]
    for d in REQUIRED_DIRS:
        if not (TARGET / d).is_dir():
            errors.append(f"Missing dir: {d}")
    for f in REQUIRED_TOP_FILES:
        p = TARGET / f
        if not p.is_file():
            errors.append(f"Missing required file: {f}")
        elif p.stat().st_size == 0:
            errors.append(f"Empty required file: {f}")
    manifest_path = TARGET / "manifests/manifest.json"
    if manifest_path.exists():
        entries = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in entries:
            if not (ROOT / entry["package_path"]).exists():
                errors.append(f"Manifest package path missing: {entry['package_path']}")
            if entry["copied_or_referenced"] == "copied" and not entry["sha256"]:
                errors.append(f"Copied entry missing checksum: {entry['package_path']}")
    core_csv = TARGET / "tables/table2_reference_hard_guard.csv"
    if core_csv.exists():
        text = core_csv.read_text(encoding="utf-8")
        for metric in ["E48 hard guard UPA", "Held-out UPA", "Source-balanced UPA"]:
            if metric not in text:
                errors.append(f"Missing core table metric: {metric}")
    warnings = (TARGET / "warnings.md").read_text(encoding="utf-8", errors="replace") if (TARGET / "warnings.md").exists() else ""
    for phrase in ["no experiments", "real external side effects", "production-safety"]:
        if phrase not in warnings:
            errors.append(f"Warnings missing phrase: {phrase}")
    build = (TARGET / "build_status.md").read_text(encoding="utf-8", errors="replace") if (TARGET / "build_status.md").exists() else ""
    if "2-page" not in build and "pages: `2`" not in build:
        errors.append("Build status does not record 2-page PDF issue.")
    boundary = (TARGET / "MAINLINE_CLAIM_BOUNDARY.md").read_text(encoding="utf-8", errors="replace") if (TARGET / "MAINLINE_CLAIM_BOUNDARY.md").exists() else ""
    for phrase in ["E49", "controlled", "Production safety", "Original-paper benchmark reproduction"]:
        if phrase not in boundary:
            errors.append(f"Claim boundary missing phrase: {phrase}")
    return errors


def build(force: bool, threshold_mb: int) -> dict[str, Any]:
    if TARGET.exists():
        if not force:
            raise SystemExit(f"Refusing to overwrite existing target: {rel(TARGET)}. Use --force.")
        shutil.rmtree(TARGET)
    for d in REQUIRED_DIRS:
        (TARGET / d).mkdir(parents=True, exist_ok=True)

    threshold_bytes = threshold_mb * 1024 * 1024
    entries: list[ManifestEntry] = []
    seen: set[str] = set()
    for candidate in discover_candidates():
        entry = copy_or_reference(candidate, threshold_bytes)
        if entry.package_path in seen:
            continue
        seen.add(entry.package_path)
        entries.append(entry)

    core = collect_core_numbers()
    status = build_status()
    missing = missing_paths()
    warnings = warning_lines(entries, missing, status)

    write_manifest(entries)
    write_core_tables(core)
    write_top_files(entries, core, missing, status, warnings)

    errors = validate_package()
    if errors:
        for error in errors:
            print(f"VALIDATION ERROR: {error}")
        raise SystemExit(1)

    summary = {
        "package_path": rel(TARGET),
        "copied": sum(e.copied_or_referenced == "copied" for e in entries),
        "referenced": sum(e.copied_or_referenced == "referenced" for e in entries),
        "missing_expected": len(missing),
        "core_number_issues": sum(c.source_type in {"missing", "missing_key"} for c in core),
        "ndss_pdf_pages": status["main_pdf_pages"],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="overwrite existing target")
    parser.add_argument("--validate-only", action="store_true", help="validate existing target")
    parser.add_argument("--copy-threshold-mb", type=int, default=100)
    args = parser.parse_args()
    if args.validate_only:
        errors = validate_package()
        if errors:
            for error in errors:
                print(f"VALIDATION ERROR: {error}")
            raise SystemExit(1)
        print(f"Validated {rel(TARGET)}")
        return
    build(args.force, args.copy_threshold_mb)


if __name__ == "__main__":
    main()
