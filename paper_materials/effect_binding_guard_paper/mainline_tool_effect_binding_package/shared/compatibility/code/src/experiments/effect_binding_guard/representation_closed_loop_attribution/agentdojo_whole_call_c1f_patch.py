"""Run a whole-call provenance block in the frozen C1f execution path."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from typing import Any

from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline

from src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard import (
    agentdojo_e77_runtime_patch as e77_patch,
)


ENABLED = "REPRESENTATION_WHOLE_CALL_C1F"
PATCHED = "REPRESENTATION_WHOLE_CALL_C1F_PATCHED"
SUFFIX = "whole_call_c1f_ablation"


def _segments(evidence: Sequence[Any]) -> list[str]:
    return [
        segment
        for row in evidence
        if isinstance(row, Mapping)
        for segment in row.get("untrusted_control_segments", [])
        if isinstance(segment, str) and segment
    ]


def _patch_pipeline_name() -> None:
    original = AgentPipeline.from_config.__func__

    def named(cls: type[AgentPipeline], config: Any) -> AgentPipeline:
        pipeline = original(cls, config)
        name = getattr(pipeline, "name", None) or "local"
        if not name.endswith(f"-{SUFFIX}"):
            pipeline.name = f"{name}-{SUFFIX}"
        return pipeline

    AgentPipeline.from_config = classmethod(named)


if os.getenv(ENABLED) == "1" and os.getenv(PATCHED) != "1":
    original_evaluate = e77_patch.evaluate_atom_envelope

    def whole_call(user_task: str, descriptor: Any, arguments: Any, evidence: Any, **kwargs: Any) -> dict[str, Any]:
        if descriptor.get("side_effectful") and (
            not kwargs.get("registered", True) or not kwargs.get("totalized", True)
        ):
            return original_evaluate(user_task, descriptor, arguments, evidence, **kwargs)
        segments = _segments(evidence)
        if descriptor.get("side_effectful") and segments:
            return {
                "decision": "DENY",
                "reasons": ["whole_call_prior_untrusted_control"],
                "field_checks": [],
                "untrusted_control_segments": len(segments),
                "runtime_called_llm": False,
            }
        return {
            "decision": "ALLOW",
            "reasons": ["whole_call_no_prior_untrusted_control"],
            "field_checks": [],
            "untrusted_control_segments": len(segments),
            "runtime_called_llm": False,
        }

    e77_patch.evaluate_atom_envelope = whole_call
    _patch_pipeline_name()
    os.environ[PATCHED] = "1"
