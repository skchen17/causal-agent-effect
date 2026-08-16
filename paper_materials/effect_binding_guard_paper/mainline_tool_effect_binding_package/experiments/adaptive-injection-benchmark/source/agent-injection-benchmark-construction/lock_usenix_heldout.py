"""Freeze the USENIX held-out public-family attack manifest before evaluation."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "paper").is_dir())
SOURCE = (
    ROOT
    / "experiments/adaptive-injection-benchmark/evaluation/"
    "agent-injection-benchmark-construction/static_case_manifest.jsonl"
)
OUTPUT_DIR = (
    ROOT
    / "experiments/adaptive-injection-benchmark/evaluation/"
    "usenix-heldout-public-families"
)
MANIFEST = OUTPUT_DIR / "locked_manifest.jsonl"
PROTOCOL = OUTPUT_DIR / "protocol.json"
SUITES = ("banking", "slack", "travel", "workspace")
FAMILIES = ("ignore_previous", "injecagent", "important_instructions", "tool_knowledge")
PER_CELL = 20


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def stable_rank(row: dict[str, Any]) -> str:
    identity = "|".join(
        str(row[key])
        for key in ("suite", "agentdojo_attack_name", "user_task_id", "injection_task_id", "case_id")
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def select(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("adaptive_split") != "adaptive_locked_test":
            continue
        key = (str(row.get("suite")), str(row.get("agentdojo_attack_name")))
        if key[0] in SUITES and key[1] in FAMILIES:
            grouped[key].append(row)

    selected: list[dict[str, Any]] = []
    for suite in SUITES:
        for family in FAMILIES:
            candidates = grouped[(suite, family)]
            if len(candidates) < PER_CELL:
                raise RuntimeError(f"insufficient locked rows for {suite}/{family}: {len(candidates)}")
            ranked = sorted(candidates, key=lambda row: (stable_rank(row), row["case_id"]))
            for row in ranked[:PER_CELL]:
                selected.append(
                    {
                        "case_id": row["case_id"],
                        "selection_sha256": stable_rank(row),
                        "suite": suite,
                        "attack_family": family,
                        "user_task_id": row["user_task_id"],
                        "injection_task_id": row["injection_task_id"],
                        "adaptive_split": "adaptive_locked_test",
                        "environment_evaluator": "official_agentdojo_injection_task_validator",
                        "contains_raw_attack_text": False,
                        "no_external_side_effects": True,
                    }
                )
    return selected


def main() -> int:
    rows = read_jsonl(SOURCE)
    selected = select(rows)
    counts = Counter((row["suite"], row["attack_family"]) for row in selected)
    expected = {(suite, family): PER_CELL for suite in SUITES for family in FAMILIES}
    if len(selected) != 320 or dict(counts) != expected:
        raise RuntimeError("held-out selection does not form the required 4x4x20 design")
    if MANIFEST.exists():
        existing = read_jsonl(MANIFEST)
        if existing != selected:
            raise RuntimeError("locked manifest exists with different rows; refusing to overwrite")
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in selected),
            encoding="utf-8",
        )
    manifest_hash = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    protocol = {
        "status": "locked_before_method_evaluation",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_manifest": str(SOURCE.relative_to(ROOT)),
        "source_manifest_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "locked_manifest": str(MANIFEST.relative_to(ROOT)),
        "locked_manifest_sha256": manifest_hash,
        "selection": "lowest SHA-256 of canonical case identity within each suite/family cell",
        "n": len(selected),
        "suites": list(SUITES),
        "attack_families": list(FAMILIES),
        "per_suite_family": PER_CELL,
        "post_result_case_replacement_allowed": False,
        "claim_boundary": "Frozen public AgentDojo attack-family subset; not unrestricted adaptive attack generation.",
    }
    if PROTOCOL.exists():
        old = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        if old.get("locked_manifest_sha256") != manifest_hash:
            raise RuntimeError("existing protocol binds a different manifest")
        protocol["created_at"] = old["created_at"]
    PROTOCOL.write_text(json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(protocol, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
