"""Run the frozen C1f policy with effect labels but no registered fields."""

from __future__ import annotations

import copy
import os
from typing import Any

from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline

from src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard import (
    agentdojo_e77_runtime_patch as e77_patch,
)


ENABLED = "REPRESENTATION_EFFECT_ONLY_C1F"
PATCHED = "REPRESENTATION_EFFECT_ONLY_C1F_PATCHED"
SUFFIX = "effect_only_c1f_ablation"


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

    def effect_only(user_task: str, descriptor: Any, arguments: Any, evidence: Any, **kwargs: Any) -> dict[str, Any]:
        candidate = copy.deepcopy(dict(descriptor))
        candidate["security_fields"] = []
        candidate["field_roles"] = {}
        return original_evaluate(user_task, candidate, arguments, evidence, **kwargs)

    e77_patch.evaluate_atom_envelope = effect_only
    _patch_pipeline_name()
    os.environ[PATCHED] = "1"
