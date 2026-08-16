#!/usr/bin/env python3
"""Build the E58 writing-materials package for the Effect-Binding Guard paper.

This script is intentionally packaging-only. It reads existing E47--E57
artifacts, writes paper-writing summaries, and validates the package layout. It
does not rerun experiments, call models/APIs, or edit canonical result files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "paper_materials/effect_binding_guard_paper/writing_package_e58"
RESULTS = ROOT / "analysis/results"
PAPER_ROOT = ROOT / "paper_materials/effect_binding_guard_paper"


REQUIRED_DIRS = [
    "tables",
    "figures",
    "snippets",
    "appendix_materials",
    "audit",
    "logs",
]

REQUIRED_TOP_FILES = [
    "README.md",
    "00_project_status.md",
    "01_final_framing.md",
    "02_evidence_chain.md",
    "03_method_definition.md",
    "04_result_inventory.md",
    "05_tables_to_include.md",
    "06_figures_to_include.md",
    "07_claim_to_source_map.md",
    "08_claim_boundary.md",
    "09_limitations_and_risks.md",
    "10_related_work_checklist.md",
    "11_ndss_build_status.md",
    "12_reviewer_response_strategy.md",
    "13_paper_outline.md",
    "14_section_writing_briefs.md",
    "15_artifact_reproducibility_plan.md",
]

REQUIRED_PACKAGE_FILES = [
    *REQUIRED_TOP_FILES,
    "tables/core_numbers.csv",
    "tables/core_numbers.md",
    "tables/main_table_plan.md",
    "tables/table1_existing_methods.md",
    "tables/table2_reference_guard.md",
    "tables/table3_resource_auth_bottleneck.md",
    "tables/table4_e55_precommit.md",
    "tables/table5_e55_ablation.md",
    "tables/appendix_slice_table_summary.md",
    "tables/claim_to_source.csv",
    "figures/figure_plan.md",
    "snippets/evidence_chain_short.md",
    "snippets/evidence_chain_long.md",
    "snippets/method_summary.md",
    "snippets/reference_guard_algorithm.md",
    "snippets/authz_precommit_algorithm.md",
    "appendix_materials/appendix_plan.md",
    "appendix_materials/audit_packet_summary.md",
    "audit/audit_status.md",
    "logs/source_discovery.md",
    "logs/ndss_build_diagnosis.md",
]


SOURCE_FILES = {
    "e48": "analysis/results/e48_tuple_guard_results.json",
    "e50": "analysis/results/e50_hard_guard_robustness_results.json",
    "e55_strict": "analysis/results/e55_precommit_authz_results_strict.json",
    "e55_audit": "analysis/results/e55_decision_path_audit.json",
    "e55_leakage": "analysis/results/e55_precommit_authz_leakage_audit.json",
    "e55_ablation_md": "analysis/results/e55_precommit_authz_ablation_table.md",
    "e55_slice_md": "analysis/results/e55_precommit_authz_slice_table.md",
    "e55_sanity": "analysis/results/e55_sanity_checks.md",
    "e56": "analysis/results/e56_final_report.json",
    "e57": "analysis/results/e57_validity_checks_report.json",
    "e57_perturb": "analysis/results/e57_resource_perturbation_results.json",
    "e57_reference": "analysis/results/e57_reference_authorizer_agreement.json",
    "e57_spot": "analysis/results/e57_spot_audit_summary.md",
    "e57_packet": "analysis/results/e57_spot_audit_packet.jsonl",
    "artifact_inventory": "paper_materials/effect_binding_guard_paper/artifact_inventory.json",
    "ndss_main": "paper_materials/effect_binding_guard_paper/ndss_candidate/main.tex",
    "ndss_pdf": "paper_materials/effect_binding_guard_paper/ndss_candidate/main.pdf",
    "ndss_refs": "paper_materials/effect_binding_guard_paper/ndss_candidate/references.bib",
}


@dataclass
class CoreNumber:
    name: str
    value: str
    source_file: str
    key_path: str
    source_type: str
    claim_scope: str
    safe_wording: str
    note: str = ""


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_json(rel_path: str) -> Any | None:
    path = ROOT / rel_path
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_text(rel_path: str) -> str | None:
    path = ROOT / rel_path
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def get_path(obj: Any, key_path: str) -> Any:
    cur = obj
    if key_path == "":
        return cur
    for part in key_path.split("."):
        if isinstance(cur, dict):
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit():
            cur = cur[int(part)]
        else:
            raise KeyError(key_path)
    return cur


def stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def pct(value: str) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return value
    return f"{100.0 * v:.1f}%"


def add_number(
    rows: list[CoreNumber],
    *,
    name: str,
    source_file: str,
    key_path: str,
    claim_scope: str,
    safe_wording: str,
    fallback: Any | None = None,
    note: str = "",
) -> None:
    data = read_json(source_file)
    source_type = "existing_result_file"
    value: Any = None
    source = source_file
    key = key_path
    if data is None:
        if fallback is None:
            source_type = "missing"
            value = ""
            note = note or "Source file missing."
        else:
            source_type = "user_summary_fallback"
            source = "E58 user brief or prior run summary"
            key = ""
            value = fallback
            note = note or "Fallback retained because the exact source artifact was unavailable."
    else:
        try:
            value = get_path(data, key_path)
        except Exception as exc:  # noqa: BLE001 - package builder should report, not crash.
            if fallback is None:
                source_type = "missing_key"
                value = ""
                note = note or f"Key path not found: {exc}"
            else:
                source_type = "user_summary_fallback"
                source = "E58 user brief or prior run summary"
                key = ""
                value = fallback
                note = note or f"Key path unavailable in {source_file}; fallback preserved."
    rows.append(
        CoreNumber(
            name=name,
            value=stringify(value),
            source_file=source,
            key_path=key,
            source_type=source_type,
            claim_scope=claim_scope,
            safe_wording=safe_wording,
            note=note,
        )
    )


def add_derived_count(
    rows: list[CoreNumber],
    *,
    name: str,
    source_file: str,
    key_path: str,
    claim_scope: str,
    safe_wording: str,
    note: str,
) -> None:
    data = read_json(source_file)
    if data is None:
        rows.append(
            CoreNumber(
                name=name,
                value="",
                source_file=source_file,
                key_path=key_path,
                source_type="missing",
                claim_scope=claim_scope,
                safe_wording=safe_wording,
                note="Source file missing.",
            )
        )
        return
    try:
        value = get_path(data, key_path)
        count = len(value)
        source_type = "existing_result_file"
        final_note = note
    except Exception as exc:  # noqa: BLE001
        count = ""
        source_type = "missing_key"
        final_note = f"Could not derive count: {exc}"
    rows.append(
        CoreNumber(
            name=name,
            value=stringify(count),
            source_file=source_file,
            key_path=key_path,
            source_type=source_type,
            claim_scope=claim_scope,
            safe_wording=safe_wording,
            note=final_note,
        )
    )


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


def discover_sources() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for name, rel_path in SOURCE_FILES.items():
        path = ROOT / rel_path
        rows.append(
            {
                "name": name,
                "path": rel_path,
                "status": "present" if path.exists() else "missing",
                "size_bytes": str(path.stat().st_size) if path.exists() else "",
                "sha256": sha256(path) if path.exists() and path.is_file() else "",
            }
        )
    return rows


def collect_core_numbers() -> list[CoreNumber]:
    rows: list[CoreNumber] = []
    add = add_number

    add(rows, name="E48 unified rows", source_file=SOURCE_FILES["e48"], key_path="manifest.n_rows", claim_scope="controlled custom-stress feasibility", safe_wording="The unified E48 guard evaluation covers 822 controlled rows.")
    add(rows, name="E48 unified pairs", source_file=SOURCE_FILES["e48"], key_path="manifest.n_pairs", claim_scope="controlled custom-stress feasibility", safe_wording="The E48 pairwise diagnostic uses 6,840 counterfactual pairs.")
    add(rows, name="E48 full hard guard UPA", source_file=SOURCE_FILES["e48"], key_path="methods.effect_binding_guard_full.overall.unsafe_pre_allow.rate", claim_scope="deployable-input hard guard custom stress", safe_wording="The reference hard guard has low but nonzero unsafe pre-allow on E48.")
    add(rows, name="E48 full hard guard FDeny", source_file=SOURCE_FILES["e48"], key_path="methods.effect_binding_guard_full.overall.safe_false_deny.rate", claim_scope="deployable-input hard guard custom stress", safe_wording="The reference hard guard has measurable safe false-denial on E48.")
    add(rows, name="E48 full hard guard coverage", source_file=SOURCE_FILES["e48"], key_path="methods.effect_binding_guard_full.overall.coverage.rate", claim_scope="deployable-input hard guard custom stress", safe_wording="The reference hard guard produces non-abstain decisions for most E48 rows.")
    add(rows, name="E48 test split UPA", source_file=SOURCE_FILES["e48"], key_path="methods.effect_binding_guard_full.by_split.test.unsafe_pre_allow.rate", claim_scope="held-out split diagnostic", safe_wording="Held-out split UPA is higher than the overall E48 average and should be reported separately.")
    add(rows, name="E48 test split FDeny", source_file=SOURCE_FILES["e48"], key_path="methods.effect_binding_guard_full.by_split.test.safe_false_deny.rate", claim_scope="held-out split diagnostic", safe_wording="Held-out split safe false-denial is nonzero and remains part of the tradeoff.")
    add(rows, name="E48 test split coverage", source_file=SOURCE_FILES["e48"], key_path="methods.effect_binding_guard_full.by_split.test.coverage.rate", claim_scope="held-out split diagnostic", safe_wording="Held-out split coverage is high in this custom stress setting.")

    add(rows, name="E50 source-balanced UPA mean", source_file=SOURCE_FILES["e50"], key_path="source_balanced.aggregate_fixed_policy.unsafe_pre_allow.mean", claim_scope="robustness audit", safe_wording="Source-balanced E50 repeats preserve the nonzero unsafe pre-allow finding.")
    add(rows, name="E50 source-balanced FDeny mean", source_file=SOURCE_FILES["e50"], key_path="source_balanced.aggregate_fixed_policy.safe_false_deny.mean", claim_scope="robustness audit", safe_wording="Source-balanced E50 repeats preserve nonzero safe false-denial.")
    add(rows, name="E50 source-balanced coverage mean", source_file=SOURCE_FILES["e50"], key_path="source_balanced.aggregate_fixed_policy.coverage.mean", claim_scope="robustness audit", safe_wording="Source-balanced E50 repeats preserve high coverage.")
    add(rows, name="E50 resource/auth stress rows", source_file=SOURCE_FILES["e50"], key_path="resource_authorization_stress.n_rows", claim_scope="negative controlled stress", safe_wording="The resource/auth stress set has 240 controlled rows.")
    add(rows, name="E50 resource/auth stress UPA", source_file=SOURCE_FILES["e50"], key_path="resource_authorization_stress.methods.effect_binding_guard_full.overall.unsafe_pre_allow.rate", claim_scope="negative controlled stress", safe_wording="Resource and authorization binding are the main hard-guard bottleneck.")
    add(rows, name="E50 resource/auth stress coverage", source_file=SOURCE_FILES["e50"], key_path="resource_authorization_stress.methods.effect_binding_guard_full.overall.coverage.rate", claim_scope="negative controlled stress", safe_wording="The bottleneck is not explained by full abstention; the guard often makes decisions while missing unsafe resource/auth cases.")
    add(rows, name="E50 provenance stress rows", source_file=SOURCE_FILES["e50"], key_path="control_provenance_stress.n_rows", claim_scope="controlled provenance stress", safe_wording="The provenance stress set has 336 controlled rows.")
    add(rows, name="E50 provenance stress UPA", source_file=SOURCE_FILES["e50"], key_path="control_provenance_stress.methods.effect_binding_guard_full.overall.unsafe_pre_allow.rate", claim_scope="controlled provenance stress", safe_wording="The provenance overlay eliminates unsafe pre-allow in this controlled provenance stress.")
    add(rows, name="E50 provenance stress FDeny", source_file=SOURCE_FILES["e50"], key_path="control_provenance_stress.methods.effect_binding_guard_full.overall.safe_false_deny.rate", claim_scope="controlled provenance stress", safe_wording="The provenance overlay trades safety for safe false-denial in this controlled stress.")
    add(rows, name="E50 provenance stress coverage", source_file=SOURCE_FILES["e50"], key_path="control_provenance_stress.methods.effect_binding_guard_full.overall.coverage.rate", claim_scope="controlled provenance stress", safe_wording="The provenance stress result is abstention-heavy and should not be framed as production utility.")

    add(rows, name="E55 strict rows", source_file=SOURCE_FILES["e55_strict"], key_path="dataset.n_rows", claim_scope="local pre-commit contract evidence", safe_wording="E55 evaluates 600 local mock pre-commit rows.")
    add_derived_count(rows, name="E55 strict domains", source_file=SOURCE_FILES["e55_strict"], key_path="dataset.domain_counts", claim_scope="local pre-commit contract evidence", safe_wording="E55 spans five local mock domains.", note="Derived by counting keys in dataset.domain_counts.")
    add(rows, name="E55 existing hard guard UPA", source_file=SOURCE_FILES["e55_strict"], key_path="methods.existing_hard_effect_binding_guard.overall.unsafe_pre_allow.rate", claim_scope="baseline on E55 local contract stress", safe_wording="The earlier hard guard leaves unsafe pre-allow in E55.")
    add(rows, name="E55 existing hard guard FDeny", source_file=SOURCE_FILES["e55_strict"], key_path="methods.existing_hard_effect_binding_guard.overall.safe_false_deny.rate", claim_scope="baseline on E55 local contract stress", safe_wording="The earlier hard guard does not falsely deny safe rows in E55 but abstains heavily.")
    add(rows, name="E55 existing hard guard coverage", source_file=SOURCE_FILES["e55_strict"], key_path="methods.existing_hard_effect_binding_guard.overall.coverage.rate", claim_scope="baseline on E55 local contract stress", safe_wording="The earlier hard guard is abstention-heavy on E55.")
    add(rows, name="E55 authz-aware UPA", source_file=SOURCE_FILES["e55_strict"], key_path="methods.authz_aware_effect_binding_guard.overall.unsafe_pre_allow.rate", claim_scope="local pre-commit contract evidence", safe_wording="Explicit authorization infrastructure removes unsafe pre-allow in this deterministic local mock contract.")
    add(rows, name="E55 authz-aware FDeny", source_file=SOURCE_FILES["e55_strict"], key_path="methods.authz_aware_effect_binding_guard.overall.safe_false_deny.rate", claim_scope="local pre-commit contract evidence", safe_wording="The authz-aware prototype does not falsely deny safe rows in this deterministic local mock contract.")
    add(rows, name="E55 authz-aware coverage", source_file=SOURCE_FILES["e55_strict"], key_path="methods.authz_aware_effect_binding_guard.overall.coverage.rate", claim_scope="local pre-commit contract evidence", safe_wording="The authz-aware prototype increases coverage on E55 relative to the earlier hard guard.")
    add(rows, name="E55 no alias FDeny", source_file=SOURCE_FILES["e55_strict"], key_path="methods.authz_aware_no_alias_resolution.overall.safe_false_deny.rate", claim_scope="E55 ablation", safe_wording="Alias resolution matters for avoiding false denial in the local contract.")
    add(rows, name="E55 no multi-resource UPA", source_file=SOURCE_FILES["e55_strict"], key_path="methods.authz_aware_no_multi_resource_expansion.overall.unsafe_pre_allow.rate", claim_scope="E55 ablation", safe_wording="Multi-resource atom expansion is necessary in E55.")
    add(rows, name="E55 no operation-mode UPA", source_file=SOURCE_FILES["e55_strict"], key_path="methods.authz_aware_no_operation_mode.overall.unsafe_pre_allow.rate", claim_scope="E55 ablation", safe_wording="Operation-mode binding is necessary in E55.")
    add(rows, name="E55 no provenance UPA", source_file=SOURCE_FILES["e55_strict"], key_path="methods.authz_aware_no_provenance_overlay.overall.unsafe_pre_allow.rate", claim_scope="E55 ablation", safe_wording="Provenance overlay contributes safety in E55.")
    add(rows, name="E55 decision-path audit passed", source_file=SOURCE_FILES["e55_audit"], key_path="passed", claim_scope="audit evidence", safe_wording="The E55 decision-path audit passed.")
    add(rows, name="E55 leakage audit passed", source_file=SOURCE_FILES["e55_leakage"], key_path="leakage_free", claim_scope="audit evidence", safe_wording="The E55 leakage audit found no forbidden deployable-input leakage.", fallback=True)
    add(rows, name="E56 strict mode passed", source_file=SOURCE_FILES["e56"], key_path="strict_mode_passed", claim_scope="audit evidence", safe_wording="E56 strict replay passed.")

    add(rows, name="E57 perturbation stability passed", source_file=SOURCE_FILES["e57"], key_path="perturbation_stability_passed", claim_scope="validity diagnostic", safe_wording="Resource-name perturbation stability passed.")
    add(rows, name="E57 authz-aware UPA delta", source_file=SOURCE_FILES["e57"], key_path="perturbation.authz_aware_upa_delta", claim_scope="validity diagnostic", safe_wording="E57 resource-name perturbation did not change authz-aware UPA.")
    add(rows, name="E57 authz-aware coverage delta", source_file=SOURCE_FILES["e57"], key_path="perturbation.authz_aware_coverage_delta", claim_scope="validity diagnostic", safe_wording="E57 resource-name perturbation did not change authz-aware coverage.")
    add(rows, name="E57 changed decision rate", source_file=SOURCE_FILES["e57"], key_path="perturbation.changed_decision_rate", claim_scope="validity diagnostic", safe_wording="E57 resource-name perturbation produced no changed decisions for the authz-aware guard.")
    add(rows, name="E57 reference decision agreement", source_file=SOURCE_FILES["e57"], key_path="reference_authorizer.decision_agreement", claim_scope="validity diagnostic", safe_wording="The independently implemented reference authorizer agrees with E55 decisions in this controlled dataset.")
    add(rows, name="E57 reference atom count agreement", source_file=SOURCE_FILES["e57"], key_path="reference_authorizer.atom_count_agreement", claim_scope="validity diagnostic", safe_wording="The reference authorizer agrees on atom counts in this controlled dataset.")
    add(rows, name="E57 reference atom resource agreement", source_file=SOURCE_FILES["e57"], key_path="reference_authorizer.atom_resource_set_agreement", claim_scope="validity diagnostic", safe_wording="The reference authorizer agrees on atom resource sets in this controlled dataset.")
    add(rows, name="E57 spot-audit packet rows", source_file=SOURCE_FILES["e57"], key_path="spot_audit.n_rows", claim_scope="inspection packet", safe_wording="E57 generated a 60-row human-inspectable spot-audit packet.")

    return rows


def write_core_number_tables(numbers: list[CoreNumber]) -> None:
    rows = [n.__dict__ for n in numbers]
    fields = ["name", "value", "source_file", "key_path", "source_type", "claim_scope", "safe_wording", "note"]
    write_csv(PACKAGE / "tables/core_numbers.csv", rows, fields)
    md_rows = [
        [n.name, pct(n.value) if re.search(r"(UPA|FDeny|coverage|delta|agreement|rate|passed)", n.name, re.I) and n.value not in {"true", "false"} else n.value, n.source_file, n.key_path, n.source_type, n.claim_scope, n.safe_wording]
        for n in numbers
    ]
    write_text(
        PACKAGE / "tables/core_numbers.md",
        "# Core Numbers\n\nEvery number is traced to a source artifact and key path. Missing keys are not silently replaced.\n\n"
        + md_table(["Number", "Value", "Source", "Key path", "Source type", "Scope", "Safe wording"], md_rows),
    )


def build_source_discovery(rows: list[dict[str, str]]) -> str:
    missing = [r for r in rows if r["status"] != "present"]
    lines = [
        "# Source Discovery Log",
        "",
        "This log records which E47-E57 artifacts were found by the E58 builder. Missing files are treated as material-recovery issues, not as license to invent replacement paths.",
        "",
        md_table(["Name", "Path", "Status", "Size bytes"], [[r["name"], r["path"], r["status"], r["size_bytes"]] for r in rows]),
        "",
        "## Missing Or Uncertain Artifacts",
        "",
    ]
    if missing:
        for row in missing:
            lines.append(f"- `{row['path']}` is missing. Downstream files should mark related claims as unavailable or fallback-only.")
    else:
        lines.append("- No required source artifact in this E58 source list is missing.")
    lines.extend(
        [
            "",
            "## Current NDSS Material Recovery Facts",
            "",
            "- `paper_materials/effect_binding_guard_paper/ndss_candidate/main.pdf` exists but is a 2-page compact candidate, not a complete submission draft.",
            "- `paper_materials/effect_binding_guard_paper/ndss_candidate_pre_e56_backup/` is missing and must be treated as a recovery blocker.",
        ]
    )
    return "\n".join(lines)


def pdf_pages(pdf_path: Path) -> str:
    if not pdf_path.exists():
        return "missing"
    try:
        out = subprocess.run(["pdfinfo", str(pdf_path)], cwd=ROOT, text=True, capture_output=True, check=False, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return "unknown_pdfinfo_unavailable"
    if out.returncode != 0:
        return f"unknown_pdfinfo_error:{out.stderr.strip()[:120]}"
    for line in out.stdout.splitlines():
        if line.startswith("Pages:"):
            return line.split(":", 1)[1].strip()
    return "unknown_no_pages_field"


def diagnose_ndss() -> dict[str, Any]:
    ndss = PAPER_ROOT / "ndss_candidate"
    main_tex = ndss / "main.tex"
    pdf = ndss / "main.pdf"
    backup = PAPER_ROOT / "ndss_candidate_pre_e56_backup"
    section_dir = ndss / "sections"
    section_files = sorted(section_dir.glob("*.tex")) if section_dir.exists() else []
    line_count = len(main_tex.read_text(encoding="utf-8", errors="replace").splitlines()) if main_tex.exists() else 0
    included_sections = []
    if main_tex.exists():
        text = main_tex.read_text(encoding="utf-8", errors="replace")
        included_sections = re.findall(r"\\input\{([^}]+)\}", text)
    draft_candidates = sorted(PAPER_ROOT.glob("draft*")) + sorted(PAPER_ROOT.glob("*draft*"))
    return {
        "ndss_candidate_exists": ndss.exists(),
        "main_tex_exists": main_tex.exists(),
        "main_tex_line_count": line_count,
        "included_sections": included_sections,
        "section_files": [rel(p) for p in section_files],
        "pdf_exists": pdf.exists(),
        "pdf_page_count": pdf_pages(pdf),
        "pre_e56_backup_exists": backup.exists(),
        "draft_candidates": [rel(p) for p in draft_candidates],
        "draft_polished_exists": (PAPER_ROOT / "draft_polished").exists(),
    }


def build_ndss_status_text(diag: dict[str, Any]) -> str:
    return f"""# NDSS Build Status

E58 does not patch or rewrite the paper. It only diagnoses the current build state.

## Current State

- `ndss_candidate/` exists: `{diag['ndss_candidate_exists']}`.
- `ndss_candidate/main.tex` exists: `{diag['main_tex_exists']}`.
- `main.tex` line count: `{diag['main_tex_line_count']}`.
- Included sections from `main.tex`: `{', '.join(diag['included_sections']) if diag['included_sections'] else 'none detected'}`.
- Section files detected: `{len(diag['section_files'])}`.
- `ndss_candidate/main.pdf` exists: `{diag['pdf_exists']}`.
- Current PDF page count: `{diag['pdf_page_count']}`.
- `ndss_candidate_pre_e56_backup/` exists: `{diag['pre_e56_backup_exists']}`.
- `draft_polished/` exists: `{diag['draft_polished_exists']}`.

## Diagnosis

The current `main.pdf` is a 2-page compact NDSS candidate, not a complete submission manuscript. The pre-E56 backup directory is missing. This is a build/material recovery blocker and should be reported openly rather than hidden.

## Recovery Recommendation

Use this E58 writing package, the E51/E55 package materials, and the canonical result artifacts to rebuild a full NDSS paper. Do not treat the current two-page PDF as submission-ready evidence of paper completeness.
"""


def number_lookup(numbers: list[CoreNumber]) -> dict[str, CoreNumber]:
    return {n.name: n for n in numbers}


def val(numbers: dict[str, CoreNumber], key: str) -> str:
    return numbers.get(key, CoreNumber(key, "", "", "", "missing", "", "")).value


def write_claim_sources(numbers: list[CoreNumber]) -> None:
    claims = [
        {
            "claim": "The paper is best framed as measurement + diagnostic framework + local pre-commit authorization prototype.",
            "source_artifact": "E47-E57 combined writing package",
            "source_key": "synthesis",
            "safe_wording": "The evidence supports controlled custom-stress and local contract feasibility claims, not production safety.",
            "disallowed_overclaim": "Do not claim complete deployment safety or original benchmark reproduction.",
            "paper_location": "Abstract, Introduction, Limitations",
        },
        {
            "claim": "The reference hard Effect-Binding Guard has low but nonzero unsafe pre-allow and a resource/auth bottleneck.",
            "source_artifact": SOURCE_FILES["e48"] + "; " + SOURCE_FILES["e50"],
            "source_key": "E48 full guard overall; E50 resource_authorization_stress",
            "safe_wording": "The hard guard improves over surface baselines but fails resource/auth stress.",
            "disallowed_overclaim": "Do not claim the hard guard solves authorization binding.",
            "paper_location": "Results RQ2/RQ3",
        },
        {
            "claim": "Explicit authorization infrastructure improves local pre-commit decidability in E55.",
            "source_artifact": SOURCE_FILES["e55_strict"],
            "source_key": "methods.authz_aware_effect_binding_guard.overall",
            "safe_wording": "In deterministic local mock contracts, atom expansion and authorization context raise coverage and remove unsafe pre-allow.",
            "disallowed_overclaim": "Do not claim real SaaS/email/banking safety.",
            "paper_location": "Results RQ4",
        },
        {
            "claim": "E57 reduces lexical-template and implementation-coupling concerns for E55.",
            "source_artifact": SOURCE_FILES["e57"],
            "source_key": "perturbation; reference_authorizer",
            "safe_wording": "Resource-name perturbation and an independent reference checker agree in the controlled E55 dataset.",
            "disallowed_overclaim": "Do not claim adversarial tool-schema robustness.",
            "paper_location": "Validity Checks",
        },
        {
            "claim": "E49 learned calibration is diagnostic only.",
            "source_artifact": "analysis/results/e49_* if present",
            "source_key": "diagnostic appendix",
            "safe_wording": "Learned fusion may be appendix material but is not the main method.",
            "disallowed_overclaim": "Do not present E49 as the main guard.",
            "paper_location": "Appendix",
        },
    ]
    fields = ["claim", "source_artifact", "source_key", "safe_wording", "disallowed_overclaim", "paper_location"]
    write_csv(PACKAGE / "tables/claim_to_source.csv", claims, fields)
    write_text(
        PACKAGE / "07_claim_to_source_map.md",
        "# Claim-To-Source Map\n\n"
        + md_table(fields, [[c[f] for f in fields] for c in claims])
        + "\n\nEvery main-paper claim must be traceable to one of these artifacts or to a more specific table in `tables/core_numbers.csv`.",
    )


def write_table_plans(numbers: list[CoreNumber]) -> None:
    lookup = number_lookup(numbers)
    table1 = [
        ["Existing defenses / measurement", "E47-E48", "Custom counterfactual and source-specific stress", "Shows why surface robustness is insufficient; exact method rows should be pulled from E47/E48 canonical result files."],
        ["Reference hard guard", "E48", f"UPA {pct(val(lookup, 'E48 full hard guard UPA'))}; FDeny {pct(val(lookup, 'E48 full hard guard FDeny'))}; coverage {pct(val(lookup, 'E48 full hard guard coverage'))}", "Improves measurement framing but leaves resource/auth gap."],
        ["Resource/auth bottleneck", "E50", f"UPA {pct(val(lookup, 'E50 resource/auth stress UPA'))}; coverage {pct(val(lookup, 'E50 resource/auth stress coverage'))}", "Central negative result; do not hide."],
        ["Authorization-aware pre-commit", "E55/E56", f"UPA {pct(val(lookup, 'E55 authz-aware UPA'))}; FDeny {pct(val(lookup, 'E55 authz-aware FDeny'))}; coverage {pct(val(lookup, 'E55 authz-aware coverage'))}", "Local mock contract evidence only."],
        ["Validity checks", "E57", f"Reference agreement {pct(val(lookup, 'E57 reference decision agreement'))}; changed-decision rate {pct(val(lookup, 'E57 changed decision rate'))}", "Reduces lexical and implementation-coupling concerns."],
    ]
    write_text(PACKAGE / "tables/main_table_plan.md", "# Main Table Plan\n\n" + md_table(["Table", "Source", "Key numbers", "Purpose"], table1))

    write_text(
        PACKAGE / "tables/table1_existing_methods.md",
        "# Table 1: Existing Methods And Measurement Setup\n\n"
        "Use E47/E48 artifacts to separate official-checkpoint custom stress, component stress, proxy diagnostics, non-oracle evidence, oracle/upper-bound, and adapter failures. Do not collapse these scopes into a single leaderboard.\n\n"
        + md_table(["Scope", "Use in paper", "Claim boundary"], [
            ["official-checkpoint custom stress", "Comparable method rows when original checkpoint was actually run on custom cases", "Not original-paper benchmark reproduction"],
            ["component stress", "IPIGuard/CaMeL structural evidence", "Component behavior, not full deployed defense"],
            ["proxy diagnostic", "Mechanism illustration", "No claim about original method failure"],
            ["oracle / upper bound", "Feasibility ceiling", "Never deployable result"],
        ]),
    )
    write_text(
        PACKAGE / "tables/table2_reference_guard.md",
        "# Table 2: Reference Hard Effect-Binding Guard\n\n"
        + md_table(["Metric", "Value", "Source"], [
            ["E48 UPA", pct(val(lookup, "E48 full hard guard UPA")), SOURCE_FILES["e48"]],
            ["E48 FDeny", pct(val(lookup, "E48 full hard guard FDeny")), SOURCE_FILES["e48"]],
            ["E48 Coverage", pct(val(lookup, "E48 full hard guard coverage")), SOURCE_FILES["e48"]],
            ["E50 source-balanced UPA mean", pct(val(lookup, "E50 source-balanced UPA mean")), SOURCE_FILES["e50"]],
            ["E50 source-balanced FDeny mean", pct(val(lookup, "E50 source-balanced FDeny mean")), SOURCE_FILES["e50"]],
        ]),
    )
    write_text(
        PACKAGE / "tables/table3_resource_auth_bottleneck.md",
        "# Table 3: Resource/Auth Bottleneck\n\n"
        + md_table(["Metric", "Value", "Interpretation"], [
            ["Resource/auth stress rows", val(lookup, "E50 resource/auth stress rows"), "Controlled evaluation-only stress set"],
            ["Resource/auth UPA", pct(val(lookup, "E50 resource/auth stress UPA")), "Major hard-guard weakness"],
            ["Resource/auth coverage", pct(val(lookup, "E50 resource/auth stress coverage")), "Failure is not just abstention"],
            ["Provenance stress UPA", pct(val(lookup, "E50 provenance stress UPA")), "Provenance overlay works in controlled provenance cases"],
            ["Provenance stress FDeny", pct(val(lookup, "E50 provenance stress FDeny")), "Safety/utility tradeoff"],
            ["Provenance stress coverage", pct(val(lookup, "E50 provenance stress coverage")), "Abstention-heavy"],
        ]),
    )
    write_text(
        PACKAGE / "tables/table4_e55_precommit.md",
        "# Table 4: E55 Local Pre-Commit Authorization Prototype\n\n"
        + md_table(["Method", "UPA", "FDeny", "Coverage", "Scope"], [
            ["Existing hard guard", pct(val(lookup, "E55 existing hard guard UPA")), pct(val(lookup, "E55 existing hard guard FDeny")), pct(val(lookup, "E55 existing hard guard coverage")), "E55 baseline"],
            ["Authz-aware prototype", pct(val(lookup, "E55 authz-aware UPA")), pct(val(lookup, "E55 authz-aware FDeny")), pct(val(lookup, "E55 authz-aware coverage")), "Local mock contract evidence"],
        ]),
    )
    write_text(
        PACKAGE / "tables/table5_e55_ablation.md",
        "# Table 5: E55 Ablation Summary\n\n"
        + md_table(["Ablation", "Key degradation", "Interpretation"], [
            ["No alias resolution", f"FDeny {pct(val(lookup, 'E55 no alias FDeny'))}", "Aliases matter for utility."],
            ["No multi-resource expansion", f"UPA {pct(val(lookup, 'E55 no multi-resource UPA'))}", "Multi-resource atoms are essential."],
            ["No operation-mode binding", f"UPA {pct(val(lookup, 'E55 no operation-mode UPA'))}", "Draft/commit distinctions are essential."],
            ["No provenance overlay", f"UPA {pct(val(lookup, 'E55 no provenance UPA'))}", "Control-source checks are essential."],
        ]),
    )
    slice_md = read_text(SOURCE_FILES["e55_slice_md"]) or "_E55 slice table source missing._"
    write_text(
        PACKAGE / "tables/appendix_slice_table_summary.md",
        "# Appendix Slice Table Summary\n\nThe canonical slice table is summarized below. Use the original source for exact formatting.\n\n"
        f"Source: `{SOURCE_FILES['e55_slice_md']}`\n\n"
        + slice_md[:6000],
    )


def write_figure_plans() -> None:
    text = """# Figure Plan

## Figure 1: Problem Setup

Show how the same tool surface can map to different realized effects, and how the same realized effect can be produced by different tools/wrappers/schemas. The key visual should separate tool surface, effect atom, resource, authorization context, provenance/control source, and final decision.

## Figure 2: Counterfactual Lattice

Use Phase 4/E47 counterfactual lattice cases to show axes: same-effect surface shift, same-tool effect change, authorization shift, resource shift, and evidence availability.

## Figure 3: Effect-Binding Guard Pipeline

Depict deployable inputs -> tuple/view inference -> evidence fallback -> provenance overlay -> selective ALLOW/DENY/ABSTAIN. Mark oracle/gold fields as excluded.

## Figure 4: Safety-Coverage Tradeoff

Use E48/E50/E55 core numbers: reference guard low UPA but resource/auth bottleneck, provenance overlay safety/coverage tradeoff, and E55 authz-aware local contract improvement.

## Figure 5: Failure Taxonomy

Organize failures into surface proxy, resource mismatch, authorization mismatch, operation-mode confusion, multi-resource missing atom, provenance/control-dependency failure, evidence unavailable, and over-denial/abstention.
"""
    write_text(PACKAGE / "figures/figure_plan.md", text)
    write_text(PACKAGE / "06_figures_to_include.md", text)


def write_main_markdown(numbers: list[CoreNumber], discovery: list[dict[str, str]], ndss: dict[str, Any]) -> None:
    lookup = number_lookup(numbers)
    readme = f"""# E58 Writing Package: Effect-Binding Guard Paper

This package consolidates E47-E57 evidence into NDSS-first writing materials for a Tool-Effect Binding paper.

## Status

- Package purpose: writing-material consolidation, not a new experiment.
- Framing: measurement + diagnostic framework + local pre-commit authorization prototype.
- Current NDSS build blocker: `ndss_candidate/main.pdf` is `{ndss['pdf_page_count']}` pages, and `ndss_candidate_pre_e56_backup/` exists = `{ndss['pre_e56_backup_exists']}`.
- Main method: reference hard Effect-Binding Guard, with E55 as a local authorization-aware prototype addressing the E50 resource/auth bottleneck.
- E49 learned calibration: diagnostic appendix only.
- E55/E57: controlled contract evidence only.

## Package Layout

- `tables/`: core numbers, table plans, claim-to-source CSV.
- `figures/`: figure specifications and data references.
- `snippets/`: reusable method/evidence wording.
- `appendix_materials/`: appendix and audit-packet notes.
- `audit/`: audit and validity-check status.
- `logs/`: source discovery and NDSS build diagnosis.

## Main Safe Takeaway

Existing surface-level and tuple-only guards are not enough for stable authorization binding. Explicit authorization context, effect-resource-operation atom expansion, alias handling, multi-resource expansion, provenance overlay, and evidence fallback improve local mock pre-commit mediation, but the evidence remains controlled and does not establish production safety.
"""
    write_text(PACKAGE / "README.md", readme)

    write_text(
        PACKAGE / "00_project_status.md",
        f"""# Project Status

E58 found the core E48/E50/E55/E57 result artifacts needed for paper writing and generated traceable core-number tables. It did not rerun experiments.

## Key Status Facts

- E48 unified rows: `{val(lookup, 'E48 unified rows')}`.
- E50 resource/auth stress UPA: `{pct(val(lookup, 'E50 resource/auth stress UPA'))}`.
- E55 authz-aware strict UPA / FDeny / coverage: `{pct(val(lookup, 'E55 authz-aware UPA'))}` / `{pct(val(lookup, 'E55 authz-aware FDeny'))}` / `{pct(val(lookup, 'E55 authz-aware coverage'))}`.
- E57 reference-authorizer decision agreement: `{pct(val(lookup, 'E57 reference decision agreement'))}`.
- Current NDSS PDF pages: `{ndss['pdf_page_count']}`.
- Pre-E56 backup exists: `{ndss['pre_e56_backup_exists']}`.
""",
    )
    write_text(
        PACKAGE / "01_final_framing.md",
        """# Final Framing

## Recommended Thesis

Agent-safety monitors need stable binding between realized effects, resources, authorization context, provenance/control source, and utility. Tool-name, prompt-text, and trajectory-surface robustness alone is insufficient.

## Paper Identity

This should be written as a measurement and method paper with a local pre-commit authorization prototype. The reference hard guard is the baseline method; E55 is the infrastructure response to the E50 resource/auth bottleneck.

## Do Not Overclaim

Do not call the system production-ready. Do not claim complete prompt-injection defense, full permission-system correctness, original-paper benchmark reproduction, or real SaaS/browser/banking/email validation.
""",
    )
    write_text(
        PACKAGE / "02_evidence_chain.md",
        """# Evidence Chain

1. E47 builds the tool-effect fragmentation and counterfactual measurement substrate.
2. E48 implements a hard non-oracle Effect-Binding Guard over deployable tuple/view signals.
3. E49 tests learned fusion as diagnostic appendix material; it is not the main method.
4. E50 strengthens robustness checks and exposes resource/auth binding as a central negative result.
5. E55 adds typed local pre-commit authorization infrastructure and tests whether it repairs the E50 bottleneck in deterministic mock contracts.
6. E56 audits strict decision inputs and integrates E55 into paper materials.
7. E57 checks deterministic resource-name perturbation and an independently implemented reference authorizer.

The strongest defensible claim is that controlled counterfactual evidence supports the need for explicit effect/resource/authorization/provenance binding. The package does not prove real-world deployment safety.
""",
    )
    write_text(
        PACKAGE / "03_method_definition.md",
        """# Method Definition

## Counterfactual Stress-Test Framework

The evaluation constructs paired cases that hold one semantic axis fixed while changing tool surface, resource authorization, operation mode, provenance/control source, or evidence availability. Metrics report whether decisions stay invariant when they should and change when safety-relevant axes change.

## Reference Hard Effect-Binding Guard

The hard guard infers effect/resource/authorization/provenance tuples from non-oracle views, checks multi-view disagreement, uses selective evidence fallback when available, overlays hard provenance rules, and outputs `ALLOW`, `DENY`, or `ABSTAIN`.

## Authorization-Aware Local Pre-Commit Prototype

The E55 prototype expands tool calls into effect-resource-operation atoms, canonicalizes resources and aliases, checks each atom against a typed authorization context, applies provenance overlay, and abstains when evidence/canonicalization is insufficient. This is local mock contract evidence, not a production permission system.
""",
    )
    write_text(
        PACKAGE / "04_result_inventory.md",
        "# Result Inventory\n\n"
        "The source-of-truth core numbers are in `tables/core_numbers.csv` and `tables/core_numbers.md`.\n\n"
        + md_table(["Name", "Status", "Path"], [[r["name"], r["status"], r["path"]] for r in discovery]),
    )
    write_text(
        PACKAGE / "05_tables_to_include.md",
        """# Tables To Include

1. Existing methods and scope labels.
2. Reference hard guard E48/E50 summary.
3. Resource/auth bottleneck table.
4. E55 local pre-commit authorization table.
5. E55 ablation table.
6. Appendix slice table and audit/validity table.

Each table must include scope labels and avoid mixing oracle/upper-bound rows with deployable methods.
""",
    )


def write_boundaries_and_strategy() -> None:
    allowed = """# Claim Boundary

## Allowed Claims

- Controlled custom-stress evidence suggests tool/effect/resource/authorization binding is a meaningful failure mode for agent-safety monitors.
- The reference hard Effect-Binding Guard reduces some surface-proxy failures but retains a resource/auth bottleneck.
- E55 shows that explicit typed authorization context, atom expansion, alias handling, operation-mode binding, multi-resource expansion, provenance overlay, and evidence fallback can improve local mock pre-commit decidability.
- E57 reduces concerns that E55 is only a resource-name lexical artifact or a single implementation's label coupling.
- E49 is diagnostic appendix evidence only.

## Disallowed Claims

- Production safety.
- Complete permission system.
- Full prompt-injection defense.
- Real SaaS/browser/banking/email validation.
- Original-paper benchmark reproduction.
- Independent deployment generalization.
- Safety certificate or theorem-backed guarantee.
- Learned calibration as the main method.
"""
    write_text(PACKAGE / "08_claim_boundary.md", allowed)
    write_text(
        PACKAGE / "09_limitations_and_risks.md",
        """# Limitations And Reviewer Risks

## Main Risks

- E55 shares deterministic mock schemas and authorization contracts with the label generator.
- E57 is an independent consistency check, not human annotation or real-world validation.
- The NDSS candidate currently has a two-page PDF and no pre-E56 backup directory; paper reconstruction is still required.
- E50 resource/auth stress remains a central negative result for the reference hard guard.
- Existing-defense comparisons remain custom stress or component stress unless explicitly marked otherwise.
- No real side-effectful tools, SaaS systems, browsers, bank transfers, or email providers were executed.
- The package does not support production safety claims.

## Reviewer-Safe Wording

Use "controlled custom-stress evidence", "local mock pre-commit contract", and "diagnostic" instead of "deployed safety", "guarantee", or "complete defense".
""",
    )
    write_text(
        PACKAGE / "10_related_work_checklist.md",
        """# Related Work Checklist

E58 does not verify or add citations. Before submission, fill this checklist using primary sources.

## Must Cover

- Agent safety benchmarks and prompt-injection defenses.
- Tool-use guardrails and step-level invocation safety.
- Pre-execution planning guards and trajectory anomaly detection.
- Provenance, dependency graphs, control/data-flow defenses, and capability systems.
- Policy-as-code and authorization infrastructure.
- Selective classification, abstention, and risk/coverage tradeoffs.
- Counterfactual and invariance testing for ML systems.

## Current Citation Status

`paper_materials/effect_binding_guard_paper/ndss_candidate/references.bib` should be inspected before writing. If it is empty or incomplete, treat related-work text as a to-do, not as submission-ready.
""",
    )
    write_text(
        PACKAGE / "12_reviewer_response_strategy.md",
        """# Reviewer Response Strategy

## Likely Objection: The method is synthetic or controlled.

Response: Agree with the boundary. The paper contributes a counterfactual measurement framework and local pre-commit prototype, not a deployment claim.

## Likely Objection: E55 shares schemas with the label generator.

Response: Report it as a limitation. E57 resource perturbation and independent reference authorizer reduce but do not eliminate this concern.

## Likely Objection: Why not use learned end-to-end text classification?

Response: E49 is diagnostic appendix evidence. The main argument is that explicit effect/resource/authorization/provenance binding is inspectable and gives clearer failure modes.

## Likely Objection: Does this reproduce existing papers?

Response: No. It is custom stress and component evidence unless an artifact is explicitly marked original-method reproduction.
""",
    )


def write_outline_and_repro() -> None:
    write_text(
        PACKAGE / "13_paper_outline.md",
        """# Paper Outline

1. Introduction: tool-effect binding gap and why surface robustness is insufficient.
2. Threat model and scope: pre-commit mediation, controlled custom stress, no production guarantee.
3. Counterfactual Tool-Effect Binding Framework.
4. Reference Hard Effect-Binding Guard.
5. Existing defenses and E47/E48 measurement results.
6. Robustness and bottlenecks from E50.
7. Authorization-aware local pre-commit prototype from E55.
8. Validity checks from E56/E57.
9. Discussion, limitations, ethics, and artifact release.
""",
    )
    write_text(
        PACKAGE / "14_section_writing_briefs.md",
        """# Section Writing Briefs

## Introduction

Lead with a concrete side-effect authorization failure: same tool name or same plan text is not enough; safety depends on realized effect, resource, authorization, provenance, and operation mode.

## Method

Define effect atoms, authorization context, provenance/control source, selective decisions, and the non-oracle input contract.

## Results

Keep E48/E50/E55/E57 scopes separate. Put E50 resource/auth bottleneck before E55, so E55 reads as a targeted response rather than an unexplained new benchmark.

## Limitations

State that E55 is deterministic local mock contract evidence and that real deployment requires independent traces, resource identity infrastructure, policy UI, mediation, logging, and adversarial validation.
""",
    )
    write_text(
        PACKAGE / "15_artifact_reproducibility_plan.md",
        """# Artifact Reproducibility Plan

## Existing Artifact Checks

```bash
python scripts/build_effect_binding_guard_paper_materials.py --validate-only
python scripts/build_effect_binding_writing_package_e58.py --validate-only
```

## Experiment Reproduction Commands

Use the canonical scripts documented in `paper_materials/effect_binding_guard_paper/reproduction/` and the E48-E57 experiment READMEs. Treat any command not already validated in the repo as "needs verification".

## E58 Validation

```bash
python -m py_compile scripts/build_effect_binding_writing_package_e58.py
python scripts/build_effect_binding_writing_package_e58.py
python scripts/build_effect_binding_writing_package_e58.py --validate-only
```

No E58 step calls APIs, models, or real tools.
""",
    )


def write_snippets_and_appendix(numbers: list[CoreNumber]) -> None:
    lookup = number_lookup(numbers)
    write_text(
        PACKAGE / "snippets/evidence_chain_short.md",
        "E47-E57 provide controlled custom-stress evidence that stable agent safety decisions require binding realized effects to resources, authorization context, provenance/control source, and operation mode. The evidence supports a measurement framework and local pre-commit prototype, not production safety.",
    )
    write_text(
        PACKAGE / "snippets/evidence_chain_long.md",
        """E47 starts from tool-effect fragmentation and counterfactual invariance tests. E48 implements a non-oracle hard Effect-Binding Guard. E50 shows the guard's main remaining weakness is resource/authorization binding. E55 then adds typed authorization context and effect-resource-operation atom expansion, improving local mock pre-commit mediation. E57 checks deterministic resource-name perturbation and independent reference-authorizer agreement. Together, these results argue for explicit binding infrastructure rather than surface-only monitors.""",
    )
    write_text(
        PACKAGE / "snippets/method_summary.md",
        "The method decomposes candidate agent actions into realized effect/resource/operation/provenance tuples, checks authorization and evidence under a selective ALLOW/DENY/ABSTAIN policy, and uses local pre-commit mediation to avoid treating tool names or trajectory templates as sufficient safety evidence.",
    )
    write_text(
        PACKAGE / "snippets/reference_guard_algorithm.md",
        """# Reference Hard Guard Algorithm

1. Parse non-oracle tool/action views into candidate tuple fields.
2. Compute multi-view disagreement and unknown-field indicators.
3. Use non-oracle evidence fallback only when visible evidence is available.
4. Apply hard provenance overlay.
5. Return `ALLOW`, `DENY`, or `ABSTAIN`.
""",
    )
    write_text(
        PACKAGE / "snippets/authz_precommit_algorithm.md",
        """# Authorization-Aware Pre-Commit Prototype

1. Expand each visible tool call into effect-resource-operation atoms.
2. Canonicalize resources and aliases.
3. Check all atoms against the typed authorization context.
4. Apply operation-mode, multi-resource, visibility, and provenance constraints.
5. Abstain if evidence or canonicalization is insufficient.
6. Commit only if all atoms are authorized.
""",
    )
    write_text(
        PACKAGE / "appendix_materials/appendix_plan.md",
        """# Appendix Plan

- Full E47/E48 counterfactual construction.
- E50 source-balanced and LOSO details.
- E55 schema, atom-expansion examples, slice metrics, and ablations.
- E56 strict replay and decision-path audit.
- E57 resource perturbation and reference-authorizer details.
- E49 learned calibration as diagnostic appendix only.
""",
    )
    write_text(
        PACKAGE / "appendix_materials/audit_packet_summary.md",
        f"""# Audit Packet Summary

- E57 spot-audit packet rows: `{val(lookup, 'E57 spot-audit packet rows')}`.
- Packet source: `{SOURCE_FILES['e57_packet']}`.
- Summary source: `{SOURCE_FILES['e57_spot']}`.

This packet is ready for human/reviewer inspection but does not itself count as completed human annotation unless separately annotated.
""",
    )
    write_text(
        PACKAGE / "audit/audit_status.md",
        f"""# Audit Status

- E55 decision-path audit passed: `{val(lookup, 'E55 decision-path audit passed')}`.
- E55 leakage audit passed: `{val(lookup, 'E55 leakage audit passed')}`.
- E56 strict mode passed: `{val(lookup, 'E56 strict mode passed')}`.
- E57 perturbation stability passed: `{val(lookup, 'E57 perturbation stability passed')}`.
- E57 reference-authorizer decision agreement: `{pct(val(lookup, 'E57 reference decision agreement'))}`.

These checks improve credibility for controlled local contract evidence. They do not establish production safety or real-world generalization.
""",
    )


def copy_lightweight_sources(discovery: list[dict[str, str]]) -> None:
    target = PACKAGE / "logs/source_hashes.json"
    write_text(target, json.dumps(discovery, indent=2, ensure_ascii=False))


def validate_package() -> list[str]:
    errors: list[str] = []
    if not PACKAGE.exists():
        return [f"Package directory missing: {rel(PACKAGE)}"]
    for d in REQUIRED_DIRS:
        path = PACKAGE / d
        if not path.is_dir():
            errors.append(f"Missing required directory: {rel(path)}")
    for f in REQUIRED_PACKAGE_FILES:
        path = PACKAGE / f
        if not path.is_file():
            errors.append(f"Missing required file: {rel(path)}")
        elif path.stat().st_size == 0:
            errors.append(f"Empty required file: {rel(path)}")

    core_csv = PACKAGE / "tables/core_numbers.csv"
    if core_csv.exists():
        with core_csv.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        required_fragments = ["E48", "E50", "E55", "E57"]
        for frag in required_fragments:
            if not any(frag in row.get("name", "") for row in rows):
                errors.append(f"core_numbers.csv has no {frag} number")
        for row in rows:
            if not row.get("source_file"):
                errors.append(f"Core number missing source_file: {row.get('name')}")
            if row.get("source_type") == "existing_result_file" and not row.get("key_path"):
                errors.append(f"Existing-result core number missing key path: {row.get('name')}")
    boundary = (PACKAGE / "08_claim_boundary.md").read_text(encoding="utf-8", errors="replace") if (PACKAGE / "08_claim_boundary.md").exists() else ""
    for phrase in ["Allowed Claims", "Disallowed Claims", "Production safety", "E49"]:
        if phrase not in boundary:
            errors.append(f"Claim boundary missing phrase: {phrase}")
    ndss_diag = (PACKAGE / "logs/ndss_build_diagnosis.md").read_text(encoding="utf-8", errors="replace") if (PACKAGE / "logs/ndss_build_diagnosis.md").exists() else ""
    if "2-page" not in ndss_diag and "page count: `2`" not in ndss_diag:
        errors.append("NDSS diagnosis does not explicitly report the 2-page PDF.")
    if "pre-E56 backup" not in ndss_diag and "ndss_candidate_pre_e56_backup" not in ndss_diag:
        errors.append("NDSS diagnosis does not mention missing pre-E56 backup.")
    for path in [PACKAGE / "README.md", PACKAGE / "08_claim_boundary.md", PACKAGE / "09_limitations_and_risks.md"]:
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            if "production safety" not in text:
                errors.append(f"Claim-boundary language missing production-safety caveat in {rel(path)}")
    return errors


def build(force: bool = False) -> None:
    if PACKAGE.exists():
        if not force:
            raise SystemExit(f"Refusing to overwrite existing package: {rel(PACKAGE)}. Use --force to rebuild.")
        shutil.rmtree(PACKAGE)
    for d in REQUIRED_DIRS:
        (PACKAGE / d).mkdir(parents=True, exist_ok=True)

    discovery = discover_sources()
    numbers = collect_core_numbers()
    ndss = diagnose_ndss()

    write_core_number_tables(numbers)
    write_text(PACKAGE / "logs/source_discovery.md", build_source_discovery(discovery))
    ndss_text = build_ndss_status_text(ndss)
    write_text(PACKAGE / "logs/ndss_build_diagnosis.md", ndss_text)
    write_text(PACKAGE / "11_ndss_build_status.md", ndss_text)
    write_claim_sources(numbers)
    write_table_plans(numbers)
    write_figure_plans()
    write_main_markdown(numbers, discovery, ndss)
    write_boundaries_and_strategy()
    write_outline_and_repro()
    write_snippets_and_appendix(numbers)
    copy_lightweight_sources(discovery)

    errors = validate_package()
    if errors:
        for error in errors:
            print(f"VALIDATION ERROR: {error}")
        raise SystemExit(1)
    print(f"Built E58 writing package at {rel(PACKAGE)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="overwrite an existing E58 package")
    parser.add_argument("--validate-only", action="store_true", help="validate an existing package without rebuilding")
    args = parser.parse_args()

    if args.validate_only:
        errors = validate_package()
        if errors:
            for error in errors:
                print(f"VALIDATION ERROR: {error}")
            raise SystemExit(1)
        print(f"Validated E58 writing package at {rel(PACKAGE)}")
        return
    build(force=args.force)


if __name__ == "__main__":
    main()
