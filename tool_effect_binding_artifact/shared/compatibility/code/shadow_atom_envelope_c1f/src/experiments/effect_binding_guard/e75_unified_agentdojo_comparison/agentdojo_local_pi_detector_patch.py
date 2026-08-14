"""Patch AgentDojo's built-in PI detector to use the local ProtectAI checkpoint.

AgentDojo v0.1.35 hard-codes the Hugging Face model id for
``transformers_pi_detector``.  The E75 runner uses this module through
``agentdojo.scripts.benchmark --module-to-load`` so the official AgentDojo
pipeline remains otherwise unchanged while avoiding network/cache ambiguity.
"""

from __future__ import annotations

import os
from pathlib import Path

from agentdojo.agent_pipeline import pi_detector


LOCAL_PI_DETECTOR_MODEL = Path(
    os.environ.get(
        "E75_LOCAL_PI_DETECTOR_MODEL",
        "models/protectai_deberta-v3-base-prompt-injection-v2",
    )
)


_original_init = pi_detector.TransformersBasedPIDetector.__init__


def _patched_init(self, model_name: str = "protectai/deberta-v3-base-prompt-injection-v2", *args, **kwargs):
    if model_name == "protectai/deberta-v3-base-prompt-injection-v2" and LOCAL_PI_DETECTOR_MODEL.exists():
        model_name = str(LOCAL_PI_DETECTOR_MODEL)
    return _original_init(self, model_name=model_name, *args, **kwargs)


pi_detector.TransformersBasedPIDetector.__init__ = _patched_init
