#!/usr/bin/env python3
"""Audit PDF-included USENIX sources, references, build log, and PDF text."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper/current-usenix").is_dir()
    and (candidate / "analysis/results").is_dir()
)
PAPER = ROOT / "paper/current-usenix"
RESULTS = ROOT / "analysis/results"


INPUT_RE = re.compile(r"\\(?:input|include)\{([^}]+)\}")
LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
REF_RE = re.compile(r"\\(?:ref|pageref|autoref)\{([^}]+)\}")
CITE_RE = re.compile(r"\\cite\w*\{([^}]+)\}")
BIB_RE = re.compile(r"^@\w+\s*\{\s*([^,\s]+)", re.MULTILINE)


def included_sources(main: Path) -> list[Path]:
    seen: set[Path] = set()

    def visit(path: Path) -> None:
        path = path.resolve()
        if path in seen:
            return
        if not path.exists():
            raise FileNotFoundError(path)
        seen.add(path)
        text = path.read_text(encoding="utf-8")
        for name in INPUT_RE.findall(text):
            candidates = [main.parent / name, path.parent / name]
            candidates = [candidate.with_suffix(".tex") if candidate.suffix == "" else candidate for candidate in candidates]
            child = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
            visit(child)

    visit(main)
    references = main.parent / "references.bib"
    if references.exists():
        seen.add(references.resolve())
    return sorted(seen)


def scan_text(text: str) -> list[dict[str, str]]:
    patterns = {
        "absolute_home_path": r"/(?:home|Users)/[^\s}\]]+",
        "absolute_data_path": r"/data/[^\s}\]]+",
        "todo_fixme": r"\b(?:TODO|FIXME|XXX)\b",
        "credential": r"\b(?:sk-[A-Za-z0-9_-]{12,}|api[_-]?key\s*[:=])",
        "private_project_label": r"(?:causal-agent-safety-research|mainline_tool_effect_binding_package)",
        "broken_reference": r"\?\?",
    }
    findings = []
    for name, pattern in patterns.items():
        if re.search(pattern, text, flags=re.IGNORECASE if name in {"credential", "private_project_label"} else 0):
            findings.append({"category": name, "pattern": pattern})
    return findings


def run_command(command: list[str]) -> str:
    completed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=60)
    if completed.returncode != 0:
        raise RuntimeError(f"command failed: {command[0]}: {completed.stderr[-500:]}")
    return completed.stdout


def build() -> dict[str, Any]:
    sources = included_sources(PAPER / "main.tex")
    source_findings = []
    combined_tex = ""
    for path in sources:
        text = path.read_text(encoding="utf-8")
        combined_tex += "\n" + text
        for finding in scan_text(text):
            source_findings.append({"path": str(path.relative_to(PAPER)), **finding})

    tex_only = "\n".join(path.read_text(encoding="utf-8") for path in sources if path.suffix == ".tex")
    labels = LABEL_RE.findall(tex_only)
    refs = REF_RE.findall(tex_only)
    duplicate_labels = sorted(label for label in set(labels) if labels.count(label) > 1)
    missing_labels = sorted(set(refs) - set(labels))
    cites = sorted({key.strip() for group in CITE_RE.findall(tex_only) for key in group.split(",") if key.strip()})
    bib_text = (PAPER / "references.bib").read_text(encoding="utf-8")
    bib_keys = sorted(set(BIB_RE.findall(bib_text)))
    missing_citations = sorted(set(cites) - set(bib_keys))
    uncited_bib_entries = sorted(set(bib_keys) - set(cites))

    log_text = (PAPER / "main.log").read_text(encoding="utf-8")
    fatal_log_patterns = {
        "undefined_reference_or_citation": r"(?:undefined references|Citation .* undefined|Reference .* undefined)",
        "overfull_box": r"Overfull \\[hv]box",
        "fatal_or_error": r"(?:Fatal error|Emergency stop|^! )",
        "missing_file": r"(?:No file .*\.|File .* not found)",
    }
    log_findings = [name for name, pattern in fatal_log_patterns.items() if re.search(pattern, log_text, re.MULTILINE)]

    pdf_text = run_command(["pdftotext", str(PAPER / "main.pdf"), "-"])
    pdf_findings = scan_text(pdf_text)
    info = run_command(["pdfinfo", str(PAPER / "main.pdf")])
    page_match = re.search(r"^Pages:\s+(\d+)", info, re.MULTILINE)
    pages = int(page_match.group(1)) if page_match else None
    errors = []
    if source_findings:
        errors.append("source_scan_findings")
    if pdf_findings:
        errors.append("pdf_scan_findings")
    if duplicate_labels:
        errors.append("duplicate_labels")
    if missing_labels:
        errors.append("missing_reference_targets")
    if missing_citations:
        errors.append("missing_bib_entries")
    if uncited_bib_entries:
        errors.append("uncited_bib_entries")
    if log_findings:
        errors.append("build_log_findings")
    return {
        "audit": "usenix27_pdf_included_source_and_pdf",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not errors else "failed",
        "pdf_pages_total": pages,
        "included_sources": [str(path.relative_to(PAPER)) for path in sources],
        "source_findings": source_findings,
        "pdf_findings": pdf_findings,
        "cross_references": {
            "labels": len(labels),
            "references": len(refs),
            "duplicate_labels": duplicate_labels,
            "missing_reference_targets": missing_labels,
        },
        "citations": {
            "cited_keys": len(cites),
            "bib_entries": len(bib_keys),
            "missing_bib_entries": missing_citations,
            "uncited_bib_entries": uncited_bib_entries,
        },
        "build_log_findings": log_findings,
        "errors": errors,
        "scope_boundary": (
            "This pass covers sources reachable from main.tex, references.bib, main.log, and extracted main.pdf text. "
            "It does not certify pending row-level experiment logs or a future uploaded artifact archive."
        ),
    }


def main() -> int:
    report = build()
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "usenix27_source_pdf_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# USENIX Source/PDF Audit", "", f"Status: `{report['status']}`.", "",
        f"- Total PDF pages: `{report['pdf_pages_total']}`.",
        f"- Included source files: `{len(report['included_sources'])}`.",
        f"- Labels/references: `{report['cross_references']['labels']}` / `{report['cross_references']['references']}`.",
        f"- Cited/BibTeX keys: `{report['citations']['cited_keys']}` / `{report['citations']['bib_entries']}`.",
        f"- Source/PDF/build findings: `{len(report['source_findings'])}` / `{len(report['pdf_findings'])}` / `{len(report['build_log_findings'])}`.",
        "", "## Scope Boundary", "", report["scope_boundary"], "",
    ]
    (RESULTS / "usenix27_source_pdf_audit.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
