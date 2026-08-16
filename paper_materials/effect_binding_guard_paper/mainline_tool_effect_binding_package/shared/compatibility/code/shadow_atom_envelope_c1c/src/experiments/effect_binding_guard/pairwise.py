from __future__ import annotations

import random
from collections import Counter, defaultdict
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

from src.experiments.tool_effect_fragmentation.metrics import wilson

from .dataset import row_input_text
from .schema import EffectBindingRow


def pair_text(pair: dict[str, Any]) -> str:
    return f"LEFT\\n{pair['left_input_text']}\\nPAIR\\nRIGHT\\n{pair['right_input_text']}"


def build_classifier() -> Any:
    return LogisticRegression(max_iter=2000, class_weight="balanced", random_state=0)


def run_pairwise_diagnostic(rows: list[EffectBindingRow], pairs: list[dict[str, Any]]) -> dict[str, Any]:
    row_by_id = {row.case_id: row for row in rows}
    groups = np.asarray([pair["split_group_id"] for pair in pairs])
    labels = np.asarray([pair["relation_label"] for pair in pairs])
    predictions = {"pairwise_relation_learner": [], "independent_x_to_y_relation": []}
    fold_records = []
    splitter = GroupKFold(n_splits=5)
    dummy = np.zeros(len(pairs))
    for fold, (train_index, test_index) in enumerate(splitter.split(dummy, labels, groups)):
        train_groups = set(groups[train_index])
        test_groups = set(groups[test_index])
        train_rows = [row for row in rows if row.split_group_id in train_groups]
        test_rows = [row for row in rows if row.split_group_id in test_groups]
        train_texts = [row_input_text(row) for row in train_rows]
        test_texts = [row_input_text(row) for row in test_rows]
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=12000)
        train_matrix = vectorizer.fit_transform(train_texts)
        test_matrix = vectorizer.transform(test_texts)
        n_components = max(2, min(64, train_matrix.shape[0] - 1, train_matrix.shape[1] - 1))
        svd = TruncatedSVD(n_components=n_components, random_state=fold)
        train_embed = svd.fit_transform(train_matrix)
        test_embed = svd.transform(test_matrix)
        scaler = StandardScaler()
        train_embed = scaler.fit_transform(train_embed)
        test_embed = scaler.transform(test_embed)
        row_model = build_classifier()
        row_model.fit(train_embed, [row.labels["expected_decision"] for row in train_rows])
        train_probs = row_model.predict_proba(train_embed)
        test_probs = row_model.predict_proba(test_embed)
        embed_by_case = {
            **{row.case_id: train_embed[index] for index, row in enumerate(train_rows)},
            **{row.case_id: test_embed[index] for index, row in enumerate(test_rows)},
        }
        prob_by_case = {
            **{row.case_id: train_probs[index] for index, row in enumerate(train_rows)},
            **{row.case_id: test_probs[index] for index, row in enumerate(test_rows)},
        }
        relation_model = build_classifier()
        relation_model.fit(
            pair_feature_matrix([pairs[index] for index in train_index], embed_by_case, prob_by_case),
            labels[train_index],
        )
        pair_pred = relation_model.predict(
            pair_feature_matrix([pairs[index] for index in test_index], embed_by_case, prob_by_case)
        )
        row_pred = {
            row.case_id: decision
            for row, decision in zip(test_rows, row_model.predict(test_embed))
        }
        for offset, index in enumerate(test_index):
            pair = pairs[index]
            predictions["pairwise_relation_learner"].append(
                prediction_record(pair, str(pair_pred[offset]), fold)
            )
            left = row_pred[pair["left_case_id"]]
            right = row_pred[pair["right_case_id"]]
            relation = "should_same_decision" if left == right else "should_flip_decision"
            predictions["independent_x_to_y_relation"].append(prediction_record(pair, relation, fold))
        fold_records.append(
            {
                "fold": fold,
                "train_groups": sorted(train_groups),
                "test_groups": sorted(test_groups),
                "group_overlap": sorted(train_groups & test_groups),
            }
        )
    camel_holdout = source_holdout(rows, pairs, "camel")
    return {
        "schema_version": "e48_pairwise_v1",
        "n_rows": len(rows),
        "n_pairs": len(pairs),
        "folds": fold_records,
        "methods": {method: summarize_relation_predictions(items) for method, items in predictions.items()},
        "paired_delta_pairwise_vs_independent": paired_relation_delta(
            predictions["pairwise_relation_learner"],
            predictions["independent_x_to_y_relation"],
        ),
        "camel_source_held_out": camel_holdout,
        "predictions": predictions,
        "claim_boundary": "Pairwise relation learning is a counterfactual diagnostic and not a single-case deployable guard.",
    }


def paired_relation_delta(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
    *,
    bootstrap_iters: int = 2000,
    seed: int = 0,
) -> dict[str, Any]:
    left_by_id = {row["pair_id"]: row for row in left}
    right_by_id = {row["pair_id"]: row for row in right}
    group_values: dict[str, list[float]] = defaultdict(list)
    for pair_id in sorted(set(left_by_id) & set(right_by_id)):
        left_row = left_by_id[pair_id]
        right_row = right_by_id[pair_id]
        if left_row["split_group_id"] != right_row["split_group_id"]:
            raise ValueError(f"Pair group mismatch for {pair_id}")
        left_correct = left_row["predicted_relation"] == left_row["gold_relation"]
        right_correct = right_row["predicted_relation"] == right_row["gold_relation"]
        group_values[left_row["split_group_id"]].append(float(left_correct) - float(right_correct))
    group_deltas = {group: sum(values) / len(values) for group, values in group_values.items()}
    groups = sorted(group_deltas)
    if not groups:
        return {"rate": None, "ci_low": None, "ci_high": None, "n_groups": 0}
    estimate = sum(group_deltas.values()) / len(groups)
    rng = random.Random(seed)
    samples = []
    for _ in range(bootstrap_iters):
        selected = [rng.choice(groups) for _ in groups]
        samples.append(sum(group_deltas[group] for group in selected) / len(selected))
    samples.sort()
    return {
        "rate": estimate,
        "ci_low": samples[max(0, int(0.025 * len(samples)) - 1)],
        "ci_high": samples[min(len(samples) - 1, int(0.975 * len(samples)))],
        "n_groups": len(groups),
    }


def source_holdout(rows: list[EffectBindingRow], pairs: list[dict[str, Any]], source: str) -> dict[str, Any]:
    train_pairs = [pair for pair in pairs if pair["source_scope"] != source]
    test_pairs = [pair for pair in pairs if pair["source_scope"] == source]
    if not train_pairs or not test_pairs:
        return {"status": "not_evaluable"}
    train_rows = [row for row in rows if row.source_scope != source]
    test_rows = [row for row in rows if row.source_scope == source]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=12000)
    train_matrix = vectorizer.fit_transform([row_input_text(row) for row in train_rows])
    test_matrix = vectorizer.transform([row_input_text(row) for row in test_rows])
    n_components = max(2, min(64, train_matrix.shape[0] - 1, train_matrix.shape[1] - 1))
    svd = TruncatedSVD(n_components=n_components, random_state=0)
    train_embed = svd.fit_transform(train_matrix)
    test_embed = svd.transform(test_matrix)
    scaler = StandardScaler()
    train_embed = scaler.fit_transform(train_embed)
    test_embed = scaler.transform(test_embed)
    row_model = build_classifier()
    row_model.fit(train_embed, [row.labels["expected_decision"] for row in train_rows])
    embed_by_case = {
        **{row.case_id: train_embed[index] for index, row in enumerate(train_rows)},
        **{row.case_id: test_embed[index] for index, row in enumerate(test_rows)},
    }
    prob_by_case = {
        **{row.case_id: row_model.predict_proba(train_embed)[index] for index, row in enumerate(train_rows)},
        **{row.case_id: row_model.predict_proba(test_embed)[index] for index, row in enumerate(test_rows)},
    }
    model = build_classifier()
    model.fit(
        pair_feature_matrix(train_pairs, embed_by_case, prob_by_case),
        [pair["relation_label"] for pair in train_pairs],
    )
    predictions = [
        prediction_record(pair, str(prediction), 0)
        for pair, prediction in zip(test_pairs, model.predict(pair_feature_matrix(test_pairs, embed_by_case, prob_by_case)))
    ]
    return {
        "status": "complete",
        "train_source_counts": dict(Counter(pair["source_scope"] for pair in train_pairs)),
        "test_source": source,
        "metrics": summarize_relation_predictions(predictions),
    }


def pair_feature_matrix(
    pairs: list[dict[str, Any]],
    embed_by_case: dict[str, np.ndarray],
    prob_by_case: dict[str, np.ndarray],
) -> np.ndarray:
    features = []
    for pair in pairs:
        left_embed = embed_by_case[pair["left_case_id"]]
        right_embed = embed_by_case[pair["right_case_id"]]
        left_prob = prob_by_case[pair["left_case_id"]]
        right_prob = prob_by_case[pair["right_case_id"]]
        cosine = float(np.dot(left_embed, right_embed) / (np.linalg.norm(left_embed) * np.linalg.norm(right_embed) + 1e-9))
        features.append(
            np.concatenate(
                [
                    np.abs(left_embed - right_embed),
                    left_embed * right_embed,
                    np.abs(left_prob - right_prob),
                    left_prob * right_prob,
                    np.asarray([cosine]),
                ]
            )
        )
    return np.asarray(features)


def prediction_record(pair: dict[str, Any], prediction: str, fold: int) -> dict[str, Any]:
    return {
        "pair_id": pair["pair_id"],
        "split_group_id": pair["split_group_id"],
        "source_scope": pair["source_scope"],
        "gold_relation": pair["relation_label"],
        "predicted_relation": prediction,
        "changed_fields": pair.get("changed_fields", []),
        "fold": fold,
    }


def summarize_relation_predictions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    correct = [row["predicted_relation"] == row["gold_relation"] for row in rows]
    labels = [row["gold_relation"] for row in rows]
    predictions = [row["predicted_relation"] for row in rows]
    by_source = {}
    for source, items in group_dict(rows, "source_scope").items():
        by_source[source] = wilson(
            sum(row["predicted_relation"] == row["gold_relation"] for row in items),
            len(items),
        )
    by_changed_field = {}
    for field in ("effect", "resource", "authorization_match", "provenance_risk"):
        items = [row for row in rows if field in row.get("changed_fields", [])]
        by_changed_field[field] = wilson(
            sum(row["predicted_relation"] == row["gold_relation"] for row in items),
            len(items),
        )
    return {
        "n_pairs": len(rows),
        "accuracy": wilson(sum(correct), len(correct)),
        "balanced_accuracy": balanced_accuracy_score(labels, predictions) if rows else None,
        "by_source": by_source,
        "by_changed_field": by_changed_field,
    }


def group_dict(rows: list[dict[str, Any]], field: str) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        output[str(row.get(field))].append(row)
    return output
