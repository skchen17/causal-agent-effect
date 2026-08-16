#!/usr/bin/env python3
"""Freeze the reviewed-subset protocol for the E81 runtime ablations."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
    if (candidate / "paper").is_dir()
    and (candidate / "experiments").is_dir()
    and (candidate / "shared").is_dir()
)
PYTHON = (
    ROOT
    / "experiments/unified-agent-security-baselines/runs/"
    "unified-agent-security-comparison/agentdojo-env/bin/python"
)
EVALUATION = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/evaluation/"
    "runtime-mechanism-ablation"
)
RESULTS = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "runtime-mechanism-ablation"
)
MANIFESTS = (
    ROOT
    / "experiments/human-authority-and-causal-validation/evaluation/"
    "authority-manifest-human-review/runtime_ready_trusted_manifests.jsonl"
)
PROJECTIONS = (
    ROOT
    / "experiments/human-authority-and-causal-validation/evaluation/"
    "causal-effect-projection-validation-2/trusted_security_effect_projections.jsonl"
)
CATALOG = EVALUATION / "agentdojo_runtime_catalog.json"
RAW_REGISTRY = EVALUATION / "a9_raw_descriptor_registry.jsonl"
APPLICABILITY = (
    ROOT
    / "experiments/security-analysis-ablation-and-overhead/results/"
    "runtime-mechanism-ablation/e81-ablation-applicability-audit.json"
)
MODEL = Path(
    "/data/CSK/causal-agent-safety-research/models/"
    "Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf"
)
OUTPUT_JSON = EVALUATION / "final_common_protocol_manifest_qwen32.json"
OUTPUT_MD = RESULTS / "final-common-protocol-manifest-qwen32.md"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def official_injection_tasks() -> dict[str, list[str]]:
    code = (
        "from agentdojo.task_suite.load_suites import get_suite; import json; "
        "print(json.dumps({s: sorted(get_suite('v1.1.2', s).injection_tasks) "
        "for s in ['banking','slack','travel','workspace']}))"
    )
    completed = subprocess.run(
        [str(PYTHON), "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    return json.loads(completed.stdout)


def main() -> int:
    required = (
        PYTHON,
        MANIFESTS,
        PROJECTIONS,
        CATALOG,
        RAW_REGISTRY,
        APPLICABILITY,
        MODEL,
    )
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"E81 protocol inputs missing: {missing}")

    manifests = read_jsonl(MANIFESTS)
    projections = read_jsonl(PROJECTIONS)
    raw_registry = read_jsonl(RAW_REGISTRY)
    applicability = json.loads(APPLICABILITY.read_text(encoding="utf-8"))
    tasks: dict[str, list[str]] = defaultdict(list)
    for row in manifests:
        tasks[row["suite"]].append(row["user_task_id"])
    frozen_tasks = {
        suite: sorted(set(task_ids)) for suite, task_ids in sorted(tasks.items())
    }
    if sum(map(len, frozen_tasks.values())) != len(manifests):
        raise ValueError("runtime-ready authority manifests contain duplicate task keys")
    if len(manifests) != 26:
        raise ValueError(f"expected 26 runtime-ready reviewed tasks, found {len(manifests)}")

    injections = official_injection_tasks()
    attack_counts = {
        suite: len(task_ids) * len(injections[suite])
        for suite, task_ids in frozen_tasks.items()
    }
    n_benign = len(manifests)
    n_attack = sum(attack_counts.values())
    if n_attack != 169:
        raise ValueError(f"expected 169 reviewed-subset attack pairs, found {n_attack}")

    rows = {
        "A0": {
            "label": "no_guard",
            "single_change_from_a1": "remove_all_runtime_mediation",
        },
        "A1": {
            "label": "full_reviewed_effect_contract_guard",
            "single_change_from_a1": None,
        },
        "A2": {
            "label": "tool_call_level_only",
            "single_change_from_a1": "remove_field_and_atom_granularity",
        },
        "A7": {
            "label": "no_provenance_control_binding",
            "single_change_from_a1": "accept_untrusted_or_untyped_resolver_evidence",
        },
        "A9": {
            "label": "schema_description_only_registration",
            "single_change_from_a1": "replace_counterfactually_validated_registry_with_round0_registry",
        },
        "A11": {
            "label": "no_task_authority_envelope",
            "single_change_from_a1": "remove_reviewed_task_scoped_authority_bound",
        },
        "A12": {
            "label": "no_authorized_read_grounding",
            "single_change_from_a1": "disable_typed_resolver_ledger",
        },
        "A13": {
            "label": "omitted_fields_permissive",
            "single_change_from_a1": "do_not_fail_closed_on_unresolved_security_defaults",
        },
        "A15": {
            "label": "no_replan_recovery",
            "single_change_from_a1": "replace_replan_feedback_with_terminal_denial",
        },
    }
    report = {
        "experiment": "E81",
        "artifact_type": "frozen_reviewed_subset_common_protocol",
        "status": "protocol_frozen_runner_pending",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agentdojo_version": "v1.1.2",
        "model": {
            "file_name": MODEL.name,
            "sha256": sha256(MODEL),
            "temperature": 0.0,
            "context_window": 65536,
        },
        "case_manifest": {
            "tasks": frozen_tasks,
            "suite_task_counts": {
                suite: len(task_ids) for suite, task_ids in frozen_tasks.items()
            },
            "official_injection_task_counts": {
                suite: len(injections[suite]) for suite in frozen_tasks
            },
            "attack_pair_counts": attack_counts,
            "n_benign_per_row": n_benign,
            "n_attack_per_row": n_attack,
            "n_total_per_row": n_benign + n_attack,
            "all_official_injection_tasks_for_reviewed_tasks": True,
        },
        "reviewed_inputs": {
            "runtime_ready_authority_manifests": len(manifests),
            "trusted_security_effect_projections": len(projections),
            "raw_registration_rows": len(raw_registry),
        },
        "applicability": applicability,
        "rows": rows,
        "required_metrics": [
            "benign_utility",
            "attack_success_rate",
            "attack_user_utility",
            "coverage",
            "abstain_or_block_rate",
            "precommit_check_count",
            "blocked_call_execution_count",
        ],
        "single_variable_gate": (
            "A2, A7, A9, A11, A12, A13, and A15 must differ from A1 only by "
            "the declared switch. All rows share the model, task keys, official "
            "injection keys, decoding settings, tool schemas, and validators."
        ),
        "execution_gate": (
            "This manifest is not an ablation result. Rows become evidence only "
            "after the hybrid reviewed-authority/effect-descriptor runner passes "
            "source-hash, row-count, and audit-log checks."
        ),
        "claim_boundary": (
            "E81 is scoped to the 26 AgentDojo tasks with runtime-ready reviewed "
            "authority manifests and all 169 official attack pairs for those "
            "tasks. It is not the full 726-case benchmark. A13 has no applicable "
            "dynamic security-default field in this slice and is not claim-eligible."
        ),
        "input_sha256": {
            "authority_manifests": sha256(MANIFESTS),
            "trusted_effect_projections": sha256(PROJECTIONS),
            "runtime_catalog": sha256(CATALOG),
            "raw_descriptor_registry": sha256(RAW_REGISTRY),
            "applicability_audit": sha256(APPLICABILITY),
        },
        "task_suite_counts": dict(
            sorted(Counter(row["suite"] for row in manifests).items())
        ),
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# E81 Frozen Common Protocol",
        "",
        f"- Status: `{report['status']}`",
        f"- Benign cases per row: `{n_benign}`",
        f"- Official attack pairs per row: `{n_attack}`",
        f"- Total cases per row: `{n_benign + n_attack}`",
        f"- Trusted effect projections: `{len(projections)}`",
        "",
        "| Row | Variant | Single change from A1 |",
        "|---|---|---|",
    ]
    for row_id, row in rows.items():
        lines.append(
            f"| {row_id} | {row['label']} | "
            f"{row['single_change_from_a1'] or 'full path'} |"
        )
    lines.extend(
        [
            "",
            "## Execution Gate",
            "",
            report["execution_gate"],
            "",
            "## Claim Boundary",
            "",
            report["claim_boundary"],
            "",
        ]
    )
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "n_benign_per_row": n_benign,
                "n_attack_per_row": n_attack,
                "rows": list(rows),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
