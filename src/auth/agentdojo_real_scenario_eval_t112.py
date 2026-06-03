"""T112 AgentDojo real-scenario evaluation harness.

This script is intentionally separate from the earlier local/proxy benchmarks.
It uses AgentDojo's official task suites and metrics so future results can be
compared against AgentDojo and AuthGraph-style ASR/utility reporting.

Default mode only writes an inventory and execution plan. Use --run-agentdojo
to call an OpenAI-compatible model endpoint; the API key is read from an
environment variable and is never written to the output files.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from openai._types import NOT_GIVEN
from openai import OpenAI

import agentdojo.attacks  # noqa: F401 - registers default attacks
from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, PipelineConfig
from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.attacks.attack_registry import ATTACKS, load_attack
from agentdojo.benchmark import (
    SuiteResults,
    benchmark_suite_with_injections,
    benchmark_suite_without_injections,
)
from agentdojo.functions_runtime import EmptyEnv, Env, Function, FunctionCall, FunctionsRuntime
from agentdojo.logging import OutputLogger
from agentdojo.task_suite.load_suites import get_suite, get_suites
from agentdojo.types import (
    ChatAssistantMessage,
    ChatMessage,
    get_text_content_as_str,
    text_content_block_from_string,
)


DEFAULT_SUITES = ("workspace", "slack", "travel", "banking")


class OpenAICompatibleSystemLLM(BasePipelineElement):
    """OpenAI-compatible LLM wrapper that keeps system messages as `system`.

    AgentDojo's current OpenAI wrapper maps system messages to the newer
    `developer` role. DeepSeek's OpenAI-compatible endpoint rejects that role,
    so this wrapper uses the older system/user/assistant/tool role set while
    keeping native tool-calling.
    """

    def __init__(self, client: OpenAI, model: str, temperature: float = 0.0) -> None:
        self.client = client
        self.model = model
        self.temperature = temperature
        self.name = model

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: list[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, list[ChatMessage], dict]:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[self._message_to_payload(m) for m in messages],
            tools=[self._function_to_payload(f) for f in runtime.functions.values()] or NOT_GIVEN,
            tool_choice="auto" if runtime.functions else NOT_GIVEN,
            temperature=self.temperature,
        )
        output = self._assistant_from_response(completion.choices[0].message)
        return query, runtime, env, [*messages, output], extra_args

    @staticmethod
    def _content_to_string(message: ChatMessage) -> str | None:
        content = message.get("content")
        if content is None:
            return None
        return get_text_content_as_str(content)

    def _message_to_payload(self, message: ChatMessage) -> dict[str, Any]:
        role = message["role"]
        if role == "system":
            return {"role": "system", "content": self._content_to_string(message) or ""}
        if role == "user":
            return {"role": "user", "content": self._content_to_string(message) or ""}
        if role == "assistant":
            payload: dict[str, Any] = {
                "role": "assistant",
                "content": self._content_to_string(message),
            }
            tool_calls = message.get("tool_calls")
            if tool_calls:
                payload["tool_calls"] = [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function,
                            "arguments": json.dumps(tool_call.args),
                        },
                    }
                    for tool_call in tool_calls
                    if tool_call.id is not None
                ]
            return payload
        if role == "tool":
            return {
                "role": "tool",
                "tool_call_id": message["tool_call_id"],
                "content": message.get("error") or self._content_to_string(message) or "",
            }
        raise ValueError(f"Unsupported message role: {role}")

    @staticmethod
    def _function_to_payload(function: Function) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": function.name,
                "description": function.description,
                "parameters": function.parameters.model_json_schema(),
            },
        }

    @staticmethod
    def _assistant_from_response(message: Any) -> ChatAssistantMessage:
        tool_calls = None
        if message.tool_calls is not None:
            parsed_calls = []
            for tool_call in message.tool_calls:
                try:
                    args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                parsed_calls.append(
                    FunctionCall(
                        function=tool_call.function.name,
                        args=args,
                        id=tool_call.id,
                    )
                )
            tool_calls = parsed_calls
        content = None
        if message.content is not None:
            content = [text_content_block_from_string(message.content)]
        return ChatAssistantMessage(role="assistant", content=content, tool_calls=tool_calls)


@dataclass
class SuiteInventory:
    suite: str
    user_tasks: int
    injection_tasks: int
    tools: int
    user_task_ids: list[str]
    injection_task_ids: list[str]
    tool_names: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-version", default="v1.2.2")
    parser.add_argument("--suite", action="append", dest="suites", default=[])
    parser.add_argument("--attack", default="tool_knowledge")
    parser.add_argument("--defense", action="append", default=[])
    parser.add_argument("--user-task", action="append", dest="user_tasks", default=[])
    parser.add_argument("--injection-task", action="append", dest="injection_tasks", default=[])
    parser.add_argument("--max-user-tasks", type=int, default=0)
    parser.add_argument("--max-injection-tasks", type=int, default=0)
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument(
        "--pipeline-label",
        default="",
        help="Optional AgentDojo pipeline name label. Useful for attacks that require a recognized model-family string such as 'Local model'.",
    )
    parser.add_argument("--base-url", default=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--logdir", default="runs/agentdojo_t112")
    parser.add_argument("--output", default="analysis/results/agentdojo_real_scenario_eval_t112_v1.json")
    parser.add_argument("--output-md", default="analysis/results/agentdojo_real_scenario_eval_t112_v1.md")
    parser.add_argument("--run-agentdojo", action="store_true")
    parser.add_argument("--force-rerun", action="store_true")
    return parser.parse_args()


def suite_inventory(benchmark_version: str, suites: list[str]) -> list[SuiteInventory]:
    out: list[SuiteInventory] = []
    for suite_name in suites:
        suite = get_suite(benchmark_version, suite_name)
        out.append(
            SuiteInventory(
                suite=suite_name,
                user_tasks=len(suite.user_tasks),
                injection_tasks=len(suite.injection_tasks),
                tools=len(suite.tools),
                user_task_ids=sorted(suite.user_tasks.keys()),
                injection_task_ids=sorted(suite.injection_tasks.keys()),
                tool_names=sorted(tool.name for tool in suite.tools),
            )
        )
    return out


def subset_ids(all_ids: list[str], requested: list[str], max_n: int) -> list[str]:
    if requested:
        return requested
    if max_n and max_n > 0:
        return all_ids[:max_n]
    return all_ids


def make_openai_compatible_pipeline(
    model: str,
    base_url: str,
    api_key_env: str,
    defense: str | None,
) -> AgentPipeline:
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise RuntimeError(
            f"Missing {api_key_env}. Set it in the environment to run AgentDojo model calls."
        )
    client = OpenAI(api_key=api_key, base_url=base_url)
    llm = OpenAICompatibleSystemLLM(client, model, temperature=0.0)
    return AgentPipeline.from_config(
        PipelineConfig(
            llm=llm,
            model_id=None,
            defense=defense,
            system_message_name=None,
            system_message=None,
            tool_output_format="yaml",
        )
    )


def run_one_setting(
    benchmark_version: str,
    suite_name: str,
    selected_user_tasks: list[str],
    selected_injection_tasks: list[str],
    attack_name: str,
    defense_name: str,
    model: str,
    pipeline_label: str,
    base_url: str,
    api_key_env: str,
    logdir: Path,
    force_rerun: bool,
) -> dict[str, Any]:
    suite = get_suite(benchmark_version, suite_name)
    defense = None if defense_name == "none" else defense_name
    pipeline = make_openai_compatible_pipeline(model, base_url, api_key_env, defense)
    pipeline_name = pipeline_label or model
    pipeline.name = f"{pipeline_name}-{defense_name}"

    with OutputLogger(str(logdir)):
        benign: SuiteResults = benchmark_suite_without_injections(
            pipeline,
            suite,
            logdir=logdir,
            force_rerun=force_rerun,
            user_tasks=selected_user_tasks,
            benchmark_version=benchmark_version,
        )
        attacker = load_attack(attack_name, suite, pipeline)
        attacked: SuiteResults = benchmark_suite_with_injections(
            pipeline,
            suite,
            attacker,
            logdir=logdir,
            force_rerun=force_rerun,
            user_tasks=selected_user_tasks,
            injection_tasks=selected_injection_tasks,
            benchmark_version=benchmark_version,
        )

    benign_utility = mean_bool(benign["utility_results"].values())
    injection_task_utility = mean_bool(attacked["injection_tasks_utility_results"].values())
    utility_under_attack = mean_bool(attacked["utility_results"].values())
    attack_success_rate = mean_bool(attacked["security_results"].values())
    defense_success_rate = 1.0 - attack_success_rate
    return {
        "suite": suite_name,
        "model": model,
        "defense": defense_name,
        "attack": attack_name,
        "user_tasks": selected_user_tasks,
        "injection_tasks": selected_injection_tasks,
        "n_benign": len(benign["utility_results"]),
        "n_injection_task_utility": len(attacked["injection_tasks_utility_results"]),
        "n_attacked": len(attacked["security_results"]),
        "benign_utility": benign_utility,
        "injection_task_utility": injection_task_utility,
        "utility_under_attack": utility_under_attack,
        "defense_success_rate": defense_success_rate,
        "attack_success_rate": attack_success_rate,
        "agentdojo_metric_mapping": {
            "UR": "benign_utility",
            "A.UR": "utility_under_attack",
            "ASR": "attack_success_rate",
        },
    }


def mean_bool(values: Any) -> float:
    values = list(values)
    if not values:
        return float("nan")
    return sum(bool(v) for v in values) / len(values)


def write_report(payload: dict[str, Any], output_md: Path) -> None:
    lines = [
        "# T112 AgentDojo Real-Scenario Evaluation Harness",
        "",
        "## Scope",
        "",
        "- Uses AgentDojo official suites, task IDs, attacks, and utility/security checks.",
        "- Default run writes inventory and a concrete execution plan only.",
        "- Model execution requires `--run-agentdojo` and an API key in the configured env var.",
        "- API keys are not serialized to artifacts.",
        "",
        "## Inventory",
        "",
        "| suite | user tasks | injection tasks | tools |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in payload["inventory"]:
        lines.append(
            f"| {row['suite']} | {row['user_tasks']} | {row['injection_tasks']} | {row['tools']} |"
        )

    lines.extend(
        [
            "",
            "## Planned Settings",
            "",
            "| suite | user tasks | injection tasks | attack | defenses |",
            "| --- | ---: | ---: | --- | --- |",
        ]
    )
    for row in payload["planned_settings"]:
        lines.append(
            f"| {row['suite']} | {len(row['user_task_ids'])} | {len(row['injection_task_ids'])} | "
            f"{row['attack']} | {', '.join(row['defenses'])} |"
        )

    if payload.get("results"):
        lines.extend(
            [
                "",
                "## Results",
                "",
                "| suite | model | defense | n attacked | UR | A.UR | ASR |",
                "| --- | --- | --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in payload["results"]:
            lines.append(
                f"| {row['suite']} | {row['model']} | {row['defense']} | {row['n_attacked']} | "
                f"{row['benign_utility']:.4f} | {row['utility_under_attack']:.4f} | "
                f"{row['attack_success_rate']:.4f} |"
            )
        lines.extend(
            [
                "",
                "Injection task utility is reported in the JSON artifact as `injection_task_utility`. "
                "Low values mean ASR should be interpreted cautiously because some attacker goals "
                "are not reliably solved as standalone user tasks by the evaluated model.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "## Results",
                "",
                "No AgentDojo model calls were run in this invocation.",
            ]
        )

    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- An inventory-only run is not empirical evidence for the method.",
            "- A small smoke run is only an integration check; paper claims require broad suite/task coverage.",
            "- Comparisons to AuthGraph must use the same benchmark version, suites, attacks, model family, and metrics where feasible.",
        ]
    )
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    suites = args.suites or list(DEFAULT_SUITES)
    defenses = args.defense or ["none"]
    all_suites = get_suites(args.benchmark_version)
    missing = sorted(set(suites) - set(all_suites))
    if missing:
        raise ValueError(f"Unknown suites for {args.benchmark_version}: {missing}")
    if args.attack not in ATTACKS:
        raise ValueError(f"Unknown attack {args.attack}; available={sorted(ATTACKS)}")

    inventory = suite_inventory(args.benchmark_version, suites)
    planned_settings = []
    for inv in inventory:
        planned_settings.append(
            {
                "suite": inv.suite,
                "user_task_ids": subset_ids(inv.user_task_ids, args.user_tasks, args.max_user_tasks),
                "injection_task_ids": subset_ids(
                    inv.injection_task_ids, args.injection_tasks, args.max_injection_tasks
                ),
                "attack": args.attack,
                "defenses": defenses,
            }
        )

    results = []
    if args.run_agentdojo:
        logdir = Path(args.logdir)
        for setting in planned_settings:
            for defense in defenses:
                results.append(
                    run_one_setting(
                        benchmark_version=args.benchmark_version,
                        suite_name=setting["suite"],
                        selected_user_tasks=setting["user_task_ids"],
                        selected_injection_tasks=setting["injection_task_ids"],
                        attack_name=args.attack,
                        defense_name=defense,
                        model=args.model,
                        pipeline_label=args.pipeline_label,
                        base_url=args.base_url,
                        api_key_env=args.api_key_env,
                        logdir=logdir,
                        force_rerun=args.force_rerun,
                    )
                )

    payload = {
        "schema_version": "agentdojo_real_scenario_eval_t112_v1",
        "benchmark_version": args.benchmark_version,
        "mode": "run_agentdojo" if args.run_agentdojo else "inventory_only",
        "model": args.model,
        "base_url_host": args.base_url.split("//")[-1].split("/")[0],
        "api_key_env": args.api_key_env,
        "inventory": [asdict(row) for row in inventory],
        "planned_settings": planned_settings,
        "results": results,
        "comparison_targets": {
            "AgentDojo": ["benign_utility", "utility_under_attack", "attack_success_rate"],
            "AuthGraph": ["ASR", "UR", "A.UR", "same benchmark/suite/model caveat"],
            "project_method": ["U-Commit", "FDeny", "pre-effect block", "mapped to ASR/UR when run in AgentDojo"],
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(payload, Path(args.output_md))
    print(f"Wrote T112 JSON to {output}")
    print(f"Wrote T112 report to {args.output_md}")


if __name__ == "__main__":
    main()
