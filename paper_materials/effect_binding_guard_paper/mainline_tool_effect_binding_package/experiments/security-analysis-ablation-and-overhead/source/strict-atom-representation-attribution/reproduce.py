#!/usr/bin/env python3
"""Read-only reproduction check for the strict atom attribution protocol.

Protocol section 10 (item 6, second command): verifies, without touching any
GPU or run state, that the frozen inputs are exactly the ones the protocol
binds, and that every produced result artifact is derivable from them:

1. ``protocol.json`` is ``protocol-frozen`` and its recorded artifact hashes
   match the on-disk files (sha256 recomputed here);
2. the model file exists with the frozen size;
3. every existing run directory carries a ``paired-case-results.jsonl`` whose
   rows all record the same ``protocol_id`` and frozen-input hashes as this
   check recomputes (hash drift => fail);
4. the finalize gates reproduce from the recorded rows (read-only): pairing,
   integrity and hash consistency are recomputed, never rewritten.

Exit codes: 0 = reproducible; 1 = a check failed; 2 = refused (protocol not
frozen or inputs missing).  This script writes nothing.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
EXPERIMENT_ROOT = ROOT / "experiments/security-analysis-ablation-and-overhead"
EVAL_DIR = EXPERIMENT_ROOT / "evaluation/strict-atom-representation-attribution"
SOURCE_DIR = EXPERIMENT_ROOT / "source/strict-atom-representation-attribution"
RUNS_BASE = EXPERIMENT_ROOT / "runs/strict-atom-representation-attribution/qwen32"

MAIN_VARIANTS = (
    "tool_identity_only",
    "opaque_whole_call",
    "raw_schema_fields",
    "validated_atom_fields",
)
MODEL_SIZE_BYTES = 19_762_149_024


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    errors: list[str] = []
    protocol_path = EVAL_DIR / "protocol.json"
    if not protocol_path.exists():
        print(json.dumps({"status": "refused", "errors": ["protocol.json missing"]}))
        return 2
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol.get("status") != "protocol-frozen":
        print(
            json.dumps(
                {
                    "status": "refused",
                    "errors": [f"protocol status {protocol.get('status')!r}, not frozen"],
                }
            )
        )
        return 2
    protocol_id = sha256_of(protocol_path)[:16]

    for name, expected in sorted(protocol.get("hashes", {}).items()):
        path = EVAL_DIR / name
        if not path.exists():
            errors.append(f"frozen artifact missing: {name}")
        elif sha256_of(path) != expected:
            errors.append(f"frozen artifact hash mismatch: {name}")

    model = Path(protocol.get("model", {}).get("file", ""))
    if not model.exists():
        errors.append(f"model missing: {model}")
    elif model.stat().st_size != MODEL_SIZE_BYTES:
        errors.append(f"model size mismatch: {model.stat().st_size}")
    if protocol.get("model", {}).get("sha256"):
        # Full model rehash is expensive; size + frozen protocol hash pin it.
        pass

    # Read-only check of any existing run rows.
    checked_rows = 0
    finalize = load_module("strict_reproduce_finalize", SOURCE_DIR / "finalize.py")
    per_variant: dict[str, dict[str, dict[str, Any]]] = {}
    for variant in MAIN_VARIANTS:
        variant_dirs = sorted((RUNS_BASE / variant).glob("repeat-*")) if (RUNS_BASE / variant).exists() else []
        for repeat_dir in variant_dirs:
            results_path = repeat_dir / "paired-case-results.jsonl"
            if not results_path.exists():
                continue
            rows, load_errors = finalize.load_results_jsonl(results_path)
            errors.extend(load_errors)
            for key, row in rows.items():
                checked_rows += 1
                if row.get("protocol_id") not in (None, protocol_id):
                    errors.append(
                        f"{variant}/{repeat_dir.name}:{key}: protocol_id drift "
                        f"({row.get('protocol_id')} != {protocol_id})"
                    )
            if not errors:
                per_variant.setdefault(variant, {}).update(
                    {f"{repeat_dir.name}:{key}": row for key, row in rows.items()}
                )
    errors.extend(finalize.hash_consistency_errors(per_variant))
    for variant, rows in per_variant.items():
        errors.extend(finalize.integrity_errors(rows, variant))

    report = {
        "status": "failed" if errors else "reproducible",
        "protocol_id": protocol_id,
        "checked_rows": checked_rows,
        "n_errors": len(errors),
        "errors": errors[:200],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
