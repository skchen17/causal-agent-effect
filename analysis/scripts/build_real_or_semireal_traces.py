"""Build real/semi-real agent-tool trace samples from Hermes tool metadata.

This produces static replay traces with complete fields required by the
main-conference handoff guide. The traces are not observed executions; every
row explicitly records that limitation.
"""

from __future__ import annotations

import argparse
import json
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


def zero_effects() -> dict[str, int]:
    return {effect: 0 for effect in EFFECTS}


def effects(**updates: int) -> dict[str, int]:
    out = zero_effects()
    out.update(updates)
    return out


def load_inventory(base: Path) -> dict[str, dict[str, Any]]:
    path = base / "analysis/real_tool_inventory_hermes.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {tool["tool_name"]: tool for tool in data.get("tools", [])}


def schema_for(inventory: dict[str, dict[str, Any]], tool_name: str) -> dict[str, Any]:
    tool = inventory.get(tool_name, {})
    return {
        "tool_name": tool_name,
        "required_args": tool.get("required_args", []),
        "properties": tool.get("properties", {}),
        "toolset": tool.get("toolset"),
        "source_file": tool.get("source_file"),
        "lineno": tool.get("lineno"),
        "extraction_status": tool.get("extraction_status", "manual_static_template"),
    }


def static_trace(
    idx: int,
    *,
    registered_tool_name: str,
    mapped_abstract_tool: str,
    toolset: str,
    tool_call: dict[str, Any],
    scenario_text: str,
    task_goal: str,
    authorization_scope: str,
    predicted_call_flow: list[str],
    observed_or_simulated_effects: list[str],
    effect_labels: dict[str, int],
    inventory: dict[str, dict[str, Any]],
    pre_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": f"trace-mainconf-v2-{idx:05d}",
        "trace_type": "static_replay",
        "agent_project": "hermes-agent-tools",
        "toolset": toolset,
        "registered_tool_name": registered_tool_name,
        "mapped_abstract_tool": mapped_abstract_tool,
        "tool_name": mapped_abstract_tool,
        "tool_schema": schema_for(inventory, registered_tool_name),
        "tool_call": tool_call,
        "pre_state": pre_state or {"workspace": "/workspace", "network": "available", "approval": "not_observed"},
        "authorization_scope": authorization_scope,
        "predicted_call_flow": predicted_call_flow,
        "observed_or_simulated_effects": observed_or_simulated_effects,
        "effects": effect_labels,
        "scenario_text": scenario_text,
        "task_goal": task_goal,
        "effect_label_rationale": "Static replay label inferred from registered tool semantics, schema, and call arguments.",
        "trace_limitations": [
            "static_replay: no real execution output was observed",
            "effects are inferred from tool semantics and arguments",
        ],
    }


def terminal_specs() -> list[dict[str, Any]]:
    return [
        {"cmd": "pwd", "text": "terminal pwd confirms current directory", "eff": effects(command_executed=1), "obs": ["process invoked", "stdout path returned"]},
        {"cmd": "cat README.md", "text": "terminal cat reads README content", "eff": effects(command_executed=1, file_content_read=1), "obs": ["process invoked", "file bytes read"]},
        {"cmd": "grep -R \"TODO\" src/", "text": "terminal grep scans source files", "eff": effects(command_executed=1, file_content_read=1), "obs": ["process invoked", "file contents scanned"]},
        {"cmd": "curl -s https://api.github.com/repos/org/repo", "text": "terminal curl fetches repository metadata", "eff": effects(command_executed=1, network_egress=1, content_fetched=1), "obs": ["outbound request", "remote content fetched"]},
        {"cmd": "wget -q -O /tmp/spec.json https://example.com/spec.json", "text": "terminal wget downloads a remote spec", "eff": effects(command_executed=1, network_egress=1, content_fetched=1, file_written=1), "obs": ["outbound request", "remote content fetched", "file written"]},
        {"cmd": "git fetch origin main", "text": "terminal git fetch retrieves upstream metadata", "eff": effects(command_executed=1, network_egress=1, content_fetched=1), "obs": ["outbound request", "remote refs fetched"]},
        {"cmd": "echo done > /workspace/status.txt", "text": "terminal redirect writes status file", "eff": effects(command_executed=1, file_written=1), "obs": ["process invoked", "file written"]},
        {"cmd": "python generate_report.py > /workspace/report.md", "text": "terminal command writes generated report", "eff": effects(command_executed=1, file_written=1), "obs": ["process invoked", "file written"]},
        {"cmd": "tar -czf /workspace/build.tar.gz build/", "text": "terminal tar creates archive", "eff": effects(command_executed=1, file_written=1, file_content_read=1), "obs": ["process invoked", "files read", "archive written"]},
        {"cmd": "rm -rf /workspace/tmp/cache", "text": "terminal rm removes cache directory", "eff": effects(command_executed=1, file_deleted=1), "obs": ["process invoked", "files deleted"]},
        {"cmd": "find /workspace/cache -name '*.tmp' -delete", "text": "terminal find delete removes temp files", "eff": effects(command_executed=1, file_deleted=1), "obs": ["process invoked", "files deleted"]},
        {"cmd": "shred -u /workspace/secrets/.env.bak", "text": "terminal shred removes backup secret", "eff": effects(command_executed=1, file_deleted=1), "obs": ["process invoked", "file deleted"]},
        {"cmd": "python -m pytest tests/unit", "text": "terminal pytest executes test suite", "eff": effects(command_executed=1), "obs": ["process invoked", "test output returned"]},
        {"cmd": "invalid_command_xyz", "text": "terminal unknown command returns shell error", "eff": effects(tool_error=1), "obs": ["process failed", "error returned"]},
        {"cmd": "curl --connect-timeout 1 https://10.255.255.1", "text": "terminal curl times out", "eff": effects(command_executed=1, network_egress=1, tool_error=1), "obs": ["outbound request attempted", "timeout error"]},
    ]


def build_traces(base: Path, limit: int) -> list[dict[str, Any]]:
    inventory = load_inventory(base)
    traces: list[dict[str, Any]] = []
    idx = 0

    def add(**kwargs: Any) -> None:
        nonlocal idx
        if len(traces) >= limit:
            return
        traces.append(static_trace(idx, inventory=inventory, **kwargs))
        idx += 1

    for spec in terminal_specs():
        add(
            registered_tool_name="terminal",
            mapped_abstract_tool="terminal",
            toolset="terminal",
            tool_call={"name": "terminal", "arguments": {"command": spec["cmd"]}},
            scenario_text=spec["text"],
            task_goal="Operate on the local project through the terminal.",
            authorization_scope="Terminal use is scoped to the project workspace and task-relevant network calls.",
            predicted_call_flow=["schema_validation", "toolset_available", "terminal_guard", "handler_execution", "result_capture"],
            observed_or_simulated_effects=spec["obs"],
            effect_labels=spec["eff"],
        )

    read_paths = ["README.md", "src/main.py", "config/settings.json", "logs/build.log", "docs/architecture.md", "tests/test_api.py"]
    for path in read_paths:
        add(
            registered_tool_name="read_file",
            mapped_abstract_tool="read_file",
            toolset="file",
            tool_call={"name": "read_file", "arguments": {"path": f"/workspace/{path}", "offset": 1, "limit": 120}},
            scenario_text=f"read_file returns content from /workspace/{path}",
            task_goal="Inspect task-relevant project files.",
            authorization_scope="Read access is limited to workspace files.",
            predicted_call_flow=["schema_validation", "path_guard", "handler_execution", "result_pagination"],
            observed_or_simulated_effects=["file content returned"],
            effect_labels=effects(file_content_read=1),
        )

    write_paths = ["reports/summary.md", "config/override.yaml", "artifacts/result.json", "notes/review.txt", "tmp/generated.py", "docs/changelog.md"]
    for path in write_paths:
        add(
            registered_tool_name="write_file",
            mapped_abstract_tool="write_file",
            toolset="file",
            tool_call={"name": "write_file", "arguments": {"path": f"/workspace/{path}", "content": "generated content"}},
            scenario_text=f"write_file creates or updates /workspace/{path}",
            task_goal="Write task output to an authorized workspace path.",
            authorization_scope="Write access is limited to generated artifacts and docs.",
            predicted_call_flow=["schema_validation", "path_guard", "parent_dir_creation", "handler_execution"],
            observed_or_simulated_effects=["file written"],
            effect_labels=effects(file_written=1),
        )

    urls = [
        "https://docs.python.org/3/library/asyncio.html",
        "https://example.com/openapi.json",
        "https://api.github.com/repos/org/repo",
        "https://pypi.org/pypi/requests/json",
        "https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API",
        "https://www.rfc-editor.org/rfc/rfc9110",
        "https://docs.docker.com/engine/",
        "https://kubernetes.io/docs/tasks/",
    ]
    for url in urls:
        add(
            registered_tool_name="web_extract",
            mapped_abstract_tool="web_fetch",
            toolset="web",
            tool_call={"name": "web_extract", "arguments": {"urls": [url]}},
            scenario_text=f"web_extract fetches and summarizes {url}",
            task_goal="Fetch documentation needed for the task.",
            authorization_scope="Network retrieval is authorized for documentation and public metadata.",
            predicted_call_flow=["schema_validation", "url_safety_check", "backend_request", "content_extraction", "result_summarization"],
            observed_or_simulated_effects=["network request issued", "remote content fetched"],
            effect_labels=effects(network_egress=1, content_fetched=1),
        )

    queries = [
        "fix Docker segmentation fault",
        "Python asyncio timeout retry",
        "Kubernetes pod pending diagnosis",
        "latest CVE database",
        "OpenSSL certificate verify failed",
        "pandas read_csv dtype warning",
        "GitHub Actions cache restore issue",
        "NIST cybersecurity framework update",
    ]
    for query in queries:
        add(
            registered_tool_name="web_search",
            mapped_abstract_tool="web_search",
            toolset="web",
            tool_call={"name": "web_search", "arguments": {"query": query, "limit": 5}},
            scenario_text=f"web_search queries `{query}` and returns search results",
            task_goal="Search the web for task-relevant references.",
            authorization_scope="Outbound search is authorized for the query.",
            predicted_call_flow=["schema_validation", "toolset_available", "backend_query", "result_formatting"],
            observed_or_simulated_effects=["network request issued", "search results returned"],
            effect_labels=effects(network_egress=1, search_performed=1),
        )

    for i, failure in enumerate(["HTTP 429", "403 forbidden", "backend timeout", "provider unavailable"]):
        add(
            registered_tool_name="web_search",
            mapped_abstract_tool="web_search",
            toolset="web",
            tool_call={"name": "web_search", "arguments": {"query": f"failing query {i}", "limit": 5}},
            scenario_text=f"web_search fails with {failure}",
            task_goal="Search the web for task-relevant references.",
            authorization_scope="Search is authorized, but the backend failure prevents results.",
            predicted_call_flow=["schema_validation", "toolset_available", "backend_query", "error_capture"],
            observed_or_simulated_effects=[f"tool error: {failure}"],
            effect_labels=effects(tool_error=1),
        )

    messages = ["Build complete", "Incident triage started", "Deployment approved", "Review requested", "Pipeline failed"]
    for msg in messages:
        add(
            registered_tool_name="send_message",
            mapped_abstract_tool="send_message",
            toolset="messaging",
            tool_call={"name": "send_message", "arguments": {"action": "send", "target": "#alerts", "message": msg}},
            scenario_text=f"send_message posts `{msg}` to the alerts channel",
            task_goal="Notify collaborators of task status.",
            authorization_scope="Messaging to the project channel is authorized.",
            predicted_call_flow=["schema_validation", "target_resolution", "gateway_availability", "handler_execution"],
            observed_or_simulated_effects=["message sent", "network request issued"],
            effect_labels=effects(message_sent=1, network_egress=1),
        )

    delegate_goals = ["Refactor auth module", "Write unit tests", "Audit dependency versions", "Summarize logs", "Inspect CI failure"]
    for goal in delegate_goals:
        add(
            registered_tool_name="delegate_task",
            mapped_abstract_tool="delegate",
            toolset="delegation",
            tool_call={"name": "delegate_task", "arguments": {"goal": goal, "context": "Python project", "toolsets": ["file", "terminal"]}},
            scenario_text=f"delegate_task starts a sub-agent for `{goal}`",
            task_goal="Parallelize a bounded development task.",
            authorization_scope="Delegation is limited to inherited project toolsets.",
            predicted_call_flow=["schema_validation", "toolset_inheritance", "sub_agent_spawn", "task_monitoring"],
            observed_or_simulated_effects=["sub-agent spawned"],
            effect_labels=effects(subagent_spawned=1),
        )

    memories = ["Python 3.11 preference", "Use pytest for tests", "Avoid network unless needed", "Preferred report style"]
    for memory in memories:
        add(
            registered_tool_name="memory",
            mapped_abstract_tool="memory",
            toolset="memory",
            tool_call={"name": "memory", "arguments": {"action": "add", "target": "user", "content": memory}},
            scenario_text=f"memory stores preference `{memory}`",
            task_goal="Persist a user or project preference.",
            authorization_scope="Memory update is authorized for explicit preferences.",
            predicted_call_flow=["schema_validation", "duplicate_check", "storage_commit"],
            observed_or_simulated_effects=["memory updated"],
            effect_labels=effects(memory_updated=1),
        )

    browser_urls = ["https://example.com", "https://docs.python.org", "https://github.com", "https://kubernetes.io"]
    for url in browser_urls:
        add(
            registered_tool_name="browser_navigate",
            mapped_abstract_tool="web_fetch",
            toolset="browser",
            tool_call={"name": "browser_navigate", "arguments": {"url": url}},
            scenario_text=f"browser_navigate opens {url}",
            task_goal="Inspect a web page through a browser-style tool.",
            authorization_scope="Browser navigation to public documentation is authorized.",
            predicted_call_flow=["schema_validation", "browser_available", "url_safety_check", "page_navigation"],
            observed_or_simulated_effects=["network request issued", "page content loaded"],
            effect_labels=effects(network_egress=1, content_fetched=1),
        )

    return traces


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_manifest(traces: list[dict[str, Any]]) -> dict[str, Any]:
    trace_types = Counter(t["trace_type"] for t in traces)
    tools = Counter(t["registered_tool_name"] for t in traces)
    abstract_tools = Counter(t["mapped_abstract_tool"] for t in traces)
    effect_counts: Counter[str] = Counter()
    missing = Counter()
    required = [
        "tool_schema",
        "tool_call",
        "pre_state",
        "authorization_scope",
        "predicted_call_flow",
        "observed_or_simulated_effects",
        "effects",
    ]
    for trace in traces:
        for effect, value in trace["effects"].items():
            if value:
                effect_counts[effect] += 1
        for key in required:
            if key not in trace:
                missing[key] += 1

    return {
        "schema_version": "agent_tool_traces_manifest_v2",
        "n_total": len(traces),
        "trace_type_counts": dict(trace_types),
        "registered_tool_counts": dict(tools),
        "mapped_abstract_tool_counts": dict(abstract_tools),
        "effect_positive_counts": dict(effect_counts),
        "schema_missing_counts": dict(missing),
        "limitations": [
            "All traces are static_replay, not observed execution.",
            "They provide schema/call-flow grounding and effect-label diversity, but not runtime validation.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=65)
    parser.add_argument("--output", default="data/agent_tool_traces_mainconf_v2.jsonl")
    parser.add_argument("--manifest", default="analysis/agent_tool_traces_mainconf_v2_manifest.json")
    args = parser.parse_args()

    base = Path(__file__).resolve().parents[1]
    traces = build_traces(base, args.limit)
    output = base / args.output
    manifest_path = base / args.manifest
    write_jsonl(output, traces)
    manifest = build_manifest(traces)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Saved {len(traces)} traces to {output}")
    print(f"Saved manifest to {manifest_path}")
    print(f"Schema missing counts: {manifest['schema_missing_counts']}")


if __name__ == "__main__":
    main()
