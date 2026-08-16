"""AgentDojo patch for E76 LLM-generated atom descriptor runtime."""

from __future__ import annotations

import hashlib
import json
import os
from ast import literal_eval
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import openai

from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline
from agentdojo.agent_pipeline.llms.google_llm import EMPTY_FUNCTION_NAME
from agentdojo.agent_pipeline.tool_execution import ToolsExecutor, is_string_list
from agentdojo.functions_runtime import EmptyEnv
from agentdojo.types import ChatToolResultMessage, text_content_block_from_string

from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.full_atom_runtime import (
    call_signature,
    compare_call_to_plan,
    descriptor_atom_checks,
    planner_prompt,
)
from src.experiments.effect_binding_guard.e76_llm_descriptor_agentdojo_runtime.llm_descriptor_runtime import (
    PROMPT_VERSION,
    build_llm_descriptor_registry,
    load_registered_descriptor_rows,
    parse_permission_plan_fail_closed,
    should_allow_explicit_override,
)


GUARD_ENV = "E76_LLM_DESCRIPTOR_RUNTIME"
PATCHED_ENV = "E76_LLM_DESCRIPTOR_RUNTIME_PATCHED"
OUTPUT_CAP_PATCHED_ENV = "E76_AGENT_OUTPUT_CAP_PATCHED"


def _enabled() -> bool:
    return os.getenv(GUARD_ENV) == "1"


def _agent_output_max_tokens() -> int:
    return max(1, int(os.getenv("E76_AGENT_MAX_TOKENS", "4096")))


def _patch_agent_output_cap() -> None:
    """Bound AgentDojo local-agent generations to avoid unbounded tails."""
    if os.getenv(OUTPUT_CAP_PATCHED_ENV) == "1":
        return
    from openai.resources.chat.completions import Completions

    original_create = Completions.create

    def capped_create(self: Any, *args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("max_tokens", _agent_output_max_tokens())
        return original_create(self, *args, **kwargs)

    Completions.create = capped_create
    os.environ[OUTPUT_CAP_PATCHED_ENV] = "1"


def _descriptor_path() -> Path:
    value = os.getenv("E76_REGISTERED_DESCRIPTOR_JSONL")
    if not value:
        raise RuntimeError("E76_REGISTERED_DESCRIPTOR_JSONL is required")
    return Path(value)


def _cache_path() -> Path:
    value = os.getenv("E76_PLAN_CACHE")
    return Path(value) if value else Path("runs/e76_llm_descriptor_plan_cache.json")


def _audit_path() -> Path:
    value = os.getenv("E76_AUDIT_JSONL")
    return Path(value) if value else Path("runs/e76_llm_descriptor_runtime_audit.jsonl")


def _load_cache() -> dict[str, Any]:
    path = _cache_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8") or "{}")
    except (OSError, json.JSONDecodeError):
        return {}


def _save_cache(cache: dict[str, Any]) -> None:
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")


def _append_audit(row: dict[str, Any]) -> None:
    path = _audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def _model_plan(query: str, registry: dict[str, dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    prompt = planner_prompt(query, registry)
    max_tokens = int(os.getenv("E76_PLANNER_MAX_TOKENS", "4096"))
    cache_material = json.dumps(
        {"prompt": prompt, "max_tokens": max_tokens, "response_format": "json_object_v1", "prompt_version": PROMPT_VERSION},
        sort_keys=True,
    )
    prompt_hash = hashlib.sha256(cache_material.encode("utf-8")).hexdigest()
    cache = _load_cache()
    if prompt_hash in cache:
        cached = cache[prompt_hash]
        return cached.get("plan"), {"cache_hit": True, "prompt_hash": prompt_hash, **cached.get("diagnostic", {})}

    port = os.getenv("E76_PLANNER_PORT") or os.getenv("LOCAL_LLM_PORT", "8000")
    model = os.getenv("E76_PLANNER_MODEL")
    client = openai.OpenAI(api_key="EMPTY", base_url=f"http://127.0.0.1:{port}/v1")
    if not model:
        model = client.models.list().data[0].id
    diagnostic: dict[str, Any] = {
        "cache_hit": False,
        "prompt_hash": prompt_hash,
        "model": model,
        "prompt_version": PROMPT_VERSION,
    }
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            top_p=1.0,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or ""
        from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.full_atom_runtime import extract_json_object

        parsed = extract_json_object(raw)
        plan = parse_permission_plan_fail_closed(parsed, registry)
        diagnostic.update({"parse_valid": plan is not None, "raw_output_prefix": raw[:600]})
    except Exception as exc:  # noqa: BLE001
        plan = None
        diagnostic.update({"parse_valid": False, "error": repr(exc)})
    cache[prompt_hash] = {"plan": plan, "diagnostic": diagnostic}
    _save_cache(cache)
    return plan, diagnostic


def _feedback(call: Any, comparison: dict[str, Any]) -> ChatToolResultMessage:
    content = (
        "ATOM_RUNTIME_NEEDS_REPLAN: This proposed side effect does not match the LLM-generated, "
        "counterfactually registered atom descriptor and task permission scope. Review the mismatch and "
        "either revise the tool call or explicitly repeat the same call only if it is truly required by the "
        f"original user task. Reasons: {', '.join(comparison['reasons'])}."
    )
    return _tool_result_message(call, content, None)


def _tool_result_message(call: Any, value: str, error: str | None) -> ChatToolResultMessage:
    return ChatToolResultMessage(
        role="tool",
        content=[text_content_block_from_string(value)],
        tool_call_id=call.id,
        tool_call=call,
        error=error,
    )


def _patch_pipeline_name() -> None:
    original = AgentPipeline.from_config.__func__

    def named(cls: type[AgentPipeline], config: Any) -> AgentPipeline:
        pipeline = original(cls, config)
        if _enabled():
            base = getattr(pipeline, "name", None) or "local"
            pipeline.name = f"{base}-ours_llm_descriptor_runtime"
        return pipeline

    AgentPipeline.from_config = classmethod(named)


def _patch_tools_executor() -> None:
    original_query = ToolsExecutor.query

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
        if not messages or messages[-1]["role"] != "assistant":
            return query, runtime, env, messages, extra_args
        calls = messages[-1]["tool_calls"]
        if not calls:
            return query, runtime, env, messages, extra_args

        descriptor_rows = load_registered_descriptor_rows(_descriptor_path())
        registry = build_llm_descriptor_registry(runtime, descriptor_rows)
        state = dict(extra_args.get("e76_llm_descriptor_runtime_state", {}))
        if "plan_initialized" not in state:
            plan, diagnostic = _model_plan(query, registry)
            state.update({"plan_initialized": True, "plan": plan, "planner": diagnostic, "blocked_signatures": []})
            _append_audit({"event": "task_plan", "query_hash": hashlib.sha256(query.encode()).hexdigest(), **diagnostic})

        blocked = set(state.get("blocked_signatures", []))
        results = []
        available = {tool.name for tool in runtime.functions.values()}
        for call in calls:
            if call.function == EMPTY_FUNCTION_NAME or call.function not in available:
                error = "Empty function name." if call.function == EMPTY_FUNCTION_NAME else f"Invalid tool {call.function}."
                results.append(_tool_result_message(call, "", error))
                continue
            for key, value in call.args.items():
                if isinstance(value, str) and is_string_list(value):
                    call.args[key] = literal_eval(value)

            descriptor = registry[call.function]
            signature = call_signature(call.function, call.args)
            descriptor_unregistered = bool(
                descriptor.get("side_effectful") and not descriptor.get("llm_descriptor_registered")
            )
            if descriptor_unregistered:
                comparison = {
                    "decision": "NEEDS_REPLAN",
                    "reasons": ["no_counterfactually_registered_llm_atom_descriptor", *descriptor.get("llm_descriptor_failure", [])],
                    "checks": [],
                }
            else:
                comparison = compare_call_to_plan(query, descriptor, state.get("plan"), call.args)
            # A repeated call may explicitly override a plan mismatch only when
            # the tool has a counterfactually registered descriptor. Missing
            # descriptor coverage is a registration failure, not a replan choice.
            explicit_override = should_allow_explicit_override(
                descriptor_unregistered=descriptor_unregistered,
                signature_blocked=signature in blocked,
                decision=comparison["decision"],
            )
            if not descriptor.get("side_effectful"):
                descriptor_source = "read_only_schema_descriptor"
            elif descriptor.get("llm_descriptor_registered"):
                descriptor_source = "llm_counterfactual_registered"
            else:
                descriptor_source = "unregistered_fail_closed"
            audit = {
                "event": "precommit_check",
                "query_hash": hashlib.sha256(query.encode()).hexdigest(),
                "tool_name": call.function,
                "call_signature": signature,
                "decision": "ALLOW_EXPLICIT_OVERRIDE" if explicit_override else comparison["decision"],
                "reasons": comparison["reasons"],
                "atom_checks": descriptor_atom_checks(descriptor, call.args, comparison),
                "runtime_called_llm": False,
                "descriptor_source": descriptor_source,
            }
            _append_audit(audit)
            if comparison["decision"] == "NEEDS_REPLAN" and not explicit_override:
                blocked.add(signature)
                results.append(_feedback(call, comparison))
                continue

            value, error = runtime.run_function(env, call.function, call.args)
            results.append(_tool_result_message(call, self.output_formatter(value), error))
        state["blocked_signatures"] = sorted(blocked)
        extra_args["e76_llm_descriptor_runtime_state"] = state
        return query, runtime, env, [*messages, *results], extra_args

    ToolsExecutor.query = guarded


if _enabled() and os.getenv(PATCHED_ENV) != "1":
    _patch_agent_output_cap()
    _patch_pipeline_name()
    _patch_tools_executor()
    os.environ[PATCHED_ENV] = "1"
