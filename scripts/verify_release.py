#!/usr/bin/env python3
"""Fail-fast integrity and hygiene checks for the curated artifact."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "RELEASE_MANIFEST.json"
REPORT = ROOT / "ANONYMIZATION_REPORT.json"
TEXT_SUFFIXES = {".py", ".md", ".tex", ".bib", ".json", ".jsonl", ".csv", ".txt"}
FORBIDDEN = {
    "api_key_literal": re.compile(r"\bsk-[A-Za-z0-9]{12,}\b"),
    "workspace_path": re.compile(r"/(?:data/CSK|home/user)/"),
    "private_root": re.compile(r"causal-agent-safety-research"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_status(relative: str, expected: str = "passed") -> None:
    payload = json.loads((ROOT / relative).read_text())
    status = payload.get("status")
    if status != expected:
        raise RuntimeError(f"{relative}: expected status={expected!r}, got {status!r}")


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    for row in manifest["files"]:
        path = ROOT / row["path"]
        if not path.is_file():
            raise FileNotFoundError(row["path"])
        if path.stat().st_size != row["bytes"] or sha256(path) != row["sha256"]:
            raise RuntimeError(f"manifest mismatch: {row['path']}")

    violations = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if path in {
            MANIFEST,
            ROOT / "ANONYMIZATION_REPORT.json",
            Path(__file__).resolve(),
        }:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in FORBIDDEN.items():
            if pattern.search(text):
                violations.append(f"{name}: {path.relative_to(ROOT)}")
    if violations:
        raise RuntimeError("release hygiene failures:\n" + "\n".join(violations))

    require_status(
        "experiments/human-authority-and-causal-validation/results/"
        "concrete-atom-authorizer-mechanism/concrete-atom-authorizer-report.json"
    )
    require_status(
        "experiments/security-analysis-ablation-and-overhead/results/"
        "representation-mechanism-attribution/representation-mechanism-attribution-report.json"
    )
    require_status(
        "experiments/security-analysis-ablation-and-overhead/results/"
        "atom-vs-field-semantic-attribution/atom-vs-field-report.json"
    )
    report = {
        "status": "passed",
        "manifest_files": manifest["n_files"],
        "credential_patterns_checked": sorted(FORBIDDEN),
        "violations": [],
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
