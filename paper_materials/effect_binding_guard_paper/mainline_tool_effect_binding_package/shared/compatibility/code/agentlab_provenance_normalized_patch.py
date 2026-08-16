"""Normalize AgentLAB saved-message provenance for the frozen C1f runtime.

AgentLAB serializes attacker-controlled saved messages as ChatML role blocks
before placing them in sandbox data.  The frozen C1f runtime recognizes
AgentDojo ``<INFORMATION>`` blocks, but not this public serialization format.
This adapter converts only explicit ChatML blocks into the runtime's existing
untrusted-control interface.  It does not inspect labels, attack goals, or
validator outcomes.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import fields, is_dataclass
from typing import Any


CHATML_BLOCK = re.compile(
    r"<\|im_start\|>\s*(?:system|user|assistant|tool)\b(.*?)<\|im_end\|>",
    flags=re.IGNORECASE | re.DOTALL,
)


def _strings(value: Any) -> list[str]:
    seen: set[int] = set()

    def visit(item: Any) -> list[str]:
        if isinstance(item, str):
            return [item]
        if item is None or isinstance(item, (bytes, bytearray, int, float, bool)):
            return []
        identity = id(item)
        if identity in seen:
            return []
        seen.add(identity)
        if isinstance(item, Mapping):
            output: list[str] = []
            for child in item.values():
                output.extend(visit(child))
            return output
        if isinstance(item, Sequence):
            output = []
            for child in item:
                output.extend(visit(child))
            return output
        if is_dataclass(item) and not isinstance(item, type):
            output = []
            for field in fields(item):
                output.extend(visit(getattr(item, field.name)))
            return output
        for method_name in ("model_dump", "dict"):
            method = getattr(item, method_name, None)
            if callable(method):
                try:
                    dumped = method()
                except (TypeError, ValueError, RuntimeError):
                    continue
                if dumped is not item:
                    return visit(dumped)
        try:
            attributes = vars(item)
        except TypeError:
            attributes = None
        return visit(attributes) if isinstance(attributes, Mapping) else []

    return visit(value)


def extract_agentlab_untrusted_control_segments(value: Any) -> list[str]:
    """Extract explicit ChatML payloads emitted by the saved-attack adapter."""
    segments: list[str] = []
    for text in _strings(value):
        segments.extend(match.group(1).strip() for match in CHATML_BLOCK.finditer(text))
    return list(dict.fromkeys(segment for segment in segments if segment))


def install() -> None:
    """Compose ChatML normalization with the frozen runtime extractor."""
    from src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard import (
        agentdojo_e77_runtime_patch as runtime_patch,
    )

    if getattr(runtime_patch, "_E79_AGENTLAB_PROVENANCE_NORMALIZED", False):
        return
    original = runtime_patch.extract_untrusted_control_segments

    def extract(value: Any) -> list[str]:
        combined = [*original(value), *extract_agentlab_untrusted_control_segments(value)]
        return list(dict.fromkeys(segment for segment in combined if segment))

    runtime_patch.extract_untrusted_control_segments = extract
    runtime_patch.RUNTIME_VERSION = f"{runtime_patch.RUNTIME_VERSION}_agentlab_pn_v1"
    runtime_patch._E79_AGENTLAB_PROVENANCE_NORMALIZED = True


install()
