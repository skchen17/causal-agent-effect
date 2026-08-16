"""Pure runtime ablation kernel for the final common protocol."""

from .kernel import ABLATIONS, AblationConfig, compare_under_ablation, config_diff

__all__ = ["ABLATIONS", "AblationConfig", "compare_under_ablation", "config_diff"]
