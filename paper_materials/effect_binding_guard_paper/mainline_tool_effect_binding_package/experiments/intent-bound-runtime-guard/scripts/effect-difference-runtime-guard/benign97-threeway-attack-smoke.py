#!/usr/bin/env python3
"""Attack-surface smoke for the benign97 three-way comparison.

Safety gate (preregistered): ASR(G') must NOT exceed ASR(G) on the identical
16-attack set (benign97_threeway_attack_smoke_manifest_2026-08-08.json).

Runs one condition per invocation:
  G       : frozen guard   (PYTHONPATH=code:.)
  Gprime  : iffix variant  (PYTHONPATH=code/shadow_iffix:code)

Both conditions use DeepSeek via E77_LLM_* env (set by caller from
/tmp/deepseek_key.env; never printed here).  Does not touch V0-V3 or any
benign97 three-way run directory.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EVAL = ROOT / "experiments/intent-bound-runtime-guard/evaluation/effect-difference-runtime-guard"
RESULTS = ROOT / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard"
RUN_BASE = ROOT / "experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard"
E75PY = ROOT / "experiments/unified-agent-security-baselines/runs/unified-agent-security-comparison/agentdojo-env/bin/python"
E75_MODULE = "src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.run_e75"
SHADOW_ROOT = ROOT / "code/shadow_iffix"
MANIFEST = EVAL / "benign97_threeway_attack_smoke_manifest_2026-08-08.json"
EXECUTION_DATE = "2026-08-02"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def condition_env(condition: str, run_root: Path) -> dict[str, str]:
    pythonpath = f"{ROOT / 'code'}:." if condition == "G" else f"{SHADOW_ROOT}:{ROOT / 'code'}"
    return {
        **os.environ,
        "CUDA_VISIBLE_DEVICES": "",
        "PYTHONPATH": pythonpath,
        "E77_PLAN_CACHE": str(run_root / "plan_cache.json"),
        "E77_AUDIT_JSONL": str(run_root / "runtime_audit.jsonl"),
        "E77_RUNTIME_CATALOG": str(
            ROOT / "experiments/security-analysis-ablation-and-overhead/evaluation/runtime-mechanism-ablation/agentdojo_runtime_catalog.json"
        ),
        "E77_REGISTERED_DESCRIPTOR_JSONL": str(RESULTS / "registered-effect-diff-descriptors.jsonl"),
        "E77_RELATION_CATALOG": str(
            ROOT / "experiments/intent-bound-runtime-guard/evaluation/effect-difference-runtime-guard/registered_relation_catalog.json"
        ),
        "E77_EXECUTION_DATE": EXECUTION_DATE,
        "E77_PLANNER_PORT": "18087",
        "E77_AGENT_MAX_TOKENS": "4096",
        "E77_MAX_PLAN_REVISIONS": "3",
        "E77_MAX_TOTAL_PLAN_REVISIONS": "12",
        "E77_UNCERTAINTY_POLICY": "allow_with_trail",
        "E77_PLANNER_REPAIR_ATTEMPTS": "2",
        "E77_REVISION_MAX_TOKENS": "2048",
        "E77_REVISION_REPAIR_ATTEMPTS": "2",
        "E77_REVISION_NO_THINK_PREFIX": "0",
        "E75_LIVE_MODEL_NAME": "Qwen3-32B-Q4_K_M.gguf",
    }


def run_block(condition: str, suite: str, injection: str, tasks: list[str], run_root: Path) -> int:
    cmd = [
        str(E75PY), "-m", E75_MODULE,
        "--mode", "official-live-run",
        "--agentdojo-version", "v1.1.2",
        "--live-method", "ours_e77_effect_diff_runtime",
        "--live-suites", suite,
        "--live-modes", "attack",
        "--live-logdir", str(run_root / "agentdojo_logs"),
        "--local-llm-port", "18087",
        "--live-timeout-seconds", "0",
    ]
    for t in tasks:
        cmd += ["--live-user-task", t]
    cmd += ["--live-injection-task", injection]
    env = condition_env(condition, run_root)
    completed = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True)
    (run_root / f"command_status.{suite}.{injection}.txt").write_text(
        f"returncode={completed.returncode}\n## stdout\n{completed.stdout}\n## stderr\n{completed.stderr}\n",
        encoding="utf-8",
    )
    return completed.returncode


def main() -> int:
    condition = sys.argv[1]
    if condition not in {"G", "Gprime"}:
        raise ValueError("condition must be G or Gprime")
    if not os.getenv("E77_LLM_BASE_URL"):
        raise RuntimeError("E77_LLM_BASE_URL must be set (external API mode)")

    manifest = json.loads(MANIFEST.read_text())
    cases = manifest["cases"]
    # group by (suite, injection_task_id)
    by_group = defaultdict(list)
    for c in cases:
        by_group[(c["suite"], c["injection_task_id"])].append(c["user_task_id"])

    tag = "deepseek-benign97-smoke-gprime-20260808" if condition == "Gprime" else "deepseek-benign97-smoke-g-20260808"
    run_root = RUN_BASE / tag
    run_root.mkdir(parents=True, exist_ok=True)

    record = {
        "condition": condition,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": sha256(MANIFEST),
        "n_cases": len(cases),
        "groups": {f"{s}/{inj}": tasks for (s, inj), tasks in sorted(by_group.items())},
        "execution_date": EXECUTION_DATE,
    }

    rc_all = 0
    for (suite, injection), tasks in sorted(by_group.items()):
        print(f"[{condition}] suite={suite} injection={injection} tasks={len(tasks)}")
        rc = run_block(condition, suite, injection, sorted(tasks, key=lambda t: int(t.split("_")[-1])), run_root)
        print(f"[{condition}] suite={suite} rc={rc}")
        if rc != 0:
            rc_all = rc

    record["finished_at"] = datetime.now(timezone.utc).isoformat()
    record["rc"] = rc_all
    (run_root / "smoke_record.json").write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"condition": condition, "rc": rc_all, "record": str(run_root / "smoke_record.json")}))
    return rc_all


if __name__ == "__main__":
    raise SystemExit(main())
