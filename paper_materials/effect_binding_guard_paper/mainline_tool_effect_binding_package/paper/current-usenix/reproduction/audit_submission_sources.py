#!/usr/bin/env python3
"""Audit only the LaTeX sources included by the active USENIX manuscript."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


PAPER = Path(__file__).resolve().parents[1]
INPUT = re.compile(r"\\input\{([^}]+)\}")
CITE = re.compile(r"\\cite\{([^}]+)\}")
LABEL = re.compile(r"\\label\{([^}]+)\}")
REF = re.compile(r"\\(?:ref|pageref|autoref)\{([^}]+)\}")
BIB_KEY = re.compile(r"^\s*@\w+\s*\{\s*([^,\s]+)", re.MULTILINE)

FORBIDDEN_SOURCE = {
    "local_path": re.compile(r"/(?:data/CSK|home/user)(?:/|\b)"),
    "credential": re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    "private_project_label": re.compile(r"causal-agent-safety-research", re.I),
    "unfinished_marker": re.compile(r"\b(?:TODO|FIXME)\b"),
}
FORBIDDEN_PDF = {
    **FORBIDDEN_SOURCE,
    "internal_experiment_id": re.compile(r"\bE\d{2}(?:-v\d+)?\b"),
    "broken_reference": re.compile(r"\?\?|Appendix\s+(?:8|10)\b"),
    "unsupported_sota": re.compile(r"\b(?:state[- ]of[- ]the[- ]art|SOTA)\b", re.I),
    "unsupported_production_claim": re.compile(r"\bproduction safety\b", re.I),
}
BAD_LOG = re.compile(
    r"(?:LaTeX Warning: (?:Reference|Citation).*undefined|There were undefined references|"
    r"Overfull \\hbox|Overfull \\vbox|Fatal error|Emergency stop|! LaTeX Error)",
    re.I,
)


def included_sources() -> list[Path]:
    root = PAPER / "main.tex"
    pending = [root]
    seen: set[Path] = set()
    while pending:
        path = pending.pop()
        path = path.resolve()
        if path in seen:
            continue
        if not path.is_file():
            raise FileNotFoundError(path)
        seen.add(path)
        text = path.read_text(encoding="utf-8")
        for raw in INPUT.findall(text):
            relative = Path(raw)
            if relative.suffix == "":
                relative = relative.with_suffix(".tex")
            candidate = PAPER / relative
            if not candidate.is_file():
                candidate = path.parent / relative
            pending.append(candidate)
    return sorted(seen)


def findings(text: str, patterns: dict[str, re.Pattern[str]], source: str) -> list[dict[str, str]]:
    return [
        {"source": source, "pattern": name, "match": match.group(0)}
        for name, pattern in patterns.items()
        if (match := pattern.search(text))
    ]


def main() -> int:
    sources = included_sources()
    texts = {path: path.read_text(encoding="utf-8") for path in sources}
    source_findings = []
    for path, text in texts.items():
        source_findings.extend(
            findings(text, FORBIDDEN_SOURCE, str(path.relative_to(PAPER)))
        )

    labels = {value for text in texts.values() for value in LABEL.findall(text)}
    refs = {value for text in texts.values() for value in REF.findall(text)}
    cites = {
        key.strip()
        for text in texts.values()
        for group in CITE.findall(text)
        for key in group.split(",")
        if key.strip()
    }
    bib_text = (PAPER / "references.bib").read_text(encoding="utf-8")
    bib_keys = set(BIB_KEY.findall(bib_text))

    pdf_text = subprocess.run(
        ["pdftotext", str(PAPER / "main.pdf"), "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    pdf_findings = findings(pdf_text, FORBIDDEN_PDF, "main.pdf")
    log_text = (PAPER / "main.log").read_text(encoding="utf-8", errors="replace")
    log_findings = [match.group(0) for match in BAD_LOG.finditer(log_text)]

    report = {
        "status": "passed",
        "included_sources": [str(path.relative_to(PAPER)) for path in sources],
        "n_included_sources": len(sources),
        "source_findings": source_findings,
        "pdf_findings": pdf_findings,
        "log_findings": log_findings,
        "missing_reference_labels": sorted(refs - labels),
        "unreferenced_labels": sorted(labels - refs - {"technical-body-end"}),
        "missing_bibtex_keys": sorted(cites - bib_keys),
        "uncited_bibtex_keys": sorted(bib_keys - cites),
        "n_citations": len(cites),
        "n_labels": len(labels),
        "n_refs": len(refs),
    }
    hard_failures = (
        source_findings
        or pdf_findings
        or log_findings
        or report["missing_reference_labels"]
        or report["missing_bibtex_keys"]
        or report["uncited_bibtex_keys"]
    )
    if hard_failures:
        report["status"] = "failed"
    (PAPER / "submission_source_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (PAPER / "submission_source_audit.md").write_text(
        "# Submission Source Audit\n\n"
        f"Status: `{report['status']}`. Included LaTeX files: `{len(sources)}`; "
        f"citations: `{len(cites)}`; labels/references: `{len(labels)}/{len(refs)}`.\n\n"
        f"Missing labels: `{report['missing_reference_labels']}`. Missing BibTeX keys: "
        f"`{report['missing_bibtex_keys']}`. Uncited BibTeX keys: "
        f"`{report['uncited_bibtex_keys']}`. Source/PDF/log findings: "
        f"`{len(source_findings)}/{len(pdf_findings)}/{len(log_findings)}`.\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
