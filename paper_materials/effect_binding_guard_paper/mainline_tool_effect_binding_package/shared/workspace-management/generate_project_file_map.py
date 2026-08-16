#!/usr/bin/env python3
"""Generate a searchable content map for the physical research workspace."""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "PROJECT_FILE_CONTENT_MAP.csv"
SKIP_DIRS = {".git"}


def load_active_sources() -> set[str]:
    audit = ROOT / "paper/current-usenix/submission_source_audit.json"
    if not audit.is_file():
        return set()
    payload = json.loads(audit.read_text(encoding="utf-8"))
    included = {
        f"paper/current-usenix/{path}"
        for path in payload.get("included_sources", [])
    }
    included.update(
        {
            "paper/current-usenix/references.bib",
            "paper/current-usenix/usenix.sty",
        }
    )
    return included


ACTIVE_SOURCES = load_active_sources()


def file_type(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".tar.gz"):
        return "archive"
    suffix = path.suffix.lower()
    return {
        ".py": "python",
        ".pyc": "python-cache",
        ".tex": "latex",
        ".sty": "latex-style",
        ".bib": "bibliography",
        ".md": "markdown",
        ".json": "json",
        ".jsonl": "json-lines",
        ".csv": "csv",
        ".tsv": "tsv",
        ".log": "log",
        ".out": "log",
        ".txt": "text",
        ".sh": "shell",
        ".pdf": "pdf",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
        ".svg": "vector-image",
        ".yaml": "config",
        ".yml": "config",
        ".toml": "config",
        ".lock": "lockfile",
        ".sha256": "checksum",
        ".pkl": "serialized-data",
        ".pickle": "serialized-data",
        ".pt": "model-data",
        ".bin": "binary",
        ".so": "binary-library",
    }.get(suffix, suffix.lstrip(".") or "no-extension")


def path_context(relative: str) -> tuple[str, str, str]:
    parts = Path(relative).parts
    root = parts[0] if len(parts) > 1 else "."
    family = ""
    area = ""
    if root == "experiments":
        family = parts[1] if len(parts) > 1 else ""
        area = parts[2] if len(parts) > 2 else ""
    elif root == "paper":
        family = parts[1] if len(parts) > 1 else ""
        area = parts[2] if len(parts) > 2 else ""
    elif root == "shared":
        family = parts[1] if len(parts) > 1 else ""
        area = parts[2] if len(parts) > 2 else ""
    return root, family, area


def role(relative: str, kind: str) -> tuple[str, str, str]:
    path = Path(relative)
    parts = path.parts
    lowered = relative.lower()

    if path.is_symlink():
        return "compatibility alias", "support", "Top-level compatibility path; canonical data lives at the symlink target."
    if "__pycache__" in parts or ".pytest_cache" in parts or ".ruff_cache" in parts or kind == "python-cache":
        return "cache", "generated", "Generated cache; never use as scientific evidence."
    if "site-packages" in parts or "dist-info" in lowered or "agentlab" in lowered:
        return "external dependency or benchmark copy", "external", "Third-party environment or benchmark material retained for execution compatibility."
    if relative in ACTIVE_SOURCES:
        return "active PDF source", "active", "Included by the current USENIX manuscript build."
    if relative == "paper/current-usenix/main.pdf":
        return "current compiled manuscript", "active-build", "Latest compiled USENIX candidate PDF."
    if relative.startswith("paper/current-usenix/"):
        if "/reproduction/" in relative:
            if kind == "python":
                return "paper reproduction code", "active-support", "Validates, regenerates, or audits current paper claims and artifacts."
            return "paper reproduction artifact", "generated-evidence", "Generated claim ledger, audit report, status, or finalization log."
        if "/artifact/" in relative:
            if kind == "python":
                return "artifact packaging code", "active-support", "Builds or checks the anonymous artifact package."
            return "anonymous artifact output", "generated", "Packaged artifact, manifest, checksum, or anonymization report."
        if relative.endswith(".md"):
            return "paper status or design note", "status-or-history", "Human-readable manuscript status, review, design, or handoff document; check its date before use."
        if kind in {"latex", "latex-style", "bibliography"}:
            return "inactive or pending paper source", "not-in-current-pdf", "Paper source present in the tree but not included by the current main.tex include graph."
        if kind in {"log", "pdf"} or path.name.startswith("main."):
            return "paper build artifact", "generated", "Generated compilation output."
    if relative.startswith("paper/archive/"):
        return "archived manuscript material", "historical", "Historical NDSS or earlier draft; do not use for current claims without re-audit."
    if relative.startswith("paper/compact-usenix/") or relative.startswith("paper/flat-usenix/"):
        return "derived manuscript variant", "derived", "Compact or flattened copy; current authority remains paper/current-usenix."
    if relative.startswith("paper/writing-workspace/"):
        return "PaperSpine writing artifact", "writing-support", "Motivation, evidence, rewrite, style, or logic-transfer planning artifact."
    if relative.startswith("paper/source-materials/") or relative.startswith("paper/assets/"):
        return "paper source material", "support", "Writing package, shared figure/table material, or imported source evidence."
    if relative.startswith("experiments/"):
        area = parts[2] if len(parts) > 2 else ""
        if area == "source":
            return "experiment implementation", "code", "Canonical experiment implementation."
        if area in {"scripts", "baselines"}:
            return "experiment runner or adapter", "code", "Runner, summarizer, audit script, or baseline adapter."
        if area == "tests":
            return "experiment test", "test", "Unit or integration test for the experiment family."
        if area == "evaluation":
            return "evaluation input or manifest", "input", "Frozen dataset, manifest, review packet, schema, or protocol input."
        if area in {"results", "reports", "paper-tables"}:
            if kind in {"json", "json-lines", "csv", "tsv"}:
                return "experiment result artifact", "evidence", "Structured result, prediction, metric, or evidence row."
            return "experiment report or table", "evidence-summary", "Human-readable report, claim boundary, or paper table derived from results."
        if area == "runs":
            return "raw experiment run artifact", "raw-run", "Per-case logs, model cache, environment copy, or intermediate runtime output."
        if path.name == "README.md":
            return "experiment-family guide", "documentation", "Chinese overview of the experiment family's purpose, workflow, and claim boundary."
    if relative.startswith("shared/compatibility/"):
        return "legacy compatibility storage", "compatibility", "Physical target of legacy root aliases; preserves old import and artifact paths."
    if relative.startswith("shared/workspace-management/"):
        return "workspace management", "support", "Workspace migration, packaging, or file-inventory utility."
    if path.name == "README.md":
        return "directory guide", "documentation", "Directory-level orientation and canonical path guidance."
    if kind == "python":
        return "support code", "code", "Python implementation or utility."
    if kind in {"json", "json-lines", "csv", "tsv"}:
        return "structured data", "data", "Structured configuration, manifest, trace, metric, or result data."
    if kind == "markdown":
        return "documentation", "documentation", "Human-readable note or report."
    if kind == "log":
        return "runtime log", "generated", "Generated watcher, build, or process log."
    return "project file", "support", "Project support or generated file."


def iter_entries() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    stack = [ROOT]
    while stack:
        directory = stack.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.name in SKIP_DIRS and entry.is_dir(follow_symlinks=False):
                    continue
                path = Path(entry.path)
                relative = path.relative_to(ROOT).as_posix()
                if entry.is_symlink():
                    root, family, area = path_context(relative)
                    content_role, relevance, description = role(relative, "symlink")
                    rows.append(
                        {
                            "path": relative,
                            "physical_root": root,
                            "family": family,
                            "area": area,
                            "file_type": "symlink",
                            "content_role": content_role,
                            "relevance": relevance,
                            "size_bytes": 0,
                            "modified_time": datetime.fromtimestamp(entry.stat(follow_symlinks=False).st_mtime).isoformat(timespec="seconds"),
                            "symlink_target": os.readlink(path),
                            "description": description,
                        }
                    )
                elif entry.is_dir(follow_symlinks=False):
                    stack.append(path)
                elif entry.is_file(follow_symlinks=False):
                    stat = entry.stat(follow_symlinks=False)
                    kind = file_type(path)
                    root, family, area = path_context(relative)
                    content_role, relevance, description = role(relative, kind)
                    rows.append(
                        {
                            "path": relative,
                            "physical_root": root,
                            "family": family,
                            "area": area,
                            "file_type": kind,
                            "content_role": content_role,
                            "relevance": relevance,
                            "size_bytes": stat.st_size,
                            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                            "symlink_target": "",
                            "description": description,
                        }
                    )
    return sorted(rows, key=lambda row: str(row["path"]))


def main() -> int:
    rows = iter_entries()
    fields = [
        "path",
        "physical_root",
        "family",
        "area",
        "file_type",
        "content_role",
        "relevance",
        "size_bytes",
        "modified_time",
        "symlink_target",
        "description",
    ]
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"status": "passed", "output": str(OUTPUT), "rows": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
