#!/usr/bin/env python3
"""v17 merged benign-utility loss decomposition (read-only, CPU-only, stdlib only).

PURPOSE
  Task A.2 of utility_problem_analysis_and_design (2026-08-06): recompute the
  composition of the 51 failed benign cases of the v17 merged caliber under
  case-bound binding, and produce the auxiliary comparisons needed by the
  report: override-vs-strict utility, interface-finding (manifest/resolver)
  contribution, r1-vs-r2 temperature-0 determinism, and a coarse literal
  resolver-value probe comparable in spirit to the E78-era pathway audit.

CALIBER (frozen in this docstring BEFORE any number below was computed)
  K0  Universe + binding: IDENTICAL to the pre-registered case-bound caliber
      C1/C2 of paper/current-usenix/v17_merged_o6_recount_preregistration_
      2026-08-05.md (amendment A2, pinned sha256 2046eebe...).  This script
      loads the D6 recount module (v17-merged-o6-recount.py) and reuses its
      binding functions unchanged; a merged audit must be the exact byte
      concatenation of base+stage audits, and the same fail-closed rules
      apply.  Nothing is counted that D6 excluded.
  K1  Self-check: the per-case retained rows must (a) sum to 2,657 precommit
      rows and (b) reproduce EXACTLY the D6 recount metrics (effective/guard/
      strict/override/strata counts of v17-merged-o6-recount.json).  If any
      check fails, the script exits nonzero and produces no statistics.
  K2  Official case outcomes come ONLY from the merged agentdojo_logs payload
      fields (utility/security/error), under the same is_official_case_payload
      filter as D6.  Expected anchors: benign 46/97, attack utility 272/629,
      ASR 11/629.  These anchors are verified, never tuned.
  K3  Finding-token predicates (all on retained precommit rows, reason text):
        manifest_parse     reason == "task_permission_plan_parse_failed"
        resolver_finding   reason ends with ": resolver_fill_requires_replan"
        exact_plan_finding reason ends with ": outside_exact_plan"
                           or ": forbidden_field_used"
        tool_not_in        reason starts with "tool_not_in"
        revision_denied    reason == "revision_model_denied_effect"
        replan_invalid     reason == "planner_replan_invalid"
      interface_finding := union of the six predicates.
      runtime_feedback := case segment contains >=1 event of
        {call_revision_feedback, plan_revision, planner_replan}.
      A case "contains" a finding if any of its retained rows matches.
  K4  Benign failure strata (priority order, first match wins), for cases with
      utility == False:
        S0_NO_PRECOMMIT   zero retained precommit rows (guard never engaged)
        S1_FULL_BLOCK     n_attempted == 0 and rows > 0
             - S1a DENY_FULL_BLOCK   if any retained row guard==DENY
             - S1b REPLAN_FULL_BLOCK otherwise
        S2_PARTIAL_BLOCK  0 < n_attempted < n_rows
             - S2a DENY_PARTIAL      if any retained row guard==DENY
             - S2b REPLAN_PARTIAL    otherwise
        S3_ALL_EXECUTED   n_attempted == n_rows > 0
             - S3a ALL_EXEC_OVERRIDE if any override row (decision==ALLOW and
               guard!=ALLOW and execution_attempted)
             - S3b ALL_EXEC_STRICT   otherwise
      Cases in the merge_manifest selected_rows set T are additionally flagged
      truncated_repaired (their rows are the selected-stage rows per C2).
  K5  Override-vs-strict comparison (benign): per-case utility rates within
      (i) cases with >=1 override-execution row, (ii) cases with none.
      Attack side: ASR within cases with >=1 override-execution row vs none,
      and the list of ASR cases containing override rows.
  K6  Literal resolver probe (coarse; case-level, not order-verified): for
      benign cases, parse resolver_finding reasons matching
      "<field>='<value>': resolver_fill_requires_replan"; the case passes the
      probe iff the literal <value> occurs verbatim in any tool-role message
      text of that case's merged log.  This is WEAKER than the E78-era probe
      (which required the value in an EARLIER benign result); report it as
      such.  Literal presence is a diagnostic, not an authorization argument.
  K7  Determinism audit: on the matched official keys of the r1 base run
      (recovery-normalization-qwen32-full-allow-with-trail-v17-726) and the
      r2 base run (...-r2), count case-level utility/security flips for
      benign and attack separately.  Both runs are temperature-0 full runs;
      flips quantify run-to-run nondeterminism, not guard behavior.  The
      merged caliber is NOT used here (repair stages excluded by design:
      we measure base-run reproducibility only).

  All outputs go to
  experiments/security-analysis-ablation-and-overhead/results/
  strict-atom-representation-attribution/utility-loss-decomposition/.
  Inputs (merged/base/stage roots) are opened read-only; nothing is written
  outside the output directory.  No GPU, no network.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *HERE.parents)
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
D6_SCRIPT = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/scripts/"
    "strict-atom-representation-attribution/v17-merged-o6-recount.py"
)
METHOD = "local-ours_e77_effect_diff_runtime"
OUT_DIR = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "strict-atom-representation-attribution/utility-loss-decomposition"
)
R1_BASE = (
    ROOT
    / "experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/"
    "recovery-normalization-qwen32-full-allow-with-trail-v17-726"
)
R2_BASE = (
    ROOT
    / "experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/"
    "recovery-normalization-qwen32-full-allow-with-trail-v17-726-r2"
)

FEEDBACK_EVENTS = {"call_revision_feedback", "plan_revision", "planner_replan"}
RESOLVER_REASON_RE = re.compile(
    r"^(?P<field>[A-Za-z_][A-Za-z_0-9.]*)='(?P<value>.*)': resolver_fill_requires_replan$"
)

EXPECTED = {
    "retained": 2657,
    "benign_utility": (46, 97),
    "attack_utility": (272, 629),
    "asr": (11, 629),
    "d6_metrics": {
        "effective_decision": {"ALLOW": 2180, "DENY": 83, "NEEDS_REPLAN": 394},
        "guard_decision": {"ALLOW": 1921, "DENY": 83, "NEEDS_REPLAN": 653},
        "strict_true": 1921,
        "override_total": 259,
        "override_executed": 259,
        "strict_execution": 1921,
        "override_execution": 259,
        "blocked_no_execution": 477,
    },
}


def load_d6():
    spec = importlib.util.spec_from_file_location("d6_recount", D6_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def reason_tokens(row: dict[str, Any]) -> list[str]:
    return [str(item) for item in row.get("reasons", []) or []]


def case_findings(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "manifest_parse": 0,
        "resolver_finding": 0,
        "exact_plan_finding": 0,
        "tool_not_in": 0,
        "revision_denied": 0,
        "replan_invalid": 0,
    }
    for row in rows:
        for text in reason_tokens(row):
            if text == "task_permission_plan_parse_failed":
                counts["manifest_parse"] += 1
            if text.endswith(": resolver_fill_requires_replan"):
                counts["resolver_finding"] += 1
            if text.endswith(": outside_exact_plan") or text.endswith(
                ": forbidden_field_used"
            ):
                counts["exact_plan_finding"] += 1
            if text.startswith("tool_not_in"):
                counts["tool_not_in"] += 1
            if text == "revision_model_denied_effect":
                counts["revision_denied"] += 1
            if text == "planner_replan_invalid":
                counts["replan_invalid"] += 1
    return counts


def resolver_values(rows: list[dict[str, Any]]) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    for row in rows:
        for text in reason_tokens(row):
            match = RESOLVER_REASON_RE.match(text)
            if match:
                values.append((match.group("field"), match.group("value")))
    return values


def tool_result_text(payload: dict[str, Any]) -> str:
    chunks: list[str] = []
    for message in payload.get("messages") or []:
        if not isinstance(message, dict) or message.get("role") != "tool":
            continue
        content = message.get("content")
        if isinstance(content, str):
            chunks.append(content)
        elif isinstance(content, list):
            chunks.append(
                "".join(
                    str(block.get("content", block.get("text", "")))
                    if isinstance(block, dict)
                    else str(block)
                    for block in content
                )
            )
        elif content is not None:
            chunks.append(str(content))
    return "\n".join(chunks)


def stratum_of(n_rows: int, n_attempted: int, n_deny: int, n_override: int) -> str:
    if n_rows == 0:
        return "S0_NO_PRECOMMIT"
    if n_attempted == 0:
        return "S1a_DENY_FULL_BLOCK" if n_deny else "S1b_REPLAN_FULL_BLOCK"
    if n_attempted < n_rows:
        return "S2a_DENY_PARTIAL" if n_deny else "S2b_REPLAN_PARTIAL"
    return "S3a_ALL_EXEC_OVERRIDE" if n_override else "S3b_ALL_EXEC_STRICT"


def build_retained(d6: Any, merged_root: Path) -> tuple[Any, Any, dict[str, Any]]:
    """Replicate the D6 retention loop; return universe, t_cases and per-case rows."""
    manifest = json.loads((merged_root / "merge_manifest.json").read_text())
    base_root = Path(manifest["base_run_root"])
    stage_roots = [Path(path) for path in manifest["stage_roots"]]
    selected_rows = manifest["selected_rows"]
    t_cases = {row["case_key"] for row in selected_rows}
    selected_stage_by_case = {
        row["case_key"]: str(Path(row["stage_root"]).resolve())
        for row in selected_rows
    }

    audits = [base_root / "runtime_audit.jsonl"] + [
        root / "runtime_audit.jsonl" for root in stage_roots
    ]
    merged_audit = merged_root / "runtime_audit.jsonl"
    ok, section_line_counts = d6.verify_concatenation(audits, merged_audit)
    if not ok:
        raise SystemExit("concatenation verification failed")

    universe, _ = d6.build_universe(merged_root / "agentdojo_logs" / METHOD)
    if len(universe) != 726:
        raise SystemExit(f"expected 726 official cases, found {len(universe)}")

    merged_lines = d6.split_into_lines(merged_audit.read_bytes())
    boundaries: list[tuple[int, int]] = []
    start = 0
    for count in section_line_counts:
        boundaries.append((start, start + count))
        start += count

    rows_by_case: dict[str, list[dict[str, Any]]] = {key: [] for key in universe}
    feedback_by_case: dict[str, int] = {key: 0 for key in universe}
    plan_events_by_case: dict[str, list[dict[str, Any]]] = {
        key: [] for key in universe
    }

    def note_segment(case_key: str | None, segment: dict[str, Any]) -> None:
        if case_key is None or case_key not in rows_by_case:
            return
        for entry in segment["precommit_rows"]:
            rows_by_case[case_key].append(entry["row"])

    for section_index, (lo, hi) in enumerate(boundaries):
        section_lines = merged_lines[lo:hi]
        segments, _orphans = d6.segment_section(section_lines)
        if section_index == 0:
            d6.bind_base_segments(segments, universe, t_cases)
            for segment in segments:
                case_key = segment.get("bound_case")
                if case_key is None:
                    continue
                if case_key in t_cases:
                    continue  # excluded_original_truncated (C2)
                note_segment(case_key, segment)
                _note_events(case_key, section_lines, segment,
                             feedback_by_case, plan_events_by_case)
        else:
            stage_root = stage_roots[section_index - 1]
            sequence = d6.expected_stage_sequence(stage_root, universe)
            d6.bind_stage_segments(segments, sequence, universe)
            stage_path = str(stage_root.resolve())
            for segment in segments:
                case_key = segment.get("bound_case")
                if case_key is None:
                    continue
                if selected_stage_by_case[case_key] != stage_path:
                    continue  # excluded_superseded_stage (C2)
                note_segment(case_key, segment)
                _note_events(case_key, section_lines, segment,
                             feedback_by_case, plan_events_by_case)
    return universe, {
        "t_cases": t_cases,
        "rows_by_case": rows_by_case,
        "feedback_by_case": feedback_by_case,
        "plan_events_by_case": plan_events_by_case,
    }, manifest


def _note_events(
    case_key: str,
    section_lines: list[bytes],
    segment: dict[str, Any],
    feedback_by_case: dict[str, int],
    plan_events_by_case: dict[str, list[dict[str, Any]]],
) -> None:
    start_line = segment["start_line"]
    # segment spans from its task_plan line to the next task_plan (or end);
    # walk forward until we hit the next task_plan row.
    for index in range(start_line, len(section_lines)):
        text = section_lines[index].decode("utf-8", errors="replace").strip()
        if not text:
            continue
        try:
            row = json.loads(text)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        if index > start_line and row.get("event") == "task_plan":
            break
        if row.get("event") in FEEDBACK_EVENTS:
            feedback_by_case[case_key] += 1
        if row.get("event") == "task_plan":
            plan_events_by_case[case_key].append(row)


def verify_d6_reproduction(retained_rows: list[dict[str, Any]]) -> None:
    effective = Counter()
    guard = Counter()
    strict_true = 0
    override_total = override_executed = 0
    strict_execution = override_execution = blocked = 0
    for row in retained_rows:
        decision = str(row.get("decision"))
        guard_decision = str(row.get("guard_decision"))
        attempted = bool(row.get("execution_attempted"))
        effective[decision] += 1
        guard[guard_decision] += 1
        if bool(row.get("strict_authorization_satisfied")):
            strict_true += 1
        is_override = decision == "ALLOW" and guard_decision != "ALLOW"
        if is_override:
            override_total += 1
            if attempted:
                override_executed += 1
        if guard_decision == "ALLOW" and attempted:
            strict_execution += 1
        if is_override and attempted:
            override_execution += 1
        if not attempted:
            blocked += 1
    d6m = EXPECTED["d6_metrics"]
    problems = []
    if len(retained_rows) != EXPECTED["retained"]:
        problems.append(f"retained {len(retained_rows)} != {EXPECTED['retained']}")
    if dict(effective) != d6m["effective_decision"]:
        problems.append(f"effective {dict(effective)}")
    if dict(guard) != d6m["guard_decision"]:
        problems.append(f"guard {dict(guard)}")
    if strict_true != d6m["strict_true"]:
        problems.append(f"strict_true {strict_true}")
    if override_total != d6m["override_total"]:
        problems.append(f"override_total {override_total}")
    if override_executed != d6m["override_executed"]:
        problems.append(f"override_executed {override_executed}")
    if strict_execution != d6m["strict_execution"]:
        problems.append(f"strict_execution {strict_execution}")
    if override_execution != d6m["override_execution"]:
        problems.append(f"override_execution {override_execution}")
    if blocked != d6m["blocked_no_execution"]:
        problems.append(f"blocked {blocked}")
    if problems:
        raise SystemExit("D6 reproduction failed: " + "; ".join(problems))


def determinism_audit(d6: Any) -> dict[str, Any]:
    u1, _ = d6.build_universe(R1_BASE / "agentdojo_logs" / METHOD)
    u2, _ = d6.build_universe(R2_BASE / "agentdojo_logs" / METHOD)
    common = sorted(set(u1) & set(u2))
    result: dict[str, Any] = {
        "r1_cases": len(u1),
        "r2_cases": len(u2),
        "common_cases": len(common),
    }
    for kind in ("benign", "attack"):
        keys = [k for k in common if u1[k]["kind"] == kind]
        utility_flip = security_flip = 0
        flip_examples_u: list[str] = []
        flip_examples_s: list[str] = []
        for key in keys:
            if bool(u1[key]["utility"]) != bool(u2[key]["utility"]):
                utility_flip += 1
                if len(flip_examples_u) < 12:
                    flip_examples_u.append(key)
            if bool(u1[key]["security"]) != bool(u2[key]["security"]):
                security_flip += 1
                if len(flip_examples_s) < 12:
                    flip_examples_s.append(key)
        result[kind] = {
            "n": len(keys),
            "utility_flips": utility_flip,
            "security_flips": security_flip,
            "utility_flip_examples": flip_examples_u,
            "security_flip_examples": flip_examples_s,
        }
    return result


def main() -> int:
    d6 = load_d6()
    merged_root = d6.DEFAULT_MERGED
    universe, bundle, manifest = build_retained(d6, merged_root)
    rows_by_case: dict[str, list[dict[str, Any]]] = bundle["rows_by_case"]
    feedback_by_case: dict[str, int] = bundle["feedback_by_case"]
    plan_events_by_case = bundle["plan_events_by_case"]
    t_cases: set[str] = bundle["t_cases"]

    all_retained = [row for rows in rows_by_case.values() for row in rows]
    verify_d6_reproduction(all_retained)

    # ---- anchor verification (K2) -------------------------------------------
    benign_keys = sorted(k for k, info in universe.items() if info["kind"] == "benign")
    attack_keys = sorted(k for k, info in universe.items() if info["kind"] == "attack")
    benign_success = sum(1 for k in benign_keys if bool(universe[k]["utility"]))
    attack_success = sum(1 for k in attack_keys if bool(universe[k]["utility"]))
    # Repo-native mapping (tests: test_native_security_true_means_attack_success):
    # in these local logs security==True for an attack case == attack succeeded.
    asr_count = sum(1 for k in attack_keys if bool(universe[k]["security"]))
    if (benign_success, len(benign_keys)) != EXPECTED["benign_utility"]:
        raise SystemExit(f"benign anchor mismatch: {benign_success}/{len(benign_keys)}")
    if (attack_success, len(attack_keys)) != EXPECTED["attack_utility"]:
        raise SystemExit(f"attack-utility anchor mismatch: {attack_success}/{len(attack_keys)}")
    if (asr_count, len(attack_keys)) != EXPECTED["asr"]:
        raise SystemExit(f"ASR anchor mismatch: {asr_count}/{len(attack_keys)}")

    # ---- per-case aggregation ------------------------------------------------
    case_records: dict[str, dict[str, Any]] = {}
    for key, info in universe.items():
        rows = rows_by_case[key]
        n_rows = len(rows)
        n_attempted = sum(1 for r in rows if bool(r.get("execution_attempted")))
        n_deny = sum(1 for r in rows if str(r.get("guard_decision")) == "DENY")
        n_override = sum(
            1
            for r in rows
            if str(r.get("decision")) == "ALLOW"
            and str(r.get("guard_decision")) != "ALLOW"
            and bool(r.get("execution_attempted"))
        )
        n_strict_exec = sum(
            1
            for r in rows
            if str(r.get("guard_decision")) == "ALLOW"
            and bool(r.get("execution_attempted"))
        )
        findings = case_findings(rows)
        record = {
            "kind": info["kind"],
            "utility": bool(info["utility"]),
            "security": bool(info["security"]),
            "n_rows": n_rows,
            "n_attempted": n_attempted,
            "n_blocked": n_rows - n_attempted,
            "n_deny": n_deny,
            "n_override_exec": n_override,
            "n_strict_exec": n_strict_exec,
            "findings": findings,
            "interface_finding_rows": sum(findings.values()),
            "runtime_feedback_events": feedback_by_case[key],
            "plan_rejected_events": sum(
                1 for p in plan_events_by_case[key] if not p.get("validation_passed", True)
            ),
            "plan_parse_failed_events": sum(
                1
                for p in plan_events_by_case[key]
                if not p.get("parse_valid", True)
            ),
            "truncated_repaired": key in t_cases,
        }
        if info["kind"] == "benign":
            record["failure_stratum"] = (
                None if record["utility"] else stratum_of(n_rows, n_attempted, n_deny, n_override)
            )
        case_records[key] = record

    # ---- benign failure decomposition (K4) ----------------------------------
    failed_benign = [k for k in benign_keys if not case_records[k]["utility"]]
    stratum_counter = Counter(
        case_records[k]["failure_stratum"] for k in failed_benign
    )
    benign_stratum_utility: dict[str, dict[str, int]] = {}
    for key in benign_keys:
        rec = case_records[key]
        if rec["failure_stratum"] is not None:
            continue
        label = stratum_of(
            rec["n_rows"], rec["n_attempted"], rec["n_deny"], rec["n_override_exec"]
        )
        cell = benign_stratum_utility.setdefault(label, {"n": 0, "utility_true": 0})
        cell["n"] += 1
        cell["utility_true"] += int(rec["utility"])

    findings_in_failed: dict[str, int] = {}
    for name in (
        "manifest_parse",
        "resolver_finding",
        "exact_plan_finding",
        "tool_not_in",
        "revision_denied",
        "replan_invalid",
    ):
        findings_in_failed[name] = sum(
            1 for k in failed_benign if case_records[k]["findings"][name] > 0
        )
    findings_in_failed["interface_finding_any"] = sum(
        1 for k in failed_benign if case_records[k]["interface_finding_rows"] > 0
    )
    findings_in_failed["runtime_feedback_any"] = sum(
        1 for k in failed_benign if case_records[k]["runtime_feedback_events"] > 0
    )
    findings_in_failed["plan_rejected_any"] = sum(
        1 for k in failed_benign if case_records[k]["plan_rejected_events"] > 0
    )
    # same findings across ALL benign (success+fail) for rate comparison
    findings_in_all_benign: dict[str, int] = {}
    for name in (
        "manifest_parse",
        "resolver_finding",
        "exact_plan_finding",
        "tool_not_in",
        "revision_denied",
        "replan_invalid",
        "interface_finding_any",
        "runtime_feedback_any",
        "plan_rejected_any",
    ):
        if name in findings_in_failed:
            key_field = name
            findings_in_all_benign[name] = sum(
                1
                for k in benign_keys
                if (
                    case_records[k]["findings"].get(name, 0) > 0
                    if name in case_records[k]["findings"]
                    else (
                        case_records[k]["interface_finding_rows"] > 0
                        if name == "interface_finding_any"
                        else (
                            case_records[k]["runtime_feedback_events"] > 0
                            if name == "runtime_feedback_any"
                            else case_records[k]["plan_rejected_events"] > 0
                        )
                    )
                )
            )

    # ---- literal resolver probe (K6, benign only) ----------------------------
    probe = {"cases_with_resolver_findings": 0, "cases_probe_pass": 0, "detail": []}
    log_by_case: dict[str, dict[str, Any]] = {}
    for path in sorted((merged_root / "agentdojo_logs" / METHOD).rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue
        official, kind = d6.is_official_case_payload(payload)
        if official:
            log_by_case[d6.case_key_of(payload, kind)] = payload
    for key in failed_benign:
        values = resolver_values(rows_by_case[key])
        if not values:
            continue
        probe["cases_with_resolver_findings"] += 1
        tool_text = tool_result_text(log_by_case[key])
        matched = [f"{field}={value!r}" for field, value in values if value and value in tool_text]
        passed = len(matched) > 0
        if passed:
            probe["cases_probe_pass"] += 1
        probe["detail"].append({"case": key, "n_values": len(values), "passed": passed,
                                "matched_literals": matched[:6]})

    # ---- override vs strict utility (K5) -------------------------------------
    def utility_block(kind: str, metric: str) -> dict[str, Any]:
        keys = benign_keys if kind == "benign" else attack_keys
        with_ov = [k for k in keys if case_records[k]["n_override_exec"] > 0]
        without = [k for k in keys if case_records[k]["n_override_exec"] == 0]
        def rate(subset: list[str]) -> dict[str, Any]:
            n = len(subset)
            if metric == "utility":
                s = sum(1 for k in subset if case_records[k]["utility"])
            else:
                s = sum(1 for k in subset if case_records[k]["security"])
            return {"n": n, "successes": s, "rate": (s / n) if n else None}
        return {"with_override_execution": rate(with_ov),
                "without_override_execution": rate(without),
                "override_cases": with_ov}

    override_utility_benign = utility_block("benign", "utility")
    override_asr_attack = utility_block("attack", "asr")
    asr_cases = [k for k in attack_keys if bool(universe[k]["security"])]
    asr_with_override = [k for k in asr_cases if case_records[k]["n_override_exec"] > 0]

    # ---- determinism audit (K7) ----------------------------------------------
    determinism = determinism_audit(d6)

    report = {
        "schema": "v17-merged-utility-loss-decomposition/1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "merged_root": str(merged_root),
            "r1_base": str(R1_BASE),
            "r2_base": str(R2_BASE),
            "d6_recount_script": str(D6_SCRIPT),
            "t_cases": sorted(t_cases),
        },
        "anchors_verified": {
            "benign_utility": [benign_success, len(benign_keys)],
            "attack_utility": [attack_success, len(attack_keys)],
            "asr": [asr_count, len(attack_keys)],
            "retained_precommit_rows": len(all_retained),
            "d6_metrics_reproduced": True,
        },
        "benign": {
            "n_cases": len(benign_keys),
            "utility_true": benign_success,
            "failed_cases": len(failed_benign),
            "failure_strata": dict(sorted(stratum_counter.items())),
            "stratum_utility_table": benign_stratum_utility,
            "findings_case_counts_in_failed": findings_in_failed,
            "findings_case_counts_in_all_benign": findings_in_all_benign,
            "failed_case_list": [
                {
                    "case": k,
                    "stratum": case_records[k]["failure_stratum"],
                    "n_rows": case_records[k]["n_rows"],
                    "n_attempted": case_records[k]["n_attempted"],
                    "n_deny": case_records[k]["n_deny"],
                    "n_override_exec": case_records[k]["n_override_exec"],
                    "interface_finding_rows": case_records[k]["interface_finding_rows"],
                    "findings": case_records[k]["findings"],
                    "runtime_feedback_events": case_records[k]["runtime_feedback_events"],
                    "plan_rejected_events": case_records[k]["plan_rejected_events"],
                    "truncated_repaired": case_records[k]["truncated_repaired"],
                }
                for k in failed_benign
            ],
        },
        "override_comparison": {
            "benign_utility": override_utility_benign,
            "attack_asr": override_asr_attack,
            "asr_cases": asr_cases,
            "asr_cases_with_override_execution": asr_with_override,
        },
        "literal_resolver_probe": probe,
        "determinism_r1_vs_r2": determinism,
        "caveats": [
            "Finding tokens mark rows whose FINAL reasons contain interface findings; presence is necessary-condition evidence, not causal proof of loss.",
            "The literal resolver probe here is case-level (value anywhere in tool results), weaker than the E78-era earlier-result probe.",
            "r1/r2 flips quantify temperature-0 nondeterminism of the base runs; merged repair stages are excluded from this audit by design.",
            "Strata are computed on retained rows only (case-bound caliber C1/C2); rows excluded by D6 are excluded here.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "v17-merged-utility-loss-decomposition.json"
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"\n[loss-decomposition] ok -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
