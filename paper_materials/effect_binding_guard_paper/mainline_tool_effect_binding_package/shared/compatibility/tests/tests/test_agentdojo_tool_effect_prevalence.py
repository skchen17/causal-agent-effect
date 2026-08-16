from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_agentdojo_tool_effect_prevalence.py"
SPEC = importlib.util.spec_from_file_location("effect_prevalence", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_calendar_creation_and_notifications_are_separate_effects() -> None:
    before = {"calendar": {"events": {}}, "inbox": {"emails": {}}}
    after = {
        "calendar": {"events": {"7": {"participants": ["a@example.com"]}}},
        "inbox": {
            "emails": {
                "9": {
                    "recipients": ["a@example.com"],
                    "cc": [],
                    "bcc": [],
                    "subject": "Invitation",
                }
            }
        },
    }
    units = MODULE.normalized_effects(before, after)
    assert {row["effect"] for row in units} == {
        "calendar_event_created",
        "email_delivered",
    }
    assert len(units) == 2


def test_drive_metadata_and_mirror_changes_do_not_inflate_effect_count() -> None:
    before = {
        "cloud_drive": {
            "files": {
                "1": {
                    "content": "old",
                    "size": 3,
                    "last_modified": "t0",
                    "shared_with": {},
                }
            },
            "initial_files": [],
        }
    }
    after = {
        "cloud_drive": {
            "files": {
                "1": {
                    "content": "new",
                    "size": 3,
                    "last_modified": "t1",
                    "shared_with": {},
                }
            },
            "initial_files": [{"id_": "1"}],
        }
    }
    units = MODULE.normalized_effects(before, after)
    assert len(units) == 1
    assert units[0]["effect"] == "file_updated"
    assert units[0]["details"]["changed_fields"] == ["content"]
    assert MODULE.raw_changed_paths(before, after) == ["cloud_drive.files.1.content"]


def test_target_expansion_is_per_principal() -> None:
    before = {"inbox": {"emails": {}}}
    after = {
        "inbox": {
            "emails": {
                "1": {
                    "recipients": ["a@example.com", "b@example.com", "a@example.com"],
                    "cc": ["c@example.com"],
                    "bcc": [],
                    "subject": "x",
                }
            }
        }
    }
    units = MODULE.inbox_effects(before, after)
    assert [row["target"] for row in units] == [
        "a@example.com",
        "b@example.com",
        "c@example.com",
    ]


def test_empty_structural_slack_containers_are_not_effects() -> None:
    before = {"slack": {"users": ["Alice"], "user_channels": {}, "user_inbox": {}}}
    after = {
        "slack": {
            "users": ["Alice", "Dora"],
            "user_channels": {"Dora": []},
            "user_inbox": {"Dora": []},
        }
    }
    units = MODULE.slack_effects(before, after)
    assert len(units) == 1
    assert units[0]["effect"] == "workspace_user_invited"


def test_report_fails_closed_on_missing_population() -> None:
    protocol = {
        "protocol_id": "test",
        "protocol_sha256": "hash",
        "analysis_status": "test",
        "execution": {"expected_inventory_source_manifest_sha256": "wrong"},
        "claim_boundary": "bounded",
    }
    report = MODULE.build_report([], [], protocol)
    assert report["status"] == "failed"


def test_generated_table_matches_report() -> None:
    report_path = (
        ROOT
        / "experiments/human-authority-and-causal-validation/results/"
        "agentdojo-tool-effect-prevalence/agentdojo-tool-effect-prevalence-report.json"
    )
    if not report_path.exists():
        return
    import json

    report = json.loads(report_path.read_text(encoding="utf-8"))
    table = (ROOT / "paper/current-usenix/tables/table_agentdojo_effect_prevalence.tex").read_text(
        encoding="utf-8"
    )
    prevalence = report["prevalence"]
    assert f"Effectful calls & {prevalence['n_effectful_calls']}/{report['n_official_calls']}" in table
    assert f"Compound effects & {prevalence['n_compound_calls']}/{prevalence['n_effectful_calls']}" in table
    assert f"Heterogeneous effects & {prevalence['n_heterogeneous_compound_calls']}/{prevalence['n_effectful_calls']}" in table
