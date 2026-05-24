"""
True Interchange Intervention using forward hooks.

Strategy:
  1. Register a forward hook on model.layers[INTERVENTION_LAYER]
  2. During normal forward pass, the hook intercepts the layer output
  3. Apply the subspace swap intervention on the hidden states
  4. Pass the modified hidden states to subsequent layers
  5. The model handles RoPE, attention masks, etc. automatically

This is the standard approach for IIT with HuggingFace models.
"""

from __future__ import annotations

import json
import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from transformers import AutoModel, AutoTokenizer

INTERVENTION_LAYER = 24  # 0-indexed, 2/3 of 36 layers


def load_model_and_data(data_name: str):
    base = Path(__file__).resolve().parent.parent
    emb_dir = base / "embeddings"

    X = np.load(emb_dir / f"embeddings_{data_name}.npy")
    Y = np.load(emb_dir / f"effects_{data_name}.npy")
    with open(emb_dir / f"meta_{data_name}.json") as f:
        meta = json.load(f)

    texts_path = emb_dir / f"texts_{data_name}.jsonl"
    tools, texts = [], []
    with open(texts_path, encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            tools.append(item.get("tool_name", "unknown"))
            texts.append(item.get("text", ""))

    model = AutoModel.from_pretrained(
        "Qwen/Qwen3-8B", torch_dtype=torch.bfloat16,
        device_map="auto", trust_remote_code=True,
    )
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B", trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    return model, tokenizer, X, Y, meta, tools, texts


def run_ii_experiment(
    model, tokenizer, scenarios, effect_name, effect_idx,
    all_Y, all_tools, n_pairs=200, seed=42, collect_raw=False,
) -> tuple[dict, list[dict]] | None:
    rng = np.random.default_rng(seed)
    y = all_Y[:, effect_idx]
    d = model.config.hidden_size

    groups: dict[str, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    for i in range(len(y)):
        groups[all_tools[i]][int(y[i])].append(i)

    valid_tools = {t for t in groups if len(groups[t][0]) >= 5 and len(groups[t][1]) >= 5}
    if len(valid_tools) < 2:
        return None
    tool_list = sorted(valid_tools)

    # ── Precompute L24 + final hidden states ──
    print("    pooling...", end=" ", flush=True)
    h_L24 = np.zeros((len(y), d), dtype=np.float32)
    h_final = np.zeros((len(y), d), dtype=np.float32)
    batch_size = 8
    for i in range(0, len(scenarios), batch_size):
        batch_texts = scenarios[i : i + batch_size]
        inputs = tokenizer(batch_texts, padding=True, truncation=True, max_length=256, return_tensors="pt").to(model.device)
        with torch.no_grad():
            outputs = model(**inputs, output_hidden_states=True)
            h24 = outputs.hidden_states[INTERVENTION_LAYER + 1]
            mask = inputs["attention_mask"].unsqueeze(-1)
            h_L24[i : i + batch_size] = (h24 * mask).sum(dim=1).cpu().to(torch.float32).numpy() / mask.sum(dim=1).cpu().float().numpy()
            hL = outputs.last_hidden_state
            h_final[i : i + batch_size] = (hL * mask).sum(dim=1).cpu().to(torch.float32).numpy() / mask.sum(dim=1).cpu().float().numpy()

    # Train per-tool probes on L24 (for intervention direction) AND final (for evaluation)
    probes_L24 = {}   # probe trained on L24 → provides intervention direction w
    probes_final = {} # probe trained on final → provides evaluation
    for t in tool_list:
        idxs = groups[t][0] + groups[t][1]
        X24_t, Xf_t = h_L24[idxs], h_final[idxs]
        y_t = y[idxs]
        if y_t.sum() == 0 or y_t.sum() == len(y_t):
            continue
        c24 = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
        c24.fit(X24_t, y_t)
        probes_L24[t] = c24
        cf = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
        cf.fit(Xf_t, y_t)
        probes_final[t] = cf
    print("done.", flush=True)

    # ── IIA via hook-based intervention ──
    # The hook captures layer ℓ's output, applies swap, returns modified tensor
    intervened_state = None  # will be set per sample

    def intervention_hook(module, input, output):
        """Hook on layer INTERVENTION_LAYER. Modifies output in-place."""
        nonlocal intervened_state
        if intervened_state is not None:
            # output is (hidden_states, ...) tuple
            if isinstance(output, tuple):
                return (intervened_state.to(output[0].device, dtype=output[0].dtype),) + output[1:]
            else:
                return intervened_state.to(output.device, dtype=output.dtype)
        return output

    hook_handle = model.layers[INTERVENTION_LAYER].register_forward_hook(intervention_hook)

    all_iia_within, all_iia_cross = [], []
    raw_outcomes: list[dict] = []

    for t_src in tool_list:
        for t_tgt in tool_list:
            if t_src == t_tgt:
                continue
            if t_src not in probes_L24 or t_tgt not in probes_L24:
                continue
            if t_src not in probes_final or t_tgt not in probes_final:
                continue

            # Intervention directions from L24-trained probes (same layer being intervened)
            w_src = probes_L24[t_src].coef_[0]
            w_src_hat = w_src / (np.linalg.norm(w_src) + 1e-8)
            w_tgt = probes_L24[t_tgt].coef_[0]
            w_tgt_hat = w_tgt / (np.linalg.norm(w_tgt) + 1e-8)

            # Within-tool IIA
            nt = min(n_pairs // 4, len(groups[t_tgt][0]), len(groups[t_tgt][1]))
            successes_within = 0
            for pair_id in range(nt):
                i0 = int(rng.choice(groups[t_tgt][0]))
                i1 = int(rng.choice(groups[t_tgt][1]))

                # Compute intervened hidden state at layer ℓ
                with torch.no_grad():
                    # Forward pass for base (E=0) to get layer-ℓ output
                    tok0 = tokenizer(scenarios[i0], truncation=True, max_length=256, return_tensors="pt").to(model.device)
                    outputs0 = model(**tok0, output_hidden_states=True)
                    h_ell_0 = outputs0.hidden_states[INTERVENTION_LAYER + 1]  # after layer ℓ

                    # Forward pass for source (E=1) to get layer-ℓ output
                    tok1 = tokenizer(scenarios[i1], truncation=True, max_length=256, return_tensors="pt").to(model.device)
                    outputs1 = model(**tok1, output_hidden_states=True)
                    h_ell_1 = outputs1.hidden_states[INTERVENTION_LAYER + 1]

                    # Compute mean projections along w_tgt
                    mask0 = tok0["attention_mask"]
                    mask1 = tok1["attention_mask"]
                    mean0 = (h_ell_0 * mask0.unsqueeze(-1)).sum(dim=1) / mask0.sum(dim=1, keepdim=True)  # (1, d)
                    mean1 = (h_ell_1 * mask1.unsqueeze(-1)).sum(dim=1) / mask1.sum(dim=1, keepdim=True)  # (1, d)

                    w_tgt_tensor = torch.from_numpy(w_tgt_hat).to(mean0.device, dtype=mean0.dtype)
                    proj0 = (mean0 @ w_tgt_tensor).item()
                    proj1 = (mean1 @ w_tgt_tensor).item()
                    delta = proj1 - proj0

                    # Create intervened hidden state: add delta * w_hat to every token
                    h_int = h_ell_0 + delta * w_tgt_tensor.view(1, 1, -1)

                    # Run second forward pass with intervention hook
                    intervened_state = h_int
                    outputs_int = model(**tok0, output_hidden_states=False)
                    intervened_state = None
                    h_final_int = outputs_int.last_hidden_state
                    pooled_int = (h_final_int * mask0.unsqueeze(-1)).sum(dim=1) / mask0.sum(dim=1, keepdim=True)

                score_before = probes_final[t_tgt].predict_proba(h_final[i0:i0+1])[0, 1]
                score_after = probes_final[t_tgt].predict_proba(pooled_int.cpu().to(torch.float32).numpy())[0, 1]
                success = bool(score_after > score_before)
                if success:
                    successes_within += 1
                if collect_raw:
                    raw_outcomes.append({
                        "effect": effect_name,
                        "mode": "within_tool",
                        "evaluation_tool": t_tgt,
                        "direction_tool": t_tgt,
                        "base_example_tool": t_tgt,
                        "source_example_tool": t_tgt,
                        "base_index": i0,
                        "source_index": i1,
                        "base_effect_label": 0,
                        "source_effect_label": 1,
                        "score_before": float(score_before),
                        "score_after": float(score_after),
                        "score_delta": float(score_after - score_before),
                        "success_score_increase": success,
                        "crosses_threshold_0_5": bool(score_before <= 0.5 < score_after),
                        "base_projection": float(proj0),
                        "source_projection": float(proj1),
                        "projection_delta": float(delta),
                        "layer": INTERVENTION_LAYER,
                        "seed": seed,
                        "pair_id": pair_id,
                    })

            iia_within = successes_within / nt if nt > 0 else 0

            # Cross-tool IIA
            ns = min(n_pairs // 4, len(groups[t_tgt][0]), len(groups[t_tgt][1]))
            successes_cross = 0
            for pair_id in range(ns):
                i0 = int(rng.choice(groups[t_tgt][0]))
                i1 = int(rng.choice(groups[t_tgt][1]))

                with torch.no_grad():
                    tok0 = tokenizer(scenarios[i0], truncation=True, max_length=256, return_tensors="pt").to(model.device)
                    outputs0 = model(**tok0, output_hidden_states=True)
                    h_ell_0 = outputs0.hidden_states[INTERVENTION_LAYER + 1]

                    tok1 = tokenizer(scenarios[i1], truncation=True, max_length=256, return_tensors="pt").to(model.device)
                    outputs1 = model(**tok1, output_hidden_states=True)
                    h_ell_1 = outputs1.hidden_states[INTERVENTION_LAYER + 1]

                    mask0 = tok0["attention_mask"]
                    mask1 = tok1["attention_mask"]
                    mean0 = (h_ell_0 * mask0.unsqueeze(-1)).sum(dim=1) / mask0.sum(dim=1, keepdim=True)
                    mean1 = (h_ell_1 * mask1.unsqueeze(-1)).sum(dim=1) / mask1.sum(dim=1, keepdim=True)

                    w_src_tensor = torch.from_numpy(w_src_hat).to(mean0.device, dtype=mean0.dtype)
                    proj0 = (mean0 @ w_src_tensor).item()
                    proj1 = (mean1 @ w_src_tensor).item()
                    delta = proj1 - proj0

                    h_int = h_ell_0 + delta * w_src_tensor.view(1, 1, -1)

                    intervened_state = h_int
                    outputs_int = model(**tok0, output_hidden_states=False)
                    intervened_state = None
                    h_final_int = outputs_int.last_hidden_state
                    pooled_int = (h_final_int * mask0.unsqueeze(-1)).sum(dim=1) / mask0.sum(dim=1, keepdim=True)

                score_before = probes_final[t_tgt].predict_proba(h_final[i0:i0+1])[0, 1]
                score_after = probes_final[t_tgt].predict_proba(pooled_int.cpu().to(torch.float32).numpy())[0, 1]
                success = bool(score_after > score_before)
                if success:
                    successes_cross += 1
                if collect_raw:
                    raw_outcomes.append({
                        "effect": effect_name,
                        "mode": "cross_tool_direction",
                        "evaluation_tool": t_tgt,
                        "direction_tool": t_src,
                        "base_example_tool": t_tgt,
                        "source_example_tool": t_tgt,
                        "base_index": i0,
                        "source_index": i1,
                        "base_effect_label": 0,
                        "source_effect_label": 1,
                        "score_before": float(score_before),
                        "score_after": float(score_after),
                        "score_delta": float(score_after - score_before),
                        "success_score_increase": success,
                        "crosses_threshold_0_5": bool(score_before <= 0.5 < score_after),
                        "base_projection": float(proj0),
                        "source_projection": float(proj1),
                        "projection_delta": float(delta),
                        "layer": INTERVENTION_LAYER,
                        "seed": seed,
                        "pair_id": pair_id,
                    })

            iia_cross = successes_cross / ns if ns > 0 else 0
            all_iia_within.append(iia_within)
            all_iia_cross.append(iia_cross)

    hook_handle.remove()

    summary = {
        "effect": effect_name,
        "n_tools": len(tool_list),
        "tools": tool_list,
        "iia_within": round(float(np.mean(all_iia_within)) if all_iia_within else 0, 4),
        "iia_cross": round(float(np.mean(all_iia_cross)) if all_iia_cross else 0, 4),
        "gap": round(float(np.mean(all_iia_cross) - np.mean(all_iia_within)) if all_iia_cross else 0, 4),
        "n_pairs": len(all_iia_cross),
        "n_raw_outcomes": len(raw_outcomes),
    }
    return summary, raw_outcomes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hook-based pIIA/interchange diagnostic.")
    parser.add_argument("--data-name", default="qwen3-8b_scenarios_merged")
    parser.add_argument("--n-pairs", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--effects", nargs="*", help="Optional subset of effect names to run.")
    parser.add_argument("--out", help="Aggregate JSON output path.")
    parser.add_argument("--raw-out", help="Raw intervention JSONL output path.")
    parser.add_argument(
        "--no-save-raw",
        action="store_true",
        help="Do not save per-intervention raw outcomes. Raw JSONL is saved by default.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    save_raw = not args.no_save_raw

    model, tokenizer, X, Y, meta, tools, texts = load_model_and_data(args.data_name)
    effect_names = meta["effect_names"]
    print(f"Loaded: {len(effect_names)} effects, {len(texts)} samples, layer {INTERVENTION_LAYER}/36")

    effect_tools = {}
    for i, effect in enumerate(effect_names):
        tool_pos = defaultdict(int)
        for j, t in enumerate(tools):
            if Y[j, i] == 1: tool_pos[t] += 1
        valid = {t: c for t, c in tool_pos.items() if c >= 5}
        if len(valid) >= 2:
            effect_tools[effect] = valid

    print(f"Testable effects: {sorted(effect_tools.keys())}")

    print(f"\n{'=' * 85}")
    print("True Interchange Intervention (hook-based, layer 24/36)")
    print(f"{'=' * 85}")

    all_results = []
    all_raw_outcomes = []
    for i, effect in enumerate(effect_names):
        if args.effects and effect not in args.effects:
            continue
        if effect not in effect_tools:
            continue
        print(f"\n  {effect} ...", flush=True)
        result = run_ii_experiment(
            model,
            tokenizer,
            texts,
            effect,
            i,
            Y,
            tools,
            n_pairs=args.n_pairs,
            seed=args.seed,
            collect_raw=save_raw,
        )
        if result is None:
            print("    insufficient data")
            continue
        r, raw_outcomes = result

        gap = r["gap"]
        if gap > -0.10: v = "✓ CAUSAL"
        elif gap > -0.25: v = "~ PARTIAL"
        elif gap > -0.50: v = "◈ PROXY"
        else: v = "✗ PURE PROXY"

        print(f"    IIA_w={r['iia_within']:.3f}  IIA_c={r['iia_cross']:.3f}  gap={gap:+.4f}  {v}")
        all_results.append(r)
        all_raw_outcomes.extend(raw_outcomes)

    causal = [r for r in all_results if r["gap"] > -0.10]
    proxy = [r for r in all_results if r["gap"] <= -0.25]
    print(f"\nTrue IIA: {len(causal)} causal, {len(proxy)} proxy  (of {len(all_results)} testable)")
    if proxy:
        for r in proxy:
            print(f"  {r['effect']}: gap={r['gap']:+.4f}")

    out = Path(args.out) if args.out else Path(__file__).resolve().parent.parent / "analysis" / f"iia_true_{args.data_name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(all_results, indent=2, ensure_ascii=False, default=str) + "\n")
    print(f"\nSaved to {out}")
    if save_raw:
        raw_out = Path(args.raw_out) if args.raw_out else Path(__file__).resolve().parent.parent / "analysis" / f"iia_true_raw_{args.data_name}.jsonl"
        raw_out.parent.mkdir(parents=True, exist_ok=True)
        with raw_out.open("w", encoding="utf-8") as f:
            for item in all_raw_outcomes:
                f.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")
        print(f"Saved raw outcomes to {raw_out} ({len(all_raw_outcomes)} rows)")


if __name__ == "__main__":
    main()
