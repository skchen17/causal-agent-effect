"""
Phase 2: 从 LLM 提取嵌入。

支持:
  - 本地 transformers 模型 (如 BERT, Llama)
  - sentence-transformers (轻量)
  - OpenAI API (可选)

对每个场景文本，提取:
  - 最后一层隐藏状态的均值池化
  - (可选) 中间层隐藏状态
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def load_scenarios(data_path: str) -> list[dict]:
    """加载生成的数据。"""
    scenarios = []
    with open(data_path, encoding="utf-8") as f:
        for line in f:
            scenarios.append(json.loads(line))
    return scenarios


def extract_with_sentence_transformers(
    scenarios: list[dict],
    model_name: str = "all-MiniLM-L6-v2",
    batch_size: int = 64,
) -> np.ndarray:
    """
    使用 sentence-transformers 提取嵌入。

    all-MiniLM-L6-v2: 384 维, 轻量, 适合初步实验
    all-mpnet-base-v2: 768 维, 更好的质量
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise ImportError("pip install sentence-transformers")

    model = SentenceTransformer(model_name)
    texts = [s["scenario_text"] for s in scenarios]

    print(f"Extracting embeddings using {model_name}...")
    print(f"  Samples: {len(texts)}")
    print(f"  Batch size: {batch_size}")

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    return embeddings


def extract_with_transformers(
    scenarios: list[dict],
    model_name: str = "bert-base-uncased",
    batch_size: int = 32,
) -> dict[str, np.ndarray]:
    """
    使用 HuggingFace transformers 提取多层嵌入。

    返回 dict: {layer_name: embeddings_array}
    """
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
    except ImportError:
        raise ImportError("pip install torch transformers")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(
        model_name, output_hidden_states=True
    ).to(device)
    model.eval()

    texts = [s["scenario_text"] for s in scenarios]
    all_hidden = {f"layer_{i}": [] for i in range(model.config.num_hidden_layers + 1)}

    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        inputs = tokenizer(
            batch_texts,
            padding=True,
            truncation=True,
            max_length=128,
            return_tensors="pt",
        ).to(device)

        with torch.no_grad():
            outputs = model(**inputs)

        # 对每层做均值池化
        for layer_idx, hidden in enumerate(outputs.hidden_states):
            # hidden: (batch, seq_len, dim) → (batch, dim)
            pooled = hidden.mean(dim=1).cpu().numpy()
            all_hidden[f"layer_{layer_idx}"].append(pooled)

        if (i // batch_size) % 20 == 0:
            print(f"  Processed {min(i + batch_size, len(texts))}/{len(texts)}")

    # 拼接所有 batch
    for key in all_hidden:
        all_hidden[key] = np.concatenate(all_hidden[key], axis=0)

    return all_hidden


def main() -> None:
    import sys

    # Accept data file name from command line, default to counterfactual
    if len(sys.argv) > 1:
        data_file = sys.argv[1]
    else:
        data_file = "scenarios_counterfactual.jsonl"

    data_path = Path(__file__).resolve().parent.parent / "data" / data_file
    if not data_path.exists():
        # Fall back to template data
        data_path = Path(__file__).resolve().parent.parent / "data" / "scenarios_template.jsonl"
        data_file = "scenarios_template.jsonl"
        if not data_path.exists():
            print(f"Data not found. Run generate_data.py or generate_counterfactual_data.py first.")
            return

    data_name = data_file.replace(".jsonl", "")
    scenarios = load_scenarios(str(data_path))
    print(f"Loaded {len(scenarios)} scenarios ({data_name})")

    # 选择模型: 优先用轻量的
    model_name = "all-MiniLM-L6-v2"
    try:
        embeddings = extract_with_sentence_transformers(
            scenarios, model_name=model_name
        )
    except ImportError:
        print("sentence-transformers not available, trying transformers...")
        embeddings_dict = extract_with_transformers(scenarios)
        # 使用最后一层
        last_layer = max(k for k in embeddings_dict)
        embeddings = embeddings_dict[last_layer]
        model_name = "bert-base-uncased (last layer)"

    print(f"Embeddings shape: {embeddings.shape}")

    # 保存嵌入和效果标签
    effects = np.array([
        [s["effects"][e] for e in sorted(s["effects"].keys())]
        for s in scenarios
    ], dtype=np.int32)

    out_path = Path(__file__).resolve().parent.parent / "embeddings"
    out_path.mkdir(parents=True, exist_ok=True)

    # Use data_name suffix so template and counterfactual embeddings coexist
    np.save(out_path / f"embeddings_{data_name}.npy", embeddings.astype(np.float32))
    np.save(out_path / f"effects_{data_name}.npy", effects)

    # 保存元数据
    meta = {
        "model": model_name,
        "dim": int(embeddings.shape[1]),
        "n_samples": len(scenarios),
        "effect_names": sorted(scenarios[0]["effects"].keys()),
        "tools": sorted(set(s["tool_name"] for s in scenarios)),
        "data_name": data_name,
    }
    with open(out_path / f"meta_{data_name}.json", "w") as f:
        json.dump(meta, f, indent=2)

    # 保存文本（供后续分析）
    with open(out_path / f"texts_{data_name}.jsonl", "w", encoding="utf-8") as f:
        for s in scenarios:
            f.write(json.dumps({
                "tool_name": s["tool_name"],
                "text": s["scenario_text"],
                "effects": s["effects"],
            }, ensure_ascii=False) + "\n")

    print(f"\nSaved to {out_path}:")
    print(f"  embeddings_{data_name}.npy  — {embeddings.shape}")
    print(f"  effects_{data_name}.npy     — {effects.shape}")
    print(f"  meta_{data_name}.json       — model: {model_name}")
    print(f"  texts_{data_name}.jsonl     — {len(scenarios)} texts")


if __name__ == "__main__":
    main()
