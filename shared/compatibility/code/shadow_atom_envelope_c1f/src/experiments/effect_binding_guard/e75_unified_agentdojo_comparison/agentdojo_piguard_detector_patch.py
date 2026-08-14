"""Patch AgentDojo's PI detector to use the public PIGuard checkpoint.

This module is loaded through ``agentdojo.scripts.benchmark --module-to-load``.
It keeps the AgentDojo detector placement unchanged and only swaps the
underlying text-classification model.  The resulting row is an adapted
same-protocol AgentDojo live detector baseline, not a reproduction of PIGuard's
original evaluation protocol.
"""

from __future__ import annotations

import os
from typing import Literal

from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline
from agentdojo.agent_pipeline import pi_detector


PIGUARD_MODEL = os.environ.get("E75_PIGUARD_MODEL", "leolee99/PIGuard")
PIGUARD_SAFE_LABEL = os.environ.get("E75_PIGUARD_SAFE_LABEL", "benign")
PIGUARD_THRESHOLD = float(os.environ.get("E75_PIGUARD_THRESHOLD", "0.5"))
PIGUARD_ENV = "E75_PIGUARD"
PATCHED_ENV = "E75_PIGUARD_PATCHED"


def _patched_init(
    self,
    model_name: str = "protectai/deberta-v3-base-prompt-injection-v2",
    safe_label: str = "SAFE",
    threshold: float = 0.5,
    mode: Literal["message", "full_conversation"] = "message",
    raise_on_injection: bool = False,
) -> None:
    try:
        import torch  # type: ignore
        from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised in the AgentDojo runtime environment.
        raise ImportError(
            "PIGuard detector requires transformers and torch in the AgentDojo environment."
        ) from exc

    pi_detector.PromptInjectionDetector.__init__(
        self,
        mode=mode,
        raise_on_injection=raise_on_injection,
    )
    self.model_name = PIGUARD_MODEL
    self.safe_label = PIGUARD_SAFE_LABEL
    self.threshold = PIGUARD_THRESHOLD
    tokenizer = AutoTokenizer.from_pretrained(PIGUARD_MODEL, model_max_length=2048)
    model = AutoModelForSequenceClassification.from_pretrained(PIGUARD_MODEL, trust_remote_code=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    self.pipeline = pipeline(
        "text-classification",
        model=model,
        tokenizer=tokenizer,
        truncation=True,
        device=device,
    )


pi_detector.TransformersBasedPIDetector.__init__ = _patched_init


def _patch_pipeline_name() -> None:
    original_from_config = AgentPipeline.from_config.__func__

    def from_config_with_piguard_name(cls: type[AgentPipeline], config):
        pipeline = original_from_config(cls, config)
        if os.getenv(PIGUARD_ENV) == "1":
            base_name = getattr(pipeline, "name", None) or (config.llm if isinstance(config.llm, str) else "local")
            pipeline.name = f"{base_name}-piguard"
        return pipeline

    AgentPipeline.from_config = classmethod(from_config_with_piguard_name)


if os.getenv(PATCHED_ENV) != "1":
    _patch_pipeline_name()
    os.environ[PATCHED_ENV] = "1"
