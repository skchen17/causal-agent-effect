"""Candidate-envelope guard for ToolSandbox's trusted multi-turn user channel."""

from __future__ import annotations

import functools
import hashlib
import inspect
import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from openai import OpenAI
from tool_sandbox.common.execution_context import DatabaseNamespace, RoleType, get_current_context
from tool_sandbox.roles.execution_environment import ExecutionEnvironment

from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.full_atom_runtime import (
    extract_json_object,
    parse_permission_plan,
    planner_prompt,
)
from src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.e77_runtime import (
    compare_call_to_plan_with_evidence,
)


def trusted_user_transcript() -> str:
    context = get_current_context()
    rows = context.get_database(
        DatabaseNamespace.SANDBOX,
        drop_sandbox_message_index=False,
        get_all_history_snapshots=True,
    ).select(["sender", "recipient", "content", "visible_to"]).to_dicts()
    messages = [
        str(row["content"])
        for row in rows
        if row["sender"] == RoleType.USER and row["recipient"] == RoleType.AGENT
        and (row["visible_to"] is None or RoleType.AGENT in row["visible_to"])
    ]
    return "\n".join(f"USER_TURN_{index + 1}: {content}" for index, content in enumerate(messages))


def registry_from_evidence(evidence: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    registry = {}
    for name, row in evidence.items():
        effectful = row.classification == "effectful"
        registry[name] = {
            "tool_name": name,
            "description": "",
            "side_effectful": effectful,
            "effect": "native_state_mutation" if effectful else "read_only_observation",
            "operation": name,
            "commit_mode": "commit" if effectful else "read",
            "resource_fields": [],
            "scope_fields": [],
            "security_fields": list(row.schema_fields) if effectful else [],
            "required_fields": list(row.schema_required_fields),
            "field_descriptions": {},
        }
    return registry


class ToolSandboxEffectGuard:
    def __init__(
        self,
        evidence: Mapping[str, Any],
        *,
        planner: Callable[[str, Mapping[str, Mapping[str, Any]]], dict[str, Any] | None] | None = None,
        audit_path: Path | None = None,
    ) -> None:
        self.evidence = dict(evidence)
        self.registry = registry_from_evidence(evidence)
        self.planner = planner or self._model_plan
        self.audit_path = audit_path
        self.plan_cache: dict[str, dict[str, Any] | None] = {}
        self.authorized_read_evidence: list[str] = []
        self.precommit_count = 0
        self.executed_effect_count = 0

    def _append(self, row: dict[str, Any]) -> None:
        if self.audit_path is None:
            return
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    def _model_plan(self, transcript: str, registry: Mapping[str, Mapping[str, Any]]) -> dict[str, Any] | None:
        base_url = os.environ.get("E79_TOOLSANDBOX_BASE_URL", "http://127.0.0.1:18082/v1")
        client = OpenAI(api_key="EMPTY", base_url=base_url)
        prompt = planner_prompt(transcript, registry)
        started = time.perf_counter()
        response = client.chat.completions.create(
            model=os.environ.get("E79_TOOLSANDBOX_MODEL", "qwen3_32b_local"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            top_p=1.0,
            max_tokens=int(os.environ.get("E79_TOOLSANDBOX_MAX_TOKENS", "4096")),
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or ""
        plan = parse_permission_plan(extract_json_object(raw), registry)
        usage = getattr(response, "usage", None)
        self._append({
            "event": "permission_plan",
            "trusted_transcript_sha256": hashlib.sha256(transcript.encode()).hexdigest(),
            "parse_valid": plan is not None,
            "elapsed_seconds": time.perf_counter() - started,
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
        })
        return plan

    def current_plan(self) -> tuple[str, dict[str, Any] | None]:
        transcript = trusted_user_transcript()
        digest = hashlib.sha256(transcript.encode()).hexdigest()
        if digest not in self.plan_cache:
            self.plan_cache[digest] = self.planner(transcript, self.registry)
        return transcript, self.plan_cache[digest]

    @staticmethod
    def _totalized_arguments(tool: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
        bound = inspect.signature(tool).bind(*args, **kwargs)
        bound.apply_defaults()
        return dict(bound.arguments)

    def invoke(self, tool_name: str, tool: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        row = self.evidence[tool_name]
        totalized = self._totalized_arguments(tool, args, kwargs)
        descriptor = self.registry[tool_name]
        if row.classification == "effectful":
            transcript, plan = self.current_plan()
            comparison = compare_call_to_plan_with_evidence(
                transcript, descriptor, plan, totalized, self.authorized_read_evidence
            )
            self.precommit_count += 1
            signature = hashlib.sha256(
                json.dumps({"tool": tool_name, "arguments": totalized}, sort_keys=True, default=str).encode()
            ).hexdigest()
            self._append({
                "event": "precommit_check", "tool_name": tool_name, "call_signature": signature,
                "decision": comparison["decision"],
                "check_fields": sorted({check.get("field", "") for check in comparison.get("checks", [])}),
                "check_statuses": sorted(check.get("status", "") for check in comparison.get("checks", [])),
                "runtime_called_llm": False,
            })
            if comparison["decision"] != "ALLOW":
                statuses = sorted({check.get("status", "unresolved") for check in comparison.get("checks", [])})
                raise PermissionError(
                    "EFFECT_GUARD_NEEDS_REPLAN: this effect is outside or unresolved under the trusted user transcript; "
                    f"revise the call or ask the user. Statuses: {', '.join(statuses) or 'missing_plan'}."
                )
            result = tool(**totalized)
            self.executed_effect_count += 1
            self._append({"event": "effect_executed", "tool_name": tool_name, "call_signature": signature})
            return result
        result = tool(**totalized)
        try:
            rendered = json.dumps(result, sort_keys=True, default=str)
        except (TypeError, ValueError):
            rendered = repr(result)
        if rendered:
            self.authorized_read_evidence.append(rendered[:12000])
            self.authorized_read_evidence = self.authorized_read_evidence[-20:]
        return result

    def patch_console(self) -> None:
        console = get_current_context().interactive_console
        for tool_name in self.evidence:
            current = console.locals.get(tool_name)
            if not callable(current) or getattr(current, "_e79_effect_guard_wrapped", False):
                continue

            @functools.wraps(current)
            def wrapped(*args: Any, __name: str = tool_name, __tool: Callable[..., Any] = current, **kwargs: Any) -> Any:
                return self.invoke(__name, __tool, *args, **kwargs)

            wrapped._e79_effect_guard_wrapped = True  # type: ignore[attr-defined]
            console.locals[tool_name] = wrapped


class GuardedExecutionEnvironment(ExecutionEnvironment):
    def __init__(self, guard: ToolSandboxEffectGuard) -> None:
        super().__init__()
        self.guard = guard

    def respond(self, ending_index: int | None = None) -> None:
        self.guard.patch_console()
        super().respond(ending_index=ending_index)
        self.guard.patch_console()
