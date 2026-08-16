from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "evaluation/e79_long_horizon/toolsandbox_feasibility_manifest.json"


def test_toolsandbox_subset_is_frozen_offline_and_deterministic() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    scenarios = manifest["scenarios"]
    canonical = json.dumps(scenarios, sort_keys=True, separators=(",", ":"))
    assert manifest["status"] == "frozen_for_adapter_smoke"
    assert manifest["n_selected"] == 30 == len(scenarios)
    assert manifest["all_external_search_excluded"] is True
    assert all(not row["uses_external_search"] for row in scenarios)
    assert manifest["selection_hash"] == hashlib.sha256(canonical.encode()).hexdigest()


def test_toolsandbox_subset_covers_required_feasibility_strata() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    categories = manifest["category_counts"]
    assert categories["STATE_DEPENDENCY"] >= 7
    assert categories["CANONICALIZATION"] >= 7
    assert categories["INSUFFICIENT_INFORMATION"] >= 6
    assert categories["MULTIPLE_TOOL_CALL"] >= 20
    assert manifest["milestone_count_range"][1] >= 5
