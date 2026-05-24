"""
Baseline comparison experiment.

Tests 4 methods on worst-tool FNR across all effects:
  - pooled: standard LogisticRegression with class_weight=balanced
  - balanced: subsample each tool to equal counts before training
  - tool_cond: concatenate tool one-hot ID to embedding
  - group_reweight: inverse-frequency per-tool sample weights

Also computes complete LOTO table with within-FNR, heldout-FNR, FNR-Gap.
"""

from __future__ import annotations
import json, sys
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import recall_score
from sklearn.model_selection import StratifiedKFold
from pathlib import Path


def load_data(data_name: str):
    base = Path(__file__).resolve().parent.parent
    emb_dir = base / "embeddings"
    emb_path = emb_dir / f"embeddings_{data_name}.npy"
    eff_path = emb_dir / f"effects_{data_name}.npy"
    meta_path = emb_dir / f"meta_{data_name}.json"
    texts_path = emb_dir / f"texts_{data_name}.jsonl"

    if not emb_path.exists():
        raise FileNotFoundError(f"No embeddings found for {data_name}")

    X = np.load(emb_path)
    Y = np.load(eff_path)
    with open(meta_path) as f:
        meta = json.load(f)
    tools = []
    if texts_path.exists():
        with open(texts_path) as f:
            tools = [json.loads(line).get("tool_name", "unknown") for line in f]
    else:
        tools = ["unknown"] * X.shape[0]
    return X, Y, meta, tools


def main():
    data_name = sys.argv[1] if len(sys.argv) > 1 else "qwen3-8b_scenarios_merged"
    X, Y, meta, tools = load_data(data_name)
    effect_names = meta["effect_names"]
    tool_set = sorted(set(tools))

    print(f"Model: {meta['model']}")
    print(f"Samples: {X.shape[0]}, Effects: {len(effect_names)}")

    # ============================================================
    # 1. Complete LOTO table
    # ============================================================
    print(f"\n{'=' * 95}")
    print("1. LOTO TABLE: within-FNR | heldout-FNR | FNR-Gap")
    print(f"{'=' * 95}")

    loto_table = {}
    for ei, effect in enumerate(effect_names):
        y = Y[:, ei]
        effect_rows = {}

        for t in tool_set:
            pos_i = [i for i, tt in enumerate(tools) if tt == t and y[i] == 1]
            neg_i = [i for i, tt in enumerate(tools) if tt == t and y[i] == 0]
            n_pos, n_neg = len(pos_i), len(neg_i)
            if n_pos < 5 or n_neg < 5:
                continue

            all_idx = np.array(pos_i + neg_i)
            labels = np.array([1] * n_pos + [0] * n_neg)

            # Within-FNR: stratified CV within same tool
            skf = StratifiedKFold(n_splits=min(3, n_pos), shuffle=True, random_state=42)
            within_fnrs = []
            for tr, te in skf.split(all_idx, labels):
                clf = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
                clf.fit(X[all_idx[tr]], labels[tr])
                yp = clf.predict(X[all_idx[te]])
                within_fnrs.append(1.0 - recall_score(labels[te], yp, zero_division=0))
            within_fnr = float(np.mean(within_fnrs))

            # Heldout-FNR: train on all other tools
            train_i = [i for i in range(len(y)) if tools[i] != t]
            clf_loto = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
            clf_loto.fit(X[train_i], y[train_i])
            yp_loto = clf_loto.predict(X[all_idx])
            heldout_fnr = 1.0 - recall_score(labels, yp_loto, zero_division=0)

            effect_rows[t] = {
                "n_pos": n_pos, "n_neg": n_neg,
                "within_FNR": round(within_fnr, 4),
                "heldout_FNR": round(heldout_fnr, 4),
                "FNR_gap": round(heldout_fnr - within_fnr, 4),
            }

        if len(effect_rows) >= 2:
            loto_table[effect] = effect_rows
            max_held = max(r["heldout_FNR"] for r in effect_rows.values())
            max_gap = max(r["FNR_gap"] for r in effect_rows.values())
            print(f"\n  {effect}: max_heldout={max_held:.4f}  max_gap={max_gap:.4f}")
            hdr = f"    {'Tool':>12s} | {'N+':>4s} | {'withinFNR':>9s} | {'heldoutFNR':>10s} | {'FNR-Gap':>7s}"
            print(hdr)
            print("    " + "-" * 58)
            for t, r in sorted(effect_rows.items(), key=lambda x: -x[1]["heldout_FNR"]):
                print(f"    {t:>12s} | {r['n_pos']:>4d} | {r['within_FNR']:>9.4f} | {r['heldout_FNR']:>10.4f} | {r['FNR_gap']:>7.4f}")

    # ============================================================
    # 2. Baseline comparison
    # ============================================================
    print(f"\n{'=' * 95}")
    print("2. BASELINE COMPARISON: Worst-tool FNR")
    print(f"{'=' * 95}")

    baselines = {}
    tool_to_idx = {tt: i for i, tt in enumerate(tool_set)}

    for ei, effect in enumerate(effect_names):
        y = Y[:, ei]
        tool_stats = {}
        for t in tool_set:
            pos_i = [i for i, tt in enumerate(tools) if tt == t and y[i] == 1]
            neg_i = [i for i, tt in enumerate(tools) if tt == t and y[i] == 0]
            if len(pos_i) >= 5 and len(neg_i) >= 5:
                tool_stats[t] = {"pos": len(pos_i), "neg": len(neg_i)}
        if len(tool_stats) < 2:
            continue

        per_tool_fnr = {m: {} for m in ["pooled", "balanced", "tool_cond", "group_reweight"]}

        for t in tool_stats:
            pos_i = [i for i, tt in enumerate(tools) if tt == t and y[i] == 1]
            neg_i = [i for i, tt in enumerate(tools) if tt == t and y[i] == 0]
            all_i = pos_i + neg_i
            labels = np.array([1] * len(pos_i) + [0] * len(neg_i))
            train_i = np.array([i for i in range(len(y)) if tools[i] != t])
            X_test = X[all_i]

            # A: Pooled
            clf_p = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
            clf_p.fit(X[train_i], y[train_i])
            yp_p = clf_p.predict(X_test)
            per_tool_fnr["pooled"][t] = round(1.0 - recall_score(labels, yp_p, zero_division=0), 4)

            # B: Balanced pooled (exclude held-out tool from sizing)
            tool_train_sizes = {tt: sum(1 for i, tt2 in enumerate(tools) if tt2 == tt)
                                for tt in tool_stats if tt != t}
            min_sz = min(tool_train_sizes.values()) if tool_train_sizes else 0
            if min_sz >= 10:
                rng = np.random.default_rng(42)
                bal_idx = []
                for tt in tool_stats:
                    if tt == t:
                        continue
                    tt_i = [i for i, tt2 in enumerate(tools) if tt2 == tt]
                    sampled = rng.choice(tt_i, size=min(min_sz, len(tt_i)), replace=False)
                    bal_idx.extend(sampled)
                bal_idx = np.array(bal_idx)
                clf_b = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
                clf_b.fit(X[bal_idx], y[bal_idx])
                yp_b = clf_b.predict(X_test)
                per_tool_fnr["balanced"][t] = round(1.0 - recall_score(labels, yp_b, zero_division=0), 4)
            else:
                per_tool_fnr["balanced"][t] = None

            # C: Tool-conditioned
            tool_oh_train = np.zeros((len(train_i), len(tool_set)), dtype=np.float32)
            for j, idx in enumerate(train_i):
                tool_oh_train[j, tool_to_idx[tools[idx]]] = 1.0
            X_train_tc = np.concatenate([X[train_i], tool_oh_train], axis=1)

            tool_oh_test = np.zeros((len(all_i), len(tool_set)), dtype=np.float32)
            tool_oh_test[:, tool_to_idx[t]] = 1.0
            X_test_tc = np.concatenate([X[all_i], tool_oh_test], axis=1)

            clf_tc = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
            clf_tc.fit(X_train_tc, y[train_i])
            yp_tc = clf_tc.predict(X_test_tc)
            per_tool_fnr["tool_cond"][t] = round(1.0 - recall_score(labels, yp_tc, zero_division=0), 4)

            # D: Group reweight (inverse-frequency per-tool sample weights)
            sample_weights = np.ones(len(train_i), dtype=np.float64)
            for j, idx in enumerate(train_i):
                tt = tools[idx]
                if tt in tool_stats:
                    sample_weights[j] = 1.0 / max(tool_stats[tt]["pos"] + tool_stats[tt]["neg"], 1)
            sample_weights = sample_weights / sample_weights.mean()
            clf_dro = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
            clf_dro.fit(X[train_i], y[train_i], sample_weight=sample_weights)
            yp_dro = clf_dro.predict(X_test)
            per_tool_fnr["group_reweight"][t] = round(1.0 - recall_score(labels, yp_dro, zero_division=0), 4)

        # Summarize
        row_data = {"effect": effect, "n_tools": len(tool_stats)}
        for method in ["pooled", "balanced", "tool_cond", "group_reweight"]:
            valid = {t: v for t, v in per_tool_fnr[method].items() if v is not None}
            if valid:
                row_data[f"{method}_worstFNR"] = max(valid.values())
                row_data[f"{method}_worstTool"] = max(valid, key=valid.get)
                if method == "group_reweight":
                    row_data["group_dro_worstFNR"] = row_data[f"{method}_worstFNR"]
                    row_data["group_dro_worstTool"] = row_data[f"{method}_worstTool"]
        baselines[effect] = row_data

        print(f"\n  {effect}:")
        print(f"    {'Method':>15s} | {'Worst-FNR':>9s} | {'Worst Tool':>12s}")
        for method in ["pooled", "balanced", "tool_cond", "group_reweight"]:
            wf = row_data.get(f"{method}_worstFNR", 1.0)
            wt = row_data.get(f"{method}_worstTool", "N/A")
            print(f"    {method:>15s} | {wf:>9.4f} | {wt:>12s}")

    # Summary
    print(f"\n{'=' * 95}")
    print("3. SUMMARY")
    print(f"{'=' * 95}")
    print(f"{'Effect':<25s} | {'Pooled':>7s} | {'Balanced':>8s} | {'ToolCond':>8s} | {'GrpRew':>7s} | {'Best':>7s}")
    print("-" * 75)
    for effect in sorted(baselines):
        r = baselines[effect]
        p = r.get("pooled_worstFNR", 1.0)
        b = r.get("balanced_worstFNR", 1.0)
        t_val = r.get("tool_cond_worstFNR", 1.0)
        d = r.get("group_reweight_worstFNR", r.get("group_dro_worstFNR", 1.0))
        best = min(p, b, t_val, d)
        print(f"{effect:<25s} | {p:>7.4f} | {b:>8.4f} | {t_val:>8.4f} | {d:>7.4f} | {best:>7.4f}")

    # Save
    out = Path(__file__).resolve().parent.parent / "analysis" / f"baseline_comparison_{data_name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"loto_table": loto_table, "baselines": baselines}, indent=2))
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
