"""Procrustes alignment: rotate probe directions to reduce ToolProxyGap."""
import json, sys, numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import recall_score
from pathlib import Path

base = Path(__file__).resolve().parent.parent
data_name = sys.argv[1] if len(sys.argv) > 1 else "qwen3-8b_scenarios_merged"

X = np.load(base / f"embeddings/embeddings_{data_name}.npy")
Y = np.load(base / f"embeddings/effects_{data_name}.npy")
with open(base / f"embeddings/texts_{data_name}.jsonl") as f:
    tools = [json.loads(line)["tool_name"] for line in f]
with open(base / f"embeddings/meta_{data_name}.json") as f:
    effect_names = json.load(f)["effect_names"]


def align(w_src, w_tgt, X_src):
    """Rotate X_src in w_src-w_tgt plane to align directions."""
    u = w_src / (np.linalg.norm(w_src) + 1e-8)
    v = w_tgt / (np.linalg.norm(w_tgt) + 1e-8)
    c = np.clip(np.dot(u, v), -1.0, 1.0)
    if c > 0.999:
        return X_src.copy()
    s = np.sqrt(1.0 - c * c)
    n = v - c * u
    n = n / (np.linalg.norm(n) + 1e-8)
    Xu = X_src @ u
    Xn = X_src @ n
    return X_src + s * (np.outer(Xu, n) - np.outer(Xn, u)) + (c - 1.0) * (np.outer(Xn, n) + np.outer(Xu, u))


print(f"Model: {data_name}")
print(f"{'Effect':<22s} | {'Pair':>22s} | {'preFNR':>7s} | {'postFNR':>8s} | {'delta':>7s}")
print("-" * 75)

improvements = []
by_effect = {}

for ei, effect in enumerate(effect_names):
    y = Y[:, ei]
    # Train per-tool probes
    tool_probes = {}
    for t in sorted(set(tools)):
        pos_i = [i for i, tt in enumerate(tools) if tt == t and y[i] == 1]
        neg_i = [i for i, tt in enumerate(tools) if tt == t and y[i] == 0]
        if len(pos_i) >= 5 and len(neg_i) >= 5:
            clf = LogisticRegression(l1_ratio=0, C=1.0, max_iter=2000, class_weight="balanced")
            clf.fit(X[pos_i + neg_i], [1] * len(pos_i) + [0] * len(neg_i))
            tool_probes[t] = clf.coef_[0]
    if len(tool_probes) < 2:
        continue

    tl = sorted(tool_probes.keys())
    effect_deltas = []

    for i in range(len(tl)):
        for j in range(i + 1, len(tl)):
            t_src, t_tgt = tl[i], tl[j]

            # Pre-alignment LOTO FNR
            tgt_pos = [k for k, tt in enumerate(tools) if tt == t_tgt and y[k] == 1]
            tgt_neg = [k for k, tt in enumerate(tools) if tt == t_tgt and y[k] == 0]
            if len(tgt_pos) < 5 or len(tgt_neg) < 5:
                continue
            all_tgt = tgt_pos + tgt_neg
            labels = np.array([1] * len(tgt_pos) + [0] * len(tgt_neg))
            train_k = [k for k in range(len(y)) if tools[k] != t_tgt]

            clf = LogisticRegression(l1_ratio=0, C=1.0, max_iter=2000, class_weight="balanced")
            clf.fit(X[train_k], y[train_k])
            yp = clf.predict(X[all_tgt])
            pre_fnr = 1.0 - recall_score(labels, yp, zero_division=0)

            # Post-alignment: rotate src embeddings
            src_k = [k for k, tt in enumerate(tools) if tt == t_src]
            Xa = X.copy()
            Xa[src_k] = align(tool_probes[t_src], tool_probes[t_tgt], X[src_k])

            clf.fit(Xa[train_k], y[train_k])
            yp = clf.predict(Xa[all_tgt])
            post_fnr = 1.0 - recall_score(labels, yp, zero_division=0)

            delta = pre_fnr - post_fnr
            improvements.append(delta)
            effect_deltas.append(delta)
            pair = f"{t_src[:8]}->{t_tgt[:8]}"
            print(f"{effect:<22s} | {pair:>22s} | {pre_fnr:>7.4f} | {post_fnr:>8.4f} | {delta:>+7.4f}")

    if effect_deltas:
        by_effect[effect] = {
            "mean_delta": round(float(np.mean(effect_deltas)), 4),
            "n_improved": sum(1 for d in effect_deltas if d > 0),
            "n_pairs": len(effect_deltas),
        }

print(f"\n--- Summary ---")
print(f"Mean delta: {np.mean(improvements):+.4f}")
print(f"Improved pairs: {sum(1 for d in improvements if d > 0)}/{len(improvements)}")
print(f"By effect:")
for e, r in sorted(by_effect.items(), key=lambda x: -x[1]["mean_delta"]):
    print(f"  {e:<22s}: mean_delta={r['mean_delta']:+.4f}, improved={r['n_improved']}/{r['n_pairs']}")

# Save
out = base / "analysis" / f"procrustes_{data_name}.json"
out.write_text(json.dumps({"by_effect": by_effect, "all_deltas": [float(d) for d in improvements]}, indent=2))
print(f"\nSaved to {out}")
