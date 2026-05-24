"""Standalone contrastive projection multiseed experiment.

Usage:
  python run_contrastive_multiseed.py --model qwen3-8b --data scenarios_merged --seeds 0 1 2 3 4 --dim 128
"""
from __future__ import annotations
import argparse, json, sys
import numpy as np, torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import recall_score
from pathlib import Path


def resolve_data_name(model, data):
    if data.startswith(f"{model}_"):
        return data
    return f"{model}_{data}"

def load_data(base, model, data):
    emb_dir = base / "embeddings"
    name = resolve_data_name(model, data)
    emb_path = emb_dir / f"embeddings_{name}.npy"
    if not emb_path.exists():
        raise FileNotFoundError(f"No embeddings found for {name}: {emb_path}")
    eff_path = Path(str(emb_path).replace("embeddings_", "effects_"))
    texts_path = Path(str(emb_path).replace("embeddings_", "texts_")).with_suffix(".jsonl")

    X = np.load(emb_path)
    Y = np.load(eff_path)
    with open(texts_path) as f:
        tools = [json.loads(line).get("tool_name", "unknown") for line in f]
    with open(Path(str(emb_path).replace("embeddings_", "meta_")).with_suffix(".json")) as f:
        meta = json.load(f)
    return X, Y, meta, tools


def train_and_eval(X_np, Y_np, tools, effect_idx, dim_out, seed, device, epochs=300):
    y_np = Y_np[:, effect_idx]
    tool_pos = {}
    for i, t in enumerate(tools):
        if y_np[i] == 1:
            tool_pos.setdefault(t, []).append(i)
    valid = {t: idxs for t, idxs in tool_pos.items() if len(idxs) >= 5}
    if len(valid) < 2:
        return None

    rng = np.random.default_rng(seed)
    tl = sorted(valid.keys())
    pairs = []
    for i in range(len(tl)):
        for j in range(i + 1, len(tl)):
            a_idx, b_idx = valid[tl[i]], valid[tl[j]]
            npairs = min(50, len(a_idx), len(b_idx))
            a_s = rng.choice(a_idx, size=npairs, replace=False)
            b_s = rng.choice(b_idx, size=npairs, replace=False)
            for k in range(npairs):
                pairs.append((int(a_s[k]), int(b_s[k])))
    if len(pairs) < 5:
        return None

    neg_pool = [i for i in range(len(y_np)) if y_np[i] == 0]
    X_t = torch.tensor(X_np, dtype=torch.float32, device=device)
    pairs_t = torch.tensor(pairs, dtype=torch.long, device=device)
    neg_t = torch.tensor(neg_pool, dtype=torch.long, device=device)

    torch.manual_seed(seed)
    P = torch.nn.Parameter(torch.randn(X_np.shape[1], dim_out, device=device) * 0.01)
    opt = torch.optim.Adam([P], lr=0.001)
    m, bs = 1.0, 64

    for epoch in range(epochs):
        perm = torch.randperm(len(pairs), device=device)
        for b_start in range(0, len(pairs), bs):
            b_end = min(b_start + bs, len(pairs))
            batch = perm[b_start:b_end]
            h_a = X_t[pairs_t[batch, 0]] @ P
            h_b = X_t[pairs_t[batch, 1]] @ P
            h_a = torch.nn.functional.normalize(h_a, dim=1)
            h_b = torch.nn.functional.normalize(h_b, dim=1)
            pos_loss = torch.mean(torch.sum((h_a - h_b) ** 2, dim=1))
            neg_idx = neg_t[torch.randint(len(neg_pool), (len(batch),), device=device)]
            h_neg = X_t[neg_idx] @ P
            h_neg = torch.nn.functional.normalize(h_neg, dim=1)
            neg_loss = torch.mean(torch.clamp(m - torch.sum((h_a - h_neg) ** 2, dim=1), min=0))
            neg_loss += torch.mean(torch.clamp(m - torch.sum((h_b - h_neg) ** 2, dim=1), min=0))
            loss = pos_loss + 0.5 * neg_loss + 0.01 * torch.sum(P ** 2)
            opt.zero_grad()
            loss.backward()
            opt.step()

    with torch.no_grad():
        X_proj = (X_t @ P).cpu().numpy()
    X_proj = X_proj / (np.linalg.norm(X_proj, axis=1, keepdims=True) + 1e-8)

    # LOTO evaluation
    results = {}
    for t in sorted(set(tools)):
        pos_i = [i for i, tt in enumerate(tools) if tt == t and y_np[i] == 1]
        neg_i = [i for i, tt in enumerate(tools) if tt == t and y_np[i] == 0]
        if len(pos_i) < 5 or len(neg_i) < 5:
            continue
        all_i = pos_i + neg_i
        labels = np.array([1] * len(pos_i) + [0] * len(neg_i))
        train_i = [i for i in range(len(y_np)) if tools[i] != t]
        clf = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
        clf.fit(X_proj[train_i], y_np[train_i])
        yp = clf.predict(X_proj[all_i])
        fnr = 1.0 - recall_score(labels, yp, zero_division=0)
        results[t] = fnr
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="qwen3-8b")
    p.add_argument("--data", default="scenarios_merged")
    p.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    p.add_argument("--dim", type=int, default=128)
    args = p.parse_args()

    base = Path(__file__).resolve().parent.parent
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    data_name = resolve_data_name(args.model, args.data)
    X, Y, meta, tools = load_data(base, args.model, args.data)
    effect_names = meta["effect_names"]

    all_results = {}
    for ei, effect in enumerate(effect_names):
        seed_runs = {t: [] for t in sorted(set(tools))}
        for seed in args.seeds:
            r = train_and_eval(X, Y, tools, ei, args.dim, seed, device)
            if r is None:
                continue
            for t, fnr in r.items():
                seed_runs[t].append(fnr)
        effect_data = {}
        for t, fnrs in seed_runs.items():
            if fnrs:
                effect_data[t] = {
                    "post_fnr_mean": round(float(np.mean(fnrs)), 4),
                    "post_fnr_std": round(float(np.std(fnrs)), 4),
                    "values": [float(v) for v in fnrs],
                    "aggregation": "worst_form",
                }
        if effect_data:
            all_results[effect] = effect_data

    payload = {
        "schema_version": "contrastive_multiseed_v2",
        "generated_by": "run_contrastive_multiseed.py",
        "config": {
            "model": args.model,
            "data": args.data,
            "data_name": data_name,
            "seeds": args.seeds,
            "dim": args.dim,
            "train_protocol": "full_training",
        },
        "results": all_results,
    }
    out = base / "analysis" / f"contrastive_multiseed_{data_name}.json"
    out.write_text(json.dumps(payload, indent=2))

    md = [
        "# Contrastive Multiseed Results",
        "",
        f"- Model: `{args.model}`",
        f"- Data: `{data_name}`",
        f"- Seeds: `{args.seeds}`",
        f"- Projection dim: `{args.dim}`",
        "",
        "| Effect | Tool | Post-FNR mean | Post-FNR std |",
        "|---|---:|---:|---:|",
    ]
    for effect, by_tool in sorted(all_results.items()):
        for tool, vals in sorted(by_tool.items()):
            md.append(f"| {effect} | {tool} | {vals['post_fnr_mean']:.4f} | {vals['post_fnr_std']:.4f} |")
    out_md = base / "analysis" / f"contrastive_multiseed_{data_name}.md"
    out_md.write_text("\n".join(md))
    print(f"Saved to {out}")
    print(f"Saved to {out_md}")


if __name__ == "__main__":
    main()
