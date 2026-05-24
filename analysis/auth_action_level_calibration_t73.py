"""T73: Action-level threshold calibration negative diagnostic.

Shows that simple false-denial-constrained threshold calibration can collapse
to all-allow on held-out trace families, exposing the row-to-action gap.
"""
import json, sys, numpy as np
from pathlib import Path
from sklearn.linear_model import LogisticRegression

def main():
    base = Path(__file__).parent.parent
    data_name = sys.argv[1] if len(sys.argv)>1 else "qwen3-8b_authorization_counterfactuals_v1"
    emb_dir = base / "embeddings"
    X = np.load(emb_dir / f"embeddings_{data_name}.npy")
    Y = np.load(emb_dir / f"effects_{data_name}.npy")
    with open(emb_dir / f"meta_{data_name}.json") as f:
        meta = json.load(f)
    data_file = data_name.replace("qwen3-8b_","")
    with open(base / "data" / f"{data_file}.jsonl") as f:
        items = [json.loads(l) for l in f]

    effect_names = meta["effect_names"]
    # Split by counterfactual family
    families = sorted(set(it.get("counterfactual_family","unknown") for it in items))
    print(f"Counterfactual families: {families}")

    results = {}
    for heldout_family in families:
        train_i = np.array([i for i,it in enumerate(items) if it.get("counterfactual_family")!=heldout_family])
        test_i = np.array([i for i,it in enumerate(items) if it.get("counterfactual_family")==heldout_family])
        if len(train_i)==0 or len(test_i)==0: continue

        probes = {}
        for ei, effect in enumerate(effect_names):
            clf = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
            clf.fit(X[train_i], Y[train_i, ei])
            probes[effect] = clf

        # Try threshold calibration: minimize FDeny subject to FNR <= 0.10 on training
        best_deny = 1.0; best_thresh = 0.5
        for thresh in np.arange(0.05, 0.95, 0.05):
            unauth_allows = 0; auth_denials = 0
            for idx in train_i:
                item = items[int(idx)]
                unauth_set = set(item.get("unauthorized_effects",[]))
                auth_set = set(item.get("authorized_effects",[]))
                any_fires = False
                for ei, effect in enumerate(effect_names):
                    p = probes[effect].predict_proba(X[idx:idx+1])[0,1]
                    if p > thresh: any_fires = True
                if unauth_set:
                    if not any_fires: unauth_allows += 1
                if auth_set and not unauth_set:
                    if any_fires: auth_denials += 1
            unauth_rate = unauth_allows / max(sum(1 for i in train_i if items[int(i)].get("unauthorized_effects")),1)
            fdeny = auth_denials / max(sum(1 for i in train_i if items[int(i)].get("authorized_effects") and not items[int(i)].get("unauthorized_effects")),1)
            if unauth_rate <= 0.10 and fdeny < best_deny:
                best_deny = fdeny; best_thresh = thresh

        # Evaluate on test
        unauth_allows_t = 0; auth_denials_t = 0; unauth_t = 0; auth_t = 0
        for idx in test_i:
            item = items[int(idx)]
            unauth_set = set(item.get("unauthorized_effects",[]))
            auth_set = set(item.get("authorized_effects",[]))
            any_fires = False
            for ei, effect in enumerate(effect_names):
                p = probes[effect].predict_proba(X[idx:idx+1])[0,1]
                if p > best_thresh: any_fires = True
            if unauth_set:
                unauth_t += 1
                if not any_fires: unauth_allows_t += 1
            if auth_set and not unauth_set:
                auth_t += 1
                if any_fires: auth_denials_t += 1

        results[heldout_family] = {
            "best_threshold": round(best_thresh,2),
            "test_unauth_allow": round(unauth_allows_t/max(unauth_t,1),4),
            "test_auth_fdeny": round(auth_denials_t/max(auth_t,1),4),
            "all_allow_collapse": best_thresh < 0.1,
        }

    out = base / "analysis/results" / f"auth_action_level_calibration_{data_name}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(f"Saved to {out}")
    for fam, v in results.items():
        flag = "⚠️ COLLAPSE" if v["all_allow_collapse"] else "OK"
        print(f"  {fam}: thresh={v['best_threshold']} unauth_allow={v['test_unauth_allow']:.4f} auth_fdeny={v['test_auth_fdeny']:.4f} {flag}")

if __name__ == "__main__": main()
