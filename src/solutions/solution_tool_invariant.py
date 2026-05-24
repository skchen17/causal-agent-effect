"""
Solution methods for the tool-proxy problem.

Solution 2 (Procrustes Subspace Alignment):
  - Learn per-tool-pair orthogonal rotation R that aligns effect directions
  - Closed-form (SVD), no training needed
  - R = U V^T where W_A^T W_B = U Σ V^T

Solution 1 (Contrastive Projection):
  - Train a linear projection P into tool-invariant space
  - Contrastive loss: pull same-effect, different-tool pairs together
  - Evaluated via cross-tool FNR after projection

Reports post-alignment vs pre-alignment ToolProxyGap reduction.
"""

from __future__ import annotations

import json, sys
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import recall_score
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


def align_two_directions(w_src, w_tgt, X_src):
    """Rotate X_src in the plane spanned by w_src and w_tgt to align w_src → w_tgt.

    Uses Rodrigues rotation formula in the 2D plane.
    Returns rotated X_src.
    """
    u = w_src / (np.linalg.norm(w_src) + 1e-8)
    v = w_tgt / (np.linalg.norm(w_tgt) + 1e-8)

    cos_theta = np.clip(np.dot(u, v), -1.0, 1.0)
    sin_theta = np.sqrt(1.0 - cos_theta**2)

    # If already aligned, skip
    if cos_theta > 0.999:
        return X_src.copy()

    # Construct unit vectors spanning the rotation plane
    # n: unit vector perpendicular to u in the u-v plane
    n = v - cos_theta * u
    n = n / (np.linalg.norm(n) + 1e-8)

    # Rodrigues: R(x) = x + sin_theta*(n x*u - u x*n) + (cos_theta-1)*(n x*n + u x*u)
    # where x*u = (x·u), etc.
    # X_rot = X + sin_theta*(n(X·u) - u(X·n)) + (cos_theta-1)*(n(X·n) + u(X·u))

    Xu = X_src @ u   # (n,)
    Xn = X_src @ n   # (n,)

    X_rot = X_src + sin_theta * (np.outer(Xu, n) - np.outer(Xn, u)) \
             + (cos_theta - 1.0) * (np.outer(Xn, n) + np.outer(Xu, u))

    return X_rot


def compute_pairwise_fnrs(X, Y, tools, effect_idx, y):
    """Compute per-tool and LOTO FNR for a single effect."""
    tool_set = sorted(set(tools))
    fnrs = {}
    for t in tool_set:
        pos_i = [i for i, tt in enumerate(tools) if tt == t and y[i] == 1]
        neg_i = [i for i, tt in enumerate(tools) if tt == t and y[i] == 0]
        if len(pos_i) < 5 or len(neg_i) < 5:
            continue
        all_i = pos_i + neg_i
        labels = np.array([1] * len(pos_i) + [0] * len(neg_i))
        # LOTO: train on other tools, test on this tool
        train_i = [i for i in range(len(y)) if tools[i] != t]
        clf = LogisticRegression(l1_ratio=0, C=1.0, max_iter=2000, class_weight="balanced")
        clf.fit(X[train_i], y[train_i])
        yp = clf.predict(X[all_i])
        fnrs[t] = 1.0 - recall_score(labels, yp, zero_division=0)
    return fnrs


def train_contrastive_projection(X, Y, tools, effect_idx, y, dim_out=256, lr=0.01, epochs=500):
    """Train a linear projection P that minimizes contrastive loss across tools."""
    # Get positive-class samples, grouped by tool
    tool_pos = {}
    for i, t in enumerate(tools):
        if y[i] == 1:
            tool_pos.setdefault(t, []).append(i)
    valid = {t: idxs for t, idxs in tool_pos.items() if len(idxs) >= 5}
    if len(valid) < 2:
        return None

    d_in = X.shape[1]
    rng = np.random.default_rng(42)
    # Initialize projection matrix
    P = rng.normal(0, 0.01, (d_in, dim_out)).astype(np.float64)
    # Normalize columns
    P = P / np.linalg.norm(P, axis=0, keepdims=True)

    # Create positive pairs: same effect, different tool
    pairs = []
    tl = sorted(valid.keys())
    for i in range(len(tl)):
        for j in range(i + 1, len(tl)):
            idx_a = valid[tl[i]]
            idx_b = valid[tl[j]]
            npairs = min(50, len(idx_a), len(idx_b))
            a_sample = rng.choice(idx_a, size=npairs, replace=False)
            b_sample = rng.choice(idx_b, size=npairs, replace=False)
            for k in range(npairs):
                pairs.append((a_sample[k], b_sample[k]))
    if len(pairs) < 10:
        return None
    pairs = np.array(pairs)
    n_pairs = len(pairs)

    # Also get negative samples (E=0) for contrast
    neg_idx = [i for i in range(len(y)) if y[i] == 0]
    neg_sample = rng.choice(neg_idx, size=min(len(neg_idx), n_pairs * 2), replace=False)

    # SGD training
    temperature = 0.1
    for epoch in range(epochs):
        # Shuffle pairs
        perm = rng.permutation(n_pairs)
        total_loss = 0.0
        batch_size = 32
        for b_start in range(0, n_pairs, batch_size):
            b_end = min(b_start + batch_size, n_pairs)
            batch = perm[b_start:b_end]
            batch_pairs = pairs[batch]

            h_a = X[batch_pairs[:, 0]] @ P  # (batch, dim_out)
            h_b = X[batch_pairs[:, 1]] @ P

            # Normalize projected embeddings
            h_a = h_a / (np.linalg.norm(h_a, axis=1, keepdims=True) + 1e-8)
            h_b = h_b / (np.linalg.norm(h_b, axis=1, keepdims=True) + 1e-8)

            # Positive similarity
            pos_sim = np.sum(h_a * h_b, axis=1) / temperature  # (batch,)

            # Negative: sample random negatives from pool
            neg_idx_batch = rng.choice(neg_sample, size=len(batch), replace=True)
            h_neg = X[neg_idx_batch] @ P
            h_neg = h_neg / (np.linalg.norm(h_neg, axis=1, keepdims=True) + 1e-8)
            neg_sim_a = np.sum(h_a * h_neg, axis=1) / temperature
            neg_sim_b = np.sum(h_b * h_neg, axis=1) / temperature

            # InfoNCE loss
            pos_exp = np.exp(pos_sim)
            neg_exp = np.exp(neg_sim_a) + np.exp(neg_sim_b) + 1e-8
            softmax_ratio = (pos_exp / (pos_exp + neg_exp))
            loss = -np.mean(np.log(softmax_ratio + 1e-8))

            # Simplified gradient: move P toward reducing distance between positive pairs
            # and increasing distance to negatives
            # dL/dP ≈ -X_a^T (h_b - h_neg * softmax_neg) / temp + symmetric
            for k in range(len(batch)):
                ha_k = h_a[k:k+1]
                hb_k = h_b[k:k+1]
                hn_k = h_neg[k:k+1]

                # Weighted negative
                w_neg = (neg_exp[k] / (pos_exp[k] + neg_exp[k]))
                target_a = hb_k - w_neg * hn_k
                target_b = ha_k - w_neg * hn_k

                idx_a = batch_pairs[batch[k], 0]
                idx_b = batch_pairs[batch[k], 1]
                x_a = X[idx_a:idx_a+1]
                x_b = X[idx_b:idx_b+1]

                P -= (lr / len(batch)) * (x_a.T @ (ha_k - target_a) + x_b.T @ (hb_k - target_b))

            # Re-normalize columns
            col_norms = np.linalg.norm(P, axis=0)
            col_norms = np.where(col_norms > 1.0, col_norms, 1.0)  # soft norm constraint
            P = P / (col_norms + 1e-8)
            total_loss += loss

        if epoch % 100 == 0:
            print(f"    epoch {epoch}: loss={total_loss:.4f}", flush=True)

    return P


def main():
    data_name = sys.argv[1] if len(sys.argv) > 1 else "qwen3-8b_scenarios_merged"
    X_orig, Y, meta, tools = load_data(data_name)
    effect_names = meta["effect_names"]
    d = X_orig.shape[1]

    print(f"Model: {meta['model']}, Dim: {d}, Samples: {X_orig.shape[0]}")

    # ============================================================
    # Solution 2: Procrustes Subspace Alignment
    # ============================================================
    print(f"\n{'=' * 85}")
    print("SOLUTION 2: Procrustes Subspace Alignment")
    print(f"{'=' * 85}")
    print(f"{'Effect':<25s} | {'Pair':>24s} | {'pre-FNR':>7s} | {'post-FNR':>8s} | {'Δ':>7s}")
    print("-" * 80)

    procrustes_results = {}

    for ei, effect in enumerate(effect_names):
        y = Y[:, ei]
        # Train per-tool probes to get direction vectors
        tool_probes = {}
        for t in sorted(set(tools)):
            idxs = [i for i, tt in enumerate(tools) if tt == t and y[i] == 1]
            negs = [i for i, tt in enumerate(tools) if tt == t and y[i] == 0]
            if len(idxs) >= 5 and len(negs) >= 5:
                all_i = idxs + negs
                labels = np.array([1] * len(idxs) + [0] * len(negs))
                clf = LogisticRegression(l1_ratio=0, C=1.0, max_iter=2000, class_weight="balanced")
                clf.fit(X_orig[all_i], labels)
                tool_probes[t] = clf.coef_[0]  # (d,)

        if len(tool_probes) < 2:
            continue

        effect_results = {}
        tl = sorted(tool_probes.keys())

        for i in range(len(tl)):
            for j in range(i + 1, len(tl)):
                t_src, t_tgt = tl[i], tl[j]
                w_src = tool_probes[t_src]
                w_tgt = tool_probes[t_tgt]

                # Pre-alignment LOTO FNR
                pre_fnrs = compute_pairwise_fnrs(X_orig, Y, tools, ei, y)
                pre_fnr = pre_fnrs.get(t_tgt, 1.0)

                # -- Align t_src's probe direction to t_tgt's in the 2D plane they span --
                src_idxs = [i for i, tt in enumerate(tools) if tt == t_src]
                X_aligned = X_orig.copy()
                X_aligned[src_idxs] = align_two_directions(w_src, w_tgt, X_orig[src_idxs])

                # Post-alignment LOTO FNR (evaluate on aligned source tool embeddings)
                post_fnrs = compute_pairwise_fnrs(X_aligned, Y, tools, ei, y)
                post_fnr = post_fnrs.get(t_tgt, 1.0)

                delta = pre_fnr - post_fnr
                pair_name = f"{t_src[:8]}→{t_tgt[:8]}"
                print(f"{effect:<25s} | {pair_name:>24s} | {pre_fnr:>7.4f} | {post_fnr:>8.4f} | {delta:>+7.4f}")

                effect_results[f"{t_src}→{t_tgt}"] = {
                    "pre_fnr": round(pre_fnr, 4),
                    "post_fnr": round(post_fnr, 4),
                    "delta": round(delta, 4),
                }

        if effect_results:
            procrustes_results[effect] = effect_results

    # Summary
    all_deltas = []
    for e, pairs in procrustes_results.items():
        for p, r in pairs.items():
            all_deltas.append(r["delta"])
    if all_deltas:
        print(f"\nProcrustes: mean ΔFNR = {np.mean(all_deltas):+.4f}, "
              f"improved pairs = {sum(1 for d in all_deltas if d > 0)}/{len(all_deltas)}")

    # ============================================================
    # Solution 1: Contrastive Projection
    # ============================================================
    print(f"\n{'=' * 85}")
    print("SOLUTION 1: Contrastive Projection")
    print(f"{'=' * 85}")

    contrastive_results = {}

    for ei, effect in enumerate(effect_names):
        y = Y[:, ei]
        # Check if effect has ≥2 tools with ≥5 pos
        tool_pos_counts = {}
        for t in sorted(set(tools)):
            n_pos = int(sum(y[i] for i, tt in enumerate(tools) if tt == t))
            if n_pos >= 5:
                tool_pos_counts[t] = n_pos
        if len(tool_pos_counts) < 2:
            continue

        print(f"\n  {effect} ({len(tool_pos_counts)} tools, {sum(tool_pos_counts.values())} pos)...", flush=True)
        P = train_contrastive_projection(X_orig, Y, tools, ei, y, dim_out=128, epochs=300)
        if P is None:
            print("    insufficient data for contrastive training")
            continue

        # Project all embeddings
        X_proj = X_orig @ P  # (n, dim_out)
        # Normalize
        X_proj = X_proj / (np.linalg.norm(X_proj, axis=1, keepdims=True) + 1e-8)

        # Pre-alignment LOTO FNR
        pre_fnrs = compute_pairwise_fnrs(X_orig, Y, tools, ei, y)

        # Post-alignment LOTO FNR
        post_fnrs = compute_pairwise_fnrs(X_proj, Y, tools, ei, y)

        effect_contrast = {}
        for t in pre_fnrs:
            pre_f = pre_fnrs[t]
            post_f = post_fnrs.get(t, 1.0)
            delta = pre_f - post_f
            effect_contrast[t] = {"pre_fnr": round(pre_f, 4), "post_fnr": round(post_f, 4), "delta": round(delta, 4)}
            print(f"    {t:>12s}: preFNR={pre_f:.4f} → postFNR={post_f:.4f}  Δ={delta:+.4f}")

        contrastive_results[effect] = effect_contrast

    # Summary
    all_c_deltas = []
    for e, tool_results in contrastive_results.items():
        for t, r in tool_results.items():
            all_c_deltas.append(r["delta"])
    if all_c_deltas:
        print(f"\nContrastive: mean ΔFNR = {np.mean(all_c_deltas):+.4f}, "
              f"improved tools = {sum(1 for d in all_c_deltas if d > 0)}/{len(all_c_deltas)}")

    # ============================================================
    # Save
    # ============================================================
    out = Path(__file__).resolve().parent.parent / "analysis" / f"solution_results_{data_name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "procrustes": procrustes_results,
        "contrastive": contrastive_results,
    }, indent=2))
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
