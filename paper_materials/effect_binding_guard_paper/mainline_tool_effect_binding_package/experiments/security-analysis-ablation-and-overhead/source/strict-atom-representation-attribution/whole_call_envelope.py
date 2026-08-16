"""Whole-call envelope projection for protocol v2 (V1 ``opaque_whole_call``).

Protocol v2 revises the V1 definition (see
``paper/current-usenix/strict_atom_representation_attribution_protocol_v2_2026-08-05.md``):
the V1 monitor authorizes a totalized tool call as an INDIVISIBLE object by
exact-matching its canonical signature against a pre-registered envelope set
that is a deterministic projection of the frozen common plan cache.  No
field-level comparison, no per-field repair, and no reuse of the V3/E77
field comparator.

This module implements the OFFLINE projection half (registration).  The
runtime half (opaque exact-match lookup) lives in
``agentdojo_representation_patch.py`` and shares the two signature functions
defined here; unit tests assert byte-identical agreement between both halves
and against ``full_atom_runtime.call_signature``.

Registration rules (claim boundary)
-----------------------------------
The envelope set covers ONLY call shapes that are statically instantiable
from the frozen plan cache:

* a plan entry's tool projection is registrable iff every field binding in
  the plan's tool entry is either ``exact`` (with at least one value) or
  ``forbidden``; any ``resolve`` binding makes the whole call statically
  uninstantiable (whole-call representations cannot express "resolve this
  value from authorized evidence at runtime");
* ``exact`` bindings with multiple values enumerate the cartesian product of
  authorized whole calls (capped at ``MAX_COMBINATIONS_PER_TOOL_PLAN``);
* candidate argument objects are totalized by the SAME frozen pipeline used
  at runtime (``e77_runtime.totalize_registered_call`` with the frozen
  runtime catalog); candidates that do not totalize are not registered;
* forbidden fields are omitted from candidates; a call that sets a forbidden
  field can therefore never match a registered envelope;
* envelope authority is keyed by the canonical signature of the plan itself,
  so runtime plans produced by replan/revision (which are not part of the
  frozen cache) carry no envelopes and every call under them is
  NEEDS_REPLAN.  This is the pre-registered, expected "whole-call blindness"
  characterization, not an implementation defect.

Decision semantics at runtime (documented here for the registry artifact):

* ALLOW -- the totalized call signature equals a registered envelope
  signature of the current plan;
* NEEDS_REPLAN -- plan unavailable, tool not in plan, no envelope registered
  for the plan/tool, or signature mismatch.  The feedback is opaque
  (``checks == []``);
* DENY -- never emitted by the whole-call comparator itself (match/mismatch
  is binary); DENY rows can still arise through the shared revision-DENY
  recovery path, which is identical across all four variants.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from collections.abc import Mapping
from typing import Any

from src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.full_atom_runtime import (
    call_signature as runtime_call_signature,
)
from src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.e77_runtime import (
    totalize_registered_call,
)

# ---------------------------------------------------------------------------
# Canonical signatures.  These two functions are the ONLY serialization layer
# of the whole-call design; the runtime comparator must produce byte-identical
# signatures (enforced by unit tests).
# ---------------------------------------------------------------------------

#: Cap on the cartesian product of multi-valued exact bindings per tool entry.
MAX_COMBINATIONS_PER_TOOL_PLAN = 64


def canonical_json(obj: Any) -> str:
    """Deterministic JSON serialization used for all whole-call signatures."""
    return json.dumps(obj, sort_keys=True, default=str)


def plan_signature(plan: Mapping[str, Any]) -> str:
    """Indivisible identity of a permission plan (key of the envelope registry).

    Runtime plans are byte-identical JSON round-trips of the frozen cache
    entries, so the same plan content always hashes to the same key on both
    the offline projection side and the runtime comparator side.
    """
    return hashlib.sha256(canonical_json(plan).encode("utf-8")).hexdigest()


def whole_call_signature(tool_name: str, args: Mapping[str, Any]) -> str:
    """Indivisible identity of a totalized whole call.

    Deliberately identical to ``full_atom_runtime.call_signature`` (the
    signature already recorded in every runtime audit row); kept as a named
    wrapper so the whole-call contract has a single point of definition.
    """
    return runtime_call_signature(tool_name, dict(args))


# ---------------------------------------------------------------------------
# Projection of one plan-tool entry into envelope candidates.
# ---------------------------------------------------------------------------


def _exact_value_choices(
    fields: Mapping[str, Any],
) -> tuple[dict[str, list[Any]], list[str]]:
    """Collect per-field authorized value choices from plan bindings.

    Returns ``(choices, block_reasons)``; a non-empty ``block_reasons`` list
    means the whole call is not statically instantiable and no envelope may
    be registered.
    """
    choices: dict[str, list[Any]] = {}
    block_reasons: list[str] = []
    for field in sorted(fields):
        binding = fields.get(field)
        if not isinstance(binding, Mapping):
            block_reasons.append(f"binding_schema_invalid:{field}")
            continue
        mode = binding.get("mode")
        if mode == "resolve":
            # Whole-call representations cannot express runtime resolution of
            # a value from authorized evidence; the call is not statically
            # instantiable.  This is the core whole-call limitation.
            block_reasons.append(f"resolve_bound_field_not_instantiable:{field}")
        elif mode == "forbidden":
            # Forbidden fields must be absent from any authorized call; they
            # are simply not added to the candidate arguments.
            continue
        elif mode == "exact":
            values = binding.get("values")
            if not isinstance(values, list) or not values:
                block_reasons.append(f"exact_binding_without_values:{field}")
                continue
            choices[str(field)] = list(values)
        else:
            block_reasons.append(f"unknown_binding_mode:{field}")
    return choices, block_reasons


def project_tool_envelopes(
    tool_name: str,
    tool_plan: Mapping[str, Any],
    descriptor: Mapping[str, Any],
    totalization_catalog: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Project one plan-tool entry into registered whole-call envelopes.

    Uses the exact shared totalization pipeline (protocol section 5:
    totalization identical across variants).  Returns a registry row::

        {"status": "registered", "signatures": [...], "arguments": [...]}
        {"status": "not_instantiable", "signatures": [], "reasons": [...]}
    """
    fields = tool_plan.get("fields")
    if not isinstance(fields, Mapping):
        return {
            "status": "not_instantiable",
            "signatures": [],
            "reasons": ["plan_tool_entry_has_no_fields"],
        }
    choices, block_reasons = _exact_value_choices(fields)
    if block_reasons:
        return {
            "status": "not_instantiable",
            "signatures": [],
            "reasons": sorted(block_reasons),
        }

    field_names = sorted(choices)
    combinations: list[dict[str, Any]] = [{}]
    for field in field_names:
        combinations = [
            {**partial, field: value}
            for partial in combinations
            for value in choices[field]
        ]
        if len(combinations) > MAX_COMBINATIONS_PER_TOOL_PLAN:
            return {
                "status": "not_instantiable",
                "signatures": [],
                "reasons": [
                    "envelope_combination_limit_exceeded:"
                    f"{MAX_COMBINATIONS_PER_TOOL_PLAN}"
                ],
            }

    signatures: list[str] = []
    arguments: list[dict[str, Any]] = []
    totalization_failures: list[str] = []
    seen: set[str] = set()
    for candidate in combinations:
        totalized = totalize_registered_call(
            descriptor, candidate, totalization_catalog
        )
        if not totalized.get("resolved"):
            totalization_failures.extend(
                f"totalization_unresolved:{reason}"
                for reason in totalized.get("reasons", [])
            )
            continue
        total_args = dict(totalized.get("arguments") or {})
        signature = whole_call_signature(tool_name, total_args)
        if signature in seen:
            continue
        seen.add(signature)
        signatures.append(signature)
        arguments.append(total_args)

    if not signatures:
        reasons = sorted(set(totalization_failures)) or [
            "no_candidate_totalized"
        ]
        return {"status": "not_instantiable", "signatures": [], "reasons": reasons}
    return {
        "status": "registered",
        "signatures": signatures,
        "arguments": arguments,
        # Totalization failures of sibling candidates (multi-value products)
        # are retained for auditability; they never weaken registered rows.
        "partial_totalization_failures": sorted(set(totalization_failures)),
    }


# ---------------------------------------------------------------------------
# Projection of the whole frozen plan cache.
# ---------------------------------------------------------------------------


def project_plan_cache(
    plan_cache: Mapping[str, Any],
    registered_tool_names: list[str],
    totalization_catalog: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Project every accepted plan in the frozen cache into the registry.

    ``registered_tool_names`` are the 25 registered effectful/external tools
    of the experiment (protocol section 4); plan tool entries outside this
    set carry no whole-call authority and are skipped with an audit reason.
    Revision cache entries carry no plan authority and are ignored.
    """
    registered = set(registered_tool_names)
    envelopes: dict[str, dict[str, Any]] = {}
    summary = {
        "n_cache_entries": len(plan_cache),
        "n_accepted_plans": 0,
        "n_plans_with_registered_envelope": 0,
        "n_tool_plan_entries": 0,
        "n_tool_entries_registered": 0,
        "n_registered_envelopes": 0,
        "skip_reason_counts": {},
        "block_reason_counts": {},
    }

    def _bump(counter_name: str, reasons: list[str]) -> None:
        bucket = summary[counter_name]
        for reason in reasons:
            key = str(reason).split(":", 1)[0]
            bucket[key] = bucket.get(key, 0) + 1

    for prompt_hash in sorted(plan_cache):
        entry = plan_cache[prompt_hash]
        plan = entry.get("plan") if isinstance(entry, Mapping) else None
        if not isinstance(plan, Mapping):
            continue  # revision entry or rejected plan: no initial authority
        summary["n_accepted_plans"] += 1
        tools = plan.get("tools")
        if not isinstance(tools, Mapping):
            continue
        psig = plan_signature(plan)
        plan_row: dict[str, Any] = {}
        plan_has_envelope = False
        for tool_name in sorted(tools):
            tool_plan = tools[tool_name]
            if not isinstance(tool_plan, Mapping):
                continue
            summary["n_tool_plan_entries"] += 1
            if tool_name not in registered:
                plan_row[tool_name] = {
                    "status": "not_instantiable",
                    "signatures": [],
                    "reasons": ["tool_not_in_registered_effectful_set"],
                }
                _bump("skip_reason_counts", ["tool_not_in_registered_effectful_set"])
                continue
            descriptor = {"tool_name": tool_name, "side_effectful": True}
            row = project_tool_envelopes(
                tool_name, tool_plan, descriptor, totalization_catalog
            )
            plan_row[tool_name] = row
            if row["status"] == "registered":
                summary["n_tool_entries_registered"] += 1
                summary["n_registered_envelopes"] += len(row["signatures"])
                plan_has_envelope = True
            else:
                _bump("block_reason_counts", row.get("reasons", []))
        if plan_row:
            envelopes[psig] = plan_row
            if plan_has_envelope:
                summary["n_plans_with_registered_envelope"] += 1
    return {"envelopes": envelopes, "summary": summary}


# ---------------------------------------------------------------------------
# Registry loading + integrity verification (used by the runtime patch).
# ---------------------------------------------------------------------------


def verify_registry_bytes(registry_bytes: bytes, expected_sha256: str) -> bool:
    return hashlib.sha256(registry_bytes).hexdigest() == expected_sha256.lower()


def extract_lookup(
    registry: Mapping[str, Any],
) -> dict[str, dict[str, set[str]]]:
    """Build the runtime lookup: plan_signature -> tool -> signature set."""
    lookup: dict[str, dict[str, set[str]]] = {}
    for psig, tools in (registry.get("envelopes") or {}).items():
        if not isinstance(tools, Mapping):
            continue
        tool_map: dict[str, set[str]] = {}
        for tool_name, row in tools.items():
            if not isinstance(row, Mapping):
                continue
            signatures = row.get("signatures") or []
            tool_map[str(tool_name)] = {str(signature) for signature in signatures}
        lookup[str(psig)] = tool_map
    return lookup
