"""Strict leave-one-pair-out contrastive projection experiment.

For each effect with ≥3 tools, for each unordered tool pair (A,B):
  - Train projection excluding ALL A-B positive pairs
  - Test FNR on A and B via LOTO
  - Report pair-level pre/post/delta
"""
import argparse
import json, numpy as np, torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import recall_score
from pathlib import Path

def resolve_data_name(model, data):
    if data.startswith(f"{model}_"):
        return data
    return f"{model}_{data}"

def load_data(base, data_name):
    emb_dir = base / "embeddings"
    emb_path = emb_dir / f"embeddings_{data_name}.npy"
    eff_path = emb_dir / f"effects_{data_name}.npy"
    texts_path = emb_dir / f"texts_{data_name}.jsonl"
    meta_path = emb_dir / f"meta_{data_name}.json"
    X = np.load(emb_path)
    Y = np.load(eff_path)
    with open(texts_path) as f: tools = [json.loads(line).get("tool_name","unknown") for line in f]
    with open(meta_path) as f: meta = json.load(f)
    return X, Y, meta, tools

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="qwen3-8b")
    p.add_argument("--data", default="scenarios_merged")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--dim", type=int, default=128)
    args = p.parse_args()

    base = Path(__file__).resolve().parent.parent
    data_name = resolve_data_name(args.model, args.data)
    X, Y, meta, tools = load_data(base, data_name)
    effect_names = meta["effect_names"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    d_in = X.shape[1]
    rng = np.random.default_rng(args.seed)

    results = {"schema_version":"contrastive_strict_lopo_v1","generated_by":"run_contrastive_strict_lopo.py",
               "config":{"model":args.model,"data":args.data,"data_name":data_name,"seed":args.seed,"dim":args.dim},
               "summary":{},"effects":{}}

    evaluable = 0; total_cases = 0; total_improved = 0; all_deltas = []

    for ei, effect in enumerate(effect_names):
        y_np = Y[:, ei]
        tool_pos = {t: [i for i,tt in enumerate(tools) if tt==t and y_np[i]==1] for t in sorted(set(tools))}
        valid = {t: idxs for t,idxs in tool_pos.items() if len(idxs)>=5}
        if len(valid) < 3:
            results["effects"][effect] = {"status":"not_evaluable","n_forms":len(valid),
                "reason":"Fewer than 3 tools; leaving out sole cross-form pair removes all training signal"}
            continue

        evaluable += 1
        tl = sorted(valid.keys())
        pairs_data = []
        for i in range(len(tl)):
            for j in range(i+1, len(tl)):
                heldout_pair = (tl[i], tl[j])
                # Build training pairs excluding A-B
                train_pairs = []
                for a in range(len(tl)):
                    for b in range(a+1, len(tl)):
                        if (tl[a],tl[b])==heldout_pair or (tl[b],tl[a])==heldout_pair: continue
                        na = min(30, len(valid[tl[a]]), len(valid[tl[b]]))
                        a_s = rng.choice(valid[tl[a]], size=na, replace=False)
                        b_s = rng.choice(valid[tl[b]], size=na, replace=False)
                        for k in range(na): train_pairs.append((int(a_s[k]), int(b_s[k])))
                if len(train_pairs) < 3: continue

                neg_pool = [i for i in range(len(y_np)) if y_np[i]==0]
                X_t = torch.tensor(X, dtype=torch.float32, device=device)
                pairs_t = torch.tensor(train_pairs, dtype=torch.long, device=device)
                neg_t = torch.tensor(neg_pool, dtype=torch.long, device=device)
                torch.manual_seed(args.seed)
                P = torch.nn.Parameter(torch.randn(d_in, args.dim, device=device)*0.01)
                opt = torch.optim.Adam([P], lr=0.001)
                for epoch in range(200):
                    perm = torch.randperm(len(train_pairs), device=device)
                    for bs in range(0, len(train_pairs), 64):
                        be = min(bs+64, len(train_pairs)); batch = perm[bs:be]
                        ha = X_t[pairs_t[batch,0]] @ P; hb = X_t[pairs_t[batch,1]] @ P
                        ha = torch.nn.functional.normalize(ha, dim=1)
                        hb = torch.nn.functional.normalize(hb, dim=1)
                        pl = torch.mean(torch.sum((ha-hb)**2,dim=1))
                        ni = neg_t[torch.randint(len(neg_pool),(len(batch),),device=device)]
                        hn = X_t[ni] @ P; hn = torch.nn.functional.normalize(hn, dim=1)
                        nl = torch.mean(torch.clamp(1.0-torch.sum((ha-hn)**2,dim=1),min=0))
                        nl += torch.mean(torch.clamp(1.0-torch.sum((hb-hn)**2,dim=1),min=0))
                        loss = pl + 0.5*nl + 0.01*torch.sum(P**2)
                        opt.zero_grad(); loss.backward(); opt.step()

                with torch.no_grad(): X_proj = (X_t @ P).cpu().numpy()
                X_proj = X_proj/(np.linalg.norm(X_proj, axis=1, keepdims=True)+1e-8)

                tool_results = []
                for tt in heldout_pair:
                    pos_i = [k for k,tt2 in enumerate(tools) if tt2==tt and y_np[k]==1]
                    neg_i = [k for k,tt2 in enumerate(tools) if tt2==tt and y_np[k]==0]
                    if len(pos_i)<5 or len(neg_i)<5: continue
                    all_i = pos_i+neg_i; labels = np.array([1]*len(pos_i)+[0]*len(neg_i))
                    train_i = [k for k in range(len(y_np)) if tools[k]!=tt]
                    # Raw FNR
                    c1 = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
                    c1.fit(X[train_i], y_np[train_i]); yp1 = c1.predict(X[all_i])
                    raw_fnr = 1.0-recall_score(labels, yp1, zero_division=0)
                    # Strict post-FNR
                    c2 = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
                    c2.fit(X_proj[train_i], y_np[train_i]); yp2 = c2.predict(X_proj[all_i])
                    strict_fnr = 1.0-recall_score(labels, yp2, zero_division=0)
                    delta = raw_fnr - strict_fnr
                    tool_results.append({"tool":tt,"n_positive":len(pos_i),"raw_fnr":round(raw_fnr,4),
                        "strict_post_fnr":round(strict_fnr,4),"delta_fnr":round(delta,4)})
                    total_cases += 1
                    all_deltas.append(delta)
                    if delta > 0: total_improved += 1

                pairs_data.append({"heldout_pair":list(heldout_pair),"train_pairs_excluded":[list(heldout_pair)],
                    "n_train_pairs":len(train_pairs),"tool_results":tool_results})

        results["effects"][effect] = {"status":"evaluable","tools":tl,"pairs":pairs_data}

    results["summary"] = {"num_evaluable_effects":evaluable,"num_strict_tool_cases":total_cases,
        "num_improved":total_improved,"mean_delta_fnr":round(float(np.mean(all_deltas)),4) if all_deltas else 0}

    out = base/"analysis"/f"contrastive_strict_lopo_{data_name}.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"Saved to {out}")
    print(f"Evaluable effects: {evaluable}, Cases: {total_cases}, Improved: {total_improved}/{total_cases}, Mean delta: {results['summary']['mean_delta_fnr']:.4f}")

if __name__ == "__main__": main()
