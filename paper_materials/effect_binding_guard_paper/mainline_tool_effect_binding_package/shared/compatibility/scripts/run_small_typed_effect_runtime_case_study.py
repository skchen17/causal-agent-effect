#!/usr/bin/env python3
"""Run 30 local-Qwen call proposals through the frozen typed-effect runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

IMPORT_ROOT = Path(__file__).resolve().parents[3]
if str(IMPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(IMPORT_ROOT))

from shared.compatibility.scripts.independent_authority_benchmark.authority_model import authority_state
from shared.compatibility.scripts.independent_authority_benchmark.specs import descriptor_candidates
from shared.compatibility.scripts.small_typed_effect_runtime_case_study.cases import SCHEMAS, generate_cases
from shared.compatibility.scripts.small_typed_effect_runtime_case_study.local_llm import build_prompt, propose
from shared.compatibility.scripts.small_typed_effect_runtime_case_study.runtime_engine import canonical, evaluate


ROOT = IMPORT_ROOT
EVAL = ROOT / "experiments/human-authority-and-causal-validation/evaluation/small-typed-effect-runtime-case-study"
RESULTS = ROOT / "experiments/human-authority-and-causal-validation/results/small-typed-effect-runtime-case-study"
MODEL_PATH = Path(os.environ.get("TYPED_RUNTIME_MODEL_PATH", "models/Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf"))
MODEL_SHA256 = "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689"


def sha(value: Any) -> str:
    data = value if isinstance(value, bytes) else canonical(value).encode()
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18093/v1")
    parser.add_argument("--model", default="qwen3_32b_local")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force", action="store_true", help="replace this experiment's protocol after preserving a development run")
    args = parser.parse_args()
    cases = generate_cases()
    if args.limit:
        cases = cases[:args.limit]
    descriptors = {item["tool_name"]: item for item in descriptor_candidates()["descriptors"]
                   if item["tool_name"] in SCHEMAS}
    harness_files = [
        Path(__file__),
        ROOT / "shared/compatibility/scripts/small_typed_effect_runtime_case_study/cases.py",
        ROOT / "shared/compatibility/scripts/small_typed_effect_runtime_case_study/local_llm.py",
        ROOT / "shared/compatibility/scripts/small_typed_effect_runtime_case_study/runtime_engine.py",
    ]
    protocol = {
        "protocol": "small-typed-effect-runtime-case-study-v2", "n_cases": len(cases),
        "case_hash": sha(cases), "descriptor_hash": sha(descriptors), "authority_hash": sha(authority_state()),
        "model_file": MODEL_PATH.name, "model_sha256": MODEL_SHA256, "model_role": "structured call proposer only",
        "runtime_llm_calls": 0, "copied_sandbox_only": True, "real_external_side_effects": 0,
        "harness_source_hashes": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                  for path in harness_files},
    }
    EVAL.mkdir(parents=True, exist_ok=True); RESULTS.mkdir(parents=True, exist_ok=True)
    manifest_path = EVAL / ("smoke_protocol_manifest.json" if args.limit else "protocol_manifest.json")
    if manifest_path.exists() and json.loads(manifest_path.read_text()) != protocol and not args.force:
        raise SystemExit("runtime case-study protocol drift")
    write_json(manifest_path, protocol)
    write_jsonl(EVAL / ("smoke_tasks.jsonl" if args.limit else "tasks.jsonl"), cases)
    rows_path = RESULTS / ("smoke_runtime_trajectories.jsonl" if args.limit else "runtime_trajectories.jsonl")
    existing: dict[str, dict[str, Any]] = {}
    if args.resume and rows_path.exists():
        existing = {row["case_id"]: row for row in map(json.loads, rows_path.read_text().splitlines())}
    rows = []
    for case in cases:
        if case["case_id"] in existing:
            old = existing[case["case_id"]]
            refreshed = evaluate(
                case, old.get("proposed_call"), descriptors[case["tool_name"]],
                parse_error=old.get("parse_error"),
            )
            rows.append({**old, **refreshed})
            continue
        prompt = build_prompt(case, SCHEMAS[case["tool_name"]])
        proposed, raw, parse_error = None, None, None
        try:
            proposed, raw = propose(args.base_url, args.model, prompt)
        except Exception as exc:
            parse_error = f"{type(exc).__name__}:{exc}"
        row = evaluate(case, proposed, descriptors[case["tool_name"]], parse_error=parse_error)
        row.update({
            "prompt": prompt, "prompt_hash": sha(prompt.encode()), "raw_model_output": raw,
            "raw_output_hash": sha(raw) if raw is not None else None,
            "state_version_hash": sha(case["pre_state"]), "descriptor_hash": sha(descriptors[case["tool_name"]]),
            "authority_snapshot_hash": sha(authority_state()), "model": args.model,
        })
        rows.append(row)
        write_jsonl(rows_path, rows)
        time.sleep(0.05)
    # Persist deterministic refreshes applied to resumed rows as well.
    write_jsonl(rows_path, rows)
    counts = Counter(row["decision"] for row in rows)
    committed = [row for row in rows if row["executed_call"] is not None]
    report = {
        "status": "passed" if len(rows) == len(cases) and
                                all(row.get("check_use_equal", True) for row in rows) and
                                all(row.get("reconciliation_passed") is True for row in committed) else "failed",
        "n_cases": len(rows), "decision_counts": dict(counts), "coverage": (len(rows) - counts["ABSTAIN"]) / len(rows),
        "n_committed": len(committed), "check_use_failures": sum(row.get("check_use_equal") is False for row in rows),
        "reconciliation_failures": sum(row.get("reconciliation_passed") is False for row in committed),
        "parse_failures": sum(row.get("parse_error") is not None for row in rows),
        "runtime_llm_calls": 0, "real_external_side_effects": 0,
        "scenario_decisions": {scenario: dict(Counter(row["decision"] for row in rows if row["scenario"] == scenario))
                               for scenario in sorted({row["scenario"] for row in rows})},
        "claim_boundary": "Integration case study over copied in-memory tools; the LLM proposes calls but does not decide authority.",
    }
    suffix = "smoke_report" if args.limit else "runtime_case_study_report"
    write_json(RESULTS / f"{suffix}.json", report)
    md = ["# Small Typed-Effect Runtime Case Study", "", f"Status: `{report['status']}`; cases: {len(rows)}.", "",
          f"Decisions: {dict(counts)}. Committed calls: {len(committed)}. Parse failures: {report['parse_failures']}.", "",
          f"Check-use failures: {report['check_use_failures']}; reconciliation failures: {report['reconciliation_failures']}.", "",
          "The model proposes structured calls only. Frozen descriptors and the explicit authority engine make the pre-commit decision.", ""]
    (RESULTS / f"{suffix}.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
