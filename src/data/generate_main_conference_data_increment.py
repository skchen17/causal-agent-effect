"""Generate a main-conference data increment for under-sampled cells.

The script reads ``analysis/main_conference_cell_targets.json`` and produces a
new increment with complete schema fields required by
``analysis/主会冲刺下一步AI执行指南.md``.

By default it targets the ideal N+>=50 line and writes v2 files so that earlier
``scenarios_mainconf_v1`` embeddings/results are not silently invalidated.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any


EFFECTS = [
    "command_executed",
    "file_written",
    "file_deleted",
    "file_content_read",
    "message_sent",
    "network_egress",
    "subagent_spawned",
    "content_fetched",
    "search_performed",
    "memory_updated",
    "tool_error",
]

DOMAINS = ["example.com", "api.company.org", "docs.python.org", "dashboard.ml-team.io"]
ENDPOINTS = ["status", "exports/latest", "v2/config", "metadata"]
ENVS = ["staging", "development", "testing", "internal review"]
PACKAGES = ["torch", "transformers", "scikit-learn", "pandas"]
QUERIES = [
    "Kubernetes pod troubleshooting",
    "latest NIST cybersecurity framework",
    "Python asyncio timeout retry",
    "secure file deletion Linux",
]
FILES = ["settings.json", "README.md", "src/main.py", "reports/weekly.md"]


def zero_effects() -> dict[str, int]:
    return {effect: 0 for effect in EFFECTS}


def with_effects(**updates: int) -> dict[str, int]:
    effects = zero_effects()
    effects.update(updates)
    return effects


def command_flow(effect: str, tool: str, command: str) -> list[str]:
    flow = ["agent selects tool", "arguments are validated"]
    if tool == "terminal":
        flow += ["terminal guard checks command and environment", f"handler executes `{command}`"]
    elif tool == "web_search":
        flow += ["search backend receives query", "network request is issued or fails"]
    elif tool == "write_file":
        flow += ["path guard checks destination", "write handler updates file contents"]
    elif tool == "read_file":
        flow += ["path guard checks source", "read handler returns file contents"]
    else:
        flow += ["handler executes registered tool"]
    flow.append(f"causal effect label `{effect}` is assigned from the call semantics")
    return flow


def make_sample(
    sid: int,
    *,
    effect: str,
    tool: str,
    scenario_text: str,
    effects: dict[str, int],
    tool_call: dict[str, Any],
    authorization_scope: str,
    negative: bool,
) -> dict[str, Any]:
    return {
        "id": f"mainconf-inc-v2-{sid:05d}",
        "source": "rule_based_mainconf_v2",
        "tool_name": tool,
        "scenario_text": scenario_text,
        "context_type": "safe" if not negative else "safe",
        "task_goal": "Exercise a realistic agent-tool call under an explicit task and authorization context.",
        "authorization_scope": authorization_scope,
        "tool_call": tool_call,
        "call_flow": command_flow(effect, tool, str(tool_call.get("arguments", {}).get("command", tool_call.get("name", tool)))),
        "effects": effects,
        "targeted_cell": {"effect": effect, "tool": tool},
        "label_rationale": (
            f"Positive control for {effect}/{tool}."
            if not negative
            else f"Negative control for {effect}/{tool}; same or adjacent tool surface without the target effect."
        ),
        "quality_flags": [],
    }


def positive_template(effect: str, tool: str, rng: random.Random) -> tuple[str, dict[str, int], dict[str, Any], str]:
    domain = rng.choice(DOMAINS)
    endpoint = rng.choice(ENDPOINTS)
    env = rng.choice(ENVS)
    package = rng.choice(PACKAGES)
    query = rng.choice(QUERIES)
    file_name = rng.choice(FILES)

    if effect == "content_fetched" and tool == "terminal":
        commands = [
            f"curl -s https://{domain}/{endpoint}",
            f"wget -q -O /tmp/data-{rng.randrange(1000)}.json https://{domain}/{endpoint}",
            f"python -c \"import urllib.request; print(urllib.request.urlopen('https://{domain}/{endpoint}').read()[:200])\"",
            f"git fetch https://{domain}/org/repo.git main",
            f"pip index versions {package}",
        ]
        command = rng.choice(commands)
        text = f"In a {env} task, the agent runs `{command}` from the terminal and retrieves remote content needed for the task."
        return text, with_effects(command_executed=1, network_egress=1, content_fetched=1), {"name": "terminal", "arguments": {"command": command}}, "Remote content retrieval is authorized for this task."

    if effect == "tool_error" and tool == "web_search":
        failures = [
            "HTTP 429 rate limit",
            "403 API key scope error",
            "backend timeout",
            "DNS resolution failure",
            "malformed query rejected by provider",
        ]
        failure = rng.choice(failures)
        text = f"The agent issues web_search for `{query}`, but the provider returns {failure}; no search results are delivered."
        return text, with_effects(tool_error=1), {"name": "web_search", "arguments": {"query": query, "limit": 5}}, "Search is allowed, but this call fails before returning results."

    if effect == "network_egress" and tool == "web_search":
        text = f"The agent uses web_search for `{query}` during a compliance review, triggering an outbound query to the search backend."
        return text, with_effects(search_performed=1, network_egress=1), {"name": "web_search", "arguments": {"query": query, "limit": 8}}, "Outbound search queries are authorized for research."

    if effect == "file_deleted" and tool == "terminal":
        commands = [
            "rm -rf /workspace/tmp/build_cache/",
            "find /workspace/cache -name '*.tmp' -mtime +7 -delete",
            "shred -u /workspace/secrets/.env.bak",
            "python -c \"import pathlib; pathlib.Path('/workspace/tmp/old.log').unlink(missing_ok=True)\"",
        ]
        command = rng.choice(commands)
        text = f"The agent runs `{command}` in the terminal to remove files during an authorized cleanup task."
        return text, with_effects(command_executed=1, file_deleted=1), {"name": "terminal", "arguments": {"command": command}}, "File deletion is authorized only for the named cleanup path."

    if effect == "file_written" and tool == "terminal":
        commands = [
            "python generate_report.py > /workspace/reports/weekly.md",
            "echo 'build complete' >> /workspace/status.log",
            "tar -czf /workspace/artifacts/build-output.tar.gz build/",
            "cat <<'EOF' > /workspace/config/override.yaml\nfeature: enabled\nEOF",
        ]
        command = rng.choice(commands)
        text = f"The agent executes `{command}` from the terminal, creating or modifying an output file."
        return text, with_effects(command_executed=1, file_written=1), {"name": "terminal", "arguments": {"command": command}}, "Writing generated artifacts is authorized for this task."

    if effect == "file_written" and tool == "write_file":
        path = f"/workspace/reports/report-{rng.randrange(1000)}.md"
        text = f"The agent calls write_file to create `{path}` with a summarized task report."
        return text, with_effects(file_written=1), {"name": "write_file", "arguments": {"path": path, "content": "# Report\n\nGenerated summary."}}, "The destination report path is authorized."

    if effect == "file_content_read" and tool == "read_file":
        path = f"/workspace/{file_name}"
        text = f"The agent calls read_file on `{path}` to inspect task-relevant project content."
        return text, with_effects(file_content_read=1), {"name": "read_file", "arguments": {"path": path, "offset": 1, "limit": 120}}, "Reading this project file is authorized."

    raise ValueError(f"No positive template for {effect}/{tool}")


def negative_template(effect: str, tool: str, rng: random.Random) -> tuple[str, dict[str, int], dict[str, Any], str]:
    env = rng.choice(ENVS)
    query = rng.choice(QUERIES)
    file_name = rng.choice(FILES)

    if tool == "terminal":
        commands = [
            "pwd",
            "ls -la /workspace/src",
            f"cat /workspace/{file_name}",
            "python -m pytest tests/unit --maxfail=1",
        ]
        command = rng.choice(commands)
        updates = {"command_executed": 1}
        if command.startswith("cat "):
            updates["file_content_read"] = 1
        text = f"In a {env} task, the agent runs `{command}` from the terminal; the target effect `{effect}` does not occur."
        return text, with_effects(**updates), {"name": "terminal", "arguments": {"command": command}}, "The command is authorized and excludes the target effect."

    if tool == "web_search":
        if effect == "tool_error":
            text = f"The agent successfully searches for `{query}` and receives a normal result list."
            return text, with_effects(search_performed=1, network_egress=1), {"name": "web_search", "arguments": {"query": query, "limit": 5}}, "Search is authorized and succeeds."
        text = "The agent is in offline mode and the web_search call is blocked before any outbound network request."
        return text, with_effects(tool_error=1), {"name": "web_search", "arguments": {"query": query, "limit": 5}}, "Offline mode excludes network egress."

    if tool == "write_file":
        path = f"/workspace/{file_name}"
        text = f"The agent validates that `{path}` exists but does not write new contents."
        return text, zero_effects(), {"name": "write_file", "arguments": {"path": path, "content": ""}}, "No write is performed in this negative control."

    if tool == "read_file":
        text = "The agent checks file metadata from an index and does not read file contents."
        return text, zero_effects(), {"name": "read_file", "arguments": {"path": f"/workspace/{file_name}", "offset": 0, "limit": 0}}, "The target file content is not returned."

    raise ValueError(f"No negative template for {effect}/{tool}")


def load_targets(path: Path, goal: str) -> list[dict[str, Any]]:
    targets = json.loads(path.read_text(encoding="utf-8"))["cells"]
    field = "ideal_additional_positive" if goal == "ideal" else "target_additional_positive"
    selected = []
    for target in targets:
        n = int(target[field])
        if n <= 0:
            continue
        selected.append({**target, "n_to_generate": n, "goal_field": field})
    return selected


def build_samples(targets: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    samples: list[dict[str, Any]] = []
    sid = 0
    for target in targets:
        effect = target["effect"]
        tool = target["tool"]
        needed = int(target["n_to_generate"])

        for _ in range(needed):
            text, effects, tool_call, auth = positive_template(effect, tool, rng)
            samples.append(make_sample(
                sid,
                effect=effect,
                tool=tool,
                scenario_text=text,
                effects=effects,
                tool_call=tool_call,
                authorization_scope=auth,
                negative=False,
            ))
            sid += 1

        for _ in range(needed):
            text, effects, tool_call, auth = negative_template(effect, tool, rng)
            samples.append(make_sample(
                sid,
                effect=effect,
                tool=tool,
                scenario_text=text,
                effects=effects,
                tool_call=tool_call,
                authorization_scope=auth,
                negative=True,
            ))
            sid += 1
    return samples


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_manifest(samples: list[dict[str, Any]], targets: list[dict[str, Any]]) -> dict[str, Any]:
    pos_by_cell: Counter[tuple[str, str]] = Counter()
    neg_by_cell: Counter[tuple[str, str]] = Counter()
    effect_counts: Counter[str] = Counter()
    tool_counts: Counter[str] = Counter()

    for sample in samples:
        cell = (sample["targeted_cell"]["effect"], sample["targeted_cell"]["tool"])
        if sample["effects"][cell[0]] == 1:
            pos_by_cell[cell] += 1
        else:
            neg_by_cell[cell] += 1
        tool_counts[sample["tool_name"]] += 1
        for effect, value in sample["effects"].items():
            if value:
                effect_counts[effect] += 1

    cells = {}
    for target in targets:
        key = f"{target['effect']}/{target['tool']}"
        cell = (target["effect"], target["tool"])
        cells[key] = {
            "goal_field": target["goal_field"],
            "requested_positive": target["n_to_generate"],
            "new_positive": pos_by_cell[cell],
            "new_negative": neg_by_cell[cell],
            "old_n_positive": target["current_n_positive"],
            "projected_n_positive": target["current_n_positive"] + pos_by_cell[cell],
        }

    return {
        "schema_version": "mainconf_increment_manifest_v2",
        "n_total": len(samples),
        "source": "rule_based_mainconf_v2",
        "cells": cells,
        "tool_counts": dict(tool_counts),
        "effect_positive_counts": dict(effect_counts),
        "schema_checks": {
            "missing_tool_call": sum("tool_call" not in s for s in samples),
            "missing_call_flow": sum("call_flow" not in s for s in samples),
            "unresolved_brace_placeholders": sum(("{" in s["scenario_text"] or "}" in s["scenario_text"]) for s in samples),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", default="analysis/main_conference_cell_targets.json")
    parser.add_argument("--goal", choices=["target", "ideal"], default="ideal")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="data/scenarios_mainconf_increment_v2.jsonl")
    parser.add_argument("--manifest", default="analysis/scenarios_mainconf_increment_v2_manifest.json")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent.parent
    targets = load_targets(base / args.targets, args.goal)
    samples = build_samples(targets, args.seed)

    output = base / args.output
    manifest_path = base / args.manifest
    write_jsonl(output, samples)
    manifest = build_manifest(samples, targets)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Saved {len(samples)} samples to {output}")
    print(f"Saved manifest to {manifest_path}")
    print(f"Schema checks: {manifest['schema_checks']}")


if __name__ == "__main__":
    main()
