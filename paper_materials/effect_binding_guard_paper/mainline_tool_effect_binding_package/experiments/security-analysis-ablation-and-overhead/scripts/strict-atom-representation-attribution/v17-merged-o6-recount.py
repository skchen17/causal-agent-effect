#!/usr/bin/env python3
"""v17 merged O6 recount under the pre-registered case-bound caliber (D6).

Implements EXACTLY the caliber pre-registered in
paper/current-usenix/v17_merged_o6_recount_preregistration_2026-08-05.md
(sha256 pinned below; the script refuses to run if the pre-registration file
changed).  The order of operations is enforced: the pre-registration existed
and was hashed before this script computes anything.

Caliber summary (see the pre-registration for the authoritative text):
  C1 case-bound binding   every audit row is bound to a unified_case_id via
                          section (base/stage concatenation partitions) +
                          segment (task_plan-bounded) + execution-order rules;
  C2 truncation exclusion for the 9 cases T enumerated in merge_manifest
                          selected_rows, the base-section rows are excluded
                          (forensically retained in the file) and the rows of
                          the case's SELECTED repair stage replace them; rows
                          of non-selected stages are excluded as superseded;
  C3 dual caliber         override commits (strict non-ALLOW -> effective
                          ALLOW, with/without execution_attempted) and the
                          diagnostic_uncertainty_override flag are counted
                          separately and never conflated.

Read-only: the merged/base/stage run directories are opened for reading only;
outputs go to results/strict-atom-representation-attribution/merged-o6-recount/.
Python standard library only; CPU-only; no network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)

SCHEMA = "v17-merged-o6-recount/1"
METHOD = "local-ours_e77_effect_diff_runtime"
SUITES = ("workspace", "slack", "travel", "banking")

PREREGISTRATION = ROOT / "paper/current-usenix/v17_merged_o6_recount_preregistration_2026-08-05.md"
PREREGISTRATION_SHA256 = "3e31501496a221cc4c00464cc45283ce5b014a27789c2e690354598b445d3359"  # amendment A2

DEFAULT_MERGED = (
    ROOT
    / "experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/"
    "recovery-normalization-qwen32-full-allow-with-trail-v17-726-r2-context-repaired"
)
OUT_DIR = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "strict-atom-representation-attribution/merged-o6-recount"
)

# Reference numbers, cited as constants (never tuned here):
#   recommendation section 3.3 (theory_experiment_narrative_risk_reduction_...md)
#   naive merged counts of recommendations_analysis_2026-08-05.md section 1.4
REFERENCE_RECOMMENDATION = {
    "source": "theory_experiment_narrative_risk_reduction_recommendations_2026-08-05.md section 3.3",
    "precommit_total": 2707,
    "effective_ALLOW": 2217,
    "effective_DENY": 83,
    "effective_NEEDS_REPLAN": 407,
    "strict_true": 1958,
    "strict_false": 749,
    "override_commit_executed": 259,
    "diagnostic_flag_true": 455,
}
REFERENCE_NAIVE_MERGED = {
    "source": "recommendations_analysis_2026-08-05.md section 1.4 (naive precommit counts)",
    "precommit_total": 2778,
    "effective_ALLOW": 2275,
    "effective_DENY": 91,
    "effective_NEEDS_REPLAN": 412,
    "strict_true": 2000,
    "strict_false": 778,
    "override_commit_executed": 275,
    "diagnostic_flag_true": 481,
}

DISQUALIFYING_TOKENS = (
    "forbidden_field_used",
    "outside_exact_plan",
    "tool_not_in",
    "missing_e77",
    "revision_binding_invalid",
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def message_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(item.get("content", item.get("text", "")))
            if isinstance(item, dict)
            else str(item)
            for item in content
        )
    return str(content)


def text_of_first_user_message(messages: list[Any]) -> str | None:
    for message in messages:
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(
                str(block.get("content", block.get("text", "")))
                if isinstance(block, dict)
                else str(block)
                for block in content
            )
    return None


def is_official_case_payload(payload: dict[str, Any]) -> tuple[bool, str]:
    """Mirror context-repair-v17.py::is_official_case_payload (preregistration C1.1)."""
    suite = str(payload.get("suite_name"))
    user_task_id = str(payload.get("user_task_id"))
    injection_task_id = payload.get("injection_task_id")
    attack_type = payload.get("attack_type")
    if suite not in SUITES:
        return False, "suite_not_official"
    benign_injection = injection_task_id in {None, "none", ""}
    benign_attack = attack_type in {None, "none", ""}
    if benign_injection or benign_attack:
        if user_task_id.startswith("injection_task_"):
            return False, "auxiliary_injection_task_utility_log"
        if not benign_attack:
            return False, "benign_row_with_attack_type"
        return True, "benign"
    if attack_type != "important_instructions":
        return False, "non_official_attack_type"
    return True, "attack"


def case_key_of(payload: dict[str, Any], kind: str) -> str:
    attack = "important_instructions" if kind == "attack" else "none"
    injection = str(payload.get("injection_task_id")) if kind == "attack" else "none"
    return f"{payload.get('suite_name')}:{payload.get('user_task_id')}:{attack}:{injection}"


def iter_section_rows(lines: list[bytes]) -> Iterator[tuple[int, dict[str, Any] | None]]:
    for offset, raw in enumerate(lines):
        text = raw.decode("utf-8", errors="replace").strip()
        if not text:
            continue
        try:
            row = json.loads(text)
        except json.JSONDecodeError:
            yield offset, None
            continue
        yield offset, row if isinstance(row, dict) else None


# ---------------------------------------------------------------------------
# universe + query_hash map (C1)
# ---------------------------------------------------------------------------

def build_universe(logs_root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Return case_key -> case info, plus stats; recompute query_hash per case."""
    universe: dict[str, dict[str, Any]] = {}
    stats = Counter()
    for path in sorted(logs_root.rglob("*.json")):
        stats["files"] += 1
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            stats["unparseable"] += 1
            continue
        official, kind = is_official_case_payload(payload)
        if not official:
            stats["skipped_non_official"] += 1
            continue
        stats["official"] += 1
        key = case_key_of(payload, kind)
        if key in universe:
            raise ValueError(f"duplicate official case_key: {key}")
        query = text_of_first_user_message(payload.get("messages") or [])
        query_hash = hashlib.sha256(query.encode()).hexdigest() if query is not None else None
        universe[key] = {
            "case_key": key,
            "kind": kind,
            "query_hash": query_hash,
            "evaluation_timestamp": payload.get("evaluation_timestamp"),
            "utility": payload.get("utility"),
            "security": payload.get("security"),
            "error": payload.get("error"),
        }
    return universe, dict(stats)


# ---------------------------------------------------------------------------
# sections + segments (C1)
# ---------------------------------------------------------------------------

def verify_concatenation(paths: list[Path], merged: Path) -> tuple[bool, list[int]]:
    """merged audit must be the exact byte concatenation of the given files."""
    merged_bytes = merged.read_bytes()
    parts = [path.read_bytes() for path in paths]
    line_counts = [part.count(b"\n") + (0 if part.endswith(b"\n") or not part else 1) for part in parts]
    return b"".join(parts) == merged_bytes, line_counts


def split_into_lines(data: bytes) -> list[bytes]:
    return data.split(b"\n") if data else []


def segment_section(lines: list[bytes]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split a section into task_plan-bounded segments; return (segments, orphans)."""
    segments: list[dict[str, Any]] = []
    orphans: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for index, raw in enumerate(lines):
        text = raw.decode("utf-8", errors="replace").strip()
        if not text:
            continue
        try:
            row = json.loads(text)
        except json.JSONDecodeError:
            entry = {"section_line": index, "error": "json_decode_error"}
            (orphans if current is None else current["errors"]).append(entry)
            continue
        if not isinstance(row, dict):
            entry = {"section_line": index, "error": "row_not_an_object"}
            (orphans if current is None else current["errors"]).append(entry)
            continue
        if row.get("event") == "task_plan":
            current = {
                "start_line": index,
                "query_hash": row.get("query_hash"),
                "precommit_rows": [],
                "n_events": 0,
                "errors": [],
            }
            segments.append(current)
            continue
        if current is None:
            orphans.append({"section_line": index, "event": row.get("event")})
            continue
        current["n_events"] += 1
        if row.get("event") == "precommit_check":
            current["precommit_rows"].append({"section_line": index, "row": row})
    return segments, orphans


def bind_base_segments(
    segments: list[dict[str, Any]],
    universe: dict[str, dict[str, Any]],
    t_cases: set[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Bind base-section segments to cases (timestamp order); report per group."""
    by_qhash: dict[str, list[dict[str, Any]]] = {}
    for segment in segments:
        by_qhash.setdefault(str(segment["query_hash"]), []).append(segment)
    cases_by_qhash: dict[str, list[str]] = {}
    for key, info in universe.items():
        if info["query_hash"]:
            cases_by_qhash.setdefault(info["query_hash"], []).append(key)
    for qhash in cases_by_qhash:
        cases_by_qhash[qhash].sort(
            key=lambda k: (str(universe[k]["evaluation_timestamp"]), k)
        )

    binding: dict[str, Any] = {}
    warnings: list[dict[str, Any]] = []
    for qhash, segs in by_qhash.items():
        candidates = cases_by_qhash.get(qhash, [])
        group_has_t = any(case in t_cases for case in candidates)
        timestamps = [universe[c]["evaluation_timestamp"] for c in candidates]
        strictly_increasing = all(
            a < b for a, b in zip(timestamps, timestamps[1:])
        ) if len(timestamps) > 1 else True
        counts_match = len(segs) == len(candidates)
        status = "bound"
        if not candidates:
            status = "non_official"
        elif not counts_match or not strictly_increasing:
            status = "fail_closed" if group_has_t else "unattributed_non_t"
        if status == "bound":
            for segment, case_key in zip(segs, candidates):
                segment["bound_case"] = case_key
        elif status == "non_official":
            for segment in segs:
                segment["bound_case"] = None
        else:
            for segment in segs:
                segment["bound_case"] = None
        warnings.append(
            {
                "query_hash_prefix": qhash[:16],
                "n_segments": len(segs),
                "n_candidate_cases": len(candidates),
                "group_has_t_cases": group_has_t,
                "timestamps_strictly_increasing": strictly_increasing,
                "status": status,
                "cases": candidates if len(candidates) <= 8 else candidates[:8] + ["..."],
            }
        )
        if status == "fail_closed":
            raise ValueError(
                f"base binding fail-closed for query_hash {qhash[:16]}: "
                f"{len(segs)} segments vs {len(candidates)} cases, "
                f"strictly_increasing={strictly_increasing} (group contains T cases)"
            )
    return {"groups": warnings}, warnings


def expected_stage_sequence(stage_root: Path, universe: dict[str, dict[str, Any]]) -> list[str]:
    manifest = read_json(stage_root / "protocol_manifest.json")
    sequence: list[str] = []
    for group in manifest.get("rerun_groups", []):
        suite = group["suite"]
        user_task_id = group["user_task_id"]
        if group["mode"] == "benign":
            sequence.append(f"{suite}:{user_task_id}:none:none")
        else:
            for injection in group["injection_task_ids"]:
                sequence.append(
                    f"{suite}:{user_task_id}:important_instructions:{injection}"
                )
    for key in sequence:
        if key not in universe:
            raise ValueError(f"stage rerun case not in official universe: {key}")
    return sequence


def bind_stage_segments(
    segments: list[dict[str, Any]],
    sequence: list[str],
    universe: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Amendment A1: auxiliary (non_official) segments are removed from the
    binding sequence before the count check; official segments must match the
    expected rerun sequence in count, order and query_hash."""
    official_qhashes = {info["query_hash"] for info in universe.values() if info["query_hash"]}
    official_segments = [s for s in segments if s["query_hash"] in official_qhashes]
    auxiliary_segments = [s for s in segments if s["query_hash"] not in official_qhashes]
    for segment in auxiliary_segments:
        segment["bound_case"] = None
    if len(official_segments) != len(sequence):
        raise ValueError(
            f"stage binding fail-closed: {len(official_segments)} official segments "
            f"(+{len(auxiliary_segments)} auxiliary) vs {len(sequence)} expected case runs"
        )
    for segment, case_key in zip(official_segments, sequence):
        expected_hash = universe[case_key]["query_hash"]
        if str(segment["query_hash"]) != expected_hash:
            raise ValueError(
                f"stage binding query_hash mismatch for {case_key}: "
                f"{str(segment['query_hash'])[:16]} != {expected_hash[:16]}"
            )
        segment["bound_case"] = case_key
    return {
        "official_segments": len(official_segments),
        "auxiliary_segments": len(auxiliary_segments),
        "auxiliary_query_hash_prefixes": sorted(
            {str(s["query_hash"])[:16] for s in auxiliary_segments}
        ),
    }


# ---------------------------------------------------------------------------
# metrics (C3 + section 5)
# ---------------------------------------------------------------------------

def final_material(row: dict[str, Any]) -> list[str]:
    material = [str(item) for item in row.get("reasons", []) or []]
    checks = row.get("atom_checks")
    if isinstance(checks, list):
        for check in checks:
            if isinstance(check, dict):
                material.append(str(check.get("check_result", "")))
    return material


def compute_metrics(retained: list[dict[str, Any]]) -> dict[str, Any]:
    effective = Counter()
    guard = Counter()
    strict_bool = Counter()
    cross = Counter()
    reconciliation: list[dict[str, Any]] = []

    override_total = 0
    override_executed = 0
    override_structured = 0
    override_fallback = 0
    override_by_guard = Counter()
    token_violations: list[dict[str, Any]] = []

    flag_total = 0
    flag_strict_allow = 0
    flag_strict_non_allow = 0

    strict_execution = 0
    override_execution = 0
    blocked_no_execution = 0
    allow_without_attempt = 0

    for entry in retained:
        row = entry["row"]
        decision = str(row.get("decision"))
        guard_decision = str(row.get("guard_decision"))
        attempted = bool(row.get("execution_attempted"))
        effective[decision] += 1
        guard[guard_decision] += 1
        strict_flag = row.get("strict_authorization_satisfied")
        strict_bool[str(bool(strict_flag))] += 1
        cross[f"{guard_decision}->{decision}"] += 1
        if isinstance(strict_flag, bool) and strict_flag != (guard_decision == "ALLOW"):
            reconciliation.append(
                {"kind": "strict_flag_mismatch", "case": entry["case_key"]}
            )
        if decision != "ALLOW" and attempted:
            reconciliation.append(
                {"kind": "executed_without_allow", "case": entry["case_key"]}
            )
        if decision == "ALLOW" and not attempted:
            allow_without_attempt += 1

        is_override = decision == "ALLOW" and guard_decision != "ALLOW"
        if is_override:
            override_total += 1
            override_by_guard[guard_decision] += 1
            checks = row.get("atom_checks")
            if isinstance(checks, list) and len(checks) > 0:
                override_structured += 1
            else:
                override_fallback += 1
            if attempted:
                override_executed += 1
                override_execution += 1
            tokens = {
                token
                for token in DISQUALIFYING_TOKENS
                if any(token in text for text in final_material(row))
            }
            if tokens:
                token_violations.append(
                    {"case": entry["case_key"], "tokens": sorted(tokens)}
                )

        if bool(row.get("diagnostic_uncertainty_override")):
            flag_total += 1
            if guard_decision == "ALLOW":
                flag_strict_allow += 1
            else:
                flag_strict_non_allow += 1

        if guard_decision == "ALLOW" and attempted:
            strict_execution += 1
        if not attempted:
            blocked_no_execution += 1

    partition_ok = (
        strict_execution + override_execution + blocked_no_execution == len(retained)
    )
    return {
        "retained_precommit_total": len(retained),
        "effective_decision": dict(effective),
        "guard_decision": dict(guard),
        "strict_authorization_satisfied": {"true": strict_bool["True"], "false": strict_bool["False"]},
        "strict_x_effective": dict(sorted(cross.items())),
        "override_commit": {
            "definition": "decision==ALLOW and guard_decision!=ALLOW",
            "total": override_total,
            "executed_subset": override_executed,
            "structured": override_structured,
            "fallback": override_fallback,
            "by_guard_decision": dict(override_by_guard),
            "disqualifying_token_violations_final_material": token_violations,
            "disqualifying_token_violation_count": len(token_violations),
        },
        "diagnostic_flag": {
            "definition": "diagnostic_uncertainty_override==true (separate caliber; never conflated with commits)",
            "total": flag_total,
            "with_strict_allow": flag_strict_allow,
            "with_strict_non_allow": flag_strict_non_allow,
        },
        "execution_strata": {
            "strict_execution": strict_execution,
            "override_execution": override_execution,
            "blocked_or_no_execution": blocked_no_execution,
            "partition_of_retained_total": partition_ok,
            "effective_allow_without_execution_attempt": allow_without_attempt,
        },
        "reconciliation_violations": reconciliation,
        "reconciliation_violation_count": len(reconciliation),
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--merged-root", default=str(DEFAULT_MERGED))
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    args = parser.parse_args()

    # ---- preregistration gate (order enforcement) --------------------------
    if not PREREGISTRATION.is_file():
        print(f"error: preregistration missing: {PREREGISTRATION}", file=sys.stderr)
        return 2
    prereg_sha = sha256_file(PREREGISTRATION)
    if prereg_sha != PREREGISTRATION_SHA256:
        print(
            "error: preregistration file changed since the caliber was frozen "
            f"({prereg_sha}); amend the preregistration properly and pin the new hash",
            file=sys.stderr,
        )
        return 2

    merged_root = Path(args.merged_root).expanduser().resolve()
    manifest = read_json(merged_root / "merge_manifest.json")
    finalizer_passed = read_json(merged_root / "finalizer-passed.json")
    base_root = Path(manifest["base_run_root"])
    stage_roots = [Path(path) for path in manifest["stage_roots"]]
    selected_rows = manifest["selected_rows"]
    t_cases = {row["case_key"] for row in selected_rows}
    selected_stage_by_case = {row["case_key"]: str(Path(row["stage_root"]).resolve()) for row in selected_rows}

    audits = [base_root / "runtime_audit.jsonl"] + [root / "runtime_audit.jsonl" for root in stage_roots]
    merged_audit = merged_root / "runtime_audit.jsonl"
    concatenation_ok, section_line_counts = verify_concatenation(audits, merged_audit)
    if not concatenation_ok:
        print("error: merged audit is NOT the exact concatenation of base+stage audits", file=sys.stderr)
        return 1

    # ---- universe -----------------------------------------------------------
    universe, universe_stats = build_universe(merged_root / "agentdojo_logs" / METHOD)
    if len(universe) != 726:
        print(f"error: expected 726 official cases, found {len(universe)}", file=sys.stderr)
        return 1
    for key in t_cases:
        if key not in universe:
            print(f"error: T case missing from universe: {key}", file=sys.stderr)
            return 1

    # ---- sections -----------------------------------------------------------
    merged_lines = split_into_lines(merged_audit.read_bytes())
    boundaries: list[tuple[int, int]] = []
    start = 0
    for count in section_line_counts:
        boundaries.append((start, start + count))
        start += count
    section_names = ["S0_base"] + [f"S{i + 1}_{root.name}" for i, root in enumerate(stage_roots)]

    retained: list[dict[str, Any]] = []
    excluded_counts = Counter()
    t_case_detail: dict[str, dict[str, Any]] = {
        key: {"base_rows_excluded": 0, "stage_rows": {}, "retained_rows": 0, "retained_section": None}
        for key in t_cases
    }
    binding_groups: list[dict[str, Any]] = []
    orphans_total = 0

    for section_index, (lo, hi) in enumerate(boundaries):
        section_lines = merged_lines[lo:hi]
        segments, orphans = segment_section(section_lines)
        orphans_total += len(orphans)
        excluded_counts["orphan_lines"] += len(orphans)
        if section_index == 0:
            _, group_warnings = bind_base_segments(segments, universe, t_cases)
            binding_groups.extend(group_warnings)
            for segment in segments:
                case_key = segment.get("bound_case")
                n_rows = len(segment["precommit_rows"])
                if case_key is None:
                    excluded_counts["non_official_segment_rows"] += n_rows
                    continue
                if case_key in t_cases:
                    excluded_counts["excluded_original_truncated"] += n_rows
                    t_case_detail[case_key]["base_rows_excluded"] += n_rows
                    continue
                for row_entry in segment["precommit_rows"]:
                    retained.append(
                        {
                            "case_key": case_key,
                            "section": "S0_base",
                            "global_line": lo + row_entry["section_line"] + 1,
                            "row": row_entry["row"],
                        }
                    )
        else:
            stage_root = stage_roots[section_index - 1]
            sequence = expected_stage_sequence(stage_root, universe)
            stage_binding = bind_stage_segments(segments, sequence, universe)
            binding_groups.append(
                {"section": section_names[section_index], "stage_binding": stage_binding}
            )
            stage_path = str(stage_root.resolve())
            for segment in segments:
                case_key = segment.get("bound_case")
                n_rows = len(segment["precommit_rows"])
                if case_key is None:  # auxiliary injection-utility segment: report, never count
                    excluded_counts["non_official_segment_rows"] += n_rows
                    continue
                t_case_detail[case_key]["stage_rows"][stage_root.name] = n_rows
                if selected_stage_by_case[case_key] == stage_path:
                    for row_entry in segment["precommit_rows"]:
                        retained.append(
                            {
                                "case_key": case_key,
                                "section": section_names[section_index],
                                "global_line": lo + row_entry["section_line"] + 1,
                                "row": row_entry["row"],
                            }
                        )
                    t_case_detail[case_key]["retained_rows"] = n_rows
                    t_case_detail[case_key]["retained_section"] = section_names[section_index]
                else:
                    excluded_counts["excluded_superseded_stage"] += n_rows

    for key, detail in t_case_detail.items():
        if detail["retained_section"] is None:
            print(f"error: T case has no retained segment: {key}", file=sys.stderr)
            return 1

    # ---- integrity cross-check (preregistration C2.3) -----------------------
    s0_precommit_total = 0
    stage_precommit_total = 0
    for section_index, (lo, hi) in enumerate(boundaries):
        for raw in merged_lines[lo:hi]:
            text = raw.decode("utf-8", errors="replace").strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("event") == "precommit_check":
                if section_index == 0:
                    s0_precommit_total += 1
                else:
                    stage_precommit_total += 1
    # Amendment A2: auxiliary (non_official) segment precommit rows are never
    # counted, so the retention arithmetic must subtract them explicitly.
    expected_retained = (
        s0_precommit_total
        - excluded_counts["excluded_original_truncated"]
        + stage_precommit_total
        - excluded_counts["excluded_superseded_stage"]
        - excluded_counts["non_official_segment_rows"]
    )
    if expected_retained != len(retained):
        print(
            "error: retention arithmetic mismatch: "
            f"{expected_retained} expected vs {len(retained)} retained",
            file=sys.stderr,
        )
        return 1

    metrics = compute_metrics(retained)
    integrity_ok = (
        metrics["reconciliation_violation_count"] == 0
        and metrics["execution_strata"]["partition_of_retained_total"]
        and metrics["override_commit"]["disqualifying_token_violation_count"] == 0
    )

    # ---- comparison block (explanation only, never a tuning input) ----------
    def diff_block(reference: dict[str, Any]) -> dict[str, Any]:
        observed = {
            "precommit_total": metrics["retained_precommit_total"],
            "effective_ALLOW": metrics["effective_decision"].get("ALLOW", 0),
            "effective_DENY": metrics["effective_decision"].get("DENY", 0),
            "effective_NEEDS_REPLAN": metrics["effective_decision"].get("NEEDS_REPLAN", 0),
            "strict_true": metrics["strict_authorization_satisfied"]["true"],
            "strict_false": metrics["strict_authorization_satisfied"]["false"],
            "override_commit_executed": metrics["override_commit"]["executed_subset"],
            "diagnostic_flag_true": metrics["diagnostic_flag"]["total"],
        }
        keys = [k for k in reference if k != "source"]
        return {
            "source": reference["source"],
            "items": {
                key: {
                    "reference": reference[key],
                    "observed": observed[key],
                    "delta_observed_minus_reference": observed[key] - reference[key],
                }
                for key in keys
            },
        }

    report = {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "preregistration": {
            "path": str(PREREGISTRATION),
            "sha256": prereg_sha,
            "pinned_sha256": PREREGISTRATION_SHA256,
            "mtime_utc": datetime.fromtimestamp(
                PREREGISTRATION.stat().st_mtime, tz=timezone.utc
            ).isoformat(),
        },
        "inputs": {
            "merged_root": str(merged_root),
            "merge_manifest_sha256": sha256_file(merged_root / "merge_manifest.json"),
            "merge_manifest_plan_hash": manifest.get("plan_hash"),
            "finalizer_passed": finalizer_passed,
            "merged_audit_sha256": sha256_file(merged_audit),
            "section_audits": [
                {"path": str(path), "sha256": sha256_file(path), "lines": count}
                for path, count in zip(audits, section_line_counts)
            ],
            "concatenation_verified": concatenation_ok,
            "universe_stats": universe_stats,
            "t_cases": sorted(t_cases),
            "selected_rows": selected_rows,
        },
        "binding": {"groups": binding_groups, "orphan_lines": orphans_total},
        "exclusions": dict(excluded_counts),
        "t_case_detail": t_case_detail,
        "metrics": metrics,
        "integrity_ok": integrity_ok,
        "comparisons": {
            "recommendation_section_3_3": diff_block(REFERENCE_RECOMMENDATION),
            "naive_merged_counts": diff_block(REFERENCE_NAIVE_MERGED),
        },
        "caveats": [
            "Counts describe the retained precommit rows of the merged audit under the pre-registered caliber; they are not outcome metrics of the V0-V3 experiment.",
            "Override commits and diagnostic flags are separate calibers (C3) and must never be conflated in the paper.",
            "ASR/benign utility/attack utility remain the frozen merged values of p2b_execution_report section 6.1 (11/629, 46/97, 272/629); this recount does not recompute official case outcomes.",
        ],
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "v17-merged-o6-recount.json"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"\n[recount] integrity_ok={integrity_ok} -> {json_path}")
    return 0 if integrity_ok else 1


if __name__ == "__main__":
    sys.exit(main())
