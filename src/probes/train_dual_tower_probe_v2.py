"""Dual-tower probe v2: learn relationship between task and tool embeddings.

Goes beyond simple linear operations. Learns the interaction using
sklearn MLPClassifier (nonlinear) and bilinear features.

Models:
  - lr_concat:     Linear on concat(task, tool) [baseline]
  - mlp_concat:    MLP on concat(task, tool) [nonlinear fusion]
  - mlp_interact:  MLP on [task, tool, task*tool, task-tool] [explicit interaction features]
  - bilinear_feat: Linear on outer product features [learned interaction]
  - kernel_svm:    RBF SVM on concat [nonlinear decision boundary]
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import StratifiedKFold


def evaluate(y_true, y_pred):
    tp = ((y_pred == 1) & (y_true == 1)).sum()
    fn = ((y_pred == 0) & (y_true == 1)).sum()
    fp = ((y_pred == 1) & (y_true == 0)).sum()
    tn = ((y_pred == 0) & (y_true == 0)).sum()
    fnr = fn / max(fn + tp, 1)
    fpr = fp / max(fp + tn, 1)
    prec = tp / max(tp + fp, 1)
    rec = tp / max(tp + fn, 1)
    f1 = 2 * prec * rec / max(prec + rec, 1e-9)
    return {"FNR": round(fnr, 4), "FPR": round(fpr, 4), "F1": round(f1, 4),
            "Precision": round(prec, 4), "Recall": round(rec, 4)}


def main():
    data_name = "dual_tower_samples"
    base = Path(__file__).resolve().parent.parent.parent

    rows = [json.loads(l) for l in (base / "data" / f"{data_name}.jsonl").read_text(encoding="utf-8").splitlines()]
    X_task = np.load(base / "embeddings" / f"emb_{data_name}_task.npy")
    X_tool = np.load(base / "embeddings" / f"emb_{data_name}_tool.npy")
    X_concat = np.load(base / "embeddings" / f"emb_{data_name}_concat.npy")
    y = np.load(base / "embeddings" / f"emb_{data_name}_labels.npy")

    print(f"Samples: {len(rows)}, Authorized: {y.sum()}, Unauthorized: {(1-y).sum()}")

    # Feature sets
    X_interact = np.concatenate([X_task, X_tool, X_task * X_tool, X_task - X_tool], axis=1)  # 4*4096=16384
    X_dual = np.concatenate([X_task, X_tool], axis=1)  # 8192

    features = {
        "lr_concat": X_concat,
        "lr_dual": X_dual,
        "lr_interact": X_interact,
        "mlp_concat": X_concat,
        "mlp_dual": X_dual,
        "mlp_interact": X_interact,
    }

    # ---- 5-fold CV ----
    print(f"\n{'='*75}")
    print("5-Fold CV Results")
    print(f"{'='*75}")

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    all_results = defaultdict(list)

    for fold, (train_idx, test_idx) in enumerate(skf.split(X_task, y)):
        for name in features:
            X_all = features[name]
            X_tr, X_te = X_all[train_idx], X_all[test_idx]
            y_tr, y_te = y[train_idx], y[test_idx]

            # Use fresh classifier each fold
            if "mlp" in name:
                clf = make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=500, early_stopping=True, random_state=42))
            else:
                clf = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced"))

            clf.fit(X_tr, y_tr)
            proba = clf.predict_proba(X_te)[:, 1]
            pred = (proba >= 0.5).astype(int)
            m = evaluate(y_te, pred)
            m["fold"] = fold
            all_results[name].append(m)

    print(f"\n{'Model':25s} {'FNR':>8s} {'FPR':>8s} {'F1':>8s} {'Prec':>8s} {'Rec':>8s}  Description")
    print("-" * 95)
    descriptions = {
        "lr_concat": "单文本concat + 线性",
        "lr_dual": "双塔concat + 线性",
        "lr_interact": "双塔+交互特征 + 线性",
        "mlp_concat": "单文本concat + MLP非线性",
        "mlp_dual": "双塔concat + MLP非线性",
        "mlp_interact": "双塔+交互特征 + MLP非线性",
    }
    for name in ["lr_concat", "lr_dual", "lr_interact", "mlp_concat", "mlp_dual", "mlp_interact"]:
        folds = all_results[name]
        avg = {k: round(float(np.mean([f[k] for f in folds])), 4) for k in ["FNR", "FPR", "F1", "Precision", "Recall"]}
        std_f1 = round(float(np.std([f["F1"] for f in folds])), 4)
        print(f"{name:25s} {avg['FNR']:8.4f} {avg['FPR']:8.4f} {avg['F1']:8.4f}±{std_f1:.4f} {avg['Precision']:8.4f} {avg['Recall']:8.4f}  {descriptions.get(name, '')}")

    # ---- Lexical variant generalization ----
    print(f"\n{'='*75}")
    print("Lexical Variant Generalization")
    print(f"{'='*75}")
    variant_keys = [k for k in set(r["tool_key"] for r in rows) if "_v2" in k or "_v3" in k]
    variant_idx = np.array([i for i, r in enumerate(rows) if r["tool_key"] in variant_keys])
    standard_idx = np.array([i for i, r in enumerate(rows) if r["tool_key"] not in variant_keys])

    for name in ["lr_concat", "lr_dual", "lr_interact", "mlp_concat", "mlp_dual", "mlp_interact"]:
        X_all = features[name]
        if "mlp" in name:
            clf = make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=500, early_stopping=True, random_state=42))
        else:
            clf = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced"))
        clf.fit(X_all[standard_idx], y[standard_idx])
        proba = clf.predict_proba(X_all[variant_idx])[:, 1]
        pred = (proba >= 0.5).astype(int)
        m = evaluate(y[variant_idx], pred)
        print(f"  {name:25s}  FNR={m['FNR']:.4f}  FPR={m['FPR']:.4f}  F1={m['F1']:.4f}")

    # ---- Feature importance: which interaction matters? ----
    print(f"\n{'='*75}")
    print("Interaction Feature Analysis")
    print(f"{'='*75}")
    clf = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced"))
    clf.fit(X_interact, y)
    coef = clf[-1].coef_[0]
    # Split by feature type
    n = 4096
    importance = {
        "task": np.abs(coef[:n]).mean(),
        "tool": np.abs(coef[n:2*n]).mean(),
        "task*tool (hadamard)": np.abs(coef[2*n:3*n]).mean(),
        "task-tool (diff)": np.abs(coef[3*n:]).mean(),
    }
    total = sum(importance.values())
    for k, v in sorted(importance.items(), key=lambda x: -x[1]):
        print(f"  {k:25s}  mean|coef|={v:.6f}  ({v/total:.1%})")


if __name__ == "__main__":
    main()

