from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/audit_usenix27_source_pdf.py"


def module():
    spec = importlib.util.spec_from_file_location("usenix_audit", SCRIPT)
    loaded = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(loaded)
    return loaded


def test_current_pdf_included_sources_and_pdf_pass_strict_audit() -> None:
    report = module().build()
    assert report["status"] == "passed"
    assert 1 <= report["pdf_pages_total"] <= 20
    assert report["citations"]["cited_keys"] == report["citations"]["bib_entries"]
    assert report["citations"]["cited_keys"] >= 34
    assert report["cross_references"]["missing_reference_targets"] == []
    assert report["citations"]["missing_bib_entries"] == []
    assert report["citations"]["uncited_bib_entries"] == []
    assert report["source_findings"] == []
    assert report["pdf_findings"] == []
