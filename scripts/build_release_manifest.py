#!/usr/bin/env python3
"""Build a deterministic SHA-256 manifest for the curated release."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "RELEASE_MANIFEST.json"
IGNORED = {OUTPUT, ROOT / "ANONYMIZATION_REPORT.json"}
IGNORED_PARTS = {".git", ".pytest_cache", ".ruff_cache", ".mypy_cache", "__pycache__"}
IGNORED_SUFFIXES = {".aux", ".blg", ".fdb_latexmk", ".fls", ".log", ".out", ".pyc", ".pyo", ".synctex.gz"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    files = []
    for path in sorted(ROOT.rglob("*")):
        if (
            not path.is_file()
            or path in IGNORED
            or any(part in IGNORED_PARTS for part in path.parts)
            or any(path.name.endswith(suffix) for suffix in IGNORED_SUFFIXES)
        ):
            continue
        files.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    payload = {
        "artifact": "tool_effect_binding_research_artifact",
        "claim_boundary": (
            "Finite-domain representation and bounded runtime mediation evidence; "
            "not production safety or a complete authorization system."
        ),
        "n_files": len(files),
        "files": files,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "passed", "n_files": len(files)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
