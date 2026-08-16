from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace

import pytest


pytest.importorskip("polars")

from tool_sandbox.common.execution_context import ToolBackend, set_current_context
from tool_sandbox.scenarios import named_scenarios

from src.experiments.effect_binding_guard.e79_toolsandbox_local_runner.guard import (
    ToolSandboxEffectGuard,
    trusted_user_transcript,
)


def scenario_context():
    scenario = named_scenarios(preferred_tool_backend=ToolBackend.DEFAULT)["find_days_till_holiday"]
    context = copy.deepcopy(scenario.starting_context)
    set_current_context(context)
    return context


def evidence():
    return {
        "lookup": SimpleNamespace(
            classification="read_only", schema_fields=("query",), schema_required_fields=("query",)
        ),
        "commit": SimpleNamespace(
            classification="effectful", schema_fields=("recipient", "content"),
            schema_required_fields=("recipient", "content"),
        ),
    }


def planner(transcript, registry):
    assert transcript
    assert set(registry) == {"lookup", "commit"}
    return {"task_goal": "test", "tools": {"commit": {"fields": {
        "recipient": {"mode": "resolve", "values": [], "intent": "resolved target"},
        "content": {"mode": "exact", "values": ["hello"], "intent": "message"},
    }}}}


def test_trusted_transcript_excludes_user_simulator_private_few_shots() -> None:
    scenario_context()
    transcript = trusted_user_transcript()
    assert transcript.count("USER_TURN_") == 1
    assert "SYSTEM" not in transcript


def test_read_evidence_can_resolve_effect_and_every_execution_is_precommitted() -> None:
    scenario_context()
    guard = ToolSandboxEffectGuard(evidence(), planner=planner)
    assert guard.invoke("lookup", lambda query: {"recipient": "alice@example.com"}, query="owner")
    committed = []

    def commit(recipient, content):
        committed.append((recipient, content))
        return True

    assert guard.invoke("commit", commit, recipient="alice@example.com", content="hello") is True
    assert committed == [("alice@example.com", "hello")]
    assert guard.precommit_count == guard.executed_effect_count == 1


def test_unresolved_effect_is_rejected_before_callable() -> None:
    scenario_context()
    guard = ToolSandboxEffectGuard(evidence(), planner=planner)
    committed = []
    with pytest.raises(PermissionError, match="NEEDS_REPLAN"):
        guard.invoke(
            "commit", lambda recipient, content: committed.append((recipient, content)),
            recipient="unresolved@example.com", content="hello",
        )
    assert committed == []
    assert guard.precommit_count == 1
    assert guard.executed_effect_count == 0
