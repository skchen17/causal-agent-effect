"""Extract embeddings from a local GGUF model via llama-cpp for trace/schema data.

Differs from extract_embeddings_llm.py: uses llama-cpp-python's create_embedding
API with mean pooling over token embeddings, rather than HuggingFace
transformers hidden states.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
from llama_cpp import Llama


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract embeddings from local GGUF model.")
    parser.add_argument("data_name", help="Name of the data file (without .jsonl)")
    parser.add_argument("--model-path", default="models/Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf")
    parser.add_argument("--n-ctx", type=int, default=8192)
    parser.add_argument("--batch-size", type=int, default=1, help="Process one text at a time")
    parser.add_argument("--output-dir", default="embeddings")
    parser.add_argument("--model-short-name", default="qwen3.5-9b-deepseek-v4")
    parser.add_argument("--model-full-name", default="Jackrong/Qwen3.5-9B-DeepSeek-V4-Flash-GGUF")
    parser.add_argument("--n-gpu-layers", type=int, default=-1, help="GPU layers (-1=all)")
    return parser.parse_args()


def load_data(base: Path, data_name: str) -> tuple[list[dict[str, Any]], np.ndarray | None]:
    """Load data rows. Support both effect-style and auth-style data formats."""
    data_file = data_name.replace("qwen3.5-9b-deepseek-v4_", "")
    data_path = base / "data" / f"{data_file}.jsonl"
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")

    rows = [json.loads(line) for line in data_path.read_text(encoding="utf-8").splitlines()]
    print(f"Loaded {len(rows)} rows from {data_path}")

    # Try loading effects if available (for non-auth data)
    effects = None
    effects_path = base / "embeddings" / f"effects_{data_name}.npy"
    if effects_path.exists():
        effects = np.load(effects_path)
        print(f"Loaded effects from {effects_path}")
    elif "scenario_text" in rows[0]:
        pass  # Will need to use verifier-based effects

    return rows, effects


def extract_embeddings(
    model: Llama,
    texts: list[str],
    dim: int = 4096,
) -> np.ndarray:
    """Extract mean-pooled embeddings for all texts."""
    embeddings = np.zeros((len(texts), dim), dtype=np.float32)

    for i, text in enumerate(texts):
        if i > 0 and i % 50 == 0:
            print(f"  {i}/{len(texts)} ...")
        output = model.create_embedding(text)
        token_embs = output["data"][0]["embedding"]
        if isinstance(token_embs[0], list):
            # Token-level embeddings -> mean pool
            embeddings[i] = np.mean(token_embs, axis=0)
        else:
            # Already pooled
            embeddings[i] = np.array(token_embs, dtype=np.float32)

    return embeddings


def build_texts(rows: list[dict[str, Any]]) -> list[str]:
    """Build the text to embed from each row. Uses scenario_text if available,
    otherwise constructs from fields like the auth trace schema builder does."""
    texts = []
    for row in rows:
        if "scenario_text" in row:
            texts.append(str(row["scenario_text"]))
        else:
            # Fallback: construct from key fields
            parts = []
            for key in ["task_context", "authorized_effects", "tool_call",
                         "candidate_effect", "candidate_effect_definition"]:
                if key in row:
                    val = row[key]
                    if isinstance(val, (list, dict)):
                        val = json.dumps(val, ensure_ascii=False)
                    parts.append(str(val))
            texts.append("\n".join(parts))
    return texts


def collect_effect_names(rows: list[dict[str, Any]]) -> list[str]:
    """Collect effect names from rows."""
    if "candidate_effect" in rows[0]:
        return sorted(set(r["candidate_effect"] for r in rows))
    if "effects" in rows[0]:
        effect_keys = set()
        for r in rows:
            effect_keys.update(r["effects"].keys())
        return sorted(effect_keys)
    return []


def collect_tools(rows: list[dict[str, Any]]) -> list[str]:
    """Collect tool names from rows."""
    tools = set()
    for r in rows:
        for key in ["tool_name", "registered_tool_name", "mapped_abstract_tool"]:
            if key in r:
                tools.add(str(r[key]))
    return sorted(tools)


def main() -> None:
    args = parse_args()
    base = Path(__file__).resolve().parent.parent.parent
    output_dir = base / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load model
    model_path = base / args.model_path
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    print(f"Loading model: {model_path}")
    t0 = time.time()
    model = Llama(
        model_path=str(model_path),
        n_ctx=args.n_ctx,
        n_gpu_layers=args.n_gpu_layers,
        embedding=True,
        verbose=False,
    )
    print(f"Model loaded in {time.time() - t0:.1f}s")

    # Load data
    rows, effects = load_data(base, args.data_name)
    texts = build_texts(rows)

    # Extract embeddings
    print(f"Extracting embeddings for {len(texts)} texts...")
    t0 = time.time()
    X = extract_embeddings(model, texts)
    elapsed = time.time() - t0
    print(f"Done in {elapsed:.1f}s ({len(texts) / elapsed:.1f} texts/s)")

    # Build effects matrix for non-auth data
    effect_names = collect_effect_names(rows)
    tools = collect_tools(rows)

    # Save outputs
    prefix = f"{args.model_short_name}_{args.data_name}"

    emb_path = output_dir / f"embeddings_{prefix}.npy"
    np.save(emb_path, X)
    print(f"Saved embeddings: {emb_path} ({X.shape})")

    # Save effects if available from original data
    if effects is not None:
        eff_path = output_dir / f"effects_{prefix}.npy"
        np.save(eff_path, effects)
        print(f"Saved effects: {eff_path}")

    # Save texts
    texts_path = output_dir / f"texts_{prefix}.jsonl"
    texts_path.write_text("\n".join(texts), encoding="utf-8")
    print(f"Saved texts: {texts_path}")

    # Save meta
    meta = {
        "model": args.model_full_name,
        "short_name": args.model_short_name,
        "dim": int(X.shape[1]),
        "n_samples": len(rows),
        "effect_names": effect_names,
        "tools": tools,
        "data_name": args.data_name,
        "embedding_method": "llama-cpp create_embedding mean-pool",
    }
    meta_path = output_dir / f"meta_{prefix}.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"Saved meta: {meta_path}")
    print(f"Effects: {effect_names}")
    print(f"Tools: {tools}")


if __name__ == "__main__":
    main()
