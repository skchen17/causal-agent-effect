"""Supplemental attack-surface smoke for the gfix safety gate: slack suite.

The main smoke (gfix-attack-smoke.py) used injection_task_0 per suite, but the
AgentDojo v1.1.2 slack suite registers only InjectionTask1..5 (no
injection_task_0), so the slack attack block produced zero attack logs under
both conditions (symmetric gap). The preregistration requires 6 attack cases
per suite; this supplement restores slack coverage with injection_task_1,
identical case list for G and Gprime (symmetric design).

Conditions (identical to main smoke):
  G  : frozen guard   (PYTHONPATH=code:.)
  G' : iffix variant  (PYTHONPATH=shadow_iffix:code)

Gate contribution: ASR(Gprime) vs ASR(G) on slack x user_task_0..5 x
injection_task_1 (important_instructions). Read-only w.r.t. all prior runs.
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

SUITE = "slack"
ATTACK_TASKS = [f"user_task_{i}" for i in range(6)]
INJECTION = "injection_task_1"
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


def main() -> int:
    condition = sys.argv[1]
    if condition not in {"G", "Gprime"}:
        raise ValueError("condition must be G or Gprime")
    for var in ("E77_LLM_BASE_URL", "E77_LLM_API_KEY", "E77_LLM_MODEL"):
        if not os.getenv(var):
            raise RuntimeError(f"{var} must be set (external API mode; values never printed)")
    tag = "deepseek-gfix-smoke-slack-inj1-gprime" if condition == "Gprime" else "deepseek-gfix-smoke-slack-inj1-gfrozen"
    run_root = RUN_BASE / f"{tag}-20260807"
    run_root.mkdir(parents=True, exist_ok=True)

    frozen_pkg = ROOT / "code/src/experiments/effect_binding_guard"
    frozen = walk_files(frozen_pkg)
    record: dict = {
        "condition": condition,
        "supplement_of": "gfix-attack-smoke main run (slack injection_task_0 does not exist in AgentDojo v1.1.2 slack suite)",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "frozen_file_count": len(frozen),
        "case_selection": {"attack": {SUITE: {t: INJECTION for t in ATTACK_TASKS}}},
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
    baseline = json.loads(baseline_path.read_text())
    drift = sorted(n for n, h in baseline.items() if frozen.get(n) != h)
    if drift or len(baseline) != len(frozen):
        raise RuntimeError(f"FROZEN TREE DRIFT DETECTED — aborting smoke: {drift}")
    record["frozen_tree_zero_drift"] = True
    (run_root / "smoke_record.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")

    cmd = [
        str(E75PY), "-m", E75_MODULE,
        "--mode", "official-live-run",
        "--agentdojo-version", "v1.1.2",
        "--live-method", "ours_e77_effect_diff_runtime",
        "--live-suites", SUITE,
        "--live-modes", "attack",
        "--live-logdir", str(run_root / "agentdojo_logs"),
        "--local-llm-port", "18087",
        "--live-timeout-seconds", "0",
    ]
    for t in ATTACK_TASKS:
        cmd += ["--live-user-task", t]
    cmd += ["--live-injection-task", INJECTION]
    env = condition_env(condition, run_root)
    completed = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True)
    (run_root / f"command_status.{SUITE}.attack.txt").write_text(
        f"returncode={completed.returncode}\n## stdout\n{completed.stdout}\n## stderr\n{completed.stderr}\n",
        encoding="utf-8",
    )
    record["completed_at"] = datetime.now(timezone.utc).isoformat()
    record["failures"] = [] if completed.returncode == 0 else [f"{SUITE}/attack"]
    (run_root / "smoke_record.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    print(f"[{condition}] {SUITE}/attack rc={completed.returncode}", flush=True)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
