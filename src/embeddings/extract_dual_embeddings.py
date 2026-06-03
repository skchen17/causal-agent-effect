"""Extract separate embeddings for task and tool texts using Qwen3-8B.

Outputs:
  embeddings/emb_{data_name}_task.npy  — task embeddings
  embeddings/emb_{data_name}_tool.npy  — tool embeddings
  embeddings/emb_{data_name}_concat.npy — baseline concat embeddings
  embeddings/meta_{data_name}.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("data_name", default="dual_tower_samples")
    parser.add_argument("--model-id", default="Qwen/Qwen3-8B")
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    base = Path(__file__).resolve().parent.parent.parent

    data_path = base / "data" / f"{args.data_name}.jsonl"
    rows = [json.loads(l) for l in data_path.read_text(encoding="utf-8").splitlines()]
    print(f"Loaded {len(rows)} samples")

    task_texts = [r["task_text"] for r in rows]
    tool_texts = [r["tool_text"] for r in rows]
    concat_texts = [r["concat_text"] for r in rows]
    labels = np.array([r["label"] for r in rows], dtype=int)

    # Load model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading {args.model_id} on {device}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)
    model = AutoModel.from_pretrained(args.model_id, trust_remote_code=True, torch_dtype=torch.float16).to(device)
    model.eval()

    def embed(texts: list[str]) -> np.ndarray:
        embs = np.zeros((len(texts), model.config.hidden_size), dtype=np.float32)
        for i in range(0, len(texts), args.batch_size):
            batch = texts[i:i + args.batch_size]
            inputs = tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=128)
            inputs = {k: v.to(device) for k, v in inputs.items()}
            with torch.no_grad():
                hidden = model(**inputs).last_hidden_state
                mask = inputs["attention_mask"].unsqueeze(-1).float()
                pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
                embs[i:i + len(batch)] = pooled.cpu().numpy()
        return embs

    print("Extracting task embeddings...")
    X_task = embed(task_texts)
    print(f"  Task: {X_task.shape}")

    print("Extracting tool embeddings...")
    X_tool = embed(tool_texts)
    print(f"  Tool: {X_tool.shape}")

    print("Extracting concat (baseline) embeddings...")
    X_concat = embed(concat_texts)
    print(f"  Concat: {X_concat.shape}")

    out_dir = base / "embeddings"
    out_dir.mkdir(parents=True, exist_ok=True)

    np.save(out_dir / f"emb_{args.data_name}_task.npy", X_task)
    np.save(out_dir / f"emb_{args.data_name}_tool.npy", X_tool)
    np.save(out_dir / f"emb_{args.data_name}_concat.npy", X_concat)
    np.save(out_dir / f"emb_{args.data_name}_labels.npy", labels)

    meta = {
        "data_name": args.data_name,
        "model": args.model_id,
        "dim": int(X_task.shape[1]),
        "n_samples": len(rows),
        "n_authorized": int(labels.sum()),
        "n_unauthorized": int((1 - labels).sum()),
    }
    json.dump(meta, (out_dir / f"meta_{args.data_name}.json").open("w"), indent=2, ensure_ascii=False)

    print(f"Saved to {out_dir}/emb_{args.data_name}_*.npy")
    print(f"  Authorized: {meta['n_authorized']}, Unauthorized: {meta['n_unauthorized']}")

    del model
    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
