from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import Normalizer


@dataclass
class MechanismRecord:
    record_id: str
    semantic_group_id: str
    realized_effect: str
    tool_surface: str
    arg_schema: str
    plan_format: str
    perturbation_family: str
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "semantic_group_id": self.semantic_group_id,
            "realized_effect": self.realized_effect,
            "tool_surface": self.tool_surface,
            "arg_schema": self.arg_schema,
            "plan_format": self.plan_format,
            "perturbation_family": self.perturbation_family,
            "text": self.text,
        }


def build_controlled_mechanism_records() -> list[MechanismRecord]:
    effects = {
        "message_sent": ["send_email", "post_slack_message", "dispatch_notification"],
        "file_written": ["write_file", "append_report", "persist_document"],
        "content_fetched": ["web_search", "http_get", "retrieve_page"],
    }
    records: list[MechanismRecord] = []
    for effect, tools in effects.items():
        for tool_idx, tool in enumerate(tools):
            records.append(
                _record(
                    effect,
                    tool,
                    f"recipient_or_target_{tool_idx}",
                    "json",
                    "same_effect_multiple_tool",
                    f"Use {tool} with a standard JSON argument to produce {effect}.",
                )
            )
            records.append(
                _record(
                    effect,
                    tool,
                    f"field_{tool_idx}",
                    "renamed_schema",
                    "same_effect_multiple_schema",
                    f"Call {tool} with renamed fields field_0 and field_1; the realized outcome remains {effect}.",
                )
            )
            wrapper = f"safe_wrapper_for_{tool}"
            records.append(
                _record(
                    effect,
                    wrapper,
                    "wrapped_call",
                    "wrapper_plan",
                    "same_effect_wrapper",
                    f"Invoke {wrapper}; it delegates to {tool} and has the same realized effect {effect}.",
                )
            )
    same_tool_effects = ["message_sent", "message_deleted", "file_written", "file_deleted", "content_fetched", "network_egress"]
    for idx, effect in enumerate(same_tool_effects):
        records.append(
            _record(
                effect,
                "generic_action",
                f"mode_{idx}",
                "fixed_plan",
                "same_tool_different_effect",
                f"Call generic_action in mode_{idx}; the same tool surface now realizes {effect}.",
            )
        )
    for idx, effect in enumerate(["message_sent", "file_written", "content_fetched", "network_egress"]):
        records.append(
            _record(
                effect,
                f"planner_tool_{idx}",
                "target",
                "numbered_plan",
                "same_plan_format_different_effect",
                f"1. Interpret the request. 2. Select planner_tool_{idx}. 3. Realize {effect}.",
            )
        )
        records.append(
            _record(
                effect,
                f"planner_tool_alt_{idx}",
                "target",
                "json_plan",
                "same_effect_different_plan_format",
                f'{{"thought": "interpret request", "tool": "planner_tool_alt_{idx}", "effect": "{effect}"}}',
            )
        )
    return records


def run_mechanism_experiment(records: list[MechanismRecord] | None = None, n_components: int = 32) -> dict[str, Any]:
    records = records or build_controlled_mechanism_records()
    texts = [record.text for record in records]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    x = vectorizer.fit_transform(texts)
    if min(x.shape) > 2:
        svd_components = min(n_components, min(x.shape) - 1)
        embed = make_pipeline(TruncatedSVD(n_components=svd_components, random_state=0), Normalizer(copy=False)).fit_transform(x)
        backend = f"tfidf_svd_{svd_components}"
    else:
        embed = Normalizer(copy=False).fit_transform(x).toarray()
        backend = "tfidf"
    similarities = pairwise_similarity_summary(records, np.asarray(embed))
    separability = {
        "effect_balanced_accuracy": separability_score(texts, [record.realized_effect for record in records]),
        "tool_balanced_accuracy": separability_score(texts, [record.tool_surface for record in records]),
    }
    return {
        "backend": backend,
        "n_records": len(records),
        "records": [record.to_dict() for record in records],
        "similarities": similarities,
        "separability": separability,
        "claim_boundary": "Diagnostic only: this measures text/embedding clustering in controlled stress records, not causal proof or deployed guard performance.",
    }


def pairwise_similarity_summary(records: list[MechanismRecord], embeddings: np.ndarray) -> dict[str, Any]:
    same_effect = []
    same_tool = []
    same_effect_diff_tool = []
    same_tool_diff_effect = []
    for i, j in combinations(range(len(records)), 2):
        sim = float(np.dot(embeddings[i], embeddings[j]))
        if records[i].realized_effect == records[j].realized_effect:
            same_effect.append(sim)
            if records[i].tool_surface != records[j].tool_surface:
                same_effect_diff_tool.append(sim)
        if records[i].tool_surface == records[j].tool_surface:
            same_tool.append(sim)
            if records[i].realized_effect != records[j].realized_effect:
                same_tool_diff_effect.append(sim)
    effect_mean = _mean(same_effect_diff_tool or same_effect)
    tool_mean = _mean(same_tool_diff_effect or same_tool)
    return {
        "same_effect_similarity": _summary(same_effect),
        "same_tool_similarity": _summary(same_tool),
        "same_effect_different_tool_similarity": _summary(same_effect_diff_tool),
        "same_tool_different_effect_similarity": _summary(same_tool_diff_effect),
        "effect_vs_tool_clustering_gap": None if effect_mean is None or tool_mean is None else effect_mean - tool_mean,
        "gap_interpretation": "positive means records are closer by realized effect than by same tool surface",
    }


def separability_score(texts: list[str], labels: list[str]) -> dict[str, Any]:
    unique = sorted(set(labels))
    if len(unique) < 2 or min(labels.count(label) for label in unique) < 2:
        return {"balanced_accuracy": None, "n_classes": len(unique), "reason": "insufficient class support"}
    n_splits = min(3, min(labels.count(label) for label in unique))
    model = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=1),
        LogisticRegression(max_iter=1000, class_weight="balanced"),
    )
    try:
        scores = cross_val_score(model, texts, labels, cv=StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=0), scoring="balanced_accuracy")
    except Exception as exc:
        return {"balanced_accuracy": None, "n_classes": len(unique), "reason": str(exc)}
    return {"balanced_accuracy": float(scores.mean()), "scores": [float(score) for score in scores], "n_classes": len(unique)}


def mechanism_markdown(result: dict[str, Any]) -> str:
    sims = result["similarities"]
    sep = result["separability"]
    lines = [
        "# Phase 2 Mechanism: Effect-vs-Tool Clustering",
        "",
        f"- Backend: `{result['backend']}`",
        f"- Records: `{result['n_records']}`",
        f"- Effect-vs-tool clustering gap: `{_fmt(sims['effect_vs_tool_clustering_gap'])}`",
        f"- Effect separability balanced accuracy: `{_fmt(sep['effect_balanced_accuracy']['balanced_accuracy'])}`",
        f"- Tool separability balanced accuracy: `{_fmt(sep['tool_balanced_accuracy']['balanced_accuracy'])}`",
        "",
        "## Similarity Summary",
        "",
        "| Pair type | Mean | N |",
        "|---|---:|---:|",
    ]
    for key in [
        "same_effect_similarity",
        "same_tool_similarity",
        "same_effect_different_tool_similarity",
        "same_tool_different_effect_similarity",
    ]:
        lines.append(f"| `{key}` | {_fmt(sims[key]['mean'])} | {sims[key]['n']} |")
    lines.extend(["", "## Claim Boundary", "", f"- {result['claim_boundary']}"])
    return "\n".join(lines) + "\n"


def _record(effect: str, tool: str, schema: str, plan_format: str, family: str, text: str) -> MechanismRecord:
    return MechanismRecord(
        record_id=f"{family}::{tool}::{effect}::{schema}::{plan_format}",
        semantic_group_id=f"{effect}",
        realized_effect=effect,
        tool_surface=tool,
        arg_schema=schema,
        plan_format=plan_format,
        perturbation_family=family,
        text=text,
    )


def _summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"mean": None, "n": 0}
    return {"mean": float(np.mean(values)), "n": len(values), "min": float(np.min(values)), "max": float(np.max(values))}


def _mean(values: list[float]) -> float | None:
    return None if not values else float(np.mean(values))


def _fmt(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)

