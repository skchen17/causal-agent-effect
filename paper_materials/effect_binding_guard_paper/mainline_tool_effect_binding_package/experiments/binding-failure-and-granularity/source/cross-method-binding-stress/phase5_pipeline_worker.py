from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Isolated worker for original IPIGuard/CaMeL Phase 5 pipelines.")
    parser.add_argument("--system", choices=("ipiguard", "camel"), required=True)
    parser.add_argument("--suite", default="workspace")
    parser.add_argument("--attack", default="none")
    parser.add_argument("--mode", choices=("benign", "attack"), default="benign")
    parser.add_argument("--model", default="Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf")
    parser.add_argument("--base-url", default="http://127.0.0.1:18080/v1")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument(
        "--claim-scope",
        choices=("original_pipeline_local_model", "original_pipeline_external_model"),
        default="original_pipeline_local_model",
    )
    parser.add_argument("--max-cases", type=int, default=5)
    parser.add_argument("--case-protocol", choices=("paired", "full_cross_product"), default="paired")
    parser.add_argument("--policy-mode", choices=("none", "normal", "strict"), default="none")
    parser.add_argument("--output", required=True)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result = run_ipiguard(args) if args.system == "ipiguard" else run_camel(args)
    output.write_text(json.dumps(json_ready(result), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_ipiguard(args: argparse.Namespace) -> dict[str, Any]:
    external = ROOT / "external/systems/ipiguard/agentdojo/src"
    sys.path.insert(0, str(external))
    import openai
    from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, load_system_message
    from agentdojo.agent_pipeline.basic_elements import InitQuery, SystemMessage
    from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
    from agentdojo.agent_pipeline.tool_execution import (
        ToolsExecutionLoop,
        ToolsExecutor,
    )
    from agentdojo.attacks.attack_registry import load_attack
    from agentdojo.task_suite.load_suites import get_suite

    client = CompatibleOpenAIClient(openai.OpenAI(api_key=api_key(args), base_url=args.base_url))
    if args.policy_mode == "none":
        llm = OpenAILLM(client, args.model)
        pipeline = AgentPipeline([SystemMessage(load_system_message(None)), InitQuery(), llm, ToolsExecutionLoop([ToolsExecutor(), llm])])
        pipeline.name = "local"
        component = "agentdojo_no_defense_local_model"
    else:
        from agentdojo.agent_pipeline.llms.ipiguard_llm import OpenAIConstructLLM, OpenAITraverseLLM
        from agentdojo.agent_pipeline.tool_execution import DagToolsExecutionLoop, DagToolsExecutor

        construct_llm = OpenAIConstructLLM(client, args.model)
        traverse_llm = OpenAITraverseLLM(client, args.model)
        pipeline = AgentPipeline(
            [
                SystemMessage(load_system_message(None)),
                InitQuery(),
                construct_llm,
                DagToolsExecutionLoop(DagToolsExecutor(traverse_llm)),
            ]
        )
        pipeline.name = "local"
        component = "original_ipiguard_construct_traverse_pipeline"
    return run_agentdojo_cases(args, pipeline, get_suite, load_attack, component, dag_serializer=serialize_ipiguard_dag)


def run_camel(args: argparse.Namespace) -> dict[str, Any]:
    external = ROOT / "external/systems/camel/src"
    sys.path.insert(0, str(external))
    os.environ["OPENAI_API_KEY"] = api_key(args)
    os.environ["OPENAI_BASE_URL"] = args.base_url
    import openai
    from agentdojo.attacks import load_attack
    from agentdojo.task_suite import get_suite
    import camel.models as camel_models
    from camel.interpreter.interpreter import MetadataEvalMode

    real_openai = openai.OpenAI

    def local_openai(*call_args, **kwargs):
        kwargs.setdefault("api_key", api_key(args))
        kwargs.setdefault("base_url", args.base_url)
        return CompatibleOpenAIClient(real_openai(*call_args, **kwargs))

    camel_models.openai.OpenAI = local_openai
    eval_mode = MetadataEvalMode.STRICT if args.policy_mode == "strict" else MetadataEvalMode.NORMAL
    pipeline = camel_models.make_tools_pipeline(
        f"openai:{args.model}",
        use_original=False,
        replay_with_policies=False,
        attack_name="important_instructions",
        reasoning_effort="medium",
        thinking_budget_tokens=None,
        suite=args.suite,
        ad_defense=None,
        eval_mode=eval_mode,
        q_llm=f"openai:{args.model}",
    )
    pipeline.name = f"local+camel+{args.policy_mode}"
    if args.policy_mode != "none":
        # The published generator uses no policy and later replays. Inline replacement
        # preserves the original PrivilegedLLM/interpreter/policy components while
        # avoiding a second model call and real side effects.
        privileged = pipeline.elements[-1]
        privileged.security_policy_engine = camel_models._SECURITY_POLICY_ENGINES[args.suite]
    pipeline.elements[-1].max_attempts = 2
    pipeline.elements[-1].quarantined_llm_retries = 2
    component = (
        "original_camel_generator_interpreter_no_policy"
        if args.policy_mode == "none"
        else f"original_camel_generator_interpreter_inline_policy_{args.policy_mode}"
    )
    return run_agentdojo_cases(args, pipeline, get_suite, load_attack, component, dag_serializer=None)


def run_agentdojo_cases(
    args: argparse.Namespace,
    pipeline: Any,
    get_suite: Any,
    load_attack: Any,
    component: str,
    dag_serializer: Any,
) -> dict[str, Any]:
    suite = get_suite("v1.1.2" if args.system == "ipiguard" else "v1.2", args.suite)
    attack = None if args.mode == "benign" else load_attack(args.attack, suite, pipeline)
    user_ids = sorted(suite.user_tasks)
    injection_ids = sorted(suite.injection_tasks)
    if args.mode == "benign":
        case_pairs = [(user_id, None) for user_id in user_ids]
    elif args.case_protocol == "full_cross_product":
        case_pairs = [(user_id, injection_id) for user_id in user_ids for injection_id in injection_ids]
    else:
        case_pairs = [
            (user_id, injection_ids[index % len(injection_ids)])
            for index, user_id in enumerate(user_ids)
        ]
    if args.max_cases > 0:
        case_pairs = case_pairs[: args.max_cases]
    output = Path(args.output)
    existing_cases: list[dict[str, Any]] = []
    if args.resume and output.exists():
        try:
            existing_cases = json.loads(output.read_text(encoding="utf-8")).get("cases", [])
        except (json.JSONDecodeError, OSError):
            existing_cases = []
    completed = {case_identity(row.get("user_task_id"), row.get("injection_task_id")) for row in existing_cases}
    cases = list(existing_cases)
    for user_id, injection_id in case_pairs:
        if case_identity(user_id, injection_id) in completed:
            continue
        user_task = suite.get_user_task_by_id(user_id)
        injection_task = None
        injections = {}
        if attack is not None:
            assert injection_id is not None
            injection_task = suite.get_injection_task_by_id(injection_id)
            injections = attack.attack(user_task, injection_task)
        try:
            if hasattr(suite, "run_task_with_pipeline_msg"):
                utility, security, messages, extra = suite.run_task_with_pipeline_msg(
                    pipeline,
                    user_task,
                    injection_task,
                    injections,
                    extra_args={"input_tokens": 0, "output_tokens": 0},
                )
            else:
                utility, security = suite.run_task_with_pipeline(pipeline, user_task, injection_task, injections)
                messages, extra = [], {"trace_capture": "unavailable_in_native_agentdojo_version"}
            error = None
        except Exception as exc:
            utility = False
            security = False
            messages = []
            extra = {}
            error = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        dag = extra.get("dag") if isinstance(extra, dict) else None
        cases.append(
            {
                "case_id": f"{args.system}:{args.suite}:{user_id}:{getattr(injection_task, 'ID', 'none')}",
                "user_task_id": user_id,
                "injection_task_id": getattr(injection_task, "ID", None),
                "utility": bool(utility),
                "security": bool(security),
                "attack_success": bool(security) if injection_task is not None else False,
                "messages": messages,
                "extra_args": extra,
                "dag": dag_serializer(dag) if dag is not None and dag_serializer else None,
                "error": error,
                "tools_executed_in_simulation": True,
                "real_side_effects": False,
            }
        )
        write_worker_checkpoint(args, component, cases)
    return worker_payload(args, component, cases, run_complete=True)


def case_identity(user_task_id: Any, injection_task_id: Any) -> str:
    return f"{user_task_id}::{injection_task_id or 'none'}"


def worker_payload(
    args: argparse.Namespace,
    component: str,
    cases: list[dict[str, Any]],
    *,
    run_complete: bool,
) -> dict[str, Any]:
    return {
        "schema_version": "tool_effect_fragmentation_phase5_original_pipeline_worker_v1",
        "system": args.system,
        "component": component,
        "claim_scope": args.claim_scope,
        "model": args.model,
        "base_url": args.base_url,
        "suite": args.suite,
        "mode": args.mode,
        "attack": args.attack,
        "policy_mode": args.policy_mode,
        "case_protocol": args.case_protocol,
        "run_complete": run_complete,
        "n_cases": len(cases),
        "n_errors": sum(row["error"] is not None for row in cases),
        "tools_executed_in_simulation": True,
        "real_side_effects": False,
        "cases": cases,
    }


def api_key(args: argparse.Namespace) -> str:
    value = os.environ.get(args.api_key_env, "")
    if value:
        return value
    if args.base_url.startswith("http://127.0.0.1") or args.base_url.startswith("http://localhost"):
        return "local-not-secret"
    raise RuntimeError(f"{args.api_key_env} is required for non-local base URL")


def write_worker_checkpoint(args: argparse.Namespace, component: str, cases: list[dict[str, Any]]) -> None:
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(json_ready(worker_payload(args, component, cases, run_complete=False)), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)


def serialize_ipiguard_dag(dag: Any) -> dict[str, Any]:
    nodes = []
    edges = []
    for node_id, data in dag.nodes(data=True):
        call = data.get("function_call")
        nodes.append(
            {
                "id": str(node_id),
                "function_name": getattr(call, "function", None),
                "arguments": getattr(call, "args", {}),
                "depends_on": [str(dep) for dep in data.get("depends_on", [])],
            }
        )
    for source, target in dag.edges():
        edges.append({"source": str(source), "target": str(target)})
    return {"nodes": nodes, "edges": edges}


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "model_dump"):
        return json_ready(value.model_dump())
    if hasattr(value, "to_dict"):
        return json_ready(value.to_dict())
    return str(value)


class CompatibleOpenAIClient:
    """Minimal compatibility wrapper for llama.cpp's stricter chat schema."""

    def __init__(self, client: Any) -> None:
        self._client = client
        self.chat = _ChatProxy(client.chat)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)


class _ChatProxy:
    def __init__(self, chat: Any) -> None:
        self._chat = chat
        self.completions = _CompletionsProxy(chat.completions)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._chat, name)


class _CompletionsProxy:
    def __init__(self, completions: Any) -> None:
        self._completions = completions

    def create(self, **kwargs: Any) -> Any:
        messages = []
        for message in kwargs.get("messages", []):
            message = dict(message)
            if message.get("role") == "developer":
                message["role"] = "system"
            if message.get("role") == "assistant" and message.get("content") is None:
                message["content"] = ""
            if isinstance(message.get("content"), list):
                blocks = []
                for block in message["content"]:
                    if isinstance(block, dict):
                        blocks.append(str(block.get("text") or block.get("content") or ""))
                    else:
                        blocks.append(str(block))
                message["content"] = "\n".join(blocks)
            messages.append(message)
        kwargs["messages"] = messages
        kwargs.setdefault("max_tokens", 1024)
        return self._completions.create(**kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._completions, name)


if __name__ == "__main__":
    main()
