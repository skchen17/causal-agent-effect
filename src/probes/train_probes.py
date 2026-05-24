"""
Phase 3: Linear + Nonlinear probe training and comparison.

For each causal effect, train:
  - Linear probe: LogisticRegression (L2-regularized)
  - Nonlinear probe: MLPClassifier (2 hidden layers, ReLU)

Compute Δ = F1_MLP - F1_LogReg to test whether each effect is
linearly encoded (Δ ≈ 0) or requires nonlinear decoding (Δ >> 0).

This is the operationalization of Sutter et al. (NeurIPS 2025)'s
"Non-Linear Representation Dilemma" in agent safety.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import cross_val_predict, StratifiedKFold
from sklearn.metrics import f1_score, roc_auc_score, accuracy_score
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_data(data_name: str = "scenarios_counterfactual") -> tuple[np.ndarray, np.ndarray, dict]:
    """Load embeddings and effects. Auto-detects which data to use.

    Supports prefixes like 'qwen_scenarios_merged' → looks for
    embeddings_qwen_scenarios_merged.npy or embeddings_scenarios_merged.npy
    """
    base = Path(__file__).resolve().parent.parent
    emb_dir = base / "embeddings"

    # Direct path with full data_name
    emb_path = emb_dir / f"embeddings_{data_name}.npy"
    eff_path = emb_dir / f"effects_{data_name}.npy"
    meta_path = emb_dir / f"meta_{data_name}.json"

    if not emb_path.exists():
        # Try without prefix
        emb_path = emb_dir / "embeddings.npy"
        eff_path = emb_dir / "effects.npy"
        meta_path = emb_dir / "meta.json"

    if not emb_path.exists():
        raise FileNotFoundError(
            f"No embeddings found for '{data_name}' at {emb_dir}"
        )

    X = np.load(emb_path)
    Y = np.load(eff_path)
    with open(meta_path) as f:
        meta = json.load(f)
    return X, Y, meta


def train_probes(
    X: np.ndarray,
    y: np.ndarray,
    n_folds: int = 5,
    seed: int = 42,
) -> dict:
    """Train linear and nonlinear probes, return comparison metrics."""
    n_pos = int(y.sum())
    n_neg = len(y) - n_pos

    if n_pos < n_folds * 2 or n_pos == 0 or n_neg == 0:
        return _insufficient_result(n_pos, n_neg)

    cv = StratifiedKFold(n_splits=min(n_folds, n_pos), shuffle=True, random_state=seed)

    # ── Linear probe ──
    clf_lin = LogisticRegression(
        l1_ratio=0,  # equivalent to L2 penalty
        C=1.0,
        solver="lbfgs",
        max_iter=2000,
        random_state=seed,
        class_weight="balanced",
    )

    try:
        y_pred_lin = cross_val_predict(clf_lin, X, y, cv=cv, method="predict")
        y_proba_lin = cross_val_predict(clf_lin, X, y, cv=cv, method="predict_proba")[:, 1]
    except ValueError:
        return _insufficient_result(n_pos, n_neg)

    f1_lin = f1_score(y, y_pred_lin, zero_division=0)
    auc_lin = roc_auc_score(y, y_proba_lin) if n_pos > 0 and n_neg > 0 else 0.5
    acc_lin = accuracy_score(y, y_pred_lin)

    # ── Nonlinear probe (MLP) ──
    # Adapt architecture to sample size to prevent overfitting
    # With very small N+, MLP is unreliable — use a lighter nonlinear method
    if n_pos < 30:
        # Use kernel approximation (RBF) for small-N effects
        # Note: RBF fitted per CV fold to avoid data leakage
        from sklearn.kernel_approximation import RBFSampler
        from sklearn.linear_model import LogisticRegression as LinRegRBF
        from sklearn.pipeline import Pipeline
        rbf = RBFSampler(gamma=0.1, n_components=min(64, X.shape[1]), random_state=seed)
        clf_mlp = Pipeline([
            ("rbf", rbf),
            ("lr", LinRegRBF(l1_ratio=0, C=1.0, max_iter=2000,
                             random_state=seed, class_weight="balanced")),
        ])
        X_nl = X  # Pipeline handles transform internally per CV fold
    elif n_pos < 100:
        clf_mlp = MLPClassifier(
            hidden_layer_sizes=(64, 32),
            activation="relu",
            alpha=0.01,
            batch_size=32,
            max_iter=500,
            early_stopping=True,
            validation_fraction=0.15,
            n_iter_no_change=15,
            random_state=seed,
        )
        X_nl = X
    else:
        clf_mlp = MLPClassifier(
            hidden_layer_sizes=(128, 64),
            activation="relu",
            alpha=0.001,
            batch_size=64,
            max_iter=500,
            early_stopping=True,
            validation_fraction=0.15,
            n_iter_no_change=15,
            random_state=seed,
        )
        X_nl = X

    try:
        y_pred_mlp = cross_val_predict(clf_mlp, X_nl, y, cv=cv, method="predict")
        y_proba_mlp = cross_val_predict(clf_mlp, X_nl, y, cv=cv, method="predict_proba")[:, 1]
    except ValueError:
        return _insufficient_result(n_pos, n_neg)

    f1_mlp = f1_score(y, y_pred_mlp, zero_division=0)
    auc_mlp = roc_auc_score(y, y_proba_mlp) if n_pos > 0 and n_neg > 0 else 0.5
    acc_mlp = accuracy_score(y, y_pred_mlp)

    # Type of nonlinear method
    nl_method = "RBF-kernel" if n_pos < 30 else \
                "MLP(64,32)" if n_pos < 100 else "MLP(128,64)"

    # ── Delta (only meaningful when both probes converged) ──
    mlp_converged = f1_mlp > 0.3  # heuristic: MLP got some signal
    delta_f1 = round(float(f1_mlp - f1_lin), 4) if mlp_converged else None

    # ── Extract linear probe weights (full retrain) ──
    clf_full = LogisticRegression(
        l1_ratio=0, C=1.0, solver="lbfgs", max_iter=2000,
        random_state=seed, class_weight="balanced",
    )
    clf_full.fit(X, y)
    probe_weights = clf_full.coef_[0]

    return {
        "n_pos": n_pos,
        "n_neg": n_neg,
        "balance": round(n_pos / len(y), 3),
        "nl_method": nl_method,
        "linear": {
            "f1": round(float(f1_lin), 4),
            "auc": round(float(auc_lin), 4),
            "accuracy": round(float(acc_lin), 4),
        },
        "nonlinear": {
            "f1": round(float(f1_mlp), 4),
            "auc": round(float(auc_mlp), 4),
            "accuracy": round(float(acc_mlp), 4),
            "converged": mlp_converged,
        },
        "delta": {
            "f1": delta_f1,
            "method": nl_method,
        },
        "probe_norm": round(float(np.linalg.norm(probe_weights)), 4),
        "insufficient": False,
    }


def _insufficient_result(n_pos: int, n_neg: int) -> dict:
    return {
        "n_pos": n_pos, "n_neg": n_neg, "balance": 0.0,
        "nl_method": "none",
        "linear": {"f1": 0.0, "auc": 0.5, "accuracy": 0.0},
        "nonlinear": {"f1": 0.0, "auc": 0.5, "accuracy": 0.0, "converged": False},
        "delta": {"f1": None, "method": "none"},
        "probe_norm": 0.0, "insufficient": True,
    }


def analyze_and_plot(
    results: dict[str, dict],
    effect_names: list[str],
    tier_map: dict[str, str],
    out_dir: Path,
    data_name: str = "counterfactual",
) -> None:
    """Analyze linear vs nonlinear comparison and generate visualizations."""
    out_dir.mkdir(parents=True, exist_ok=True)

    valid = [(e, r) for e, r in results.items() if not r["insufficient"]]
    insufficient = [e for e, r in results.items() if r["insufficient"]]

    # Sort: first by delta (largest gap = most nonlinear), None at end
    ranked = sorted(valid, key=lambda x: (
        x[1]["delta"]["f1"] is None, -(x[1]["delta"]["f1"] or -999)
    ))

    # ── Sort: converged deltas first, then non-converged ──
    conv = [(e, r) for e, r in ranked if r["nonlinear"]["converged"]]
    nonconv = [(e, r) for e, r in ranked if not r["nonlinear"]["converged"]]
    display_order = sorted(conv, key=lambda x: -(x[1]["delta"]["f1"] or 0)) + nonconv
    nl_converged = [r["nonlinear"]["converged"] for _, r in display_order]

    # ── Console report ──
    print(f"\n{'=' * 100}")
    print(f"Linear vs Nonlinear Probe Comparison — {data_name}")
    print(f"{'=' * 100}")
    header = (f"{'Effect':<25s} {'N+':>4s} {'F1_lin':>7s} {'F1_nl':>7s} {'Δ':>7s} "
              f"{'NL method':>14s} {'Tier':>8s} {'Verdict':>14s}")
    print(header)
    print("-" * 100)

    for effect, r in display_order:
        tier = tier_map.get(effect, "UNKNOWN")
        d = r["delta"]
        n_pos = r["n_pos"]

        if not r["nonlinear"]["converged"]:
            verdict = "⚠ NL FAIL"
            delta_str = "  N/A"
        elif d["f1"] is not None and d["f1"] < -0.02:
            # Nonlinear probe is WORSE than linear — data may be too small
            # or nonlinear method is poorly suited. Inconclusive.
            verdict = "⚠ NL WORSE"
            delta_str = f"{d['f1']:+7.4f}"
        elif d["f1"] is not None and d["f1"] <= 0.02:
            verdict = "✓ LINEAR"
            delta_str = f"{d['f1']:+7.4f}"
        elif d["f1"] is not None and d["f1"] <= 0.08:
            verdict = "~ MIXED"
            delta_str = f"{d['f1']:+7.4f}"
        elif d["f1"] is not None and d["f1"] <= 0.20:
            verdict = "◈ NONLINEAR"
            delta_str = f"{d['f1']:+7.4f}"
        elif d["f1"] is not None:
            verdict = "✗ HOLLOW"
            delta_str = f"{d['f1']:+7.4f}"
        else:
            verdict = "⚠ NL FAIL"
            delta_str = "  N/A"

        print(
            f"{effect:<25s} {n_pos:4d} "
            f"{r['linear']['f1']:7.4f} {r['nonlinear']['f1']:7.4f} "
            f"{delta_str} {r['nl_method']:>14s} {tier:>8s} {verdict:>14s}"
        )

    if insufficient:
        print(f"\nInsufficient data: {', '.join(insufficient)}")

    # ── Tier summary (only converged deltas) ──
    print(f"\n{'─' * 100}")
    print("Delta (Δ) by Risk Tier (converged effects only):")
    tier_deltas: dict[str, list[float]] = {}
    for effect, r in conv:
        tier = tier_map.get(effect, "UNKNOWN")
        if r["delta"]["f1"] is not None:
            tier_deltas.setdefault(tier, []).append(r["delta"]["f1"])

    for tier in ["HIGH", "MEDIUM", "LOW", "BENIGN"]:
        if tier in tier_deltas:
            ds = tier_deltas[tier]
            avg = sum(ds) / len(ds) if ds else 0
            print(f"  {tier:10s}: avg Δ={avg:.4f}  "
                  f"(n={len(ds)}, range=[{min(ds):.4f}, {max(ds):.4f}])")
        else:
            print(f"  {tier:10s}: (no converged effects)")

    # Verdict counts
    n_total = len(valid)
    n_linear = len([e for e, r in conv if r["delta"]["f1"] is not None and -0.02 <= r["delta"]["f1"] <= 0.02])
    n_worse = len([e for e, r in conv if r["delta"]["f1"] is not None and r["delta"]["f1"] < -0.02])
    n_mixed = len([e for e, r in conv if r["delta"]["f1"] is not None and 0.02 < r["delta"]["f1"] <= 0.08])
    n_nonlinear = len([e for e, r in conv if r["delta"]["f1"] is not None and r["delta"]["f1"] > 0.08])
    n_failed = len(nonconv)
    n_conv = len(conv)
    print(f"\nSummary: {n_conv}/{n_total} effects had converged nonlinear probes — "
          f"{n_linear} linear (|Δ|≤0.02), {n_worse} NL-worse, {n_mixed} mixed, {n_nonlinear} nonlinear. "
          f"{n_failed} NL probes failed (data too small).")

    # ── Generate charts ──
    _plot_delta_comparison(display_order, tier_map, out_dir, data_name, nl_conv=nl_converged)

    # ── Save results ──
    report = {
        "data_name": data_name,
        "ranking": [(e, r) for e, r in ranked],
        "insufficient": insufficient,
        "verdicts": {
            "linear": [e for e, r in conv if r["delta"]["f1"] is not None and -0.02 <= r["delta"]["f1"] <= 0.02],
            "nl_worse": [e for e, r in conv if r["delta"]["f1"] is not None and r["delta"]["f1"] < -0.02],
            "mixed": [e for e, r in conv if r["delta"]["f1"] is not None and 0.02 < r["delta"]["f1"] <= 0.08],
            "nonlinear": [e for e, r in conv if r["delta"]["f1"] is not None and r["delta"]["f1"] > 0.08],
            "nl_failed": nonconv,
        },
        "tier_delta_summary": {
            tier: {
                "avg_delta": sum(ds) / len(ds) if ds else 0.0,
                "count": len(ds),
                "min_delta": min(ds) if ds else 0.0,
                "max_delta": max(ds) if ds else 0.0,
            }
            for tier, ds in tier_deltas.items()
        },
    }
    report_path = out_dir / f"results_{data_name}.json"
    # Convert numpy values for JSON serialization
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str)
    )
    print(f"\nResults saved to {report_path}")


def _plot_delta_comparison(
    ranked: list[tuple[str, dict]],
    tier_map: dict[str, str],
    out_dir: Path,
    data_name: str,
    nl_conv: list[bool] = None,
) -> None:
    """Visualize linear vs nonlinear comparison."""
    effects = [e for e, _ in ranked]
    f1_lins = [r["linear"]["f1"] for _, r in ranked]
    f1_mlps = [r["nonlinear"]["f1"] for _, r in ranked]
    deltas = [(r["delta"]["f1"] if r["delta"]["f1"] is not None else 0.0) for _, r in ranked]
    if nl_conv is None:
        nl_conv = [r["nonlinear"]["converged"] for _, r in ranked]
    tiers = [tier_map.get(e, "UNKNOWN") for e in effects]

    tier_colors = {
        "HIGH": "#d62728", "MEDIUM": "#2ca02c",
        "LOW": "#1f77b4", "BENIGN": "#7f7f7f",
    }
    colors = [tier_colors.get(t, "#7f7f7f") for t in tiers]

    fig, axes = plt.subplots(2, 2, figsize=(18, 14))

    # ── Subplot 1: F1_linear vs F1_MLP side-by-side ──
    ax1 = axes[0, 0]
    y_pos = range(len(effects))
    height = 0.35
    ax1.barh([y + height / 2 for y in y_pos], f1_lins, height,
             color="#3182bd", alpha=0.85, label="Linear (LogReg)")
    ax1.barh([y - height / 2 for y in y_pos], f1_mlps, height,
             color="#de2d26", alpha=0.85, label="Nonlinear (MLP)")
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(effects, fontsize=9)
    ax1.invert_yaxis()
    ax1.set_xlabel("F1 Score")
    ax1.set_title(f"Linear vs Nonlinear Probe F1 ({data_name})")
    ax1.legend(loc="lower right", fontsize=8)
    ax1.axvline(x=0.7, color="gray", linestyle="--", alpha=0.3)
    ax1.set_xlim(0, 1.05)

    # ── Subplot 2: Delta (F1_MLP - F1_LogReg) ──
    ax2 = axes[0, 1]
    bar_colors = []
    for i, (d, conv) in enumerate(zip(deltas, nl_conv)):
        if not conv:
            bar_colors.append("#cccccc")  # gray = NL failed
        elif d < -0.02:
            bar_colors.append("#9467bd")  # purple = NL worse (inconclusive)
        elif d <= 0.02:
            bar_colors.append("#2ca02c")  # green = linear
        elif d <= 0.08:
            bar_colors.append("#ff7f0e")  # orange = mixed
        else:
            bar_colors.append("#d62728")  # red = nonlinear
    ax2.barh(y_pos, deltas, color=bar_colors, alpha=0.85, edgecolor="white")
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(effects, fontsize=9)
    ax2.invert_yaxis()
    ax2.set_xlabel("Δ = F1_nl - F1_lin")
    ax2.set_title("Encoding Linearity Gap (gray = NL probe failed)")
    ax2.axvline(x=0.02, color="green", linestyle="--", alpha=0.5, label="Linear (0.02)")
    ax2.axvline(x=0.08, color="orange", linestyle="--", alpha=0.5, label="Mixed (0.08)")
    ax2.axvline(x=0.20, color="red", linestyle="--", alpha=0.5, label="Hollow (0.20)")
    ax2.legend(loc="lower right", fontsize=7)

    # ── Subplot 3: Delta by Risk Tier (converged only) ──
    ax3 = axes[1, 0]
    tier_order = ["HIGH", "MEDIUM", "LOW", "BENIGN"]
    tier_data = {}
    for e, r in ranked:
        t = tier_map.get(e, "UNKNOWN")
        if r["delta"]["f1"] is not None:
            tier_data.setdefault(t, []).append(r["delta"]["f1"])
    box_labels = [t for t in tier_order if t in tier_data and tier_data[t]]
    box_data = [tier_data[t] for t in box_labels]
    box_colors = [tier_colors[t] for t in box_labels]
    if box_data:
        bp = ax3.boxplot(box_data, tick_labels=box_labels, patch_artist=True)
        for patch, color in zip(bp["boxes"], box_colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)
        for i, (label, data) in enumerate(zip(box_labels, box_data)):
            jitter = np.random.default_rng(42).normal(0, 0.04, len(data))
            ax3.scatter([i + 1 + x for x in jitter], data, alpha=0.5, s=20, color="black")
    ax3.axhline(y=0.02, color="green", linestyle="--", alpha=0.4, label="Linear threshold")
    ax3.set_ylabel("Δ = F1_nl - F1_lin")
    ax3.set_title("Encoding Linearity Gap by Risk Tier")
    ax3.legend(fontsize=7)

    # ── Subplot 4: F1_linear vs effect frequency ──
    ax4 = axes[1, 1]
    n_pos = [r["n_pos"] for _, r in ranked]
    ax4.scatter(n_pos, f1_lins, c=colors, s=80, alpha=0.7, edgecolors="black", linewidth=0.5)
    for i, e in enumerate(effects):
        ax4.annotate(e.split("_")[0], (n_pos[i], f1_lins[i]),
                     fontsize=7, alpha=0.8,
                     xytext=(5, 5), textcoords="offset points")
    ax4.set_xlabel("Number of Positive Samples")
    ax4.set_ylabel("F1 (Linear Probe)")
    ax4.set_title("Linear Encodability vs Effect Frequency")
    ax4.axhline(y=0.7, color="gray", linestyle="--", alpha=0.4)
    ax4.set_xlim(left=0)

    plt.tight_layout()
    chart_path = out_dir / f"delta_comparison_{data_name}.png"
    fig.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Chart saved to {chart_path}")


def main() -> None:
    import sys
    data_name = sys.argv[1] if len(sys.argv) > 1 else "scenarios_counterfactual"

    print(f"Loading data: {data_name}")
    X, Y, meta = load_data(data_name)
    effect_names = meta["effect_names"]
    print(f"  Embeddings: {X.shape}")
    print(f"  Effects: {Y.shape} ({len(effect_names)} effects)")
    print(f"  Model: {meta['model']}")

    tier_map = {
        "command_executed": "HIGH",
        "file_written": "MEDIUM",
        "file_deleted": "HIGH",
        "file_content_read": "LOW",
        "message_sent": "HIGH",
        "network_egress": "HIGH",
        "subagent_spawned": "HIGH",
        "content_fetched": "LOW",
        "search_performed": "LOW",
        "memory_updated": "LOW",
        "tool_error": "BENIGN",
    }

    print(f"\nTraining linear + nonlinear probes ({len(effect_names)} effects)...")
    results = {}
    for i, effect in enumerate(effect_names):
        y = Y[:, i]
        r = train_probes(X, y)
        results[effect] = r

        if not r["insufficient"]:
            d = r["delta"]["f1"]
            if not r["nonlinear"]["converged"]:
                symbol = "⚠"
            elif d is not None and d <= 0.02:
                symbol = "="
            elif d is not None and d <= 0.08:
                symbol = "~"
            elif d is not None and d <= 0.20:
                symbol = ">"
            else:
                symbol = ">>"
            delta_str = f"Δ={d:+.4f}" if d is not None else "Δ=N/A"
            print(
                f"  {symbol} {effect:<25s} "
                f"F1_lin={r['linear']['f1']:.4f} F1_nl={r['nonlinear']['f1']:.4f} "
                f"{delta_str} N+={r['n_pos']:3d} [{r['nl_method']}]"
            )
        else:
            print(f"  ✗ {effect:<25s} insufficient data (N+={r['n_pos']})")

    out_dir = Path(__file__).resolve().parent.parent / "analysis"
    analyze_and_plot(results, effect_names, tier_map, out_dir, data_name)


if __name__ == "__main__":
    main()
