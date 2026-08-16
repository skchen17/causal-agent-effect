"""Replace E77 atom-field comparison with a tool-call-level comparator.

Load this module after ``agentdojo_e77_runtime_patch``. It changes one module
global used by the already-installed runtime wrapper and appends an explicit
pipeline suffix so result logs cannot be confused with the atom-level run.
"""

from __future__ import annotations

import os
from typing import Any

from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline

from src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard import (
    agentdojo_e77_runtime_patch as e77_patch,
)

from .semantics import tool_call_level_compare


ENABLED_ENV = "REPRESENTATION_TOOL_CALL_ABLATION"
PATCHED_ENV = "REPRESENTATION_TOOL_CALL_ABLATION_PATCHED"
PIPELINE_SUFFIX = "tool_call_representation_ablation"


def _patch_pipeline_name() -> None:
    original = AgentPipeline.from_config.__func__

    def named(cls: type[AgentPipeline], config: Any) -> AgentPipeline:
        pipeline = original(cls, config)
        name = getattr(pipeline, "name", None) or "local"
        if not name.endswith(f"-{PIPELINE_SUFFIX}"):
            pipeline.name = f"{name}-{PIPELINE_SUFFIX}"
        return pipeline

    AgentPipeline.from_config = classmethod(named)


if os.getenv(ENABLED_ENV) == "1" and os.getenv(PATCHED_ENV) != "1":
    if os.getenv(e77_patch.GUARD_ENV) != "1":
        raise RuntimeError("tool-call ablation must be loaded after enabled E77 runtime")
    e77_patch.compare_call_to_plan_with_evidence = tool_call_level_compare
    _patch_pipeline_name()
    os.environ[PATCHED_ENV] = "1"
