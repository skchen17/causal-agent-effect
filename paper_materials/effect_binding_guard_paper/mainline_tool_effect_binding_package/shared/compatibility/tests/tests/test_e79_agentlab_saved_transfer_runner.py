from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


TEST_PATH = Path(__file__).resolve()
ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *TEST_PATH.parents)
    if (candidate / "paper/current-usenix").exists()
)
SCRIPT = ROOT / "scripts/run_e79_agentlab_saved_transfer.py"
QUEUE_SCRIPT = ROOT / "shared/compatibility/scripts/run_e79_agentlab_qwen32_queue.py"


def module():
    spec = importlib.util.spec_from_file_location("e79_saved_transfer_runner", SCRIPT)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def queue_module():
    spec = importlib.util.spec_from_file_location("e79_saved_transfer_queue", QUEUE_SCRIPT)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def test_manifest_reconstructs_exact_303_cartesian_keys() -> None:
    loaded = module()
    assert loaded.ROOT == ROOT
    selection = loaded.selection_by_suite(loaded.read_cases())
    assert loaded.expected_case_count(selection) == 303
    assert {suite: (len(row["users"]), len(row["injections"])) for suite, row in selection.items()} == {
        "banking": (16, 9), "slack": (17, 5), "travel": (5, 5), "workspace": (7, 7)
    }


def test_targeted_selection_accepts_only_fixed_manifest_key() -> None:
    loaded = module()
    selection = loaded.targeted_selection(
        loaded.read_cases(), "slack:user_task_10:injection_task_5"
    )
    assert selection == {
        "slack": {
            "users": ["user_task_10"],
            "injections": ["injection_task_5"],
        }
    }


def test_targeted_selection_rejects_unknown_or_malformed_key() -> None:
    loaded = module()
    try:
        loaded.targeted_selection(loaded.read_cases(), "slack:user_task_999:injection_task_5")
    except ValueError as exc:
        assert "not in the fixed E79 manifest" in str(exc)
    else:
        raise AssertionError("unknown case must fail")
    try:
        loaded.targeted_selection(loaded.read_cases(), "malformed")
    except ValueError as exc:
        assert "SUITE:USER_TASK_ID:INJECTION_TASK_ID" in str(exc)
    else:
        raise AssertionError("malformed case key must fail")


def test_outcome_blind_pilot_manifest_reconstructs_24_fixed_keys() -> None:
    loaded = module()
    path = loaded.ROOT / "evaluation/e79_long_horizon/deepseek_c1f_pn_pilot_manifest.json"
    selection = loaded.frozen_manifest_selection(path, loaded.read_cases())
    assert loaded.expected_case_count(selection) == 24
    assert set(selection) == {"banking", "slack", "travel", "workspace"}


def test_guard_and_no_guard_commands_differ_only_by_guard_module() -> None:
    loaded = module()
    common = dict(
        suite="workspace", users=["user_task_1"], injections=["injection_task_5"],
        model_id="qwen3_32b_local", logdir=ROOT / "runs/test", force_rerun=False,
    )
    no_guard = loaded.build_command(method="no_guard", **common)
    guarded = loaded.build_command(method="e77", **common)
    assert no_guard[no_guard.index("--model") + 1] == "LOCAL"
    assert loaded.ATTACK_MODULE in no_guard and loaded.ATTACK_MODULE in guarded
    assert loaded.COMPAT_MODULE in no_guard and loaded.COMPAT_MODULE in guarded
    assert no_guard[no_guard.index("--tool-delimiter") + 1] == "user"
    assert loaded.GUARD_MODULE not in no_guard and loaded.GUARD_MODULE in guarded
    guard_index = guarded.index(loaded.GUARD_MODULE)
    assert guarded[guard_index - 1] == "--module-to-load"
    assert guarded[: guard_index - 1] + guarded[guard_index + 1 :] == no_guard


def test_provenance_normalized_command_composes_after_frozen_guard() -> None:
    loaded = module()
    command = loaded.build_command(
        suite="workspace",
        users=["user_task_1"],
        injections=["injection_task_0"],
        method="c1f_pn",
        model_id="qwen3_32b_local",
        logdir=ROOT / "runs/test",
        force_rerun=False,
    )
    assert command.index(loaded.GUARD_MODULE) < command.index(loaded.PROVENANCE_NORMALIZATION_MODULE)
    assert loaded.DEEPSEEK_MODULE not in command


def test_deepseek_agent_patch_is_explicit_and_does_not_serialize_key() -> None:
    loaded = module()
    command = loaded.build_command(
        suite="banking",
        users=["user_task_0"],
        injections=["injection_task_0"],
        method="c1f_pn",
        model_id="unused-local-id",
        logdir=ROOT / "runs/test",
        force_rerun=False,
        agent_backend="deepseek",
    )
    assert command.index(loaded.PROVENANCE_NORMALIZATION_MODULE) < command.index(loaded.DEEPSEEK_MODULE)
    assert "sk-" not in " ".join(command)


def test_dry_run_does_not_claim_results() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "separate finalizer verifies every expected key" in text
    assert "execution_completed_unfinalized" in text
    assert '"E77_RUNTIME_CATALOG": str(' in text
    assert "CURRENT_C1F_DESCRIPTORS" in text
    assert "CURRENT_C1F_RUNTIME_CATALOG" in text
    assert "CURRENT_C1F_RELATION_CATALOG" in text


def test_c1f_transfer_verifies_every_frozen_source_hash() -> None:
    loaded = module()
    observed = loaded.verify_c1f_sources()
    assert "freeze_manifest" in observed
    assert {
        "policy",
        "runtime_patch",
        "registered_descriptors",
        "runtime_catalog",
        "relation_catalog",
    }.issubset(observed)
    frozen = json.loads(loaded.FREEZE_C1F.read_text(encoding="utf-8"))
    expected = {
        name: loaded.ROOT / frozen["source_artifacts"][name]["path"]
        for name in ("registered_descriptors", "runtime_catalog", "relation_catalog")
    }
    assert loaded.CURRENT_C1F_DESCRIPTORS == expected["registered_descriptors"]
    assert loaded.CURRENT_C1F_RUNTIME_CATALOG == expected["runtime_catalog"]
    assert loaded.CURRENT_C1F_RELATION_CATALOG == expected["relation_catalog"]


def test_pair_report_binds_both_methods_and_frozen_sources(tmp_path) -> None:
    loaded = queue_module()
    loaded.ROOT = tmp_path
    loaded.CASES = tmp_path / "cases.jsonl"
    loaded.SAVED_MANIFEST = tmp_path / "saved_manifest.json"
    loaded.PAIR_RESULT = tmp_path / "analysis/results/current_pair.json"
    loaded.CASES.write_text("{}\n", encoding="utf-8")
    loaded.SAVED_MANIFEST.write_text("{}\n", encoding="utf-8")
    results = tmp_path / "analysis/results"
    results.mkdir(parents=True)
    for method, attacks, utility in (("no_guard", 9, 180), ("c1f", 2, 170)):
        payload = {
            "status": "passed",
            "expected_case_keys": 303,
            "metrics": {
                "n": 303,
                "evaluable": True,
                "attack_successes": attacks,
                "utility_successes": utility,
            },
            "precommit_mediation": (
                {"signature_multiset_exact_match": True, "missing_check_occurrences": 0}
                if method == "c1f"
                else None
            ),
        }
        (results / f"e79_agentlab_saved_transfer_{method}_results.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
    (results / "e79_agentlab_saved_transfer_c1f_full_status.json").write_text(
        json.dumps({"c1f_source_hashes": {"freeze_manifest": "a" * 64, "policy": "b" * 64}}),
        encoding="utf-8",
    )
    run_root = tmp_path / "run"
    run_root.mkdir()
    pair = loaded.build_pair_report(run_root)
    assert pair["status"] == "passed"
    assert [row["condition"] for row in pair["comparison_metrics"]] == ["no_guard", "c1f"]
    assert pair["comparison_metrics"][0]["attack_successes"] == 9
    assert pair["comparison_metrics"][1]["attack_successes"] == 2
    assert pair["precommit_mediation"]["signature_multiset_exact_match"] is True
    assert len(pair["case_manifest_sha256"]) == 64
    assert loaded.PAIR_RESULT.is_file()
