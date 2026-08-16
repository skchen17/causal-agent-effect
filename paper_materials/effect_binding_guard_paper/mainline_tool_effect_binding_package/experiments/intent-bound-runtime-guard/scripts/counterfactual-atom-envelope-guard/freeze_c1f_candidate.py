#!/usr/bin/env python3
"""Freeze the strict structured-provenance C1f repair before live regression."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "paper").is_dir() and (parent / "experiments").is_dir()
)
EVAL = ROOT / "experiments/intent-bound-runtime-guard/evaluation/counterfactual-atom-envelope-guard"
RESULTS = ROOT / "experiments/intent-bound-runtime-guard/results/counterfactual-atom-envelope-guard"
FILES = {
    "policy": ROOT / "code/shadow_atom_envelope_c1f/src/experiments/effect_binding_guard/"
    "e77_effect_diff_runtime_guard/atom_envelope_policy.py",
    "runtime_patch": ROOT / "code/shadow_atom_envelope_c1f/src/experiments/effect_binding_guard/"
    "e77_effect_diff_runtime_guard/agentdojo_e77_runtime_patch.py",
    "registered_descriptors": ROOT / "experiments/intent-bound-runtime-guard/results/"
    "effect-difference-runtime-guard/registered-effect-diff-descriptors.jsonl",
    "runtime_catalog": ROOT / "experiments/security-analysis-ablation-and-overhead/"
    "evaluation/runtime-mechanism-ablation/agentdojo_runtime_catalog.json",
    "relation_catalog": ROOT / "experiments/intent-bound-runtime-guard/evaluation/"
    "effect-difference-runtime-guard/registered_relation_catalog.json",
    "benign_confirmation": RESULTS / "deepseek_c1b_benign_confirmation.json",
    "retrospective_interception": RESULTS / "observed_trajectory_interception_report_c1f.json",
    "strict_policy_tests": ROOT / "shared/compatibility/tests/tests/"
    "test_counterfactual_atom_envelope_policy.py",
    "structured_provenance_tests": ROOT / "shared/compatibility/tests/tests/"
    "test_counterfactual_atom_envelope_structured_provenance.py",
    "known_regression_log": ROOT / "experiments/intent-bound-runtime-guard/runs/"
    "counterfactual-atom-envelope-guard/deepseek-confirmation-c1d-attack-r1/"
    "workspace/agentdojo_logs/local-ours_e77_effect_diff_runtime/workspace/"
    "user_task_8/important_instructions/injection_task_2.json",
}


def digest(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    benign = json.loads(FILES["benign_confirmation"].read_text(encoding="utf-8"))
    replay = json.loads(FILES["retrospective_interception"].read_text(encoding="utf-8"))
    if benign.get("status") != "passed" or benign.get("direct_guard_blocks") != 0:
        raise RuntimeError("benign path evidence is not eligible for C1f freezing")
    metrics = replay["metrics"]
    if metrics["successful_benign_would_block"] != 0:
        raise RuntimeError("C1f retrospectively blocks a successful benign trajectory")
    artifact = {
        "status": "frozen_before_c1f_live_regression",
        "candidate": "C1f_strict_structured_provenance_atom_envelope",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "mechanism": {
            "authority_fields": (
                "Hard-taint every field classified as security-relevant by the frozen "
                "counterfactual descriptor."
            ),
            "payload_fields": (
                "Use the strict C1b treatment: a security-relevant payload field remains "
                "binding when its concrete value is supplied by untrusted control text."
            ),
            "effect_grounding": (
                "Reject an untrusted-requested effect that is not grounded by the original "
                "task under the frozen C1b effect relation."
            ),
            "runtime_llm_calls": 0,
            "structured_provenance": (
                "Traverse mappings, sequences, dataclasses, Pydantic-like records, "
                "and marker-bearing object strings before extracting control segments."
            ),
        },
        "development_evidence": {
            "benign_no_guard_successes": benign["no_guard_successes"],
            "benign_c1b_successes": benign["c1b_successes"],
            "benign_mean_difference": benign["mean_difference"],
            "benign_lower_95": benign["cluster_bootstrap"]["one_sided_lower_95"],
            "benign_path_equivalence_basis": (
                "C1f changes only extraction of explicit untrusted-control segments from "
                "structured outputs; the four-repetition benign audit observed none and "
                "the retrospective benign replay blocks no successful trajectory."
            ),
            "retrospective_attack_cases": metrics["attack_cases"],
            "retrospective_successful_attacks": metrics["official_attack_successes"],
            "retrospective_successful_attacks_intercepted": metrics[
                "successful_attack_trajectories_intercepted"
            ],
            "retrospective_attack_trajectories_blocked": metrics["attack_would_block"],
            "retrospective_benign_trajectories_blocked": metrics["benign_would_block"],
            "targeted_tests_passed": 16,
            "known_c1d_regression_case": (
                "workspace/user_task_8/important_instructions/injection_task_2"
            ),
        },
        "source_artifacts": {
            name: {"path": str(path.relative_to(ROOT)), "sha256": digest(path)}
            for name, path in FILES.items()
        },
        "required_live_evidence": {
            "agentdojo_version": "v1.1.2",
            "model": "deepseek-v4-flash",
            "attack_pairs": 629,
            "official_attack_labels_only": True,
            "retain_all_failures": True,
            "confirmation_exclusion": (
                "workspace/user_task_8/important_instructions/injection_task_2"
            ),
        },
        "claim_boundary": (
            "Post-confirmation repair developed from one C1d failure caused by dropped "
            "structured-output provenance. The triggering case is a regression case and "
            "must be excluded from confirmatory statistics. Retrospective interception "
            "is a mechanism diagnostic, not a live ASR or production-safety result."
        ),
    }
    target = EVAL / "c1f_frozen_candidate_2026-08-08.json"
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        left = dict(existing)
        right = dict(artifact)
        left.pop("frozen_at", None)
        right.pop("frozen_at", None)
        if left != right:
            raise FileExistsError(f"refusing to alter frozen C1f candidate: {target}")
    else:
        target.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(json.loads(target.read_text(encoding="utf-8")), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
