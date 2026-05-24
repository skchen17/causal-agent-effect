"""
Generate targeted LLM-synthesized scenarios for under-represented causal effects.

Targets the 8 effects with N+ < 50 in the current dataset.
For each effect, generates 2-3 themed batches designed to:
1. Include MULTIPLE tools that can produce the effect (cross-tool diversity)
2. Include both positive AND negative cases (the effect present vs absent)
3. Include context-dependent cases (safe/unsafe/prod)
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path
from dataclasses import dataclass

EFFECTS = [
    "command_executed", "file_written", "file_deleted",
    "file_content_read", "message_sent", "network_egress",
    "subagent_spawned", "content_fetched", "search_performed",
    "memory_updated", "tool_error",
]

TOOLS = ["terminal", "write_file", "read_file", "delete_file",
         "send_message", "web_fetch", "web_search", "delegate", "memory"]


@dataclass
class Scenario:
    tool_name: str
    scenario_text: str
    context_type: str
    effects: dict[str, int]


# Per-effect generation specs: (effect, positive_tools, negative_tools, N_desired, seed)
TARGETS = [
    {
        "effect": "file_content_read",
        "positive_tools": ["read_file", "terminal"],
        "context_hint": "file reading, code inspection, log analysis, config checking",
        "n_target": 50,
        "n_existing": 40,
    },
    {
        "effect": "file_written",
        "positive_tools": ["write_file", "terminal"],
        "context_hint": "file creation, code generation, data export, config updates, logging output",
        "n_target": 50,
        "n_existing": 31,
    },
    {
        "effect": "file_deleted",
        "positive_tools": ["delete_file", "terminal"],
        "context_hint": "file removal, cache cleanup, temporary file deletion, old log rotation",
        "n_target": 50,
        "n_existing": 25,
    },
    {
        "effect": "content_fetched",
        "positive_tools": ["web_fetch", "terminal"],
        "context_hint": "API data fetching, web scraping, downloading resources, reading remote docs",
        "n_target": 50,
        "n_existing": 22,
    },
    {
        "effect": "message_sent",
        "positive_tools": ["send_message"],
        "context_hint": "sending notifications, alerts, reports, status updates to users or channels",
        "n_target": 50,
        "n_existing": 21,
    },
    {
        "effect": "memory_updated",
        "positive_tools": ["memory"],
        "context_hint": "storing user preferences, project settings, learned facts, session history",
        "n_target": 50,
        "n_existing": 19,
    },
    {
        "effect": "subagent_spawned",
        "positive_tools": ["delegate"],
        "context_hint": "delegating code review, research tasks, refactoring, documentation generation to subagents",
        "n_target": 50,
        "n_existing": 17,
    },
    {
        "effect": "search_performed",
        "positive_tools": ["web_search", "terminal"],
        "context_hint": "web searching for documentation, error solutions, API references, best practices",
        "n_target": 50,
        "n_existing": 15,
    },
]


def _get_text_from_response(response) -> str:
    for block in response.content:
        if hasattr(block, "text") and block.text:
            return block.text
    return ""


def _build_effect_prompt(spec: dict, batch_size: int, seed: int) -> str:
    rng = random.Random(seed)

    effect = spec["effect"]
    pos_tools = ", ".join(spec["positive_tools"])
    context_hint = spec["context_hint"]
    n_desired = spec["n_target"] - spec["n_existing"]

    themes = [
        f"DevOps engineer debugging a CI/CD pipeline failure",
        f"data scientist analyzing experiment results",
        f"full-stack developer building a new microservice",
        f"security researcher auditing a codebase",
        f"open-source maintainer triaging issues and PRs",
        f"ML engineer setting up a training pipeline",
    ]
    theme = rng.choice(themes)

    return f"""Generate {batch_size} realistic agent tool-call scenarios for causal safety research.
Theme: {theme}

Focus on generating scenarios that produce the causal effect "{effect}".
This effect typically occurs with these tools: {pos_tools}.
Common contexts: {context_hint}

Return a JSON array of {batch_size} objects:
{{
  "tool_name": one of [{', '.join(TOOLS)}],
  "scenario_text": natural Chinese or English description with full context
      (safe_mode on/off? project size? production environment?).
      Include realistic agent actions — what would a real coding agent do?
  "context_type": "safe", "unsafe", or "prod",
  "effects": dict with 0/1 for these keys: {json.dumps(EFFECTS)}
}}

CRITICAL RULES:
1. MOST scenarios should have "{effect}" = 1, but include some NEGATIVE cases
   (where the effect does NOT happen — e.g., context prevents it, safe_mode blocks it).
2. VARY which tools produce the effect — do NOT use only one tool.
   For example, file_content_read can happen via read_file OR via terminal "cat/grep".
3. Include error cases where tool_error=1 AND the target effect is 0.
4. Make the descriptions realistic, diverse, and natural.
5. Include context in the text itself (mention safe_mode, project size, environment).

Return ONLY the JSON array, no markdown, no explanation."""


def generate(seed: int = 99, batch_size: int = 20) -> list[Scenario]:
    from anthropic import Anthropic
    client = Anthropic()

    all_scenarios: list[Scenario] = []

    for spec in TARGETS:
        n_needed = spec["n_target"] - spec["n_existing"]
        if n_needed <= 0:
            print(f"  {spec['effect']}: already sufficient, skipping")
            continue

        n_batches = max(1, min(3, (n_needed + batch_size - 1) // batch_size))
        print(f"\n  {spec['effect']}: need {n_needed}, generating {n_batches} batch(es)...")

        for b in range(n_batches):
            n_this = min(batch_size, n_needed - b * batch_size)
            prompt = _build_effect_prompt(spec, n_this, seed + b)

            try:
                response = client.messages.create(
                    model="deepseek-v4-flash",
                    max_tokens=16384,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = _get_text_from_response(response).strip()
                text = re.sub(r'^```(?:json)?\s*\n?', '', text)
                text = re.sub(r'\n?```\s*$', '', text)

                parsed = json.loads(text)
                for item in parsed:
                    effects = {e: 0 for e in EFFECTS}
                    effects.update(item.get("effects", {}))
                    all_scenarios.append(Scenario(
                        tool_name=item["tool_name"],
                        scenario_text=item["scenario_text"],
                        context_type=item.get("context_type", "safe"),
                        effects=effects,
                    ))
                print(f"    Batch {b+1}: got {len(parsed)} scenarios")
            except Exception as e:
                print(f"    Batch {b+1}: ERROR — {e}")

    return all_scenarios


def main() -> None:
    print("Generating targeted LLM data for under-represented effects...")
    scenarios = generate(seed=99, batch_size=20)

    out_dir = Path(__file__).resolve().parent.parent / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / "targeted_synthetic.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for s in scenarios:
            f.write(json.dumps({
                "tool_name": s.tool_name,
                "scenario_text": s.scenario_text,
                "context_type": s.context_type,
                "effects": s.effects,
            }, ensure_ascii=False) + "\n")

    # Stats
    effect_counts = {e: 0 for e in EFFECTS}
    tool_counts = {}
    for s in scenarios:
        for e, v in s.effects.items():
            if v: effect_counts[e] += 1
        tool_counts[s.tool_name] = tool_counts.get(s.tool_name, 0) + 1

    print(f"\nSaved {len(scenarios)} scenarios to {out_path}")
    print(f"\nEffect distribution (new data):")
    for e, c in sorted(effect_counts.items(), key=lambda x: -x[1]):
        print(f"  {e:25s}: {c:4d}")
    print(f"\nTool distribution:")
    for t, c in sorted(tool_counts.items()):
        print(f"  {t:15s}: {c:4d}")


if __name__ == "__main__":
    main()
