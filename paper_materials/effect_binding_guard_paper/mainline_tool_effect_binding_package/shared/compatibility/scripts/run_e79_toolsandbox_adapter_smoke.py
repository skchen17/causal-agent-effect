#!/usr/bin/env python3
"""Run the bounded E79 ToolSandbox adapter-readiness smoke.

This script uses the local ToolSandbox snapshot only.  It does not run an LLM,
user simulator, external API, or network-backed tool.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import json
import socket
import sys
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Iterator, Mapping
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
TOOL_SANDBOX = ROOT / "runs/e79_external_benchmarks/ToolSandbox"
MANIFEST = ROOT / "evaluation/e79_long_horizon/toolsandbox_feasibility_manifest.json"
RESULT_JSON = ROOT / "analysis/results/e79_toolsandbox_adapter_smoke.json"
RESULT_MD = ROOT / "analysis/results/e79_toolsandbox_adapter_smoke.md"

SMOKE_SCENARIOS = (
    "modify_contact_with_message_recency",
    "send_message_with_contact_content_cellular_off",
)
STATE_MUTATION_PRIMITIVES = frozenset(
    {"add_to_database", "remove_from_database", "update_database"}
)


class AdapterRejection(RuntimeError):
    """A call rejected before the native callable is invoked."""

    def __init__(self, code: str, tool_name: str, fields: list[str]) -> None:
        self.code = code
        self.tool_name = tool_name
        self.fields = sorted(fields)
        super().__init__(f"{code}: {tool_name}: {', '.join(self.fields)}")


@dataclass(frozen=True)
class ToolEvidence:
    name: str
    module: str
    qualname: str
    signature: str
    classification: str
    mutation_path: tuple[str, ...]
    source_file: str
    source_line: int
    source_sha256: str
    signature_fields: tuple[str, ...]
    schema_fields: tuple[str, ...]
    schema_required_fields: tuple[str, ...]
    default_bearing_fields: tuple[str, ...]
    unsupported_schema_fields: tuple[str, ...]
    defaults: tuple[dict[str, Any], ...]
    allowed_by_scenarios: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed_by_scenarios": list(self.allowed_by_scenarios),
            "classification": self.classification,
            "classification_evidence": {
                "method": "transitive_static_call_path_to_native_context_mutator",
                "mutation_path": list(self.mutation_path),
                "mutation_primitives": sorted(STATE_MUTATION_PRIMITIVES),
            },
            "default_bearing_fields": list(self.default_bearing_fields),
            "defaults": list(self.defaults),
            "function": {
                "module": self.module,
                "name": self.name,
                "qualname": self.qualname,
                "signature": self.signature,
            },
            "schema_evidence": {
                "native_schema_fields": list(self.schema_fields),
                "native_schema_required_fields": list(self.schema_required_fields),
                "signature_fields": list(self.signature_fields),
                "unsupported_schema_fields": list(self.unsupported_schema_fields),
            },
            "source_evidence": {
                "file": self.source_file,
                "line": self.source_line,
                "sha256": self.source_sha256,
            },
            "tool_name": self.name,
        }


def _configure_import() -> None:
    source = str(TOOL_SANDBOX)
    if source not in sys.path:
        sys.path.insert(0, source)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _json_safe_default(value: Any) -> tuple[Any, bool]:
    try:
        _canonical_json(value)
    except (TypeError, ValueError):
        return repr(value), False
    return value, True


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _module_function_calls(module: ModuleType) -> tuple[dict[str, set[str]], Path]:
    source_path_text = inspect.getsourcefile(module)
    if source_path_text is None:
        raise RuntimeError(f"No source file for native module {module.__name__}")
    source_path = Path(source_path_text).resolve()
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    calls: dict[str, set[str]] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            calls[node.name] = {
                name
                for child in ast.walk(node)
                if isinstance(child, ast.Call)
                for name in [_call_name(child)]
                if name is not None
            }
    return calls, source_path


def _mutation_path(module: ModuleType, function_name: str) -> tuple[str, ...]:
    calls, _ = _module_function_calls(module)

    def visit(name: str, active: frozenset[str]) -> tuple[str, ...]:
        if name in active:
            return ()
        callees = calls.get(name, set())
        direct = sorted(callees & STATE_MUTATION_PRIMITIVES)
        if direct:
            return (name, direct[0])
        for callee in sorted(callees & calls.keys()):
            path = visit(callee, active | {name})
            if path:
                return (name, *path)
        return ()

    return visit(function_name, frozenset())


def classify_tool(
    name: str,
    tool: Callable[..., Any],
    native_schema: Mapping[str, Any],
    allowed_by_scenarios: tuple[str, ...],
) -> ToolEvidence:
    """Classify one native callable using implementation and native schema evidence."""

    module = inspect.getmodule(tool)
    if module is None:
        raise RuntimeError(f"No native module for {name}")
    calls, source_path = _module_function_calls(module)
    if name not in calls:
        raise RuntimeError(f"Native source does not define registered tool {name}")
    mutation_path = _mutation_path(module, name)
    signature = inspect.signature(tool)
    properties = native_schema["parameters"]["properties"]
    signature_fields = tuple(signature.parameters)
    schema_fields = tuple(sorted(properties))
    unsupported = sorted(
        (set(signature_fields) - set(schema_fields))
        | {
            field
            for field, descriptor in properties.items()
            if "type" not in descriptor and "enum" not in descriptor
        }
    )
    defaults: list[dict[str, Any]] = []
    for parameter in signature.parameters.values():
        if parameter.default is inspect.Parameter.empty:
            continue
        value, serializable = _json_safe_default(parameter.default)
        defaults.append(
            {
                "field": parameter.name,
                "json_serializable": serializable,
                "value_or_repr": value,
            }
        )
    source_text = source_path.read_bytes()
    source_lines, source_line = inspect.getsourcelines(tool)
    del source_lines
    return ToolEvidence(
        name=name,
        module=tool.__module__,
        qualname=tool.__qualname__,
        signature=str(signature),
        classification="effectful" if mutation_path else "read_only",
        mutation_path=mutation_path,
        source_file=str(source_path.relative_to(ROOT)),
        source_line=source_line,
        source_sha256=hashlib.sha256(source_text).hexdigest(),
        signature_fields=signature_fields,
        schema_fields=schema_fields,
        schema_required_fields=tuple(sorted(native_schema["parameters"]["required"])),
        default_bearing_fields=tuple(row["field"] for row in defaults),
        unsupported_schema_fields=tuple(unsupported),
        defaults=tuple(defaults),
        allowed_by_scenarios=allowed_by_scenarios,
    )


def build_tool_inventory(scenarios: Mapping[str, Any]) -> tuple[list[ToolEvidence], dict[str, Callable[..., Any]]]:
    """Enumerate the exact native allow lists for the bounded scenario slice."""

    from tool_sandbox.common.execution_context import set_current_context
    from tool_sandbox.common.tool_conversion import convert_to_openai_tool

    allowed_by: dict[str, list[str]] = {}
    native_tools: dict[str, Callable[..., Any]] = {}
    native_schemas: dict[str, dict[str, Any]] = {}
    for scenario_name in sorted(scenarios):
        context = scenarios[scenario_name].starting_context
        set_current_context(context)
        available = context.get_available_tools(scrambling_allowed=False)
        for name, tool in available.items():
            allowed_by.setdefault(name, []).append(scenario_name)
            native_tools.setdefault(name, tool)
            native_schemas.setdefault(name, convert_to_openai_tool(tool, name)["function"])
    evidence = [
        classify_tool(
            name=name,
            tool=native_tools[name],
            native_schema=native_schemas[name],
            allowed_by_scenarios=tuple(sorted(allowed_by[name])),
        )
        for name in sorted(native_tools)
    ]
    return evidence, native_tools


def _world_digest(context: Any) -> str:
    from tool_sandbox.common.execution_context import DatabaseNamespace

    world = {
        str(namespace): context.get_database(namespace).to_dicts()
        for namespace in DatabaseNamespace
        if namespace != DatabaseNamespace.SANDBOX
    }
    return hashlib.sha256(_canonical_json(world).encode()).hexdigest()


class NativeToolAdapter:
    """Fail-closed adapter around a scenario's exact native callable objects."""

    def __init__(self, context: Any, evidence: Mapping[str, ToolEvidence]) -> None:
        self.context = context
        self.tools = context.get_available_tools(scrambling_allowed=False)
        self.evidence = evidence
        self.precommits: list[dict[str, Any]] = []
        self.executed_effects: list[dict[str, Any]] = []
        self.successful_calls: list[dict[str, Any]] = []
        self.rejections: list[dict[str, Any]] = []

    def _reject(self, code: str, tool_name: str, fields: list[str]) -> None:
        rejection = {"code": code, "fields": sorted(fields), "tool_name": tool_name}
        self.rejections.append(rejection)
        raise AdapterRejection(code, tool_name, fields)

    def _append_native_trace_target(self) -> None:
        from tool_sandbox.common.execution_context import DatabaseNamespace, RoleType

        self.context.add_to_database(
            DatabaseNamespace.SANDBOX,
            [
                {
                    "content": "",
                    "recipient": RoleType.AGENT,
                    "sender": RoleType.EXECUTION_ENVIRONMENT,
                }
            ],
        )

    def invoke(self, tool_name: str, arguments: Mapping[str, Any]) -> Any:
        if tool_name not in self.tools:
            self._reject("tool_not_allowed", tool_name, [])
        if not isinstance(arguments, Mapping):
            self._reject("arguments_not_object", tool_name, [])
        tool = self.tools[tool_name]
        evidence = self.evidence[tool_name]
        argument_dict = dict(arguments)
        unsupported_call_fields = sorted(
            set(argument_dict) - set(evidence.signature_fields)
            | (set(argument_dict) - set(evidence.schema_fields))
        )
        if unsupported_call_fields:
            self._reject("unsupported_fields", tool_name, unsupported_call_fields)
        if evidence.classification == "effectful" and evidence.unsupported_schema_fields:
            self._reject(
                "effectful_tool_has_unsupported_schema_fields",
                tool_name,
                list(evidence.unsupported_schema_fields),
            )
        try:
            inspect.signature(tool).bind(**argument_dict)
        except TypeError:
            required = set(evidence.schema_required_fields)
            self._reject("invalid_signature_binding", tool_name, sorted(required - set(argument_dict)))
        if evidence.classification == "effectful":
            implicit_defaults = sorted(set(evidence.default_bearing_fields) - set(argument_dict))
            if implicit_defaults:
                self._reject("implicit_default_fields", tool_name, implicit_defaults)
        try:
            canonical_arguments = json.loads(_canonical_json(argument_dict))
        except (TypeError, ValueError):
            self._reject("non_json_arguments", tool_name, sorted(argument_dict))

        function_identity = {
            "module": tool.__module__,
            "name": tool.__name__,
            "qualname": tool.__qualname__,
            "signature": str(inspect.signature(tool)),
        }
        binding = {"arguments": canonical_arguments, "function": function_identity}
        binding_hash = hashlib.sha256(_canonical_json(binding).encode()).hexdigest()
        before_world = _world_digest(self.context)
        if evidence.classification == "effectful":
            self.precommits.append(
                {
                    "arguments": canonical_arguments,
                    "binding_hash": binding_hash,
                    "function": function_identity,
                    "sequence": len(self.precommits),
                }
            )

        self._append_native_trace_target()
        try:
            result = tool(**argument_dict)
        except Exception as exc:
            if evidence.classification == "effectful":
                self.executed_effects.append(
                    {
                        "arguments": canonical_arguments,
                        "binding_hash": binding_hash,
                        "error_type": type(exc).__name__,
                        "function": function_identity,
                        "outcome": "raised",
                        "state_changed": _world_digest(self.context) != before_world,
                    }
                )
            raise
        state_changed = _world_digest(self.context) != before_world
        self.successful_calls.append(
            {
                "binding_hash": binding_hash,
                "classification": evidence.classification,
                "state_changed": state_changed,
                "tool_name": tool_name,
            }
        )
        if evidence.classification == "effectful":
            self.executed_effects.append(
                {
                    "arguments": canonical_arguments,
                    "binding_hash": binding_hash,
                    "function": function_identity,
                    "outcome": "returned",
                    "state_changed": state_changed,
                }
            )
        return result


@contextmanager
def network_disabled() -> Iterator[dict[str, int]]:
    """Block socket connection attempts for the complete native replay."""

    counter = {"blocked_attempts": 0}

    def blocked(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        counter["blocked_attempts"] += 1
        raise RuntimeError("Network access is disabled for the E79 adapter smoke")

    with (
        patch.object(socket.socket, "connect", blocked),
        patch.object(socket.socket, "connect_ex", blocked),
        patch.object(socket, "create_connection", blocked),
    ):
        yield counter


def _append_agent_response(context: Any, content: str) -> None:
    from tool_sandbox.common.execution_context import DatabaseNamespace, RoleType

    context.add_to_database(
        DatabaseNamespace.SANDBOX,
        [{"content": content, "recipient": RoleType.USER, "sender": RoleType.AGENT}],
    )


def _evaluate_scenario(name: str, scenario: Any, adapter: NativeToolAdapter) -> dict[str, Any]:
    result = scenario.evaluation.evaluate(scenario.starting_context, scenario.max_messages)
    precommit_counts = Counter(row["binding_hash"] for row in adapter.precommits)
    execution_counts = Counter(row["binding_hash"] for row in adapter.executed_effects)
    return {
        "effect_calls": sum(
            row["classification"] == "effectful" for row in adapter.successful_calls
        ),
        "effect_calls_changed_native_world_state": all(
            row["state_changed"] for row in adapter.executed_effects
        ),
        "executed_effect_bindings": sorted(execution_counts.elements()),
        "executed_effect_records": list(adapter.executed_effects),
        "milestone_mapping_count": len(result.milestone_mapping),
        "milestone_similarity": float(result.milestone_similarity),
        "minefield_mapping_count": len(result.minefield_mapping),
        "minefield_similarity": float(result.minefield_similarity),
        "n_native_milestones": len(scenario.evaluation.milestone_matcher.milestones),
        "n_native_minefields": len(scenario.evaluation.minefield_matcher.milestones),
        "native_evaluator_invoked": True,
        "precommit_bindings": sorted(precommit_counts.elements()),
        "precommit_execution_exact_match": precommit_counts == execution_counts,
        "precommit_records": list(adapter.precommits),
        "read_calls": sum(
            row["classification"] == "read_only" for row in adapter.successful_calls
        ),
        "rejections": list(adapter.rejections),
        "scenario_name": name,
        "similarity": float(result.similarity),
        "successful_native_calls": len(adapter.successful_calls),
    }


def _run_modify_contact(scenario: Any, evidence: Mapping[str, ToolEvidence]) -> dict[str, Any]:
    from tool_sandbox.common.execution_context import set_current_context

    context = scenario.starting_context
    set_current_context(context)
    context.trace_tool = True
    adapter = NativeToolAdapter(context, evidence)
    now = adapter.invoke("get_current_timestamp", {})
    self_contact = adapter.invoke("search_contacts", {"is_self": True})[0]
    messages = adapter.invoke(
        "search_messages",
        {
            "creation_timestamp_upperbound": now,
            "sender_person_id": self_contact["person_id"],
        },
    )
    latest = max(
        (row for row in messages if row["recipient_person_id"] is not None),
        key=lambda row: row["creation_timestamp"],
    )
    target = adapter.invoke(
        "search_contacts", {"person_id": latest["recipient_person_id"]}
    )[0]
    try:
        adapter.invoke(
            "modify_contact",
            {"person_id": target["person_id"], "phone_number": "+10293847563"},
        )
    except AdapterRejection as exc:
        if exc.code != "implicit_default_fields":
            raise
    adapter.invoke(
        "modify_contact",
        {
            "is_self": target["is_self"],
            "name": target["name"],
            "person_id": target["person_id"],
            "phone_number": "+10293847563",
            "relationship": target["relationship"],
        },
    )
    _append_agent_response(
        context,
        "The phone number of the person you last talked to has been updated to +10293847563.",
    )
    return _evaluate_scenario("modify_contact_with_message_recency", scenario, adapter)


def _run_send_message(scenario: Any, evidence: Mapping[str, ToolEvidence]) -> dict[str, Any]:
    from tool_sandbox.common.execution_context import set_current_context

    context = scenario.starting_context
    set_current_context(context)
    context.trace_tool = True
    adapter = NativeToolAdapter(context, evidence)
    initial_cellular = adapter.invoke("get_cellular_service_status", {})
    if initial_cellular is not False:
        raise RuntimeError("Frozen scenario no longer starts with cellular service disabled")
    try:
        adapter.invoke(
            "set_cellular_service_status", {"on": True, "unsupported_field": "blocked"}
        )
    except AdapterRejection as exc:
        if exc.code != "unsupported_fields":
            raise
    adapter.invoke("set_cellular_service_status", {"on": True})
    contact = adapter.invoke("search_contacts", {"name": "Fredrik Thordendal"})[0]
    adapter.invoke(
        "send_message_with_phone_number",
        {
            "content": "How's the new album coming along",
            "phone_number": contact["phone_number"],
        },
    )
    _append_agent_response(
        context,
        "Your message to Fredrik Thordendal has been sent saying: "
        "How's the new album coming along",
    )
    return _evaluate_scenario(
        "send_message_with_contact_content_cellular_off", scenario, adapter
    )


def run_smoke() -> dict[str, Any]:
    _configure_import()
    from tool_sandbox.common.execution_context import ToolBackend
    from tool_sandbox.scenarios import named_scenarios

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest_rows = {row["scenario_name"]: row for row in manifest["scenarios"]}
    if not set(SMOKE_SCENARIOS) <= set(manifest_rows):
        raise RuntimeError("Smoke scenario is not in the frozen E79 manifest")
    all_scenarios = named_scenarios(preferred_tool_backend=ToolBackend.DEFAULT)
    scenarios = {name: copy.deepcopy(all_scenarios[name]) for name in SMOKE_SCENARIOS}
    for name, scenario in scenarios.items():
        frozen = manifest_rows[name]
        native_allowed = sorted(scenario.starting_context.tool_allow_list or [])
        if native_allowed != sorted(frozen["allowed_tools"]):
            raise RuntimeError(f"Native allow list drift for {name}")
        if len(scenario.evaluation.milestone_matcher.milestones) != frozen["n_milestones"]:
            raise RuntimeError(f"Native milestone drift for {name}")

    inventory, _ = build_tool_inventory(scenarios)
    evidence = {row.name: row for row in inventory}
    with network_disabled() as network:
        scenario_results = [
            _run_modify_contact(scenarios[SMOKE_SCENARIOS[0]], evidence),
            _run_send_message(scenarios[SMOKE_SCENARIOS[1]], evidence),
        ]

    rejections = [row for scenario in scenario_results for row in scenario["rejections"]]
    precommits = sum(len(row["precommit_bindings"]) for row in scenario_results)
    executions = sum(len(row["executed_effect_bindings"]) for row in scenario_results)
    precommit_counter = Counter(
        binding for row in scenario_results for binding in row["precommit_bindings"]
    )
    execution_counter = Counter(
        binding for row in scenario_results for binding in row["executed_effect_bindings"]
    )
    default_fields = sum(len(row.default_bearing_fields) for row in inventory)
    unsupported_schema_fields = sum(len(row.unsupported_schema_fields) for row in inventory)
    passed = all(
        (
            all(row["similarity"] == 1.0 for row in scenario_results),
            all(row["minefield_similarity"] == 0.0 for row in scenario_results),
            all(row["precommit_execution_exact_match"] for row in scenario_results),
            all(row["effect_calls_changed_native_world_state"] for row in scenario_results),
            precommit_counter == execution_counter,
            {row["code"] for row in rejections}
            == {"implicit_default_fields", "unsupported_fields"},
            network["blocked_attempts"] == 0,
        )
    )
    return {
        "claim_boundaries": {
            "not_established": [
                "victim-model security or prompt-injection robustness",
                "guard effectiveness, authorization soundness, or production complete mediation",
                "positive minefield detection because both bounded scenarios have zero native minefields",
                "coverage of the remaining 28 frozen scenarios or 20-plus-call horizons",
                "remote-service, concurrent-executor, or post-check mutation integrity",
            ],
            "scope": (
                "Implementation-readiness evidence only: two frozen native ToolSandbox scenarios, "
                "their local tools, exact precommit mediation, and native evaluation."
            ),
        },
        "controls": {
            "deterministic_scenario_order": list(SMOKE_SCENARIOS),
            "external_search_tools_selected": False,
            "llm_calls": 0,
            "network_blocked_attempts": network["blocked_attempts"],
            "network_connections_enabled": False,
            "user_simulator_runs": 0,
        },
        "experiment": "E79",
        "fail_closed_checks": {
            "default_bearing_signature_fields_detected": default_fields,
            "native_schema_unsupported_fields_detected": unsupported_schema_fields,
            "rejected_before_native_execution": len(rejections),
            "rejections": rejections,
        },
        "mediation_audit": {
            "effectful_calls_reaching_native_executor": executions,
            "effectful_calls_with_precommit": precommits,
            "extra_precommit_occurrences": sum((precommit_counter - execution_counter).values()),
            "missing_precommit_occurrences": sum((execution_counter - precommit_counter).values()),
            "signature_multiset_exact_match": precommit_counter == execution_counter,
        },
        "scenario_results": scenario_results,
        "smoke_type": "toolsandbox_native_adapter_implementation_readiness",
        "source": {
            "frozen_manifest": str(MANIFEST.relative_to(ROOT)),
            "local_snapshot": str(TOOL_SANDBOX.relative_to(ROOT)),
            "repository": manifest["source_repository"],
            "revision": manifest["source_revision"],
            "selection_hash": manifest["selection_hash"],
        },
        "status": "passed" if passed else "failed",
        "subset": {
            "n_frozen_scenarios": manifest["n_selected"],
            "n_smoke_scenarios": len(SMOKE_SCENARIOS),
            "scenario_names": list(SMOKE_SCENARIOS),
            "subset_membership_verified": True,
        },
        "tool_inventory": {
            "classification_counts": dict(
                sorted(Counter(row.classification for row in inventory).items())
            ),
            "n_unique_allowed_tools": len(inventory),
            "tools": [row.to_dict() for row in inventory],
        },
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    audit = report["mediation_audit"]
    fail_closed = report["fail_closed_checks"]
    lines = [
        "# E79 ToolSandbox Native Adapter Smoke",
        "",
        f"Status: `{report['status']}`.",
        "",
        report["claim_boundaries"]["scope"],
        "",
        "## Native Replay",
        "",
        "| Scenario | Native calls | Effect calls | Milestones | Minefields | Similarity |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in report["scenario_results"]:
        lines.append(
            f"| `{row['scenario_name']}` | {row['successful_native_calls']} | "
            f"{row['effect_calls']} | {row['n_native_milestones']} | "
            f"{row['n_native_minefields']} | {row['similarity']:.1f} |"
        )
    lines.extend(
        [
            "",
            "The native ToolSandbox milestone and minefield evaluator was invoked for each replay. "
            "Both selected scenarios have empty native minefield sets, so the zero minefield score "
            "does not test positive minefield detection.",
            "",
            "## Tool Evidence",
            "",
            "| Tool | Class | Defaults | Unsupported schema fields | Mutation path |",
            "|---|---|---|---|---|",
        ]
    )
    for row in report["tool_inventory"]["tools"]:
        path = " -> ".join(row["classification_evidence"]["mutation_path"]) or "none"
        defaults = ", ".join(row["default_bearing_fields"]) or "none"
        unsupported = ", ".join(row["schema_evidence"]["unsupported_schema_fields"]) or "none"
        lines.append(
            f"| `{row['tool_name']}` | `{row['classification']}` | {defaults} | "
            f"{unsupported} | `{path}` |"
        )
    lines.extend(
        [
            "",
            "Classification is derived from native implementation call paths to ToolSandbox database "
            "mutation primitives, not from tool names. Field coverage is checked against native "
            "ToolSandbox schemas and Python signatures.",
            "",
            "## Complete Mediation",
            "",
            f"- Effectful native calls: `{audit['effectful_calls_reaching_native_executor']}`.",
            f"- Exact precommit records: `{audit['effectful_calls_with_precommit']}`.",
            f"- Signature multiset exact match: `{audit['signature_multiset_exact_match']}`.",
            f"- Missing/extra precommits: `{audit['missing_precommit_occurrences']}`/`{audit['extra_precommit_occurrences']}`.",
            f"- Rejected before native execution: `{fail_closed['rejected_before_native_execution']}` "
            "(one omitted-default call and one unknown-field call).",
            "",
            "## Controls",
            "",
            "The replay made no LLM or user-simulator calls. Socket connections were disabled, "
            "and the selected native tools do not include ToolSandbox external-search tools.",
            "",
            "## Claim Boundary",
            "",
            report["claim_boundaries"]["scope"],
            "",
            "This smoke does not establish:",
            "",
        ]
    )
    lines.extend(f"- {claim}." for claim in report["claim_boundaries"]["not_established"])
    lines.append("")
    return "\n".join(lines)


def write_outputs(report: Mapping[str, Any]) -> None:
    RESULT_JSON.parent.mkdir(parents=True, exist_ok=True)
    RESULT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    RESULT_MD.write_text(render_markdown(report), encoding="utf-8")


def main() -> int:
    report = run_smoke()
    write_outputs(report)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
