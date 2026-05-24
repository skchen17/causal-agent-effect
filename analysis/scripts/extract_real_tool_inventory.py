"""Extract Hermes registered tool inventory with resolved schema variables.

Parses source files with AST, resolves schema=VAR references to their dict definitions,
extracts properties, required args, and filters pseudo-tools.
"""

from __future__ import annotations
import ast, json, sys, re
from pathlib import Path
from collections import defaultdict


def _ast_to_python(node: ast.AST) -> object:
    """Convert a literal AST node to a Python object."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return node.id  # Variable reference — will be resolved later
    if isinstance(node, ast.List):
        return [_ast_to_python(e) for e in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_ast_to_python(e) for e in node.elts)
    if isinstance(node, ast.Dict):
        result = {}
        for k, v in zip(node.keys, node.values):
            key = _ast_to_python(k)
            if isinstance(key, str):
                result[key] = _ast_to_python(v)
        return result
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_ast_to_python(node.operand)
    return None


def extract_schema_variables(source: str) -> dict[str, dict]:
    """Find all `VAR_NAME = { ... }` assignments at module level and return the dict values."""
    tree = ast.parse(source)
    schemas = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Dict):
                    name = target.id
                    val = _ast_to_python(node.value)
                    if isinstance(val, dict):
                        schemas[name] = val
    return schemas


def extract_register_calls(source: str, file_path: str) -> list[dict]:
    """Find all `registry.register(...)` calls and extract keyword arguments."""
    tree = ast.parse(source)
    source_lines = source.split("\n")
    results = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            if func.value.id == "registry" and func.attr == "register":
                kw = {}
                for kwarg in node.keywords:
                    kw[kwarg.arg] = _ast_to_python(kwarg.value)
                kw["_lineno"] = node.lineno
                kw["_source_file"] = file_path
                results.append(kw)
    return results


def resolve_schemas(register_calls: list[dict], schema_vars: dict) -> list[dict]:
    """Resolve schema=VAR references to actual schema dicts."""
    tools = []
    for call in register_calls:
        name = call.get("name", None)
        if not isinstance(name, str):
            continue

        # Filter pseudo-tools
        if name in ("tool_name_prefixed", "util_name"):
            continue
        if re.match(r'^[a-z]+_[a-z]+_[a-z]+$', name) and len(name.split('_')) > 3:
            # Suspicious pattern — mark but keep
            pass

        schema_ref = call.get("schema")
        schema_dict = None
        if isinstance(schema_ref, str) and schema_ref in schema_vars:
            schema_dict = schema_vars[schema_ref]
        elif isinstance(schema_ref, dict):
            schema_dict = schema_ref

        toolset = call.get("toolset", "")
        handler = call.get("handler", "")
        check_fn = call.get("check_fn", "")

        # Extract required args and properties from resolved schema
        required_args = []
        properties = {}
        schema_name = None
        schema_desc = ""
        extraction_status = "ok"
        notes = ""

        if schema_dict and isinstance(schema_dict, dict):
            schema_name = schema_dict.get("name", "")
            schema_desc = schema_dict.get("description", "")[:200] if schema_dict.get("description") else ""
            params = schema_dict.get("parameters", {})
            if isinstance(params, dict):
                properties = params.get("properties", {})
                required_args = params.get("required", [])
                if not isinstance(properties, dict):
                    notes += "properties_not_dict; "
                if not isinstance(required_args, list):
                    required_args = []
                    notes += "required_not_list; "
        elif isinstance(schema_ref, str) and schema_ref not in schema_vars:
            extraction_status = "unresolved_schema_var"
            notes = f"Schema variable '{schema_ref}' not found in module-level dicts"
        elif schema_ref is None:
            extraction_status = "no_schema"
            notes = "No schema argument in register call"
        else:
            extraction_status = "schema_not_dict"
            notes = f"Schema is {type(schema_ref).__name__}, not resolved"

        tools.append({
            "tool_name": name,
            "source_file": call.get("_source_file", ""),
            "lineno": call.get("_lineno", 0),
            "toolset": toolset if isinstance(toolset, str) else str(toolset),
            "handler": handler if isinstance(handler, str) else str(handler)[:80],
            "schema_name": schema_name,
            "required_args": required_args if isinstance(required_args, list) else [],
            "properties": properties if isinstance(properties, dict) else {},
            "check_fn": check_fn if isinstance(check_fn, str) else (str(check_fn)[:80] if check_fn else ""),
            "availability_gated": bool(check_fn),
            "extraction_status": extraction_status,
            "notes": notes.strip(),
        })

    return tools


def main():
    base = Path(__file__).parent.parent
    tools_dir = base / "real-agent-tools/hermes-agent-tools/tools"

    if not tools_dir.exists():
        print(f"ERROR: {tools_dir} not found", file=sys.stderr)
        sys.exit(1)

    all_calls = []
    all_schemas: dict[str, dict] = {}

    for fpath in sorted(tools_dir.glob("*.py")):
        try:
            source = fpath.read_text(encoding="utf-8")
        except Exception as e:
            print(f"  [SKIP] {fpath.name}: {e}", file=sys.stderr)
            continue

        # Extract both schemas and register calls
        schemas = extract_schema_variables(source)
        for name, val in schemas.items():
            all_schemas[f"{fpath.name}:{name}"] = val
            if name not in all_schemas:
                all_schemas[name] = val

        calls = extract_register_calls(source, f"real-agent-tools/hermes-agent-tools/tools/{fpath.name}")
        all_calls.extend(calls)

    tools = resolve_schemas(all_calls, all_schemas)

    # Stats
    n_ok = sum(1 for t in tools if t["extraction_status"] == "ok")
    n_unresolved = sum(1 for t in tools if t["extraction_status"] != "ok")
    n_with_req = sum(1 for t in tools if t["required_args"])
    n_with_props = sum(1 for t in tools if t["properties"])

    output = {
        "source_root": "real-agent-tools/hermes-agent-tools",
        "tools": sorted(tools, key=lambda t: t["tool_name"]),
        "n_tools": len(tools),
        "n_ok": n_ok,
        "n_unresolved": n_unresolved,
        "n_with_required_args": n_with_req,
        "n_with_properties": n_with_props,
    }

    # Save JSON
    out_json = base / "analysis/real_tool_inventory_hermes.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(output, indent=2, ensure_ascii=False, default=str))
    print(f"Saved {len(tools)} tools ({n_ok} ok, {n_unresolved} unresolved) to {out_json}")

    # Save MD
    out_md = base / "analysis/real_tool_inventory_hermes.md"
    lines = [
        "# Hermes Agent Tool Inventory",
        "",
        f"Extracted {len(tools)} tools | {n_ok} OK | {n_unresolved} unresolved",
        f"{n_with_req} with required args | {n_with_props} with properties",
        "",
        "## Core Tools",
        "",
        "| Tool Name | Toolset | Required Args | Handler | Gated | Status |",
        "|---|---|---|---|:---:|:---:|",
    ]
    for t in tools:
        name = t["tool_name"]
        ts = t["toolset"]
        reqs = ", ".join(t["required_args"][:5])
        handler = t["handler"][:40]
        gated = "✓" if t["availability_gated"] else "-"
        status = t["extraction_status"]
        lines.append(f"| {name} | {ts} | {reqs} | {handler} | {gated} | {status} |")

    lines += ["", "## Tools with Missing Schemas", ""]
    for t in tools:
        if t["extraction_status"] != "ok":
            lines.append(f"- **{t['tool_name']}**: {t['extraction_status']} — {t['notes']}")

    out_md.write_text("\n".join(lines))
    print(f"Saved markdown to {out_md}")


if __name__ == "__main__":
    main()
