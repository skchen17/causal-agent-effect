#!/usr/bin/env python3
"""Build the E58 consolidated paper-materials package.

This is a packaging-only utility. It copies, references, summarizes, and indexes
existing E47--E57 artifacts for paper writing and verification. It does not
rerun experiments, call APIs/models, modify original result files, or execute
real external side-effectful tools.
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
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
TARGET = PAPER_ROOT / "e58_consolidated_package"

REQUIRED_DIRS = [
    "paper_drafts",
    "data",
    "results",
    "scripts",
    "tests",
    "tables",
    "figures",
    "audit",
    "reproduction",
    "manifests",
    "logs",
]

TOP_LEVEL_FILES = [
    "README.md",
    "PACKAGE_SUMMARY.md",
    "MISSING_FILES.md",
    "build_status.md",
    "warnings.md",
    "manifests/manifest.json",
    "manifests/manifest.csv",
    "manifests/manifest.md",
    "tables/core_result_table.csv",
    "tables/core_result_table.md",
    "tables/e50_resource_auth_bottleneck.csv",
    "tables/e50_resource_auth_bottleneck.md",
    "tables/e55_e56_precommit_prototype.csv",
    "tables/e55_e56_precommit_prototype.md",
    "tables/e55_ablation_table.csv",
    "tables/e55_ablation_table.md",
    "tables/e57_validity_check_table.csv",
    "tables/e57_validity_check_table.md",
    "tables/appendix_slice_tables.md",
    "figures/figure_specs.md",
    "reproduction/README.md",
    "logs/source_discovery.md",
]

TEXT_EXTENSIONS = {
    ".bib",
    ".csv",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".sh",
    ".tex",
    ".txt",
    ".yaml",
    ".yml",
}

PACKAGE_EXTENSIONS = TEXT_EXTENSIONS | {".pdf", ".png", ".jpg", ".jpeg", ".svg"}

SKIP_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "models",
}

SKIP_SUFFIXES = {
    ".aux",
    ".bbl",
    ".blg",
    ".fdb_latexmk",
    ".fls",
    ".log",
    ".out",
    ".synctex.gz",
    ".toc",
    ".xdv",
    ".pyc",
}

EXPECTED_PATHS = [
    "paper_materials/effect_binding_guard_paper/ndss_candidate/main.tex",
    "paper_materials/effect_binding_guard_paper/ndss_candidate/main.pdf",
    "paper_materials/effect_binding_guard_paper/ndss_candidate/references.bib",
    "paper_materials/effect_binding_guard_paper/ndss_candidate/appendix.tex",
    "paper_materials/effect_binding_guard_paper/ndss_candidate/TODO.md",
    "paper_materials/effect_binding_guard_paper/ndss_candidate/ndss_readiness_report.md",
    "paper_materials/effect_binding_guard_paper/ndss_candidate/claim_to_source.md",
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
    "src/experiments/effect_binding_guard/run_e48.py",
    "src/experiments/effect_binding_guard/run_e50.py",
    "src/experiments/effect_binding_guard/e55_precommit_authz/run_e55.py",
    "src/experiments/effect_binding_guard/e55_precommit_authz/e56_audit.py",
    "src/experiments/effect_binding_guard/e55_precommit_authz/e57_validity_checks.py",
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
    note: str = ""


@dataclass
class ManifestEntry:
    package_path: str
    original_path: str
    experiment_tag: str
    file_type: str
    role: str
    action: str
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
    if path.name.endswith(".pyc"):
        return True
    if path.suffix and path.suffix.lower() not in PACKAGE_EXTENSIONS:
        return True
    return False


def source_rel_for_dest(path: Path, section: str) -> Path:
    original = Path(rel(path))
    if section == "paper_drafts" and original.parts[:2] == ("paper_materials", "effect_binding_guard_paper"):
        return Path(*original.parts[2:])
    return original


def infer_tag(path: Path) -> str:
    text = rel(path).lower()
    for tag in ["e57", "e56", "e55", "e50", "e49", "e48", "e47"]:
        if tag in text:
            return tag.upper()
    if "tool_effect_fragmentation" in text:
        return "E47"
    if "ndss" in text or "paper_materials" in text:
        return "paper"
    return "support"


def file_type(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    return suffix or "file"


def add_file(candidates: list[Candidate], path: Path, section: str, role: str, tag: str | None = None, note: str = "") -> None:
    if not path.exists() or not path.is_file() or should_skip(path):
        return
    candidates.append(Candidate(path, section, tag or infer_tag(path), role, note))


def add_tree(candidates: list[Candidate], root: Path, section: str, role: str, tag: str | None = None, note: str = "") -> None:
    if not root.exists():
        return
    if root.is_file():
        add_file(candidates, root, section, role, tag, note)
        return
    for path in sorted(root.rglob("*")):
        add_file(candidates, path, section, role, tag, note)


def add_glob(candidates: list[Candidate], pattern: str, section: str, role: str, tag: str | None = None, note: str = "") -> None:
    for path in sorted(ROOT.glob(pattern)):
        if path.is_dir():
            add_tree(candidates, path, section, role, tag, note)
        else:
            add_file(candidates, path, section, role, tag, note)


def discover_candidates() -> list[Candidate]:
    candidates: list[Candidate] = []

    # Paper materials and drafts.
    for subdir in [
        "ndss_candidate",
        "ndss_candidate_pre_e56_backup",
        "draft",
        "draft_polished",
        "paper_draft",
        "claim_boundary",
        "summaries",
        "tables",
        "figures",
        "appendix",
        "reproduction",
        "failure_examples",
        "e55_precommit_authz",
        "writing_package_e58",
    ]:
        add_tree(candidates, PAPER_ROOT / subdir, "paper_drafts", "paper/material source", tag="paper")
    for file_name in ["README.md", "artifact_inventory.json", "artifact_inventory.md"]:
        add_file(candidates, PAPER_ROOT / file_name, "paper_drafts", "paper package index", tag="paper")

    # E47-E57 data.
    add_tree(candidates, ROOT / "data/tool_effect_fragmentation", "data", "E47 tool-effect fragmentation data", tag="E47")
    for pattern in [
        "data/e48_*",
        "data/e49_*",
        "data/e50_*",
        "data/e55_*",
    ]:
        add_glob(candidates, pattern, "data", "Effect-Binding data/stress set")

    # E47-E57 result artifacts.
    for prefix in [
        "tool_effect_fragmentation*",
        "e48_*",
        "e49_*",
        "e50_*",
        "e55_*",
        "e56_*",
        "e57_*",
    ]:
        add_glob(candidates, f"analysis/results/{prefix}", "results", "experiment result artifact")

    # Scripts and source code.
    for script in [
        "scripts/build_effect_binding_guard_paper_materials.py",
        "scripts/build_effect_binding_writing_package_e58.py",
        "scripts/build_e58_consolidated_package.py",
        "scripts/build_tool_effect_paper_package.py",
        "scripts/run_e47_phase5_full.sh",
        "scripts/status_e47_phase5_full.sh",
    ]:
        add_file(candidates, ROOT / script, "scripts", "builder/reproduction script")
    add_tree(candidates, ROOT / "src/experiments/effect_binding_guard", "scripts", "E48/E50/E55/E56/E57 implementation", tag="E48-E57")
    add_tree(candidates, ROOT / "src/experiments/effect_binding_calibrator", "scripts", "E49 diagnostic implementation", tag="E49")
    add_tree(candidates, ROOT / "src/experiments/tool_effect_fragmentation", "scripts", "E47 implementation", tag="E47")

    # Tests.
    for pattern in [
        "tests/test_effect_binding_guard_e48.py",
        "tests/test_effect_binding_calibrator_e49.py",
        "tests/test_effect_binding_guard_e50.py",
        "tests/test_effect_binding_guard_e55_precommit_authz.py",
        "tests/test_effect_binding_guard_e56_audit.py",
        "tests/test_effect_binding_guard_e57_validity.py",
        "tests/test_tool_effect_fragmentation*.py",
    ]:
        add_glob(candidates, pattern, "tests", "relevant test")

    # Audit-specific copies for easy access.
    for pattern in [
        "analysis/results/e55_*audit*",
        "analysis/results/e55_*strict*",
        "analysis/results/e56_*",
        "analysis/results/e57_*",
        "analysis/results/tool_effect_fragmentation_human_audit_phase6.*",
        "analysis/results/tool_effect_fragmentation_counterfactual_phase4_audit_packet.*",
        "data/tool_effect_fragmentation/human_audit*",
    ]:
        add_glob(candidates, pattern, "audit", "audit/validity artifact")
    for path in [
        PAPER_ROOT / "ndss_candidate/claim_to_source.md",
        PAPER_ROOT / "writing_package_e58/07_claim_to_source_map.md",
        PAPER_ROOT / "writing_package_e58/tables/claim_to_source.csv",
        PAPER_ROOT / "claim_boundary",
    ]:
        add_tree(candidates, path, "audit", "claim/source or boundary material")

    # Reproduction materials.
    add_tree(candidates, PAPER_ROOT / "reproduction", "reproduction", "reproduction note", tag="paper")
    for script in [
        "scripts/build_effect_binding_guard_paper_materials.py",
        "scripts/build_effect_binding_writing_package_e58.py",
        "scripts/build_e58_consolidated_package.py",
    ]:
        add_file(candidates, ROOT / script, "reproduction", "package/reproduction helper")

    return candidates


def copy_or_reference(candidate: Candidate, threshold_bytes: int) -> ManifestEntry:
    src = candidate.source
    size = src.stat().st_size
    digest = sha256(src)
    dest_rel = Path(candidate.section) / source_rel_for_dest(src, candidate.section)
    dest = TARGET / dest_rel
    if size <= threshold_bytes:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        action = "copied"
        package_path = rel(dest)
    else:
        ref_dest = dest.with_suffix(dest.suffix + ".reference.txt")
        ref_dest.parent.mkdir(parents=True, exist_ok=True)
        write_text(
            ref_dest,
            "\n".join(
                [
                    "# Reference-Only Large File",
                    "",
                    f"Original path: `{rel(src)}`",
                    f"Size bytes: `{size}`",
                    f"SHA256: `{digest}`",
                    "",
                    "This file exceeded the package copy threshold and was intentionally referenced rather than copied.",
                ]
            ),
        )
        action = "referenced"
        package_path = rel(ref_dest)
    return ManifestEntry(
        package_path=package_path,
        original_path=rel(src),
        experiment_tag=candidate.experiment_tag,
        file_type=file_type(src),
        role=candidate.role,
        action=action,
        notes=candidate.note,
        size_bytes=size,
        sha256=digest,
    )


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


def add_core_number(
    rows: list[CoreNumber],
    metric: str,
    source_file: str,
    key_path: str,
    claim_scope: str,
    safe_wording: str,
    *,
    fallback: Any | None = None,
    decimals: int = 3,
    notes: str = "",
) -> None:
    data = read_json(source_file)
    source_type = "existing_result_file"
    source_value: Any = None
    if data is None:
        if fallback is None:
            source_type = "missing"
            source_value = ""
            notes = notes or "Source file missing."
        else:
            source_type = "user_summary_fallback"
            source_value = fallback
            source_file = "user-provided E58 plan"
            key_path = ""
            notes = notes or "Fallback from user-provided plan."
    else:
        try:
            source_value = get_path(data, key_path)
        except Exception as exc:  # noqa: BLE001
            if fallback is None:
                source_type = "missing_key"
                source_value = ""
                notes = notes or f"Missing key: {exc}"
            else:
                source_type = "user_summary_fallback"
                source_value = fallback
                source_file = "user-provided E58 plan"
                key_path = ""
                notes = notes or f"Key unavailable in artifact: {exc}"
    rows.append(
        CoreNumber(
            metric=metric,
            display_value=display_value(source_value, decimals) if source_value != "" else "",
            source_value=str(source_value),
            source_file=source_file,
            key_path=key_path,
            source_type=source_type,
            claim_scope=claim_scope,
            safe_wording=safe_wording,
            notes=notes,
        )
    )


def add_derived_domain_count(rows: list[CoreNumber]) -> None:
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
    rows.append(
        CoreNumber(
            metric="E55 domain count",
            display_value=str(value),
            source_value=str(value),
            source_file=source_file,
            key_path="dataset.domain_counts",
            source_type=source_type,
            claim_scope="controlled local contract evidence",
            safe_wording="E55 covers five deterministic local mock domains.",
            notes=notes,
        )
    )


def collect_core_numbers() -> list[CoreNumber]:
    rows: list[CoreNumber] = []
    add = add_core_number
    e48 = "analysis/results/e48_tuple_guard_results.json"
    e50 = "analysis/results/e50_hard_guard_robustness_results.json"
    e55 = "analysis/results/e55_precommit_authz_results_strict.json"
    e55_audit = "analysis/results/e55_decision_path_audit.json"
    e56 = "analysis/results/e56_final_report.json"
    e57 = "analysis/results/e57_validity_checks_report.json"

    add(rows, "E48/E50 full hard guard UPA", e48, "methods.effect_binding_guard_full.overall.unsafe_pre_allow.rate", "E48 hard guard custom stress", "Reference hard guard has low but nonzero unsafe pre-allow.")
    add(rows, "E48/E50 full hard guard FDeny", e48, "methods.effect_binding_guard_full.overall.safe_false_deny.rate", "E48 hard guard custom stress", "Reference hard guard has measurable safe false-denial.")
    add(rows, "E48/E50 full hard guard coverage", e48, "methods.effect_binding_guard_full.overall.coverage.rate", "E48 hard guard custom stress", "Reference hard guard has high coverage on E48.")
    add(rows, "Held-out UPA", e48, "methods.effect_binding_guard_full.by_split.test.unsafe_pre_allow.rate", "held-out split diagnostic", "Held-out split UPA must be reported separately.")
    add(rows, "Held-out FDeny", e48, "methods.effect_binding_guard_full.by_split.test.safe_false_deny.rate", "held-out split diagnostic", "Held-out split safe false-denial is nonzero.")
    add(rows, "Held-out coverage", e48, "methods.effect_binding_guard_full.by_split.test.coverage.rate", "held-out split diagnostic", "Held-out split coverage is high in the custom stress.")
    add(rows, "Source-balanced UPA", e50, "source_balanced.aggregate_fixed_policy.unsafe_pre_allow.mean", "E50 robustness audit", "Source-balanced runs preserve nonzero unsafe pre-allow.")
    add(rows, "Source-balanced FDeny", e50, "source_balanced.aggregate_fixed_policy.safe_false_deny.mean", "E50 robustness audit", "Source-balanced runs preserve nonzero safe false-denial.")
    add(rows, "Source-balanced coverage", e50, "source_balanced.aggregate_fixed_policy.coverage.mean", "E50 robustness audit", "Source-balanced runs preserve high coverage.")
    add(rows, "E50 resource/auth stress UPA", e50, "resource_authorization_stress.methods.effect_binding_guard_full.overall.unsafe_pre_allow.rate", "negative controlled stress", "Resource/authorization binding remains the main bottleneck.")
    add(rows, "E50 resource/auth stress coverage", e50, "resource_authorization_stress.methods.effect_binding_guard_full.overall.coverage.rate", "negative controlled stress", "The resource/auth bottleneck is not just abstention.")
    add(rows, "E50 provenance stress UPA", e50, "control_provenance_stress.methods.effect_binding_guard_full.overall.unsafe_pre_allow.rate", "controlled provenance stress", "Provenance overlay blocks unsafe pre-allow in this controlled stress.")
    add(rows, "E50 provenance stress FDeny", e50, "control_provenance_stress.methods.effect_binding_guard_full.overall.safe_false_deny.rate", "controlled provenance stress", "Provenance overlay introduces safe false-denial.")
    add(rows, "E50 provenance stress coverage", e50, "control_provenance_stress.methods.effect_binding_guard_full.overall.coverage.rate", "controlled provenance stress", "Provenance stress is coverage-limited.")

    add(rows, "E55 dataset rows", e55, "dataset.n_rows", "controlled local contract evidence", "E55 has 600 deterministic local mock rows.", decimals=0)
    add_derived_domain_count(rows)
    add(rows, "E55 existing hard guard UPA", e55, "methods.existing_hard_effect_binding_guard.overall.unsafe_pre_allow.rate", "E55 baseline", "Existing hard guard leaves unsafe pre-allow on E55.")
    add(rows, "E55 existing hard guard FDeny", e55, "methods.existing_hard_effect_binding_guard.overall.safe_false_deny.rate", "E55 baseline", "Existing hard guard avoids false denial but abstains heavily.")
    add(rows, "E55 existing hard guard coverage", e55, "methods.existing_hard_effect_binding_guard.overall.coverage.rate", "E55 baseline", "Existing hard guard has low coverage on E55.")
    add(rows, "E55 existing hard guard abstain", e55, "methods.existing_hard_effect_binding_guard.overall.abstain_rate.rate", "E55 baseline", "Existing hard guard is abstention-heavy.")
    add(rows, "E55 authz-aware UPA", e55, "methods.authz_aware_effect_binding_guard.overall.unsafe_pre_allow.rate", "controlled local contract evidence", "Authz-aware guard eliminates unsafe pre-allow in E55.")
    add(rows, "E55 authz-aware FDeny", e55, "methods.authz_aware_effect_binding_guard.overall.safe_false_deny.rate", "controlled local contract evidence", "Authz-aware guard does not falsely deny safe rows in E55.")
    add(rows, "E55 authz-aware coverage", e55, "methods.authz_aware_effect_binding_guard.overall.coverage.rate", "controlled local contract evidence", "Authz-aware guard increases coverage in E55.")
    add(rows, "E55 authz-aware abstain", e55, "methods.authz_aware_effect_binding_guard.overall.abstain_rate.rate", "controlled local contract evidence", "Authz-aware guard has limited abstention in E55.")
    add(rows, "E55 no multi-resource expansion UPA", e55, "methods.authz_aware_no_multi_resource_expansion.overall.unsafe_pre_allow.rate", "E55 ablation", "Multi-resource atom expansion is necessary in E55.")
    add(rows, "E55 no operation mode UPA", e55, "methods.authz_aware_no_operation_mode.overall.unsafe_pre_allow.rate", "E55 ablation", "Operation-mode binding is necessary in E55.")
    add(rows, "E55 no provenance overlay UPA", e55, "methods.authz_aware_no_provenance_overlay.overall.unsafe_pre_allow.rate", "E55 ablation", "Provenance overlay contributes safety in E55.")
    add(rows, "E55 no alias resolution FDeny", e55, "methods.authz_aware_no_alias_resolution.overall.safe_false_deny.rate", "E55 ablation", "Alias resolution avoids false denial in E55.")
    add(rows, "E55 decision-path audit", e55_audit, "passed", "audit evidence", "Decision-path audit passed.")
    add(rows, "E56 strict label-hidden replay", e56, "strict_mode_passed", "audit evidence", "Strict label-hidden replay passed.")

    add(rows, "E57 perturbation stability", e57, "perturbation_stability_passed", "validity diagnostic", "Perturbation stability passed.")
    add(rows, "E57 UPA delta", e57, "perturbation.authz_aware_upa_delta", "validity diagnostic", "Resource-name perturbation did not change UPA.")
    add(rows, "E57 coverage delta", e57, "perturbation.authz_aware_coverage_delta", "validity diagnostic", "Resource-name perturbation did not change coverage.")
    add(rows, "E57 changed decisions", e57, "perturbation.changed_decision_count", "validity diagnostic", "Resource-name perturbation changed zero decisions.", decimals=0)
    add(rows, "E57 reference decision agreement", e57, "reference_authorizer.decision_agreement", "validity diagnostic", "Reference authorizer agrees on decisions.")
    add(rows, "E57 atom count agreement", e57, "reference_authorizer.atom_count_agreement", "validity diagnostic", "Reference authorizer agrees on atom count.")
    add(rows, "E57 atom resource-set agreement", e57, "reference_authorizer.atom_resource_set_agreement", "validity diagnostic", "Reference authorizer agrees on atom resource sets.")
    add(rows, "E57 spot-audit packet rows", e57, "spot_audit.n_rows", "inspection packet", "E57 produced a 60-row spot-audit packet.", decimals=0)

    return rows


def write_core_number_tables(core: list[CoreNumber]) -> None:
    rows = [c.__dict__ for c in core]
    fields = ["metric", "display_value", "source_value", "source_file", "key_path", "source_type", "claim_scope", "safe_wording", "notes"]
    write_csv(TARGET / "tables/core_result_table.csv", rows, fields)
    write_text(
        TARGET / "tables/core_result_table.md",
        "# Core Result Table\n\n"
        "Every number is traced to a source artifact and key path. Values are displayed rounded for paper use; source values are retained in CSV.\n\n"
        + md_table(["Metric", "Value", "Source", "Key", "Scope", "Safe wording"], [[c.metric, c.display_value, c.source_file, c.key_path, c.claim_scope, c.safe_wording] for c in core]),
    )

    def subset(names: list[str]) -> list[CoreNumber]:
        return [c for c in core if c.metric in names]

    tables = {
        "e50_resource_auth_bottleneck": [
            "E50 resource/auth stress UPA",
            "E50 resource/auth stress coverage",
            "E50 provenance stress UPA",
            "E50 provenance stress FDeny",
            "E50 provenance stress coverage",
        ],
        "e55_e56_precommit_prototype": [
            "E55 dataset rows",
            "E55 domain count",
            "E55 existing hard guard UPA",
            "E55 existing hard guard FDeny",
            "E55 existing hard guard coverage",
            "E55 existing hard guard abstain",
            "E55 authz-aware UPA",
            "E55 authz-aware FDeny",
            "E55 authz-aware coverage",
            "E55 authz-aware abstain",
            "E55 decision-path audit",
            "E56 strict label-hidden replay",
        ],
        "e55_ablation_table": [
            "E55 no multi-resource expansion UPA",
            "E55 no operation mode UPA",
            "E55 no provenance overlay UPA",
            "E55 no alias resolution FDeny",
        ],
        "e57_validity_check_table": [
            "E57 perturbation stability",
            "E57 UPA delta",
            "E57 coverage delta",
            "E57 changed decisions",
            "E57 reference decision agreement",
            "E57 atom count agreement",
            "E57 atom resource-set agreement",
            "E57 spot-audit packet rows",
        ],
    }
    for name, metrics in tables.items():
        part = subset(metrics)
        write_csv(TARGET / f"tables/{name}.csv", [c.__dict__ for c in part], fields)
        title = name.replace("_", " ").title()
        write_text(
            TARGET / f"tables/{name}.md",
            f"# {title}\n\n"
            + md_table(["Metric", "Value", "Claim scope", "Source"], [[c.metric, c.display_value, c.claim_scope, c.source_file] for c in part]),
        )

    slice_source = ROOT / "analysis/results/e55_precommit_authz_slice_table.md"
    if slice_source.exists():
        text = slice_source.read_text(encoding="utf-8", errors="replace")
        write_text(TARGET / "tables/appendix_slice_tables.md", "# Appendix Slice Tables\n\n" + text)
    else:
        write_text(TARGET / "tables/appendix_slice_tables.md", "# Appendix Slice Tables\n\nMissing source: `analysis/results/e55_precommit_authz_slice_table.md`.")


def pdf_page_count(path: Path) -> str:
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


def ndss_build_status() -> dict[str, Any]:
    ndss = PAPER_ROOT / "ndss_candidate"
    main = ndss / "main.tex"
    pdf = ndss / "main.pdf"
    text = main.read_text(encoding="utf-8", errors="replace") if main.exists() else ""
    return {
        "ndss_candidate_exists": ndss.exists(),
        "main_tex_exists": main.exists(),
        "main_tex_line_count": len(text.splitlines()) if text else 0,
        "included_sections": re.findall(r"\\input\{([^}]+)\}", text),
        "main_pdf_exists": pdf.exists(),
        "main_pdf_page_count": pdf_page_count(pdf),
        "references_bib_exists": (ndss / "references.bib").exists(),
        "appendix_exists": (ndss / "appendix.tex").exists(),
        "pre_e56_backup_exists": (PAPER_ROOT / "ndss_candidate_pre_e56_backup").exists(),
        "draft_polished_exists": (PAPER_ROOT / "draft_polished").exists(),
    }


def missing_expected_paths() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in EXPECTED_PATHS:
        p = ROOT / item
        if not p.exists():
            rows.append({"path": item, "reason": "expected file or directory not found"})
    return rows


def write_manifest(entries: list[ManifestEntry]) -> None:
    fields = ["package_path", "original_path", "experiment_tag", "file_type", "role", "action", "notes", "size_bytes", "sha256"]
    rows = [e.__dict__ for e in entries]
    write_text(TARGET / "manifests/manifest.json", json.dumps(rows, indent=2, ensure_ascii=False))
    write_csv(TARGET / "manifests/manifest.csv", rows, fields)
    write_text(
        TARGET / "manifests/manifest.md",
        "# Consolidated Package Manifest\n\n"
        + md_table(fields, [[getattr(e, f) for f in fields] for e in entries[:300]])
        + ("\n\n_Manifest truncated in Markdown; use JSON/CSV for full list._" if len(entries) > 300 else ""),
    )


def scan_warnings(entries: list[ManifestEntry], missing: list[dict[str, str]], build: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    warnings.append("E58 is packaging-only: it does not run experiments, call APIs/models, or execute real external side effects; it does not support production safety claims.")
    if build.get("main_pdf_page_count") == "2":
        warnings.append("NDSS candidate `main.pdf` is 2 pages; treat it as a compact candidate, not a submission-ready paper.")
    if not build.get("pre_e56_backup_exists"):
        warnings.append("`ndss_candidate_pre_e56_backup/` is missing.")
    if not build.get("draft_polished_exists"):
        warnings.append("`draft_polished/` is missing.")
    for row in missing:
        warnings.append(f"Missing expected artifact: `{row['path']}` ({row['reason']}).")

    text_patterns = {
        "absolute_repo_path": re.compile(r"/data/CSK|/home/user"),
        "possible_secret": re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
        "email_or_affiliation": re.compile(r"@[A-Za-z0-9_.-]+\\.[A-Za-z]{2,}"),
    }
    samples: list[str] = []
    for entry in entries:
        package_path = ROOT / entry.package_path
        if entry.action != "copied" or package_path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            text = package_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for label, pattern in text_patterns.items():
            if pattern.search(text):
                samples.append(f"{label}: `{entry.package_path}`")
                break
        if len(samples) >= 20:
            break
    if samples:
        warnings.append("Potential anonymity/path/secret patterns were found in copied text files. Review samples:\n" + "\n".join(f"- {s}" for s in samples))
    return warnings


def write_summary_files(entries: list[ManifestEntry], core: list[CoreNumber], missing: list[dict[str, str]], build: dict[str, Any], warnings: list[str]) -> None:
    copied = sum(1 for e in entries if e.action == "copied")
    referenced = sum(1 for e in entries if e.action == "referenced")
    core_missing = [c for c in core if c.source_type in {"missing", "missing_key"}]
    source_types = sorted({c.source_type for c in core})

    write_text(
        TARGET / "README.md",
        f"""# E58 Consolidated Package

This folder consolidates the Tool-Effect Binding paper materials needed to write, verify, and later prepare a submission.

## What Is Included

- Paper drafts and NDSS candidate sources.
- E47-E57 data and generated stress-test datasets.
- E47-E57 result artifacts.
- E48/E50 hard guard scripts and E55/E56/E57 pre-commit authorization code.
- Relevant tests.
- Paper-ready core tables and figure specifications.
- Audit, reproduction, warning, build-status, and manifest files.

## Current Status

- Files copied: `{copied}`.
- Files referenced: `{referenced}`.
- Missing expected files: `{len(missing)}`.
- Core numbers missing or fallback-only: `{len(core_missing)}`.
- NDSS current PDF page count: `{build.get('main_pdf_page_count')}`.

## Claim Boundary

This package supports writing and verification for a controlled custom-stress measurement paper plus local pre-commit authorization prototype. It does not support production safety, real SaaS/browser/banking/email validation, complete permission-system correctness, or original-paper benchmark reproduction.
""",
    )
    write_text(
        TARGET / "PACKAGE_SUMMARY.md",
        f"""# Package Summary

## Counts

- Copied files: `{copied}`
- Referenced files: `{referenced}`
- Manifest entries: `{len(entries)}`
- Missing expected files/directories: `{len(missing)}`
- Core-number source types: `{', '.join(source_types)}`

## Main Paper-Usable Numbers

See `tables/core_result_table.md` and `tables/core_result_table.csv`.

## Recommended Use

Use this package as the single entry point for drafting and checking the Tool-Effect Binding paper. Use the original paths in `manifests/manifest.csv` to trace every copied/reference file back to the repository source.
""",
    )
    write_text(
        TARGET / "MISSING_FILES.md",
        "# Missing Files\n\n"
        + (
            md_table(["Path", "Reason"], [[m["path"], m["reason"]] for m in missing])
            if missing
            else "No expected file from the E58 checklist is missing."
        )
        + "\n\n## Core Number Source Issues\n\n"
        + (
            md_table(["Metric", "Source type", "Source file", "Key", "Notes"], [[c.metric, c.source_type, c.source_file, c.key_path, c.notes] for c in core_missing])
            if core_missing
            else "All required core numbers were found or derived from existing artifacts."
        ),
    )
    write_text(
        TARGET / "build_status.md",
        f"""# NDSS Build Status

E58 did not compile or rewrite the paper. It inspected existing build artifacts only.

- `ndss_candidate/` exists: `{build.get('ndss_candidate_exists')}`.
- `main.tex` exists: `{build.get('main_tex_exists')}`.
- `main.tex` line count: `{build.get('main_tex_line_count')}`.
- Included sections: `{', '.join(build.get('included_sections') or []) or 'none detected'}`.
- `main.pdf` exists: `{build.get('main_pdf_exists')}`.
- Current `main.pdf` page count: `{build.get('main_pdf_page_count')}`.
- `references.bib` exists: `{build.get('references_bib_exists')}`.
- `appendix.tex` exists: `{build.get('appendix_exists')}`.
- `ndss_candidate_pre_e56_backup/` exists: `{build.get('pre_e56_backup_exists')}`.
- `draft_polished/` exists: `{build.get('draft_polished_exists')}`.

## Interpretation

The current NDSS artifact is a 2-page compact candidate, not a submission-ready paper. The missing pre-E56 backup and polished draft should be treated as material recovery issues, not hidden.
""",
    )
    write_text(
        TARGET / "warnings.md",
        "# Warnings\n\n" + ("\n\n".join(f"- {w}" for w in warnings) if warnings else "No warnings generated by E58 validation."),
    )
    write_text(
        TARGET / "figures/figure_specs.md",
        """# Figure Specifications

E58 does not create new unscripted figures. Use existing figure materials if present, and otherwise use these specifications:

1. Problem setup: tool surface vs realized effect/resource/authorization/provenance.
2. Counterfactual lattice: same-effect surface shift, same-tool effect change, authorization/resource flips.
3. Hard Effect-Binding Guard pipeline: deployable views, tuple binding, evidence fallback, provenance overlay.
4. Resource/auth bottleneck and E55 authorization-aware pre-commit repair.
5. Failure taxonomy: unsafe pre-allow, false deny, abstain, evidence unavailable, provenance/control failure.
""",
    )
    write_text(
        TARGET / "reproduction/README.md",
        """# Reproduction Notes

## Run Order

1. Inspect E47 artifacts and custom-stress results.
2. Reproduce or inspect E48 hard guard results.
3. Reproduce or inspect E50 robustness/resource-auth/provenance stress.
4. Reproduce or inspect E55 strict local pre-commit authorization results.
5. Inspect E56 decision-path audit and strict replay.
6. Inspect E57 perturbation and reference-authorizer agreement.

## Commands

```bash
python -m src.experiments.effect_binding_guard.run_e48
python -m src.experiments.effect_binding_guard.run_e50 --bootstrap-iters 2000
python -m src.experiments.effect_binding_guard.e55_precommit_authz.run_e55 --strict-label-hidden --output analysis/results/e55_precommit_authz_results_strict.json
python -m src.experiments.effect_binding_guard.e55_precommit_authz.e57_validity_checks
```

Treat commands as repository reproduction entry points; check the corresponding experiment README before rerunning.

## Side Effects And Models

E55/E57 are local deterministic mock pre-commit experiments and do not execute real external side effects. E48 local-Qwen tuple predictions require a local model only when regenerating those predictions; E58 itself requires no model or API.
""",
    )
    write_text(
        TARGET / "logs/source_discovery.md",
        "# Source Discovery\n\n"
        + md_table(["Action", "Count"], [["copied", copied], ["referenced", referenced], ["missing expected", len(missing)]])
        + "\n\nSee `manifests/manifest.csv` for file-level provenance.",
    )


def validate_package(core: list[CoreNumber] | None = None) -> list[str]:
    errors: list[str] = []
    if not TARGET.exists():
        return [f"Target package missing: {rel(TARGET)}"]
    for d in REQUIRED_DIRS:
        path = TARGET / d
        if not path.is_dir():
            errors.append(f"Missing directory: {rel(path)}")
    for f in TOP_LEVEL_FILES:
        path = TARGET / f
        if not path.is_file():
            errors.append(f"Missing required file: {rel(path)}")
        elif path.stat().st_size == 0:
            errors.append(f"Empty required file: {rel(path)}")

    manifest_path = TARGET / "manifests/manifest.json"
    if manifest_path.exists():
        rows = json.loads(manifest_path.read_text(encoding="utf-8"))
        for row in rows:
            action = row.get("action")
            package_path = row.get("package_path")
            if action in {"copied", "referenced"} and not (ROOT / package_path).exists():
                errors.append(f"Manifest package path missing: {package_path}")
            if action == "copied" and not row.get("sha256"):
                errors.append(f"Copied file missing checksum: {package_path}")
            if row.get("role", "").lower().find("oracle") >= 0 and row.get("claim_scope", "").lower().find("deployable") >= 0:
                errors.append(f"Oracle/upper-bound row appears deployable: {package_path}")

    core_csv = TARGET / "tables/core_result_table.csv"
    if core_csv.exists():
        with core_csv.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        required = ["E48/E50 full hard guard UPA", "E50 resource/auth stress UPA", "E55 authz-aware UPA", "E57 reference decision agreement"]
        for metric in required:
            matches = [r for r in rows if r.get("metric") == metric]
            if not matches:
                errors.append(f"Missing core number: {metric}")
            elif matches[0].get("source_type") in {"missing", "missing_key"}:
                errors.append(f"Core number missing source: {metric}")

    build_status = (TARGET / "build_status.md").read_text(encoding="utf-8", errors="replace") if (TARGET / "build_status.md").exists() else ""
    if "page count: `2`" not in build_status and "2-page" not in build_status:
        errors.append("Build status does not document the 2-page NDSS PDF issue.")
    if "ndss_candidate_pre_e56_backup" not in build_status:
        errors.append("Build status does not mention missing pre-E56 backup.")

    for path in [TARGET / "README.md", TARGET / "warnings.md", TARGET / "reproduction/README.md"]:
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            if "real external side effect" not in text and "production safety" not in text:
                errors.append(f"Scope/side-effect warning missing from {rel(path)}")
    return errors


def build(force: bool, threshold_mb: int) -> dict[str, Any]:
    if TARGET.exists():
        if not force:
            raise SystemExit(f"Refusing to overwrite existing target: {rel(TARGET)}. Use --force to rebuild.")
        shutil.rmtree(TARGET)
    for d in REQUIRED_DIRS:
        (TARGET / d).mkdir(parents=True, exist_ok=True)

    threshold_bytes = threshold_mb * 1024 * 1024
    candidates = discover_candidates()
    entries: list[ManifestEntry] = []
    seen_dest: set[str] = set()
    for candidate in candidates:
        entry = copy_or_reference(candidate, threshold_bytes)
        if entry.package_path in seen_dest:
            continue
        seen_dest.add(entry.package_path)
        entries.append(entry)

    core = collect_core_numbers()
    missing = missing_expected_paths()
    build_info = ndss_build_status()
    warnings = scan_warnings(entries, missing, build_info)

    write_manifest(entries)
    write_core_number_tables(core)
    write_summary_files(entries, core, missing, build_info, warnings)

    errors = validate_package(core)
    if errors:
        for error in errors:
            print(f"VALIDATION ERROR: {error}")
        raise SystemExit(1)

    copied = sum(1 for e in entries if e.action == "copied")
    referenced = sum(1 for e in entries if e.action == "referenced")
    summary = {
        "package_path": rel(TARGET),
        "copied": copied,
        "referenced": referenced,
        "missing_expected": len(missing),
        "core_number_issues": sum(1 for c in core if c.source_type in {"missing", "missing_key"}),
        "ndss_pdf_pages": build_info.get("main_pdf_page_count"),
        "ndss_build_issue_detected": build_info.get("main_pdf_page_count") == "2",
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="overwrite existing package")
    parser.add_argument("--validate-only", action="store_true", help="validate an existing package")
    parser.add_argument("--copy-threshold-mb", type=int, default=100, help="copy files up to this size; larger files are referenced")
    args = parser.parse_args()

    if args.validate_only:
        errors = validate_package()
        if errors:
            for error in errors:
                print(f"VALIDATION ERROR: {error}")
            raise SystemExit(1)
        print(f"Validated {rel(TARGET)}")
        return
    build(force=args.force, threshold_mb=args.copy_threshold_mb)


if __name__ == "__main__":
    main()
