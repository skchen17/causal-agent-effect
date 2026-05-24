"""
Generic LLM embedding extraction supporting multiple models and 4-bit quantization.

Usage:
  python extract_embeddings_llm.py <model_id> <data_file> [--4bit]
Examples:
  python extract_embeddings_llm.py Qwen/Qwen3-8B scenarios_merged.jsonl
  python extract_embeddings_llm.py google/gemma-4-26b-a4b scenarios_merged.jsonl --4bit
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer, BitsAndBytesConfig


def load_scenarios(data_path: str) -> list[dict]:
    with open(data_path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def extract_embeddings(
    scenarios: list[dict],
    model_id: str,
    use_4bit: bool = False,
    batch_size: int = 8,
    max_length: int = 256,
) -> np.ndarray:
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Set max_memory for dual GPU
    max_memory = {}
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            free = torch.cuda.get_device_properties(i).total_memory
            max_memory[i] = f"{int(free // (1024**3) * 0.9)}GiB"  # 90% of VRAM
        # Add CPU offload with generous RAM
        import psutil
        cpu_ram = psutil.virtual_memory().available // (1024**3)
        max_memory["cpu"] = f"{min(cpu_ram - 10, 64)}GiB"

    if use_4bit:
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
            llm_int8_enable_fp32_cpu_offload=True,
        )
        print(f"Loading {model_id} (4-bit quantized, max_memory={max_memory})...")
        model = AutoModel.from_pretrained(
            model_id,
            quantization_config=quant_config,
            device_map="auto",
            max_memory=max_memory,
            trust_remote_code=True,
        )
    else:
        print(f"Loading {model_id} on cuda (bfloat16)...")
        model = AutoModel.from_pretrained(
            model_id,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            max_memory=max_memory,
            trust_remote_code=True,
        )
    model.eval()

    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    texts = [s["scenario_text"] for s in scenarios]
    # Handle models with nested config (e.g., Gemma4 with text_config)
    config = model.config
    if hasattr(config, 'hidden_size'):
        dim = config.hidden_size
    elif hasattr(config, 'text_config') and hasattr(config.text_config, 'hidden_size'):
        dim = config.text_config.hidden_size
    else:
        raise ValueError(f"Cannot find hidden_size in config: {type(config)}")
    print(f"  Dim: {dim}, Samples: {len(texts)}, Batch: {batch_size}")
    mem_mb = torch.cuda.memory_allocated(0) / 1024**2 if torch.cuda.is_available() else 0
    print(f"  GPU memory used after load: {mem_mb:.0f} MB")

    all_embeddings = np.zeros((len(texts), dim), dtype=np.float32)

    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        inputs = tokenizer(
            batch_texts, padding=True, truncation=True,
            max_length=max_length, return_tensors="pt",
        ).to(device)

        with torch.no_grad():
            hidden = model(**inputs).last_hidden_state
            mask = inputs["attention_mask"].unsqueeze(-1)
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1)
            all_embeddings[i : i + batch_size] = pooled.cpu().to(torch.float32).numpy()

        if (i // batch_size) % 10 == 0:
            print(f"  {min(i + batch_size, len(texts))}/{len(texts)}")

    return all_embeddings


def model_short_name(model_id: str) -> str:
    """Qwen/Qwen3-8B → qwen3-8b, google/gemma-4-26b-a4b → gemma4-26b-a4b"""
    name = model_id.split("/")[-1].lower()
    name = re.sub(r'[^a-z0-9-]', '-', name)
    return name


def main() -> None:
    import sys, argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("model_id", help="HuggingFace model ID")
    parser.add_argument("data_file", nargs="?", default="scenarios_merged.jsonl",
                        help="Data JSONL file in data/ directory")
    parser.add_argument("--4bit", action="store_true", dest="use_4bit",
                        help="Use 4-bit quantization")
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_path = data_dir / args.data_file
    if not data_path.exists():
        print(f"Data not found: {data_path}")
        return

    data_name = args.data_file.replace(".jsonl", "")
    short_name = model_short_name(args.model_id)
    scenarios = load_scenarios(str(data_path))
    print(f"Loaded {len(scenarios)} scenarios ({data_name})")

    embeddings = extract_embeddings(
        scenarios, args.model_id,
        use_4bit=args.use_4bit, batch_size=args.batch_size,
    )
    print(f"Embeddings shape: {embeddings.shape}")

    effects = np.array([
        [s["effects"][e] for e in sorted(s["effects"].keys())]
        for s in scenarios
    ], dtype=np.int32)

    out_dir = Path(__file__).resolve().parent.parent / "embeddings"
    out_dir.mkdir(parents=True, exist_ok=True)

    emb_name = f"embeddings_{short_name}_{data_name}"
    np.save(out_dir / f"{emb_name}.npy", embeddings.astype(np.float32))
    np.save(out_dir / f"effects_{short_name}_{data_name}.npy", effects)

    meta = {
        "model": args.model_id,
        "short_name": short_name,
        "dim": int(embeddings.shape[1]),
        "n_samples": len(scenarios),
        "effect_names": sorted(scenarios[0]["effects"].keys()),
        "tools": sorted(set(s["tool_name"] for s in scenarios)),
        "data_name": data_name,
        "use_4bit": args.use_4bit,
    }
    with open(out_dir / f"meta_{short_name}_{data_name}.json", "w") as f:
        json.dump(meta, f, indent=2)

    with open(out_dir / f"texts_{short_name}_{data_name}.jsonl", "w", encoding="utf-8") as f:
        for s in scenarios:
            f.write(json.dumps({
                "tool_name": s["tool_name"],
                "text": s["scenario_text"],
                "effects": s["effects"],
            }, ensure_ascii=False) + "\n")

    print(f"\nSaved → {out_dir}/{emb_name}.*")
    print(f"  dim={embeddings.shape[1]}, samples={len(scenarios)}")

    # clean up GPU
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
