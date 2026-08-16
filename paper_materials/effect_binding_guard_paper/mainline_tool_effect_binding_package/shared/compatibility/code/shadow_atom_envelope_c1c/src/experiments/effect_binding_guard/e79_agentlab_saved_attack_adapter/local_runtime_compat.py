"""Strict E79 compatibility patch for prompt-style local function calling.

AgentDojo's prompt-based ``LocalLLM`` emits textual function tags, so its
``FunctionCall`` objects do not have OpenAI tool-call IDs.  E79 therefore sends
tool results back as user-role observations.  This module also replaces the
vendored helper that previously swallowed API/schema errors and returned an
empty assistant message.
"""

from __future__ import annotations

import os
import random
from typing import Any

from agentdojo.agent_pipeline.llms import local_llm


def _reformat_message(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    return local_llm.reformat_message(message)


def strict_chat_completion_request(
    client: Any,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float | None = 1.0,
    top_p: float | None = 0.9,
) -> str:
    """Call the local server and fail closed on API or empty-output errors."""

    reformatted_messages = [
        {"role": message["role"], "content": _reformat_message(message)}
        for message in messages
    ]
    response = client.chat.completions.create(
        model=model,
        messages=reformatted_messages,
        temperature=temperature,
        top_p=top_p,
        seed=random.randint(0, 1_000_000),
    )
    content = response.choices[0].message.content
    if content is None or not content.strip():
        raise local_llm.InvalidModelOutputError("Local model returned an empty assistant response")
    return content


if os.getenv("E79_STRICT_LOCAL_RUNTIME", "1") == "1":
    local_llm.chat_completion_request = strict_chat_completion_request
