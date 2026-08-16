"""Finite-domain effect oracle for counterfactual validation.

The oracle is built from the frozen 56-call AgentDojo finite domain
(``finite-contexts.jsonl``), read-only:

  1. Load all 56 contexts; group by tool_instance_key.
  2. Learn, per tool, the argument -> effect-atom binding by matching observed
     value sets (identity binding, prefix template binding such as
     ``account_funds:{amount}``, and list fan-out binding such as
     participants -> one atom per participant).
  3. Calibrate: for every observed context, the model's projected effect
     signature must equal the observed effects' projected signature. A tool
     whose effects the model cannot reproduce (e.g. slack's opaque payload
     digest) is marked uncalibrated; rules scoped to it are fail-closed
     UNDETERMINED.

The oracle projects effect-atom leaves with the declared per-role semantics
(pre-registered in ``oracle_semantics``), which are rule-independent. The
differential compares projected effect signatures: identical signatures imply
identical safety-relevant effects and, because authorization is a
deterministic function of the effect signature in this framework, identical
authorization conclusions.

Deterministic, CPU-only, stdlib-only. No input file is modified.
"""
from __future__ import annotations

import copy
import json
import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from transforms import _PUNCT_RUN, _WS_RUN, parse_calendar_date, _NUMBER_TOKEN
from paths import EXPECTED_FINITE_CONTEXTS

_PREFIX_TEMPLATES = ("account_funds:", "payload:")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _flatten(value: Any, prefix: tuple[str, ...] = ()):
    if isinstance(value, dict):
        for key in sorted(value):
            yield from _flatten(value[key], prefix + (key,))
    else:
        yield (prefix, value)


def _set_leaf(container: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    """Set a leaf at ``path``, creating intermediate dicts as needed.

    Works both on pre-structured atoms (deep copies of observed effects) and
    on freshly built projection dicts.
    """
    node = container
    for part in path[:-1]:
        node = node.setdefault(part, {})
    node[path[-1]] = value


class DomainOracle:
    """Finite-domain effect oracle with per-tool calibration."""

    def __init__(
        self,
        contexts_path: Path,
        tool_arg_roles: dict[str, dict[str, str]],
        role_semantics: dict[str, dict[str, Any]],
    ) -> None:
        self.contexts_path = contexts_path
        self.tool_arg_roles = tool_arg_roles
        self.role_semantics = role_semantics
        self.rows = read_jsonl(contexts_path)
        if len(self.rows) != EXPECTED_FINITE_CONTEXTS:
            raise ValueError(
                f"frozen finite domain must contain {EXPECTED_FINITE_CONTEXTS} "
                f"contexts, found {len(self.rows)}"
            )
        self.per_tool: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in self.rows:
            self.per_tool[row["tool_instance_key"]].append(row)
        self.tool_info: dict[str, dict[str, Any]] = {}
        for tool, rows in self.per_tool.items():
            self.tool_info[tool] = self._learn_tool(tool, rows)
        self.calibration: dict[str, dict[str, Any]] = {}
        self.calibrated_tools: set[str] = set()
        self._calibrate()

    # ------------------------------------------------------------------
    # binding learning
    # ------------------------------------------------------------------
    def _learn_tool(self, tool: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        base = rows[0]
        base_args = dict(base["args"])
        base_atoms = copy.deepcopy(base["source_effects"])

        arg_values: dict[str, set[str]] = {}
        for row in rows:
            for key, value in row["args"].items():
                if isinstance(value, (list, tuple)):
                    continue
                arg_values.setdefault(key, set()).add(str(value))

        leaf_values: dict[tuple[str, ...], set[str]] = defaultdict(set)
        for row in rows:
            for atom in row["source_effects"]:
                for path, value in _flatten(atom):
                    leaf_values[path].add(str(value))

        bindings: dict[tuple[str, ...], dict[str, Any]] = {}
        for arg_field, avals in arg_values.items():
            role = self.tool_arg_roles.get(tool, {}).get(arg_field, "exact_string")
            for path, evals in list(leaf_values.items()):
                if path in bindings:
                    continue
                if evals == avals:
                    bindings[path] = {
                        "kind": "identity",
                        "arg_field": arg_field,
                        "role": role,
                    }
                    continue
                for prefix in _PREFIX_TEMPLATES:
                    stripped: set[str] = set()
                    ok = True
                    for entry in evals:
                        if not entry.startswith(prefix):
                            ok = False
                            break
                        stripped.add(entry[len(prefix):])
                    if ok and stripped == avals:
                        bindings[path] = {
                            "kind": "prefix",
                            "arg_field": arg_field,
                            "prefix": prefix,
                            "role": role,
                        }
                        break

        fanouts: list[tuple[str, tuple[str, ...]]] = []
        for arg_field, value in base_args.items():
            if not isinstance(value, (list, tuple)):
                continue
            flat: set[str] = set()
            for row in rows:
                for item in row["args"].get(arg_field, []):
                    flat.add(str(item))
            for path, evals in leaf_values.items():
                if evals == flat:
                    fanouts.append((arg_field, path))
                    break

        return {
            "base_args": base_args,
            "base_atoms": base_atoms,
            "bindings": bindings,
            "fanouts": fanouts,
        }

    # ------------------------------------------------------------------
    # effect model
    # ------------------------------------------------------------------
    def _render(self, binding: dict[str, Any], value: Any) -> Any:
        kind = binding["kind"]
        if kind == "identity":
            return value
        if kind == "prefix":
            return binding["prefix"] + str(value)
        raise ValueError(f"unknown binding kind: {kind}")

    def effect_multiset(self, tool: str, args: dict[str, Any]) -> list[dict[str, Any]]:
        info = self.tool_info[tool]
        if info["fanouts"]:
            arg_field, leaf = info["fanouts"][0]
            elements = list(args.get(arg_field, []))
            template = copy.deepcopy(info["base_atoms"][0])
            atoms = []
            for elem in elements:
                atom = copy.deepcopy(template)
                _set_leaf(atom, leaf, elem)
                for path, binding in info["bindings"].items():
                    _set_leaf(atom, path, self._render(binding, args.get(binding["arg_field"])))
                atoms.append(atom)
            return sorted(atoms, key=canonical_json)
        atoms = copy.deepcopy(info["base_atoms"])
        for path, binding in info["bindings"].items():
            rendered = self._render(binding, args.get(binding["arg_field"]))
            for atom in atoms:
                _set_leaf(atom, path, rendered)
        return sorted(atoms, key=canonical_json)

    # ------------------------------------------------------------------
    # role semantics projection
    # ------------------------------------------------------------------
    def project_value(self, role: str, value: Any) -> tuple[str, str]:
        sem = self.role_semantics.get(role, {"kind": "exact_string"})
        kind = sem["kind"]
        if kind == "numeric":
            match = _NUMBER_TOKEN.search(str(value))
            if match is None:
                return ("num", "unparseable:" + str(value))
            try:
                d = Decimal(match.group(0))
            except InvalidOperation:
                return ("num", "unparseable:" + str(value))
            if d == d.to_integral_value():
                return ("num", str(int(d)))
            return ("num", format(d.normalize(), "f"))
        if kind == "date":
            parsed = parse_calendar_date(
                value, sem.get("slash_convention", "MM/DD/YYYY")
            )
            if parsed is None:
                return ("date", "unparseable:" + str(value))
            return ("date", parsed.isoformat())
        if kind == "label":
            text = str(value)
            if sem.get("punctuation_run_fold", False):
                text = _PUNCT_RUN.sub(r"\1", text)
            if sem.get("whitespace_fold", False):
                text = _WS_RUN.sub(" ", text).strip()
            if sem.get("casefold", False):
                text = text.casefold()
            return ("label", text)
        if kind == "case_insensitive_string":
            return ("ci", str(value).casefold())
        return ("exact", str(value))

    def projected_signature(self, tool: str, args: dict[str, Any]) -> str:
        info = self.tool_info[tool]
        out = []
        for atom in self.effect_multiset(tool, args):
            projected = {}
            for path, value in _flatten(atom):
                binding = info["bindings"].get(path)
                role = binding["role"] if binding else "exact_string"
                _set_leaf(projected, path, self.project_value(role, value))
            out.append(projected)
        return canonical_json(sorted(out, key=canonical_json))

    def project_observed(self, tool: str, effects: list[dict[str, Any]]) -> str:
        info = self.tool_info[tool]
        out = []
        for atom in effects:
            projected = {}
            for path, value in _flatten(atom):
                binding = info["bindings"].get(path)
                role = binding["role"] if binding else "exact_string"
                _set_leaf(projected, path, self.project_value(role, value))
            out.append(projected)
        return canonical_json(sorted(out, key=canonical_json))

    # ------------------------------------------------------------------
    # calibration
    # ------------------------------------------------------------------
    def _calibrate(self) -> None:
        for tool, rows in self.per_tool.items():
            mismatches: list[str] = []
            for row in rows:
                observed = self.project_observed(tool, row["source_effects"])
                modeled = self.projected_signature(tool, row["args"])
                if observed != modeled:
                    mismatches.append(row["context_id"])
            self.calibration[tool] = {
                "calibrated": not mismatches,
                "n_contexts": len(rows),
                "mismatched_contexts": mismatches,
            }
            if not mismatches:
                self.calibrated_tools.add(tool)

    # ------------------------------------------------------------------
    # validation-facing queries
    # ------------------------------------------------------------------
    def arg_field_for_role(self, tool: str, role: str) -> str | None:
        for field, declared in self.tool_arg_roles.get(tool, {}).items():
            if declared == role:
                return field
        return None

    def is_calibrated(self, tool: str) -> bool:
        return tool in self.calibrated_tools

    def signature_for_role_value(self, tool: str, role: str, value: Any) -> str:
        """Projected effect signature of the tool call with ``role`` = value."""
        field = self.arg_field_for_role(tool, role)
        if field is None:
            raise ValueError(f"role '{role}' not declared for tool '{tool}'")
        args = dict(self.tool_info[tool]["base_args"])
        args[field] = value
        return self.projected_signature(tool, args)

    def value_observed(self, tool: str, role: str, value: Any) -> bool:
        field = self.arg_field_for_role(tool, role)
        if field is None:
            return False
        for row in self.per_tool[tool]:
            if str(row["args"].get(field)) == str(value):
                return True
        return False

    def calibration_summary(self) -> dict[str, Any]:
        total = sum(v["n_contexts"] for v in self.calibration.values())
        calibrated = sum(v["n_contexts"] for v in self.calibration.values() if v["calibrated"])
        return {
            "tools": sorted(self.calibration),
            "calibrated_tools": sorted(self.calibrated_tools),
            "n_contexts_total": total,
            "n_contexts_calibrated": calibrated,
            "calibrated_ratio": calibrated / total if total else None,
            "per_tool": self.calibration,
        }
