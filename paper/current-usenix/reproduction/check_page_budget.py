#!/usr/bin/env python3
"""Measure the USENIX technical-body page budget from the compiled AUX label."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


PAPER = Path(__file__).resolve().parents[1]
LIMIT = 13


def main() -> int:
    aux = PAPER / "main.aux"
    pdf = PAPER / "main.pdf"
    if not aux.is_file() or not pdf.is_file():
        raise FileNotFoundError("compile main.tex before checking the page budget")
    match = re.search(
        r"\\newlabel\{technical-body-end\}\{\{[^}]*\}\{(\d+)\}",
        aux.read_text(encoding="utf-8", errors="replace"),
    )
    if not match:
        raise RuntimeError("technical-body-end label is missing from main.aux")
    body_pages = int(match.group(1))
    info = subprocess.run(
        ["pdfinfo", str(pdf)], check=True, capture_output=True, text=True
    ).stdout
    total_match = re.search(r"^Pages:\s+(\d+)$", info, re.MULTILINE)
    if not total_match:
        raise RuntimeError("pdfinfo did not report a page count")
    total_pages = int(total_match.group(1))
    report = {
        "status": "passed" if body_pages <= LIMIT else "failed",
        "technical_body_pages": body_pages,
        "technical_body_limit": LIMIT,
        "total_pdf_pages": total_pages,
        "excluded_from_body_limit": ["references", "ethics", "open_science", "appendices"],
        "measurement": "LaTeX page label immediately after Conclusion in the USENIX-template build",
    }
    output = PAPER / "page_budget_report.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (PAPER / "page_budget_report.md").write_text(
        "# USENIX Page-Budget Check\n\n"
        f"Status: `{report['status']}`. Technical body: `{body_pages}/{LIMIT}` pages; "
        f"complete PDF: `{total_pages}` pages.\n\n"
        "The body endpoint is a LaTeX label placed immediately after Conclusion. "
        "References, Ethics, Open Science, and appendices follow that label.\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
