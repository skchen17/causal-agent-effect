"""
Extract embeddings from Qwen2.5-7B-Instruct.

Loads model on GPU (bfloat16, ~14GB), runs forward passes, and saves
mean-pooled last hidden state (~3584d) for each scenario text.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer


def load_scenarios(data_path: str) -> list[dict]:
    scenarios = []
    with open(data_path, encoding="utf-8") as f:
        for line in f:
            scenarios.append(json.loads(line))
    return scenarios


def extract_qwen_embeddings(
    scenarios: list[dict],
    model_name: str = "Qwen/Qwen2.5-7B-Instruct",
    batch_size: int = 8,
    max_length: int = 256,
) -> np.ndarray:
    """Extract mean-pooled last hidden state from Qwen2.5-7B."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading {model_name} on {device}...")

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    # Set pad_token if not present
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModel.from_pretrained(
        model_name,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()

    texts = [s["scenario_text"] for s in scenarios]
    dim = model.config.hidden_size
    print(f"  Model dim: {dim}, Samples: {len(texts)}, Batch: {batch_size}")

    all_embeddings = np.zeros((len(texts), dim), dtype=np.float32)

    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        inputs = tokenizer(
            batch_texts,
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        ).to(device)

        with torch.no_grad():
            outputs = model(**inputs)
            # Mean pool over token dimension (excluding padding)
            hidden = outputs.last_hidden_state  # (batch, seq, dim)
            attention_mask = inputs["attention_mask"].unsqueeze(-1)  # (batch, seq, 1)
            pooled = (hidden * attention_mask).sum(dim=1) / attention_mask.sum(dim=1)
            all_embeddings[i : i + batch_size] = pooled.cpu().to(torch.float32).numpy()

        if (i // batch_size) % 10 == 0:
            print(f"  Processed {min(i + batch_size, len(texts))}/{len(texts)}")

    return all_embeddings


def main() -> None:
    import sys

    data_file = sys.argv[1] if len(sys.argv) > 1 else "scenarios_merged.jsonl"
    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_path = data_dir / data_file
    if not data_path.exists():
        print(f"Data not found at {data_path}")
        return

    data_name = data_file.replace(".jsonl", "")
    scenarios = load_scenarios(str(data_path))
    print(f"Loaded {len(scenarios)} scenarios ({data_name})")

    embeddings = extract_qwen_embeddings(scenarios)
    print(f"Embeddings shape: {embeddings.shape}")

    # Save
    effects = np.array([
        [s["effects"][e] for e in sorted(s["effects"].keys())]
        for s in scenarios
    ], dtype=np.int32)

    out_dir = Path(__file__).resolve().parent.parent / "embeddings"
    out_dir.mkdir(parents=True, exist_ok=True)

    emb_name = f"embeddings_qwen_{data_name}"
    np.save(out_dir / f"{emb_name}.npy", embeddings.astype(np.float32))
    np.save(out_dir / f"effects_qwen_{data_name}.npy", effects)

    meta = {
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "dim": int(embeddings.shape[1]),
        "n_samples": len(scenarios),
        "effect_names": sorted(scenarios[0]["effects"].keys()),
        "tools": sorted(set(s["tool_name"] for s in scenarios)),
        "data_name": data_name,
    }
    with open(out_dir / f"meta_qwen_{data_name}.json", "w") as f:
        json.dump(meta, f, indent=2)

    with open(out_dir / f"texts_qwen_{data_name}.jsonl", "w", encoding="utf-8") as f:
        for s in scenarios:
            f.write(json.dumps({
                "tool_name": s["tool_name"],
                "text": s["scenario_text"],
                "effects": s["effects"],
            }, ensure_ascii=False) + "\n")

    print(f"\nSaved to {out_dir}/{emb_name}.*")
    print(f"  dim={embeddings.shape[1]}, samples={len(scenarios)}")


if __name__ == "__main__":
    main()
