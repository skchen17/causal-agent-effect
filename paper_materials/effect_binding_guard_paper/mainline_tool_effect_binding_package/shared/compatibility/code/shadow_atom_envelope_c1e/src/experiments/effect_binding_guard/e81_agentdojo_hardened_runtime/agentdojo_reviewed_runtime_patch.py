"""AgentDojo pre-commit patch backed only by independently reviewed manifests."""

from __future__ import annotations

import hashlib
import json
import os
from ast import literal_eval
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline
from agentdojo.agent_pipeline.llms.google_llm import EMPTY_FUNCTION_NAME
from agentdojo.agent_pipeline.tool_execution import ToolsExecutor, is_string_list
from agentdojo.functions_runtime import EmptyEnv
from agentdojo.types import ChatToolResultMessage, text_content_block_from_string

from .runtime import mediate_reviewed_agentdojo_call
from .trusted_interface import build_typed_resolver_ledger_entry, compile_trusted_interface


GUARD_ENV = "E84_REVIEWED_AUTHORITY_RUNTIME"
PATCHED_ENV = "E84_REVIEWED_AUTHORITY_RUNTIME_PATCHED"
RUNTIME_VERSION = "e84_reviewed_authority_runtime_v2_observation_read_split"


def _enabled() -> bool:
    return os.getenv(GUARD_ENV) == "1"


def _path(name: str, default: str) -> Path:
    return Path(os.getenv(name, default))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _load_runtime_state() -> dict[str, Any]:
    manifest_path = _path(
        "E84_RUNTIME_MANIFESTS",
        "experiments/human-authority-and-causal-validation/evaluation/"
        "authority-manifest-human-review/runtime_ready_trusted_manifests.jsonl",
    )
    catalog_path = _path("E84_RUNTIME_CATALOG", "evaluation/e81_ablation/agentdojo_runtime_catalog.json")
    projections_path = _path(
        "E84_TRUSTED_EFFECT_PROJECTIONS",
        "experiments/human-authority-and-causal-validation/evaluation/"
        "causal-effect-projection-validation-2/trusted_security_effect_projections.jsonl",
    )
    rows = _read_jsonl(manifest_path)
    interfaces = [compile_trusted_interface(row) for row in rows]
    by_task_hash: dict[str, Any] = {}
    for interface in interfaces:
        if interface.original_task_sha256 in by_task_hash:
            raise RuntimeError("duplicate reviewed authority task hash")
        by_task_hash[interface.original_task_sha256] = interface
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    projections = _read_jsonl(projections_path)
    projection_index = {
        (row["suite"], row["tool_name"]): row for row in projections
    }
    globally_unprivileged_tools = _globally_unprivileged_tools(
        catalog,
        projection_index,
    )
    material = {
        "manifests": rows,
        "catalog": catalog,
        "trusted_effect_projections": projections,
        "runtime_version": RUNTIME_VERSION,
    }
    registry_hash = hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()
    return {
        "by_task_hash": by_task_hash,
        "catalog": catalog,
        "projection_index": projection_index,
        "globally_unprivileged_tools": globally_unprivileged_tools,
        "registry_hash": registry_hash,
        "manifest_path": str(manifest_path),
    }


def _globally_unprivileged_tools(
    catalog: dict[str, Any],
    projection_index: dict[tuple[str, str], dict[str, Any]],
) -> set[str]:
    """Return names that are observation-only in every suite where they exist."""
    classifications: dict[str, list[bool]] = {}
    for suite, tools in catalog.get("suites", {}).items():
        for tool_name, tool in tools.items():
            projections = projection_index.get((suite, tool_name), {}).get(
                "security_effect_projections",
                [],
            )
            reviewed_observation_only = bool(projections) and all(
                projection.get("operation") == "read"
                for projection in projections
            )
            unprivileged = (
                not bool(tool.get("effectful_or_external"))
                or reviewed_observation_only
            )
            classifications.setdefault(tool_name, []).append(unprivileged)
    return {
        tool_name
        for tool_name, values in classifications.items()
        if values and all(values)
    }


def _append_audit(row: dict[str, Any]) -> None:
    path = _path("E84_RUNTIME_AUDIT_JSONL", "runs/e84_reviewed_authority_runtime_audit.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def _tool_result(call: Any, value: str, error: str | None = None) -> ChatToolResultMessage:
    return ChatToolResultMessage(
        role="tool",
        content=[text_content_block_from_string(value)],
        tool_call_id=call.id,
        tool_call=call,
        error=error,
    )


def _blocked_result(call: Any, decision: str, reasons: list[str]) -> ChatToolResultMessage:
    payload = {
        "runtime_guard": decision,
        "executed": False,
        "reasons": reasons,
        "instruction": "Revise the tool call to remain within the independently reviewed task authority.",
    }
    return _tool_result(call, json.dumps(payload, sort_keys=True), f"E84_{decision}")


def _suite_tool(catalog: dict[str, Any], suite: str, tool_name: str) -> dict[str, Any] | None:
    return catalog.get("suites", {}).get(suite, {}).get(tool_name)


def _is_effectful(tool: dict[str, Any] | None) -> bool:
    return bool(tool and tool.get("effectful_or_external"))


def _is_reviewed_observation_only(
    projection_index: dict[tuple[str, str], dict[str, Any]], suite: str, tool_name: str
) -> bool:
    row = projection_index.get((suite, tool_name))
    projections = row.get("security_effect_projections", []) if row else []
    return bool(projections) and all(projection.get("operation") == "read" for projection in projections)


def _patch_pipeline_name() -> None:
    original = AgentPipeline.from_config.__func__

    def named(cls: type[AgentPipeline], config: Any) -> AgentPipeline:
        pipeline = original(cls, config)
        if _enabled():
            pipeline.name = f"{getattr(pipeline, 'name', None) or 'local'}-ours_e84_reviewed_authority"
        return pipeline

    AgentPipeline.from_config = classmethod(named)


def _patch_tools_executor() -> None:
    original_query = ToolsExecutor.query
    runtime_state = _load_runtime_state()

    def guarded(
        self: ToolsExecutor,
        query: str,
        runtime: Any,
        env: Any = EmptyEnv(),
        messages: Sequence[Any] = (),
        extra_args: dict[str, Any] | None = None,
    ) -> tuple[str, Any, Any, Sequence[Any], dict[str, Any]]:
        extra_args = extra_args or {}
        if not _enabled():
            return original_query(self, query, runtime, env, messages, extra_args)
        if not messages or messages[-1]["role"] != "assistant" or not messages[-1]["tool_calls"]:
            return query, runtime, env, messages, extra_args

        query_hash = hashlib.sha256(query.encode()).hexdigest()
        interface = runtime_state["by_task_hash"].get(query_hash)
        ledger = list(extra_args.get("e84_typed_resolver_ledger", []))
        available = {tool.name for tool in runtime.functions.values()}
        results = []

        for call in messages[-1]["tool_calls"]:
            if call.function == EMPTY_FUNCTION_NAME or call.function not in available:
                error = "Empty function name." if call.function == EMPTY_FUNCTION_NAME else f"Invalid tool {call.function}."
                results.append(_tool_result(call, "", error))
                continue
            for key, value in call.args.items():
                if isinstance(value, str) and is_string_list(value):
                    call.args[key] = literal_eval(value)

            suite = interface.manifest.task_id.split("/", 1)[0] if interface is not None else ""
            tool_entry = _suite_tool(runtime_state["catalog"], suite, call.function)
            effectful_or_external = _is_effectful(tool_entry)
            observation_only = _is_reviewed_observation_only(
                runtime_state["projection_index"], suite, call.function
            )
            effectful = effectful_or_external and not observation_only
            globally_unprivileged = (
                interface is None
                and call.function in runtime_state["globally_unprivileged_tools"]
            )
            if globally_unprivileged:
                decision = "ALLOW"
                reasons = ["globally_consistent_observation_only_tool"]
            elif interface is None:
                decision = "ABSTAIN"
                reasons = ["independently_reviewed_authority_manifest_unavailable"]
            elif tool_entry is None:
                decision = "ABSTAIN"
                reasons = ["tool_semantics_unavailable"]
            elif effectful:
                mediated = mediate_reviewed_agentdojo_call(
                    original_task=query,
                    suite=suite,
                    tool_name=call.function,
                    arguments=call.args,
                    runtime_catalog=runtime_state["catalog"],
                    interface=interface,
                    resolver_ledger=ledger,
                    registry_hash=runtime_state["registry_hash"],
                )
                decision = mediated["decision"]
                reasons = list(mediated["reasons"])
            else:
                decision = "ALLOW"
                reasons = [
                    "reviewed_sandbox_observation_only"
                    if observation_only
                    else "read_only_tool_call"
                ]

            _append_audit(
                {
                    "event": "precommit_check",
                    "runtime_version": RUNTIME_VERSION,
                    "query_hash": query_hash,
                    "manifest_available": interface is not None,
                    "tool_name": call.function,
                    "decision": decision,
                    "reasons": reasons,
                    "effectful_or_external": effectful_or_external,
                    "reviewed_observation_only": observation_only,
                    "globally_unprivileged_without_manifest": globally_unprivileged,
                    "runtime_called_llm": False,
                    "runtime_executed_tool": decision == "ALLOW",
                    "registry_hash": runtime_state["registry_hash"],
                }
            )
            if decision != "ALLOW":
                results.append(_blocked_result(call, decision, reasons))
                continue

            value, error = runtime.run_function(env, call.function, call.args)
            results.append(_tool_result(call, self.output_formatter(value), error))
            if error is None and interface is not None:
                for spec in interface.resolver_specs.values():
                    entry = build_typed_resolver_ledger_entry(
                        spec,
                        tool_name=call.function,
                        arguments=call.args,
                        result=value,
                    )
                    if entry is not None:
                        ledger.append(entry)
                        _append_audit(
                            {
                                "event": "typed_resolver_evidence",
                                "runtime_version": RUNTIME_VERSION,
                                "query_hash": query_hash,
                                "resolver_id": spec.resolver_id,
                                "read_tool": call.function,
                                "projected_scalar_count": len(entry["values"]),
                                "result_values_logged": False,
                            }
                        )

        extra_args["e84_typed_resolver_ledger"] = ledger[-100:]
        return query, runtime, env, [*messages, *results], extra_args

    ToolsExecutor.query = guarded


if _enabled() and os.getenv(PATCHED_ENV) != "1":
    _patch_pipeline_name()
    _patch_tools_executor()
    os.environ[PATCHED_ENV] = "1"
