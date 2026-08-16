"""Disposable adapters around independently authored MCP implementations."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any

from .mcp_client import MCPClient


ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / "experiments/human-authority-and-causal-validation/runs/third-party-tool-interface-validation"
SOURCES = RUN / "sources"


COMMANDS = {
    "filesystem": ["node", str(SOURCES / "modelcontextprotocol-servers/src/filesystem/dist/index.js")],
    "sqlite": ["node", str(SOURCES / "mcp-sqlite/mcp-sqlite-server.js")],
    "memory": ["node", str(SOURCES / "simple-memory-mcp/index.js")],
}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _filesystem_snapshot(root: Path) -> dict[str, Any]:
    entries: dict[str, Any] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            entries[relative] = {"kind": "directory"}
        elif path.is_file():
            data = path.read_bytes()
            entries[relative] = {
                "kind": "file", "size": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                "text": data.decode("utf-8", errors="replace"),
            }
    return {"entries": entries}


def _sqlite_snapshot(path: Path) -> dict[str, Any]:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    tables = {}
    for table in ("records", "secrets"):
        rows = [dict(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY id")]
        tables[table] = rows
    connection.close()
    return {"tables": tables}


def _memory_snapshot(directory: Path) -> dict[str, Any]:
    path = directory / "memory.json"
    if not path.exists():
        return {"entities": [], "relations": []}
    value = json.loads(path.read_text(encoding="utf-8"))
    return {
        "entities": sorted(value.get("entities", []), key=lambda item: item["name"]),
        "relations": sorted(value.get("relations", []), key=lambda item: (item["from"], item["to"], item["relationType"])),
    }


def _prepare_filesystem(root: Path, fixture: dict[str, Any]) -> None:
    for relative, value in fixture.get("entries", {}).items():
        path = root / relative
        if value is None:
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(value), encoding="utf-8")


def _prepare_sqlite(path: Path, fixture: dict[str, Any]) -> None:
    connection = sqlite3.connect(path)
    for table in ("records", "secrets"):
        connection.execute(
            f"CREATE TABLE {table}(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, owner TEXT, visibility TEXT, value TEXT)"
        )
        for row in fixture.get("tables", {}).get(table, []):
            connection.execute(
                f"INSERT INTO {table}(id,name,owner,visibility,value) VALUES(?,?,?,?,?)",
                (row["id"], row["name"], row["owner"], row["visibility"], row["value"]),
            )
    connection.commit()
    connection.close()


def _prepare_memory(directory: Path, fixture: dict[str, Any]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "memory.json").write_text(json.dumps({
        "entities": fixture.get("entities", []), "relations": fixture.get("relations", []),
    }, indent=2), encoding="utf-8")


def execute(row: dict[str, Any]) -> dict[str, Any]:
    """Execute one call in fresh disposable state and return normalized snapshots."""

    source = row["source"]
    with tempfile.TemporaryDirectory(prefix=f"third-party-{source}-") as temporary:
        root = Path(temporary)
        arguments = json.loads(json.dumps(row["arguments"]))
        env: dict[str, str] = {}
        if source == "filesystem":
            _prepare_filesystem(root, row["fixture"])
            before = _filesystem_snapshot(root)
            for field in ("path", "source", "destination"):
                if field in arguments:
                    arguments[field] = str(root / arguments[field])
            command = [*COMMANDS[source], str(root)]
        elif source == "sqlite":
            database = root / "fixture.sqlite"
            _prepare_sqlite(database, row["fixture"])
            before = _sqlite_snapshot(database)
            command = [*COMMANDS[source], str(database)]
        elif source == "memory":
            memory_dir = root / "memory"
            _prepare_memory(memory_dir, row["fixture"])
            before = _memory_snapshot(memory_dir)
            command = COMMANDS[source]
            env["MEMORY_PATH"] = str(memory_dir)
        else:
            raise ValueError(source)

        error = None
        raw_result: dict[str, Any] | None = None
        try:
            with MCPClient(command, env=env) as client:
                if source == "memory":
                    # This third-party server starts loadMemory() asynchronously.
                    # Wait for its declared fixture to become observable before the
                    # evaluated call, then allow its un-awaited saveMemory() to drain.
                    expected_names = {item["name"] for item in row["fixture"].get("entities", [])}
                    for _ in range(40):
                        graph = client.call("read_graph", {})
                        content = json.loads(graph["content"][0]["text"])
                        if {item["name"] for item in content.get("entities", [])} == expected_names:
                            break
                        time.sleep(0.01)
                    else:
                        raise RuntimeError("memory fixture did not load before evaluated call")
                raw_result = client.call(row["tool_name"], arguments)
                if source == "memory":
                    time.sleep(0.05)
        except Exception as exc:
            error = f"{type(exc).__name__}:{exc}"

        if source == "filesystem":
            after = _filesystem_snapshot(root)
        elif source == "sqlite":
            after = _sqlite_snapshot(database)
        else:
            after = _memory_snapshot(memory_dir)
        return {
            "before": before, "after": after, "raw_result": raw_result, "execution_error": error,
            "materialized_arguments_sha256": _sha(canonical(arguments)),
        }


def discover_schemas() -> dict[str, list[dict[str, Any]]]:
    """Run tools/list against all three pinned source implementations."""

    output = {}
    with tempfile.TemporaryDirectory(prefix="third-party-schema-") as temporary:
        root = Path(temporary)
        (root / "fs").mkdir()
        database = root / "schema.sqlite"
        _prepare_sqlite(database, {})
        memory = root / "memory"
        _prepare_memory(memory, {})
        configs = {
            "filesystem": ([*COMMANDS["filesystem"], str(root / "fs")], {}),
            "sqlite": ([*COMMANDS["sqlite"], str(database)], {}),
            "memory": (COMMANDS["memory"], {"MEMORY_PATH": str(memory)}),
        }
        for name, (command, env) in configs.items():
            with MCPClient(command, env=env) as client:
                output[name] = client.list_tools()
    return output


def referenced_state(row: dict[str, Any], before: dict[str, Any]) -> dict[str, Any]:
    """Effect-free trusted state for resources explicitly named by the call."""

    args, source = row["arguments"], row["source"]
    if source == "filesystem":
        names = [args[key] for key in ("path", "source", "destination") if key in args]
        return {name: before["entries"].get(name) for name in names}
    if source == "sqlite":
        table = args["table"]
        conditions = args.get("conditions", {})
        matched = [item for item in before["tables"].get(table, []) if all(item.get(k) == v for k, v in conditions.items())]
        return {"table": table, "matched_records": matched, "table_exists": table in before["tables"]}
    names = set(args.get("entityNames", []))
    names.update(item.get("name") for item in args.get("entities", []))
    names.update(item.get("entityName") for item in args.get("observations", []))
    for relation in args.get("relations", []):
        names.update((relation.get("from"), relation.get("to")))
    return {
        "entities": [item for item in before["entities"] if item["name"] in names],
        "relations": [item for item in before["relations"] if item["from"] in names or item["to"] in names],
    }
