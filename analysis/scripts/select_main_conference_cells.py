"""Task A: Generate main-conference cell targets from statistical audit."""
import json
from pathlib import Path

def main():
    base = Path(__file__).parent.parent
    with open(base / 'analysis/statistical_uncertainty_audit.json') as f:
        audit = json.load(f)

    p0_pairs = [
        ("content_fetched", "terminal"),
        ("tool_error", "web_search"),
        ("network_egress", "web_search"),
        ("file_deleted", "terminal"),
        ("file_written", "terminal"),
        ("file_written", "write_file"),
        ("file_content_read", "read_file"),
    ]

    all_cells = audit['datasets']['scenarios_merged'].get('cells', [])
    targets = []
    for effect, tool in p0_pairs:
        match = next((c for c in all_cells if c['effect'] == effect and c['tool'] == tool), None)
        n_pos = match.get('n_positive', 0) if match and isinstance(match.get('n_positive'), (int,float)) else 0
        n_neg = match.get('n_negative', 0) if match and isinstance(match.get('n_negative'), (int,float)) else 0
        short = max(0, 30 - n_pos)
        ideal = max(0, 50 - n_pos)
        targets.append({
            "effect": effect, "tool": tool, "current_n_positive": n_pos, "current_n_negative": n_neg,
            "target_additional_positive": short, "ideal_additional_positive": ideal,
            "priority": "P0", "reason": "Main LOTO row; small N+ cited in statistical audit"
        })

    output = {
        "schema_version": "main_conference_cell_targets_v1",
        "source_audit": "analysis/statistical_uncertainty_audit.json",
        "target_positive_min": 30, "ideal_positive_min": 50,
        "cells": targets,
        "summary": {"n_p0_cells": len(targets),
            "total_additional_needed": sum(t['target_additional_positive'] for t in targets),
            "total_ideal_additional": sum(t['ideal_additional_positive'] for t in targets)}
    }
    (base / 'analysis/main_conference_cell_targets.json').write_text(json.dumps(output, indent=2))
    md = ["# Main-Conference Cell Targets", "", f"**{len(targets)} P0 cells** | Target: N+ ≥ 30", "",
          "| Effect | Tool | Current N+ | Addl (min) | Addl (ideal) |",
          "|---|---:|---:|---:|"]
    for t in targets:
        md.append(f"| {t['effect']} | {t['tool']} | {t['current_n_positive']} | {t['target_additional_positive']} | {t['ideal_additional_positive']} |")
    (base / 'analysis/main_conference_cell_targets.md').write_text("\n".join(md))
    print(f"Saved {len(targets)} P0 cells. Additional needed: {output['summary']['total_additional_needed']} (ideal: {output['summary']['total_ideal_additional']})")

if __name__ == '__main__': main()
