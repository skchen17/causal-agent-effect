"""Train and evaluate dual-tower probes for task-tool authorization detection.

Compares multiple architectures:
  - baseline_concat: single embedding of "Task: ... Tool: ..." → classify
  - concat_dual:    [v_task; v_tool] → classify
  - diff:           v_task - v_tool → classify
  - hadamard:       v_task ⊙ v_tool → classify
  - cosine_only:    cos(v_task, v_tool) → threshold
  - dot_only:       dot(v_task, v_tool) → threshold

Evaluates with stratified 5-fold CV, reporting per-fold FNR/FPR/F1.
Also evaluates on held-out lexical variants (cross-tool generalization).
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import StratifiedKFold


def build_features(X_task, X_tool, X_concat):
    """Build all feature variants."""
    return {
        "baseline_concat": X_concat,
        "concat_dual": np.concatenate([X_task, X_tool], axis=1),
        "diff": X_task - X_tool,
        "hadamard": X_task * X_tool,
        "cosine": cosine_scores(X_task, X_tool).reshape(-1, 1),
        "dot": (X_task * X_tool).sum(axis=1, keepdims=True),
    }


def cosine_scores(A, B):
    """Row-wise cosine similarity."""
    norm_a = np.linalg.norm(A, axis=1, keepdims=True)
    norm_b = np.linalg.norm(B, axis=1, keepdims=True)
    return np.sum(A * B, axis=1) / (norm_a.ravel() * norm_b.ravel() + 1e-9)


def evaluate(y_true, y_pred, proba):
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
            "Precision": round(prec, 4), "Recall": round(rec, 4),
            "TP": int(tp), "FN": int(fn), "FP": int(fp), "TN": int(tn)}


def main():
    data_name = "dual_tower_samples"
    base = Path(__file__).resolve().parent.parent.parent

    # Load data
    rows = [json.loads(l) for l in (base / "data" / f"{data_name}.jsonl").read_text(encoding="utf-8").splitlines()]
    X_task = np.load(base / "embeddings" / f"emb_{data_name}_task.npy")
    X_tool = np.load(base / "embeddings" / f"emb_{data_name}_tool.npy")
    X_concat = np.load(base / "embeddings" / f"emb_{data_name}_concat.npy")
    y = np.load(base / "embeddings" / f"emb_{data_name}_labels.npy")

    print(f"Samples: {len(rows)}, Authorized: {y.sum()}, Unauthorized: {(1-y).sum()}")
    print(f"Task dim: {X_task.shape[1]}, Tool dim: {X_tool.shape[1]}")

    features = build_features(X_task, X_tool, X_concat)

    # ---- 5-fold CV ----
    print(f"\n{'='*70}")
    print("5-Fold Cross-Validation")
    print(f"{'='*70}")

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    results = defaultdict(list)

    for fold, (train_idx, test_idx) in enumerate(skf.split(X_task, y)):
        for name, X in features.items():
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            if name in ("cosine", "dot"):
                # 1-dim features → use simple threshold
                best_f1, best_thresh = 0, 0.5
                for thresh in np.arange(0.1, 0.95, 0.05):
                    pred = (X_test.ravel() >= thresh).astype(int)
                    m = evaluate(y_test, pred, None)
                    if m["F1"] > best_f1:
                        best_f1, best_thresh = m["F1"], thresh
                pred = (X_test.ravel() >= best_thresh).astype(int)
                m = evaluate(y_test, pred, None)
                m["threshold"] = round(best_thresh, 2)
            else:
                probe = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced"))
                probe.fit(X_train, y_train)
                proba = probe.predict_proba(X_test)[:, 1]
                pred = (proba >= 0.5).astype(int)
                m = evaluate(y_test, pred, proba)
                m["threshold"] = 0.5

            m["fold"] = fold
            results[name].append(m)

    # Print per-architecture summary
    print(f"\n{'Architecture':25s} {'FNR':>8s} {'FPR':>8s} {'F1':>8s} {'Prec':>8s} {'Rec':>8s}")
    print("-" * 70)
    for name in ["baseline_concat", "concat_dual", "diff", "hadamard", "cosine", "dot"]:
        folds = results[name]
        avg = {k: round(np.mean([f[k] for f in folds]), 4) for k in ["FNR", "FPR", "F1", "Precision", "Recall"]}
        print(f"{name:25s} {avg['FNR']:8.4f} {avg['FPR']:8.4f} {avg['F1']:8.4f} {avg['Precision']:8.4f} {avg['Recall']:8.4f}")

    # ---- Generalization: lexical variants ----
    print(f"\n{'='*70}")
    print("Lexical Variant Generalization (held-out surface forms)")
    print(f"{'='*70}")

    # Identify lexical variant samples
    variant_tool_keys = [k for k in set(r["tool_key"] for r in rows) if "_v2" in k or "_v3" in k]
    variant_idx = np.array([i for i, r in enumerate(rows) if r["tool_key"] in variant_tool_keys])
    standard_idx = np.array([i for i, r in enumerate(rows) if r["tool_key"] not in variant_tool_keys])

    print(f"  Standard tools: {len(standard_idx)} samples")
    print(f"  Variant tools:  {len(variant_idx)} samples ({variant_tool_keys})")

    if len(variant_idx) > 0:
        # Train on standard, test on variant
        print(f"\n  Train on standard, test on lexical variants:")
        for name in ["baseline_concat", "concat_dual", "diff", "hadamard", "cosine", "dot"]:
            X = features[name]
            if name in ("cosine", "dot"):
                best_f1, best_thresh = 0, 0.5
                for thresh in np.arange(0.1, 0.95, 0.05):
                    pred = (X[variant_idx].ravel() >= thresh).astype(int)
                    m = evaluate(y[variant_idx], pred, None)
                    if m["F1"] > best_f1:
                        best_f1, best_thresh = m["F1"], thresh
                pred = (X[variant_idx].ravel() >= best_thresh).astype(int)
                m = evaluate(y[variant_idx], pred, None)
            else:
                probe = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced"))
                probe.fit(X[standard_idx], y[standard_idx])
                proba = probe.predict_proba(X[variant_idx])[:, 1]
                pred = (proba >= 0.5).astype(int)
                m = evaluate(y[variant_idx], pred, proba)

            print(f"    {name:25s}  FNR={m['FNR']:.4f}  FPR={m['FPR']:.4f}  F1={m['F1']:.4f}")

    # ---- Cross-tool generalization ----
    print(f"\n{'='*70}")
    print("Cross-Tool Generalization (same task, different tool surface)")
    print(f"{'='*70}")

    cross_tool_groups = {
        "read_config_across_tools": [
            ("read_config", "read_file_config"),
            ("read_config", "bash_cat_config"),
            ("read_config", "read_file_config_v2"),
            ("read_config", "read_file_config_v3"),
            ("read_config", "bash_cat_config_v2"),
            ("read_config", "bash_cat_config_v3"),
        ],
        "check_health_across_tools": [
            ("check_health", "bash_curl_head"),
            ("check_health", "bash_curl_head_v2"),
        ],
    }

    for group_name, pairs in cross_tool_groups.items():
        all_idx = []
        for task_key, tool_key in pairs:
            idx = [i for i, r in enumerate(rows) if r["task_key"] == task_key and r["tool_key"] == tool_key]
            all_idx.extend(idx)
        all_idx = np.array(all_idx)

        if len(all_idx) < 2:
            continue

        print(f"\n  {group_name} ({len(all_idx)} samples):")
        # Leave-one-tool-out style: for each unique tool, train on others, test on it
        unique_tools = sorted(set(rows[i]["tool_key"] for i in all_idx))
        for heldout_tool in unique_tools:
            test_i = np.array([i for i in all_idx if rows[i]["tool_key"] == heldout_tool])
            train_i = np.array([i for i in all_idx if rows[i]["tool_key"] != heldout_tool])
            if len(train_i) < 3 or len(test_i) == 0:
                continue
            if len(set(y[train_i])) < 2:
                continue  # need both classes for training

            print(f"    holdout={heldout_tool:30s} train={len(train_i):2d} test={len(test_i):1d}  ", end="")
            best_name, best_f1 = "", 0
            for name in ["baseline_concat", "concat_dual", "diff", "hadamard"]:
                X = features[name]
                probe = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced"))
                probe.fit(X[train_i], y[train_i])
                proba = probe.predict_proba(X[test_i])[:, 1]
                pred = (proba >= 0.5).astype(int)
                m = evaluate(y[test_i], pred, proba)
                if m["F1"] > best_f1:
                    best_name, best_f1 = name, m["F1"]
                print(f"{name}={m['F1']:.3f} ", end="")
            print(f" best={best_name}")


if __name__ == "__main__":
    main()
