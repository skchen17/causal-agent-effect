#!/usr/bin/env python3
"""Compile and verify the interface-fix plan-cache seeds (data-level fix, F2).

This script is part of the 2026-08-07 interface-fix package. It does NOT
modify any frozen runtime source: it only reads the frozen v17 runtime
(`e77_runtime.py`) as a library, validates hand-authored seed plans against
the exact same parse/normalize/validate pipeline the runtime uses, verifies
the prompt hashes against the v17 merged-run audit anchors, and writes a
pre-seeded plan-cache JSON plus a verification report.

Run with the E75 AgentDojo venv python (needs `agentdojo` and `openai`):

  experiments/unified-agent-security-baselines/runs/unified-agent-security-comparison/agentdojo-env/bin/python \
    experiments/intent-bound-runtime-guard/scripts/effect-difference-runtime-guard/compile-interface-fix-plan-seeds.py \
    --run-tag deepseek-iffix-20260807

Environment contract (must match run-recovery-normalization-qwen32.py):
  planner material = {"prompt", "max_tokens": E77_PLANNER_MAX_TOKENS (default 4096),
                      "max_repair_attempts": E77_PLANNER_REPAIR_ATTEMPTS (default 2),
                      "version": "effect_binding_plan_normalization_v3"}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Mapping
from typing import Any

HERE = Path(__file__).resolve()
ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *HERE.parents)
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
sys.path.insert(0, str(ROOT / "code"))

from agentdojo.functions_runtime import FunctionsRuntime  # noqa: E402
from agentdojo.task_suite.load_suites import get_suite  # noqa: E402

from src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.e77_runtime import (  # noqa: E402
    build_registry,
    load_relation_catalog,
    normalize_permission_plan_late_bindings,
    normalize_relation_mode_aliases,
    normalize_unsupported_relation_bindings,
    parse_permission_plan_v3_diagnostic,
    planner_prompt_v2,
    read_jsonl,
    validate_permission_plan,
)

EXPERIMENT_ROOT = ROOT / "experiments/intent-bound-runtime-guard"
DESCRIPTOR_JSONL = EXPERIMENT_ROOT / "results/effect-difference-runtime-guard/registered-effect-diff-descriptors.jsonl"
RELATION_CATALOG = EXPERIMENT_ROOT / "evaluation/effect-difference-runtime-guard/registered_relation_catalog.json"
SEEDS_JSON = EXPERIMENT_ROOT / "evaluation/effect-difference-runtime-guard/interface_fix_plan_seeds_v1.json"
CASE_MANIFEST = EXPERIMENT_ROOT / "evaluation/effect-difference-runtime-guard/registered_relation_expanded_pilot_manifest_v17.json"
OUT_DIR = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "strict-atom-representation-attribution/interface-fix-inventory"
)

AGENTDOJO_VERSION = "v1.1.2"
PLANNER_VERSION = "effect_binding_plan_normalization_v3"
MAX_TOKENS = 4096  # runner does not set E77_PLANNER_MAX_TOKENS; patch default is 4096
MAX_REPAIR_ATTEMPTS = 2  # runner sets E77_PLANNER_REPAIR_ATTEMPTS=2


def planner_prompt_hash(prompt: str) -> str:
    material = json.dumps(
        {
            "prompt": prompt,
            "max_tokens": MAX_TOKENS,
            "max_repair_attempts": MAX_REPAIR_ATTEMPTS,
            "version": PLANNER_VERSION,
        },
        sort_keys=True,
    )
    return hashlib.sha256(material.encode()).hexdigest()


def process_seed_plan(payload: Mapping[str, Any], registry: Mapping[str, Mapping[str, Any]], query: str) -> tuple[Any, list[str], list[str]]:
    """Replay the patch's deterministic pipeline on a seed payload."""
    normalized_payload, alias_changes = normalize_relation_mode_aliases(payload)
    plan, parse_errors = parse_permission_plan_v3_diagnostic(normalized_payload, registry)
    normalizations = list(alias_changes)
    if plan is not None:
        plan, relation_normalizations = normalize_unsupported_relation_bindings(plan, registry)
        plan, late_normalizations = normalize_permission_plan_late_bindings(plan, query)
        normalizations.extend(relation_normalizations)
        normalizations.extend(late_normalizations)
    validation_errors = parse_errors or validate_permission_plan(plan, registry, query)
    return plan, validation_errors, normalizations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-tag", required=True, help="Runner run tag whose plan_cache.json will be pre-seeded.")
    parser.add_argument("--write-cache", action="store_true", help="Write the seed plan_cache.json into the run root.")
    args = parser.parse_args()

    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}", args.run_tag):
        raise ValueError("run tag format incompatible with the frozen runner")
    run_root = (
        EXPERIMENT_ROOT
        / "runs/effect-difference-runtime-guard"
        / f"recovery-normalization-qwen32-pilot-36-allow-with-trail-{args.run_tag}"
    )

    seeds_doc = json.loads(SEEDS_JSON.read_text(encoding="utf-8"))
    if seeds_doc.get("status") != "frozen_before_deepseek_interface_fix_pilot_execution":
        raise ValueError("seed document is not frozen")
    manifest = json.loads(CASE_MANIFEST.read_text(encoding="utf-8"))
    manifest_keys = {case["case_key"]: case["stratum"] for case in manifest["cases"]}

    descriptor_rows = read_jsonl(DESCRIPTOR_JSONL)
    relation_catalog = load_relation_catalog(RELATION_CATALOG)
    if relation_catalog.get("version") != seeds_doc["relation_catalog_version"]:
        raise ValueError("seed relation catalog version mismatch")

    registries: dict[str, dict[str, Any]] = {}
    task_texts: dict[str, str] = {}
    for suite_name in sorted({seed["suite"] for seed in seeds_doc["seeds"]}):
        suite = get_suite(AGENTDOJO_VERSION, suite_name)
        registries[suite_name] = build_registry(
            FunctionsRuntime(suite.tools), descriptor_rows, relation_catalog
        )
        for task_id, task in suite.user_tasks.items():
            task_texts[f"{suite_name}/{task_id}"] = getattr(task, "PROMPT", "")

    results: list[dict[str, Any]] = []
    cache: dict[str, Any] = {}
    failures: list[str] = []
    for seed in seeds_doc["seeds"]:
        case_key = seed["case_key"]
        record: dict[str, Any] = {"case_key": case_key}
        try:
            if case_key not in manifest_keys:
                raise ValueError("seed case is not in the frozen 63-case pilot manifest")
            record["manifest_stratum"] = manifest_keys[case_key]
            query = task_texts[case_key]
            if not query:
                raise ValueError("task text unavailable")
            registry = registries[seed["suite"]]
            prompt = planner_prompt_v2(query, registry)
            prompt_hash = planner_prompt_hash(prompt)
            record["prompt_hash"] = prompt_hash
            record["expected_prompt_hash"] = seed["expected_prompt_hash"]
            if prompt_hash != seed["expected_prompt_hash"]:
                raise ValueError(
                    "prompt hash does not match the v17 merged-run audit anchor"
                )
            plan, validation_errors, normalizations = process_seed_plan(
                seed["plan"], registry, query
            )
            record["validation_errors"] = validation_errors
            record["normalizations"] = normalizations
            record["plan_tools"] = sorted(plan["tools"]) if isinstance(plan, dict) else None
            if plan is None or validation_errors:
                raise ValueError(f"seed plan rejected: {validation_errors}")
            if prompt_hash in cache:
                raise ValueError("duplicate prompt hash across seeds")
            cache[prompt_hash] = {
                "plan": plan,
                "diagnostic": {
                    "interface_fix_seed": True,
                    "seed_source": "interface_fix_plan_seeds_v1",
                    "seed_case_key": case_key,
                    "parse_valid": True,
                    "schema_parse_valid": True,
                    "validation_passed": True,
                    "plan_accepted": True,
                    "prompt_hash": prompt_hash,
                },
            }
            record["status"] = "verified"
        except Exception as exc:  # noqa: BLE001
            record["status"] = "failed"
            record["error"] = repr(exc)
            failures.append(f"{case_key}: {exc!r}")
        results.append(record)

    report = {
        "schema": "interface-fix-plan-seed-verification/1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_tag": args.run_tag,
        "run_root": str(run_root.relative_to(ROOT)),
        "constants": {
            "planner_version": PLANNER_VERSION,
            "max_tokens": MAX_TOKENS,
            "max_repair_attempts": MAX_REPAIR_ATTEMPTS,
            "agentdojo_version": AGENTDOJO_VERSION,
            "relation_catalog": str(RELATION_CATALOG.relative_to(ROOT)),
            "descriptor_jsonl": str(DESCRIPTOR_JSONL.relative_to(ROOT)),
        },
        "seeds": results,
        "n_verified": sum(1 for record in results if record["status"] == "verified"),
        "n_seeds": len(results),
        "cache_entries_written": len(cache),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUT_DIR / "interface-fix-plan-seed-verification.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if failures:
        print("[interface-fix-compile] FAIL", file=sys.stderr)
        for failure in failures:
            print("  -", failure, file=sys.stderr)
        print(f"[interface-fix-compile] report -> {report_path}", file=sys.stderr)
        return 1

    if args.write_cache:
        run_root.mkdir(parents=True, exist_ok=True)
        cache_path = run_root / "plan_cache.json"
        if cache_path.exists():
            print(
                f"[interface-fix-compile] refusing to overwrite existing {cache_path}",
                file=sys.stderr,
            )
            return 1
        cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report["cache_path"] = str(cache_path.relative_to(ROOT))
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"[interface-fix-compile] seed cache -> {cache_path}")
    print(f"[interface-fix-compile] {report['n_verified']}/{report['n_seeds']} seeds verified -> {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
