"""Attack-surface smoke driver for the generalized-fix (iffix) safety gate.

Runs the SAME case list under two conditions:
  G  : frozen guard   (PYTHONPATH=code:.)
  G' : iffix variant  (PYTHONPATH=shadow_iffix:code)

Case list (preregistered, see gfix_preregistration_2026-08-07.json):
  per suite: 3 benign cases (user_task_0/1/2) + 6 attack cases
  (user_task_0..5 x injection_task_0, important_instructions).

Gate: abort/flag if ASR(G') > ASR(G) on the identical attack set.

Both conditions use DeepSeek via E77_LLM_* env (set from /tmp/deepseek_key.env
by the caller; never printed here).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
E75PY = ROOT / "experiments/unified-agent-security-baselines/runs/unified-agent-security-comparison/agentdojo-env/bin/python"
E75_MODULE = "src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.run_e75"
RESULTS = ROOT / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard"
SHADOW_ROOT = ROOT / "code/shadow_iffix"
RUN_BASE = ROOT / "experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard"

SUITES = ["banking", "slack", "travel", "workspace"]
BENIGN_TASKS = ["user_task_0", "user_task_1", "user_task_2"]
ATTACK_TASKS = [f"user_task_{i}" for i in range(6)]
INJECTION = "injection_task_0"
EXECUTION_DATE = "2026-08-02"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def walk_files(pkg_root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(pkg_root, followlinks=True):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.is_file():
                files[str(p.relative_to(pkg_root))] = sha256(p)
    return files


def condition_env(condition: str, run_root: Path) -> dict[str, str]:
    if condition == "G":
        pythonpath = f"{ROOT / 'code'}:."
    elif condition == "Gprime":
        pythonpath = f"{SHADOW_ROOT}:{ROOT / 'code'}"
    else:
        raise ValueError(condition)
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


def run_block(condition: str, suite: str, mode: str, run_root: Path) -> int:
    cmd = [
        str(E75PY), "-m", E75_MODULE,
        "--mode", "official-live-run",
        "--agentdojo-version", "v1.1.2",
        "--live-method", "ours_e77_effect_diff_runtime",
        "--live-suites", suite,
        "--live-modes", mode,
        "--live-logdir", str(run_root / "agentdojo_logs"),
        "--local-llm-port", "18087",
        "--live-timeout-seconds", "0",
    ]
    if mode == "benign":
        for t in BENIGN_TASKS:
            cmd += ["--live-user-task", t]
    else:
        for t in ATTACK_TASKS:
            cmd += ["--live-user-task", t]
        cmd += ["--live-injection-task", INJECTION]
    env = condition_env(condition, run_root)
    completed = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True)
    (run_root / f"command_status.{suite}.{mode}.txt").write_text(
        f"returncode={completed.returncode}\n## stdout\n{completed.stdout}\n## stderr\n{completed.stderr}\n",
        encoding="utf-8",
    )
    return completed.returncode


def main() -> int:
    condition = sys.argv[1]  # G or Gprime
    if condition not in {"G", "Gprime"}:
        raise ValueError("condition must be G or Gprime")
    if not os.getenv("E77_LLM_BASE_URL"):
        raise RuntimeError("E77_LLM_BASE_URL must be set (external API mode)")
    tag = "deepseek-gfix-smoke-gprime" if condition == "Gprime" else "deepseek-gfix-smoke-gfrozen"
    run_root = RUN_BASE / f"{tag}-20260807"
    run_root.mkdir(parents=True, exist_ok=True)

    # fail-closed integrity audit: for Gprime, non-variant shadow files must
    # equal the frozen tree; for G, the frozen tree must remain untouched
    # relative to the preregistration baseline.
    frozen_pkg = ROOT / "code/src/experiments/effect_binding_guard"
    frozen = walk_files(frozen_pkg)
    record: dict = {
        "condition": condition,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "frozen_file_count": len(frozen),
        "case_selection": {
            "benign": {s: BENIGN_TASKS for s in SUITES},
            "attack": {s: {t: INJECTION for t in ATTACK_TASKS} for s in SUITES},
        },
        "execution_date": EXECUTION_DATE,
    }
    if condition == "Gprime":
        shadow = walk_files(SHADOW_ROOT / "src/experiments/effect_binding_guard")
        variants = {
            "e77_effect_diff_runtime_guard/e77_runtime.py",
            "e77_effect_diff_runtime_guard/agentdojo_e77_runtime_patch.py",
        }
        mism = sorted(n for n, h in frozen.items() if n not in variants and shadow.get(n) != h)
        if mism or len(shadow) != len(frozen):
            raise RuntimeError(f"shadow integrity failed: {mism}")
        record["shadow_integrity_ok"] = True
    baseline_path = ROOT / "audit/gfix-20260807/frozen_tree_hashes_before.json"
    baseline = json.loads(baseline_path.read_text())  # flat dict: relpath -> sha256
    drift = sorted(n for n, h in baseline.items() if frozen.get(n) != h)
    if drift or len(baseline) != len(frozen):
        raise RuntimeError(f"FROZEN TREE DRIFT DETECTED — aborting smoke: {drift}")
    record["frozen_tree_zero_drift"] = True
    (run_root / "smoke_record.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")

    failures = []
    for suite in SUITES:
        for mode in ("attack", "benign"):
            rc = run_block(condition, suite, mode, run_root)
            print(f"[{condition}] {suite}/{mode} rc={rc}", flush=True)
            if rc != 0:
                failures.append(f"{suite}/{mode}")
    record["completed_at"] = datetime.now(timezone.utc).isoformat()
    record["failures"] = failures
    (run_root / "smoke_record.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
