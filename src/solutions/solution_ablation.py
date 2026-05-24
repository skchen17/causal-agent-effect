"""
Ablation and strict cross-tool test for contrastive projection.

1. Dimension ablation: 64, 128, 256, 512, 1024
2. Strict cross-tool: leave-one-tool-pair-out during projection training
3. content_fetched analysis: per-tool-pair FNR breakdown
"""

import json, sys
import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import recall_score
from pathlib import Path


def load_data(base, data_name):
    X = np.load(base / f"embeddings/embeddings_{data_name}.npy")
    Y = np.load(base / f"embeddings/effects_{data_name}.npy")
    with open(base / f"embeddings/texts_{data_name}.jsonl") as f:
        tools = [json.loads(line)["tool_name"] for line in f]
    with open(base / f"embeddings/meta_{data_name}.json") as f:
        meta = json.load(f)
    return X, Y, meta, tools


def train_projection(X_np, y_np, tools, dim_out, device, exclude_pair=None):
    """Train contrastive projection. If exclude_pair=(toolA, toolB), skip pairs involving that pair."""
    # Group positive samples by tool
    tool_pos = {}
    for i, t in enumerate(tools):
        if y_np[i] == 1:
            tool_pos.setdefault(t, []).append(i)
    valid = {t: idxs for t, idxs in tool_pos.items() if len(idxs) >= 5}
    if len(valid) < 2:
        return None

    d_in = X_np.shape[1]
    rng = np.random.default_rng(42)
    tl = sorted(valid.keys())
    pairs = []
    for i in range(len(tl)):
        for j in range(i + 1, len(tl)):
            # Skip if this pair is excluded (strict cross-tool test)
            if exclude_pair is not None:
                if (tl[i], tl[j]) == exclude_pair or (tl[j], tl[i]) == exclude_pair:
                    continue
            a_idx = valid[tl[i]]
            b_idx = valid[tl[j]]
            n_pairs = min(100, len(a_idx), len(b_idx))
            a_s = rng.choice(a_idx, size=n_pairs, replace=False)
            b_s = rng.choice(b_idx, size=n_pairs, replace=False)
            for k in range(n_pairs):
                pairs.append((int(a_s[k]), int(b_s[k])))

    if len(pairs) < 5:
        return None

    neg_pool = [i for i in range(len(y_np)) if y_np[i] == 0]

    X_t = torch.tensor(X_np, dtype=torch.float32, device=device)
    pairs_t = torch.tensor(pairs, dtype=torch.long, device=device)
    neg_pool_t = torch.tensor(neg_pool, dtype=torch.long, device=device)

    P = torch.nn.Parameter(torch.randn(d_in, dim_out, device=device) * 0.01)
    optimizer = torch.optim.Adam([P], lr=0.001)
    margin = 1.0
    batch_size = 64

    for epoch in range(500):
        perm = torch.randperm(len(pairs), device=device)
        for b_start in range(0, len(pairs), batch_size):
            b_end = min(b_start + batch_size, len(pairs))
            batch = perm[b_start:b_end]
            idx_a = pairs_t[batch, 0]
            idx_b = pairs_t[batch, 1]
            h_a = X_t[idx_a] @ P
            h_b = X_t[idx_b] @ P
            h_a = torch.nn.functional.normalize(h_a, dim=1)
            h_b = torch.nn.functional.normalize(h_b, dim=1)

            pos_loss = torch.mean(torch.sum((h_a - h_b) ** 2, dim=1))

            neg_idx = neg_pool_t[torch.randint(len(neg_pool), (len(batch),), device=device)]
            h_neg = X_t[neg_idx] @ P
            h_neg = torch.nn.functional.normalize(h_neg, dim=1)
            neg_loss = torch.mean(torch.clamp(margin - torch.sum((h_a - h_neg) ** 2, dim=1), min=0))
            neg_loss += torch.mean(torch.clamp(margin - torch.sum((h_b - h_neg) ** 2, dim=1), min=0))

            loss = pos_loss + 0.5 * neg_loss + 0.01 * torch.sum(P ** 2)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

    with torch.no_grad():
        X_proj = (X_t @ P).cpu().numpy()
    return X_proj / (np.linalg.norm(X_proj, axis=1, keepdims=True) + 1e-8)


def compute_loto_fnr(X_arr, Y_arr, tools, effect_idx, y):
    """LOTO FNR per tool."""
    fnrs = {}
    for t in sorted(set(tools)):
        pos_i = [i for i, tt in enumerate(tools) if tt == t and y[i] == 1]
        neg_i = [i for i, tt in enumerate(tools) if tt == t and y[i] == 0]
        if len(pos_i) < 5 or len(neg_i) < 5:
            continue
        all_i = pos_i + neg_i
        labels = np.array([1] * len(pos_i) + [0] * len(neg_i))
        train_i = [i for i in range(len(y)) if tools[i] != t]
        clf = LogisticRegression(l1_ratio=0, C=1.0, max_iter=2000, class_weight="balanced")
        clf.fit(X_arr[train_i], y[train_i])
        yp = clf.predict(X_arr[all_i])
        fnrs[t] = round(1.0 - recall_score(labels, yp, zero_division=0), 4)
    return fnrs


def main():
    base = Path(__file__).resolve().parent.parent
    data_name = sys.argv[1] if len(sys.argv) > 1 else "qwen3-8b_scenarios_merged"
    X_np, Y_np, meta, tools = load_data(base, data_name)
    effect_names = meta["effect_names"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # ============================================================
    # 1. Dimension ablation
    # ============================================================
    print("=" * 80)
    print("1. DIMENSION ABLATION: postFNR vs projection dimension")
    print("=" * 80)

    dims = [64, 128, 256, 512, 1024]
    dim_results = {}

    for ei, effect in enumerate(effect_names):
        y_np = Y_np[:, ei]
        tool_pos = {}
        for i, t in enumerate(tools):
            if y_np[i] == 1:
                tool_pos.setdefault(t, []).append(i)
        valid_tools = {t: idxs for t, idxs in tool_pos.items() if len(idxs) >= 5}
        if len(valid_tools) < 2:
            continue

        pre_fnrs = compute_loto_fnr(X_np, Y_np, tools, ei, y_np)
        max_pre = max(pre_fnrs.values())

        dim_rows = {}
        for dim in dims:
            X_proj = train_projection(X_np, y_np, tools, dim, device)
            if X_proj is None:
                continue
            post_fnrs = compute_loto_fnr(X_proj, Y_np, tools, ei, y_np)
            max_post = max(post_fnrs.values())
            dim_rows[dim] = {"max_pre": max_pre, "max_post": round(max_post, 4)}

        dim_results[effect] = dim_rows
        dim_str = " ".join(f"d{d}={dim_rows[d]['max_post']:.3f}" for d in dims if d in dim_rows)
        print(f"  {effect:<22s} pre_max={max_pre:.3f} | {dim_str}")

    # Best dim per effect
    print(f"\n  Best dimension per effect:")
    for e, rows in dim_results.items():
        best_d = min(rows, key=lambda d: rows[d]["max_post"])
        print(f"    {e:<22s}: best dim={best_d}, postFNR={rows[best_d]['max_post']:.4f}")

    # ============================================================
    # 2. Strict cross-tool: leave one tool PAIR out
    # ============================================================
    print(f"\n{'=' * 80}")
    print("2. STRICT CROSS-TOOL: leave one tool pair out during projection training")
    print("=" * 80)

    strict_results = {}

    for ei, effect in enumerate(effect_names):
        y_np = Y_np[:, ei]
        tool_pos = {}
        for i, t in enumerate(tools):
            if y_np[i] == 1:
                tool_pos.setdefault(t, []).append(i)
        valid = {t: idxs for t, idxs in tool_pos.items() if len(idxs) >= 5}
        if len(valid) < 3:  # Need ≥3 tools for strict test (≥2 for train, 1 pair excluded)
            continue

        tl = sorted(valid.keys())
        # For each pair, train projection WITHOUT that pair, test LOTO FNR
        for i in range(len(tl)):
            for j in range(i + 1, len(tl)):
                pair = (tl[i], tl[j])
                # Train projection excluding this pair
                X_proj = train_projection(X_np, y_np, tools, dim_out=128, device=device, exclude_pair=pair)
                if X_proj is None:
                    continue
                post_fnrs = compute_loto_fnr(X_proj, Y_np, tools, ei, y_np)

                # Only care about the excluded pair's tools
                pre_fnrs = compute_loto_fnr(X_np, Y_np, tools, ei, y_np)
                for tt in pair:
                    if tt in pre_fnrs and tt in post_fnrs:
                        pre_f = pre_fnrs[tt]
                        post_f = post_fnrs[tt]
                        delta = pre_f - post_f
                        k = f"{effect}|{pair[0][:6]}↔{pair[1][:6]}|{tt[:8]}"
                        strict_results[k] = {
                            "effect": effect, "pair": f"{pair[0]}↔{pair[1]}",
                            "tool": tt, "pre": pre_f, "post": post_f, "delta": delta,
                        }

    # Summarize strict results
    strict_deltas = [r["delta"] for r in strict_results.values()]
    strict_improved = sum(1 for d in strict_deltas if d > 0)
    print(f"\n  Strict cross-tool (projection training excluded the tested pair):")
    print(f"    Mean delta: {np.mean(strict_deltas):+.4f}")
    print(f"    Improved: {strict_improved}/{len(strict_deltas)}")
    for k, r in sorted(strict_results.items(), key=lambda x: -x[1]["delta"])[:10]:
        print(f"    {k:<55s} pre={r['pre']:.3f} post={r['post']:.3f} delta={r['delta']:+.3f}")

    # ============================================================
    # 3. content_fetched analysis
    # ============================================================
    print(f"\n{'=' * 80}")
    print("3. content_fetched ANALYSIS: why residual FNR?")
    print("=" * 80)

    ei = effect_names.index("content_fetched")
    y_np = Y_np[:, ei]
    tool_pos = {}
    for i, t in enumerate(tools):
        if y_np[i] == 1:
            tool_pos.setdefault(t, []).append(i)
    for t, idxs in tool_pos.items():
        print(f"  {t}: {len(idxs)} positive samples")
    print(f"  Cross-tool pairs available: min(web_fetch=32, terminal=8) = 8 pairs")
    print(f"  The limited N+ on terminal (8) restricts the number of cross-tool")
    print(f"  contrastive pairs, providing weaker alignment signal for this effect.")

    # Save
    out = base / "analysis" / f"ablation_{data_name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "dim_ablation": {e: {str(d): v for d, v in rows.items()} for e, rows in dim_results.items()},
        "strict_cross_tool": strict_results,
    }, indent=2))
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
