"""Analyze surface-form graph alignment for Auth-SafeInv data.

The graph is diagnostic, not a proof of mitigation success. For each effect, we
summarize which tool surfaces realize the effect, which tool surfaces realize it
as unauthorized, and whether strict held-out-pair alignment is identifiable from
the available surface graph.

Outputs:
  analysis/surface_graph_alignment_<data_name>.json
  analysis/surface_graph_alignment_<data_name>.md
"""

from __future__ import annotations

import itertools
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def complete_edges(nodes: list[str]) -> list[tuple[str, str]]:
    return list(itertools.combinations(sorted(nodes), 2))


def pair_identifiability(nodes: list[str]) -> dict[str, Any]:
    pairs = complete_edges(nodes)
    if len(nodes) < 2:
        return {
            "n_pairs": 0,
            "strict_pair_identifiable": False,
            "reason": "fewer than two surface forms",
            "heldout_pair_rows": [],
        }
    rows = []
    identifiable_count = 0
    for a, b in pairs:
        # With complete cross-surface positive pairing, a held-out edge remains
        # transitively alignable iff there is at least one intermediate surface.
        intermediate = sorted(set(nodes) - {a, b})
        identifiable = bool(intermediate)
        identifiable_count += int(identifiable)
        rows.append(
            {
                "heldout_pair": [a, b],
                "intermediate_surfaces": intermediate,
                "identifiable_under_strict_pair_holdout": identifiable,
            }
        )
    return {
        "n_pairs": len(pairs),
        "strict_pair_identifiable": identifiable_count == len(pairs),
        "identifiable_pair_count": identifiable_count,
        "nonidentifiable_pair_count": len(pairs) - identifiable_count,
        "reason": "three_or_more_surface_forms" if len(nodes) >= 3 else "two-form effect; no transitive path after holding out the only pair",
        "heldout_pair_rows": rows,
    }


def load_auth_loto(base: Path, data_name: str) -> dict[tuple[str, str], dict[str, Any]]:
    path = base / "analysis" / f"auth_safeinv_qwen3-8b_{data_name}.json"
    if not path.exists():
        path = base / "analysis" / f"auth_safeinv_{data_name}.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("leave_one_tool_out", [])
    return {(row["effect"], row["heldout_tool"]): row for row in rows}


def analyze(data_name: str) -> dict[str, Any]:
    base = Path(__file__).resolve().parent.parent
    data_path = base / "data" / f"{data_name}.jsonl"
    rows = [json.loads(line) for line in data_path.read_text(encoding="utf-8").splitlines()]
    effects = sorted(rows[0]["effects"].keys())
    auth_loto = load_auth_loto(base, data_name)

    by_effect: dict[str, Any] = {}
    for effect in effects:
        verified_counts: Counter[str] = Counter()
        unauthorized_counts: Counter[str] = Counter()
        family_counts: Counter[str] = Counter()
        for row in rows:
            tool = row["tool_name"]
            if effect in row.get("verified_effects", []):
                verified_counts[tool] += 1
                family_counts[row["counterfactual_family"]] += 1
            if effect in row.get("unauthorized_effects", []):
                unauthorized_counts[tool] += 1

        verified_tools = sorted(verified_counts)
        unauthorized_tools = sorted(unauthorized_counts)
        verified_ident = pair_identifiability(verified_tools)
        unauthorized_ident = pair_identifiability(unauthorized_tools)

        loto_rows = []
        for tool in unauthorized_tools:
            metric = auth_loto.get((effect, tool))
            if metric:
                loto_rows.append(
                    {
                        "heldout_tool": tool,
                        "n_unauth": metric["n_unauth_test"],
                        "heldout_fnr": metric["unauthorized_fnr"],
                        "within_fnr": metric.get("within_unauthorized_fnr"),
                        "auth_tool_proxy_gap": metric.get("auth_tool_proxy_gap"),
                        "unsafe_allow_bound": metric.get("unsafe_allow_bound"),
                    }
                )

        by_effect[effect] = {
            "verified_tool_counts": dict(sorted(verified_counts.items())),
            "unauthorized_tool_counts": dict(sorted(unauthorized_counts.items())),
            "counterfactual_family_counts_for_verified_effect": dict(sorted(family_counts.items())),
            "n_verified_tools": len(verified_tools),
            "n_unauthorized_tools": len(unauthorized_tools),
            "verified_graph": {
                "nodes": verified_tools,
                "edges": [list(edge) for edge in complete_edges(verified_tools)],
                **verified_ident,
            },
            "unauthorized_graph": {
                "nodes": unauthorized_tools,
                "edges": [list(edge) for edge in complete_edges(unauthorized_tools)],
                **unauthorized_ident,
            },
            "auth_loto_rows": loto_rows,
        }

    return {
        "data_name": data_name,
        "n_rows": len(rows),
        "graph_assumption": "complete graph over surfaces with positive samples; edges represent available cross-surface positive pairs for representation alignment",
        "by_effect": by_effect,
        "caveats": [
            "This graph is a diagnostic of pair-holdout identifiability, not evidence that a mitigation succeeds.",
            "Two-surface effects are not strict-pair identifiable because holding out the only cross-surface pair removes all alignment paths.",
            "Unauthorized graphs can be less identifiable than verified-effect graphs when authorization violations occur on only two tools.",
        ],
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Surface Graph Alignment",
        "",
        f"- Data: `{payload['data_name']}`",
        f"- Rows: {payload['n_rows']}",
        f"- Graph assumption: {payload['graph_assumption']}",
        "",
        "## Effect Summary",
        "",
        "| Effect | Verified tools | Unauthorized tools | Verified strict identifiable | Unauthorized strict identifiable | Max AuthToolProxyGap |",
        "|---|---:|---:|---|---|---:|",
    ]
    for effect, row in payload["by_effect"].items():
        gaps = [
            r["auth_tool_proxy_gap"]
            for r in row["auth_loto_rows"]
            if r.get("auth_tool_proxy_gap") is not None
        ]
        max_gap = None if not gaps else round(max(gaps), 4)
        lines.append(
            f"| `{effect}` | {row['n_verified_tools']} | {row['n_unauthorized_tools']} | "
            f"{row['verified_graph']['strict_pair_identifiable']} | "
            f"{row['unauthorized_graph']['strict_pair_identifiable']} | {max_gap} |"
        )

    lines.extend(["", "## Auth LOTO Rows With Graph Context", "", "| Effect | Heldout tool | N unauth | Heldout FNR | Within FNR | Gap | Bound |", "|---|---|---:|---:|---:|---:|---:|"])
    for effect, row in payload["by_effect"].items():
        for metric in row["auth_loto_rows"]:
            lines.append(
                f"| `{effect}` | `{metric['heldout_tool']}` | {metric['n_unauth']} | "
                f"{metric['heldout_fnr']} | {metric['within_fnr']} | "
                f"{metric['auth_tool_proxy_gap']} | {metric['unsafe_allow_bound']} |"
            )

    lines.extend(["", "## Caveats", ""])
    for caveat in payload["caveats"]:
        lines.append(f"- {caveat}")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    data_name = sys.argv[1] if len(sys.argv) > 1 else "authorization_counterfactuals_v1"
    payload = analyze(data_name)
    base = Path(__file__).resolve().parent.parent
    out_json = base / "analysis" / f"surface_graph_alignment_{data_name}.json"
    out_md = base / "analysis" / f"surface_graph_alignment_{data_name}.md"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown(out_md, payload)
    print(f"Saved JSON: {out_json}")
    print(f"Saved MD:   {out_md}")
    print(f"Effects: {len(payload['by_effect'])}")


if __name__ == "__main__":
    main()
