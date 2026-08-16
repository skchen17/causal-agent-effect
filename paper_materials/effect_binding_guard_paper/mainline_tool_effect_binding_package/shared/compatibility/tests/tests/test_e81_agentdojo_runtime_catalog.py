from __future__ import annotations

import json
from pathlib import Path

from src.experiments.effect_binding_guard.e80_contract_obligation_hardening import totalize_call
from src.experiments.effect_binding_guard.e81_agentdojo_hardened_runtime import compile_tool_semantics


ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "evaluation/e81_ablation/agentdojo_runtime_catalog.json"


def test_catalog_has_no_schema_descriptor_mismatches() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    assert catalog["status"] == "passed"
    assert catalog["errors"] == []
    assert catalog["registered_effectful_tool_names"] == 25
    assert catalog["security_field_semantics_counts"].get("dynamic_or_unknown", 0) == 0


def test_optional_static_security_default_is_totalized_before_check() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    selected = None
    for suite, tools in catalog["suites"].items():
        for name, tool in tools.items():
            optional = [
                field for field in tool["security_fields"]
                if tool["fields"][field]["kind"] == "static"
            ]
            if optional:
                selected = (suite, name, tool, optional[0])
                break
        if selected:
            break
    assert selected is not None
    suite, name, raw, optional_field = selected
    compiled = compile_tool_semantics(catalog, suite, name)
    arguments = {
        field: "fixture"
        for field, semantics in raw["fields"].items()
        if semantics["kind"] == "required"
    }
    result = totalize_call(arguments, compiled.field_semantics)
    assert result.resolved is True
    assert optional_field in result.arguments
    assert optional_field in result.instantiated_defaults


def test_unknown_call_field_fails_totalization() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    suite = next(iter(catalog["suites"]))
    name = next(iter(catalog["suites"][suite]))
    compiled = compile_tool_semantics(catalog, suite, name)
    result = totalize_call({"not_in_schema": "x"}, compiled.field_semantics)
    assert result.resolved is False
    assert result.reasons == ("unknown_field:not_in_schema",)
