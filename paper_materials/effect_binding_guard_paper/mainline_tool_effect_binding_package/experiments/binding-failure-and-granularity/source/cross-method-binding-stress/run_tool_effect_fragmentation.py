from __future__ import annotations

import argparse
from pathlib import Path

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from src.experiments.tool_effect_fragmentation.adapters import build_system_cases, run_baselines
    from src.experiments.tool_effect_fragmentation.io_utils import write_jsonl
    from src.experiments.tool_effect_fragmentation.reporting import write_system_report, write_unified_report
else:
    from .adapters import build_system_cases, run_baselines
    from .io_utils import write_jsonl
    from .reporting import write_system_report, write_unified_report


DEFAULT_SYSTEMS = ("agentdojo", "toolsafe", "ipiguard", "safiron", "camel")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Tool-Effect Fragmentation stress tests.")
    parser.add_argument("--system", action="append", dest="systems", default=[])
    parser.add_argument("--max-base-cases", type=int, default=0)
    parser.add_argument("--data-dir", default="data/tool_effect_fragmentation")
    parser.add_argument("--results-dir", default="analysis/results")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path.cwd()
    systems = args.systems or list(DEFAULT_SYSTEMS)
    data_dir = root / args.data_dir
    results_dir = root / args.results_dir
    payloads = []
    for system in systems:
        cases, manifest = build_system_cases(system, root, args.max_base_cases)
        predictions = run_baselines(cases)
        write_jsonl(data_dir / f"stress_cases_{system}.jsonl", [case.to_dict() for case in cases])
        write_jsonl(data_dir / f"predictions_{system}.jsonl", [pred.to_dict() for pred in predictions])
        payloads.append(
            write_system_report(
                system=system,
                cases=cases,
                predictions=predictions,
                manifest=manifest,
                output_json=results_dir / f"tool_effect_fragmentation_{system}.json",
                output_md=results_dir / f"tool_effect_fragmentation_{system}.md",
            )
        )
    write_unified_report(
        payloads,
        results_dir / "tool_effect_fragmentation_unified.json",
        results_dir / "tool_effect_fragmentation_unified.md",
    )


if __name__ == "__main__":
    main()
