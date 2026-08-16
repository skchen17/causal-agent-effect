"""Minimal synchronous MCP stdio client used by disposable source fixtures."""

from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Any


class MCPError(RuntimeError):
    pass


class MCPClient:
    def __init__(self, command: list[str], env: dict[str, str] | None = None, timeout: float = 15.0):
        merged = os.environ.copy()
        if env:
            merged.update(env)
        self.timeout = timeout
        self.process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, env=merged,
        )
        self._next_id = 1
        self._request("initialize", {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "third-party-interface-validator", "version": "1"},
        })
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    def _send(self, value: dict[str, Any]) -> None:
        if self.process.stdin is None:
            raise MCPError("server stdin unavailable")
        self.process.stdin.write(json.dumps(value, separators=(",", ":")) + "\n")
        self.process.stdin.flush()

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout
        if self.process.stdout is None:
            raise MCPError("server stdout unavailable")
        while time.monotonic() < deadline:
            line = self.process.stdout.readline()
            if not line:
                break
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if value.get("id") != request_id:
                continue
            if "error" in value:
                raise MCPError(json.dumps(value["error"], sort_keys=True))
            return value.get("result", {})
        stderr = "" if self.process.stderr is None else self.process.stderr.read()
        raise MCPError(f"timeout/EOF for {method}: {stderr[-2000:]}")

    def list_tools(self) -> list[dict[str, Any]]:
        return self._request("tools/list", {}).get("tools", [])

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise MCPError(json.dumps(result, sort_keys=True))
        return result

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)

    def __enter__(self) -> "MCPClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
