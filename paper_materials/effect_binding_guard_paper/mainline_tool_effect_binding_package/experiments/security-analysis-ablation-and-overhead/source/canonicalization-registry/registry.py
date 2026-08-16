"""Canonicalization rule registry: schema, hashing, freeze/load.

Rule schema (registered rule):
  {
    "rule_id": str,
    "field_role": str,              # e.g. "amount", "subject_label"
    "tool": str,                    # scope anchor tool
    "transform": {"name": str, "params": dict},
    "scope": {"tools": [str], "roles": [str]},
    "rationale": str,               # structural argument (human-checkable)
    "validation_record": dict,      # counterfactual evidence (from validation.py)
    "frozen_hash": str,             # sha256 over the behavioral spec (excludes
                                    # validation_record and timestamps)
    "registered_at_utc": str
  }

The frozen hash covers rule_id, field_role, tool, transform, scope -- the
behavioral spec. It deliberately excludes the validation record and any
timestamp so that the hash identifies the rule's behavior and can be verified
at freeze/load time regardless of evidence bookkeeping.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from transforms import TRANSFORMS

REQUIRED_KEYS = ("rule_id", "field_role", "tool", "transform", "scope")
SCOPE_KEYS = ("tools", "roles")
TRANSFORM_KEYS = ("name",)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def behavioral_spec(rule: dict[str, Any]) -> dict[str, Any]:
    """The behavior-defining slice of a rule (hash input, never evidence)."""
    return {
        "rule_id": rule["rule_id"],
        "field_role": rule["field_role"],
        "tool": rule["tool"],
        "transform": rule["transform"],
        "scope": rule["scope"],
    }


def rule_frozen_hash(rule: dict[str, Any]) -> str:
    return sha256_hex(canonical_json(behavioral_spec(rule)))


def validate_rule_spec(rule: dict[str, Any]) -> list[str]:
    """Structural schema validation. Returns a list of error messages (empty=ok)."""
    errors: list[str] = []
    for key in REQUIRED_KEYS:
        if key not in rule:
            errors.append(f"missing required key '{key}'")
    if errors:
        return errors
    if not isinstance(rule["rule_id"], str) or not rule["rule_id"]:
        errors.append("rule_id must be a non-empty string")
    if not isinstance(rule["field_role"], str) or not rule["field_role"]:
        errors.append("field_role must be a non-empty string")
    if not isinstance(rule["tool"], str) or not rule["tool"]:
        errors.append("tool must be a non-empty string")
    transform = rule["transform"]
    if not isinstance(transform, dict) or "name" not in transform:
        errors.append("transform must be a dict with a 'name' key")
    elif transform["name"] not in TRANSFORMS:
        errors.append(f"unknown transform name '{transform['name']}'")
    scope = rule["scope"]
    if not isinstance(scope, dict):
        errors.append("scope must be a dict")
    else:
        for key in SCOPE_KEYS:
            if key not in scope:
                errors.append(f"scope missing '{key}'")
        for key in SCOPE_KEYS:
            value = scope.get(key)
            if not isinstance(value, (list, tuple)) or not value:
                errors.append(f"scope.{key} must be a non-empty list")
    return errors


class Registry:
    """An in-memory registry keyed by rule_id, with freeze/load support."""

    def __init__(self) -> None:
        self.rules: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # mutation
    # ------------------------------------------------------------------
    def add_rule(self, rule: dict[str, Any], validation_record: dict[str, Any] | None = None) -> None:
        errors = validate_rule_spec(rule)
        if errors:
            raise ValueError(f"invalid rule spec: {errors}")
        rule_id = rule["rule_id"]
        if rule_id in self.rules:
            raise ValueError(f"duplicate rule_id: {rule_id}")
        entry = dict(rule)
        if validation_record is not None:
            entry["validation_record"] = validation_record
        entry["frozen_hash"] = rule_frozen_hash(rule)
        self.rules[rule_id] = entry

    # ------------------------------------------------------------------
    # queries
    # ------------------------------------------------------------------
    def get(self, rule_id: str) -> dict[str, Any] | None:
        return self.rules.get(rule_id)

    def all_rules(self) -> list[dict[str, Any]]:
        return [self.rules[k] for k in sorted(self.rules)]

    def rules_for(self, role: str, tool: str | None = None) -> list[dict[str, Any]]:
        """Rules applicable to a role, optionally constrained to a tool's scope."""
        out: list[dict[str, Any]] = []
        for rule in self.all_rules():
            if rule["field_role"] != role:
                continue
            if tool is not None and tool not in rule["scope"]["tools"]:
                continue
            out.append(rule)
        return out

    def has_rule(self, rule_id: str) -> bool:
        return rule_id in self.rules

    # ------------------------------------------------------------------
    # freeze / load
    # ------------------------------------------------------------------
    def freeze(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "n_rules": len(self.rules),
            "rules": self.all_rules(),
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.freeze(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "Registry":
        data = json.loads(path.read_text(encoding="utf-8"))
        registry = cls()
        for rule in data["rules"]:
            registry.rules[rule["rule_id"]] = rule
        return registry

    def verify_frozen_hashes(self) -> list[str]:
        """Recompute each rule's frozen hash; return mismatched rule_ids."""
        mismatched: list[str] = []
        for rule_id, rule in self.rules.items():
            expected = rule.get("frozen_hash")
            actual = rule_frozen_hash(rule)
            if expected != actual:
                mismatched.append(rule_id)
        return mismatched

    def verify_frozen_file(self, path: Path) -> list[str]:
        """Verify a frozen registry file's hashes against its own contents."""
        data = json.loads(path.read_text(encoding="utf-8"))
        mismatched: list[str] = []
        for rule in data["rules"]:
            expected = rule.get("frozen_hash")
            actual = rule_frozen_hash(rule)
            if expected != actual:
                mismatched.append(rule["rule_id"])
        return mismatched
