from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMResponse:
    status: str
    text: str
    backend: str
    model: str
    error: str = ""


class CompletionBackend(Protocol):
    backend_name: str
    model: str

    def health(self) -> tuple[bool, str]:
        ...

    def complete(self, prompt: str) -> LLMResponse:
        ...


class UnavailableBackend:
    backend_name = "none"
    model = ""

    def __init__(self, reason: str = "E62_LOCAL_LLM_BACKEND is unset or none") -> None:
        self.reason = reason

    def health(self) -> tuple[bool, str]:
        return False, self.reason

    def complete(self, prompt: str) -> LLMResponse:
        return LLMResponse("not_executed", "", self.backend_name, self.model, self.reason)


class StaticBackend:
    def __init__(self, responses: dict[str, str], *, backend_name: str = "static", model: str = "test-double") -> None:
        self.responses = responses
        self.backend_name = backend_name
        self.model = model

    def health(self) -> tuple[bool, str]:
        return True, "static backend"

    def complete(self, prompt: str) -> LLMResponse:
        for key, value in self.responses.items():
            if key in prompt:
                return LLMResponse("ok", value, self.backend_name, self.model)
        return LLMResponse("ok", next(iter(self.responses.values()), "{}"), self.backend_name, self.model)


class OllamaBackend:
    backend_name = "ollama"

    def __init__(
        self,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
        timeout: int = 240,
        max_tokens: int = 4096,
        response_format: str = "json_object",
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.response_format = response_format

    def health(self) -> tuple[bool, str]:
        try:
            request_json(f"{self.base_url}/api/tags", {}, method="GET", timeout=10)
            return True, "ollama reachable"
        except Exception as exc:  # pragma: no cover - depends on local service
            return False, f"ollama unavailable: {exc}"

    def complete(self, prompt: str) -> LLMResponse:
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0, "num_predict": self.max_tokens, "stop": ["</FINAL_JSON>"]},
            }
            if self.response_format == "json_object":
                payload["format"] = "json"
            response = request_json(f"{self.base_url}/api/generate", payload, timeout=self.timeout)
            return LLMResponse("ok", str(response.get("response", "")), self.backend_name, self.model)
        except Exception as exc:  # pragma: no cover - depends on local service
            return LLMResponse("error", "", self.backend_name, self.model, str(exc))


class OpenAICompatibleBackend:
    backend_name = "openai_compatible"

    def __init__(
        self,
        model: str,
        base_url: str,
        timeout: int = 240,
        max_tokens: int = 4096,
        response_format: str = "json_object",
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.response_format = response_format
        self.api_key = (
            os.environ.get("E62_LOCAL_LLM_API_KEY", "").strip()
            or os.environ.get("E63_LOCAL_LLM_API_KEY", "").strip()
            or os.environ.get("OPENAI_API_KEY", "").strip()
        )

    def health(self) -> tuple[bool, str]:
        try:
            request_json(f"{self.base_url}/models", {}, method="GET", timeout=10, api_key=self.api_key)
            return True, "openai-compatible endpoint reachable"
        except Exception as exc:  # pragma: no cover - depends on local service
            return False, f"openai-compatible endpoint unavailable: {exc}"

    def complete(self, prompt: str) -> LLMResponse:
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Use no-think mode if supported. Return exactly one JSON object and no markdown. "
                            "If a non-JSON runtime forces a thinking block, keep it brief and put the final "
                            "object between <FINAL_JSON> and </FINAL_JSON>."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
                "max_tokens": self.max_tokens,
                "stop": ["</FINAL_JSON>"],
                "stream": False,
            }
            if self.response_format == "json_object":
                payload["response_format"] = {"type": "json_object"}
            response = request_json(f"{self.base_url}/chat/completions", payload, timeout=self.timeout, api_key=self.api_key)
            content = response["choices"][0]["message"]["content"]
            return LLMResponse("ok", str(content), self.backend_name, self.model)
        except Exception as exc:  # pragma: no cover - depends on local service
            return LLMResponse("error", "", self.backend_name, self.model, str(exc))


def backend_from_env() -> CompletionBackend:
    backend = os.environ.get("E62_LOCAL_LLM_BACKEND", "none").strip().lower() or "none"
    model = os.environ.get("E62_LOCAL_LLM_MODEL", "").strip()
    base_url = os.environ.get("E62_LOCAL_LLM_BASE_URL", "").strip()
    max_tokens = int(os.environ.get("E62_LOCAL_LLM_MAX_TOKENS", "4096"))
    timeout = int(os.environ.get("E62_LOCAL_LLM_TIMEOUT", "240"))
    response_format = os.environ.get("E62_LOCAL_LLM_RESPONSE_FORMAT", "json_object").strip().lower()
    if backend == "none":
        return UnavailableBackend()
    if not model:
        return UnavailableBackend("E62_LOCAL_LLM_MODEL is required for local LLM execution")
    if backend == "ollama":
        return OllamaBackend(
            model,
            base_url or "http://127.0.0.1:11434",
            timeout=timeout,
            max_tokens=max_tokens,
            response_format=response_format,
        )
    if backend == "openai_compatible":
        if not base_url:
            return UnavailableBackend("E62_LOCAL_LLM_BASE_URL is required for openai_compatible")
        return OpenAICompatibleBackend(
            model,
            base_url,
            timeout=timeout,
            max_tokens=max_tokens,
            response_format=response_format,
        )
    return UnavailableBackend(f"Unsupported E62_LOCAL_LLM_BACKEND={backend}")


def request_json(url: str, payload: dict, *, method: str = "POST", timeout: int = 120, api_key: str = "") -> dict:
    data = None if method == "GET" else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # pragma: no cover - depends on local service
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
