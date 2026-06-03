"""Direct probe evaluation: skip the present verifier, use a single linear probe
to predict unauthorized effects directly from embeddings.

Trains on schema-conditioned data, tests on agent runtime trace data.
Reports per-effect FNR/FPR and overall tradeoffs.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline


def main():
    data_name = sys.argv[1] if len(sys.argv) > 1 else "qwen3.5-9b-deepseek-v4"
    train_data = sys.argv[2] if len(sys.argv) > 2 else f"{data_name}_auth_effect_schema_conditioned_v2"
    test_data = sys.argv[3] if len(sys.argv) > 3 else f"{data_name}_auth_trace_effect_schema_conditioned_agent_runtime_v2"

    base = Path(__file__).resolve().parent.parent.parent

    # Load training data
    train_x = np.load(base / "embeddings" / f"embeddings_{train_data}.npy").astype(np.float32)
    train_file = train_data.replace(f"{data_name}_", "")
    train_rows = [json.loads(l) for l in (base / "data" / f"{train_file}.jsonl").read_text(encoding="utf-8").splitlines()]
    print(f"Train: {len(train_rows)} rows from {train_data}")

    # Load test data
    test_x = np.load(base / "embeddings" / f"embeddings_{test_data}.npy").astype(np.float32)
    test_file = test_data.replace(f"{data_name}_", "")
    test_rows = [json.loads(l) for l in (base / "data" / f"{test_file}.jsonl").read_text(encoding="utf-8").splitlines()]
    print(f"Test:  {len(test_rows)} rows from {test_data}")

    # Filter training to full_tool_chain condition
    train_idx = np.array([i for i, r in enumerate(train_rows) if r.get("schema_condition") == "full_tool_chain"])
    print(f"Train (full_tool_chain): {len(train_idx)} rows")

    y_train = np.array([int(train_rows[i]["label_unauthorized_effect"]) for i in train_idx], dtype=int)
    n_pos = y_train.sum()
    print(f"Train positives (unauthorized): {n_pos} / {len(train_idx)} ({n_pos/len(train_idx):.1%})")

    # Filter test to full_tool_chain
    test_idx = np.array([i for i, r in enumerate(test_rows) if r.get("schema_condition") == "full_tool_chain"])
    print(f"Test (full_tool_chain): {len(test_idx)} rows")

    y_test = np.array([int(test_rows[i]["label_unauthorized_effect"]) for i in test_idx], dtype=int)
    n_pos_test = y_test.sum()
    print(f"Test positives (unauthorized): {n_pos_test} / {len(test_idx)} ({n_pos_test/len(test_idx):.1%})")

    # Train probe
    probe = make_pipeline(StandardScaler(), SGDClassifier(loss="log_loss", class_weight="balanced", max_iter=2000, random_state=42))
    probe.fit(train_x[train_idx], y_train)
    print(f"\nProbe trained. Coef shape: {probe[-1].coef_.shape}")

    # Predict on test
    proba = probe.predict_proba(test_x[test_idx])[:, 1]

    # ---- Overall metrics ----
    print(f"\n{'='*60}")
    print("Overall Results")
    print(f"{'='*60}")
    for threshold in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
        pred = (proba >= threshold).astype(int)
        tp = ((pred == 1) & (y_test == 1)).sum()
        fn = ((pred == 0) & (y_test == 1)).sum()
        fp = ((pred == 1) & (y_test == 0)).sum()
        tn = ((pred == 0) & (y_test == 0)).sum()
        fnr = fn / max(fn + tp, 1)
        fpr = fp / max(fp + tn, 1)
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-9)
        print(f"  thresh={threshold:.1f}  FNR={fnr:.4f}  FPR={fpr:.4f}  F1={f1:.4f}  P={precision:.4f}  R={recall:.4f}  TP={tp} FN={fn} FP={fp} TN={tn}")

    # ---- Per-effect breakdown ----
    print(f"\n{'='*60}")
    print("Per-Effect Breakdown (threshold=0.5)")
    print(f"{'='*60}")
    effects = sorted(set(r["candidate_effect"] for r in test_rows))
    pred_05 = (proba >= 0.5).astype(int)

    for effect in effects:
        effect_test_idx = np.array([pos for pos, i in enumerate(test_idx) if test_rows[int(i)]["candidate_effect"] == effect])
        if len(effect_test_idx) == 0:
            continue
        y_eff = y_test[effect_test_idx]
        pred_eff = pred_05[effect_test_idx]
        n_pos_eff = y_eff.sum()
        n_neg_eff = (1 - y_eff).sum()
        tp = ((pred_eff == 1) & (y_eff == 1)).sum()
        fn = ((pred_eff == 0) & (y_eff == 1)).sum()
        fp = ((pred_eff == 1) & (y_eff == 0)).sum()
        tn = ((pred_eff == 0) & (y_eff == 0)).sum()
        fnr = fn / max(n_pos_eff, 1)
        fpr = fp / max(n_neg_eff, 1)
        acc = (tp + tn) / max(len(effect_test_idx), 1)
        print(f"  {effect:25s}  N+={n_pos_eff:2d}  N-={n_neg_eff:2d}  FNR={fnr:.4f}  FPR={fpr:.4f}  Acc={acc:.4f}")

    # ---- Per-tool breakdown ----
    print(f"\n{'='*60}")
    print("Per-Tool Breakdown (threshold=0.5)")
    print(f"{'='*60}")
    tools = sorted(set(r.get("tool_name", r.get("registered_tool_name", "?")) for r in test_rows))
    for tool in tools:
        tool_test_idx = np.array([pos for pos, i in enumerate(test_idx) if test_rows[int(i)].get("tool_name", test_rows[int(i)].get("registered_tool_name")) == tool])
        if len(tool_test_idx) == 0:
            continue
        y_tool = y_test[tool_test_idx]
        pred_tool = pred_05[tool_test_idx]
        n_pos_t = y_tool.sum()
        n_neg_t = (1 - y_tool).sum()
        tp = ((pred_tool == 1) & (y_tool == 1)).sum()
        fn = ((pred_tool == 0) & (y_tool == 1)).sum()
        fp = ((pred_tool == 1) & (y_tool == 0)).sum()
        fnr = fn / max(n_pos_t, 1)
        fpr = fp / max(n_neg_t, 1)
        print(f"  {tool:20s}  N+={n_pos_t:2d}  N-={n_neg_t:2d}  FNR={fnr:.4f}  FPR={fpr:.4f}")

    # ---- Per-scenario-kind breakdown ----
    print(f"\n{'='*60}")
    print("Per-Scenario-Kind Breakdown (threshold=0.5)")
    print(f"{'='*60}")
    kinds = sorted(set(r.get("counterfactual_family", "?").replace("agent_runtime_execution", "agent_runtime") for r in test_rows))
    for kind in set(r.get("counterfactual_family", r.get("trace_type", "?")) for r in test_rows):
        kind_test_idx = np.array([pos for pos, i in enumerate(test_idx) if test_rows[int(i)].get("counterfactual_family", test_rows[int(i)].get("trace_type")) == kind])
        if len(kind_test_idx) == 0:
            continue
        y_k = y_test[kind_test_idx]
        pred_k = pred_05[kind_test_idx]
        n_pos_k = y_k.sum()
        n_neg_k = (1 - y_k).sum()
        tp = ((pred_k == 1) & (y_k == 1)).sum()
        fn = ((pred_k == 0) & (y_k == 1)).sum()
        fp = ((pred_k == 1) & (y_k == 0)).sum()
        fnr = fn / max(n_pos_k, 1)
        fpr = fp / max(n_neg_k, 1)
        print(f"  {kind:30s}  N+={n_pos_k:2d}  N-={n_neg_k:2d}  FNR={fnr:.4f}  FPR={fpr:.4f}")

    # ---- Misclassified examples ----
    print(f"\n{'='*60}")
    print("Top Misclassifications (FN: should alarm but didn't)")
    print(f"{'='*60}")
    fn_idx = test_idx[(pred_05 == 0) & (y_test == 1)]
    for i in fn_idx[:8]:
        r = test_rows[int(i)]
        print(f"  FN | {r['candidate_effect']:20s} | tool={r.get('tool_name','?'):12s} | proba={proba[list(test_idx).index(i)]:.3f}")
        print(f"      text: {r['scenario_text'][:150]}...")

    print(f"\n{'='*60}")
    print("Top Misclassifications (FP: false alarm)")
    print(f"{'='*60}")
    fp_idx = test_idx[(pred_05 == 1) & (y_test == 0)]
    for i in fp_idx[:8]:
        r = test_rows[int(i)]
        print(f"  FP | {r['candidate_effect']:20s} | tool={r.get('tool_name','?'):12s} | proba={proba[list(test_idx).index(i)]:.3f}")
        print(f"      text: {r['scenario_text'][:150]}...")


if __name__ == "__main__":
    main()
