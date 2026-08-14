"""Run the frozen C1f path with generic raw-field provenance checks only."""

from __future__ import annotations

import copy
import os
from collections.abc import Mapping, Sequence
from types import SimpleNamespace
from typing import Any, Callable

try:
    from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline
    from src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard import (
        agentdojo_e77_runtime_patch as e77_patch,
    )
except ModuleNotFoundError:
    AgentPipeline = None
    from src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.atom_envelope_policy import (
        evaluate_atom_envelope,
    )

    e77_patch = SimpleNamespace(evaluate_atom_envelope=evaluate_atom_envelope)


ENABLED = "REPRESENTATION_RAW_FIELD_C1F"
PATCHED = "REPRESENTATION_RAW_FIELD_C1F_PATCHED"
SUFFIX = "raw_field_c1f_ablation"


def evaluate_raw_field_envelope(
    original_evaluate: Callable[..., dict[str, Any]],
    user_task: str,
    descriptor: Mapping[str, Any],
    arguments: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
    **kwargs: Any,
) -> dict[str, Any]:
    """Check every concrete argument leaf while discarding effect-label semantics."""
    candidate = copy.deepcopy(dict(descriptor))
    candidate["security_fields"] = sorted(str(field) for field in arguments)
    candidate["field_roles"] = {
        field: "raw_argument" for field in candidate["security_fields"]
    }
    result = original_evaluate(
        user_task,
        candidate,
        arguments,
        evidence,
        **kwargs,
    )
    if result.get("decision") == "ABSTAIN":
        return result

    field_reasons = [
        str(reason)
        for reason in result.get("reasons", [])
        if str(reason).endswith(":untrusted_control_value")
    ]
    result["decision"] = "DENY" if field_reasons else "ALLOW"
    result["reasons"] = field_reasons or [
        "raw_fields_have_no_untrusted_control_value"
    ]
    return result


def _patch_pipeline_name() -> None:
    if AgentPipeline is None:
        return
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

    def raw_field(
        user_task: str,
        descriptor: Any,
        arguments: Any,
        evidence: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return evaluate_raw_field_envelope(
            original_evaluate,
            user_task,
            descriptor,
            arguments,
            evidence,
            **kwargs,
        )

    e77_patch.evaluate_atom_envelope = raw_field
    _patch_pipeline_name()
    os.environ[PATCHED] = "1"
