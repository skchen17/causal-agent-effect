#!/usr/bin/env python3
"""Emit a readiness record for the pure E81 ablation kernel."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.experiments.effect_binding_guard.e81_runtime_ablation_kernel import ABLATIONS, config_diff


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "analysis/results"


def main() -> int:
    rows = {row: {"config_diff_from_A1": config_diff(row)} for row in ABLATIONS}
    report = {
        "experiment": "E81",
        "artifact_type": "runtime_ablation_kernel_readiness",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "implementation_ready_not_evaluated",
        "rows": rows,
        "counterexample_tests": [
            "A2 recipient substitution", "A7 injected provenance/control", "A9 raw descriptor missed binding", "A11 unplanned effect",
            "A12 legitimate resolver utility loss", "A13 nonempty default omission", "A15 terminal deny",
        ],
        "claim_boundary": (
            "The pure kernels and single-component counterexamples pass unit tests. No AgentDojo, ToolSandbox, "
            "long-horizon, security, utility, or overhead result is claimed until these rows run on one frozen protocol."
        ),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "e81_ablation_kernel_readiness.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# E81 Runtime Ablation Kernel Readiness", "", f"Status: `{report['status']}`.", "",
        *[f"- `{row}` diff: `{json.dumps(item['config_diff_from_A1'], sort_keys=True)}`" for row, item in rows.items()],
        "", "## Claim Boundary", "", report["claim_boundary"], "",
    ]
    (RESULTS / "e81_ablation_kernel_readiness.md").write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
