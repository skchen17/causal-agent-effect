"""Local llama.cpp AgentDojo LLM wrapper with full input/output auditing.

The DeepSeek API runners use OpenAI-native tool calling. A GGUF model loaded
through llama.cpp does not expose that API, so this wrapper renders the
AgentDojo conversation and tool schemas into a text prompt, asks the model to
emit explicit ``<tool_call>{...}</tool_call>`` blocks, parses those blocks back
into AgentDojo ``FunctionCall`` objects, and appends an audit JSONL row for
every local model invocation.
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any, Sequence

from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.functions_runtime import EmptyEnv, Env, FunctionCall, FunctionsRuntime
from agentdojo.types import (
    ChatAssistantMessage,
    ChatMessage,
    ChatUserMessage,
    get_text_content_as_str,
    text_content_block_from_string,
)


DEFAULT_LOCAL_MODEL_PATH = "models/Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf"
TOOL_CALL_RE = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)
JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_LLAMA_CACHE: dict[tuple[str, int, int, int, str], Any] = {}


def _content_to_text(message: ChatMessage) -> str:
    content = message.get("content")
    if content is None:
        return ""
    try:
        return get_text_content_as_str(content)
    except Exception:
        return str(content)


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [_jsonable(v) for v in value]
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump())
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def function_schema(function: Any) -> dict[str, Any]:
    parameters = {}
    try:
        parameters = function.parameters.model_json_schema()
    except Exception:
        parameters = {}
    return {
        "name": function.name,
        "description": getattr(function, "description", "") or "",
        "parameters": parameters,
    }


def load_local_llama(
    *,
    model_path: str,
    n_gpu_layers: int,
    n_ctx: int,
    n_threads: int,
    chat_format: str,
) -> Any:
    resolved = str(Path(model_path).expanduser().resolve())
    key = (resolved, n_gpu_layers, n_ctx, n_threads, chat_format)
    if key in _LLAMA_CACHE:
        return _LLAMA_CACHE[key]
    try:
        from llama_cpp import Llama
    except ImportError as exc:
        raise RuntimeError(
            "llama_cpp is required for --model-backend local. Install "
            "llama-cpp-python in the causal-safety environment before running local GGUF experiments."
        ) from exc
    kwargs: dict[str, Any] = {
        "model_path": resolved,
        "n_gpu_layers": n_gpu_layers,
        "n_ctx": n_ctx,
        "verbose": False,
    }
    if n_threads > 0:
        kwargs["n_threads"] = n_threads
    if chat_format:
        kwargs["chat_format"] = chat_format
    model = Llama(**kwargs)
    _LLAMA_CACHE[key] = model
    return model


def parse_local_tool_calls(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    payloads = [m.group(1) for m in TOOL_CALL_RE.finditer(text)]
    if not payloads:
        payloads = [m.group(1) for m in JSON_BLOCK_RE.finditer(text)]
    if not payloads:
        stripped = text.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            payloads = [stripped]

    calls: list[dict[str, Any]] = []
    for payload in payloads:
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as exc:
            errors.append(f"json_decode_error:{exc.msg}")
            continue
        if isinstance(parsed, dict) and "tool_calls" in parsed:
            entries = parsed.get("tool_calls") or []
        elif isinstance(parsed, list):
            entries = parsed
        else:
            entries = [parsed]
        for entry in entries:
            if not isinstance(entry, dict):
                errors.append("tool_call_entry_not_object")
                continue
            function_name = entry.get("name") or entry.get("tool") or entry.get("function")
            arguments = entry.get("arguments") or entry.get("args") or {}
            if isinstance(function_name, dict):
                arguments = function_name.get("arguments", arguments)
                function_name = function_name.get("name")
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    errors.append("arguments_string_not_json")
                    arguments = {}
            if not isinstance(function_name, str) or not function_name:
                errors.append("missing_tool_name")
                continue
            if not isinstance(arguments, dict):
                errors.append("arguments_not_object")
                arguments = {}
            calls.append({"name": function_name, "arguments": arguments})
    return calls, errors


class LocalLlamaCppAgentDojoLLM(BasePipelineElement):
    """AgentDojo pipeline element backed by a local llama.cpp GGUF model."""

    def __init__(
        self,
        *,
        model_name: str,
        model_path: str = DEFAULT_LOCAL_MODEL_PATH,
        n_gpu_layers: int = -1,
        n_ctx: int = 16384,
        n_threads: int = 0,
        max_tokens: int = 768,
        temperature: float = 0.0,
        chat_format: str = "",
        io_logdir: str = "runs/agentdojo_local_model_io",
        audit_label: str = "agentdojo_local",
        max_prompt_chars: int = 30000,
    ) -> None:
        self.name = model_name
        self.model_name = model_name
        self.model_path = model_path
        self.n_gpu_layers = n_gpu_layers
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.chat_format = chat_format
        self.io_logdir = io_logdir
        self.audit_label = audit_label
        self.max_prompt_chars = max_prompt_chars

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = (),
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, list[ChatMessage], dict]:
        raw_text, audit = self.complete_messages(
            messages=messages,
            runtime=runtime,
            purpose="agent_tool_or_final",
            allow_tool_calls=True,
        )
        parsed_calls, parse_errors = parse_local_tool_calls(raw_text)
        tool_calls = [
            FunctionCall(
                function=call["name"],
                args=call["arguments"],
                id=f"local_call_{uuid.uuid4().hex[:16]}",
            )
            for call in parsed_calls
        ]
        available = {tool.name for tool in runtime.functions.values()}
        unknown = sorted({call.function for call in tool_calls if call.function not in available})
        if unknown:
            parse_errors.extend(f"unknown_tool:{name}" for name in unknown)
        output = ChatAssistantMessage(
            role="assistant",
            content=[text_content_block_from_string(raw_text)] if raw_text else None,
            tool_calls=tool_calls or None,
        )
        audit.update(
            {
                "parsed_tool_calls": [
                    {"function": call.function, "args": _jsonable(call.args), "id": call.id}
                    for call in tool_calls
                ],
                "parse_errors": parse_errors,
                "assistant_message": _jsonable(output),
            }
        )
        self.write_audit(audit)
        return query, runtime, env, [*messages, output], extra_args

    def complete_messages(
        self,
        *,
        messages: Sequence[ChatMessage],
        runtime: FunctionsRuntime,
        purpose: str,
        allow_tool_calls: bool,
        extra_instruction: str = "",
    ) -> tuple[str, dict[str, Any]]:
        tools = [function_schema(f) for f in runtime.functions.values()]
        full_prompt = self.render_prompt(
            messages=messages,
            tools=tools,
            allow_tool_calls=allow_tool_calls,
            extra_instruction=extra_instruction,
        )
        prompt_sent, truncated = self.truncate_prompt(full_prompt)
        started = time.time()
        model = load_local_llama(
            model_path=self.model_path,
            n_gpu_layers=self.n_gpu_layers,
            n_ctx=self.n_ctx,
            n_threads=self.n_threads,
            chat_format=self.chat_format,
        )
        response = model(
            prompt_sent,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        duration = time.time() - started
        raw_text = str(response.get("choices", [{}])[0].get("text", "")).strip()
        audit = {
            "schema_version": "agentdojo_local_model_io_v1",
            "timestamp_unix": started,
            "duration_sec": duration,
            "audit_label": self.audit_label,
            "purpose": purpose,
            "model_backend": "local_llama_cpp",
            "model_name": self.model_name,
            "model_path": str(Path(self.model_path).expanduser().resolve()),
            "generation": {
                "n_gpu_layers": self.n_gpu_layers,
                "n_ctx": self.n_ctx,
                "n_threads": self.n_threads,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "chat_format": self.chat_format,
                "max_prompt_chars": self.max_prompt_chars,
            },
            "available_tools": tools,
            "messages": [_jsonable(m) for m in messages],
            "full_prompt": full_prompt,
            "prompt_sent": prompt_sent,
            "prompt_truncated": truncated,
            "raw_output": raw_text,
            "raw_response": _jsonable(response),
        }
        return raw_text, audit

    def render_prompt(
        self,
        *,
        messages: Sequence[ChatMessage],
        tools: list[dict[str, Any]],
        allow_tool_calls: bool,
        extra_instruction: str = "",
    ) -> str:
        lines = [
            "You are an AgentDojo-compatible tool-using assistant.",
            "Follow the system and user instructions in the conversation.",
            "Use tools when needed to complete the user task.",
            "",
            "Available tools as JSON schema:",
            json.dumps(tools, ensure_ascii=False, indent=2, sort_keys=True),
            "",
            "Tool-call output contract:",
            "When you need a tool, output only one or more blocks in this exact form:",
            "<tool_call>",
            '{"name": "<tool_name>", "arguments": {"arg": "value"}}',
            "</tool_call>",
            "Do not invent tool results. After a tool result appears in the conversation, continue from it.",
        ]
        if not allow_tool_calls:
            lines.append("For this step, do not call tools; answer with plain text only.")
        if extra_instruction:
            lines.extend(["", extra_instruction])
        lines.extend(["", "Conversation transcript:"])
        for idx, message in enumerate(messages):
            role = message.get("role", "unknown")
            text = _content_to_text(message)
            lines.append(f"\n[{idx}] {role.upper()}:")
            if text:
                lines.append(text)
            tool_calls = message.get("tool_calls")
            if tool_calls:
                lines.append("Assistant tool calls already issued:")
                for call in tool_calls:
                    lines.append(json.dumps(_jsonable(call), ensure_ascii=False, sort_keys=True))
            if role == "tool":
                tool_call = message.get("tool_call")
                if tool_call is not None:
                    lines.append(f"Tool call metadata: {json.dumps(_jsonable(tool_call), ensure_ascii=False, sort_keys=True)}")
                if message.get("error"):
                    lines.append(f"Tool error: {message.get('error')}")
        lines.extend(["", "Next assistant message:"])
        return "\n".join(lines)

    def truncate_prompt(self, prompt: str) -> tuple[str, bool]:
        if self.max_prompt_chars <= 0 or len(prompt) <= self.max_prompt_chars:
            return prompt, False
        keep_head = max(2000, self.max_prompt_chars // 3)
        keep_tail = max(2000, self.max_prompt_chars - keep_head)
        truncated = (
            prompt[:keep_head]
            + "\n\n[...prompt truncated for local context window; full prompt is recorded in audit...]\n\n"
            + prompt[-keep_tail:]
        )
        return truncated, True

    def write_audit(self, audit: dict[str, Any]) -> None:
        logdir = Path(self.io_logdir)
        logdir.mkdir(parents=True, exist_ok=True)
        safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "_", self.audit_label).strip("_") or "local"
        path = logdir / f"{safe_label}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(audit, ensure_ascii=False, sort_keys=True, default=str) + "\n")


class LocalLlamaCppToolFilter(BasePipelineElement):
    """AgentDojo tool-filter prompt backed by the local text LLM wrapper."""

    def __init__(self, prompt: str, llm: LocalLlamaCppAgentDojoLLM) -> None:
        self.prompt = prompt
        self.llm = llm

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = (),
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, list[ChatMessage], dict]:
        prompt_msg = ChatUserMessage(role="user", content=[text_content_block_from_string(self.prompt)])
        filter_messages = [*messages, prompt_msg]
        raw_text, audit = self.llm.complete_messages(
            messages=filter_messages,
            runtime=runtime,
            purpose="tool_filter",
            allow_tool_calls=False,
            extra_instruction=(
                "Return only the names of tools from the provided schema that are necessary for the task. "
                "Do not explain."
            ),
        )
        output = ChatAssistantMessage(
            role="assistant",
            content=[text_content_block_from_string(raw_text)] if raw_text else None,
            tool_calls=None,
        )
        selected = {
            tool_name: tool
            for tool_name, tool in runtime.functions.items()
            if raw_text and tool_name in raw_text
        }
        runtime.update_functions(selected)
        audit.update(
            {
                "tool_filter_selected_tools": sorted(selected),
                "assistant_message": _jsonable(output),
            }
        )
        self.llm.write_audit(audit)
        return query, runtime, env, [*filter_messages, output], extra_args


def add_local_model_args(parser: Any) -> None:
    parser.add_argument("--model-backend", choices=("openai", "local"), default="openai")
    parser.add_argument(
        "--local-model-path",
        default=os.environ.get("AGENTDOJO_LOCAL_MODEL_PATH", DEFAULT_LOCAL_MODEL_PATH),
        help="GGUF model path used when --model-backend local.",
    )
    parser.add_argument("--local-n-gpu-layers", type=int, default=int(os.environ.get("AGENTDOJO_LOCAL_N_GPU_LAYERS", "-1")))
    parser.add_argument("--local-n-ctx", type=int, default=int(os.environ.get("AGENTDOJO_LOCAL_N_CTX", "16384")))
    parser.add_argument("--local-n-threads", type=int, default=int(os.environ.get("AGENTDOJO_LOCAL_N_THREADS", "0")))
    parser.add_argument("--local-max-tokens", type=int, default=int(os.environ.get("AGENTDOJO_LOCAL_MAX_TOKENS", "768")))
    parser.add_argument("--local-temperature", type=float, default=float(os.environ.get("AGENTDOJO_LOCAL_TEMPERATURE", "0.0")))
    parser.add_argument("--local-chat-format", default=os.environ.get("AGENTDOJO_LOCAL_CHAT_FORMAT", ""))
    parser.add_argument(
        "--local-max-prompt-chars",
        type=int,
        default=int(os.environ.get("AGENTDOJO_LOCAL_MAX_PROMPT_CHARS", "30000")),
    )
    parser.add_argument(
        "--local-io-logdir",
        default=os.environ.get("AGENTDOJO_LOCAL_IO_LOGDIR", "runs/agentdojo_local_model_io"),
        help="Directory for full local-model input/output JSONL audit logs.",
    )
