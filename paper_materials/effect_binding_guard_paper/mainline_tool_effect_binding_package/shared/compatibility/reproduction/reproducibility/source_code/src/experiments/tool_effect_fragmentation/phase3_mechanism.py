from __future__ import annotations

import random
import re
from pathlib import Path
from typing import Any

import numpy as np

from .mechanism import MechanismRecord, build_controlled_mechanism_records, pairwise_similarity_summary, run_mechanism_experiment


ABLATIONS = {
    "full_text": lambda record: record.text,
    "tool_name_stripped": lambda record: _strip_tokens(record.text, [record.tool_surface]),
    "arg_schema_stripped": lambda record: _strip_tokens(record.text, [record.arg_schema, "field_0", "field_1", "json", "mode_0", "mode_1"]),
    "effect_resource_stripped": lambda record: _strip_tokens(record.text, [record.realized_effect, "effect", "realized", "outcome"]),
    "plan_only": lambda record: f"{record.plan_format}: {record.text}",
    "step_only": lambda record: f"tool={record.tool_surface}; args={record.arg_schema}",
    "trajectory_only": lambda record: f"{record.plan_format} -> {record.tool_surface} -> {record.realized_effect}",
}


def run_phase3_mechanism(
    *,
    root: Path,
    bootstrap_iters: int = 500,
    run_local_encoder: bool = True,
    seed: int = 0,
) -> dict[str, Any]:
    records = build_controlled_mechanism_records()
    backends: dict[str, Any] = {}
    for ablation, text_fn in ABLATIONS.items():
        ablated = [_replace_text(record, text_fn(record)) for record in records]
        result = run_mechanism_experiment(ablated)
        result["bootstrap"] = bootstrap_gap(records=ablated, bootstrap_iters=bootstrap_iters, seed=seed)
        result["permutation_controls"] = permutation_controls(ablated, bootstrap_iters=max(50, min(bootstrap_iters, 200)), seed=seed)
        backends[f"tfidf_svd::{ablation}"] = result
    local_encoder = run_local_deberta_backend(root, records, bootstrap_iters=bootstrap_iters, seed=seed) if run_local_encoder else None
    return {
        "schema_version": "tool_effect_fragmentation_mechanism_phase3_v1",
        "n_records": len(records),
        "backends": backends,
        "local_encoder_backend": local_encoder,
        "primary_backend": "tfidf_svd::full_text",
        "claim_boundary": "Mechanism Phase 3 is diagnostic: it tests representation/text clustering under controlled records and does not prove causal understanding or deployed safety.",
    }


def bootstrap_gap(records: list[MechanismRecord], bootstrap_iters: int = 500, seed: int = 0) -> dict[str, Any]:
    rng = random.Random(seed)
    gaps = []
    effect_sims = []
    tool_sims = []
    for _ in range(bootstrap_iters):
        sampled = [records[rng.randrange(len(records))] for _ in records]
        result = run_mechanism_experiment(sampled)
        sims = result["similarities"]
        gaps.append(_none_to_zero(sims["effect_vs_tool_clustering_gap"]))
        effect_sims.append(_none_to_zero(sims["same_effect_different_tool_similarity"]["mean"]))
        tool_sims.append(_none_to_zero(sims["same_tool_different_effect_similarity"]["mean"]))
    return {
        "effect_vs_tool_gap_ci": _ci(gaps),
        "same_effect_similarity_ci": _ci(effect_sims),
        "same_tool_similarity_ci": _ci(tool_sims),
        "bootstrap_iters": bootstrap_iters,
    }


def permutation_controls(records: list[MechanismRecord], bootstrap_iters: int = 200, seed: int = 0) -> dict[str, Any]:
    rng = random.Random(seed)
    effect_shuffle_gaps = []
    tool_shuffle_gaps = []
    for _ in range(bootstrap_iters):
        effect_labels = [record.realized_effect for record in records]
        tool_labels = [record.tool_surface for record in records]
        rng.shuffle(effect_labels)
        rng.shuffle(tool_labels)
        effect_shuffled = [
            MechanismRecord(
                record_id=record.record_id,
                semantic_group_id=effect_labels[idx],
                realized_effect=effect_labels[idx],
                tool_surface=record.tool_surface,
                arg_schema=record.arg_schema,
                plan_format=record.plan_format,
                perturbation_family=record.perturbation_family,
                text=record.text,
            )
            for idx, record in enumerate(records)
        ]
        tool_shuffled = [
            MechanismRecord(
                record_id=record.record_id,
                semantic_group_id=record.semantic_group_id,
                realized_effect=record.realized_effect,
                tool_surface=tool_labels[idx],
                arg_schema=record.arg_schema,
                plan_format=record.plan_format,
                perturbation_family=record.perturbation_family,
                text=record.text,
            )
            for idx, record in enumerate(records)
        ]
        effect_shuffle_gaps.append(_none_to_zero(run_mechanism_experiment(effect_shuffled)["similarities"]["effect_vs_tool_clustering_gap"]))
        tool_shuffle_gaps.append(_none_to_zero(run_mechanism_experiment(tool_shuffled)["similarities"]["effect_vs_tool_clustering_gap"]))
    observed = _none_to_zero(run_mechanism_experiment(records)["similarities"]["effect_vs_tool_clustering_gap"])
    return {
        "observed_gap": observed,
        "effect_label_shuffle_gap": {"mean": float(np.mean(effect_shuffle_gaps)), "ci": _ci(effect_shuffle_gaps)},
        "tool_label_shuffle_gap": {"mean": float(np.mean(tool_shuffle_gaps)), "ci": _ci(tool_shuffle_gaps)},
        "iters": bootstrap_iters,
    }


def run_local_deberta_backend(root: Path, records: list[MechanismRecord], bootstrap_iters: int, seed: int) -> dict[str, Any] | None:
    model_path = root / "models/protectai_deberta-v3-base-prompt-injection-v2"
    if not model_path.exists():
        return {"status": "skipped", "reason": f"local_encoder_missing:{model_path}"}
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
    except Exception as exc:
        return {"status": "skipped", "reason": f"transformers_or_torch_unavailable:{exc}"}
    try:
        tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
        model = AutoModel.from_pretrained(str(model_path), local_files_only=True)
        model.eval()
        texts = [record.text for record in records]
        vectors = []
        with torch.no_grad():
            for text in texts:
                batch = tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
                output = model(**batch)
                mask = batch["attention_mask"].unsqueeze(-1)
                pooled = (output.last_hidden_state * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
                vectors.append(pooled.squeeze(0).cpu().numpy())
        embeddings = np.asarray(vectors)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / np.clip(norms, 1e-8, None)
        sims = pairwise_similarity_summary(records, embeddings)
        return {
            "status": "ok",
            "backend": str(model_path),
            "similarities": sims,
            "bootstrap_note": "Local encoder bootstrap is omitted to keep Phase 3 runtime bounded; tfidf_svd backend carries bootstrap/permutation controls.",
        }
    except Exception as exc:
        return {"status": "failed", "reason": str(exc), "backend": str(model_path)}


def mechanism_phase3_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Tool-Effect Fragmentation Mechanism Phase 3",
        "",
        f"- Primary backend: `{result['primary_backend']}`",
        f"- Records: `{result['n_records']}`",
        "",
        "## Ablation Results",
        "",
        "| Backend/Ablation | Gap | Gap CI | Same-effect diff-tool | Same-tool diff-effect |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, payload in result["backends"].items():
        sims = payload["similarities"]
        boot = payload["bootstrap"]
        lines.append(
            "| `{}` | {} | {} | {} | {} |".format(
                name,
                _fmt(sims["effect_vs_tool_clustering_gap"]),
                _fmt_ci(boot["effect_vs_tool_gap_ci"]),
                _fmt(sims["same_effect_different_tool_similarity"]["mean"]),
                _fmt(sims["same_tool_different_effect_similarity"]["mean"]),
            )
        )
    lines.extend(["", "## Local Encoder", "", f"- `{result['local_encoder_backend']}`", "", "## Claim Boundary", "", f"- {result['claim_boundary']}"])
    return "\n".join(lines) + "\n"


def _replace_text(record: MechanismRecord, text: str) -> MechanismRecord:
    return MechanismRecord(
        record_id=record.record_id,
        semantic_group_id=record.semantic_group_id,
        realized_effect=record.realized_effect,
        tool_surface=record.tool_surface,
        arg_schema=record.arg_schema,
        plan_format=record.plan_format,
        perturbation_family=record.perturbation_family,
        text=text,
    )


def _strip_tokens(text: str, tokens: list[str]) -> str:
    out = text
    for token in tokens:
        if token:
            out = re.sub(re.escape(token), "[STRIPPED]", out, flags=re.IGNORECASE)
    return out


def _ci(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"low": None, "high": None}
    ordered = sorted(values)
    return {"low": ordered[int(0.025 * (len(ordered) - 1))], "high": ordered[int(0.975 * (len(ordered) - 1))]}


def _none_to_zero(value: float | None) -> float:
    return 0.0 if value is None else float(value)


def _fmt(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _fmt_ci(ci: dict[str, Any]) -> str:
    if ci.get("low") is None:
        return "NA"
    return f"[{ci['low']:.4f}, {ci['high']:.4f}]"

