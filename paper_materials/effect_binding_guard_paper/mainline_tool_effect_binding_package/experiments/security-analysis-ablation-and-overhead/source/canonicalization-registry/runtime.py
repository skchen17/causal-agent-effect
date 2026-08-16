"""Runtime canonicalization entry point (runtime.py).

Canonicalize a value for a field role by applying the registered rule chain:

    canonicalize(role, value, tool=None)
      -> applies every registered rule whose field_role == role and whose
         scope contains the tool, in deterministic rule_id order.

Scope discipline (fail-closed): if no rule applies -- role unregistered,
tool out of scope, or the tool context is unknown (tool=None, so scope
coverage cannot be confirmed) -- the value is returned unchanged and the
caller keeps literal comparison.

Symmetry requirement (design): the exact-match path and the forbidden path
MUST use the same canonicalization function.  ``equivalent`` and
``forbidden_match`` both delegate to the same private helper
``_canonical_compare``; ``symmetry_audit`` records evidence that both paths
agree on a probe set.  The runtime is CPU-only, deterministic, O(len) per
rule (pure string transforms).

``canonicalize_args`` is the integration interface for the later runtime
wiring: it maps a tool-call argument dict's role-typed fields through
``canonicalize`` and returns a new dict.  V0-V3 frozen files are NOT touched
by this module.
"""
from __future__ import annotations

from typing import Any

from transforms import apply_transform


class CanonicalizationRuntime:
    """Runtime role -> rule-chain canonicalization with symmetry audit."""

    def __init__(self, registry: Any, oracle: Any | None = None) -> None:
        self.registry = registry
        self.oracle = oracle

    # ------------------------------------------------------------------
    # core canonicalization
    # ------------------------------------------------------------------
    def canonicalize(self, role: str, value: Any, tool: str | None = None) -> Any:
        """Canonical value of ``value`` for ``role`` under applicable rules.

        Fail-closed: without a tool context (tool=None) scope coverage cannot
        be confirmed, so the value is returned unchanged; out-of-scope tools
        likewise keep the literal value.
        """
        if tool is None:
            return value
        for rule in self.registry.rules_for(role, tool):
            value = apply_transform(rule["transform"], value)
        return value

    def _canonical_compare(
        self, role: str, v: Any, w: Any, tool: str | None = None
    ) -> tuple[Any, Any, bool]:
        """Shared implementation of both match paths (symmetry by construction)."""
        cv = self.canonicalize(role, v, tool)
        cw = self.canonicalize(role, w, tool)
        return cv, cw, cv == cw

    # ------------------------------------------------------------------
    # match paths (must be symmetric)
    # ------------------------------------------------------------------
    def equivalent(self, role: str, v: Any, w: Any, tool: str | None = None) -> bool:
        """Exact-match path: do v and w canonicalize to the same value?"""
        return self._canonical_compare(role, v, w, tool)[2]

    def forbidden_match(self, role: str, v: Any, w: Any, tool: str | None = None) -> bool:
        """Forbidden path: do v and w canonicalize to the same value?

        Identical to ``equivalent`` by construction -- both paths use the same
        canonicalization function, which is the framework's symmetry claim.
        """
        return self._canonical_compare(role, v, w, tool)[2]

    def symmetry_audit(
        self, role: str, pairs: list[tuple[Any, Any]], tool: str | None = None
    ) -> dict[str, Any]:
        """Record evidence that exact and forbidden paths agree on a probe set."""
        rows: list[dict[str, Any]] = []
        consistent = True
        for v, w in pairs:
            eq = self.equivalent(role, v, w, tool)
            fm = self.forbidden_match(role, v, w, tool)
            same_path = eq == fm
            consistent = consistent and same_path
            rows.append(
                {
                    "v": v,
                    "w": w,
                    "equivalent": eq,
                    "forbidden_match": fm,
                    "same_path": same_path,
                }
            )
        return {
            "role": role,
            "tool": tool,
            "n_pairs": len(rows),
            "consistent": consistent,
            "rows": rows,
        }

    # ------------------------------------------------------------------
    # integration interface
    # ------------------------------------------------------------------
    def canonicalize_args(
        self,
        tool: str,
        args: dict[str, Any],
        role_map: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Map a tool-call argument dict through canonicalization by role.

        ``role_map`` maps arg field -> role.  When omitted, the oracle's
        declared ``tool_arg_roles`` for ``tool`` is used (if an oracle was
        provided).  Fields without a declared role are left unchanged.
        Returns a new dict; the input is not mutated.
        """
        if role_map is None:
            role_map = {}
            if self.oracle is not None:
                role_map = self.oracle.tool_arg_roles.get(tool, {})
        out = dict(args)
        for field, value in args.items():
            role = role_map.get(field)
            if role is None:
                continue
            out[field] = self.canonicalize(role, value, tool)
        return out
