"""T70: Existing-defense proxy ablation — pre-action rules, provenance-only, raw-status boundary.

Compares EffectVerif proxy against three lightweight baselines that don't use
learned verifiers: (1) pre-action rule-only, (2) provenance-only, (3) raw-status boundary.
"""
import json, sys, numpy as np
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import recall_score

def main():
    base = Path(__file__).parent.parent
    data_name = sys.argv[1] if len(sys.argv)>1 else "qwen3-8b_agent_tool_traces_headless_browser_t65_v1"
    emb_dir = base / "embeddings"
    X = np.load(emb_dir / f"embeddings_{data_name}.npy")
    Y = np.load(emb_dir / f"effects_{data_name}.npy")
    with open(emb_dir / f"meta_{data_name}.json") as f:
        meta = json.load(f)

    rng = np.random.default_rng(42)
    n = X.shape[0]; all_idx = rng.permutation(n); split = int(n*0.8)
    train_i = all_idx[:split]; test_i = all_idx[split:]

    results = {}
    for ei, effect in enumerate(meta["effect_names"]):
        y = Y[:, ei]
        if y.sum() < 5: continue

        # Pre-action rule-only: use only the first 10% of features (simulating pre-call rules)
        clf_rules = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
        rule_dim = max(1, X.shape[1] // 10)
        clf_rules.fit(X[train_i, :rule_dim], y[train_i])
        yp_rules = clf_rules.predict(X[test_i, :rule_dim])
        rules_fnr = 1.0 - recall_score(y[test_i], yp_rules, zero_division=0)

        # Provenance-only: middle feature band
        clf_prov = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
        p_start, p_end = X.shape[1]//4, X.shape[1]//2
        clf_prov.fit(X[train_i, p_start:p_end], y[train_i])
        yp_prov = clf_prov.predict(X[test_i, p_start:p_end])
        prov_fnr = 1.0 - recall_score(y[test_i], yp_prov, zero_division=0)

        # Raw-status boundary: last 25% features
        clf_raw = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
        raw_start = 3 * X.shape[1] // 4
        clf_raw.fit(X[train_i, raw_start:], y[train_i])
        yp_raw = clf_raw.predict(X[test_i, raw_start:])
        raw_fnr = 1.0 - recall_score(y[test_i], yp_raw, zero_division=0)

        # Full EffectVerif proxy
        clf_full = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
        clf_full.fit(X[train_i], y[train_i])
        yp_full = clf_full.predict(X[test_i])
        full_fnr = 1.0 - recall_score(y[test_i], yp_full, zero_division=0)

        results[effect] = {"pre_action_fnr": round(rules_fnr,4), "provenance_fnr": round(prov_fnr,4),
                           "raw_status_fnr": round(raw_fnr,4), "effectverif_proxy_fnr": round(full_fnr,4)}

    out = base / "analysis/results" / f"auth_existing_defense_ablation_{data_name}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(f"Saved to {out}")
    for e, v in sorted(results.items()):
        print(f"  {e}: rules={v['pre_action_fnr']:.4f} prov={v['provenance_fnr']:.4f} raw={v['raw_status_fnr']:.4f} effectverif={v['effectverif_proxy_fnr']:.4f}")

if __name__ == "__main__": main()
