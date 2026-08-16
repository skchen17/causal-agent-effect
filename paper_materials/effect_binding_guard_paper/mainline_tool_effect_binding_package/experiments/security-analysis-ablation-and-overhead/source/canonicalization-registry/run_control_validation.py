#!/usr/bin/env python3
"""Control-set validation runner: 10 pre-registered rules, frozen first.

Pre-registration discipline:
  ``preregistered_control_set.json`` was frozen BEFORE any validation run.
  This runner verifies its sha256 against the sidecar
  ``preregistered_control_set.sha256.txt`` and aborts on mismatch.  The
  pre-registered file is opened read-only; expected verdicts are fixed there
  and never edited here.

Flow:
  1. sha256 verification of the pre-registration file (frozen-first gate).
  2. Build the finite-domain oracle over the frozen 56-call domain; run the
     calibration gate (tools whose effects the model cannot reproduce are
     fail-closed).
  3. For each of the 10 rules, run the counterfactual validation pipeline and
     compare the computed verdict with the pre-registered expected verdict.
  4. Register ACCEPTed rules in the registry and freeze it (frozen hashes
     verified in memory and on the file).
  5. E2 cross-check: visibility/power_set separating pairs from the frozen
     policy-family-sensitivity report (corroborates R07's rejection).
  6. Write JSON + Markdown reports under results/canonicalization-registry/.

Run from the module directory:
  python3 run_control_validation.py
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

from domain_oracle import DomainOracle  # noqa: E402
from paths import (  # noqa: E402
    CONTROL_REPORT_JSON,
    CONTROL_REPORT_MD,
    E2_REPORT,
    FINITE_CONTEXTS,
    PREREG_FILE,
    PREREG_SHA_FILE,
    REGISTRY_FROZEN_JSON,
)
from registry import Registry, sha256_file  # noqa: E402
from validation import ValidationPipeline, VERDICT_ACCEPT  # noqa: E402

EXPECTED_TOTAL_RULES = 10


def verify_preregistration() -> dict:
    """Frozen-first gate: file must match its pre-run sidecar sha256."""
    actual = sha256_file(PREREG_FILE)
    sidecar = PREREG_SHA_FILE.read_text(encoding="utf-8").strip()
    sidecar_hash = sidecar.split()[0] if sidecar else ""
    ok = actual == sidecar_hash
    return {
        "file": str(PREREG_FILE),
        "sha256_actual": actual,
        "sha256_sidecar": sidecar_hash,
        "verified": ok,
    }


def e2_visibility_cross_check() -> dict:
    """Corroborating evidence for R07: visibility qualifier is
    authorization-relevant under the power-set family (E2 report)."""
    if not E2_REPORT.exists():
        return {"found": False, "reason": "E2 report missing"}
    data = json.loads(E2_REPORT.read_text(encoding="utf-8"))
    for row in data.get("grid_rows", []):
        if (
            row.get("domain") == "agentdojo_finite_domain"
            and row.get("qualifier") == "visibility"
            and row.get("family") == "power_set"
        ):
            return {
                "found": True,
                "domain": row.get("domain"),
                "qualifier": row.get("qualifier"),
                "family": row.get("family"),
                "separating_pairs": row.get("separating_pairs"),
                "status": row.get("status"),
                "redundant_pairs": row.get("redundant_pairs"),
                "note": "visibility must distinguish r vs rw (permission is "
                        "authorization-relevant); R07 rejects merging them",
            }
    return {"found": False, "reason": "visibility/power_set row not found"}


def build_markdown(prereg_check: dict, calibration: dict, results: list,
                   summary: dict, registry_info: dict, e2: dict) -> str:
    lines: list[str] = []
    lines.append("# Control-Set Validation Report (effect-preserving canonicalization)")
    lines.append("")
    lines.append(f"- generated_utc: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- platform: {platform.platform()}")
    lines.append(f"- python: {platform.python_version()}")
    lines.append("")
    lines.append("## 1. Pre-registration gate")
    lines.append("")
    lines.append(f"- file: `{prereg_check['file']}`")
    lines.append(f"- sha256 (actual): `{prereg_check['sha256_actual']}`")
    lines.append(f"- sha256 (sidecar): `{prereg_check['sha256_sidecar']}`")
    lines.append(f"- verified (frozen-first): **{prereg_check['verified']}**")
    lines.append("")
    lines.append("## 2. Finite-domain calibration gate")
    lines.append("")
    lines.append(
        f"- tools: {len(calibration['tools'])}; "
        f"calibrated: {len(calibration['calibrated_tools'])} "
        f"({calibration['calibrated_ratio']:.3f} of "
        f"{calibration['n_contexts_total']} contexts)"
    )
    for tool in calibration["tools"]:
        info = calibration["per_tool"][tool]
        lines.append(
            f"  - `{tool}`: calibrated={info['calibrated']} "
            f"(n={info['n_contexts']})"
        )
    lines.append("")
    lines.append("## 3. 10-rule verdict table")
    lines.append("")
    lines.append(
        "| rule | role | transform | expected | verdict | match | evidence | "
        "violations | overmerges |"
    )
    lines.append(
        "|------|------|-----------|----------|---------|-------|----------|"
        "------------|------------|"
    )
    for res in results:
        lines.append(
            f"| {res['rule_id']} | {res['field_role']} | "
            f"{res['transform_name']} | {res['expected']} | {res['verdict']} | "
            f"{'YES' if res['matches_expected'] else 'NO'} | "
            f"{res['evidence_kind']} | {res['violations']} | {res['overmerges']} |"
        )
    lines.append("")
    lines.append(f"**Summary**: {summary['n_matched']}/{summary['n_total']} "
                 f"verdicts match the pre-registered expectations; "
                 f"exact 10/10 = **{summary['exact_10_of_10']}**.")
    lines.append("")
    lines.append("## 4. Frozen registry")
    lines.append("")
    lines.append(f"- file: `{registry_info['path']}`")
    lines.append(f"- accepted rules registered: {registry_info['accepted_rules']}")
    lines.append(f"- n_rules: {registry_info['n_rules']}")
    lines.append(f"- hash verification in memory: {registry_info['verify_in_memory']}")
    lines.append(f"- hash verification on file: {registry_info['verify_on_file']}")
    lines.append("")
    lines.append("## 5. E2 cross-check (R07 corroboration)")
    lines.append("")
    if e2["found"]:
        lines.append(
            f"- visibility / power_set family (agentdojo_finite_domain): "
            f"status={e2['status']}, separating_pairs={e2['separating_pairs']}, "
            f"redundant_pairs={e2['redundant_pairs']}"
        )
        lines.append(f"- note: {e2['note']}")
    else:
        lines.append(f"- not found: {e2.get('reason')}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    t0 = time.time()

    # 1. frozen-first gate
    prereg_check = verify_preregistration()
    if not prereg_check["verified"]:
        print("FATAL: pre-registration sha256 mismatch; refusing to run "
              "(frozen-first discipline).")
        return 1
    print(f"[prereg] verified sha256 {prereg_check['sha256_actual'][:16]}...")

    prereg = json.loads(PREREG_FILE.read_text(encoding="utf-8"))
    oracle = DomainOracle(
        FINITE_CONTEXTS,
        prereg["tool_arg_roles"],
        prereg["oracle_semantics"],
    )
    calibration = oracle.calibration_summary()
    print(f"[oracle] calibration: {len(calibration['calibrated_tools'])}/"
          f"{len(calibration['tools'])} tools calibrated")

    pipeline = ValidationPipeline(oracle)
    results: list[dict] = []
    for rule in prereg["rules"]:
        record = pipeline.validate_rule(rule)
        expected = rule["expected"]
        matches = record["verdict"] == expected
        results.append(
            {
                "rule_id": rule["rule_id"],
                "field_role": rule["field_role"],
                "tool": rule["tool"],
                "transform_name": rule["transform"]["name"],
                "expected": expected,
                "verdict": record["verdict"],
                "matches_expected": matches,
                "evidence_kind": record["evidence_kind"],
                "n_samples": record["n_samples"],
                "n_probes": record["n_probes"],
                "violations": record["violations"],
                "overmerges": record["overmerges"],
                "verdict_reason": record["verdict_reason"],
            }
        )
        print(f"[validate] {rule['rule_id']}: {record['verdict']} "
              f"(expected {expected}) match={matches}")

    n_matched = sum(1 for r in results if r["matches_expected"])
    summary = {
        "n_total": len(results),
        "n_matched": n_matched,
        "exact_10_of_10": n_matched == EXPECTED_TOTAL_RULES == len(results),
    }

    # 4. register accepted rules and freeze
    registry = Registry()
    accepted: list[str] = []
    for rule in prereg["rules"]:
        record = pipeline.validate_rule(rule)
        if record["verdict"] == VERDICT_ACCEPT:
            spec = {k: v for k, v in rule.items() if k != "expected"}
            registry.add_rule(spec, validation_record=record)
            accepted.append(rule["rule_id"])
    registry.save(REGISTRY_FROZEN_JSON)
    verify_in_memory = registry.verify_frozen_hashes()
    verify_on_file = registry.verify_frozen_file(REGISTRY_FROZEN_JSON)
    registry_info = {
        "path": str(REGISTRY_FROZEN_JSON),
        "accepted_rules": accepted,
        "n_rules": len(registry.rules),
        "verify_in_memory": verify_in_memory,
        "verify_on_file": verify_on_file,
    }
    print(f"[registry] accepted={accepted} frozen to {REGISTRY_FROZEN_JSON} "
          f"verify_in_memory={verify_in_memory} verify_on_file={verify_on_file}")

    # 5. E2 cross-check
    e2 = e2_visibility_cross_check()
    print(f"[e2] visibility cross-check found={e2.get('found')}")

    report = {
        "experiment": "canonicalization-control-validation-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(time.time() - t0, 3),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "preregistration": prereg_check,
        "domain": {"path": str(FINITE_CONTEXTS), "n_contexts": len(oracle.rows)},
        "calibration": calibration,
        "results": results,
        "summary": summary,
        "frozen_registry": registry_info,
        "e2_cross_check": e2,
    }
    CONTROL_REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    CONTROL_REPORT_JSON.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    CONTROL_REPORT_MD.write_text(
        build_markdown(prereg_check, calibration, results, summary,
                       registry_info, e2),
        encoding="utf-8",
    )
    print(f"[report] wrote {CONTROL_REPORT_JSON}")
    print(f"[report] wrote {CONTROL_REPORT_MD}")
    print(f"[DONE] control validation: {summary['n_matched']}/"
          f"{summary['n_total']} matched; exact_10_of_10="
          f"{summary['exact_10_of_10']}")
    return 0 if summary["exact_10_of_10"] else 2


if __name__ == "__main__":
    sys.exit(main())
