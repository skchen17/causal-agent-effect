#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
E60_DIR = ROOT / "evaluation" / "e60_heldout_contract"
REPORTS = ROOT / "reports"
FORBIDDEN_DEPLOYABLE_KEYS = {
    "gold_atom",
    "gold_atoms",
    "gold_label",
    "gold_labels",
    "expected_decision",
    "expected_label",
    "violation_reason",
    "violation_reasons",
    "expanded_atoms",
    "label",
}
CONFIRMED_STATUS = {
    "independently-authored-confirmed",
    "independently-reviewed-confirmed",
    "strict-independent-authorship-certified",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError(f"{path}: line {line_no} is not a JSON object")
                rows.append(row)
    return rows


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().upper() in {"YES", "TRUE", "PASS", "PASSED", "1"}
    return bool(value)


def nested_forbidden_hits(obj: Any, prefix: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if str(key) in FORBIDDEN_DEPLOYABLE_KEYS:
                hits.append(path)
            hits.extend(nested_forbidden_hits(value, path))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            hits.extend(nested_forbidden_hits(value, f"{prefix}[{index}]"))
    return hits


def validate_reviewed_artifacts(packet: dict[str, Any]) -> tuple[bool, list[str]]:
    missing = []
    for artifact in packet.get("reviewed_artifacts") or []:
        if not (ROOT / artifact).exists():
            missing.append(artifact)
    return not missing, missing


def validate_leakage(packet: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    leakage_path = E60_DIR / "leakage_report.json"
    leakage = load_json(leakage_path) if leakage_path.exists() else {}
    review = packet.get("data_separation_review") or {}
    ok = (
        truthy(review.get("leakage_free"))
        and truthy(review.get("leakage_scan_passed"))
        and int(review.get("n_violations", -1)) == 0
        and truthy(leakage.get("leakage_free"))
        and int(leakage.get("n_violations", -1)) == 0
    )
    return ok, {"packet_data_separation_review": review, "artifact_leakage_report": leakage}


def validate_deployable_input() -> tuple[bool, dict[str, Any]]:
    path = E60_DIR / "deployable_inputs.jsonl"
    rows = read_jsonl(path)
    violations = []
    for row in rows:
        hits = nested_forbidden_hits(row)
        if hits:
            violations.append({"case_id": row.get("case_id"), "hits": hits[:20]})
    return not violations, {"n_rows": len(rows), "n_violations": len(violations), "violations": violations[:20]}


def validate_case_integrity(packet: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    review = packet.get("case_integrity_review") or {}
    ok = review.get("case_deletion_after_evaluation") is False
    return ok, review


def validate_required_fields(packet: dict[str, Any]) -> tuple[bool, list[str]]:
    required = [
        "author_anonymous_id",
        "reviewer_anonymous_id",
        "review_date",
        "non_e55_designer_statement",
        "reviewed_artifacts",
        "contract_independence_review",
        "data_separation_review",
        "case_integrity_review",
    ]
    missing = [field for field in required if field not in packet or packet.get(field) in (None, "", [], {})]
    if "review_date" in packet and packet.get("review_date"):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(packet["review_date"])):
            missing.append("review_date:YYYY-MM-DD")
    return not missing, missing


def validate_independence(packet: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    review = packet.get("contract_independence_review") or {}
    domains = review.get("domains") or {}
    checks = {
        "n_cases_at_least_240": int(review.get("n_cases", 0)) >= 240,
        "at_least_three_domains": isinstance(domains, dict) and len(domains) >= 3,
        "tool_names_differ_from_e55": truthy(review.get("tool_names_differ_from_e55")),
        "argument_fields_differ_from_e55": truthy(review.get("argument_fields_differ_from_e55")),
        "uses_e55_schema_names_false": review.get("uses_e55_schema_names") is False,
        "authorization_policy_format_differs_from_e55": truthy(review.get("authorization_policy_format_differs_from_e55")),
        "alias_style_differs_from_e55": truthy(review.get("alias_style_differs_from_e55")),
        "resource_identifiers_differ_from_e55": truthy(review.get("resource_identifiers_differ_from_e55")),
    }
    return all(checks.values()), {"contract_independence_review": review, "checks": checks}


def decide_status(packet: dict[str, Any], checks: dict[str, Any]) -> tuple[str, str]:
    auto_ok = all(
        checks[name]["ok"]
        for name in (
            "required_fields",
            "reviewed_artifacts_exist",
            "leakage_zero",
            "deployable_input_hidden",
            "no_post_evaluation_case_deletion",
            "contract_independence",
        )
    )
    declared = str(packet.get("strict_authorship_status", "")).strip()
    non_e55 = truthy(packet.get("non_e55_designer_statement"))
    author = str(packet.get("author_anonymous_id", "")).strip()
    reviewer = str(packet.get("reviewer_anonymous_id", "")).strip()
    distinct_reviewer = bool(author and reviewer and author != reviewer)
    if auto_ok and non_e55 and declared in CONFIRMED_STATUS:
        if declared == "independently-reviewed-confirmed" and not distinct_reviewer:
            return (
                "blocked-by-external-human-review",
                "Independent review was declared, but author and reviewer anonymous IDs are not distinct.",
            )
        return declared, "Human review packet is complete and automatic artifact checks passed."
    return (
        "blocked-by-external-human-review",
        "Automatic artifact checks may pass, but strict independent authorship/review is not certified by the packet.",
    )


def build_report(result: dict[str, Any]) -> str:
    lines = [
        "# E60 Independent Review Status",
        "",
        f"- Artifact review status: `{result['artifact_review_status']}`.",
        f"- Strict authorship status: `{result['strict_authorship_status']}`.",
        f"- Claim boundary: {result['claim_boundary']}",
        f"- Safe paper wording: {result['safe_paper_wording']}",
        f"- Unsafe until certified: {result['unsafe_until_certified']}",
        "",
        "## Automatic Checks",
        "",
        "| Check | OK | Detail |",
        "|---|---:|---|",
    ]
    for name, check in result["checks"].items():
        detail = check.get("detail")
        if isinstance(detail, (dict, list)):
            detail_text = json.dumps(detail, sort_keys=True)[:240]
        else:
            detail_text = str(detail)
        lines.append(f"| {name} | {check['ok']} | `{detail_text}` |")
    lines += [
        "",
        "This validator does not create or infer an external human reviewer. If the packet does not certify strict independent authorship/review, the manuscript must use `independently specified held-out contract`.",
    ]
    return "\n".join(lines) + "\n"


def validate(packet_path: Path) -> dict[str, Any]:
    packet = load_json(packet_path)
    checks: dict[str, Any] = {}
    ok, detail = validate_required_fields(packet)
    checks["required_fields"] = {"ok": ok, "detail": detail}
    ok, detail = validate_reviewed_artifacts(packet)
    checks["reviewed_artifacts_exist"] = {"ok": ok, "detail": detail}
    ok, detail = validate_leakage(packet)
    checks["leakage_zero"] = {"ok": ok, "detail": detail}
    ok, detail = validate_deployable_input()
    checks["deployable_input_hidden"] = {"ok": ok, "detail": detail}
    ok, detail = validate_case_integrity(packet)
    checks["no_post_evaluation_case_deletion"] = {"ok": ok, "detail": detail}
    ok, detail = validate_independence(packet)
    checks["contract_independence"] = {"ok": ok, "detail": detail}

    strict_status, reason = decide_status(packet, checks)
    artifact_status = "artifact-level-pass" if all(
        checks[name]["ok"]
        for name in (
            "reviewed_artifacts_exist",
            "leakage_zero",
            "deployable_input_hidden",
            "no_post_evaluation_case_deletion",
            "contract_independence",
        )
    ) else "artifact-level-fail"
    if strict_status in CONFIRMED_STATUS:
        claim_boundary = "The paper may describe E60 as an independently authored/reviewed held-out contract, while preserving artifact-bounded scope."
        safe_wording = "We evaluate on a 480-case independently authored/reviewed held-out contract with schema, aliases, resource identifiers, and policies that differ from E55."
    else:
        claim_boundary = "The paper may describe E60 only as an independently specified held-out contract; strict independent authorship/review remains externally uncertified."
        safe_wording = "We evaluate on a 480-case independently specified held-out contract with different tool names, argument fields, schema family, aliases, and authorization policies from E55."
    result = {
        "experiment": "E60",
        "packet_path": display_path(packet_path),
        "artifact_review_status": artifact_status,
        "strict_authorship_status": strict_status,
        "status_reason": reason,
        "claim_boundary": claim_boundary,
        "safe_paper_wording": safe_wording,
        "unsafe_until_certified": "We evaluate on an independently authored held-out contract.",
        "author_anonymous_id": packet.get("author_anonymous_id"),
        "reviewer_anonymous_id": packet.get("reviewer_anonymous_id"),
        "review_date": packet.get("review_date"),
        "non_e55_designer_statement": packet.get("non_e55_designer_statement"),
        "checks": checks,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", default=str(E60_DIR / "independent_author_review_packet.json"))
    parser.add_argument("--output", default=str(E60_DIR / "e60_artifact_level_review.json"))
    parser.add_argument("--report", default=str(REPORTS / "e60_independent_review_status.md"))
    args = parser.parse_args()

    packet_path = Path(args.packet)
    if not packet_path.is_absolute():
        packet_path = ROOT / packet_path
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = ROOT / report_path

    result = validate(packet_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_report(result), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("artifact_review_status", "strict_authorship_status", "status_reason")}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2), file=sys.stderr)
        raise SystemExit(1)
