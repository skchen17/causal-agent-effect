"""Analyze causal-chain conditioning effects from extracted embeddings.

This script is intentionally evidence-producing rather than claim-producing:
it reports LOTO FNR, ToolProxyGap, tool separability on positive samples, and
typed wrong-chain subsets when the input data contains ``wrong_chain_type``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.multiclass import OneVsRestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score


FOCUS_EFFECTS = ["content_fetched", "file_written", "network_egress", "tool_error"]


def make_clf() -> LogisticRegression:
    return LogisticRegression(
        C=1.0,
        max_iter=500,
        class_weight="balanced",
        solver="liblinear",
        random_state=0,
    )


def resolve_model_data(model: str, data: str) -> str:
    if data.startswith(f"{model}_"):
        return data
    return f"{model}_{data}"


def load_inputs(base: Path, model: str, data: str) -> tuple[np.ndarray, np.ndarray, list[dict], list[str], str]:
    data_name = resolve_model_data(model, data)
    data_file = data_name.removeprefix(f"{model}_")

    emb_path = base / "embeddings" / f"embeddings_{data_name}.npy"
    eff_path = base / "embeddings" / f"effects_{data_name}.npy"
    meta_path = base / "embeddings" / f"meta_{data_name}.json"
    jsonl_path = base / "data" / f"{data_file}.jsonl"

    missing = [p for p in [emb_path, eff_path, meta_path, jsonl_path] if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing causal-chain inputs: " + ", ".join(str(p) for p in missing))

    X = np.load(emb_path)
    Y = np.load(eff_path)
    with open(jsonl_path, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]
    with open(meta_path, encoding="utf-8") as f:
        effect_names = json.load(f)["effect_names"]

    if X.shape[0] != Y.shape[0] or X.shape[0] != len(rows):
        raise ValueError(f"Length mismatch: X={X.shape}, Y={Y.shape}, rows={len(rows)}")

    return X, Y, rows, effect_names, data_name


def fnr(labels: np.ndarray, preds: np.ndarray) -> float:
    return 1.0 - recall_score(labels, preds, zero_division=0)


def fit_predict_fnr(X: np.ndarray, y: np.ndarray, train_idx: list[int], eval_idx: list[int]) -> tuple[float | None, float | None]:
    if len(train_idx) < 10 or len(eval_idx) < 10:
        return None, None
    if len(set(y[train_idx])) < 2 or len(set(y[eval_idx])) < 2:
        return None, None

    clf = make_clf()
    clf.fit(X[train_idx], y[train_idx])
    pred = clf.predict(X[eval_idx])
    score = fnr(y[eval_idx], pred)

    auc = None
    if len(set(y[eval_idx])) >= 2:
        auc = float(roc_auc_score(y[eval_idx], clf.predict_proba(X[eval_idx])[:, 1]))
    return float(score), auc


def within_tool_fnr(X: np.ndarray, y: np.ndarray, idx: list[int]) -> float | None:
    if len(idx) < 12 or len(set(y[idx])) < 2:
        return None
    counts = np.bincount(y[idx].astype(int))
    if len(counts) < 2 or counts.min() < 3:
        return None

    cv = StratifiedKFold(n_splits=min(3, int(counts.min())), shuffle=True, random_state=0)
    preds = np.zeros(len(idx), dtype=int)
    idx_arr = np.array(idx)
    for train_sub, test_sub in cv.split(X[idx_arr], y[idx_arr]):
        clf = make_clf()
        clf.fit(X[idx_arr[train_sub]], y[idx_arr[train_sub]])
        preds[test_sub] = clf.predict(X[idx_arr[test_sub]])
    return fnr(y[idx_arr], preds)


def tool_discriminator_acc(X: np.ndarray, y: np.ndarray, tools: list[str]) -> float | None:
    pos_idx = [i for i, val in enumerate(y) if val == 1]
    if len(pos_idx) < 10:
        return None

    pos_tools = [tools[i] for i in pos_idx]
    unique_tools = sorted(set(pos_tools))
    if len(unique_tools) < 2:
        return None

    labels = np.array([unique_tools.index(t) for t in pos_tools])
    counts = np.bincount(labels)
    n_splits = min(3, int(counts.min()))
    if n_splits < 2:
        return None

    clf = OneVsRestClassifier(make_clf())
    return float(np.mean(cross_val_score(clf, X[pos_idx], labels, cv=n_splits)))


def cross_tool_distance(X: np.ndarray, y: np.ndarray, tools: list[str]) -> float | None:
    pos_by_tool: dict[str, list[int]] = {}
    for i, (tool, label) in enumerate(zip(tools, y)):
        if label == 1:
            pos_by_tool.setdefault(tool, []).append(i)

    dists = []
    valid_tools = sorted(t for t, idx in pos_by_tool.items() if len(idx) >= 3)
    for i, tool_a in enumerate(valid_tools):
        for tool_b in valid_tools[i + 1:]:
            mean_a = X[pos_by_tool[tool_a]].mean(axis=0)
            mean_b = X[pos_by_tool[tool_b]].mean(axis=0)
            dists.append(float(np.linalg.norm(mean_a - mean_b)))
    return float(np.mean(dists)) if dists else None


def evaluate_group(X: np.ndarray, y: np.ndarray, tools: list[str]) -> dict:
    unique_tools = sorted(set(tools))
    tool_rows = []
    held_fnrs = []
    within_fnrs = []
    aucs = []

    for tool in unique_tools:
        eval_idx = [i for i, t in enumerate(tools) if t == tool]
        train_idx = [i for i, t in enumerate(tools) if t != tool]

        held, auc = fit_predict_fnr(X, y, train_idx, eval_idx)
        within = within_tool_fnr(X, y, eval_idx)

        if held is not None:
            held_fnrs.append(held)
        if within is not None:
            within_fnrs.append(within)
        if auc is not None:
            aucs.append(auc)

        delta = None
        gap = None
        if held is not None and within is not None:
            delta = held - within
            gap = max(0.0, delta)

        tool_rows.append({
            "tool": tool,
            "n": len(eval_idx),
            "n_positive": int(y[eval_idx].sum()) if eval_idx else 0,
            "held_fnr": round(held, 4) if held is not None else None,
            "within_fnr": round(within, 4) if within is not None else None,
            "delta_fnr": round(delta, 4) if delta is not None else None,
            "toolproxy_gap": round(gap, 4) if gap is not None else None,
            "held_auc": round(auc, 4) if auc is not None else None,
        })

    gaps = [r["toolproxy_gap"] for r in tool_rows if r["toolproxy_gap"] is not None]
    td_acc = tool_discriminator_acc(X, y, tools)
    cross_dist = cross_tool_distance(X, y, tools)
    return {
        "n_samples": int(len(y)),
        "n_positive": int(y.sum()),
        "num_eval_tools": len([r for r in tool_rows if r["held_fnr"] is not None]),
        "max_held_fnr": round(max(held_fnrs), 4) if held_fnrs else None,
        "max_within_fnr": round(max(within_fnrs), 4) if within_fnrs else None,
        "toolproxy_gap": round(max(gaps), 4) if gaps else None,
        "tool_discriminator_acc_e1": round(td_acc, 4) if td_acc is not None else None,
        "cross_tool_distance_mean": round(cross_dist, 4) if cross_dist is not None else None,
        "effect_probe_auc": round(float(np.mean(aucs)), 4) if aucs else None,
        "tool_results": tool_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen3-8b")
    parser.add_argument("--data", default="causal_chain_conditioning_v2")
    parser.add_argument("--output-suffix", default=None)
    args = parser.parse_args()

    base = Path(__file__).parent.parent
    X, Y, rows, effect_names, data_name = load_inputs(base, args.model, args.data)

    conditions = [r["condition"] for r in rows]
    tools = [r["tool_name"] for r in rows]
    group_defs: list[tuple[str, list[int]]] = []
    for condition in sorted(set(conditions)):
        group_defs.append((condition, [i for i, c in enumerate(conditions) if c == condition]))

    wrong_types = sorted({r.get("wrong_chain_type") for r in rows if r.get("condition") == "wrong_chain" and r.get("wrong_chain_type")})
    for wrong_type in wrong_types:
        group_defs.append((
            f"wrong_chain:{wrong_type}",
            [i for i, r in enumerate(rows) if r.get("condition") == "wrong_chain" and r.get("wrong_chain_type") == wrong_type],
        ))

    effects = {}
    for effect_idx, effect in enumerate(effect_names):
        if effect not in FOCUS_EFFECTS:
            continue
        effect_results = {}
        y_all = Y[:, effect_idx]
        for group_name, idx in group_defs:
            idx_arr = np.array(idx)
            effect_results[group_name] = evaluate_group(
                X[idx_arr],
                y_all[idx_arr],
                [tools[i] for i in idx],
            )
        effects[effect] = effect_results

    wrong_chain_counts: dict[str, int] = {}
    for row in rows:
        if row.get("condition") == "wrong_chain":
            key = row.get("wrong_chain_type", "none")
            wrong_chain_counts[key] = wrong_chain_counts.get(key, 0) + 1

    payload = {
        "schema_version": "causal_chain_mechanism_v2",
        "generated_by": "analysis/analyze_causal_chain_mechanism.py",
        "config": {
            "model": args.model,
            "data": args.data,
            "data_name": data_name,
            "focus_effects": FOCUS_EFFECTS,
        },
        "summary": {
            "n_samples": len(rows),
            "conditions": sorted(set(conditions)),
            "wrong_chain_type_counts": wrong_chain_counts,
            "typed_wrong_chain_present": {"authorization_flip", "effect_flip", "effect_omission"}.issubset(wrong_chain_counts),
        },
        "effects": effects,
    }

    suffix = args.output_suffix or data_name
    out = base / "analysis" / f"causal_chain_mechanism_{suffix}.json"
    out.write_text(json.dumps(payload, indent=2))

    md = [
        "# Causal-Chain Mechanism Analysis",
        "",
        f"- Model: `{args.model}`",
        f"- Data: `{data_name}`",
        f"- Samples: `{len(rows)}`",
        f"- Wrong-chain types: `{wrong_chain_counts}`",
        "",
        "| Effect | Group | N | N+ | max Held-FNR | max Within-FNR | ToolProxyGap | ToolDisc(E=1) | CrossDist | EffAUC |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for effect, groups in effects.items():
        for group, vals in groups.items():
            def fmt(value):
                return "-" if value is None else f"{value:.4f}" if isinstance(value, float) else str(value)

            md.append(
                "| "
                + " | ".join([
                    effect,
                    group,
                    str(vals["n_samples"]),
                    str(vals["n_positive"]),
                    fmt(vals["max_held_fnr"]),
                    fmt(vals["max_within_fnr"]),
                    fmt(vals["toolproxy_gap"]),
                    fmt(vals["tool_discriminator_acc_e1"]),
                    fmt(vals["cross_tool_distance_mean"]),
                    fmt(vals["effect_probe_auc"]),
                ])
                + " |"
            )
    out_md = base / "analysis" / f"causal_chain_mechanism_{suffix}.md"
    out_md.write_text("\n".join(md))

    # Backward-compatible aliases used by earlier planning docs.
    if args.data.endswith("_v2") or data_name.endswith("_v2"):
        alias_json = base / "analysis" / f"causal_chain_mechanism_{args.model}_v2.json"
        alias_md = base / "analysis" / f"causal_chain_mechanism_{args.model}_v2.md"
        alias_json.write_text(json.dumps(payload, indent=2))
        alias_md.write_text("\n".join(md))

    print(f"Saved to {out}")
    print(f"Saved to {out_md}")


if __name__ == "__main__":
    main()
