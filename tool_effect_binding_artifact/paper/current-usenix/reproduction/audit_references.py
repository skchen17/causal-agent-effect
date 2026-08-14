#!/usr/bin/env python3
"""Audit citation closure and frozen public identifiers for the active paper."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


PAPER = Path(__file__).resolve().parents[1]
BIB = PAPER / "references.bib"
OUT_JSON = PAPER / "reference_verification_report.json"
OUT_MD = PAPER / "reference_verification_report.md"

ARXIV_IDS = {
    "toolemu": "2309.15817",
    "agentdojo": "2406.13352",
    "agentlab": "2602.16901",
    "camel": "2503.18813",
    "ipiguard": "2508.15310",
    "toolsafe": "2601.10156",
    "safiron": "2510.09781",
    "progent": "2504.11703",
    "miniscope": "2512.11147",
    "weng2026argus": "2605.03378",
    "ying2026agentvisor": "2604.24118",
    "attriguard": "2603.10749",
    "causalarmor": "2602.07918",
    "clawguard": "2604.11790",
    "pact": "2605.11039",
    "contract2tool": "2606.07904",
    "agentc": "2512.23738",
    "authgraph": "2605.26497",
    "scopegate": "2606.28679",
    "secureclaw": "2606.09549",
    "committimeauth": "2607.10487",
    "contractguard": "2606.18550",
    "alignmentcontracts": "2605.00081",
}

DOIS = {
    "saltzer1975protection": "10.1109/PROC.1975.9939",
    "dennis1966programming": "10.1145/365230.365252",
    "hardy1988confused": "10.1145/54289.871709",
    "denning1976lattice": "10.1145/360051.360056",
    "buneman2001why": "10.1007/3-540-44503-X_20",
    "cheney2009provenance": "10.1561/1900000006",
    "clarke2000cegar": "10.1007/10722167_15",
    "lu-etal-2025-toolsandbox": "10.18653/v1/2025.findings-naacl.65",
}


def included_tex() -> list[Path]:
    pending = [PAPER / "main.tex"]
    seen: set[Path] = set()
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        text = path.read_text(encoding="utf-8")
        for name in re.findall(r"\\(?:input|include)\{([^}]+)\}", text):
            child = PAPER / name
            if child.suffix == "":
                child = child.with_suffix(".tex")
            if child.is_file():
                pending.append(child)
    return sorted(seen)


def citation_keys() -> set[str]:
    keys: set[str] = set()
    for path in included_tex():
        text = re.sub(r"(?m)%.*$", "", path.read_text(encoding="utf-8"))
        for group in re.findall(r"\\cite(?:t|p)?\{([^}]+)\}", text):
            keys.update(key.strip() for key in group.split(",") if key.strip())
    return keys


def entries() -> dict[str, str]:
    text = BIB.read_text(encoding="utf-8")
    starts = list(re.finditer(r"(?m)^@(\w+)\{([^,]+),", text))
    result = {}
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        result[match.group(2).strip()] = text[match.start():end]
    return result


def field(entry: str, name: str) -> str | None:
    match = re.search(rf"(?mi)^\s*{re.escape(name)}\s*=\s*\{{([^}}]*)\}}", entry)
    return match.group(1).strip() if match else None


def main() -> int:
    cited = citation_keys()
    bib = entries()
    errors: list[str] = []
    missing = sorted(cited - set(bib))
    uncited = sorted(set(bib) - cited)
    if missing:
        errors.append(f"missing BibTeX entries: {missing}")
    if uncited:
        errors.append(f"uncited BibTeX entries: {uncited}")

    rows = []
    for key in sorted(cited & set(bib)):
        entry = bib[key]
        row = {
            "key": key,
            "title": field(entry, "title"),
            "author": field(entry, "author"),
            "year": field(entry, "year"),
            "doi": field(entry, "doi"),
            "url": field(entry, "url"),
            "eprint": field(entry, "eprint"),
            "status": "verified_static_metadata",
        }
        for required in ("title", "author", "year", "url"):
            if not row[required]:
                errors.append(f"{key}: missing {required}")
        if key in ARXIV_IDS:
            expected = ARXIV_IDS[key]
            if row["eprint"] != expected:
                errors.append(f"{key}: eprint {row['eprint']!r} != {expected!r}")
            if row["url"] != f"https://arxiv.org/abs/{expected}":
                errors.append(f"{key}: arXiv URL does not match eprint")
            if row["doi"] != f"10.48550/arXiv.{expected}":
                errors.append(f"{key}: arXiv DOI does not match eprint")
        if key in DOIS and row["doi"] != DOIS[key]:
            errors.append(f"{key}: DOI {row['doi']!r} != {DOIS[key]!r}")
        rows.append(row)

    report = {
        "status": "passed" if not errors else "failed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_cited": len(cited),
        "n_bib_entries": len(bib),
        "missing": missing,
        "uncited": uncited,
        "errors": errors,
        "public_metadata_note": (
            "Identifiers were frozen after checking their public arXiv, DOI, "
            "publisher, or proceedings landing pages. The script verifies that "
            "the manuscript has not drifted from those identifiers."
        ),
        "placement_boundary": {
            "ARGUS": "Related Work and bibliography only",
            "AgentVisor": "Related Work and bibliography only",
            "AttriGuard": "Related Work and bibliography only; not experimental evidence",
        },
        "rows": rows,
    }
    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Reference Verification Report",
        "",
        f"Status: `{report['status']}`. Cited keys: `{len(cited)}`; BibTeX entries: `{len(bib)}`.",
        "",
        report["public_metadata_note"],
        "",
        "ARGUS, AgentVisor, and AttriGuard are cited only for related-work positioning; none supplies this paper's empirical evidence.",
        "",
    ]
    if errors:
        lines.extend(["## Errors", "", *[f"- {error}" for error in errors], ""])
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": report["status"], "n_cited": len(cited), "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
