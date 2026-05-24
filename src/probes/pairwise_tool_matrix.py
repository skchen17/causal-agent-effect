"""
Pairwise tool generalization matrix.

For each effect, for every pair of tools (A → B):
  - Train linear probe on tool A
  - Test on tool B
  - Report F1_A→B

This reveals WHICH tool pairs have the proxy problem,
rather than averaging them into a single gap number.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score


def load_data(data_name: str):
    base = Path(__file__).resolve().parent.parent
    emb_dir = base / "embeddings"
    emb_path = emb_dir / f"embeddings_{data_name}.npy"
    eff_path = emb_dir / f"effects_{data_name}.npy"
    meta_path = emb_dir / f"meta_{data_name}.json"
    texts_path = emb_dir / f"texts_{data_name}.jsonl"

    X = np.load(emb_path)
    Y = np.load(eff_path)
    with open(meta_path) as f:
        meta = json.load(f)
    tools = []
    if texts_path.exists():
        with open(texts_path, encoding="utf-8") as f:
            for line in f:
                tools.append(json.loads(line).get("tool_name", "unknown"))
    else:
        tools = ["unknown"] * X.shape[0]
    return X, Y, meta, tools


def main() -> None:
    import sys
    data_name = sys.argv[1] if len(sys.argv) > 1 else "qwen3-8b_scenarios_merged"

    X, Y, meta, tools = load_data(data_name)
    effect_names = meta["effect_names"]

    # ── For each effect, build the pairwise matrix ──
    print(f"{'Effect':<25s} | {'Train'} → {'Test':>12s} | {'n_train':>7s} | {'n_test':>6s} | {'F1_A→B':>7s} | Verdict")
    print("-" * 95)

    full_results = {}
    for ei, effect in enumerate(effect_names):
        y = Y[:, ei]

        # Group samples by tool, require ≥8 total and ≥2 pos/neg
        tool_data = {}
        for t in sorted(set(tools)):
            idxs = [i for i, tt in enumerate(tools) if tt == t]
            pos = sum(y[i] for i in idxs)
            neg = len(idxs) - pos
            if len(idxs) >= 8 and pos >= 2 and neg >= 2:
                tool_data[t] = (idxs, pos, neg)

        if len(tool_data) < 2:
            continue

        rows = []
        for t_train in tool_data:
            for t_test in tool_data:
                if t_train == t_test:
                    continue
                idx_train, _, _ = tool_data[t_train]
                idx_test, pos_test, _ = tool_data[t_test]

                clf = LogisticRegression(l1_ratio=0, C=1.0, max_iter=2000, class_weight="balanced")
                clf.fit(X[idx_train], y[idx_train])
                y_pred = clf.predict(X[idx_test])
                f1 = f1_score(y[idx_test], y_pred, zero_division=0)

                # Verdict
                if f1 >= 0.80: v = "✓"
                elif f1 >= 0.60: v = "~"
                elif f1 >= 0.40: v = "◈"
                else: v = "✗"

                rows.append((t_train, t_test, len(idx_train), len(idx_test), pos_test, f1, v))
                print(
                    f"{effect:<25s} | {t_train:>12s} → {t_test:>12s} | "
                    f"{len(idx_train):>6d} | {len(idx_test):>5d} | {f1:>7.3f} | {v}"
                )

        # Summary stats per effect
        f1s = [r[5] for r in rows]
        within = [r[5] for r in rows if r[0] == r[1]] if False else None
        avg = np.mean(f1s) if f1s else 0
        hi = max(f1s) if f1s else 0
        lo = min(f1s) if f1s else 0
        spread = hi - lo
        n_good = len([r for r in rows if r[5] >= 0.80])
        n_bad = len([r for r in rows if r[5] < 0.40])

        summary_line = (
            f"\n  Summary: avg={avg:.3f} spread={spread:.3f}  "
            f"✓(≥0.8)={n_good} ✗(<0.4)={n_bad}  total_pairs={len(rows)}\n"
        )
        print(summary_line)
        full_results[effect] = {
            "n_tools": len(tool_data),
            "tools": sorted(tool_data.keys()),
            "avg_f1": round(float(avg), 4),
            "spread": round(float(spread), 4),
            "pairs_good": n_good,
            "pairs_bad": n_bad,
            "total_pairs": len(rows),
            "rows": [{
                "train": r[0], "test": r[1], "n_train": r[2],
                "n_test": r[3], "pos_test": r[4], "f1": round(float(r[5]), 4),
            } for r in rows],
        }

    # ── Global pattern: linguistic proximity ──
    print(f"\n{'=' * 95}")
    print("Tool Pair Generalization Pattern")
    print(f"{'=' * 95}")
    print()
    print("Hypothesis: tool pairs with similar linguistic style (e.g.,")
    print("web_fetch ↔ web_search) should transfer better than pairs")
    print("with different styles (e.g., terminal ↔ write_file).")
    print()

    # Group tool pairs by "linguistic proximity"
    # Tool families (subjective, based on how the tools are described)
    families = {
        "web": ["web_fetch", "web_search"],
        "file_ops": ["read_file", "write_file", "delete_file"],
        "comm": ["send_message"],
        "shell": ["terminal"],
        "agent": ["delegate", "memory"],
    }
    tool_to_family = {}
    for fam, ts in families.items():
        for t in ts:
            tool_to_family[t] = fam

    same_family_f1s = []
    diff_family_f1s = []
    all_rows = []
    for effect, r in full_results.items():
        for row in r["rows"]:
            tf_train = tool_to_family.get(row["train"], "unknown")
            tf_test = tool_to_family.get(row["test"], "unknown")
            same = tf_train == tf_test
            all_rows.append((effect, row["train"], row["test"], row["f1"], same, tf_train, tf_test))
            if same:
                same_family_f1s.append(row["f1"])
            else:
                diff_family_f1s.append(row["f1"])

    if same_family_f1s and diff_family_f1s:
        print(f"  Same-family transfer:   avg F1 = {np.mean(same_family_f1s):.3f}  (n={len(same_family_f1s)})")
        print(f"  Cross-family transfer:  avg F1 = {np.mean(diff_family_f1s):.3f}  (n={len(diff_family_f1s)})")
        print(f"  Family proximity bonus:  {np.mean(same_family_f1s) - np.mean(diff_family_f1s):+.3f}")

        # Show worst cross-family pairs
        diff_sorted = sorted([r for r in all_rows if not r[4]], key=lambda x: x[3])
        print(f"\n  Worst cross-family transfers:")
        for (effect, train, test, f1, _, fam_t, fam_e) in diff_sorted[:8]:
            print(f"    {effect:25s}  {train:12s}({fam_t:8s}) → {test:12s}({fam_e:8s})  F1={f1:.3f}")

        print(f"\n  Best cross-family transfers:")
        diff_best = sorted([r for r in all_rows if not r[4]], key=lambda x: -x[3])
        for (effect, train, test, f1, _, fam_t, fam_e) in diff_best[:5]:
            print(f"    {effect:25s}  {train:12s}({fam_t:8s}) → {test:12s}({fam_e:8s})  F1={f1:.3f}")

    # Save
    out = Path(__file__).resolve().parent.parent / "analysis" / f"pairwise_tool_{data_name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    def convert(o):
        if isinstance(o, (np.integer,)): return int(o)
        if isinstance(o, (np.floating,)): return float(o)
        if isinstance(o, np.ndarray): return o.tolist()
        raise TypeError(type(o))
    out.write_text(json.dumps(full_results, indent=2, ensure_ascii=False, default=convert))
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
