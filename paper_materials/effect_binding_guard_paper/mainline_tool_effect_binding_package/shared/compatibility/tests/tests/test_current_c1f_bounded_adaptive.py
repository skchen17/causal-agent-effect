"""Static gates for the frozen current-C1f bounded adaptive rerun."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "shared/compatibility/scripts/run_current_c1f_bounded_adaptive.py"


def load_module():
    spec = importlib.util.spec_from_file_location("current_c1f_bounded", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_locked_manifest_no_guard_rows_and_current_profile_are_exact() -> None:
    module = load_module()
    protocol = json.loads(
        (module.EVALUATION_ROOT / "preregistration.json").read_text(encoding="utf-8")
    )
    cases = module.read_jsonl(module.EVALUATION_ROOT / "locked-case-manifest.jsonl")
    module.validate_preregistration(protocol, cases)
    assert len(cases) == 40

    no_guard = module.load_no_guard(cases)
    assert len(no_guard) == 160
    assert {row["method"] for row in no_guard} == {"no_guard"}
    no_guard_hashes = module.verify_no_guard_source(protocol, cases)
    assert len(no_guard_hashes) == 5
    assert no_guard_hashes["declared_model"] == module.MODEL_SHA256

    hashes = module.verify_frozen_c1f()
    assert len(hashes) >= 2
    assert hashes["registered_descriptors"] == (
        "dc9e16d87eefcf6ba54e71bc0e799b96eaaa062f6e22cfdf9db0616b6954e9e4"
    )

    env = module.environment(18090)
    assert env["E77_POLICY_VARIANT"] == "atom_control_taint_envelope"
    assert env["E77_UNCERTAINTY_POLICY"] == "allow_with_trail"
    assert env["LOCAL_LLM_PORT"] == "18090"
    assert env["E77_REGISTERED_DESCRIPTOR_JSONL"].endswith(
        "registered-effect-diff-descriptors.jsonl"
    )
    assert env["E77_RELATION_CATALOG"].endswith("registered_relation_catalog.json")
    assert not any("gold" in key.lower() or "label" in key.lower() for key in env)
