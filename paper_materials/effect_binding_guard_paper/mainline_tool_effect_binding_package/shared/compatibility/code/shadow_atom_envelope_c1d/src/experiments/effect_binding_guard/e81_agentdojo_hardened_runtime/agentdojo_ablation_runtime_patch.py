"""AgentDojo patch for the E81 single-switch runtime ablations."""

from __future__ import annotations

import hashlib
import json
import os
from ast import literal_eval
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline
from agentdojo.agent_pipeline.llms.google_llm import EMPTY_FUNCTION_NAME
from agentdojo.agent_pipeline.tool_execution import (
    ToolsExecutionLoop,
    ToolsExecutor,
    is_string_list,
)
from agentdojo.functions_runtime import EmptyEnv
from agentdojo.logging import Logger
from agentdojo.types import (
    ChatAssistantMessage,
    ChatToolResultMessage,
    text_content_block_from_string,
)

from .ablation_runtime import (
    ABLATIONS,
    mediate_reviewed_agentdojo_call_ablation,
)
from .agentdojo_reviewed_runtime_patch import (
    _is_effectful,
    _is_reviewed_observation_only,
    _suite_tool,
)
from .trusted_interface import (
    build_typed_resolver_ledger_entry,
    compile_trusted_interface,
)


GUARD_ENV = "E81_RUNTIME_ABLATION"
ROW_ENV = "E81_ABLATION_ROW"
PATCHED_ENV = "E81_RUNTIME_ABLATION_PATCHED"
RUNTIME_VERSION = "e81_qwen32_single_switch_runtime_v1"


def _enabled() -> bool:
    return os.getenv(GUARD_ENV) == "1"


def _row_id() -> str:
    row_id = os.getenv(ROW_ENV, "A1")
    if row_id not in ABLATIONS:
        raise RuntimeError(f"unsupported E81 ablation row: {row_id}")
    return row_id


def _path(name: str, default: str) -> Path:
    return Path(os.getenv(name, default))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _load_runtime_state() -> dict[str, Any]:
    manifest_path = _path(
        "E81_RUNTIME_MANIFESTS",
        "experiments/human-authority-and-causal-validation/evaluation/"
        "authority-manifest-human-review/runtime_ready_trusted_manifests.jsonl",
    )
    catalog_path = _path(
        "E81_RUNTIME_CATALOG",
        "evaluation/e81_ablation/agentdojo_runtime_catalog.json",
    )
    projections_path = _path(
        "E81_TRUSTED_EFFECT_PROJECTIONS",
        "experiments/human-authority-and-causal-validation/evaluation/"
        "causal-effect-projection-validation-2/trusted_security_effect_projections.jsonl",
    )
    raw_registry_path = _path(
        "E81_RAW_DESCRIPTOR_REGISTRY",
        "experiments/security-analysis-ablation-and-overhead/evaluation/"
        "runtime-mechanism-ablation/a9_raw_descriptor_registry.jsonl",
    )
    rows = _read_jsonl(manifest_path)
    interfaces = [compile_trusted_interface(row) for row in rows]
    by_task_hash = {
        interface.original_task_sha256: interface for interface in interfaces
    }
    if len(by_task_hash) != len(interfaces):
        raise RuntimeError("duplicate reviewed authority task hash")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    projections = _read_jsonl(projections_path)
    raw_registry = _read_jsonl(raw_registry_path)
    raw_by_tool = {row["tool_name"]: row for row in raw_registry}
    if len(raw_by_tool) != len(raw_registry):
        raise RuntimeError("duplicate round-0 descriptor tool")
    projection_index = {
        (row["suite"], row["tool_name"]): row for row in projections
    }
    material = {
        "manifests": rows,
        "catalog": catalog,
        "trusted_effect_projections": projections,
        "raw_registry": raw_registry,
        "runtime_version": RUNTIME_VERSION,
        "ablation_row": _row_id(),
    }
    return {
        "by_task_hash": by_task_hash,
        "catalog": catalog,
        "projection_index": projection_index,
        "raw_by_tool": raw_by_tool,
        "registry_hash": hashlib.sha256(
            json.dumps(material, sort_keys=True).encode()
        ).hexdigest(),
    }


def _append_audit(row: dict[str, Any]) -> None:
    path = _path(
        "E81_RUNTIME_AUDIT_JSONL",
        "runs/e81_runtime_ablation_audit.jsonl",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def _tool_result(
    call: Any, value: str, error: str | None = None
) -> ChatToolResultMessage:
    return ChatToolResultMessage(
        role="tool",
        content=[text_content_block_from_string(value)],
        tool_call_id=call.id,
        tool_call=call,
        error=error,
    )


def _blocked_result(
    call: Any,
    decision: str,
    reasons: list[str],
    *,
    replan_recovery: bool,
) -> ChatToolResultMessage:
    payload = {
        "runtime_guard": decision,
        "executed": False,
        "reasons": reasons,
    }
    if replan_recovery:
        payload["instruction"] = (
            "Revise the tool call to remain within the independently reviewed "
            "task authority."
        )
    else:
        payload["instruction"] = (
            "The call is terminally denied; do not issue another tool call."
        )
    return _tool_result(call, json.dumps(payload, sort_keys=True), f"E81_{decision}")


def _terminal_assistant_message() -> ChatAssistantMessage:
    """Close an A15 trajectory without another model call."""
    return ChatAssistantMessage(
        role="assistant",
        content=[
            text_content_block_from_string(
                "The requested tool call was denied by the runtime policy."
            )
        ],
        tool_calls=[],
    )


def _flatten_scalars(value: Any) -> list[Any]:
    if isinstance(value, Mapping):
        return [
            child
            for item in value.values()
            for child in _flatten_scalars(item)
        ]
    if isinstance(value, (list, tuple)):
        return [child for item in value for child in _flatten_scalars(item)]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return _flatten_scalars(model_dump())
    if value is None or isinstance(value, (str, int, float, bool)):
        return [value]
    return []


def _untrusted_resolver_entries(
    interface: Any,
    *,
    tool_name: str,
    result: Any,
) -> list[dict[str, Any]]:
    """A7 evidence: any observation may populate any resolver by scalar match."""
    values = _flatten_scalars(result)
    if not values:
        return []
    return [
        {
            "resolver_id": resolver_id,
            "values": values[:100],
            "typed_projection": False,
            "provenance": "untyped_tool_output",
            "read_tool": tool_name,
        }
        for resolver_id in interface.resolver_specs
    ]


def _patch_pipeline_name() -> None:
    original = AgentPipeline.from_config.__func__

    def named(cls: type[AgentPipeline], config: Any) -> AgentPipeline:
        pipeline = original(cls, config)
        if _enabled():
            row = ABLATIONS[_row_id()]
            pipeline.name = (
                f"{getattr(pipeline, 'name', None) or 'local'}-"
                f"e81_{row.row_id.lower()}_{row.label}"
            )
        return pipeline

    AgentPipeline.from_config = classmethod(named)


def _patch_tools_executor() -> None:
    original_query = ToolsExecutor.query
    runtime_state = _load_runtime_state()
    row = ABLATIONS[_row_id()]

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
        if (
            not messages
            or messages[-1]["role"] != "assistant"
            or not messages[-1]["tool_calls"]
        ):
            return query, runtime, env, messages, extra_args

        query_hash = hashlib.sha256(query.encode()).hexdigest()
        interface = runtime_state["by_task_hash"].get(query_hash)
        ledger = list(extra_args.get("e81_resolver_ledger", []))
        available = {tool.name for tool in runtime.functions.values()}
        results = []

        for call in messages[-1]["tool_calls"]:
            if call.function == EMPTY_FUNCTION_NAME or call.function not in available:
                error = (
                    "Empty function name."
                    if call.function == EMPTY_FUNCTION_NAME
                    else f"Invalid tool {call.function}."
                )
                results.append(_tool_result(call, "", error))
                continue
            for key, value in call.args.items():
                if isinstance(value, str) and is_string_list(value):
                    call.args[key] = literal_eval(value)

            suite = (
                interface.manifest.task_id.split("/", 1)[0]
                if interface is not None
                else ""
            )
            tool_entry = _suite_tool(
                runtime_state["catalog"], suite, call.function
            )
            effectful_or_external = _is_effectful(tool_entry)
            observation_only = _is_reviewed_observation_only(
                runtime_state["projection_index"], suite, call.function
            )
            effectful = effectful_or_external and not observation_only

            if interface is None:
                decision = "ABSTAIN"
                reasons = ["independently_reviewed_authority_manifest_unavailable"]
                replan_recovery = row.replan_recovery
                checks: list[dict[str, Any]] = []
                switch_applicable = False
                mechanism_detail: dict[str, Any] = {}
            elif tool_entry is None:
                decision = "ABSTAIN"
                reasons = ["tool_semantics_unavailable"]
                replan_recovery = row.replan_recovery
                checks = []
                switch_applicable = False
                mechanism_detail = {}
            elif effectful:
                mediated = mediate_reviewed_agentdojo_call_ablation(
                    row_id=row.row_id,
                    suite=suite,
                    tool_name=call.function,
                    arguments=call.args,
                    runtime_catalog=runtime_state["catalog"],
                    interface=interface,
                    resolver_ledger=ledger,
                    registry_hash=runtime_state["registry_hash"],
                    raw_descriptor=runtime_state["raw_by_tool"].get(
                        call.function
                    ),
                )
                decision = mediated["decision"]
                reasons = list(mediated["reasons"])
                checks = list(mediated.get("checks", []))
                replan_recovery = bool(mediated["replan_recovery"])
                switch_applicable = bool(mediated.get("switch_applicable")) or (
                    row.row_id == "A9"
                ) or (
                    row.row_id == "A15" and decision != "ALLOW"
                )
                mechanism_detail = {
                    key: mediated.get(key)
                    for key in (
                        "round0_descriptor_used",
                        "untyped_evidence_entries_accepted",
                        "untyped_resolver_matches",
                        "authorized_read_grounding_disabled_with_resolvers",
                        "omitted_dynamic_security_fields",
                    )
                    if key in mediated
                }
            else:
                decision = "ALLOW"
                reasons = [
                    "reviewed_sandbox_observation_only"
                    if observation_only
                    else "read_only_tool_call"
                ]
                checks = []
                replan_recovery = row.replan_recovery
                switch_applicable = False
                mechanism_detail = {}

            _append_audit(
                {
                    "event": "precommit_check",
                    "runtime_version": RUNTIME_VERSION,
                    "ablation_row": row.row_id,
                    "ablation_label": row.label,
                    "query_hash": query_hash,
                    "manifest_available": interface is not None,
                    "tool_name": call.function,
                    "decision": decision,
                    "reasons": reasons,
                    "check_count": len(checks),
                    "effectful_or_external": effectful_or_external,
                    "reviewed_observation_only": observation_only,
                    "runtime_called_llm": False,
                    "runtime_executed_tool": decision == "ALLOW",
                    "replan_recovery": replan_recovery,
                    "switch_applicable": switch_applicable,
                    "mechanism_detail": mechanism_detail,
                    "registry_hash": runtime_state["registry_hash"],
                }
            )
            if decision != "ALLOW":
                results.append(
                    _blocked_result(
                        call,
                        decision,
                        reasons,
                        replan_recovery=replan_recovery,
                    )
                )
                if not replan_recovery:
                    extra_args["e81_terminal_denial"] = True
                    break
                continue

            value, error = runtime.run_function(
                env, call.function, call.args
            )
            results.append(_tool_result(call, self.output_formatter(value), error))
            if error is None and interface is not None:
                if row.provenance_control_binding:
                    for spec in interface.resolver_specs.values():
                        entry = build_typed_resolver_ledger_entry(
                            spec,
                            tool_name=call.function,
                            arguments=call.args,
                            result=value,
                        )
                        if entry is not None:
                            ledger.append(entry)
                elif not effectful:
                    ledger.extend(
                        _untrusted_resolver_entries(
                            interface,
                            tool_name=call.function,
                            result=value,
                        )
                    )

        extra_args["e81_resolver_ledger"] = ledger[-100:]
        return query, runtime, env, [*messages, *results], extra_args

    ToolsExecutor.query = guarded


def _patch_terminal_loop() -> None:
    """Stop A15 before the LLM can replan after a blocked call."""
    original_query = ToolsExecutionLoop.query

    def terminal_aware(
        self: ToolsExecutionLoop,
        query: str,
        runtime: Any,
        env: Any = EmptyEnv(),
        messages: Sequence[Any] = (),
        extra_args: dict[str, Any] | None = None,
    ) -> tuple[str, Any, Any, Sequence[Any], dict[str, Any]]:
        extra_args = extra_args or {}
        if not _enabled() or _row_id() != "A15":
            return original_query(self, query, runtime, env, messages, extra_args)
        if not messages:
            raise ValueError(
                "Messages should not be empty when calling ToolsExecutionLoop"
            )
        logger = Logger().get()
        for _ in range(self.max_iters):
            last_message = messages[-1]
            if (
                last_message["role"] != "assistant"
                or not last_message["tool_calls"]
            ):
                break
            for element in self.elements:
                query, runtime, env, messages, extra_args = element.query(
                    query, runtime, env, messages, extra_args
                )
                logger.log(messages)
                if extra_args.get("e81_terminal_denial"):
                    closed = [*messages, _terminal_assistant_message()]
                    logger.log(closed)
                    return query, runtime, env, closed, extra_args
        return query, runtime, env, messages, extra_args

    ToolsExecutionLoop.query = terminal_aware


if _enabled() and os.getenv(PATCHED_ENV) != "1":
    _patch_pipeline_name()
    _patch_tools_executor()
    _patch_terminal_loop()
    os.environ[PATCHED_ENV] = "1"
