"""Retrospective policy-view ablation over fixed AgentDojo trajectories."""

from __future__ import annotations

import ast
import importlib.util
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


def _load_frozen_policy():
    root = next(
        parent
        for parent in Path(__file__).resolve().parents
        if (parent / "code/shadow_atom_envelope_c1f").is_dir()
    )
    path = (
        root / "code/shadow_atom_envelope_c1f/src/experiments/effect_binding_guard/"
        "e77_effect_diff_runtime_guard/atom_envelope_policy.py"
    )
    spec = importlib.util.spec_from_file_location("frozen_c1f_atom_envelope_policy", path)
    if not spec or not spec.loader:
        raise ImportError(f"cannot load frozen C1f policy: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_FROZEN_POLICY = _load_frozen_policy()
evaluate_atom_envelope = _FROZEN_POLICY.evaluate_atom_envelope
extract_untrusted_control_segments = _FROZEN_POLICY.extract_untrusted_control_segments


VARIANTS = (
    "no_guard",
    "whole_call_provenance",
    "effect_only",
    "registered_field_c1f",
)


def content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, Sequence) and not isinstance(content, (str, bytes)):
        return "\n".join(
            str(item.get("content", item.get("text", "")))
            if isinstance(item, Mapping)
            else str(item)
            for item in content
        )
    return ""


def parse_tool_call(value: Any) -> dict[str, Any] | None:
    if isinstance(value, str):
        try:
            value = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return None
    return dict(value) if isinstance(value, Mapping) else None


def decide(
    variant: str,
    user_task: str,
    descriptor: Mapping[str, Any],
    arguments: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant: {variant}")
    segments = [
        segment
        for row in evidence
        for segment in row.get("untrusted_control_segments", [])
        if isinstance(segment, str) and segment
    ]
    if variant == "no_guard":
        return {"decision": "ALLOW", "reasons": ["no_guard"]}
    if variant == "whole_call_provenance":
        return {
            "decision": "DENY" if segments else "ALLOW",
            "reasons": ["prior_untrusted_control"] if segments else ["no_untrusted_control"],
        }
    candidate = dict(descriptor)
    if variant == "effect_only":
        candidate["security_fields"] = []
    return evaluate_atom_envelope(user_task, candidate, arguments, evidence)


def evaluate_trajectory(
    payload: Mapping[str, Any],
    descriptors: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    messages = list(payload.get("messages") or [])
    user_task = next(
        content_text(message.get("content"))
        for message in messages
        if isinstance(message, Mapping) and message.get("role") == "user"
    )
    evidence: list[dict[str, Any]] = []
    decisions = {variant: [] for variant in VARIANTS}
    for message in messages:
        if not isinstance(message, Mapping) or message.get("role") != "tool":
            continue
        call = parse_tool_call(message.get("tool_call"))
        if call:
            name = call.get("function")
            arguments = call.get("args")
            if name in descriptors and isinstance(arguments, Mapping):
                for variant in VARIANTS:
                    result = decide(
                        variant,
                        user_task,
                        descriptors[str(name)],
                        arguments,
                        evidence,
                    )
                    decisions[variant].append(
                        {
                            "tool_name": name,
                            "decision": result["decision"],
                            "reasons": result.get("reasons", []),
                        }
                    )
        segments = extract_untrusted_control_segments(content_text(message.get("content")))
        if segments:
            evidence.append({"untrusted_control_segments": segments})

    return {
        "official_utility": bool(payload.get("utility")),
        "official_attack_success": (
            bool(payload.get("security")) if payload.get("injection_task_id") else None
        ),
        "n_effectful_calls": len(decisions["no_guard"]),
        "variants": {
            variant: {
                "would_block": any(row["decision"] != "ALLOW" for row in rows),
                "decisions": rows,
            }
            for variant, rows in decisions.items()
        },
    }
