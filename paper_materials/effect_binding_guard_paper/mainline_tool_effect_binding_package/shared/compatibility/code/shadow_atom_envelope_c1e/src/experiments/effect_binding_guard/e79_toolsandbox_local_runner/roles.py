"""ToolSandbox roles backed only by a configured localhost model server."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from openai import OpenAI
from tool_sandbox.roles.openai_api_agent import OpenAIAPIAgent
from tool_sandbox.roles.openai_api_user import OpenAIAPIUser


def _client() -> OpenAI:
    base_url = os.environ.get("E79_TOOLSANDBOX_BASE_URL", "http://127.0.0.1:18082/v1")
    if not (base_url.startswith("http://127.0.0.1:") or base_url.startswith("http://localhost:")):
        raise ValueError("E79 ToolSandbox local roles require a localhost base URL")
    return OpenAI(api_key="EMPTY", base_url=base_url)


def _append_usage(role: str, elapsed: float, response: Any) -> None:
    path_text = os.environ.get("E79_TOOLSANDBOX_USAGE_JSONL")
    if not path_text:
        return
    usage = getattr(response, "usage", None)
    row = {
        "role": role,
        "elapsed_seconds": elapsed,
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
        "model": getattr(response, "model", None),
    }
    path = Path(path_text)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


class _LocalMixin:
    model_name = os.environ.get("E79_TOOLSANDBOX_MODEL", "qwen3_32b_local")

    def _local_inference(self, *, messages: list[dict[str, Any]], tools: Any, role: str) -> Any:
        started = time.perf_counter()
        response = self.openai_client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            tools=tools,
            temperature=0.0,
            top_p=1.0,
            max_tokens=int(os.environ.get("E79_TOOLSANDBOX_MAX_TOKENS", "4096")),
        )
        _append_usage(role, time.perf_counter() - started, response)
        return response


class LocalOpenAIAgent(_LocalMixin, OpenAIAPIAgent):
    def __init__(self) -> None:
        self.openai_client = _client()
        self.model_name = os.environ.get("E79_TOOLSANDBOX_MODEL", "qwen3_32b_local")

    def model_inference(self, openai_messages: list[dict[str, Any]], openai_tools: Any) -> Any:
        return self._local_inference(messages=openai_messages, tools=openai_tools, role="agent")


class LocalOpenAIUser(_LocalMixin, OpenAIAPIUser):
    def __init__(self) -> None:
        self.openai_client = _client()
        self.model_name = os.environ.get("E79_TOOLSANDBOX_MODEL", "qwen3_32b_local")

    def model_inference(self, openai_messages: list[dict[str, Any]], openai_tools: Any) -> Any:
        return self._local_inference(messages=openai_messages, tools=openai_tools, role="user_simulator")
