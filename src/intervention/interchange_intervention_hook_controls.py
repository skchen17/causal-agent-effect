"""Hook-based pIIA control runs.

This script runs a deliberately small, auditable set of true forward-hook
interventions for pIIA controls:

* within-tool same-effect direction;
* same-effect wrong-form direction;
* matched-norm random direction;
* different-effect same-form direction;
* layer sweep;
* token aggregation / intervention placement ablation.

It is a control artifact, not a full mechanism proof. The default run is kept
small because Qwen3-8B hook interventions are expensive.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from transformers import AutoModel, AutoTokenizer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hook-based pIIA controls.")
    parser.add_argument("--data-name", default="qwen3-8b_scenarios_mainconf_v2")
    parser.add_argument("--model-name", default="Qwen/Qwen3-8B")
    parser.add_argument("--layers", nargs="*", type=int, default=[12, 24, 32])
    parser.add_argument("--token-modes", nargs="*", default=["mean_broadcast", "last_token"])
    parser.add_argument("--effects", nargs="*", help="Optional effects to run.")
    parser.add_argument("--max-effects", type=int, default=3)
    parser.add_argument("--max-eval-tools", type=int, default=1)
    parser.add_argument("--pairs-per-mode", type=int, default=2)
    parser.add_argument("--min-class-per-tool", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-json")
    parser.add_argument("--out-md")
    return parser.parse_args()


def load_data(base: Path, data_name: str) -> tuple[np.ndarray, np.ndarray, dict[str, Any], list[str], list[str]]:
    x = np.load(base / "embeddings" / f"embeddings_{data_name}.npy")
    y = np.load(base / "embeddings" / f"effects_{data_name}.npy")
    meta = json.loads((base / "embeddings" / f"meta_{data_name}.json").read_text(encoding="utf-8"))
    tools: list[str] = []
    texts: list[str] = []
    with (base / "embeddings" / f"texts_{data_name}.jsonl").open(encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            tools.append(item.get("tool_name", "unknown"))
            texts.append(item.get("text", ""))
    if len(texts) != len(y):
        raise ValueError(f"text/effect length mismatch: texts={len(texts)} effects={len(y)}")
    return x, y, meta, tools, texts


def get_layers(model: Any) -> Any:
    if hasattr(model, "layers"):
        return model.layers
    if hasattr(model, "model") and hasattr(model.model, "layers"):
        return model.model.layers
    raise AttributeError("Could not find transformer layers on model or model.model")


def unit(v: np.ndarray) -> np.ndarray:
    return v / (np.linalg.norm(v) + 1e-8)


def train_probe(x: np.ndarray, y: np.ndarray) -> LogisticRegression | None:
    if len(np.unique(y)) < 2:
        return None
    clf = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
    clf.fit(x, y)
    return clf


def pooled_from_hidden(hidden: torch.Tensor, mask: torch.Tensor, mode: str) -> torch.Tensor:
    if mode == "mean_broadcast":
        return (hidden * mask.unsqueeze(-1)).sum(dim=1) / mask.sum(dim=1, keepdim=True)
    if mode == "last_token":
        last = mask.sum(dim=1).long() - 1
        row = torch.arange(hidden.shape[0], device=hidden.device)
        return hidden[row, last]
    raise ValueError(f"Unsupported token mode: {mode}")


def mean_pool_final(hidden: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    return (hidden * mask.unsqueeze(-1)).sum(dim=1) / mask.sum(dim=1, keepdim=True)


def precompute_layer_pools(
    *,
    model: Any,
    tokenizer: Any,
    texts: list[str],
    layers: list[int],
    token_modes: list[str],
    batch_size: int,
    max_length: int,
) -> tuple[dict[int, dict[str, np.ndarray]], np.ndarray]:
    hidden_size = int(model.config.hidden_size)
    layer_pools = {
        layer: {mode: np.zeros((len(texts), hidden_size), dtype=np.float32) for mode in token_modes}
        for layer in layers
    }
    final_mean = np.zeros((len(texts), hidden_size), dtype=np.float32)

    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        inputs = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        ).to(model.device)
        with torch.no_grad():
            outputs = model(**inputs, output_hidden_states=True)
        mask = inputs["attention_mask"]
        for layer in layers:
            h = outputs.hidden_states[layer + 1]
            for mode in token_modes:
                layer_pools[layer][mode][start : start + len(batch)] = (
                    pooled_from_hidden(h, mask, mode).detach().cpu().to(torch.float32).numpy()
                )
        final_mean[start : start + len(batch)] = (
            mean_pool_final(outputs.last_hidden_state, mask).detach().cpu().to(torch.float32).numpy()
        )
        print(f"  pooled {min(start + batch_size, len(texts))}/{len(texts)}", flush=True)

    return layer_pools, final_mean


def summarize_loto_gaps(base: Path, data_name: str) -> dict[str, dict[str, float]]:
    path = base / "analysis" / f"baseline_comparison_{data_name}.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    table = payload.get("loto_table", {})
    out: dict[str, dict[str, float]] = {}
    for effect, by_tool in table.items():
        gaps = [float(row.get("FNR_gap", 0.0)) for row in by_tool.values()]
        held = [float(row.get("heldout_FNR", 0.0)) for row in by_tool.values()]
        out[effect] = {
            "max_loto_gap": round(max(gaps), 4) if gaps else math.nan,
            "max_heldout_fnr": round(max(held), 4) if held else math.nan,
        }
    return out


def rankdata(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and values[order[j + 1]] == values[order[i]]:
            j += 1
        rank = (i + j + 2) / 2.0
        for k in range(i, j + 1):
            ranks[order[k]] = rank
        i = j + 1
    return ranks


def spearman(x: list[float], y: list[float]) -> float | None:
    if len(x) < 3 or len(y) < 3:
        return None
    rx = np.array(rankdata(x), dtype=float)
    ry = np.array(rankdata(y), dtype=float)
    if float(rx.std()) == 0.0 or float(ry.std()) == 0.0:
        return None
    return round(float(np.corrcoef(rx, ry)[0, 1]), 4)


def valid_effect_tools(
    y: np.ndarray,
    tools: list[str],
    min_class: int,
) -> dict[str, dict[int, list[int]]]:
    groups: dict[str, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    for idx, tool in enumerate(tools):
        groups[tool][int(y[idx])].append(idx)
    return {
        tool: dict(by_label)
        for tool, by_label in groups.items()
        if len(by_label.get(0, [])) >= min_class and len(by_label.get(1, [])) >= min_class
    }


def choose_effects(
    *,
    effect_names: list[str],
    y_all: np.ndarray,
    tools: list[str],
    min_class: int,
    requested: list[str] | None,
    max_effects: int,
    loto_gaps: dict[str, dict[str, float]],
) -> list[str]:
    testable = []
    for ei, effect in enumerate(effect_names):
        groups = valid_effect_tools(y_all[:, ei], tools, min_class)
        if len(groups) >= 2:
            testable.append(effect)
    if requested:
        missing = [e for e in requested if e not in testable]
        if missing:
            print(f"Skipping non-testable requested effects: {missing}", flush=True)
        return [e for e in requested if e in testable]

    def priority(effect: str) -> tuple[float, str]:
        return (float(loto_gaps.get(effect, {}).get("max_loto_gap", 0.0)), effect)

    return sorted(testable, key=priority, reverse=True)[:max_effects]


def choose_wrong_effect(
    *,
    effect_idx: int,
    y_all: np.ndarray,
    effect_names: list[str],
    tool_indices: list[int],
) -> int | None:
    for candidate in range(y_all.shape[1]):
        if candidate == effect_idx:
            continue
        y = y_all[tool_indices, candidate]
        if len(np.unique(y)) == 2 and min(np.bincount(y.astype(int))) >= 5:
            return candidate
    return None


def build_intervened_state(
    *,
    h_base: torch.Tensor,
    h_source: torch.Tensor,
    mask_base: torch.Tensor,
    mask_source: torch.Tensor,
    direction: np.ndarray,
    mode: str,
) -> tuple[torch.Tensor, float, float, float]:
    w = torch.from_numpy(unit(direction).astype(np.float32)).to(h_base.device, dtype=h_base.dtype)
    if mode == "mean_broadcast":
        pooled_base = pooled_from_hidden(h_base, mask_base, mode)
        pooled_source = pooled_from_hidden(h_source, mask_source, mode)
        proj_base = float((pooled_base @ w).detach().cpu().item())
        proj_source = float((pooled_source @ w).detach().cpu().item())
        delta = proj_source - proj_base
        return h_base + delta * w.view(1, 1, -1), proj_base, proj_source, delta

    if mode == "last_token":
        pooled_base = pooled_from_hidden(h_base, mask_base, mode)
        pooled_source = pooled_from_hidden(h_source, mask_source, mode)
        proj_base = float((pooled_base @ w).detach().cpu().item())
        proj_source = float((pooled_source @ w).detach().cpu().item())
        delta = proj_source - proj_base
        h_int = h_base.clone()
        last = int(mask_base.sum(dim=1).long().item() - 1)
        h_int[0, last, :] = h_int[0, last, :] + delta * w
        return h_int, proj_base, proj_source, delta

    raise ValueError(f"Unsupported token mode: {mode}")


def run_one_intervention(
    *,
    model: Any,
    tokenizer: Any,
    layer_module: Any,
    layer: int,
    max_length: int,
    base_text: str,
    source_text: str,
    direction: np.ndarray,
    token_mode: str,
    eval_probe: LogisticRegression,
    score_before: float,
) -> dict[str, Any]:
    intervened_state: torch.Tensor | None = None

    def hook(_module: Any, _inputs: Any, output: Any) -> Any:
        if intervened_state is None:
            return output
        if isinstance(output, tuple):
            return (intervened_state.to(output[0].device, dtype=output[0].dtype),) + output[1:]
        return intervened_state.to(output.device, dtype=output.dtype)

    handle = layer_module.register_forward_hook(hook)
    try:
        with torch.no_grad():
            tok_base = tokenizer(
                base_text,
                truncation=True,
                max_length=max_length,
                return_tensors="pt",
            ).to(model.device)
            out_base = model(**tok_base, output_hidden_states=True)
            h_base = out_base.hidden_states[layer + 1]
            mask_base = tok_base["attention_mask"]

            tok_source = tokenizer(
                source_text,
                truncation=True,
                max_length=max_length,
                return_tensors="pt",
            ).to(model.device)
            out_source = model(**tok_source, output_hidden_states=True)
            h_source = out_source.hidden_states[layer + 1]
            mask_source = tok_source["attention_mask"]

            intervened_state, proj_base, proj_source, proj_delta = build_intervened_state(
                h_base=h_base,
                h_source=h_source,
                mask_base=mask_base,
                mask_source=mask_source,
                direction=direction,
                mode=token_mode,
            )
            out_int = model(**tok_base, output_hidden_states=False)
            intervened_state = None
            pooled_int = mean_pool_final(out_int.last_hidden_state, mask_base).detach().cpu().to(torch.float32).numpy()
    finally:
        intervened_state = None
        handle.remove()

    score_after = float(eval_probe.predict_proba(pooled_int)[:, 1][0])
    return {
        "score_before": score_before,
        "score_after": score_after,
        "score_delta": score_after - score_before,
        "success_score_increase": bool(score_after > score_before),
        "crosses_threshold_0_5": bool(score_before <= 0.5 < score_after),
        "base_projection": proj_base,
        "source_projection": proj_source,
        "projection_delta": proj_delta,
    }


def aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, int, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["effect"], row["layer"], row["token_mode"], row["mode"])].append(row)

    out: list[dict[str, Any]] = []
    for (effect, layer, token_mode, mode), vals in sorted(groups.items()):
        out.append(
            {
                "effect": effect,
                "layer": layer,
                "token_mode": token_mode,
                "mode": mode,
                "n": len(vals),
                "score_increase_rate": round(float(np.mean([v["success_score_increase"] for v in vals])), 4),
                "threshold_cross_rate": round(float(np.mean([v["crosses_threshold_0_5"] for v in vals])), 4),
                "mean_score_delta": round(float(np.mean([v["score_delta"] for v in vals])), 4),
            }
        )
    return out


def effect_drop_summary(aggregates: list[dict[str, Any]], preferred_layer: int) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    by_key = {(r["effect"], r["layer"], r["token_mode"], r["mode"]): r for r in aggregates}
    effects = sorted({r["effect"] for r in aggregates})
    token_modes = sorted({r["token_mode"] for r in aggregates})
    for effect in effects:
        rows = []
        for token_mode in token_modes:
            within = by_key.get((effect, preferred_layer, token_mode, "within_tool_direction"))
            cross = by_key.get((effect, preferred_layer, token_mode, "same_effect_wrong_form_direction"))
            if within and cross:
                rows.append(
                    {
                        "token_mode": token_mode,
                        "within_score_increase_rate": within["score_increase_rate"],
                        "cross_score_increase_rate": cross["score_increase_rate"],
                        "piia_drop": round(within["score_increase_rate"] - cross["score_increase_rate"], 4),
                    }
                )
        if rows:
            out[effect] = {
                "preferred_layer": preferred_layer,
                "rows": rows,
                "mean_piia_drop": round(float(np.mean([r["piia_drop"] for r in rows])), 4),
            }
    return out


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Hook-Based pIIA Controls",
        "",
        f"- Data: `{payload['data_name']}`",
        f"- Model: `{payload['model_name']}`",
        f"- Effects: {', '.join(payload['effects_run'])}",
        f"- Layers: {payload['layers']}",
        f"- Token modes: {payload['token_modes']}",
        f"- Raw intervention rows: {payload['n_raw_rows']}",
        "",
        "## Aggregate Outcomes",
        "",
        "| Effect | Layer | Token mode | Mode | N | Score inc | Threshold cross | Mean delta |",
        "|---|---:|---|---|---:|---:|---:|---:|",
    ]
    for row in payload["aggregates"]:
        lines.append(
            f"| `{row['effect']}` | {row['layer']} | `{row['token_mode']}` | `{row['mode']}` | "
            f"{row['n']} | {row['score_increase_rate']} | {row['threshold_cross_rate']} | {row['mean_score_delta']} |"
        )

    lines.extend(["", "## pIIA-Drop Summary", ""])
    if payload["piia_drop_summary"]:
        lines.append("| Effect | Preferred layer | Mean pIIA-Drop | Details |")
        lines.append("|---|---:|---:|---|")
        for effect, row in payload["piia_drop_summary"].items():
            detail = "; ".join(
                f"{r['token_mode']}: {r['within_score_increase_rate']}->{r['cross_score_increase_rate']}"
                for r in row["rows"]
            )
            lines.append(f"| `{effect}` | {row['preferred_layer']} | {row['mean_piia_drop']} | {detail} |")
    else:
        lines.append("- Not enough within/cross rows to compute pIIA-Drop.")

    lines.extend(["", "## pIIA-Drop vs LOTO Gap", ""])
    corr = payload["piia_loto_correlation"]
    lines.append(f"- Spearman rho against max LOTO FNR gap: {corr.get('spearman_piia_drop_vs_loto_gap')}")
    lines.append(f"- Spearman rho against max heldout FNR: {corr.get('spearman_piia_drop_vs_heldout_fnr')}")
    lines.append(f"- Evaluable effects: {corr.get('n_effects')}")

    lines.extend(["", "## Caveats", ""])
    for caveat in payload["caveats"]:
        lines.append(f"- {caveat}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    base = Path(__file__).resolve().parent.parent
    _, y_all, meta, tools, texts = load_data(base, args.data_name)
    effect_names = list(meta["effect_names"])
    loto_gaps = summarize_loto_gaps(base, args.data_name)
    chosen_effects = choose_effects(
        effect_names=effect_names,
        y_all=y_all,
        tools=tools,
        min_class=args.min_class_per_tool,
        requested=args.effects,
        max_effects=args.max_effects,
        loto_gaps=loto_gaps,
    )
    if not chosen_effects:
        raise RuntimeError("No testable effects found for hook controls.")

    print(f"Loading {args.model_name}", flush=True)
    model = AutoModel.from_pretrained(
        args.model_name,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(args.model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    transformer_layers = get_layers(model)

    print("Precomputing layer/final pools", flush=True)
    layer_pools, final_mean = precompute_layer_pools(
        model=model,
        tokenizer=tokenizer,
        texts=texts,
        layers=args.layers,
        token_modes=args.token_modes,
        batch_size=args.batch_size,
        max_length=args.max_length,
    )

    rng = np.random.default_rng(args.seed)
    raw_rows: list[dict[str, Any]] = []

    for effect in chosen_effects:
        effect_idx = effect_names.index(effect)
        y = y_all[:, effect_idx]
        groups = valid_effect_tools(y, tools, args.min_class_per_tool)
        ordered_tools = sorted(
            groups,
            key=lambda t: (len(groups[t].get(1, [])), t),
            reverse=True,
        )[: args.max_eval_tools]
        print(f"Running {effect}: eval tools={ordered_tools}", flush=True)

        for layer in args.layers:
            for token_mode in args.token_modes:
                local_probes: dict[str, LogisticRegression] = {}
                eval_probes: dict[str, LogisticRegression] = {}
                wrong_effect_dirs: dict[str, tuple[str, np.ndarray]] = {}
                for tool in groups:
                    idx = np.array(groups[tool][0] + groups[tool][1], dtype=int)
                    local_probe = train_probe(layer_pools[layer][token_mode][idx], y[idx])
                    eval_probe = train_probe(final_mean[idx], y[idx])
                    if local_probe is not None and eval_probe is not None:
                        local_probes[tool] = local_probe
                        eval_probes[tool] = eval_probe
                    wrong_idx = choose_wrong_effect(
                        effect_idx=effect_idx,
                        y_all=y_all,
                        effect_names=effect_names,
                        tool_indices=idx.tolist(),
                    )
                    if wrong_idx is not None:
                        wrong_y = y_all[idx, wrong_idx]
                        wrong_probe = train_probe(layer_pools[layer][token_mode][idx], wrong_y)
                        if wrong_probe is not None:
                            wrong_effect_dirs[tool] = (effect_names[wrong_idx], wrong_probe.coef_[0])

                for eval_tool in ordered_tools:
                    if eval_tool not in local_probes or eval_tool not in eval_probes:
                        continue
                    base_candidates = groups[eval_tool][0]
                    source_candidates = groups[eval_tool][1]
                    n_pairs = min(args.pairs_per_mode, len(base_candidates), len(source_candidates))
                    if n_pairs <= 0:
                        continue

                    eval_probe = eval_probes[eval_tool]
                    within_direction = local_probes[eval_tool].coef_[0]
                    cross_tools = [tool for tool in local_probes if tool != eval_tool]
                    cross_tool = cross_tools[0] if cross_tools else None
                    random_direction = unit(rng.normal(size=within_direction.shape).astype(np.float32))
                    random_direction = random_direction * float(np.linalg.norm(within_direction))

                    modes: list[tuple[str, str, np.ndarray, str | None]] = [
                        ("within_tool_direction", eval_tool, within_direction, None),
                        ("matched_norm_random_direction", "random", random_direction, None),
                    ]
                    if cross_tool is not None:
                        modes.append(
                            (
                                "same_effect_wrong_form_direction",
                                cross_tool,
                                local_probes[cross_tool].coef_[0],
                                None,
                            )
                        )
                    if eval_tool in wrong_effect_dirs:
                        wrong_effect_name, wrong_direction = wrong_effect_dirs[eval_tool]
                        modes.append(
                            (
                                "different_effect_same_form_direction",
                                eval_tool,
                                wrong_direction,
                                wrong_effect_name,
                            )
                        )

                    for pair_id in range(n_pairs):
                        base_idx = int(rng.choice(base_candidates))
                        source_idx = int(rng.choice(source_candidates))
                        score_before = float(eval_probe.predict_proba(final_mean[base_idx : base_idx + 1])[:, 1][0])
                        for mode_name, direction_tool, direction, wrong_effect_name in modes:
                            outcome = run_one_intervention(
                                model=model,
                                tokenizer=tokenizer,
                                layer_module=transformer_layers[layer],
                                layer=layer,
                                max_length=args.max_length,
                                base_text=texts[base_idx],
                                source_text=texts[source_idx],
                                direction=direction,
                                token_mode=token_mode,
                                eval_probe=eval_probe,
                                score_before=score_before,
                            )
                            raw_rows.append(
                                {
                                    "effect": effect,
                                    "layer": layer,
                                    "token_mode": token_mode,
                                    "mode": mode_name,
                                    "evaluation_tool": eval_tool,
                                    "direction_tool": direction_tool,
                                    "wrong_effect_name": wrong_effect_name,
                                    "base_index": base_idx,
                                    "source_index": source_idx,
                                    "base_example_tool": eval_tool,
                                    "source_example_tool": eval_tool,
                                    "seed": args.seed,
                                    "pair_id": pair_id,
                                    **outcome,
                                }
                            )
                    print(
                        f"  {effect} layer={layer} token={token_mode} eval_tool={eval_tool}: "
                        f"{len(raw_rows)} total rows",
                        flush=True,
                    )

    aggregates = aggregate_rows(raw_rows)
    preferred_layer = 24 if 24 in args.layers else args.layers[len(args.layers) // 2]
    drop_summary = effect_drop_summary(aggregates, preferred_layer)
    corr_effects = []
    piia_drops = []
    loto_gap_vals = []
    heldout_vals = []
    for effect, row in drop_summary.items():
        if effect not in loto_gaps:
            continue
        corr_effects.append(effect)
        piia_drops.append(float(row["mean_piia_drop"]))
        loto_gap_vals.append(float(loto_gaps[effect]["max_loto_gap"]))
        heldout_vals.append(float(loto_gaps[effect]["max_heldout_fnr"]))

    payload = {
        "data_name": args.data_name,
        "model_name": args.model_name,
        "seed": args.seed,
        "layers": args.layers,
        "token_modes": args.token_modes,
        "pairs_per_mode": args.pairs_per_mode,
        "max_eval_tools": args.max_eval_tools,
        "effects_run": chosen_effects,
        "n_raw_rows": len(raw_rows),
        "raw_rows": raw_rows,
        "aggregates": aggregates,
        "piia_drop_summary": drop_summary,
        "piia_loto_correlation": {
            "effects": corr_effects,
            "spearman_piia_drop_vs_loto_gap": spearman(piia_drops, loto_gap_vals),
            "spearman_piia_drop_vs_heldout_fnr": spearman(piia_drops, heldout_vals),
            "n_effects": len(corr_effects),
            "note": "Correlation is limited by the selected effects and pairs per condition.",
        },
        "caveats": [
            "This hook-control run remains limited by the selected effects and pairs per condition.",
            "Score-increase pIIA is a probe-mediated activation transfer diagnostic, not SCM IIA.",
            "The random control is matched to the within-tool direction norm before intervention.",
            "The wrong-form direction uses another tool's same-effect probe; source/base examples remain from the evaluation tool.",
            "Strong paper claims should report per-condition sample size and avoid treating pIIA as SCM-style causal proof.",
        ],
    }

    out_json = Path(args.out_json) if args.out_json else base / "analysis" / f"piia_hook_controls_{args.data_name}.json"
    out_md = Path(args.out_md) if args.out_md else base / "analysis" / f"piia_hook_controls_{args.data_name}.md"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown(out_md, payload)
    print(f"Saved JSON: {out_json}")
    print(f"Saved MD:   {out_md}")


if __name__ == "__main__":
    main()
