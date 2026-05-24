"""
交互式分析脚本: 探索因果效果的线性可编码性。

用法: python notebooks/explore_encodability.py
  (在 train_probes.py 完成后运行)
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # 加载结果
    results_path = Path(__file__).parent.parent / "analysis" / "results.json"
    if not results_path.exists():
        print("Run train_probes.py first to generate results.")
        return

    with open(results_path) as f:
        report = json.load(f)

    # 加载数据
    embeddings_dir = Path(__file__).parent.parent / "embeddings"
    X = np.load(embeddings_dir / "embeddings.npy")
    Y = np.load(embeddings_dir / "effects.npy")
    with open(embeddings_dir / "meta.json") as f:
        meta = json.load(f)

    effects = meta["effect_names"]

    # ── 1. 线性可编码性排名 ─────────────────────────
    ranking = report["ranking"]
    print("=" * 70)
    print("Top 5: Most linearly encodable effects")
    for i, (e, r) in enumerate(ranking[:5]):
        print(f"  {i+1}. {e}: F1={r['f1']:.4f} AUC={r['auc']:.4f}")

    print("\nBottom 5: Least linearly encodable effects")
    for i, (e, r) in enumerate(ranking[-5:]):
        print(f"  {len(ranking)-4+i}. {e}: F1={r['f1']:.4f} AUC={r['auc']:.4f}")

    # ── 2. 按风险等级 ─────────────────────────────
    tier_colors = {
        "CRITICAL": "#d62728", "HIGH": "#ff7f0e",
        "MEDIUM": "#2ca02c", "LOW": "#1f77b4", "BENIGN": "#7f7f7f",
    }
    print("\n" + "-" * 70)
    print("By risk tier:")
    for tier_name in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "BENIGN"]:
        ts = report["tier_summary"].get(tier_name, {})
        if ts:
            print(f"  {tier_name}: avg F1={ts['avg_f1']:.4f} n={ts['count']}")

    # ── 3. 嵌入空间可视化 (PCA) ──────────────────
    print("\nGenerating PCA visualization...")
    from sklearn.decomposition import PCA

    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X)

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # 按工具着色
    tools = []
    with open(embeddings_dir / "texts.jsonl") as f:
        for line in f:
            tools.append(json.loads(line)["tool_name"])

    tool_set = sorted(set(tools))
    tool_colors = plt.cm.tab10(np.linspace(0, 1, len(tool_set)))
    for ax_idx, (title, labels, cmap) in enumerate([
        ("By Tool", tools, dict(zip(tool_set, tool_colors))),
    ]):
        ax = axes[ax_idx]
        for label in set(labels):
            mask = [l == label for l in labels]
            ax.scatter(
                X_pca[mask, 0], X_pca[mask, 1],
                c=[cmap[label]], label=label, alpha=0.5, s=10,
            )
        ax.set_title(title)
        ax.legend(markerscale=3, fontsize=7, loc="upper right")

    # 按效果着色: command_executed
    ce_idx = effects.index("command_executed")
    axes[1].scatter(
        X_pca[:, 0], X_pca[:, 1],
        c=Y[:, ce_idx], cmap="coolwarm", alpha=0.5, s=10,
    )
    axes[1].set_title("Colored by: command_executed")

    # 按效果着色: file_written
    fw_idx = effects.index("file_written")
    axes[2].scatter(
        X_pca[:, 0], X_pca[:, 1],
        c=Y[:, fw_idx], cmap="coolwarm", alpha=0.5, s=10,
    )
    axes[2].set_title("Colored by: file_written")

    plt.tight_layout()
    out_dir = Path(__file__).parent.parent / "analysis"
    fig.savefig(out_dir / "embedding_viz.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved to {out_dir / 'embedding_viz.png'}")

    # ── 4. 关键发现摘要 ───────────────────────────
    print("\n" + "=" * 70)
    print("KEY FINDINGS")
    print("=" * 70)

    high_enc = [e for e, r in ranking if r["f1"] > 0.7 and not r.get("insufficient")]
    mid_enc = [e for e, r in ranking if 0.5 < r["f1"] <= 0.7 and not r.get("insufficient")]
    low_enc = [e for e, r in ranking if r["f1"] <= 0.5 and not r.get("insufficient")]
    insufficient = report.get("insufficient", [])

    print(f"  High encodability (F1>0.7): {len(high_enc)} effects")
    if high_enc:
        print(f"    {', '.join(high_enc)}")

    print(f"  Medium encodability (0.5<F1<=0.7): {len(mid_enc)} effects")
    if mid_enc:
        print(f"    {', '.join(mid_enc)}")

    print(f"  Low encodability (F1<=0.5): {len(low_enc)} effects")
    if low_enc:
        print(f"    {', '.join(low_enc)}")

    if insufficient:
        print(f"  Insufficient data: {len(insufficient)} effects")
        print(f"    {', '.join(insufficient)}")

    print(f"\n  Interpretation: {len(high_enc)}/{len(effects)} effects are ")
    print(f"  reliably linearly encodable in {meta['model']} embeddings.")


if __name__ == "__main__":
    main()
