#!/usr/bin/env python3
"""Build the pre-registered whole-call envelope registry (protocol v2, D4).

Deterministically projects ``frozen-common-plan-cache.json`` into the V1
whole-call authority registry
``evaluation/strict-atom-representation-attribution/whole-call-envelopes.json``
plus a ``.sha256`` sidecar.  The projection rules are implemented in
``whole_call_envelope.py`` and pre-registered in
``whole-call-envelope-registration-rules.md``; the registry hash is written
into ``protocol.json`` (protocol v2) so every later runner verifies it via
``verify_frozen_inputs``.

Determinism: the artifact contains NO wall-clock fields; re-running this
script against unchanged frozen inputs reproduces byte-identical output
(asserted by the ``--check`` mode).

Usage (CPU-only; never starts a GPU server):

    PYTHONPATH=code:. python3 \\
      experiments/security-analysis-ablation-and-overhead/scripts/\\
      strict-atom-representation-attribution/build-whole-call-envelopes.py

    # verify existing artifact instead of rewriting:
    ... build-whole-call-envelopes.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

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

FROZEN_PLAN_CACHE = EVAL_DIR / "frozen-common-plan-cache.json"
RUNTIME_CATALOG = (
    EXPERIMENT_ROOT
    / "evaluation/runtime-mechanism-ablation/agentdojo_runtime_catalog.json"
)
REGISTERED_DESCRIPTORS = (
    ROOT
    / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/"
    / "registered-effect-diff-descriptors.jsonl"
)
OUTPUT_JSON = EVAL_DIR / "whole-call-envelopes.json"
OUTPUT_SHA = EVAL_DIR / "whole-call-envelopes.json.sha256"

REGISTRY_ARTIFACT_TYPE = "whole_call_envelope_registry"
REGISTRY_RULE_VERSION = "whole_call_exact_match_v2"


def _import_projection():
    """Load whole_call_envelope.py by path (hyphenated source directory)."""
    import importlib.util

    if str(ROOT / "code") not in sys.path:
        sys.path.insert(0, str(ROOT / "code"))
    spec = importlib.util.spec_from_file_location(
        "strict_whole_call_envelope", SOURCE_DIR / "whole_call_envelope.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["strict_whole_call_envelope"] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_registry() -> tuple[dict, dict[str, str]]:
    projection = _import_projection()
    from src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.e77_runtime import (
        load_runtime_catalog,
    )

    for path in (FROZEN_PLAN_CACHE, RUNTIME_CATALOG, REGISTERED_DESCRIPTORS):
        if not path.exists():
            raise SystemExit(f"missing frozen input: {path}")

    input_hashes = {
        "frozen-common-plan-cache.json": sha256_file(FROZEN_PLAN_CACHE),
        "agentdojo_runtime_catalog.json": sha256_file(RUNTIME_CATALOG),
        "registered-effect-diff-descriptors.jsonl": sha256_file(
            REGISTERED_DESCRIPTORS
        ),
    }

    plan_cache = json.loads(FROZEN_PLAN_CACHE.read_text(encoding="utf-8"))
    catalog = load_runtime_catalog(RUNTIME_CATALOG)
    descriptor_rows = [
        json.loads(line)
        for line in REGISTERED_DESCRIPTORS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    registered_tools = sorted(
        str(row["tool_name"])
        for row in descriptor_rows
        if row.get("registered")
    )
    if len(registered_tools) != 25:
        raise SystemExit(
            f"expected 25 registered effectful tools, got {len(registered_tools)}"
        )

    projection_result = projection.project_plan_cache(
        plan_cache, registered_tools, catalog
    )
    registry = {
        "artifact_type": REGISTRY_ARTIFACT_TYPE,
        "rule_version": REGISTRY_RULE_VERSION,
        "variant": "opaque_whole_call",
        "protocol_version": "v2",
        "match_rule": "exact_sha256_signature_equality",
        "signature_definitions": {
            "whole_call_signature": (
                'sha256(json.dumps({"tool_name": tool_name, "args": totalized_args}, '
                "sort_keys=True, default=str)) -- identical to the runtime audit "
                "call_signature"
            ),
            "plan_signature": (
                "sha256(json.dumps(plan, sort_keys=True, default=str)) over the "
                "parsed plan object as stored in the frozen plan cache"
            ),
            "totalization": (
                "e77_runtime.totalize_registered_call with the frozen "
                "agentdojo_runtime_catalog.json (identical pipeline to all variants)"
            ),
        },
        "decision_semantics": {
            "ALLOW": "totalized call signature equals a registered envelope signature of the current plan",
            "NEEDS_REPLAN": (
                "plan unavailable, tool not in plan, no registered envelope for "
                "plan/tool, or signature mismatch; feedback is opaque (checks=[])"
            ),
            "DENY": (
                "never emitted by the whole-call comparator; reachable only via "
                "the shared revision-DENY recovery path (identical across variants)"
            ),
        },
        "claim_boundary": (
            "envelopes cover only call shapes statically instantiable from the "
            "frozen plan cache; resolve-bound fields, forbidden-required "
            "conflicts and runtime-revised plans carry no whole-call authority"
        ),
        "inputs": {name: {"sha256": value} for name, value in sorted(input_hashes.items())},
        "registered_tool_names": registered_tools,
        "max_combinations_per_tool_plan": projection.MAX_COMBINATIONS_PER_TOOL_PLAN,
        "summary": projection_result["summary"],
        "envelopes": projection_result["envelopes"],
    }
    return registry, input_hashes


def render(registry: dict) -> bytes:
    return (json.dumps(registry, indent=2, sort_keys=True) + "\n").encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the existing artifact instead of rewriting it",
    )
    args = parser.parse_args(argv)

    registry, _ = build_registry()
    payload = render(registry)
    digest = hashlib.sha256(payload).hexdigest()

    if args.check:
        errors = []
        if not OUTPUT_JSON.exists():
            errors.append(f"missing {OUTPUT_JSON}")
        else:
            existing = OUTPUT_JSON.read_bytes()
            if hashlib.sha256(existing).hexdigest() != digest:
                errors.append("artifact bytes differ from deterministic rebuild")
        if not OUTPUT_SHA.exists():
            errors.append(f"missing {OUTPUT_SHA}")
        else:
            recorded = OUTPUT_SHA.read_text(encoding="utf-8").split()[0]
            if recorded != digest:
                errors.append(f"sidecar sha256 {recorded} != rebuilt {digest}")
        report = {
            "status": "PASS" if not errors else "FAIL",
            "errors": errors,
            "rebuilt_sha256": digest,
            "summary": registry["summary"],
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if not errors else 1

    OUTPUT_JSON.write_bytes(payload)
    OUTPUT_SHA.write_text(
        f"{digest}  {OUTPUT_JSON.name}\n", encoding="utf-8"
    )
    report = {
        "status": "written",
        "artifact": str(OUTPUT_JSON.relative_to(ROOT)),
        "sidecar": str(OUTPUT_SHA.relative_to(ROOT)),
        "sha256": digest,
        "summary": registry["summary"],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
