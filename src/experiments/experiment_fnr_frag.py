"""
FNR and Frag analysis experiment.

1. Deployed-probe per-tool FNR (trained on all tools)
2. LOTO diagnostic FNR
3. Spearman correlation: pIIA-Drop vs FNR-Gap
4. Pos-class Frag: cosine distance between per-tool positive-class means
"""

from __future__ import annotations
import json, sys
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import recall_score
from scipy.stats import spearmanr
from pathlib import Path


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
        with open(texts_path) as f:
            tools = [json.loads(line).get("tool_name", "unknown") for line in f]
    return X, Y, meta, tools


def main():
    data_name = sys.argv[1] if len(sys.argv) > 1 else "qwen3-8b_scenarios_merged"
    X, Y, meta, tools = load_data(data_name)
    effect_names = meta["effect_names"]
    tool_set = sorted(set(tools))

    print(f"Model: {meta['model']}, Dim: {X.shape[1]}, Samples: {X.shape[0]}")

    # ============================================================
    # 0. MultiMech verification: which effects are multi-mechanism?
    # ============================================================
    print(f"\n{'=' * 85}")
    print("0. MULTIMECH VERIFICATION: P(E=1 | T) per effect per tool")
    print(f"{'=' * 85}")
    multimech = {}
    for ei, effect in enumerate(effect_names):
        y = Y[:, ei]
        probs = {}
        for t in sorted(set(tools)):
            idxs = [i for i, tt in enumerate(tools) if tt == t]
            n = len(idxs)
            pos = int(y[idxs].sum())
            if n >= 5:
                probs[t] = round(pos / n, 4)
        n_tools_pos = sum(1 for p in probs.values() if p > 0)
        is_mm = n_tools_pos >= 2
        multimech[effect] = {"tools": probs, "n_tools_pos": n_tools_pos, "is_multi_mech": is_mm}
        marker = "✓ MultiMech" if is_mm else "  single-mech"
        tools_str = ", ".join(f"{t}={p:.2f}" for t, p in sorted(probs.items(), key=lambda x: -x[1]))
        print(f"  {marker} {effect:<25s} | {tools_str}")

    # ============================================================
    # 1. Deployed probe per-tool FNR
    # ============================================================
    print(f"\n{'=' * 85}")
    print("1. DEPLOYED PROBE FNR (trained on all tools)")
    print(f"{'=' * 85}")

    deployed_fnrs = {}
    for ei, effect in enumerate(effect_names):
        y = Y[:, ei]
        clf = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
        clf.fit(X, y)
        for t in tool_set:
            idxs = [i for i, tt in enumerate(tools) if tt == t]
            pos = int(y[idxs].sum())
            if pos < 5:
                continue
            labels = y[idxs]
            y_pred = clf.predict(X[idxs])
            fnr = 1.0 - recall_score(labels, y_pred, zero_division=0)
            if fnr > 0.05:
                print(f"  {effect:<25s} {t:>12s}: FNR={fnr:.4f} (N+={pos})")
            if effect not in deployed_fnrs:
                deployed_fnrs[effect] = {}
            deployed_fnrs[effect][t] = round(float(fnr), 4)

    # ============================================================
    # 2. LOTO FNR summary
    # ============================================================
    print(f"\n{'=' * 85}")
    print("2. LOTO DIAGNOSTIC FNR (leave-one-tool-out)")
    print(f"{'=' * 85}")

    loto_fnrs = {}
    for ei, effect in enumerate(effect_names):
        y = Y[:, ei]
        effect_loto = {}
        for t in tool_set:
            pos_idx = [i for i, tt in enumerate(tools) if tt == t and y[i] == 1]
            neg_idx = [i for i, tt in enumerate(tools) if tt == t and y[i] == 0]
            n_pos, n_neg = len(pos_idx), len(neg_idx)
            if n_pos < 5 or n_neg < 5:
                continue
            all_idx = pos_idx + neg_idx
            labels = np.array([1] * n_pos + [0] * n_neg)
            train_idx = [i for i in range(len(y)) if tools[i] != t]
            clf = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
            clf.fit(X[train_idx], y[train_idx])
            y_pred = clf.predict(X[all_idx])
            fnr = 1.0 - recall_score(labels, y_pred, zero_division=0)
            effect_loto[t] = round(float(fnr), 4)

        if len(effect_loto) >= 2:
            loto_fnrs[effect] = effect_loto
            vals = list(effect_loto.values())
            tools_str = ",".join(f"{t}={v:.2f}" for t, v in sorted(effect_loto.items(), key=lambda x: -x[1]))
            print(f"  {effect:<25s} max={max(vals):.3f} min={min(vals):.3f} gap={max(vals)-min(vals):.3f} | {tools_str}")

    # ============================================================
    # 3. Spearman: pIIA-Drop vs FNR-Gap
    # ============================================================
    print(f"\n{'=' * 85}")
    print("3. SPEARMAN: pIIA-Drop vs FNR-Gap")
    print(f"{'=' * 85}")

    iia_drops = {}  # initialize for safe reference in section 4
    iia_path = Path(__file__).resolve().parent.parent / "analysis" / f"iia_true_{data_name}.json"
    if iia_path.exists():
        with open(iia_path) as f:
            iia_data = json.load(f)
        iia_drops = {r["effect"]: -r["gap"] for r in iia_data}

        common = [e for e in loto_fnrs if e in iia_drops]
        if len(common) >= 3:
            drops = [iia_drops[e] for e in common]
            max_fnrs = [max(loto_fnrs[e].values()) for e in common]
            fnr_gaps = [max(loto_fnrs[e].values()) - min(loto_fnrs[e].values()) for e in common]

            r1, p1 = spearmanr(drops, max_fnrs)
            r2, p2 = spearmanr(drops, fnr_gaps)

            print(f"  {'Effect':<25s} {'pIIA-Drop':>9s} {'Max FNR':>8s} {'FNR-Gap':>8s}")
            for e in common:
                print(f"  {e:<25s} {iia_drops[e]:>9.4f} {max(loto_fnrs[e].values()):>8.4f} {max(loto_fnrs[e].values())-min(loto_fnrs[e].values()):>8.4f}")
            print(f"\n  ρ(pIIA-Drop, Max FNR) = {r1:.4f} (p={p1:.4f})")
            print(f"  ρ(pIIA-Drop, FNR-Gap)  = {r2:.4f} (p={p2:.4f})")
            print(f"  n={len(common)} effects")
        else:
            print("  Insufficient common effects for Spearman")
    else:
        print(f"  IIA data not found at {iia_path}")

    # ============================================================
    # 4. Pos-class Frag: cosine distance
    # ============================================================
    print(f"\n{'=' * 85}")
    print("4. POS-CLASS FRAG (cosine distance between per-tool positive means)")
    print(f"{'=' * 85}")

    for ei, effect in enumerate(effect_names):
        y = Y[:, ei]
        tool_means = {}
        for t in tool_set:
            idxs = [i for i, tt in enumerate(tools) if tt == t and y[i] == 1]
            if len(idxs) >= 3:
                tool_means[t] = X[idxs].mean(axis=0)

        if len(tool_means) < 2:
            continue

        tl = sorted(tool_means.keys())
        dists = []
        for i in range(len(tl)):
            for j in range(i + 1, len(tl)):
                a = tool_means[tl[i]]
                b = tool_means[tl[j]]
                cos_sim = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))
                dists.append(1.0 - cos_sim)

        avg_d = float(np.mean(dists))
        max_d = float(np.max(dists))

        fnr_str = ""
        if effect in loto_fnrs:
            v = list(loto_fnrs[effect].values())
            fnr_str = f"FNR_gap={max(v)-min(v):.3f}"

        iia_str = ""
        if effect in iia_drops:
            iia_str = f"IIAdrop={iia_drops[effect]:.3f}"

        print(f"  {effect:<25s} avgCosDist={avg_d:.4f} maxCosDist={max_d:.4f}  {fnr_str}  {iia_str}  ntools={len(tl)}")

    # Save
    # Also compute FPR for SafeInv
    fpr_data = {}
    for ei, effect in enumerate(effect_names):
        y = Y[:, ei]
        clf = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
        clf.fit(X, y)
        effect_fpr = {}
        for t in tool_set:
            idxs = [i for i, tt in enumerate(tools) if tt == t]
            pos = int(y[idxs].sum())
            neg = len(idxs) - pos
            if pos < 3 or neg < 3:
                continue
            y_pred = clf.predict(X[idxs])
            fp = sum((y[idxs] == 0) & (y_pred == 1))
            fpr = fp / max(neg, 1)
            effect_fpr[t] = round(float(fpr), 4)
        if effect_fpr:
            fpr_data[effect] = effect_fpr

    # Alpha variants for Theorem 1 safety accounting:
    # - alpha_deployed_aux uses auxiliary probes trained on all data.
    # - alpha_loto excludes the held-out tool for every auxiliary probe, matching
    #   the LOTO coverage-missing stress-test suite used for beta_LOTO.
    alpha_deployed_aux = {}
    alpha_loto = {}
    for ei, effect in enumerate(effect_names):
        y = Y[:, ei]
        effect_alpha_deployed = {}
        effect_alpha_loto = {}
        for t in tool_set:
            e1_idx = [i for i, tt in enumerate(tools) if tt == t and y[i] == 1]
            if len(e1_idx) < 5:
                continue
            any_other_deployed = np.zeros(len(e1_idx), dtype=bool)
            any_other_loto = np.zeros(len(e1_idx), dtype=bool)
            train_idx_loto = [i for i in range(len(y)) if tools[i] != t]
            for ej, other in enumerate(effect_names):
                if ej == ei:
                    continue
                y_other = Y[:, ej]
                if len(np.unique(y_other)) >= 2:
                    yp_other = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced").fit(X, y_other).predict(X[e1_idx])
                    any_other_deployed = any_other_deployed | (yp_other > 0.5)
                if len(np.unique(y_other[train_idx_loto])) >= 2:
                    yp_other_loto = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced").fit(
                        X[train_idx_loto], y_other[train_idx_loto]
                    ).predict(X[e1_idx])
                    any_other_loto = any_other_loto | (yp_other_loto > 0.5)
            effect_alpha_deployed[t] = round(float(np.mean(any_other_deployed)), 4)
            effect_alpha_loto[t] = round(float(np.mean(any_other_loto)), 4)
        if effect_alpha_deployed:
            alpha_deployed_aux[effect] = effect_alpha_deployed
            alpha_loto[effect] = effect_alpha_loto

    out = Path(__file__).resolve().parent.parent / "analysis" / f"fnr_frag_{data_name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "multimech": multimech,
        "deployed_fnrs": deployed_fnrs,
        "loto_fnrs": loto_fnrs,
        "fpr": fpr_data,
        "alpha": alpha_loto,
        "alpha_loto": alpha_loto,
        "alpha_deployed_aux": alpha_deployed_aux,
    }, indent=2))
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
