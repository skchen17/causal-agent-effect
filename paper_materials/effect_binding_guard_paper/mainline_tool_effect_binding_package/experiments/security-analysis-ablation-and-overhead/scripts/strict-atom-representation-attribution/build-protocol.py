#!/usr/bin/env python3
"""Build and validate the strict-atom-representation-attribution protocol.

Phase 0/1 CLI. `--build-manifests` enumerates the 726 official AgentDojo
v1.1.2 case keys (never from run logs), derives the 160-case stability subset
and the 16-case smoke subset, and builds the V2 raw-schema-field registry.
`--freeze` writes `protocol.json` and refuses to run until the v17 run has
passed its finalizer.

`--freeze` reads the finalizer marker and the plan cache from the v17 run
root.  The run root is resolved in this order of precedence:

    1. `--run-root <path>`            (explicit CLI argument)
    2. `V17_RUN_ROOT` environment variable
    3. built-in default: the r1 run directory
       (`recovery-normalization-qwen32-full-allow-with-trail-v17-726`),
       kept for backward compatibility.

Point `--run-root` at the r2 run directory
(`recovery-normalization-qwen32-full-allow-with-trail-v17-726-r2`) or at a
context-repaired merged directory before freezing; freezing against a run
that has not passed its finalizer is refused (fail-closed, exit 2).

Usage (in repo root, with the e75 env):

    runs/e75_agentdojo_env/bin/python \\
      experiments/security-analysis-ablation-and-overhead/scripts/\\
      strict-atom-representation-attribution/build-protocol.py --build-manifests

    runs/e75_agentdojo_env/bin/python \\
      experiments/security-analysis-ablation-and-overhead/scripts/\\
      strict-atom-representation-attribution/build-protocol.py --freeze

    # freeze against the r2 run (or a context-repaired merged directory):
    runs/e75_agentdojo_env/bin/python \\
      experiments/security-analysis-ablation-and-overhead/scripts/\\
      strict-atom-representation-attribution/build-protocol.py \\
      --freeze --run-root experiments/intent-bound-runtime-guard/runs/\\
      effect-difference-runtime-guard/\\
      recovery-normalization-qwen32-full-allow-with-trail-v17-726-r2
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[4]
SOURCE_DIR = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/source/"
    / "strict-atom-representation-attribution"
)


def _load_source_module(module_name: str, file_name: str) -> ModuleType:
    """Load a module from an absolute file path.

    The protocol directory name contains hyphens (protocol section 8), so it
    cannot be imported as a package; loading by file avoids sys.path pollution
    and collisions with other modules named `protocol`.
    """
    path = SOURCE_DIR / file_name
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolve class modules through sys.modules; register first.
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


proto = _load_source_module("strict_attribution_protocol", "protocol.py")
semantics = _load_source_module("strict_attribution_variant_semantics", "variant_semantics.py")

EVAL_DIR = ROOT / proto.EVALUATION_DIR
# Built-in default run root: the r1 v17 run (backward compatible).  The freeze
# chain must point at the run whose plan cache is the protocol input (r2, or a
# context-repaired merged directory); use --run-root / V17_RUN_ROOT for that.
DEFAULT_V17_RUN_ROOT = (
    ROOT
    / "experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/"
    / "recovery-normalization-qwen32-full-allow-with-trail-v17-726"
)


def resolve_v17_run_root(cli_value: str | None) -> Path:
    """Resolve the v17 run root: --run-root > $V17_RUN_ROOT > r1 default."""
    if cli_value:
        return Path(cli_value).expanduser().resolve()
    env_value = os.environ.get("V17_RUN_ROOT", "").strip()
    if env_value:
        return Path(env_value).expanduser().resolve()
    return DEFAULT_V17_RUN_ROOT
RUNTIME_CATALOG = ROOT / "experiments/security-analysis-ablation-and-overhead/evaluation/runtime-mechanism-ablation/agentdojo_runtime_catalog.json"
REGISTERED_DESCRIPTORS = ROOT / "experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/registered-effect-diff-descriptors.jsonl"


def _load_suites(benchmark_version: str) -> dict[str, object]:
    from agentdojo.task_suite.load_suites import get_suites

    return get_suites(benchmark_version)


def build_manifests(benchmark_version: str) -> int:
    suites = _load_suites(benchmark_version)
    all_cases = proto.enumerate_official_cases(suites)
    check = proto.validate_official_manifest(all_cases)
    if not check["valid"]:
        print(json.dumps(check, indent=2))
        return 1

    stability = proto.select_stability_subset(all_cases)
    stability_check = proto.validate_stability_subset(stability)
    smoke = proto.select_smoke_subset(all_cases)
    smoke_check = proto.validate_smoke_subset(smoke)
    if not stability_check["valid"] or not smoke_check["valid"]:
        print(json.dumps({"stability": stability_check, "smoke": smoke_check}, indent=2))
        return 1

    proto.write_jsonl(EVAL_DIR / "all-official-cases.jsonl", all_cases)
    proto.write_jsonl(EVAL_DIR / "stability-subset.jsonl", stability)
    proto.write_jsonl(EVAL_DIR / "smoke-subset.jsonl", smoke)

    # Variant contracts (protocol section 4): frozen semantics per variant.
    variant_contracts = {
        "variants": [
            {
                "variant": "V0",
                "id": "tool_identity_only",
                "role": "control",
                "contract": (
                    "Check only whether the tool name appears in the initial plan; "
                    "no parameter, effect-role, provenance, or evidence checks."
                ),
            },
            {
                "variant": "V1",
                "id": "opaque_whole_call",
                "contract": (
                    "Instantiate the totalized call against the authority envelope and "
                    "emit exactly one call-level match/mismatch; no per-field decision, "
                    "no per-target expansion, no role-specific repair."
                ),
            },
            {
                "variant": "V2",
                "id": "raw_schema_fields",
                "contract": (
                    "Every official schema parameter is a security_field with role "
                    "untyped_argument; unknown parameters fail closed."
                ),
            },
            {
                "variant": "V3",
                "id": "validated_atom_fields",
                "contract": (
                    "Counterfactually registered security_fields, field_roles and "
                    "effect_kind; list targets expanded per descriptor semantics; "
                    "non-security fields never block authority."
                ),
            },
            {
                "variant": "V4",
                "id": "shuffled_roles",
                "role": "diagnostic_optional",
                "contract": (
                    "V3 with roles rotated by a fixed seed; executed only if a semantic "
                    "influence test shows roles change behavior, else non_applicable."
                ),
            },
        ],
        "common_inputs": {
            "same_25_tool_names": True,
            "same_frozen_plan_cache": True,
            "same_totalization": True,
            "same_recovery_policy": True,
            "same_scorer": True,
        },
    }
    (EVAL_DIR / "variant-contracts.json").write_text(
        json.dumps(variant_contracts, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    # Artifact hashes for everything that exists today (plan cache is frozen
    # only in the freeze step, never here).
    hashable = [
        EVAL_DIR / name
        for name in (
            "all-official-cases.jsonl",
            "stability-subset.jsonl",
            "smoke-subset.jsonl",
            "raw-schema-field-registry.jsonl",
            "variant-contracts.json",
        )
    ]
    hashable += [RUNTIME_CATALOG, REGISTERED_DESCRIPTORS]
    artifact_hashes = proto.artifact_hashes(hashable)
    (EVAL_DIR / "artifact-hashes.json").write_text(
        json.dumps(artifact_hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    # V2 raw-schema-field registry (25 tools, same set as V3).
    catalog = json.loads(RUNTIME_CATALOG.read_text(encoding="utf-8"))
    registered = [json.loads(line) for line in REGISTERED_DESCRIPTORS.read_text(encoding="utf-8").splitlines() if line.strip()]
    v3_tools = sorted(row["tool_name"] for row in registered if row.get("registered"))
    v2_registry = semantics.build_v2_raw_schema_registry(catalog, v3_tools)
    v3_registry = {row["tool_name"]: row for row in registered if row.get("registered")}
    alignment_errors = semantics.validate_v2_v3_tool_set_alignment(v2_registry, v3_registry, v3_tools)
    if alignment_errors:
        print("tool-set alignment errors:", alignment_errors)
        return 1
    proto.write_jsonl(EVAL_DIR / "raw-schema-field-registry.jsonl", [v2_registry[name] for name in v3_tools])

    manifest_summary = {
        "experiment": "strict_atom_representation_attribution",
        "artifact_type": "protocol_manifests",
        "benchmark_version": benchmark_version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "manifests_built_not_frozen",
        "counts": {
            "official": len(all_cases),
            "benign": sum(1 for r in all_cases if r["mode"] == "benign"),
            "attack": sum(1 for r in all_cases if r["mode"] == "attack"),
            "stability": len(stability),
            "smoke": len(smoke),
        },
        "suite_counts": dict(proto.SUITE_COUNTS),
        "v2_registry_tools": len(v2_registry),
        "variant_contracts": len(variant_contracts["variants"]),
        "artifact_hashes_written": sorted(artifact_hashes),
    }
    (EVAL_DIR / "manifests-summary.json").write_text(
        json.dumps(manifest_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest_summary, indent=2))
    return 0


def freeze(run_root: Path) -> int:
    # v17 must have completed and passed its finalizer before freezing.
    marker = run_root / "finalizer-passed.json"
    plan_cache = run_root / "plan_cache.json"
    if not marker.exists() or not plan_cache.exists():
        print(
            f"freeze refused: v17 finalizer marker missing "
            f"({marker} or {plan_cache} not present); the running plan cache "
            "is not a protocol input; resolved run root: "
            f"{run_root} (override with --run-root or V17_RUN_ROOT)",
            file=sys.stderr,
        )
        return 2
    manifests = {
        name: EVAL_DIR / name
        for name in ("all-official-cases.jsonl", "stability-subset.jsonl", "smoke-subset.jsonl", "raw-schema-field-registry.jsonl")
    }
    missing = [str(path) for path in manifests.values() if not path.exists()]
    if missing:
        print("freeze refused: missing manifests:", missing, file=sys.stderr)
        return 2

    # Physical read-only copy of the frozen plan cache for the variants.
    frozen_cache = EVAL_DIR / "frozen-common-plan-cache.json"
    frozen_cache.write_bytes(plan_cache.read_bytes())

    frozen = {
        "experiment": "strict_atom_representation_attribution",
        "artifact_type": "frozen_protocol",
        "status": "protocol-frozen",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "model": {
            "file": "/data/CSK/causal-agent-safety-research/models/Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf",
            "sha256": "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689",
        },
        "benchmark_version": "v1.1.2",
        "hashes": {
            name: proto.sha256_file(path)
            for name, path in {**manifests, "frozen-common-plan-cache.json": frozen_cache}.items()
        },
    }
    (EVAL_DIR / "protocol.json").write_text(
        json.dumps(frozen, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(frozen, indent=2))
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-version", default="v1.1.2")
    parser.add_argument("--build-manifests", action="store_true")
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument(
        "--run-root",
        default=None,
        help=(
            "v17 run directory that --freeze reads finalizer-passed.json and "
            "plan_cache.json from. Precedence: --run-root > $V17_RUN_ROOT > "
            "built-in r1 default "
            "(recovery-normalization-qwen32-full-allow-with-trail-v17-726). "
            "Point this at the r2 run directory or at a context-repaired "
            "merged directory before freezing."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.build_manifests:
        return build_manifests(args.benchmark_version)
    if args.freeze:
        run_root = resolve_v17_run_root(args.run_root)
        return freeze(run_root)
    print("no action selected (use --build-manifests or --freeze)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
