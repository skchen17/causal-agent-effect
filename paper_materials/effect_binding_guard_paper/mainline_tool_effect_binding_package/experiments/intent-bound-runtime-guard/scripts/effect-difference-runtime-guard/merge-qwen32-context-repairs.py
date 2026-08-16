#!/usr/bin/env python3
"""Build and finalize an immutable 726-row overlay from targeted repairs."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
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
EXPERIMENT = ROOT / "experiments/intent-bound-runtime-guard"
RUNS = EXPERIMENT / "runs/effect-difference-runtime-guard"
ORIGINAL = RUNS / "recovery-normalization-qwen32-full"
MERGED = RUNS / "recovery-normalization-qwen32-full-context-repaired"
FINALIZER = (
    EXPERIMENT
    / "scripts/effect-difference-runtime-guard/"
    "finalize-recovery-normalization-qwen32-full.py"
)
METHOD = "local-ours_e77_effect_diff_runtime"

R1 = RUNS / "qwen32-context-repair"
R2 = RUNS / "qwen32-context-repair-r2"
R3 = RUNS / "qwen32-context-repair-r3-gpu-full-v2"

# A row is selected only from a stage where that individual trajectory did
# not contain the context-failure empty continuation. R3 supersedes the two
# R2 user_task_38 rows that exceeded 81,920 tokens.
REPLACEMENTS = [
    (R1, "workspace/user_task_35/none/none.json"),
    (R1, "workspace/user_task_34/important_instructions/injection_task_1.json"),
    (R1, "workspace/user_task_34/important_instructions/injection_task_3.json"),
    (R1, "workspace/user_task_35/important_instructions/injection_task_1.json"),
    (R1, "workspace/user_task_35/important_instructions/injection_task_3.json"),
    (R1, "workspace/user_task_35/important_instructions/injection_task_5.json"),
    (R2, "workspace/user_task_35/important_instructions/injection_task_2.json"),
    (R2, "workspace/user_task_35/important_instructions/injection_task_4.json"),
    (R2, "workspace/user_task_25/important_instructions/injection_task_4.json"),
    (R2, "workspace/user_task_38/important_instructions/injection_task_0.json"),
    (R3, "workspace/user_task_38/important_instructions/injection_task_1.json"),
    (R3, "workspace/user_task_38/important_instructions/injection_task_2.json"),
]


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def message_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(item.get("content", item.get("text", "")))
            if isinstance(item, dict)
            else str(item)
            for item in content
        )
    return str(content)


def has_post_tool_empty(messages: list[dict[str, Any]]) -> bool:
    for index, message in enumerate(messages[1:], 1):
        if message.get("role") == "assistant" and not message_text(message.get("content")).strip():
            if any(previous.get("role") == "tool" for previous in messages[:index]):
                return True
    return False


def validate_replacement(run_root: Path, relative: str) -> dict[str, Any]:
    path = run_root / "agentdojo_logs" / METHOD / relative
    if not path.exists():
        raise FileNotFoundError(f"repair row missing: {path}")
    payload = read_json(path)
    if payload.get("error") is not None:
        raise ValueError(f"repair row contains an error: {path}")
    if not isinstance(payload.get("utility"), bool) or not isinstance(payload.get("security"), bool):
        raise ValueError(f"repair row lacks native metrics: {path}")
    if has_post_tool_empty(payload.get("messages") or []):
        raise ValueError(f"repair row has an empty post-tool continuation: {path}")
    return {
        "run_root": str(run_root.relative_to(ROOT)),
        "relative_case_path": relative,
        "utility": payload["utility"],
        "security": payload["security"],
    }


def main() -> int:
    if MERGED.exists():
        raise FileExistsError(
            f"merged run already exists; refusing to overwrite immutable artifact: {MERGED}"
        )
    r3_report = read_json(R3 / "repair_report.json")
    if r3_report.get("status") != "passed":
        raise ValueError("R3 repair report has not passed")

    selected = [validate_replacement(run_root, relative) for run_root, relative in REPLACEMENTS]
    if len(selected) != 12 or len({row["relative_case_path"] for row in selected}) != 12:
        raise ValueError("repair overlay must contain exactly 12 unique official rows")

    shutil.copytree(
        ORIGINAL / "agentdojo_logs",
        MERGED / "agentdojo_logs",
        copy_function=os.link,
    )
    for run_root, relative in REPLACEMENTS:
        source = run_root / "agentdojo_logs" / METHOD / relative
        destination = MERGED / "agentdojo_logs" / METHOD / relative
        destination.unlink()
        os.link(source, destination)

    audit_sources = [
        ORIGINAL / "runtime_audit.jsonl",
        R1 / "runtime_audit.jsonl",
        R2 / "runtime_audit.jsonl",
        R3 / "runtime_audit.jsonl",
    ]
    with (MERGED / "runtime_audit.jsonl").open("w", encoding="utf-8") as output:
        for source in audit_sources:
            text = source.read_text(encoding="utf-8")
            output.write(text)
            if text and not text.endswith("\n"):
                output.write("\n")

    protocol = read_json(ORIGINAL / "protocol_manifest.json")
    protocol.update(
        {
            "experiment": (
                "Recovery-normalization Qwen3-32B official AgentDojo full run "
                "with targeted context repair"
            ),
            "status": "merged_context_repair_completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "repair_metadata": {
                "repaired_official_rows": 12,
                "original_official_rows_retained": 714,
                "uniform_context_window": False,
                "base_context_window": 65536,
                "repair_context_windows": [73728, 81920, 122880],
                "r3_kv_cache_type": "q8_0",
                "replacement_rows": selected,
            },
            "claim_boundary": (
                "The 726-row overlay retains 714 rows from the original Qwen3-32B run and "
                "replaces 12 context-failure trajectories with targeted reruns. The same "
                "checkpoint, temperature, output cap, descriptors, runtime logic, native "
                "AgentDojo evaluators, and sandbox are used. Context capacity differs for "
                "the repaired rows, and the two longest rows use Q8_0 KV cache. Therefore "
                "this artifact establishes complete native metrics after disclosed context "
                "repair, not a uniform-context rerun or production-safety result."
            ),
        }
    )
    write_json(MERGED / "protocol_manifest.json", protocol)
    write_json(
        MERGED / "command_status.json",
        {
            "status": "targeted_repair_overlay",
            "commands": [
                {
                    "repair_row": row["relative_case_path"],
                    "returncode": 0,
                    "server_400_error": False,
                    "server_500_error": False,
                    "context_length_exceeded": False,
                }
                for row in selected
            ],
        },
    )
    write_json(
        MERGED / "merge_manifest.json",
        {
            "status": "ready_for_finalizer",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_run": str(ORIGINAL.relative_to(ROOT)),
            "selected_repair_rows": selected,
            "original_artifacts_modified": False,
        },
    )

    env = {
        **os.environ,
        "RECOVERY_FINALIZER_RUN_ROOT": str(MERGED),
        "RECOVERY_FINALIZER_REPORT_STEM": (
            "recovery-normalization-qwen32-full-context-repaired"
        ),
    }
    completed = subprocess.run(
        [sys.executable, str(FINALIZER)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )
    (MERGED / "finalizer.stdout.log").write_text(completed.stdout, encoding="utf-8")
    (MERGED / "finalizer.stderr.log").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(
            "context-repaired finalizer failed: "
            f"{completed.stdout[-1000:]} {completed.stderr[-1000:]}"
        )
    merge_manifest = read_json(MERGED / "merge_manifest.json")
    merge_manifest["status"] = "passed"
    write_json(MERGED / "merge_manifest.json", merge_manifest)
    print(completed.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
