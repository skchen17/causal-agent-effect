from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.experiments.effect_binding_guard.dataset import row_input_text
from src.experiments.effect_binding_guard.guards import (
    infer_evidence_tuple,
    is_side_effectful,
    provenance_overlay,
    rule_tuple,
    view_predictions,
)
from src.experiments.effect_binding_guard.schema import EffectBindingRow, TuplePrediction, stable_hash
from src.experiments.tool_effect_fragmentation.io_utils import read_jsonl, write_json, write_jsonl


MAIN_FORBIDDEN_FEATURE_KEYS = {
    "pair_role",
    "counterfactual_axis",
    "claim_scope",
    "audit_status",
    "source_scope",
    "expected_decision",
    "gold_effect",
    "gold_resource",
    "gold_authorization_match",
    "gold_provenance_risk",
    "risk_label",
    "effect_resource_oracle",
    "execution_evidence_upper_bound",
    "multi_view_disagreement_guard.decision",
    "evidence_gated_selective_guard.decision",
    "effect_binding_guard_full.decision",
}

CALIBRATED_E48_METHODS = {
    "multi_view_disagreement_guard",
    "evidence_gated_selective_guard",
    "effect_binding_guard_full",
    "never_use_evidence",
}

RESOURCE_TOKEN_KEYS = {
    "raw_resource",
    "resource_value",
    "predicted_resource_value",
}


@dataclass
class FeatureRow:
    case_id: str
    split_group_id: str
    counterfactual_group_id: str
    source_scope: str
    audit_status: str
    expected_decision: str
    label: int
    features: dict[str, Any]
    text: str
    majority_tuple: dict[str, str]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "split_group_id": self.split_group_id,
            "counterfactual_group_id": self.counterfactual_group_id,
            "source_scope": self.source_scope,
            "audit_status": self.audit_status,
            "expected_decision": self.expected_decision,
            "label": self.label,
            "features": self.features,
            "text": self.text,
            "majority_tuple": self.majority_tuple,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, obj: dict[str, Any]) -> "FeatureRow":
        return cls(**obj)


def load_local_qwen_predictions(path: Path) -> dict[str, TuplePrediction]:
    predictions: dict[str, TuplePrediction] = {}
    for row in read_jsonl(path):
        allowed = {
            "case_id",
            "method",
            "source_scope",
            "split_group_id",
            "predicted_effect",
            "predicted_resource",
            "authorization_match",
            "provenance_risk",
            "decision",
            "confidence",
            "uncertainty",
            "abstain_reason",
            "accessed_fields",
            "decision_inputs_hash",
            "claim_scope",
            "metadata",
        }
        payload = {key: row[key] for key in allowed if key in row}
        payload.setdefault("method", "local_qwen_tuple_guard")
        payload.setdefault("claim_scope", "diagnostic")
        predictions[payload["case_id"]] = TuplePrediction.from_dict(payload)
    return predictions


def primitive_predictions(
    row: EffectBindingRow,
    qwen_predictions: dict[str, TuplePrediction] | None = None,
) -> list[TuplePrediction]:
    """Build threshold-independent non-oracle predictions for fusion features."""
    output: list[TuplePrediction] = []
    output.append(rule_tuple(row, method="primitive::rule_tuple"))
    output.append(rule_tuple(row, use_provenance=False, method="primitive::rule_no_provenance"))
    output.append(infer_evidence_tuple(row, method="primitive::evidence_tuple"))
    no_provenance = rule_tuple(row, use_provenance=False, method="primitive::rule_no_provenance_for_overlay")
    output.append(provenance_overlay(row, no_provenance, method="primitive::provenance_overlay"))
    output.extend(view_predictions(row, use_provenance=False))
    if qwen_predictions and row.case_id in qwen_predictions:
        qwen = qwen_predictions[row.case_id]
        qwen.method = "primitive::local_qwen_tuple"
        output.append(qwen)
    return output


def build_feature_rows(
    rows: list[EffectBindingRow],
    qwen_predictions: dict[str, TuplePrediction] | None = None,
    *,
    include_source_metadata: bool = False,
) -> list[FeatureRow]:
    feature_rows = []
    for row in rows:
        preds = primitive_predictions(row, qwen_predictions)
        features = feature_dict(row, preds, include_source_metadata=include_source_metadata)
        majority = majority_tuple(preds)
        feature_rows.append(
            FeatureRow(
                case_id=row.case_id,
                split_group_id=row.split_group_id,
                counterfactual_group_id=row.counterfactual_group_id,
                source_scope=row.source_scope,
                audit_status=row.audit_status,
                expected_decision=row.labels["expected_decision"],
                label=1 if row.labels["expected_decision"] == "DENY" else 0,
                features=features,
                text=row_input_text(row),
                majority_tuple=majority,
                metadata={
                    "feature_input_hash": stable_hash(features),
                    "primitive_methods": sorted({pred.method for pred in preds}),
                    "main_feature_policy": "strict_deployable_no_construction_metadata",
                },
            )
        )
    return feature_rows


def feature_dict(
    row: EffectBindingRow,
    preds: list[TuplePrediction],
    *,
    include_source_metadata: bool = False,
) -> dict[str, Any]:
    features: dict[str, Any] = {}
    decisions = [pred.decision for pred in preds]
    features["n_primitive_predictions"] = len(preds)
    for decision in ("ALLOW", "DENY", "ABSTAIN"):
        features[f"vote_count__{decision}"] = decisions.count(decision)
        features[f"vote_ratio__{decision}"] = decisions.count(decision) / max(len(decisions), 1)
    features["decision_disagreement"] = disagreement(decisions)

    for field in ("predicted_effect", "authorization_match", "provenance_risk"):
        values = [str(getattr(pred, field)) for pred in preds]
        features[f"{field}__disagreement"] = disagreement(values)
        features[f"{field}__known_ratio"] = sum(value not in {"unknown", "uncertain", "missing"} for value in values) / max(len(values), 1)
        for value, count in Counter(values).most_common(5):
            safe_value = sanitize_category(value)
            features[f"{field}__vote__{safe_value}"] = count

    resource_types = [resource_type(pred.predicted_resource) for pred in preds]
    features["predicted_resource_type__disagreement"] = disagreement(resource_types)
    for value, count in Counter(resource_types).most_common(5):
        features[f"predicted_resource_type__vote__{sanitize_category(value)}"] = count
    resources = [normalize_resource(pred.predicted_resource) for pred in preds if normalize_resource(pred.predicted_resource) != "unknown"]
    features["resource_exact_agreement_ratio"] = max(Counter(resources).values(), default=0) / max(len(resources), 1)
    features["resource_known_ratio"] = len(resources) / max(len(preds), 1)
    features["resource_unique_count_capped"] = min(len(set(resources)), 6)

    for pred in preds:
        prefix = method_key(pred.method)
        if pred.method in CALIBRATED_E48_METHODS:
            continue
        features[f"{prefix}__confidence"] = float(pred.confidence)
        features[f"{prefix}__uncertainty"] = float(pred.uncertainty)
        features[f"{prefix}__abstained"] = int(pred.decision == "ABSTAIN")
        features[f"{prefix}__decision__{pred.decision}"] = 1
        features[f"{prefix}__auth__{pred.authorization_match}"] = 1
        features[f"{prefix}__provenance__{pred.provenance_risk}"] = 1
        features[f"{prefix}__effect__{sanitize_category(pred.predicted_effect)}"] = 1
        features[f"{prefix}__resource_type__{resource_type(pred.predicted_resource)}"] = 1
        if "parse_valid" in pred.metadata:
            features[f"{prefix}__parse_valid"] = int(bool(pred.metadata.get("parse_valid")))

    deployable = row.deployable_input
    provenance = deployable.get("provenance_summary") or {}
    evidence = deployable.get("evidence_summary")
    features["evidence_available"] = int(bool(evidence))
    features["evidence_event_count_capped"] = min(len(evidence), 8) if isinstance(evidence, list) else int(bool(evidence))
    features["provenance_present"] = int(bool(provenance))
    features["side_effectful_visible"] = int(bool(provenance.get("side_effectful")) if provenance else is_side_effectful(majority_tuple(preds)["predicted_effect"], deployable))
    control_source = str(provenance.get("control_source", "missing")).lower() if provenance else "missing"
    data_source = str(provenance.get("data_source", "missing")).lower() if provenance else "missing"
    for value in ("user", "trusted_policy", "trusted_tool_output", "private_tool_output", "untrusted_tool_output", "injected_content", "unknown", "missing"):
        features[f"control_source__{sanitize_category(value)}"] = int(control_source == value)
    features["control_private_or_untrusted"] = int(any(token in control_source for token in ("private", "untrusted", "injected")))
    features["data_private_or_untrusted"] = int(any(token in data_source for token in ("private", "untrusted", "injected")))
    if include_source_metadata:
        features[f"diagnostic_source_scope__{row.source_scope}"] = 1
    return features


def majority_tuple(preds: list[TuplePrediction]) -> dict[str, str]:
    return {
        "predicted_effect": majority([pred.predicted_effect for pred in preds], {"unknown"}),
        "predicted_resource": majority([pred.predicted_resource for pred in preds], {"unknown"}),
        "authorization_match": majority([pred.authorization_match for pred in preds], {"uncertain", "missing"}),
        "provenance_risk": majority([pred.provenance_risk for pred in preds], {"unknown", "missing"}),
    }


def majority(values: list[str], ignored: set[str]) -> str:
    kept = [str(value) for value in values if str(value) not in ignored]
    if kept:
        return Counter(kept).most_common(1)[0][0]
    return sorted(ignored)[0]


def disagreement(values: list[str]) -> float:
    if not values:
        return 1.0
    return 1.0 - Counter(values).most_common(1)[0][1] / len(values)


def resource_type(value: Any) -> str:
    text = normalize_resource(value)
    if text == "unknown":
        return "unknown"
    if "@" in text:
        return "email"
    if text.startswith("http://") or text.startswith("https://"):
        return "url"
    if "/" in text:
        return "path"
    if any(token in text for token in ("account", "iban", "bank")):
        return "account"
    if any(token in text for token in ("channel", "slack")):
        return "channel"
    if any(token in text for token in ("event", "calendar")):
        return "event"
    if any(token in text for token in ("hotel", "reservation")):
        return "reservation"
    if text.replace("-", "").replace("_", "").isdigit():
        return "numeric_id"
    return "opaque_id"


def normalize_resource(value: Any) -> str:
    text = str(value or "unknown").strip().lower()
    return text if text and text not in {"none", "null"} else "unknown"


def method_key(method: str) -> str:
    return method.replace("primitive::", "").replace("rule_view::", "view__").replace(":", "_").replace("/", "_")


def sanitize_category(value: Any) -> str:
    text = str(value).strip().lower()
    text = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in text)
    return text[:80] or "empty"


def leakage_audit(feature_rows: list[FeatureRow], *, include_source_metadata: bool = False) -> dict[str, Any]:
    key_violations: dict[str, list[str]] = {}
    serialized_violations: dict[str, list[str]] = {}
    resource_token_violations: dict[str, list[str]] = {}
    forbidden = set(MAIN_FORBIDDEN_FEATURE_KEYS)
    if include_source_metadata:
        forbidden.discard("source_scope")
    markers = sorted(forbidden)
    for row in feature_rows:
        keys = sorted(row.features)
        bad_keys = [key for key in keys if any(marker in key for marker in markers)]
        if bad_keys:
            key_violations[row.case_id] = bad_keys[:20]
        serialized = json.dumps(row.features, ensure_ascii=False, sort_keys=True).lower()
        bad_markers = [marker for marker in markers if marker in serialized]
        if bad_markers:
            serialized_violations[row.case_id] = bad_markers[:20]
        raw_like = [key for key in keys if any(token in key for token in RESOURCE_TOKEN_KEYS)]
        if raw_like:
            resource_token_violations[row.case_id] = raw_like[:20]
    return {
        "schema_version": "e49_feature_leakage_audit_v1",
        "n_rows": len(feature_rows),
        "include_source_metadata": include_source_metadata,
        "forbidden_feature_key_violations": key_violations,
        "forbidden_serialized_marker_violations": serialized_violations,
        "raw_resource_feature_violations": resource_token_violations,
        "leakage_free": not key_violations and not serialized_violations and not resource_token_violations,
        "calibrated_e48_decisions_excluded_from_features": True,
    }


def write_feature_artifacts(root: Path, rows: list[FeatureRow], audit: dict[str, Any]) -> dict[str, Any]:
    feature_path = root / "data/e49_effect_binding_fusion_features.jsonl"
    audit_path = root / "analysis/results/e49_leakage_audit.json"
    manifest_path = root / "analysis/results/e49_feature_manifest.json"
    write_jsonl(feature_path, [row.to_dict() for row in rows])
    write_json(audit_path, audit)
    feature_names = sorted({key for row in rows for key in row.features})
    manifest = {
        "schema_version": "e49_feature_manifest_v1",
        "n_rows": len(rows),
        "n_features": len(feature_names),
        "feature_path": str(feature_path),
        "leakage_audit_path": str(audit_path),
        "feature_policy": "strict_deployable_no_construction_source_audit_or_gold_metadata",
        "excluded_feature_families": sorted(MAIN_FORBIDDEN_FEATURE_KEYS),
        "feature_names": feature_names,
        "source_counts": dict(Counter(row.source_scope for row in rows)),
        "group_count": len({row.split_group_id for row in rows}),
        "local_qwen_reused": True,
    }
    write_json(manifest_path, manifest)
    return manifest

