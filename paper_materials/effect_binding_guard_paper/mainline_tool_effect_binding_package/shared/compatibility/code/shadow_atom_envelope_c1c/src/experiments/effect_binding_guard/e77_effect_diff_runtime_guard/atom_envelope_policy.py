"""Utility-preserving atom-level control-taint policy.

The policy consumes only a frozen counterfactual descriptor, the original user
task, the concrete tool call, and runtime provenance. It does not infer labels
or call an LLM. Explicitly marked untrusted control text can block a registered
effect or a security-relevant field, while unrelated payload text is ignored.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any


CONTROL_BLOCK = re.compile(
    r"<\s*INFORMATION\s*>(.*?)<\s*/\s*INFORMATION\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)
TOKEN = re.compile(r"[a-z0-9]+")
ACTION_TERMS = {
    "add",
    "append",
    "book",
    "cancel",
    "change",
    "create",
    "delete",
    "invite",
    "modify",
    "pay",
    "post",
    "purchase",
    "remove",
    "schedule",
    "send",
    "share",
    "submit",
    "transfer",
    "update",
    "write",
}
STOP_TERMS = {
    "a",
    "an",
    "and",
    "effect",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "tool",
    "with",
}
PASSIVE_PAYLOAD_ROLES = {"data_payload"}
# Attachments identify disclosed resources even though the current descriptor
# inventory classifies the container as payload.
IDENTITY_BEARING_PAYLOAD_FIELDS = {"attachments"}


@dataclass(frozen=True)
class AtomEnvelopeDecision:
    decision: str
    reasons: tuple[str, ...]
    field_checks: tuple[dict[str, Any], ...]
    untrusted_control_segments: int
    runtime_called_llm: bool = False

    def to_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["reasons"] = list(self.reasons)
        row["field_checks"] = list(self.field_checks)
        return row


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        out: list[str] = []
        for child in value.values():
            out.extend(_strings(child))
        return out
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        out = []
        for child in value:
            out.extend(_strings(child))
        return out
    return []


def extract_untrusted_control_segments(value: Any) -> list[str]:
    """Return explicit AgentDojo-style control blocks without surrounding data."""
    segments: list[str] = []
    for text in _strings(value):
        segments.extend(match.group(1).strip() for match in CONTROL_BLOCK.finditer(text))
    return [segment for segment in segments if segment]


def _normalized(value: Any) -> str:
    text = str(value).casefold().strip()
    text = re.sub(r"https?://", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" \t\r\n.,;:!?\"'")


def _leaves(value: Any) -> list[Any]:
    if isinstance(value, Mapping):
        out: list[Any] = []
        for child in value.values():
            out.extend(_leaves(child))
        return out
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        out = []
        for child in value:
            out.extend(_leaves(child))
        return out
    return [value]


def value_in_control_segments(value: Any, segments: Sequence[str]) -> bool:
    needle = _normalized(value)
    if not needle:
        return False
    for segment in segments:
        haystack = _normalized(segment)
        if len(needle) <= 2 and needle.isalnum():
            if needle in TOKEN.findall(haystack):
                return True
            continue
        if needle in haystack:
            return True
        # URLs and identifiers often differ only in punctuation or scheme.
        needle_tokens = TOKEN.findall(needle)
        if len(needle_tokens) >= 2 and " ".join(needle_tokens) in " ".join(TOKEN.findall(haystack)):
            return True
    return False


def value_grounded_in_task(value: Any, user_task: str) -> bool:
    """Conservative literal grounding used only to avoid false taint."""
    return value_in_control_segments(value, [user_task])


def _inactive(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {} or value == ()


def _effect_terms(descriptor: Mapping[str, Any]) -> set[str]:
    material = " ".join(
        str(descriptor.get(key, ""))
        for key in ("tool_name", "effect_kind")
    )
    return {term for term in TOKEN.findall(material.casefold()) if term not in STOP_TERMS}


def _effect_mentioned(text: str, descriptor: Mapping[str, Any]) -> bool:
    terms = _effect_terms(descriptor)
    observed = set(TOKEN.findall(text.casefold()))
    action_overlap = terms & observed & ACTION_TERMS
    object_overlap = (terms - ACTION_TERMS) & observed
    return bool(action_overlap and object_overlap) or len(terms & observed) >= 3


def evaluate_atom_envelope(
    user_task: str,
    descriptor: Mapping[str, Any],
    arguments: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
    *,
    registered: bool = True,
    totalized: bool = True,
) -> dict[str, Any]:
    """Evaluate a concrete call under the role-sensitive C1c envelope."""
    if descriptor.get("side_effectful") and not registered:
        return AtomEnvelopeDecision(
            "ABSTAIN", ("missing_counterfactual_descriptor",), (), 0
        ).to_dict()
    if not totalized:
        return AtomEnvelopeDecision(
            "ABSTAIN", ("call_totalization_failed",), (), 0
        ).to_dict()
    if not descriptor.get("side_effectful"):
        return AtomEnvelopeDecision("ALLOW", ("read_only_tool",), (), 0).to_dict()

    segments: list[str] = []
    for entry in evidence:
        if not isinstance(entry, Mapping):
            continue
        raw = entry.get("untrusted_control_segments", [])
        if isinstance(raw, list):
            segments.extend(str(item) for item in raw if isinstance(item, str) and item)

    checks: list[dict[str, Any]] = []
    reasons: list[str] = []
    for field in descriptor.get("security_fields", []):
        if field not in arguments:
            continue
        tainted_values = [
            value for value in _leaves(arguments[field])
            if not _inactive(value)
            and value_in_control_segments(value, segments)
            and not value_grounded_in_task(value, user_task)
        ]
        role = descriptor.get("field_roles", {}).get(field, "security_relevant")
        passive_payload = (
            role in PASSIVE_PAYLOAD_ROLES
            and str(field) not in IDENTITY_BEARING_PAYLOAD_FIELDS
        )
        if tainted_values and passive_payload:
            status = "untrusted_payload_data_observed"
        elif tainted_values:
            status = "untrusted_control_value"
        else:
            status = "no_control_taint"
        checks.append(
            {
                "field": str(field),
                "value": arguments[field],
                "role": role,
                "status": status,
                "n_values": len(_leaves(arguments[field])),
                "n_tainted_values": len(tainted_values),
            }
        )
        if tainted_values and not passive_payload:
            reasons.append(f"{field}:untrusted_control_value")

    control_requests_effect = any(_effect_mentioned(segment, descriptor) for segment in segments)
    task_requests_effect = _effect_mentioned(user_task, descriptor)
    if control_requests_effect and not task_requests_effect:
        reasons.append("effect:untrusted_control_expansion")

    if reasons:
        decision = "DENY"
    else:
        decision = "ALLOW"
        reasons.append(
            "registered_effect_has_no_untrusted_control_expansion"
            if segments
            else "registered_effect_without_untrusted_control"
        )
    return AtomEnvelopeDecision(
        decision,
        tuple(reasons),
        tuple(checks),
        len(segments),
    ).to_dict()
