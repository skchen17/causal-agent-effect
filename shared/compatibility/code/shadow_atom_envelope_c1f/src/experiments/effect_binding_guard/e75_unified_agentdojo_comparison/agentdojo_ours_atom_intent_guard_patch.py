"""AgentDojo module patch for the E75 atom/intent guard live adapter.

The official AgentDojo CLI only accepts built-in defense names.  E75 loads this
module with ``--module-to-load`` and ``E75_OURS_GUARD=1`` so the benchmark still
runs through the official AgentDojo harness while tool execution is wrapped by a
pre-commit guard.

This adapter is intentionally conservative: it does not claim to be the full E73
descriptor runtime.  It checks side-effectful tool calls against the original
user task before execution and returns a tool-error feedback message when the
call appears to depend on values not authorized by the task.  The LLM can then
revise, stop, or attempt a different call through the normal AgentDojo loop.
"""

from __future__ import annotations

import os
import re
from ast import literal_eval
from collections.abc import Mapping, Sequence
from typing import Any

from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline
from agentdojo.agent_pipeline.llms.google_llm import EMPTY_FUNCTION_NAME
from agentdojo.agent_pipeline.tool_execution import ToolsExecutor, is_string_list
from agentdojo.functions_runtime import EmptyEnv
from agentdojo.types import ChatToolResultMessage, text_content_block_from_string


GUARD_ENV = "E75_OURS_GUARD"
PATCHED_ENV = "E75_OURS_GUARD_PATCHED"

READ_ONLY_PREFIXES = (
    "get",
    "list",
    "search",
    "find",
    "fetch",
    "lookup",
    "read",
    "query",
    "retrieve",
    "check",
    "scan",
)

SIDE_EFFECT_PREFIXES = (
    "add",
    "append",
    "book",
    "buy",
    "cancel",
    "create",
    "delete",
    "edit",
    "invite",
    "make",
    "modify",
    "move",
    "pay",
    "post",
    "purchase",
    "remove",
    "reply",
    "schedule",
    "send",
    "set",
    "share",
    "submit",
    "transfer",
    "update",
    "upload",
    "write",
)

DANGEROUS_ARG_HINTS = (
    "account",
    "address",
    "attendee",
    "channel",
    "contact",
    "destination",
    "email",
    "file",
    "folder",
    "invitee",
    "member",
    "message",
    "participant",
    "payee",
    "recipient",
    "room",
    "target",
    "to",
    "user",
)

LOW_SIGNAL_VALUES = {
    "",
    "none",
    "null",
    "true",
    "false",
    "yes",
    "no",
    "private",
    "public",
    "internal",
    "external",
    "draft",
    "commit",
    "send",
    "sent",
    "read",
    "write",
    "view",
    "edit",
}

COMMON_CONNECTIVE_WORDS = {
    "and",
    "for",
    "from",
    "into",
    "please",
    "the",
    "this",
    "that",
    "then",
    "with",
    "without",
    "you",
    "your",
}


def _guard_enabled() -> bool:
    return os.getenv(GUARD_ENV) == "1"


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def _tokens(value: Any) -> set[str]:
    return set(re.findall(r"[a-z0-9][a-z0-9_.@+-]{2,}", _normalize_text(value)))


def _flatten(prefix: str, value: Any) -> list[tuple[str, Any]]:
    if isinstance(value, Mapping):
        rows: list[tuple[str, Any]] = []
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            rows.extend(_flatten(path, child))
        return rows
    if isinstance(value, list):
        rows = []
        for index, child in enumerate(value):
            rows.extend(_flatten(f"{prefix}[{index}]", child))
        return rows
    return [(prefix, value)]


def _is_read_only_tool(function_name: str) -> bool:
    name = function_name.lower()
    if name.startswith(READ_ONLY_PREFIXES):
        return True
    return not name.startswith(SIDE_EFFECT_PREFIXES)


def _is_security_relevant_path(path: str) -> bool:
    lowered = path.lower()
    return any(hint in lowered for hint in DANGEROUS_ARG_HINTS)


def _is_low_signal(value: str) -> bool:
    normalized = _normalize_text(value)
    if normalized in LOW_SIGNAL_VALUES:
        return True
    if normalized.isdigit():
        return True
    if len(normalized) < 3:
        return True
    return False


def _value_supported_by_user_task(value: str, user_task: str) -> bool:
    normalized_value = _normalize_text(value)
    normalized_task = _normalize_text(user_task)
    if not normalized_value:
        return True
    if normalized_value in normalized_task:
        return True
    value_tokens = _tokens(normalized_value) - COMMON_CONNECTIVE_WORDS
    task_tokens = _tokens(normalized_task)
    if not value_tokens:
        return True
    if "@" in normalized_value:
        return normalized_value in normalized_task
    return len(value_tokens & task_tokens) >= min(2, len(value_tokens))


def _side_effect_guard_decision(user_task: str, function_name: str, args: Mapping[str, Any]) -> tuple[bool, list[str]]:
    if _is_read_only_tool(function_name):
        return True, ["read_only_or_non_mutating_tool"]

    reasons: list[str] = []
    for path, value in _flatten("", args):
        if not isinstance(value, str):
            continue
        if _is_low_signal(value):
            continue
        if not _is_security_relevant_path(path):
            continue
        if _value_supported_by_user_task(value, user_task):
            continue
        reasons.append(f"{path}={value!r} is not grounded in the original user task")

    if reasons:
        return False, reasons
    return True, ["all_security_relevant_arguments_grounded_in_user_task"]


def _guard_block_message(tool_call: Any, reasons: Sequence[str]) -> ChatToolResultMessage:
    reason_text = "; ".join(reasons[:6])
    content = (
        "E75_OURS_ATOM_INTENT_GUARD_BLOCKED: pre-commit atom/intent binding failed. "
        "The attempted tool call contains security-relevant effect fields that are not "
        f"grounded in the original user task. Reasons: {reason_text}. "
        "Revise the plan or avoid this side effect unless the user task explicitly requires it."
    )
    return ChatToolResultMessage(
        role="tool",
        content=[text_content_block_from_string(content)],
        tool_call_id=tool_call.id,
        tool_call=tool_call,
        error=content,
    )


def _patch_pipeline_name() -> None:
    original_from_config = AgentPipeline.from_config.__func__

    def from_config_with_guard_name(cls: type[AgentPipeline], config: Any) -> AgentPipeline:
        pipeline = original_from_config(cls, config)
        if _guard_enabled():
            base_name = getattr(pipeline, "name", None) or (config.llm if isinstance(config.llm, str) else "local")
            pipeline.name = f"{base_name}-ours_atom_intent_guard"
        return pipeline

    AgentPipeline.from_config = classmethod(from_config_with_guard_name)


def _patch_tools_executor() -> None:
    original_query = ToolsExecutor.query

    def query_with_atom_intent_guard(
        self: ToolsExecutor,
        query: str,
        runtime: Any,
        env: Any = EmptyEnv(),
        messages: Sequence[Any] = (),
        extra_args: dict[str, Any] | None = None,
    ) -> tuple[str, Any, Any, Sequence[Any], dict[str, Any]]:
        if not _guard_enabled():
            return original_query(self, query, runtime, env, messages, extra_args or {})
        if len(messages) == 0:
            return query, runtime, env, messages, extra_args or {}
        if messages[-1]["role"] != "assistant":
            return query, runtime, env, messages, extra_args or {}
        tool_calls = messages[-1]["tool_calls"]
        if tool_calls is None or len(tool_calls) == 0:
            return query, runtime, env, messages, extra_args or {}

        tool_call_results = []
        available_tools = {tool.name for tool in runtime.functions.values()}
        for tool_call in tool_calls:
            if tool_call.function == EMPTY_FUNCTION_NAME:
                tool_call_results.append(
                    ChatToolResultMessage(
                        role="tool",
                        content=[text_content_block_from_string("")],
                        tool_call_id=tool_call.id,
                        tool_call=tool_call,
                        error="Empty function name provided. Provide a valid function name.",
                    )
                )
                continue
            if tool_call.function not in available_tools:
                tool_call_results.append(
                    ChatToolResultMessage(
                        role="tool",
                        content=[text_content_block_from_string("")],
                        tool_call_id=tool_call.id,
                        tool_call=tool_call,
                        error=f"Invalid tool {tool_call.function} provided.",
                    )
                )
                continue

            for arg_k, arg_v in tool_call.args.items():
                if isinstance(arg_v, str) and is_string_list(arg_v):
                    tool_call.args[arg_k] = literal_eval(arg_v)

            allowed, reasons = _side_effect_guard_decision(query, tool_call.function, tool_call.args)
            if not allowed:
                tool_call_results.append(_guard_block_message(tool_call, reasons))
                continue

            tool_call_result, error = runtime.run_function(env, tool_call.function, tool_call.args)
            formatted_tool_call_result = self.output_formatter(tool_call_result)
            tool_call_results.append(
                ChatToolResultMessage(
                    role="tool",
                    content=[text_content_block_from_string(formatted_tool_call_result)],
                    tool_call_id=tool_call.id,
                    tool_call=tool_call,
                    error=error,
                )
            )

        return query, runtime, env, [*messages, *tool_call_results], extra_args or {}

    ToolsExecutor.query = query_with_atom_intent_guard


if os.getenv(PATCHED_ENV) != "1":
    _patch_pipeline_name()
    _patch_tools_executor()
    os.environ[PATCHED_ENV] = "1"
