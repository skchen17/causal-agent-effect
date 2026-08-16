#!/usr/bin/env python3
"""Policy self-check (backtest) for context-repair-policy-v0v3 (D5).

Pre-registered in context-repair-policy-v0v3.json section "self_check":
the policy's detection rules must reproduce the KNOWN v17 r2 ground truth
(p2b_execution_report_2026-08-05.md) before the policy may be applied to
V0-V3:

  assertion 1: F3 detection on the r2 base run reproduces exactly the
               9-case set T (user_task_35 x 6 + user_task_38 x 3);
  assertion 2: F1 server-log rule on the r2 server log counts exactly 9
               non-noise HTTP-400 lines;
  assertion 3: F3 detection on the r2 merged run returns 0 cases.

Read-only: no file outside the results output directory is written; no
process is touched; no GPU is started.  The detection engine is imported
UNCHANGED from context-repair-v17.py (the exact module hash pinned in the
policy), which also verifies the toolchain-binding claim of the policy.

Python standard library only; CPU-only.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
TOOL_PATH = (
    ROOT
    / "experiments/intent-bound-runtime-guard/scripts/"
    "effect-difference-runtime-guard/context-repair-v17/context-repair-v17.py"
)
R2_BASE = (
    ROOT
    / "experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/"
    "recovery-normalization-qwen32-full-allow-with-trail-v17-726-r2"
)
R2_MERGED = (
    ROOT
    / "experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/"
    "recovery-normalization-qwen32-full-allow-with-trail-v17-726-r2-context-repaired"
)
METHOD = "local-ours_e77_effect_diff_runtime"
OUT_DIR = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "strict-atom-representation-attribution/context-repair-v0v3/policy-selfcheck"
)
POLICY_JSON = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/evaluation/"
    "strict-atom-representation-attribution/context-repair-policy-v0v3.json"
)
EXPECTED_T = sorted(
    [
        "workspace:user_task_35:important_instructions:injection_task_1",
        "workspace:user_task_35:important_instructions:injection_task_2",
        "workspace:user_task_35:important_instructions:injection_task_3",
        "workspace:user_task_35:important_instructions:injection_task_4",
        "workspace:user_task_35:important_instructions:injection_task_5",
        "workspace:user_task_35:none:none",
        "workspace:user_task_38:important_instructions:injection_task_1",
        "workspace:user_task_38:important_instructions:injection_task_4",
        "workspace:user_task_38:important_instructions:injection_task_5",
    ]
)


def load_tool():
    spec = importlib.util.spec_from_file_location("context_repair_v17", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["context_repair_v17"] = module  # dataclasses introspects sys.modules
    spec.loader.exec_module(module)
    return module


def sha256_of(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def f1_server_log_count(server_log: Path) -> dict:
    """Policy F1 rule: regex HTTP/1.1" 400 minus 'CUDA Graph id 400' noise."""
    pattern = re.compile(r'HTTP/1\.1" 400')
    noise = "CUDA Graph id 400"
    total = 0
    non_noise = 0
    with server_log.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if pattern.search(line):
                total += 1
                if noise not in line:
                    non_noise += 1
    return {"total_400_lines": total, "non_noise_400_lines": non_noise}


def main() -> int:
    tool = load_tool()
    tool_sha256 = sha256_of(TOOL_PATH)
    policy_sha256 = sha256_of(POLICY_JSON)
    policy = json.loads(POLICY_JSON.read_text(encoding="utf-8"))
    pinned = policy["toolchain_binding"]["base_tool"]["sha256_at_preregistration"]

    results = {
        "schema": "context-repair-policy-v0v3-selfcheck/1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy_id": policy["policy_id"],
        "policy_json_sha256": policy_sha256,
        "tool_path": str(TOOL_PATH),
        "tool_sha256": tool_sha256,
        "tool_hash_matches_preregistration": tool_sha256 == pinned,
        "assertions": {},
    }

    # --- assertion 1: F3 detection on r2 base reproduces the 9-case set ----
    affected_base, stats_base = tool.detect_truncated_cases(R2_BASE, METHOD)
    keys_base = sorted(row["case_key"] for row in affected_base)
    results["assertions"]["a1_base_T_equals_precedent"] = {
        "expected_n": len(EXPECTED_T),
        "observed_n": len(keys_base),
        "expected_cases": EXPECTED_T,
        "observed_cases": keys_base,
        "scan_stats": stats_base,
        "pass": keys_base == EXPECTED_T,
    }

    # --- assertion 2: F1 rule on the r2 server log counts exactly 9 --------
    server_log = R2_BASE / "llama_cpp_server.log"
    f1 = f1_server_log_count(server_log)
    results["assertions"]["a2_server_log_400_count"] = {
        "server_log": str(server_log),
        **f1,
        "expected_non_noise": 9,
        "pass": f1["non_noise_400_lines"] == 9,
    }

    # --- assertion 3: F3 detection on the merged run returns 0 -------------
    affected_merged, stats_merged = tool.detect_truncated_cases(R2_MERGED, METHOD)
    keys_merged = sorted(row["case_key"] for row in affected_merged)
    results["assertions"]["a3_merged_T_is_empty"] = {
        "observed_n": len(keys_merged),
        "observed_cases": keys_merged,
        "scan_stats": stats_merged,
        "pass": keys_merged == [],
    }

    results["overall_pass"] = all(
        assertion["pass"] for assertion in results["assertions"].values()
    ) and results["tool_hash_matches_preregistration"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "policy-selfcheck-v17-r2.json"
    out_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2, sort_keys=True))
    print(f"\n[selfcheck] overall_pass={results['overall_pass']} -> {out_path}")
    return 0 if results["overall_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
