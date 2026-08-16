from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_e83_runtime_microbenchmark.py"


def module():
    spec = importlib.util.spec_from_file_location("e83_microbenchmark", SCRIPT)
    loaded = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(loaded)
    return loaded


def test_microbenchmark_covers_field_and_ledger_scaling_without_runtime_llm() -> None:
    report = module().run(iterations=5, warmup=1)
    assert report["status"] == "passed"
    assert report["configurations"] == 18
    assert {row["n_security_fields"] for row in report["rows"]} == {1, 2, 4, 8, 16, 32}
    assert {row["resolver_ledger_noise_entries"] for row in report["rows"]} == {0, 16, 64}
    assert report["correctness"] == {"all_allow": True, "runtime_llm_calls": 0}
    assert all(row["wall_ns"]["p95"] >= row["wall_ns"]["p50"] > 0 for row in report["rows"])
