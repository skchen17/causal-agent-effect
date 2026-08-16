#!/usr/bin/env python3
"""Write the path-scrubbed E78 common-model protocol manifest."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/results/e78_qwen32_protocol_manifest.json"


def hardware() -> list[dict[str, object]]:
    completed = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    rows = []
    for line in completed.stdout.splitlines():
        name, memory = [item.strip() for item in line.rsplit(",", 1)]
        rows.append({"name": name, "memory_mib": int(memory)})
    return rows


def main() -> int:
    report = {
        "experiment": "E78",
        "artifact_type": "common_model_protocol_manifest",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "running_protocol_frozen",
        "benchmark": {
            "name": "AgentDojo",
            "version": "v1.1.2",
            "official_case_keys": 726,
            "benign": 97,
            "attack": 629,
            "suite_counts": {"workspace": 280, "slack": 126, "travel": 160, "banking": 160},
        },
        "model": {
            "file_name": "Qwen3-32B-Q4_K_M.gguf",
            "quantization": "Q4_K_M",
            "bytes": 19762149024,
            "sha256": "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689",
            "temperature": 0.0,
            "context_window": 65536,
            "output_cap": 4096,
        },
        "hardware": hardware(),
        "methods": [
            "no_guard", "transformers_pi_detector", "piguard", "spotlighting", "prompt_sandwiching",
            "promptarmor_local", "melon_local", "ours_e77_effect_diff_runtime", "attriguard_adapted",
        ],
        "controls": {
            "same_model": True,
            "same_case_keys": True,
            "same_initial_state": True,
            "same_native_evaluators": True,
            "errors_retained": True,
        },
        "claim_boundary": (
            "This manifest freezes the E78 protocol and model identity. It is not a performance result; method rows "
            "remain unavailable until all 726 keys pass the finalizer."
        ),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
