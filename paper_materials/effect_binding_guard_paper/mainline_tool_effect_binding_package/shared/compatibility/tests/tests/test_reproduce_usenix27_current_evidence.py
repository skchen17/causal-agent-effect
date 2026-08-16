from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/reproduce_usenix27_current_evidence.py"


def module():
    spec = importlib.util.spec_from_file_location("usenix_current_evidence", SCRIPT)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def test_current_pdf_numbers_are_traceable_and_pending_rows_stay_out() -> None:
    report = module().build()
    assert report["status"] == "current_pdf_verified_final_evaluation_incomplete"
    assert report["table_checks"]["e77_missing_display_tokens"] == []
    assert report["table_checks"]["e80_obligation_table_matches"]
    assert len(report["rows"]) >= 14
    assert {"E78", "E79-no-guard", "E79-guard", "E81", "E82", "E83"} == set(report["pending_final_protocol_artifacts"])
