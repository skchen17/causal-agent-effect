"""
Linear Subspace Interchange Intervention (Experiment 3).

Tests whether the linear probe direction w_E is genuinely causal for effect E,
or merely a tool-proxy. Based on interchange intervention (Geiger et al., 2021).

Procedure:
  1. Train linear probe on ALL data → get w_E, b_E (normalized direction)
  2. Within-tool IIA: swap subspace between same-tool (E=0, E=1) pairs
  3. Cross-tool IIA: swap subspace between different-tool (E=0, E=1) pairs
  4. Cross-Tool Causal Gap = IIA_within - IIA_cross

Connection to theory:
  - High IIA_within → probe detects effect within a tool (necessary)
  - High IIA_cross → probe detects CAUSAL CONCEPT across tools (sufficient)
  - Gap → tool-proxy = statistical correlation without causal alignment
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression


def load_data(data_name: str) -> tuple[np.ndarray, np.ndarray, dict, list[str], list[str]]:
    base = Path(__file__).resolve().parent.parent
    emb_dir = base / "embeddings"
    emb_path = emb_dir / f"embeddings_{data_name}.npy"
    eff_path = emb_dir / f"effects_{data_name}.npy"
    meta_path = emb_dir / f"meta_{data_name}.json"
    texts_path = emb_dir / f"texts_{data_name}.jsonl"

    X = np.load(emb_path)
    Y = np.load(eff_path)
    with open(meta_path) as f:
        meta = json.load(f)

    tools, texts = [], []
    if texts_path.exists():
        with open(texts_path, encoding="utf-8") as f:
            for line in f:
                item = json.loads(line)
                tools.append(item.get("tool_name", "unknown"))
                texts.append(item.get("text", ""))
    else:
        tools = ["unknown"] * X.shape[0]
        texts = [""] * X.shape[0]

    return X, Y, meta, tools, texts


def compute_cross_tool_iia(
    X: np.ndarray,
    y: np.ndarray,
    tools: list[str],
    effect_idx: int,
    n_pairs: int = 200,
    seed: int = 42,
) -> dict | None:
    """
    Cross-tool interchange intervention accuracy.

    Key (avoids circularity):
      - Train w_A on tool A only (source direction)
      - Evaluate with w_B trained on tool B only (target evaluation)
      - Swap along w_A, measure prediction change with w_B

    This tests: does the effect direction learned from tool A
    transfer to tool B's representation?
    """
    rng = np.random.default_rng(seed)

    # Group by (tool, effect)
    groups: dict[str, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    for i in range(len(y)):
        groups[tools[i]][int(y[i])].append(i)

    # Find tools with ≥5 positive AND negative samples
    valid_tools = {}
    for t in groups:
        if len(groups[t][0]) >= 5 and len(groups[t][1]) >= 5:
            valid_tools[t] = groups[t]

    if len(valid_tools) < 2:
        return None

    tool_list = sorted(valid_tools.keys())
    d = X.shape[1]

    all_iia_within = []
    all_iia_cross = []

    # For each ordered tool pair (A → B), test if A's direction transfers to B
    for t_src in tool_list:
        for t_tgt in tool_list:
            if t_src == t_tgt:
                continue

            # Train probes on each tool INDEPENDENTLY
            X_src = X[valid_tools[t_src][0] + valid_tools[t_src][1]]
            y_src = y[valid_tools[t_src][0] + valid_tools[t_src][1]]
            X_tgt = X[valid_tools[t_tgt][0] + valid_tools[t_tgt][1]]
            y_tgt = y[valid_tools[t_tgt][0] + valid_tools[t_tgt][1]]

            clf_src = LogisticRegression(l1_ratio=0, C=1.0, max_iter=2000, class_weight="balanced")
            clf_src.fit(X_src, y_src)
            w_src = clf_src.coef_[0]
            w_src_hat = w_src / (np.linalg.norm(w_src) + 1e-8)

            clf_tgt = LogisticRegression(l1_ratio=0, C=1.0, max_iter=2000, class_weight="balanced")
            clf_tgt.fit(X_tgt, y_tgt)

            # Within-tool IIA: train on 50% of target tool, evaluate on other 50%
            nt_total = min(len(valid_tools[t_tgt][0]), len(valid_tools[t_tgt][1]))
            if nt_total < 10:
                continue
            nt_train = nt_total // 2
            train_0 = rng.choice(valid_tools[t_tgt][0], size=nt_train, replace=False)
            train_1 = rng.choice(valid_tools[t_tgt][1], size=nt_train, replace=False)
            test_0 = [i for i in valid_tools[t_tgt][0] if i not in train_0]
            test_1 = [i for i in valid_tools[t_tgt][1] if i not in train_1]

            X_within_train = X[list(train_0) + list(train_1)]
            y_within_train = np.array([0]*nt_train + [1]*nt_train)
            clf_within = LogisticRegression(l1_ratio=0, C=1.0, max_iter=2000, class_weight="balanced")
            clf_within.fit(X_within_train, y_within_train)
            w_within_hat = clf_within.coef_[0] / (np.linalg.norm(clf_within.coef_[0]) + 1e-8)

            successes_within = 0
            nt_eval = min(len(test_0), len(test_1), n_pairs // 4)
            for _ in range(nt_eval):
                i0 = rng.choice(test_0)
                i1 = rng.choice(test_1)
                h0, h1 = X[i0], X[i1]
                p0 = np.dot(h0, w_within_hat) * w_within_hat
                p1 = np.dot(h1, w_within_hat) * w_within_hat
                h_int = h0 - p0 + p1
                logit_before = np.dot(clf_within.coef_[0], h0) + clf_within.intercept_[0]
                logit_after = np.dot(clf_within.coef_[0], h_int) + clf_within.intercept_[0]
                if logit_after - logit_before > 0:
                    successes_within += 1
            iia_within = successes_within / nt_eval if nt_eval > 0 else 0

            # Cross-tool IIA: swap along w_src, evaluate with clf_tgt
            ns = min(n_pairs // 4, len(valid_tools[t_tgt][0]), len(valid_tools[t_tgt][1]))
            successes_cross = 0
            for _ in range(ns):
                i0 = rng.choice(valid_tools[t_tgt][0])
                i1 = rng.choice(valid_tools[t_tgt][1])
                h0, h1 = X[i0], X[i1]
                p0 = np.dot(h0, w_src_hat) * w_src_hat
                p1 = np.dot(h1, w_src_hat) * w_src_hat
                h_int = h0 - p0 + p1
                # Evaluate using TARGET'S probe (not source's!)
                logit_before = np.dot(clf_tgt.coef_[0], h0) + clf_tgt.intercept_[0]
                logit_after = np.dot(clf_tgt.coef_[0], h_int) + clf_tgt.intercept_[0]
                if logit_after - logit_before > 0:
                    successes_cross += 1
            iia_cross = successes_cross / ns if ns > 0 else 0

            all_iia_within.append(iia_within)
            all_iia_cross.append(iia_cross)

    avg_within = np.mean(all_iia_within) if all_iia_within else 0
    avg_cross = np.mean(all_iia_cross) if all_iia_cross else 0
    gap = avg_cross - avg_within

    return {
        "iia_within": round(float(avg_within), 4),
        "iia_cross": round(float(avg_cross), 4),
        "gap_iia": round(float(gap), 4),
        "n_tool_pairs": len(all_iia_cross),
        "tool_pairs": [(t_src, t_tgt) for t_src in tool_list for t_tgt in tool_list if t_src != t_tgt],
    }


def main() -> None:
    import sys
    data_name = sys.argv[1] if len(sys.argv) > 1 else "qwen3-8b_scenarios_merged"

    print(f"Loading data: {data_name}")
    X, Y, meta, tools, texts = load_data(data_name)
    effect_names = meta["effect_names"]
    print(f"  Model: {meta['model']}")
    print(f"  Dim: {X.shape[1]}, Samples: {X.shape[0]}")
    print(f"  Effects: {len(effect_names)}")

    # Map effect → indices of ≥2 tools with sufficient samples
    effect_tools = {}
    for i, effect in enumerate(effect_names):
        tool_pos = defaultdict(int)
        for j, t in enumerate(tools):
            if Y[j, i] == 1:
                tool_pos[t] += 1
        valid = {t: c for t, c in tool_pos.items() if c >= 5}
        if len(valid) >= 2:
            effect_tools[effect] = valid

    print(f"\nEffects testable for cross-tool IIA: {len(effect_tools)}")
    for e, td in effect_tools.items():
        print(f"  {e:25s}: {len(td)} tools — {dict(td)}")

    # Train full linear probes
    print(f"\n{'=' * 90}")
    print("Interchange Intervention Experiment")
    print(f"{'=' * 90}")

    results = []
    for i, effect in enumerate(effect_names):
        if effect not in effect_tools:
            continue

        y = Y[:, i]
        print(f"\n  {effect} ...", end=" ", flush=True)
        iia_result = compute_cross_tool_iia(X, y, tools, i)

        if iia_result is None:
            print("insufficient data")
            continue

        gap = iia_result["gap_iia"]
        if gap > -0.10:
            verdict = "✓ CAUSAL CONCEPT"
        elif gap > -0.25:
            verdict = "~ PARTIAL"
        elif gap > -0.50:
            verdict = "◈ TOOL PROXY"
        else:
            verdict = "✗ PURE PROXY"

        iia_result["effect"] = effect
        iia_result["verdict"] = verdict
        results.append(iia_result)

        print(
            f"IIA_w={iia_result['iia_within']:.3f}  "
            f"IIA_c={iia_result['iia_cross']:.3f}  "
            f"gap={gap:+.4f}  {verdict}"
        )

    # Summary
    print(f"\n{'─' * 90}")
    causal = [r for r in results if r["gap_iia"] > -0.10]
    partial = [r for r in results if -0.25 < r["gap_iia"] <= -0.10]
    proxy = [r for r in results if r["gap_iia"] <= -0.25]
    print(f"IIA Results: {len(causal)} causal concept, {len(partial)} partial, {len(proxy)} tool proxy")

    if causal:
        print(f"  Causal: {[r['effect'] for r in causal]}")
    if proxy:
        print(f"  Proxy:  {[r['effect'] for r in proxy]}")

    # Save
    out = Path(__file__).resolve().parent.parent / "analysis" / f"iia_{data_name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str))
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
