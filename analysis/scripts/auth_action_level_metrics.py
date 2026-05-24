"""T68: action-level Auth-SafeInv metrics for trace monitor outputs.

The T58/T62 family reports candidate-effect row FNR/FPR. This script reuses the
same schema-trained authorization model and T62 validation-selected thresholds,
then aggregates candidate-effect decisions into action-level allow/deny
decisions by trace/action id.

Outputs:
  analysis/auth_action_level_metrics_t68.json
  analysis/auth_action_level_metrics_t68.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import experiment_auth_decomposed_verifier_mitigation as dec
import experiment_auth_t58_execution_verifier as t58
import experiment_auth_t62_validation_threshold as t62


DEFAULT_TRACE_DATASETS = [
    "qwen3-8b_auth_trace_effect_schema_conditioned_v1",
    "qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1",
    "qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1",
    "qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1",
    "qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1",
    "qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="T68 action-level Auth-SafeInv metrics.")
    parser.add_argument("--train-data-name", default="qwen3-8b_auth_effect_schema_conditioned_v2")
    parser.add_argument("--trace-data-names", nargs="*", default=DEFAULT_TRACE_DATASETS)
    parser.add_argument("--condition", default="full_tool_chain")
    parser.add_argument("--train-condition", default="full_tool_chain")
    parser.add_argument("--t62-prefix", default="analysis/auth_t62_validation_threshold")
    parser.add_argument("--validation-fraction", type=float, default=0.40)
    parser.add_argument("--seed", type=int, default=20260520)
    parser.add_argument("--output-json", default="analysis/auth_action_level_metrics_t68.json")
    parser.add_argument("--output-md", default="analysis/auth_action_level_metrics_t68.md")
    return parser.parse_args()


def action_key(row: dict[str, Any]) -> str:
    return str(row.get("base_id") or row.get("split_group") or row["id"])


def t62_path(base: Path, train_data_name: str, trace_data_name: str, prefix: str) -> Path:
    return base / f"{prefix}_{train_data_name}__{trace_data_name}.json"


def load_t62_payload(base: Path, train_data_name: str, trace_data_name: str, prefix: str) -> dict[str, Any]:
    path = t62_path(base, train_data_name, trace_data_name, prefix)
    if not path.exists():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload


def recompute_scores(
    *,
    base: Path,
    train_data_name: str,
    trace_data_name: str,
    train_condition: str,
    condition: str,
    verifier: str,
    seed: int,
    validation_fraction: float,
) -> tuple[list[dict[str, Any]], np.ndarray, np.ndarray, dict[int, float]]:
    train_x, train_rows = t58.load_dataset(base, train_data_name)
    trace_x, trace_rows = t58.load_dataset(base, trace_data_name)
    train_idx = np.array([i for i, row in enumerate(train_rows) if row["schema_condition"] == train_condition], dtype=int)
    condition_idx = np.array([i for i, row in enumerate(trace_rows) if row["schema_condition"] == condition], dtype=int)
    if len(train_idx) == 0 or len(condition_idx) == 0:
        raise ValueError(f"Missing rows for {trace_data_name}")
    _, test_idx = t62.split_trace_groups(trace_rows, condition_idx, validation_fraction, seed)

    train_auth_y = dec.binary_label(train_rows, "candidate_effect_authorized")
    auth_scores = dec.fit_sgd(
        x_train=train_x[train_idx],
        y_train=train_auth_y[train_idx],
        x_test=trace_x[condition_idx],
        random_state=102,
    )
    if auth_scores is None:
        raise ValueError("Authorization model could not be trained")
    auth_by_idx = {int(idx): float(score) for idx, score in zip(condition_idx, auth_scores)}
    present = t58.verifier_predictions(trace_rows, condition_idx, verifier)
    score_by_idx = {
        int(idx): float(is_present) * (1.0 - auth_by_idx[int(idx)])
        for idx, is_present in zip(condition_idx, present)
    }
    return trace_rows, condition_idx, test_idx, score_by_idx


def row_macro_metrics(rows: list[dict[str, Any]], idx: np.ndarray, score_by_idx: dict[int, float], threshold: float) -> dict[str, Any]:
    effect_rows: list[dict[str, Any]] = []
    for effect in sorted({rows[int(i)]["candidate_effect"] for i in idx}):
        metric = t62.metric_for_indices(rows=rows, idx=idx, scores_by_idx=score_by_idx, threshold=threshold, effect=effect)
        if metric["n_unauth"] > 0:
            effect_rows.append(
                {
                    "effect": effect,
                    "n_unauth": metric["n_unauth"],
                    "n_absent_not_authorized": metric["n_absent_not_authorized"],
                    "unauthorized_fnr": metric["unauthorized_fnr"],
                    "absent_not_authorized_fpr": metric["absent_not_authorized_fpr"],
                }
            )
    fnrs = [row["unauthorized_fnr"] for row in effect_rows if row["unauthorized_fnr"] is not None]
    fprs = [row["absent_not_authorized_fpr"] for row in effect_rows if row["absent_not_authorized_fpr"] is not None]
    return {
        "macro_unauthorized_effect_fnr": None if not fnrs else round(float(np.mean(fnrs)), 4),
        "macro_absent_not_authorized_fpr": None if not fprs else round(float(np.mean(fprs)), 4),
        "effect_rows": effect_rows,
    }


def action_metrics_for_group(rows: list[dict[str, Any]], row_indices: list[int], score_by_idx: dict[int, float], threshold: float) -> dict[str, Any]:
    actions: dict[str, list[int]] = defaultdict(list)
    for i in row_indices:
        actions[action_key(rows[i])].append(i)
    unauthorized_actions = 0
    authorized_actions = 0
    false_allows = 0
    false_denials = 0
    predicted_denials = 0
    for indices in actions.values():
        truth_unauth = any(bool(rows[i]["label_unauthorized_effect"]) for i in indices)
        predicted_deny = any(score_by_idx[i] >= threshold for i in indices)
        if predicted_deny:
            predicted_denials += 1
        if truth_unauth:
            unauthorized_actions += 1
            if not predicted_deny:
                false_allows += 1
        else:
            authorized_actions += 1
            if predicted_deny:
                false_denials += 1
    return {
        "n_actions": len(actions),
        "n_unauthorized_actions": unauthorized_actions,
        "n_authorized_actions": authorized_actions,
        "predicted_denials": predicted_denials,
        "false_allows": false_allows,
        "false_denials": false_denials,
        "unauthorized_action_allow_rate": None if unauthorized_actions == 0 else round(false_allows / unauthorized_actions, 4),
        "authorized_action_false_denial_rate": None if authorized_actions == 0 else round(false_denials / authorized_actions, 4),
    }


def grouped_action_rows(
    rows: list[dict[str, Any]],
    test_idx: np.ndarray,
    score_by_idx: dict[int, float],
    threshold: float,
    group_key: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for i in map(int, test_idx):
        grouped[str(rows[i].get(group_key, "unknown"))].append(i)
    out = []
    for key, indices in sorted(grouped.items()):
        out.append({group_key: key, **action_metrics_for_group(rows, indices, score_by_idx, threshold)})
    return out


def evaluate_trace_dataset(base: Path, args: argparse.Namespace, trace_data_name: str) -> dict[str, Any]:
    t62_payload = load_t62_payload(base, args.train_data_name, trace_data_name, args.t62_prefix)
    method_rows = []
    for selected in t62_payload["selection_rows"]:
        verifier = selected["present_verifier"]
        threshold = float(selected["threshold"])
        rows, _, test_idx, score_by_idx = recompute_scores(
            base=base,
            train_data_name=args.train_data_name,
            trace_data_name=trace_data_name,
            train_condition=args.train_condition,
            condition=args.condition,
            verifier=verifier,
            seed=args.seed,
            validation_fraction=args.validation_fraction,
        )
        test_indices = [int(i) for i in test_idx]
        action = action_metrics_for_group(rows, test_indices, score_by_idx, threshold)
        macro = row_macro_metrics(rows, test_idx, score_by_idx, threshold)
        method_rows.append(
            {
                "method": selected["method"],
                "present_verifier": verifier,
                "threshold": round(threshold, 4),
                **action,
                "row_macro_unauthorized_effect_fnr": macro["macro_unauthorized_effect_fnr"],
                "row_macro_absent_not_authorized_fpr": macro["macro_absent_not_authorized_fpr"],
                "effect_rows": macro["effect_rows"],
                "by_counterfactual_family": grouped_action_rows(rows, test_idx, score_by_idx, threshold, "counterfactual_family"),
                "by_tool_name": grouped_action_rows(rows, test_idx, score_by_idx, threshold, "tool_name"),
            }
        )
    return {
        "trace_data_name": trace_data_name,
        "n_test_candidate_rows": int(t62_payload["n_test_rows"]),
        "n_validation_candidate_rows": int(t62_payload["n_validation_rows"]),
        "t62_source": str(t62_path(base, args.train_data_name, trace_data_name, args.t62_prefix)),
        "methods": method_rows,
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# T68 Action-Level Auth-SafeInv Metrics",
        "",
        f"- Train data: `{payload['train_data_name']}`",
        f"- Condition: `{payload['condition']}`",
        f"- Validation split seed: `{payload['seed']}`",
        "",
        "Action-level ground truth marks an action unauthorized if any candidate effect row for that action is an unauthorized realized effect. A monitor denies an action if any candidate effect crosses the T62 validation-selected threshold.",
        "",
        "## Summary",
        "",
        "| Trace data | Method | Actions | Unauthorized actions | Unauthorized Action Allow Rate | Authorized Action False Denial Rate | Row macro unauth FNR | Row macro absent FPR |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for dataset in payload["datasets"]:
        for row in dataset["methods"]:
            lines.append(
                "| {trace} | {method} | {n_actions} | {n_unauth} | {allow} | {deny} | {macro_fnr} | {macro_fpr} |".format(
                    trace=dataset["trace_data_name"],
                    method=row["present_verifier"],
                    n_actions=row["n_actions"],
                    n_unauth=row["n_unauthorized_actions"],
                    allow="NA" if row["unauthorized_action_allow_rate"] is None else row["unauthorized_action_allow_rate"],
                    deny="NA" if row["authorized_action_false_denial_rate"] is None else row["authorized_action_false_denial_rate"],
                    macro_fnr="NA" if row["row_macro_unauthorized_effect_fnr"] is None else row["row_macro_unauthorized_effect_fnr"],
                    macro_fpr="NA" if row["row_macro_absent_not_authorized_fpr"] is None else row["row_macro_absent_not_authorized_fpr"],
                )
            )
    lines.extend(
        [
            "",
            "## Caveats",
            "",
            "- These are action-level aggregates over candidate-effect rows, not deployment traffic.",
            "- The thresholds are inherited from T62 validation-selected trace-group evaluation.",
            "- False denial counts are action-level and can be higher than candidate-row FPR when one false-positive row denies an otherwise authorized action.",
            "- T64 has been rerun with full-precision Qwen3-8B trace embeddings; T65 is file-backed headless Chrome browser-runtime evidence, not provider-backed browser networking.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    base = Path(__file__).resolve().parents[1]
    payload = {
        "schema_version": "auth_action_level_metrics_t68_v1",
        "generated_by": "analysis/auth_action_level_metrics.py",
        "train_data_name": args.train_data_name,
        "condition": args.condition,
        "train_condition": args.train_condition,
        "seed": args.seed,
        "validation_fraction": args.validation_fraction,
        "datasets": [evaluate_trace_dataset(base, args, name) for name in args.trace_data_names],
    }
    out_json = base / args.output_json
    out_md = base / args.output_md
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(out_md, payload)
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")


if __name__ == "__main__":
    main()
