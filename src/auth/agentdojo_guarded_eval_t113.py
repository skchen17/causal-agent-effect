"""T113 future-constrained AgentDojo action-boundary guard.

This pilot evaluates a strict version of the project method on AgentDojo:

1. Run a clean, no-injection shadow trajectory for each user task.
2. Evaluate two action-boundary variants:
   a. prefix_lock: let the attacked agent continue, but only commit tool calls
      matching the next clean shadow step exactly.
   b. replay_commit: do not ask the attacked agent for a second trajectory;
      execute the clean shadow trajectory directly in the injected environment.

This is an oracle/shadow-trajectory pilot, not a deployable compiler result.
It tests whether action-boundary trace locking and two-phase shadow replay can
reduce AgentDojo attack success on real benchmark tasks without destroying
utility.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from ast import literal_eval
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import agentdojo.attacks  # noqa: F401 - registers default attacks
from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, load_system_message
from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.agent_pipeline.basic_elements import InitQuery, SystemMessage
from agentdojo.agent_pipeline.errors import AbortAgentError
from agentdojo.agent_pipeline.tool_execution import (
    ToolsExecutor,
    ToolsExecutionLoop,
    is_string_list,
    tool_result_to_str,
)
from agentdojo.attacks.attack_registry import ATTACKS, load_attack
from agentdojo.base_tasks import BaseInjectionTask, BaseUserTask
from agentdojo.functions_runtime import EmptyEnv, Env, FunctionCall, FunctionReturnType, FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suite, get_suites
from agentdojo.task_suite.task_suite import (
    functions_stack_trace_from_messages,
    model_output_from_messages,
)
from agentdojo.types import (
    ChatMessage,
    ChatToolResultMessage,
    text_content_block_from_string,
)

from agentdojo_real_scenario_eval_t112 import (
    DEFAULT_SUITES,
    OpenAICompatibleSystemLLM,
    mean_bool,
    subset_ids,
    suite_inventory,
)
from agentdojo_local_llm import LocalLlamaCppAgentDojoLLM, add_local_model_args
from openai import OpenAI


@dataclass
class GuardEvent:
    function: str
    args: dict[str, Any]
    decision: str
    expected_next: str | None
    reason: str


@dataclass
class ShadowPrefixPolicy:
    signatures: list[str]
    cursor: int = 0
    events: list[GuardEvent] = field(default_factory=list)

    def decide(self, tool_call: FunctionCall) -> bool:
        sig = call_signature(tool_call)
        expected = self.signatures[self.cursor] if self.cursor < len(self.signatures) else None
        if expected is not None and sig == expected:
            self.events.append(
                GuardEvent(
                    function=tool_call.function,
                    args=dict(tool_call.args),
                    decision="allow",
                    expected_next=expected,
                    reason="matches_next_shadow_step",
                )
            )
            self.cursor += 1
            return True
        self.events.append(
            GuardEvent(
                function=tool_call.function,
                args=dict(tool_call.args),
                decision="block",
                expected_next=expected,
                reason="outside_shadow_prefix",
            )
        )
        return False

    @property
    def allowed_count(self) -> int:
        return sum(e.decision == "allow" for e in self.events)

    @property
    def blocked_count(self) -> int:
        return sum(e.decision == "block" for e in self.events)


class GuardedToolsExecutor(BasePipelineElement):
    """ToolsExecutor variant that enforces a ShadowPrefixPolicy before commit."""

    def __init__(
        self,
        policy: ShadowPrefixPolicy,
        output_formatter=tool_result_to_str,
    ) -> None:
        self.policy = policy
        self.output_formatter = output_formatter

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: list[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, list[ChatMessage], dict]:
        if len(messages) == 0:
            return query, runtime, env, messages, extra_args
        if messages[-1]["role"] != "assistant":
            return query, runtime, env, messages, extra_args
        if messages[-1]["tool_calls"] is None or len(messages[-1]["tool_calls"]) == 0:
            return query, runtime, env, messages, extra_args

        tool_call_results = []
        for tool_call in messages[-1]["tool_calls"]:
            if not self.policy.decide(tool_call):
                tool_call_results.append(
                    ChatToolResultMessage(
                        role="tool",
                        content=[text_content_block_from_string("")],
                        tool_call_id=tool_call.id,
                        tool_call=tool_call,
                        error="AuthorizationGuardBlocked: tool call does not match the clean shadow trajectory.",
                    )
                )
                continue

            if tool_call.function not in (tool.name for tool in runtime.functions.values()):
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
        return query, runtime, env, [*messages, *tool_call_results], extra_args


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-version", default="v1.2.2")
    parser.add_argument("--suite", action="append", dest="suites", default=[])
    parser.add_argument("--attack", default="direct")
    parser.add_argument("--user-task", action="append", dest="user_tasks", default=[])
    parser.add_argument("--injection-task", action="append", dest="injection_tasks", default=[])
    parser.add_argument("--max-user-tasks", type=int, default=2)
    parser.add_argument("--max-injection-tasks", type=int, default=2)
    parser.add_argument("--model", default="deepseek-v4-flash")
    add_local_model_args(parser)
    parser.add_argument(
        "--pipeline-label",
        default="",
        help="Optional AgentDojo pipeline name label. Useful for attacks that require a recognized model-family string such as 'Local model'.",
    )
    parser.add_argument("--base-url", default=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument(
        "--mode",
        choices=("prefix_lock", "replay_commit", "both"),
        default="both",
        help="T113 guard variant to evaluate.",
    )
    parser.add_argument("--output", default="analysis/results/agentdojo_guarded_eval_t113_v1.json")
    parser.add_argument("--output-md", default="analysis/results/agentdojo_guarded_eval_t113_v1.md")
    parser.add_argument("--trace-output", default="data/agentdojo_guarded_eval_t113_v1.jsonl")
    return parser.parse_args()


def normalize_for_signature(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): normalize_for_signature(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, list):
        return [normalize_for_signature(v) for v in value]
    if hasattr(value, "model_dump"):
        return normalize_for_signature(value.model_dump())
    return value


def call_signature(call: FunctionCall) -> str:
    return json.dumps(
        {
            "function": call.function,
            "args": normalize_for_signature(dict(call.args)),
        },
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


def calls_to_records(calls: list[FunctionCall]) -> list[dict[str, Any]]:
    return [{"function": c.function, "args": normalize_for_signature(dict(c.args))} for c in calls]


def clone_call(call: FunctionCall) -> FunctionCall:
    return FunctionCall(
        function=call.function,
        args=json.loads(json.dumps(normalize_for_signature(dict(call.args)), ensure_ascii=False, default=str)),
        id=call.id,
    )


def make_pipeline(
    model: str,
    pipeline_label: str,
    base_url: str,
    api_key_env: str,
    policy: ShadowPrefixPolicy | None = None,
    model_backend: str = "openai",
    local_model_path: str = "",
    local_n_gpu_layers: int = -1,
    local_n_ctx: int = 16384,
    local_n_threads: int = 0,
    local_max_tokens: int = 768,
    local_temperature: float = 0.0,
    local_chat_format: str = "",
    local_io_logdir: str = "runs/agentdojo_local_model_io",
    local_max_prompt_chars: int = 30000,
) -> tuple[AgentPipeline, ShadowPrefixPolicy | None]:
    if model_backend == "openai":
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise RuntimeError(f"Missing {api_key_env}. Set it in the environment.")
        client = OpenAI(api_key=api_key, base_url=base_url)
        llm = OpenAICompatibleSystemLLM(client, model, temperature=0.0)
    elif model_backend == "local":
        llm = LocalLlamaCppAgentDojoLLM(
            model_name=model,
            model_path=local_model_path,
            n_gpu_layers=local_n_gpu_layers,
            n_ctx=local_n_ctx,
            n_threads=local_n_threads,
            max_tokens=local_max_tokens,
            temperature=local_temperature,
            chat_format=local_chat_format,
            io_logdir=local_io_logdir,
            audit_label="t113_t119_shadow_source",
            max_prompt_chars=local_max_prompt_chars,
        )
    else:
        raise ValueError(f"Unsupported model backend: {model_backend}")
    executor: BasePipelineElement
    if policy is None:
        executor = ToolsExecutor(tool_result_to_str)
    else:
        executor = GuardedToolsExecutor(policy, tool_result_to_str)
    pipeline = AgentPipeline(
        [
            SystemMessage(load_system_message(None)),
            InitQuery(),
            llm,
            ToolsExecutionLoop([executor, llm]),
        ]
    )
    pipeline_name = pipeline_label or model
    pipeline.name = (
        f"{pipeline_name}-shadow_prefix_lock_v1" if policy is not None else f"{pipeline_name}-shadow_source"
    )
    return pipeline, policy


def make_pipeline_for_args(
    args: argparse.Namespace,
    policy: ShadowPrefixPolicy | None = None,
) -> tuple[AgentPipeline, ShadowPrefixPolicy | None]:
    return make_pipeline(
        args.model,
        args.pipeline_label,
        args.base_url,
        args.api_key_env,
        policy=policy,
        model_backend=args.model_backend,
        local_model_path=args.local_model_path,
        local_n_gpu_layers=args.local_n_gpu_layers,
        local_n_ctx=args.local_n_ctx,
        local_n_threads=args.local_n_threads,
        local_max_tokens=args.local_max_tokens,
        local_temperature=args.local_temperature,
        local_chat_format=args.local_chat_format,
        local_io_logdir=args.local_io_logdir,
        local_max_prompt_chars=args.local_max_prompt_chars,
    )


def run_task_capture(
    suite,
    pipeline: AgentPipeline,
    task: BaseUserTask | BaseInjectionTask,
    injection_task: BaseInjectionTask | None,
    injections: dict[str, str],
) -> dict[str, Any]:
    environment = suite.load_and_inject_default_environment(injections)
    if isinstance(task, BaseUserTask):
        task_environment = task.init_environment(environment)
        prompt = task.PROMPT
    else:
        task_environment = environment
        prompt = task.GOAL

    pre_environment = task_environment.model_copy(deep=True)
    runtime = FunctionsRuntime(suite.tools)
    messages: list[ChatMessage] = []
    model_output = None
    for _ in range(3):
        try:
            _, _, task_environment, messages, _ = pipeline.query(prompt, runtime, task_environment)
        except AbortAgentError as exc:
            task_environment = exc.task_environment
            messages = exc.messages

        model_output = model_output_from_messages(messages)
        if model_output is not None:
            break

    function_trace = functions_stack_trace_from_messages(messages)
    utility = suite._check_task_result(
        task,
        model_output or [],
        pre_environment,
        task_environment,
        function_trace,
    )
    attack_success = False
    if injection_task is not None:
        attack_success = suite._check_task_result(
            injection_task,
            model_output or [],
            pre_environment,
            task_environment,
            function_trace,
        )
    return {
        "utility": bool(utility),
        "attack_success": bool(attack_success),
        "model_output": model_output or [],
        "messages": messages,
        "function_trace": function_trace,
    }


def run_replay_capture(
    suite,
    task: BaseUserTask,
    injection_task: BaseInjectionTask | None,
    injections: dict[str, str],
    shadow_calls: list[FunctionCall],
    shadow_model_output: list[Any],
) -> dict[str, Any]:
    """Commit a clean shadow trajectory without letting the attacked model replan."""

    environment = suite.load_and_inject_default_environment(injections)
    task_environment = task.init_environment(environment)
    pre_environment = task_environment.model_copy(deep=True)
    runtime = FunctionsRuntime(suite.tools)
    replayed_calls: list[FunctionCall] = []
    replay_errors: list[dict[str, Any]] = []

    available_tools = {tool.name for tool in runtime.functions.values()}
    for original_call in shadow_calls:
        call = clone_call(original_call)
        if call.function not in available_tools:
            replay_errors.append(
                {
                    "function": call.function,
                    "args": normalize_for_signature(dict(call.args)),
                    "error": "invalid_tool",
                }
            )
            continue
        for arg_k, arg_v in call.args.items():
            if isinstance(arg_v, str) and is_string_list(arg_v):
                call.args[arg_k] = literal_eval(arg_v)
        _, error = runtime.run_function(task_environment, call.function, call.args)
        replayed_calls.append(call)
        if error is not None:
            replay_errors.append(
                {
                    "function": call.function,
                    "args": normalize_for_signature(dict(call.args)),
                    "error": error,
                }
            )

    utility = suite._check_task_result(
        task,
        shadow_model_output or [],
        pre_environment,
        task_environment,
        replayed_calls,
    )
    attack_success = False
    if injection_task is not None:
        attack_success = suite._check_task_result(
            injection_task,
            shadow_model_output or [],
            pre_environment,
            task_environment,
            replayed_calls,
        )
    return {
        "utility": bool(utility),
        "attack_success": bool(attack_success),
        "function_trace": replayed_calls,
        "replay_errors": replay_errors,
    }


def run_t113(args: argparse.Namespace) -> dict[str, Any]:
    suites = args.suites or list(DEFAULT_SUITES)
    all_suites = get_suites(args.benchmark_version)
    missing = sorted(set(suites) - set(all_suites))
    if missing:
        raise ValueError(f"Unknown suites for {args.benchmark_version}: {missing}")
    if args.attack not in ATTACKS:
        raise ValueError(f"Unknown attack {args.attack}; available={sorted(ATTACKS)}")

    inventory = suite_inventory(args.benchmark_version, suites)
    rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []

    for inv in inventory:
        suite = get_suite(args.benchmark_version, inv.suite)
        selected_user_tasks = subset_ids(inv.user_task_ids, args.user_tasks, args.max_user_tasks)
        selected_injection_tasks = subset_ids(inv.injection_task_ids, args.injection_tasks, args.max_injection_tasks)

        shadow_plans: dict[str, dict[str, Any]] = {}
        for user_task_id in selected_user_tasks:
            user_task = suite.get_user_task_by_id(user_task_id)
            shadow_pipeline, _ = make_pipeline_for_args(args, policy=None)
            shadow = run_task_capture(suite, shadow_pipeline, user_task, None, {})
            shadow_calls = shadow["function_trace"]
            shadow_plans[user_task_id] = {
                "utility": shadow["utility"],
                "calls": shadow_calls,
                "signatures": [call_signature(c) for c in shadow_calls],
                "model_output": shadow["model_output"],
            }
            trace_rows.append(
                {
                    "kind": "shadow",
                    "suite": inv.suite,
                    "user_task_id": user_task_id,
                    "utility": shadow["utility"],
                    "calls": calls_to_records(shadow_calls),
                }
            )

        injection_utility: dict[str, bool] = {}
        for injection_task_id in selected_injection_tasks:
            injection_task = suite.get_injection_task_by_id(injection_task_id)
            inj_pipeline, _ = make_pipeline_for_args(args, policy=None)
            inj_res = run_task_capture(suite, inj_pipeline, injection_task, None, {})
            injection_utility[injection_task_id] = inj_res["utility"]
            trace_rows.append(
                {
                    "kind": "injection_standalone",
                    "suite": inv.suite,
                    "injection_task_id": injection_task_id,
                    "utility": inj_res["utility"],
                    "calls": calls_to_records(inj_res["function_trace"]),
                }
            )

        attacker = load_attack(
            args.attack,
            suite,
            make_pipeline_for_args(args, policy=None)[0],
        )
        for user_task_id in selected_user_tasks:
            user_task = suite.get_user_task_by_id(user_task_id)
            shadow_plan = shadow_plans[user_task_id]
            for injection_task_id in selected_injection_tasks:
                injection_task = suite.get_injection_task_by_id(injection_task_id)
                injections = attacker.attack(user_task, injection_task)
                if args.mode in ("prefix_lock", "both"):
                    policy = ShadowPrefixPolicy(signatures=list(shadow_plan["signatures"]))
                    guarded_pipeline, _ = make_pipeline_for_args(args, policy=policy)
                    guarded = run_task_capture(suite, guarded_pipeline, user_task, injection_task, injections)
                    rows.append(
                        {
                            "method": "shadow_prefix_lock_v1",
                            "suite": inv.suite,
                            "user_task_id": user_task_id,
                            "injection_task_id": injection_task_id,
                            "shadow_utility": bool(shadow_plan["utility"]),
                            "injection_task_utility": bool(injection_utility[injection_task_id]),
                            "utility_under_attack": guarded["utility"],
                            "attack_success": guarded["attack_success"],
                            "guard_allowed": policy.allowed_count,
                            "guard_blocked": policy.blocked_count,
                            "replay_errors": [],
                            "shadow_calls": calls_to_records(shadow_plan["calls"]),
                            "committed_calls": calls_to_records(guarded["function_trace"]),
                            "guard_events": [event.__dict__ for event in policy.events],
                        }
                    )
                    trace_rows.append(
                        {
                            "kind": "guarded_attacked",
                            "method": "shadow_prefix_lock_v1",
                            "suite": inv.suite,
                            "user_task_id": user_task_id,
                            "injection_task_id": injection_task_id,
                            "utility": guarded["utility"],
                            "attack_success": guarded["attack_success"],
                            "guard_allowed": policy.allowed_count,
                            "guard_blocked": policy.blocked_count,
                            "calls": calls_to_records(guarded["function_trace"]),
                            "guard_events": [event.__dict__ for event in policy.events],
                        }
                    )

                if args.mode in ("replay_commit", "both"):
                    replayed = run_replay_capture(
                        suite,
                        user_task,
                        injection_task,
                        injections,
                        shadow_plan["calls"],
                        shadow_plan["model_output"],
                    )
                    rows.append(
                        {
                            "method": "shadow_replay_commit_v1",
                            "suite": inv.suite,
                            "user_task_id": user_task_id,
                            "injection_task_id": injection_task_id,
                            "shadow_utility": bool(shadow_plan["utility"]),
                            "injection_task_utility": bool(injection_utility[injection_task_id]),
                            "utility_under_attack": replayed["utility"],
                            "attack_success": replayed["attack_success"],
                            "guard_allowed": len(replayed["function_trace"]),
                            "guard_blocked": 0,
                            "replay_errors": replayed["replay_errors"],
                            "shadow_calls": calls_to_records(shadow_plan["calls"]),
                            "committed_calls": calls_to_records(replayed["function_trace"]),
                            "guard_events": [],
                        }
                    )
                    trace_rows.append(
                        {
                            "kind": "guarded_attacked",
                            "method": "shadow_replay_commit_v1",
                            "suite": inv.suite,
                            "user_task_id": user_task_id,
                            "injection_task_id": injection_task_id,
                            "utility": replayed["utility"],
                            "attack_success": replayed["attack_success"],
                            "guard_allowed": len(replayed["function_trace"]),
                            "guard_blocked": 0,
                            "replay_errors": replayed["replay_errors"],
                            "calls": calls_to_records(replayed["function_trace"]),
                        }
                    )

    summary_by_suite = []
    for method in ("shadow_prefix_lock_v1", "shadow_replay_commit_v1"):
        for suite_name in suites:
            suite_rows = [r for r in rows if r["suite"] == suite_name and r["method"] == method]
            if not suite_rows:
                continue
            summary_by_suite.append(summarize_rows(method, suite_name, suite_rows))

    payload = {
        "schema_version": "agentdojo_guarded_eval_t113_v1",
        "method": args.mode,
        "claim_boundary": "oracle clean-shadow trajectory pilot; not an independent F_c compiler, not a full AuthGraph comparison, and not yet a deployable monitor",
        "benchmark_version": args.benchmark_version,
        "model": args.model,
        "attack": args.attack,
        "inventory": [inv.__dict__ for inv in inventory],
        "summary_by_suite": summary_by_suite,
        "rows": rows,
    }

    Path(args.trace_output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.trace_output, "w", encoding="utf-8") as f:
        for row in trace_rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    return payload


def summarize_rows(method: str, suite: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    attack_success = sum(r["attack_success"] for r in rows)
    utility = sum(r["utility_under_attack"] for r in rows)
    shadow_utility = sum(r["shadow_utility"] for r in rows)
    injection_utility = sum(r["injection_task_utility"] for r in rows)
    blocked_any = sum(r["guard_blocked"] > 0 for r in rows)
    return {
        "method": method,
        "suite": suite,
        "n": n,
        "shadow_UR": shadow_utility / n if n else math.nan,
        "injection_task_utility": injection_utility / n if n else math.nan,
        "A_UR": utility / n if n else math.nan,
        "ASR": attack_success / n if n else math.nan,
        "defense_success_rate": 1 - (attack_success / n if n else math.nan),
        "guard_block_any_rate": blocked_any / n if n else math.nan,
        "guard_allowed_total": sum(r["guard_allowed"] for r in rows),
        "guard_blocked_total": sum(r["guard_blocked"] for r in rows),
        "replay_error_total": sum(len(r.get("replay_errors", [])) for r in rows),
        "ASR_count": f"{attack_success}/{n}",
        "A_UR_count": f"{utility}/{n}",
        "blocked_any_count": f"{blocked_any}/{n}",
    }


def write_report(payload: dict[str, Any], output_md: Path) -> None:
    lines = [
        "# T113 AgentDojo Future-Constrained Guard",
        "",
        "## Scope",
        "",
        "- Evaluated methods: `shadow_prefix_lock_v1` and/or `shadow_replay_commit_v1`.",
        "- A clean no-injection shadow trajectory is generated for each user task.",
        "- `shadow_prefix_lock_v1` lets the attacked model continue but commits only exact next-step matches.",
        "- `shadow_replay_commit_v1` skips attacked replanning and commits the clean shadow trajectory in the injected environment.",
        "- This is an oracle/shadow pilot, not an independent future-constraint compiler.",
        "",
        "## Results",
        "",
        "| method | suite | n | shadow UR | A.UR | ASR | A.UR count | ASR count | block-any | allowed | blocked | replay errors |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["summary_by_suite"]:
        lines.append(
            f"| {row['method']} | {row['suite']} | {row['n']} | {row['shadow_UR']:.4f} | {row['A_UR']:.4f} | "
            f"{row['ASR']:.4f} | {row['A_UR_count']} | {row['ASR_count']} | {row['guard_block_any_rate']:.4f} | "
            f"{row['guard_allowed_total']} | {row['guard_blocked_total']} | {row['replay_error_total']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- ASR follows AgentDojo injection-task success semantics: higher is worse.",
            "- `shadow_UR` is clean-shadow task utility, not deploy-time user satisfaction.",
            "- A low ASR with low A.UR indicates over-blocking or replay utility loss, not a useful defense.",
            "- `shadow_replay_commit_v1` assumes the clean shadow trajectory is available and safe to replay; it is an upper-bound mechanism test, not a complete deployed system.",
        ]
    )
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    payload = run_t113(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    write_report(payload, Path(args.output_md))
    print(f"Wrote T113 JSON to {args.output}")
    print(f"Wrote T113 report to {args.output_md}")
    print(f"Wrote T113 trace rows to {args.trace_output}")


if __name__ == "__main__":
    main()
