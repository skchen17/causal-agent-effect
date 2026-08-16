from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = next(
    candidate
    for candidate in Path(__file__).resolve().parents
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
SCRIPT = (
    ROOT
    / "shared/compatibility/scripts/"
    "analyze_full_benign_abstain_root_causes.py"
)


def module():
    spec = importlib.util.spec_from_file_location(
        "full_benign_abstain_root_causes", SCRIPT
    )
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_full_benign_root_cause_accounting_and_privacy_gate():
    report, rows = module().summarize()
    assert report["status"] == "passed"
    assert report["n_tasks"] == 97
    assert report["precommit_checks"] == 426
    assert report["decision_counts"] == {
        "ABSTAIN": 152,
        "ALLOW": 270,
        "DENY": 4,
    }
    assert report["check_category_counts"][
        "authority_manifest_unavailable"
    ] == 107
    assert sum(report["check_category_counts"].values()) == 426
    assert report["reason_family_check_incidence"] == {
        "authority_manifest_unavailable": 107,
        "outside_exact_authority": 4,
        "resolver_value_unproven": 43,
        "security_field_unbound": 3,
        "tool_outside_bounded_plan": 2,
    }
    assert len(rows) == 97
    assert report["privacy_gate"] == {
        "task_text_emitted": False,
        "tool_arguments_emitted": False,
        "raw_model_output_emitted": False,
        "query_hash_emitted": False,
    }
    forbidden = {"task_text", "tool_arguments", "raw_model_output", "query_hash"}
    assert not any(forbidden & set(row) for row in rows)
