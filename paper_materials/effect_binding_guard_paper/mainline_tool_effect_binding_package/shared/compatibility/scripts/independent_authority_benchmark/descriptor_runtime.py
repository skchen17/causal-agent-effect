"""Interpreter for frozen, declarative typed-effect descriptors."""

from __future__ import annotations

import itertools
import json
from typing import Any


class _Missing:
    pass


MISSING = _Missing()


def _path(root: Any, path: str, env: dict[str, Any]) -> Any:
    rendered = path.format(**env)
    value = root
    for part in rendered.split(".") if rendered else []:
        if not isinstance(value, dict) or part not in value:
            return MISSING
        value = value[part]
    return value


def value(spec: Any, args: dict[str, Any], state: dict[str, Any], env: dict[str, Any]) -> Any:
    if not isinstance(spec, dict):
        return spec
    if "literal" in spec:
        return spec["literal"]
    if "arg" in spec:
        result = _path(args, spec["arg"], env)
        return value(spec["default"], args, state, env) if result is MISSING and "default" in spec else result
    if "state" in spec:
        result = _path(state, spec["state"], env)
        return value(spec["default"], args, state, env) if result is MISSING and "default" in spec else result
    if "var" in spec:
        return env.get(spec["var"], MISSING)
    if "resolve" in spec:
        raw = value(spec["resolve"]["value"], args, state, env)
        mapping = value(spec["resolve"]["mapping"], args, state, env)
        return mapping.get(raw, raw) if isinstance(mapping, dict) else MISSING
    if "coalesce" in spec:
        for candidate in spec["coalesce"]:
            result = value(candidate, args, state, env)
            if result is not MISSING and result is not None:
                return result
        return MISSING
    if "wrap" in spec:
        result = value(spec["wrap"], args, state, env)
        return [] if result is MISSING else [result]
    if "calc" in spec:
        values = [value(item, args, state, env) for item in spec["calc"]["values"]]
        if any(item is MISSING for item in values):
            return MISSING
        result = float(values[0])
        for item in values[1:]:
            result = result * float(item) if spec["calc"]["op"] == "mul" else result + float(item)
        return round(result, spec["calc"].get("round", 10))
    raise ValueError(f"unknown value expression: {spec}")


def condition(spec: dict[str, Any], args: dict[str, Any], state: dict[str, Any], env: dict[str, Any]) -> bool:
    if "all" in spec:
        return all(condition(item, args, state, env) for item in spec["all"])
    if "any" in spec:
        return any(condition(item, args, state, env) for item in spec["any"])
    if "not" in spec:
        return not condition(spec["not"], args, state, env)
    if "missing" in spec:
        return value(spec["missing"], args, state, env) is MISSING
    if "exists" in spec:
        return value(spec["exists"], args, state, env) is not MISSING
    for op in ("eq", "ne", "contains", "gt", "lt"):
        if op not in spec:
            continue
        left = value(spec[op][0], args, state, env)
        right = value(spec[op][1], args, state, env)
        if left is MISSING or right is MISSING:
            return False
        if op == "eq":
            return left == right
        if op == "ne":
            return left != right
        if op == "contains":
            return right in left
        if op == "gt":
            return float(left) > float(right)
        return float(left) < float(right)
    raise ValueError(f"unknown condition: {spec}")


def _canonical_atom(atom: dict[str, Any]) -> str:
    return json.dumps(atom, sort_keys=True, separators=(",", ":"))


def _evaluate_lets(specs: dict[str, Any], args: dict[str, Any], state: dict[str, Any], env: dict[str, Any]) -> None:
    """Resolve let dependencies without relying on JSON object key order."""
    pending = dict(specs)
    while pending:
        progressed = False
        for name, spec in list(pending.items()):
            try:
                env[name] = value(spec, args, state, env)
            except KeyError:
                continue
            del pending[name]
            progressed = True
        if not progressed:
            raise ValueError(f"unresolved let dependencies: {sorted(pending)}")


def compile_descriptor(descriptor: dict[str, Any], row: dict[str, Any]) -> list[dict[str, Any]]:
    if descriptor.get("tool_name") != row.get("tool_name") or descriptor.get("schema_version") != 1:
        raise ValueError("descriptor/tool/schema mismatch")
    args, state = row["arguments"], row["pre_state"]
    base_env: dict[str, Any] = {}
    _evaluate_lets(descriptor.get("lets", {}), args, state, base_env)
    atoms: list[dict[str, Any]] = []
    for rule in descriptor["rules"]:
        binding_names: list[str] = []
        binding_values: list[list[Any]] = []
        for binding in rule.get("bindings", []):
            source = value(binding["from"], args, state, base_env)
            if source is MISSING:
                source = []
            if not isinstance(source, list):
                raise ValueError(f"binding is not a list: {binding['name']}")
            binding_names.append(binding["name"])
            binding_values.append(source)
        products = itertools.product(*binding_values) if binding_values else [()]
        for product in products:
            env = dict(base_env)
            env.update(dict(zip(binding_names, product)))
            _evaluate_lets(rule.get("lets", {}), args, state, env)
            if "when" in rule and not condition(rule["when"], args, state, env):
                continue
            emit = rule["emit"]
            atom = {
                "effect": emit["effect"],
                "operation": emit["operation"],
                "resource_type": value(emit["resource_type"], args, state, env),
                "resource_id": value(emit["resource_id"], args, state, env),
                "target_principal": value(emit.get("target_principal", {"literal": None}), args, state, env),
                "qualifiers": {},
                "commit_mode": value(emit.get("commit_mode", {"literal": "commit"}), args, state, env),
            }
            for name, spec in emit.get("qualifiers", {}).items():
                result = value(spec, args, state, env)
                if result is not MISSING:
                    atom["qualifiers"][name] = result
            if any(item is MISSING for item in (atom["resource_type"], atom["resource_id"], atom["commit_mode"])):
                raise ValueError(f"unresolved required binding in {rule['rule_id']}")
            atoms.append(atom)
    return sorted(atoms, key=_canonical_atom)


def load_descriptors(path: str) -> dict[str, dict[str, Any]]:
    data = json.loads(open(path, encoding="utf-8").read())
    return {item["tool_name"]: item for item in data["descriptors"]}
