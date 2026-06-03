"""Extract Qwen3-8B embeddings for auth trace/schema conditioned data.

This is a specialized version of extract_embeddings_llm.py that handles the
auth data format (candidate-effect rows with scenario_text).
"""

import json
import numpy as np
import torch
from pathlib import Path
from transformers import AutoModel, AutoTokenizer


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("data_name", help="Full data name e.g. qwen3-8b_auth_trace_effect_schema_conditioned_local_agent_v1")
    parser.add_argument("--model-id", default="Qwen/Qwen3-8B")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=256)
    args = parser.parse_args()

    base = Path(__file__).resolve().parent.parent.parent

    # Load data
    data_file = args.data_name.replace("qwen3-8b_", "")
    data_path = base / "data" / f"{data_file}.jsonl"
    rows = [json.loads(l) for l in data_path.read_text(encoding="utf-8").splitlines()]
    print(f"Loaded {len(rows)} rows from {data_path}")

    texts = [r["scenario_text"] for r in rows]

    # Load model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading {args.model_id} on {device}...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)
    model = AutoModel.from_pretrained(args.model_id, trust_remote_code=True, torch_dtype=torch.float16)
    model = model.to(device)
    model.eval()

    # Extract embeddings in batches
    embeddings = np.zeros((len(texts), model.config.hidden_size), dtype=np.float32)
    for i in range(0, len(texts), args.batch_size):
        batch = texts[i:i + args.batch_size]
        inputs = tokenizer(batch, return_tensors="pt", padding=True,
                          truncation=True, max_length=args.max_length)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
            # Mean pool the last hidden state (excluding padding)
            hidden = outputs.last_hidden_state  # [B, L, D]
            mask = inputs["attention_mask"].unsqueeze(-1).float()  # [B, L, 1]
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)  # [B, D]
            embeddings[i:i + len(batch)] = pooled.cpu().numpy()

        if (i // args.batch_size) % 10 == 0:
            print(f"  {i}/{len(texts)}")

    # Save
    out_dir = base / "embeddings"
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = args.data_name

    emb_path = out_dir / f"embeddings_{prefix}.npy"
    np.save(emb_path, embeddings.astype(np.float32))
    print(f"Saved: {emb_path} ({embeddings.shape})")

    # Collect meta
    tools = sorted(set(r.get("tool_name", r.get("registered_tool_name", "unknown")) for r in rows))
    effect_names = ["candidate_unauthorized_effect"]

    meta = {
        "model": args.model_id,
        "short_name": "qwen3-8b",
        "dim": int(embeddings.shape[1]),
        "n_samples": len(rows),
        "effect_names": effect_names,
        "tools": tools,
        "data_name": args.data_name,
        "use_4bit": False,
    }
    meta_path = out_dir / f"meta_{prefix}.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"Saved: {meta_path}")

    # Clean up
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
