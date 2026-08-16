from __future__ import annotations

import hashlib

from src.experiments.effect_binding_guard.e81_agentdojo_hardened_runtime import (
    agentdojo_reviewed_runtime_patch as patch,
)


def test_reviewed_runtime_state_is_independently_indexed() -> None:
    state = patch._load_runtime_state()
    assert len(state["by_task_hash"]) == 26
    assert len(state["registry_hash"]) == 64
    assert sum(bool(interface.resolver_specs) for interface in state["by_task_hash"].values()) == 1


def test_reviewed_task_hash_resolves_but_unreviewed_task_does_not() -> None:
    state = patch._load_runtime_state()
    interface = next(iter(state["by_task_hash"].values()))
    assert state["by_task_hash"][interface.original_task_sha256] is interface
    assert hashlib.sha256(b"not a reviewed task").hexdigest() not in state["by_task_hash"]


def test_effectful_classification_comes_from_frozen_runtime_catalog() -> None:
    state = patch._load_runtime_state()
    send_email = patch._suite_tool(state["catalog"], "workspace", "send_email")
    search_files = patch._suite_tool(state["catalog"], "workspace", "search_files")
    assert patch._is_effectful(send_email) is True
    assert patch._is_effectful(search_files) is False
    assert patch._is_reviewed_observation_only(
        state["projection_index"], "slack", "get_webpage"
    ) is True
    assert patch._is_reviewed_observation_only(
        state["projection_index"], "slack", "send_direct_message"
    ) is False
