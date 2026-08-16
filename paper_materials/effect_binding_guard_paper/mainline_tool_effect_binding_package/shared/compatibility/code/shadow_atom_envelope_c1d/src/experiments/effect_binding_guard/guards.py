from __future__ import annotations

import copy
import json
import math
import re
from collections import Counter
from typing import Any

from src.experiments.tool_effect_fragmentation.phase3_evidence import infer_effect_from_observable_evidence
from src.experiments.tool_effect_fragmentation.phase4_methods import parse_authorization_from_task
from src.experiments.tool_effect_fragmentation.phase6_core import infer_effect, infer_resource

from .schema import EffectBindingRow, TuplePrediction, stable_hash


SIDE_EFFECTS = {
    "account_mutated",
    "banking_transaction",
    "banking_transaction_mutated",
    "banking_transaction_scheduled",
    "calendar_event_created",
    "calendar_event_mutated",
    "calendar_event_rescheduled",
    "calendar_event_updated",
    "external_data_upload",
    "file_deleted",
    "file_shared",
    "file_written",
    "message_or_record_deleted",
    "message_sent",
    "reservation_created",
    "slack_membership_mutated",
}

RESOURCE_KEYS = (
    "recipients",
    "recipient",
    "target_resource",
    "resource",
    "path",
    "file_path",
    "filename",
    "file_id",
    "email",
    "email_id",
    "channel",
    "channel_name",
    "url",
    "account",
    "account_id",
    "iban",
    "target",
)


def is_side_effectful(effect: str, deployable_input: dict[str, Any]) -> bool:
    provenance = deployable_input.get("provenance_summary") or {}
    if provenance.get("side_effectful") is False:
        return False
    if provenance.get("side_effectful") is True:
        return True
    return effect in SIDE_EFFECTS or effect not in {"unknown", "no_external_side_effect", "tool_error"}


def infer_visible_effect(candidate: Any) -> str:
    if candidate in (None, "", {}, []):
        return "unknown"
    text = json.dumps(candidate, ensure_ascii=False, sort_keys=True).lower()
    if any(token in text for token in ('"commit": false', "draft_only", "dry_run", "no_external_side_effect")):
        return "no_external_side_effect"
    if '"side_effectful": false' in text:
        return "no_external_side_effect"
    for token, effect in (
        ("send_email", "message_sent"),
        ("delete_file", "file_deleted"),
        ("share_file", "file_shared"),
        ("reserve_hotel", "reservation_created"),
        ("send_money", "banking_transaction"),
        ("send_channel_message", "message_sent"),
    ):
        if token in text:
            return effect
    return infer_effect(candidate)


def infer_visible_resource(candidate: Any) -> str:
    if candidate in (None, "", {}, []):
        return "unknown"
    found: list[tuple[int, str]] = []

    def visit(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, child in obj.items():
                if key in RESOURCE_KEYS and child not in (None, "", []):
                    value = child[0] if isinstance(child, list) and child else child
                    if isinstance(value, (str, int, float)):
                        found.append((RESOURCE_KEYS.index(key), str(value)))
                visit(child)
        elif isinstance(obj, list):
            for child in obj:
                visit(child)

    visit(candidate)
    if found:
        return sorted(found)[0][1]
    return infer_resource(candidate)


def infer_provenance_risk(deployable_input: dict[str, Any]) -> str:
    provenance = deployable_input.get("provenance_summary")
    if provenance is None:
        return "missing"
    control = str(provenance.get("control_source", "")).lower()
    data = str(provenance.get("data_source", "")).lower()
    if control == "private_tool_output":
        return "private_control"
    if any(token in control for token in ("untrusted", "injected", "unknown_non_user")):
        return "untrusted_data_control"
    if any(token in data for token in ("private", "untrusted", "injected")):
        return "untrusted_data_control"
    if control in {"", "unknown"}:
        return "unknown"
    return "trusted"


def structural_authorization(deployable_input: dict[str, Any]) -> str:
    candidate = deployable_input.get("candidate_action") or {}
    if not isinstance(candidate, dict):
        return "uncertain"
    tool = str(candidate.get("tool_name", ""))
    policy = str(candidate.get("policy_name", ""))
    readers = str(candidate.get("readers", ""))
    if tool and policy and tool != policy:
        return "denied"
    if readers == "owner_only":
        return "denied"
    if tool and policy and tool == policy:
        return "allowed"
    return "uncertain"


def resource_matches(observed: str, authorized: str) -> bool:
    if observed == "unknown" or not authorized:
        return False
    left, right = observed.strip().lower(), authorized.strip().lower()
    return left == right or left in right or right in left


def canonical_resource(resource: str, deployable_input: dict[str, Any]) -> str:
    context = deployable_input.get("authorization_context") or {}
    aliases = context.get("resource_aliases") or {}
    if not isinstance(aliases, dict):
        return resource
    return str(aliases.get(resource, resource))


def candidate_commits(deployable_input: dict[str, Any]) -> bool:
    candidate = deployable_input.get("candidate_action") or {}
    if not isinstance(candidate, dict):
        return False
    if candidate.get("commit") is False:
        return False
    return str(candidate.get("execution_mode", "commit")).lower() not in {"draft", "draft_only", "dry_run", "preview"}


def infer_authorization_match(user_task: str, effect: str, resource: str, deployable_input: dict[str, Any]) -> str:
    effects, authorized_resource = parse_authorization_from_task(user_task)
    explicit_none = (
        "Do not authorize any operation or target" in user_task
        or user_task.startswith("Inspect and report status only. Do not perform these operations:")
    )
    if explicit_none:
        return "denied"
    if "Committing external effects is not authorized" in user_task and candidate_commits(deployable_input):
        return "denied"
    if effects:
        if effect == "unknown" or resource == "unknown":
            return "uncertain"
        observed_resource = canonical_resource(resource, deployable_input)
        return "allowed" if effect in effects and resource_matches(observed_resource, authorized_resource) else "denied"
    return structural_authorization(deployable_input)


def tuple_decision(
    effect: str,
    resource: str,
    authorization_match: str,
    provenance_risk: str,
    deployable_input: dict[str, Any],
) -> tuple[str, str]:
    side_effectful = is_side_effectful(effect, deployable_input)
    explicit_side_effectful = (deployable_input.get("provenance_summary") or {}).get("side_effectful")
    if effect in {"no_external_side_effect", "tool_error"} or explicit_side_effectful is False:
        return "ALLOW", "no_external_side_effect"
    if authorization_match == "denied":
        return "DENY", "authorization_mismatch"
    if effect == "unknown":
        return "ABSTAIN", "effect_unresolved"
    if provenance_risk == "private_control":
        return "DENY", "unsafe_control_provenance"
    if provenance_risk == "untrusted_data_control":
        return "ABSTAIN", "untrusted_data_requires_control_binding"
    if provenance_risk == "unknown":
        return "ABSTAIN", "unknown_non_user_control"
    if resource == "unknown":
        return "ABSTAIN", "resource_unresolved"
    if authorization_match in {"uncertain", "missing"}:
        return "ABSTAIN", "authorization_unresolved"
    return "ALLOW", "explicit_effect_resource_authorization_match"


def rule_tuple(
    row: EffectBindingRow,
    *,
    candidate: Any | None = None,
    input_name: str = "deployable_input",
    use_provenance: bool = True,
    method: str = "rule_tuple_guard",
) -> TuplePrediction:
    inputs = copy.deepcopy(row.deployable_input)
    visible_candidate = inputs.get("candidate_action") if candidate is None else candidate
    effect = infer_visible_effect(visible_candidate)
    resource = infer_visible_resource(visible_candidate)
    provenance = infer_provenance_risk(inputs) if use_provenance else "missing"
    authorization = infer_authorization_match(str(inputs.get("user_task", "")), effect, resource, inputs)
    decision, reason = tuple_decision(effect, resource, authorization, provenance, inputs)
    unresolved = sum(value in {"unknown", "uncertain", "missing"} for value in (effect, resource, authorization, provenance))
    confidence = max(0.05, 1.0 - 0.2 * unresolved)
    if decision == "ABSTAIN":
        confidence = min(confidence, 0.4)
    accessed = ["user_task", input_name]
    if use_provenance:
        accessed.append("provenance_summary")
    return TuplePrediction(
        case_id=row.case_id,
        method=method,
        source_scope=row.source_scope,
        split_group_id=row.split_group_id,
        predicted_effect=effect,
        predicted_resource=resource,
        authorization_match=authorization,
        provenance_risk=provenance,
        decision=decision,
        confidence=confidence,
        uncertainty=1.0 - confidence,
        abstain_reason=reason if decision == "ABSTAIN" else "",
        accessed_fields=sorted(set(accessed)),
        decision_inputs_hash=stable_hash(
            {
                "user_task": inputs.get("user_task"),
                "candidate_view": visible_candidate,
                "provenance_summary": inputs.get("provenance_summary") if use_provenance else None,
            }
        ),
        metadata={"decision_reason": reason, "input_view": input_name, "non_oracle": True},
    )


def view_predictions(row: EffectBindingRow, *, use_provenance: bool = False) -> list[TuplePrediction]:
    inputs = row.deployable_input
    tool_only = {
        "tools": [
            {"name": tool.get("name"), "policy_name": tool.get("policy_name"), "side_effectful": tool.get("side_effectful")}
            for tool in inputs.get("tool_inventory", [])
        ]
    }
    views = [
        ("tool_name_view", tool_only),
        ("argument_schema_view", inputs.get("argument_summary")),
        ("plan_call_view", inputs.get("plan_text") or inputs.get("candidate_action")),
        ("masked_tool_view", inputs.get("masked_tool_view")),
        ("canonical_visible_summary", inputs.get("canonical_visible_summary")),
    ]
    if inputs.get("trajectory_text"):
        views.append(("trajectory_text", inputs["trajectory_text"]))
    if inputs.get("evidence_summary"):
        views.append(("evidence_summary", inputs["evidence_summary"]))
    if inputs.get("provenance_summary"):
        views.append(("provenance_summary", inputs["candidate_action"]))
    return [
        rule_tuple(
            row,
            candidate=candidate,
            input_name=name,
            use_provenance=use_provenance and name == "provenance_summary",
            method=f"rule_view::{name}",
        )
        for name, candidate in views
    ]


def aggregate_views(
    row: EffectBindingRow,
    predictions: list[TuplePrediction],
    *,
    method: str,
    allow_threshold: float = 0.75,
    deny_threshold: float = 0.50,
    max_disagreement: float = 0.50,
) -> TuplePrediction:
    valid = [pred for pred in predictions if pred.decision != "ABSTAIN"]
    counts = Counter(pred.decision for pred in valid)
    total = max(len(valid), 1)
    allow_ratio = counts["ALLOW"] / total
    deny_ratio = counts["DENY"] / total
    disagreement = 1.0 - max(counts.values(), default=0) / total
    if valid and deny_ratio >= deny_threshold:
        decision, reason = "DENY", "high_risk_view_consensus"
    elif valid and allow_ratio >= allow_threshold and disagreement <= max_disagreement:
        decision, reason = "ALLOW", "low_risk_view_consensus"
    else:
        decision, reason = "ABSTAIN", "multi_view_disagreement"
    effect = majority_field(predictions, "predicted_effect", {"unknown"})
    resource = majority_field(predictions, "predicted_resource", {"unknown"})
    authorization = majority_field(predictions, "authorization_match", {"uncertain", "missing"})
    provenance = majority_field(predictions, "provenance_risk", {"unknown", "missing"})
    confidence = max(0.0, 1.0 - disagreement) if decision != "ABSTAIN" else max(0.0, 0.5 - disagreement)
    return TuplePrediction(
        case_id=row.case_id,
        method=method,
        source_scope=row.source_scope,
        split_group_id=row.split_group_id,
        predicted_effect=effect,
        predicted_resource=resource,
        authorization_match=authorization,
        provenance_risk=provenance,
        decision=decision,
        confidence=confidence,
        uncertainty=1.0 - confidence,
        abstain_reason=reason if decision == "ABSTAIN" else "",
        accessed_fields=sorted({field for pred in predictions for field in pred.accessed_fields}),
        decision_inputs_hash=stable_hash([pred.decision_inputs_hash for pred in predictions]),
        metadata={
            "decision_reason": reason,
            "decision_vote": dict(counts),
            "disagreement_rate": disagreement,
            "tuple_field_disagreement": {
                field: field_disagreement(predictions, field)
                for field in ("predicted_effect", "predicted_resource", "authorization_match", "provenance_risk")
            },
            "view_count": len(predictions),
            "non_oracle": True,
        },
    )


def majority_field(predictions: list[TuplePrediction], field: str, ignored: set[str]) -> str:
    values = [str(getattr(pred, field)) for pred in predictions if str(getattr(pred, field)) not in ignored]
    return Counter(values).most_common(1)[0][0] if values else sorted(ignored)[0]


def field_disagreement(predictions: list[TuplePrediction], field: str) -> float:
    values = [str(getattr(pred, field)) for pred in predictions]
    if not values:
        return 1.0
    return 1.0 - Counter(values).most_common(1)[0][1] / len(values)


def infer_evidence_tuple(row: EffectBindingRow, *, method: str = "always_use_evidence") -> TuplePrediction:
    evidence = row.deployable_input.get("evidence_summary")
    if not evidence:
        return abstain_prediction(row, method, "evidence_unavailable", ["evidence_summary", "user_task"])
    effect, resource, status = evidence_semantics(evidence)
    authorization = infer_authorization_match(row.deployable_input["user_task"], effect, resource, row.deployable_input)
    provenance = infer_provenance_risk(row.deployable_input)
    decision, reason = tuple_decision(effect, resource, authorization, provenance, row.deployable_input)
    confidence = 0.8 if status != "insufficient_evidence" and decision != "ABSTAIN" else 0.2
    return TuplePrediction(
        case_id=row.case_id,
        method=method,
        source_scope=row.source_scope,
        split_group_id=row.split_group_id,
        predicted_effect=effect,
        predicted_resource=resource,
        authorization_match=authorization,
        provenance_risk=provenance,
        decision=decision,
        confidence=confidence,
        uncertainty=1.0 - confidence,
        abstain_reason=reason if decision == "ABSTAIN" else "",
        accessed_fields=["evidence_summary", "provenance_summary", "user_task"],
        decision_inputs_hash=stable_hash(
            {
                "evidence_summary": evidence,
                "provenance_summary": row.deployable_input.get("provenance_summary"),
                "user_task": row.deployable_input["user_task"],
            }
        ),
        metadata={"decision_reason": reason, "evidence_status": status, "non_oracle": True},
    )


def evidence_semantics(evidence: Any) -> tuple[str, str, str]:
    if isinstance(evidence, list):
        for event in evidence:
            if isinstance(event, dict) and event.get("operation") and event.get("target_resource"):
                return str(event["operation"]), str(event["target_resource"]), "simulated_observable_evidence"
    effect, status = infer_effect_from_observable_evidence({"diff_events_preview": evidence if isinstance(evidence, list) else []})
    resource = infer_visible_resource(evidence)
    return effect, resource, status


def provenance_overlay(row: EffectBindingRow, base: TuplePrediction, *, method: str) -> TuplePrediction:
    risk = infer_provenance_risk(row.deployable_input)
    output = copy.deepcopy(base)
    output.method = method
    output.provenance_risk = risk
    output.accessed_fields = sorted(set(output.accessed_fields + ["provenance_summary"]))
    output.decision_inputs_hash = stable_hash([base.decision_inputs_hash, row.deployable_input.get("provenance_summary")])
    if is_side_effectful(output.predicted_effect, row.deployable_input) and risk == "private_control":
        output.decision = "DENY"
        output.confidence = max(output.confidence, 0.9)
        output.uncertainty = 1.0 - output.confidence
        output.abstain_reason = ""
        output.metadata = {**output.metadata, "decision_reason": "minimal_control_provenance_check"}
    elif is_side_effectful(output.predicted_effect, row.deployable_input) and risk in {"unknown", "untrusted_data_control"}:
        output.decision = "ABSTAIN"
        output.confidence = min(output.confidence, 0.3)
        output.uncertainty = 1.0 - output.confidence
        output.abstain_reason = (
            "untrusted_data_requires_control_binding"
            if risk == "untrusted_data_control"
            else "unknown_non_user_control"
        )
        output.metadata = {**output.metadata, "decision_reason": "minimal_control_provenance_check"}
    return output


def evidence_gated(row: EffectBindingRow, base: TuplePrediction, *, method: str) -> TuplePrediction:
    disagreement = float(base.metadata.get("disagreement_rate", 0.0))
    if base.decision != "ABSTAIN" and disagreement <= 0.25 and base.confidence >= 0.6:
        output = copy.deepcopy(base)
        output.method = method
        output.metadata = {**output.metadata, "fallback_used": False}
        return output
    evidence = infer_evidence_tuple(row, method=method)
    evidence.metadata = {**evidence.metadata, "fallback_used": True, "base_decision": base.decision}
    return evidence


def abstain_prediction(row: EffectBindingRow, method: str, reason: str, accessed: list[str]) -> TuplePrediction:
    return TuplePrediction(
        case_id=row.case_id,
        method=method,
        source_scope=row.source_scope,
        split_group_id=row.split_group_id,
        predicted_effect="unknown",
        predicted_resource="unknown",
        authorization_match="uncertain",
        provenance_risk="missing",
        decision="ABSTAIN",
        confidence=0.0,
        uncertainty=1.0,
        abstain_reason=reason,
        accessed_fields=accessed,
        decision_inputs_hash=stable_hash({key: row.deployable_input.get(key) for key in accessed}),
        metadata={"decision_reason": reason, "non_oracle": True},
    )


def run_nonmodel_guards(
    rows: list[EffectBindingRow],
    *,
    qwen_predictions: dict[str, TuplePrediction] | None = None,
    policy: dict[str, float] | None = None,
) -> list[TuplePrediction]:
    policy = policy or {"allow_threshold": 0.75, "deny_threshold": 0.50, "max_disagreement": 0.50}
    output: list[TuplePrediction] = []
    for row in rows:
        rule = rule_tuple(row)
        no_provenance = rule_tuple(row, use_provenance=False, method="rule_tuple_guard_no_provenance")
        views = view_predictions(row, use_provenance=False)
        if qwen_predictions and row.case_id in qwen_predictions:
            views.append(qwen_predictions[row.case_id])
        multi = aggregate_views(row, views, method="multi_view_disagreement_guard", **policy)
        never = copy.deepcopy(multi)
        never.method = "never_use_evidence"
        always = infer_evidence_tuple(row, method="always_use_evidence")
        gated = evidence_gated(row, multi, method="evidence_gated_selective_guard")
        provenance = provenance_overlay(row, no_provenance, method="control_provenance_minimal_check")
        full = provenance_overlay(row, gated, method="effect_binding_guard_full")
        output.extend([rule, no_provenance, multi, never, always, gated, provenance, full])
    return output
