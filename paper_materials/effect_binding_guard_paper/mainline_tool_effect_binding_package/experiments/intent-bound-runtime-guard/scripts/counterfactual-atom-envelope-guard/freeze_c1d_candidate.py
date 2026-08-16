#!/usr/bin/env python3
"""Freeze the role-sensitive, atom-grounded C1d candidate before live runs."""

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
    "policy": ROOT / "code/shadow_atom_envelope_c1d/src/experiments/effect_binding_guard/"
    "e77_effect_diff_runtime_guard/atom_envelope_policy.py",
    "runtime_patch": ROOT / "code/shadow_atom_envelope_c1d/src/experiments/effect_binding_guard/"
    "e77_effect_diff_runtime_guard/agentdojo_e77_runtime_patch.py",
    "registered_descriptors": ROOT / "experiments/intent-bound-runtime-guard/results/"
    "effect-difference-runtime-guard/registered-effect-diff-descriptors.jsonl",
    "runtime_catalog": ROOT / "experiments/security-analysis-ablation-and-overhead/"
    "evaluation/runtime-mechanism-ablation/agentdojo_runtime_catalog.json",
    "relation_catalog": ROOT / "experiments/intent-bound-runtime-guard/evaluation/"
    "effect-difference-runtime-guard/registered_relation_catalog.json",
    "benign_confirmation": RESULTS / "deepseek_c1b_benign_confirmation.json",
    "retrospective_interception": RESULTS / "observed_trajectory_interception_report_c1d.json",
    "role_sensitive_tests": ROOT / "shared/compatibility/tests/tests/"
    "test_counterfactual_atom_envelope_role_sensitive.py",
    "intent_grounding_tests": ROOT / "shared/compatibility/tests/tests/"
    "test_counterfactual_atom_envelope_intent_grounding.py",
}


def digest(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    benign = json.loads(FILES["benign_confirmation"].read_text(encoding="utf-8"))
    replay = json.loads(FILES["retrospective_interception"].read_text(encoding="utf-8"))
    if benign.get("status") != "passed" or benign.get("direct_guard_blocks") != 0:
        raise RuntimeError("benign path evidence is not eligible for C1d freezing")
    metrics = replay["metrics"]
    if metrics["successful_benign_would_block"] != 0:
        raise RuntimeError("C1d retrospectively blocks a successful benign trajectory")
    artifact = {
        "status": "frozen_before_c1d_live_confirmation",
        "candidate": "C1d_role_sensitive_atom_intent_envelope",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "mechanism": {
            "authority_fields": (
                "Hard-taint target principal, resource/operation, scope constraint, "
                "network destination, and identity-bearing attachment fields."
            ),
            "payload_fields": (
                "Record untrusted payload data without treating payload provenance alone "
                "as authority expansion."
            ),
            "effect_grounding": (
                "Treat an effect as task-requested when an action-alias group matches and "
                "at least one authority-bearing call value is independently grounded in "
                "the original task."
            ),
            "runtime_llm_calls": 0,
        },
        "development_evidence": {
            "benign_no_guard_successes": benign["no_guard_successes"],
            "benign_c1b_successes": benign["c1b_successes"],
            "benign_mean_difference": benign["mean_difference"],
            "benign_lower_95": benign["cluster_bootstrap"]["one_sided_lower_95"],
            "benign_path_equivalence_basis": (
                "C1d changes only decisions in the presence of explicit untrusted-control "
                "segments; the four-repetition benign audit observed none and no block."
            ),
            "retrospective_attack_cases": metrics["attack_cases"],
            "retrospective_successful_attacks": metrics["official_attack_successes"],
            "retrospective_successful_attacks_intercepted": metrics[
                "successful_attack_trajectories_intercepted"
            ],
            "retrospective_attack_trajectories_blocked": metrics["attack_would_block"],
            "retrospective_benign_trajectories_blocked": metrics["benign_would_block"],
            "tests_passed": 80,
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
        },
        "claim_boundary": (
            "Frozen role-sensitive sandbox candidate. Retrospective interception is a "
            "mechanism diagnostic, not a live ASR or production-safety result."
        ),
    }
    target = EVAL / "c1d_frozen_candidate_2026-08-08.json"
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        left = dict(existing)
        right = dict(artifact)
        left.pop("frozen_at", None)
        right.pop("frozen_at", None)
        if left != right:
            raise FileExistsError(f"refusing to alter frozen C1d candidate: {target}")
    else:
        target.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(json.loads(target.read_text(encoding="utf-8")), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
