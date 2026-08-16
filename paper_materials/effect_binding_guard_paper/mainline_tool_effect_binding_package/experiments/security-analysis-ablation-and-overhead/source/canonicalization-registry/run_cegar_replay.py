#!/usr/bin/env python3
"""CEGAR replay runner: M3/M3b failure cases -> induction -> validation.

Replays the failure-driven loop over ``failure_cases_m3.jsonl`` (3 frozen
cases: F-M3-01 double-period artifact, F-M3b-01 sentence-final number,
F-REJ-01 spurious permission-merge candidate) against an initially empty
registry, and writes the convergence report.

Run from the module directory:
  python3 run_cegar_replay.py
CPU-only, stdlib-only; no input file is modified.
"""
from __future__ import annotations

import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cegar import CegarReplay  # noqa: E402
from domain_oracle import DomainOracle  # noqa: E402
from paths import (  # noqa: E402
    CEGAR_REPORT_JSON,
    CEGAR_REPORT_MD,
    FAILURE_CASES_FILE,
    FINITE_CONTEXTS,
    PREREG_FILE,
)
from registry import Registry  # noqa: E402


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def build_markdown(record: dict, calibration: dict, n_expected: int,
                   n_matches: int) -> str:
    lines: list[str] = []
    lines.append("# CEGAR Replay Report (effect-preserving canonicalization)")
    lines.append("")
    lines.append(f"- generated_utc: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- platform: {platform.platform()}")
    lines.append(f"- python: {platform.python_version()}")
    lines.append("")
    lines.append("## 1. Finite-domain calibration gate")
    lines.append("")
    lines.append(
        f"- calibrated tools: {len(calibration['calibrated_tools'])}/"
        f"{len(calibration['tools'])}"
    )
    lines.append("")
    lines.append("## 2. Gate trace")
    lines.append("")
    for step in record["trace"]:
        lines.append(f"### {step['failure_id']}")
        lines.append("")
        lines.append(f"- label: {step.get('case_label')}")
        lines.append(f"- gate1: {step['gate1']['decision']} "
                     f"({step['gate1'].get('classification')})")
        g2 = step.get("gate2", {})
        if g2:
            lines.append(f"- gate2: {g2['decision']} "
                         f"candidate={g2.get('candidate_rule_id')}")
        g3 = step.get("gate3", {})
        if g3:
            lines.append(f"- gate3: verdict={g3['verdict']} "
                         f"(calibrated={g3['calibrated']}, "
                         f"evidence={g3['evidence_kind']})")
        lines.append(f"- action: {step.get('action')}; "
                     f"covered={step.get('covered')}; "
                     f"fail_closed={step.get('fail_closed')}")
        if "matches_expected" in step:
            lines.append(f"- matches expected: {step['matches_expected']}")
        lines.append("")
    lines.append("## 3. Convergence record")
    lines.append("")
    lines.append(f"- n_failures: {record['n_failures']}")
    lines.append(f"- n_covered (rules cover): {record['n_covered']}")
    lines.append(f"- n_registered_rules: {record['n_registered_rules']}")
    lines.append(f"- registered_rule_ids: {record['registered_rule_ids']}")
    lines.append(f"- n_refused (fail-closed): {record['n_refused']}")
    lines.append(f"- registry_n_rules: {record['registry_n_rules']}")
    lines.append(f"- all_failures_disposed: {record['all_failures_disposed']}")
    lines.append(f"- all_failures_covered: {record['all_failures_covered']}")
    lines.append(f"- expected matches: {n_matches}/{n_expected}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    t0 = time.time()
    prereg = json.loads(PREREG_FILE.read_text(encoding="utf-8"))
    oracle = DomainOracle(
        FINITE_CONTEXTS, prereg["tool_arg_roles"], prereg["oracle_semantics"]
    )
    calibration = oracle.calibration_summary()
    print(f"[oracle] calibrated {len(calibration['calibrated_tools'])}/"
          f"{len(calibration['tools'])} tools")

    cases = read_jsonl(FAILURE_CASES_FILE)
    print(f"[cegar] replaying {len(cases)} failure cases")

    replay = CegarReplay(oracle, registry=Registry())
    record = replay.run(cases)

    n_expected = sum(1 for c in cases if c.get("expected") is not None)
    n_matches = sum(
        1 for step in record["trace"] if step.get("matches_expected") is True
    )
    for step in record["trace"]:
        print(
            f"[cegar] {step['failure_id']}: gate1={step['gate1']['decision']} "
            f"gate3={step.get('gate3', {}).get('verdict')} "
            f"action={step.get('action')} covered={step.get('covered')}"
        )

    report = {
        "experiment": "canonicalization-cegar-replay-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(time.time() - t0, 3),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "input_cases": str(FAILURE_CASES_FILE),
        "calibration": calibration,
        "convergence": {
            k: record[k]
            for k in (
                "n_failures", "n_covered", "n_registered_rules",
                "n_refused", "registered_rule_ids", "registry_n_rules",
                "all_failures_disposed", "all_failures_covered",
            )
        },
        "expected_matches": {"n_expected": n_expected, "n_matched": n_matches},
        "trace": record["trace"],
        "registry_frozen_preview": replay.registry.freeze()["rules"],
    }
    CEGAR_REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    CEGAR_REPORT_JSON.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    CEGAR_REPORT_MD.write_text(
        build_markdown(record, calibration, n_expected, n_matches),
        encoding="utf-8",
    )
    print(f"[report] wrote {CEGAR_REPORT_JSON}")
    print(f"[report] wrote {CEGAR_REPORT_MD}")
    print(f"[DONE] disposed {record['n_failures']}/{record['n_failures']}; "
          f"covered {record['n_covered']}/{record['n_failures']}; "
          f"registered={record['registered_rule_ids']}; "
          f"expected matches {n_matches}/{n_expected}")
    return 0 if record["all_failures_disposed"] and n_matches == n_expected else 2


if __name__ == "__main__":
    sys.exit(main())
