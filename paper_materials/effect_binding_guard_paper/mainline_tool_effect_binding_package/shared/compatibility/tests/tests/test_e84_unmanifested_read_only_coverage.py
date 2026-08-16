from __future__ import annotations

from src.experiments.effect_binding_guard.e81_agentdojo_hardened_runtime.agentdojo_reviewed_runtime_patch import (
    _globally_unprivileged_tools,
)


def test_only_cross_suite_consistent_observations_are_unprivileged() -> None:
    catalog = {
        "suites": {
            "a": {
                "search": {"effectful_or_external": False},
                "send": {"effectful_or_external": True},
                "mixed": {"effectful_or_external": False},
            },
            "b": {
                "search": {"effectful_or_external": False},
                "send": {"effectful_or_external": True},
                "mixed": {"effectful_or_external": True},
            },
        }
    }
    projections = {
        ("a", "search"): {"security_effect_projections": []},
        ("b", "search"): {"security_effect_projections": []},
        ("a", "send"): {
            "security_effect_projections": [{"operation": "write"}]
        },
        ("b", "send"): {
            "security_effect_projections": [{"operation": "write"}]
        },
        ("b", "mixed"): {
            "security_effect_projections": [{"operation": "write"}]
        },
    }
    assert _globally_unprivileged_tools(catalog, projections) == {"search"}


def test_reviewed_read_projection_can_reclassify_registry_false_positive() -> None:
    catalog = {
        "suites": {
            "a": {"lookup": {"effectful_or_external": True}},
            "b": {"lookup": {"effectful_or_external": True}},
        }
    }
    projections = {
        ("a", "lookup"): {
            "security_effect_projections": [{"operation": "read"}]
        },
        ("b", "lookup"): {
            "security_effect_projections": [{"operation": "read"}]
        },
    }
    assert _globally_unprivileged_tools(catalog, projections) == {"lookup"}
