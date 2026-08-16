from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run IPIGuard original DAG-construction component on Phase 5 cases.")
    parser.add_argument("--cases", default="data/tool_effect_fragmentation/ipiguard_counterfactual_phase5.jsonl")
    parser.add_argument("--output", default="analysis/results/tool_effect_fragmentation_ipiguard_component_phase5.jsonl")
    parser.add_argument("--base-url", default="http://127.0.0.1:18080/v1")
    parser.add_argument("--model", default="Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf")
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sys.path.insert(0, str(ROOT / "external/systems/ipiguard/agentdojo/src"))
    import openai
    from agentdojo.agent_pipeline.llms.ipiguard_llm import OpenAIConstructLLM

    cases = [json.loads(line) for line in (ROOT / args.cases).read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.max_cases:
        cases = cases[: args.max_cases]
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if args.resume and output.exists():
        existing = {
            row["case_id"]: row
            for row in (json.loads(line) for line in output.read_text(encoding="utf-8").splitlines() if line.strip())
        }
    client = openai.OpenAI(api_key="local-not-secret", base_url=args.base_url)
    constructor = OpenAIConstructLLM(client, args.model)
    rows = dict(existing)
    for case in cases:
        if case["case_id"] in rows:
            continue
        prompt = build_prompt(constructor, case)
        try:
            response = client.chat.completions.create(
                model=args.model,
                messages=[
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]},
                ],
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=args.max_tokens,
            )
            raw = response.choices[0].message.content or ""
            dag = constructor.construct_dag(raw)
            parsed = serialize_dag(dag)
            error = None
        except Exception as exc:
            raw = ""
            parsed = None
            error = {"type": type(exc).__name__, "message": str(exc)}
        rows[case["case_id"]] = {
            "case_id": case["case_id"],
            "counterfactual_group_id": case["counterfactual_group_id"],
            "variant": case["variant"],
            "realized_effect": case["realized_effect"],
            "same_effect_as_original": case["same_effect_as_original"],
            "prompt": prompt,
            "raw_output": raw,
            "parsed_dag": parsed,
            "parse_valid": parsed is not None,
            "error": error,
            "claim_scope": "original_component_custom_stress",
            "original_component": "OpenAIConstructLLM._construct_dag_prompt+construct_dag",
            "tools_executed_in_simulation": False,
            "real_side_effects": False,
        }
        write_rows(output, rows)


def build_prompt(constructor: Any, case: dict[str, Any]) -> dict[str, str]:
    tools = []
    for tool in case["tool_inventory"]:
        properties = {name: {"type": "string"} for name in tool.get("schema", [])}
        tools.append(
            {
                "name": tool["name"],
                "description": tool.get("description") or f"Candidate tool surface {tool['name']}.",
                "parameters": {"type": "object", "properties": properties},
            }
        )
    system = (
        "<function-definitions>\n"
        + "\n".join(json.dumps(tool, ensure_ascii=False, sort_keys=True) for tool in tools)
        + "\n</function-definitions>\n"
        + constructor._construct_dag_prompt
    )
    user = f"User task: {case['user_task']}"
    if case.get("model_visible_candidate") is not None:
        user += f"\nCandidate representation: {json.dumps(case['model_visible_candidate'], ensure_ascii=False, sort_keys=True)}"
    return {"system": system, "user": user}


def serialize_dag(dag: Any) -> dict[str, Any]:
    nodes = []
    for node_id, data in dag.nodes(data=True):
        call = data["function_call"]
        nodes.append(
            {
                "id": str(node_id),
                "function_name": call.function,
                "arguments": call.args,
                "depends_on": [str(item) for item in data.get("depends_on", [])],
            }
        )
    return {"nodes": nodes, "edges": [{"source": str(a), "target": str(b)} for a, b in dag.edges()]}


def write_rows(path: Path, rows: dict[str, dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for _, row in sorted(rows.items())) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
