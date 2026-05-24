"""pIIA control diagnostics.

This script is deliberately conservative about what it claims. It does not
replace hook-based pIIA controls. It adds three reproducible control layers:

1. direction controls: random-direction, wrong-effect, cross-tool direction cos;
2. embedding-space matched-norm intervention controls on final embeddings;
3. summaries of existing hook-based raw pIIA outcomes when available.

The output marks hook-based random/layer/token controls as not_run unless those
raw artifacts exist. This prevents the report from overstating completion.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression


def load(data_name: str):
    base = Path(__file__).resolve().parent.parent
    X = np.load(base / f"embeddings/embeddings_{data_name}.npy")
    Y = np.load(base / f"embeddings/effects_{data_name}.npy")
    tools, texts = [], []
    with open(base / f"embeddings/texts_{data_name}.jsonl", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            tools.append(item.get("tool_name", "unknown"))
            texts.append(item.get("text", ""))
    meta = json.loads((base / f"embeddings/meta_{data_name}.json").read_text(encoding="utf-8"))
    return X, Y, meta, tools, texts


def unit(v: np.ndarray) -> np.ndarray:
    return v / (np.linalg.norm(v) + 1e-8)


def train_probe(X: np.ndarray, y: np.ndarray) -> LogisticRegression | None:
    if len(np.unique(y)) < 2:
        return None
    clf = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
    clf.fit(X, y)
    return clf


def embedding_space_control(
    *,
    X: np.ndarray,
    y: np.ndarray,
    tools: list[str],
    eval_tool: str,
    direction: np.ndarray,
    rng: np.random.Generator,
    n_pairs: int = 100,
) -> dict[str, Any] | None:
    idx0 = np.array([i for i, t in enumerate(tools) if t == eval_tool and y[i] == 0], dtype=int)
    idx1 = np.array([i for i, t in enumerate(tools) if t == eval_tool and y[i] == 1], dtype=int)
    if len(idx0) < 5 or len(idx1) < 5:
        return None
    local_idx = np.concatenate([idx0, idx1])
    local_y = y[local_idx]
    eval_probe = train_probe(X[local_idx], local_y)
    if eval_probe is None:
        return None

    w = unit(direction)
    n = min(n_pairs, len(idx0) * len(idx1))
    score_increase = 0
    threshold_cross = 0
    deltas = []
    for _ in range(n):
        b = int(rng.choice(idx0))
        s = int(rng.choice(idx1))
        proj_b = float(X[b] @ w)
        proj_s = float(X[s] @ w)
        delta = proj_s - proj_b
        x_int = X[b] + delta * w
        before = float(eval_probe.predict_proba(X[b : b + 1])[:, 1][0])
        after = float(eval_probe.predict_proba(x_int.reshape(1, -1))[:, 1][0])
        score_increase += int(after > before)
        threshold_cross += int(before <= 0.5 < after)
        deltas.append(after - before)

    return {
        "n_pairs": n,
        "score_increase_rate": round(score_increase / n, 4) if n else None,
        "threshold_cross_rate": round(threshold_cross / n, 4) if n else None,
        "mean_score_delta": round(float(np.mean(deltas)), 4) if deltas else None,
    }


def summarize_raw_piia(base: Path, data_name: str) -> dict[str, Any] | None:
    raw_path = base / "analysis" / f"iia_true_raw_{data_name}.jsonl"
    if not raw_path.exists():
        return None
    rows = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines()]
    by_effect_mode: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_effect_mode[(row["effect"], row["mode"])].append(row)

    summary: dict[str, Any] = {}
    for (effect, mode), vals in sorted(by_effect_mode.items()):
        key = summary.setdefault(effect, {})
        key[mode] = {
            "n": len(vals),
            "score_increase_rate": round(float(np.mean([v["success_score_increase"] for v in vals])), 4),
            "threshold_cross_rate": round(float(np.mean([v["crosses_threshold_0_5"] for v in vals])), 4),
            "mean_score_delta": round(float(np.mean([v["score_delta"] for v in vals])), 4),
        }
    return {
        "raw_path": str(raw_path),
        "n_rows": len(rows),
        "summary_by_effect_mode": summary,
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# pIIA Controls",
        "",
        f"- Data: `{payload['data_name']}`",
        f"- Samples: {payload['n_samples']}",
        f"- Control level: {payload['control_level']}",
        "",
        "## Direction And Embedding-Space Controls",
        "",
        "| Effect | Random cos | Wrong effect | Wrong cos | Cross-tool dir cos | Random score inc | Wrong score inc |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for effect, row in payload["effects"].items():
        random_inc = row.get("embedding_random_control", {}).get("score_increase_rate")
        wrong_inc = row.get("embedding_wrong_effect_control", {}).get("score_increase_rate")
        lines.append(
            f"| `{effect}` | {row.get('random_direction', {}).get('cos_with_effect_direction')} | "
            f"`{row.get('wrong_effect_direction', {}).get('effect')}` | "
            f"{row.get('wrong_effect_direction', {}).get('abs_cos_with_effect_direction')} | "
            f"{row.get('cross_tool_direction_cos', {}).get('mean')} | {random_inc} | {wrong_inc} |"
        )

    raw = payload.get("hook_raw_piia_summary")
    lines.extend(["", "## Hook Raw pIIA Summary", ""])
    if raw is None:
        lines.append("- No hook-based raw pIIA outcomes found for this data name.")
    else:
        lines.append(f"- Raw file: `{raw['raw_path']}`")
        lines.append(f"- Rows: {raw['n_rows']}")

    lines.extend(["", "## Missing Controls", ""])
    for item in payload["missing_controls"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Caveats", ""])
    for caveat in payload["caveats"]:
        lines.append(f"- {caveat}")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    data_name = sys.argv[1] if len(sys.argv) > 1 else "qwen3-8b_scenarios_mainconf_v2"
    base = Path(__file__).resolve().parent.parent
    X, Y, meta, tools, texts = load(data_name)
    effect_names = meta["effect_names"]
    rng = np.random.default_rng(42)
    d = X.shape[1]

    results: dict[str, Any] = {}
    for ei, effect in enumerate(effect_names):
        y = Y[:, ei]
        if int(y.sum()) < 10 or len(np.unique(y)) < 2:
            continue
        clf = train_probe(X, y)
        if clf is None:
            continue
        w_effect = clf.coef_[0]
        w_norm = np.linalg.norm(w_effect)

        random_w = rng.normal(0, 1, d).astype(np.float32)
        random_w = unit(random_w) * w_norm

        wrong_ei = next((j for j in range(len(effect_names)) if j != ei and len(np.unique(Y[:, j])) == 2), None)
        wrong_effect_payload: dict[str, Any] = {"effect": None, "abs_cos_with_effect_direction": None}
        wrong_w = None
        if wrong_ei is not None:
            wrong_clf = train_probe(X, Y[:, wrong_ei])
            if wrong_clf is not None:
                wrong_w = wrong_clf.coef_[0]
                wrong_effect_payload = {
                    "effect": effect_names[wrong_ei],
                    "abs_cos_with_effect_direction": round(float(abs(unit(w_effect) @ unit(wrong_w))), 4),
                }

        tool_dirs = {}
        for tool in sorted(set(tools)):
            idx = np.array([i for i, t in enumerate(tools) if t == tool], dtype=int)
            if len(idx) < 10 or len(np.unique(y[idx])) < 2:
                continue
            local_clf = train_probe(X[idx], y[idx])
            if local_clf is not None:
                tool_dirs[tool] = local_clf.coef_[0]

        cross_tool_cos = None
        if len(tool_dirs) >= 2:
            vals = []
            for a, b in itertools_combinations(sorted(tool_dirs), 2):
                vals.append(float(unit(tool_dirs[a]) @ unit(tool_dirs[b])))
            cross_tool_cos = {
                "n_tools": len(tool_dirs),
                "mean": round(float(np.mean(vals)), 4),
                "min": round(float(np.min(vals)), 4),
                "max": round(float(np.max(vals)), 4),
            }

        eval_tool = None
        tool_pos_counts = Counter(t for i, t in enumerate(tools) if y[i] == 1)
        for tool, count in tool_pos_counts.most_common():
            neg_count = sum(1 for i, t in enumerate(tools) if t == tool and y[i] == 0)
            if count >= 5 and neg_count >= 5:
                eval_tool = tool
                break

        embedding_random = None
        embedding_wrong = None
        if eval_tool is not None:
            embedding_random = embedding_space_control(
                X=X, y=y, tools=tools, eval_tool=eval_tool, direction=random_w, rng=rng
            )
            if wrong_w is not None:
                embedding_wrong = embedding_space_control(
                    X=X, y=y, tools=tools, eval_tool=eval_tool, direction=wrong_w, rng=rng
                )

        results[effect] = {
            "n_positive": int(y.sum()),
            "random_direction": {
                "matched_norm": round(float(np.linalg.norm(random_w)), 4),
                "effect_direction_norm": round(float(w_norm), 4),
                "cos_with_effect_direction": round(float(unit(random_w) @ unit(w_effect)), 4),
            },
            "wrong_effect_direction": wrong_effect_payload,
            "cross_tool_direction_cos": cross_tool_cos,
            "embedding_control_eval_tool": eval_tool,
            "embedding_random_control": {"mean_score_increase_rate": None} if embedding_random is None else embedding_random,
            "embedding_wrong_effect_control": {"mean_score_increase_rate": None} if embedding_wrong is None else embedding_wrong,
        }

    payload = {
        "data_name": data_name,
        "n_samples": int(X.shape[0]),
        "control_level": "direction controls + final-embedding matched-norm controls; hook random/layer/token controls not run here",
        "effects": results,
        "hook_raw_piia_summary": summarize_raw_piia(base, data_name),
        "missing_controls": [
            "hook-based matched-norm random intervention outcomes",
            "hook-based same-effect wrong-form intervention controls",
            "hook-based different-effect same-form negative controls",
            "layer sweep",
            "token aggregation ablation",
        ],
        "caveats": [
            "Embedding-space controls are not equivalent to hook-based pIIA through upper-layer propagation.",
            "Use this file to audit obvious direction/norm artifacts, not as final mechanism evidence.",
            "T43 remains partial until hook-based controls and layer/token ablations are run.",
        ],
    }

    out_json = base / "analysis" / f"piia_controls_{data_name}.json"
    out_md = base / "analysis" / f"piia_controls_{data_name}.md"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown(out_md, payload)
    print(f"Saved JSON: {out_json}")
    print(f"Saved MD:   {out_md}")
    print(f"Effects: {len(results)}")


def itertools_combinations(items: list[str], r: int):
    if r != 2:
        raise ValueError("Only pair combinations are used.")
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            yield items[i], items[j]


if __name__ == "__main__":
    main()
