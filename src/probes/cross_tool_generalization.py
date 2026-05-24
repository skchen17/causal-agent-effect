"""
Cross-tool generalization test.

For each causal effect that appears in ≥2 tools:
  - Leave-one-tool-out: train linear probe on N-1 tools, test on held-out tool
  - Report F1_cross vs F1_within (baseline)
  - gap = F1_cross - F1_within  measures how much the probe depends on tool identity

Interpretation:
  gap ≈ 0   → probe learned the causal CONCEPT (generalizes across tools)
  gap << 0  → probe learned a TOOL PROXY (doesn't generalize)
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score


def load_data(data_name: str) -> tuple[np.ndarray, np.ndarray, dict, list[str]]:
    base = Path(__file__).resolve().parent.parent
    emb_dir = base / "embeddings"

    emb_path = emb_dir / f"embeddings_{data_name}.npy"
    eff_path = emb_dir / f"effects_{data_name}.npy"
    meta_path = emb_dir / f"meta_{data_name}.json"
    texts_path = emb_dir / f"texts_{data_name}.jsonl"

    if not emb_path.exists():
        emb_path = emb_dir / "embeddings.npy"
        eff_path = emb_dir / "effects.npy"
        meta_path = emb_dir / "meta.json"
        texts_path = emb_dir / "texts.jsonl"

    if not emb_path.exists():
        raise FileNotFoundError(f"No embeddings for '{data_name}' at {emb_dir}")

    X = np.load(emb_path)
    Y = np.load(eff_path)
    with open(meta_path) as f:
        meta = json.load(f)

    # Extract tool names from texts file
    tools = []
    if texts_path.exists():
        with open(texts_path, encoding="utf-8") as f:
            for line in f:
                tools.append(json.loads(line).get("tool_name", "unknown"))
    else:
        tools = ["unknown"] * X.shape[0]

    return X, Y, meta, tools


def cross_tool_test(
    effect_name: str,
    effect_idx: int,
    X: np.ndarray,
    Y: np.ndarray,
    tools: list[str],
    min_per_tool: int = 5,
) -> dict | None:
    """Leave-one-tool-out cross-validation for a single causal effect."""
    y = Y[:, effect_idx]

    # Group indices by tool
    tool_indices: dict[str, list[int]] = defaultdict(list)
    for i, t in enumerate(tools):
        tool_indices[t].append(i)

    # Keep tools with sufficient positive AND negative samples
    usable_tools = {}
    for t, idxs in tool_indices.items():
        pos_count = int(y[idxs].sum())
        neg_count = len(idxs) - pos_count
        if pos_count >= min_per_tool and neg_count >= min_per_tool:
            usable_tools[t] = idxs

    if len(usable_tools) < 2:
        return None  # Need ≥2 tools for cross-tool test

    results = []
    within_f1s = []

    for held_out_tool in usable_tools:
        # Split: all other tools → train, held-out → test
        train_idx = []
        for t, idxs in usable_tools.items():
            if t != held_out_tool:
                train_idx.extend(idxs)

        test_idx = usable_tools[held_out_tool]

        # Skip if either set has only one class
        if y[train_idx].sum() == 0 or y[train_idx].sum() == len(train_idx):
            continue
        if y[test_idx].sum() == 0 or y[test_idx].sum() == len(test_idx):
            continue

        # Train linear probe
        clf = LogisticRegression(
            l1_ratio=0, C=1.0, solver="lbfgs", max_iter=2000, class_weight="balanced"
        )
        clf.fit(X[train_idx], y[train_idx])
        y_pred = clf.predict(X[test_idx])
        f1_cross = f1_score(y[test_idx], y_pred, zero_division=0)

        # Within-tool baseline: train and test on held_out_tool (via cross-val proxy)
        # Using a simple train/test split within the tool as baseline
        n_test = max(1, len(test_idx) // 3)
        test_sub = test_idx[:n_test]
        train_sub = test_idx[n_test:]
        if y[train_sub].sum() > 0 and y[train_sub].sum() < len(train_sub):
            clf_within = LogisticRegression(
                l1_ratio=0, C=1.0, solver="lbfgs", max_iter=2000, class_weight="balanced"
            )
            clf_within.fit(X[train_sub], y[train_sub])
            y_pred_w = clf_within.predict(X[test_sub])
            f1_within = f1_score(y[test_sub], y_pred_w, zero_division=0)
            within_f1s.append(f1_within)

        results.append({
            "train_tools": [t for t in usable_tools if t != held_out_tool],
            "test_tool": held_out_tool,
            "n_train": len(train_idx),
            "n_test": len(test_idx),
            "pos_test": int(y[test_idx].sum()),
            "f1_cross": round(float(f1_cross), 4),
        })

    if not results:
        return None

    avg_cross = sum(r["f1_cross"] for r in results) / len(results)
    avg_within = sum(within_f1s) / len(within_f1s) if within_f1s else None
    gap = (avg_cross - avg_within) if avg_within is not None else None

    return {
        "effect": effect_name,
        "n_tools": len(usable_tools),
        "tools": list(usable_tools.keys()),
        "avg_cross_f1": round(avg_cross, 4),
        "avg_within_f1": round(avg_within, 4) if avg_within is not None else None,
        "gap": round(gap, 4) if gap is not None else None,
        "per_tool_results": results,
    }


def main() -> None:
    import sys
    data_name = sys.argv[1] if len(sys.argv) > 1 else "scenarios_merged"

    print(f"Loading data: {data_name}")
    X, Y, meta, tools = load_data(data_name)
    effect_names = meta["effect_names"]
    print(f"  Embeddings: {X.shape}")
    print(f"  Effects: {Y.shape}")
    print(f"  Unique tools: {sorted(set(tools))}")

    tier_map = {
        "command_executed": "HIGH", "file_written": "MEDIUM",
        "file_deleted": "HIGH", "file_content_read": "LOW",
        "message_sent": "HIGH", "network_egress": "HIGH",
        "subagent_spawned": "HIGH", "content_fetched": "LOW",
        "search_performed": "LOW", "memory_updated": "LOW",
        "tool_error": "BENIGN",
    }

    print(f"\n{'=' * 100}")
    print("Cross-Tool Generalization Test")
    print("Leave-one-tool-out: train on N-1 tools, test on held-out tool")
    print(f"{'=' * 100}")

    all_results = []
    for i, effect in enumerate(effect_names):
        r = cross_tool_test(effect, i, X, Y, tools)
        if r is None:
            continue
        all_results.append(r)

    # ── Report ──
    print(f"\n{'Effect':<25s} {'Tools':>6s} {'Cross F1':>9s} {'Within F1':>10s} {'Gap':>8s} {'Tier':>8s} {'Verdict':>16s}")
    print("-" * 110)

    for r in sorted(all_results, key=lambda x: -(x["gap"] or -999)):
        tier = tier_map.get(r["effect"], "UNKNOWN")
        if r["gap"] is None:
            verdict = "⚠ no within-baseline"
        elif r["gap"] > -0.05:
            verdict = "✓ CONCEPT LEARNED"
        elif r["gap"] > -0.15:
            verdict = "~ PARTIAL"
        elif r["gap"] > -0.30:
            verdict = "◈ TOOL PROXY"
        else:
            verdict = "✗ PURE PROXY"

        wf1 = f"{r['avg_within_f1']:.4f}" if r["avg_within_f1"] is not None else "N/A"
        gap_str = f"{r['gap']:+.4f}" if r['gap'] is not None else "N/A"

        print(
            f"{r['effect']:<25s} {r['n_tools']:>5d} "
            f"{r['avg_cross_f1']:>9.4f} {wf1:>10s} "
            f"{gap_str:>8s} {tier:>8s} {verdict:>16s}"
        )

        # Per-tool detail
        for detail in r["per_tool_results"]:
            train_str = "+".join(t[:4] for t in detail["train_tools"])
            print(
                f"  └─ train on {train_str:30s}  test on {detail['test_tool']:12s}  "
                f"F1={detail['f1_cross']:.4f}  (n={detail['n_test']}, pos={detail['pos_test']})"
            )

    # ── Summary ──
    n_concept = len([r for r in all_results if r["gap"] is not None and r["gap"] > -0.05])
    n_partial = len([r for r in all_results if r["gap"] is not None and -0.15 < r["gap"] <= -0.05])
    n_proxy = len([r for r in all_results if r["gap"] is not None and r["gap"] <= -0.15])
    n_na = len(all_results) - n_concept - n_partial - n_proxy
    print(f"\nSummary: {len(all_results)} effects testable — "
          f"{n_concept} concept learned, {n_partial} partial, {n_proxy} tool proxy"
          + (f", {n_na} no baseline" if n_na else ""))

    # Save
    out = Path(__file__).resolve().parent.parent / "analysis" / f"cross_tool_{data_name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(all_results, indent=2, ensure_ascii=False, default=str))
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
