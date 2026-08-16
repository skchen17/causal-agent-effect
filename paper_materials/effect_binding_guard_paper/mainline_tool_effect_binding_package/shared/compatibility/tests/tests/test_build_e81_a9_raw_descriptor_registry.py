from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/build_e81_a9_raw_descriptor_registry.py"


def module():
    spec = importlib.util.spec_from_file_location("e81_a9", SCRIPT)
    loaded = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(loaded)
    return loaded


def test_a9_uses_only_round0_candidates_and_preserves_omissions() -> None:
    rows, summary = module().build()
    assert summary["status"] == "passed"
    assert len(rows) == summary["round0_candidates"] == 24
    assert all(row["round_index"] == 0 for row in rows)
    assert summary["tools_differing_from_counterfactually_validated_e77"] > 0
    assert summary["total_unclassified_fields"] > 0
    assert summary["contains_gold_labels_or_atoms"] is False


def test_raw_registry_is_a_complete_schema_partition() -> None:
    rows, _ = module().build()
    for row in rows:
        assert not (set(row["security_fields"]) & set(row["non_security_fields"]))
        assert set(row["unclassified_fields"]) <= set(row["non_security_fields"])
        assert row.get("counterfactual_validation_applied") is not True
