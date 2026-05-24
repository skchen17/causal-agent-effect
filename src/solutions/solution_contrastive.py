"""Contrastive Projection: learn tool-invariant linear projection with PyTorch autograd.

Uses Siamese-style contrastive loss:
  L = |P(h_a) - P(h_b)|^2 for cross-tool, same-effect pairs
    + max(0, margin - |P(h_a) - P(h_neg)|^2) for effect-negative pairs
"""

import json, sys
import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import recall_score
from pathlib import Path


def main():
    base = Path(__file__).resolve().parent.parent
    data_name = sys.argv[1] if len(sys.argv) > 1 else "qwen3-8b_scenarios_merged"

    X_np = np.load(base / f"embeddings/embeddings_{data_name}.npy")
    Y_np = np.load(base / f"embeddings/effects_{data_name}.npy")
    with open(base / f"embeddings/texts_{data_name}.jsonl") as f:
        tools = [json.loads(line)["tool_name"] for line in f]
    with open(base / f"embeddings/meta_{data_name}.json") as f:
        effect_names = json.load(f)["effect_names"]

    d_in = X_np.shape[1]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}, Dim: {d_in}")

    results = {}

    for ei, effect in enumerate(effect_names):
        y_np = Y_np[:, ei]

        # Group positive samples by tool
        tool_pos = {}
        for i, t in enumerate(tools):
            if y_np[i] == 1:
                tool_pos.setdefault(t, []).append(i)
        valid = {t: idxs for t, idxs in tool_pos.items() if len(idxs) >= 5}
        if len(valid) < 2:
            continue

        n_pos = sum(len(v) for v in valid.values())
        print(f"\n  {effect}: {len(valid)} tools, {n_pos} pos samples", flush=True)

        # Create positive pairs: same effect, different tool
        rng = np.random.default_rng(42)
        tl = sorted(valid.keys())
        pairs = []
        for i in range(len(tl)):
            for j in range(i + 1, len(tl)):
                a_idx = valid[tl[i]]
                b_idx = valid[tl[j]]
                n_pairs = min(100, len(a_idx), len(b_idx))
                a_sampled = rng.choice(a_idx, size=n_pairs, replace=False)
                b_sampled = rng.choice(b_idx, size=n_pairs, replace=False)
                for k in range(n_pairs):
                    pairs.append((int(a_sampled[k]), int(b_sampled[k])))

        if len(pairs) < 5:
            print(f"    insufficient pairs ({len(pairs)})")
            continue

        # Negative pool: E=0 samples
        neg_pool = [i for i in range(len(y_np)) if y_np[i] == 0]

        # Convert to tensors
        X_t = torch.tensor(X_np, dtype=torch.float32, device=device)
        pairs_t = torch.tensor(pairs, dtype=torch.long, device=device)
        neg_pool_t = torch.tensor(neg_pool, dtype=torch.long, device=device)

        # Trainable projection: d_in -> 128
        dim_out = 128
        P = torch.nn.Parameter(torch.randn(d_in, dim_out, device=device) * 0.01)

        optimizer = torch.optim.Adam([P], lr=0.001)
        margin = 1.0
        batch_size = 64

        best_loss = float("inf")
        for epoch in range(500):
            # Shuffle pairs
            perm = torch.randperm(len(pairs), device=device)
            total_loss = 0.0

            for b_start in range(0, len(pairs), batch_size):
                b_end = min(b_start + batch_size, len(pairs))
                batch = perm[b_start:b_end]

                # Get embeddings
                idx_a = pairs_t[batch, 0]
                idx_b = pairs_t[batch, 1]
                h_a = X_t[idx_a] @ P  # (batch, dim_out)
                h_b = X_t[idx_b] @ P

                # Normalize
                h_a = torch.nn.functional.normalize(h_a, dim=1)
                h_b = torch.nn.functional.normalize(h_b, dim=1)

                # Positive loss: pull together
                pos_loss = torch.mean(torch.sum((h_a - h_b) ** 2, dim=1))

                # Negative loss: push apart from random negatives
                neg_idx = neg_pool_t[torch.randint(len(neg_pool), (len(batch),), device=device)]
                h_neg = X_t[neg_idx] @ P
                h_neg = torch.nn.functional.normalize(h_neg, dim=1)
                neg_dist_a = torch.sum((h_a - h_neg) ** 2, dim=1)
                neg_dist_b = torch.sum((h_b - h_neg) ** 2, dim=1)
                neg_loss = torch.mean(torch.clamp(margin - neg_dist_a, min=0))
                neg_loss += torch.mean(torch.clamp(margin - neg_dist_b, min=0))

                # Regularization: prevent collapse
                reg_loss = 0.01 * torch.sum(P ** 2)

                loss = pos_loss + 0.5 * neg_loss + reg_loss
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            avg_loss = total_loss / max(1, len(pairs) // batch_size)
            if epoch % 100 == 0:
                print(f"    epoch {epoch}: loss={avg_loss:.4f}", flush=True)
            best_loss = min(best_loss, avg_loss)

        # Evaluate: project all embeddings, re-compute LOTO FNR
        with torch.no_grad():
            X_proj = (X_t @ P).cpu().numpy()
        X_proj = X_proj / (np.linalg.norm(X_proj, axis=1, keepdims=True) + 1e-8)

        y = Y_np[:, ei]
        pre_fnrs = {}
        post_fnrs = {}
        for t in sorted(set(tools)):
            pos_i = [i for i, tt in enumerate(tools) if tt == t and y[i] == 1]
            neg_i = [i for i, tt in enumerate(tools) if tt == t and y[i] == 0]
            if len(pos_i) < 5 or len(neg_i) < 5:
                continue
            all_i = pos_i + neg_i
            labels = np.array([1] * len(pos_i) + [0] * len(neg_i))
            train_i = [i for i in range(len(y)) if tools[i] != t]

            # Pre
            c1 = LogisticRegression(l1_ratio=0, C=1.0, max_iter=2000, class_weight="balanced")
            c1.fit(X_np[train_i], y[train_i])
            yp1 = c1.predict(X_np[all_i])
            pre_fnrs[t] = 1.0 - recall_score(labels, yp1, zero_division=0)

            # Post
            c2 = LogisticRegression(l1_ratio=0, C=1.0, max_iter=2000, class_weight="balanced")
            c2.fit(X_proj[train_i], y[train_i])
            yp2 = c2.predict(X_proj[all_i])
            post_fnrs[t] = 1.0 - recall_score(labels, yp2, zero_division=0)

        effect_result = {}
        print(f"    {'Tool':>12s} | {'preFNR':>7s} | {'postFNR':>8s} | {'delta':>7s}")
        for t in sorted(pre_fnrs.keys()):
            d = pre_fnrs[t] - post_fnrs[t]
            effect_result[t] = {"pre": round(pre_fnrs[t], 4), "post": round(post_fnrs[t], 4), "delta": round(d, 4)}
            print(f"    {t:>12s} | {pre_fnrs[t]:>7.4f} | {post_fnrs[t]:>8.4f} | {d:>+7.4f}")
        results[effect] = effect_result

    # Summary
    print(f"\n{'=' * 60}")
    all_deltas = []
    for e, tool_r in results.items():
        for t, r in tool_r.items():
            all_deltas.append(r["delta"])
    if all_deltas:
        print(f"Contrastive projection: mean delta = {np.mean(all_deltas):+.4f}")
        print(f"Improved: {sum(1 for d in all_deltas if d > 0)}/{len(all_deltas)}")

    out = base / "analysis" / f"contrastive_{data_name}.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"Saved to {out}")


if __name__ == "__main__":
    main()
