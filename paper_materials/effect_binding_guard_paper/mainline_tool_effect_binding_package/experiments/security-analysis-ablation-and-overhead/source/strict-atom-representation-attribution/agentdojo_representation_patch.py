"""AgentDojo representation patch for the strict atom attribution protocol.

This module implements the four pre-commit representation variants (V0--V3) of
the frozen protocol
``paper/current-usenix/strict_atom_representation_attribution_protocol_2026-08-03.md``
as revised by protocol v2
(``paper/current-usenix/strict_atom_representation_attribution_protocol_v2_2026-08-05.md``).

Design (mirrors the sanctioned ``representation_closed_loop_attribution``
ablation precedent): the shared agent execution path -- planner, replan,
revision, totalization, canonicalization, authorized-read resolver, recovery
policy, uncertainty policy, sandbox execution and the official AgentDojo
scorers -- is provided verbatim by ``agentdojo_e77_runtime_patch``.  This
module is loaded *after* that patch and changes exactly one thing: the
pre-commit comparison function that the already-installed runtime wrapper
calls.  Everything else is held constant across variants (protocol sections 4
and 5).

The variant is selected with ``STRICT_ATTRIB_VARIANT``:

    tool_identity_only      V0 -- planned tool name only
    opaque_whole_call       V1 -- TRUE whole call (protocol v2): indivisible
                                  signature exact-match against the
                                  pre-registered envelope registry
    raw_schema_fields       V2 -- every schema parameter is a security field
    validated_atom_fields   V3 -- counterfactually registered atom fields

V3 leaves the E77 comparator untouched; it is the main-method condition.  V0,
V1 and V2 replace it with a variant-specific comparator that emits the same
``{"decision", "reasons", "checks"}`` shape so the surrounding recovery and
uncertainty machinery behaves consistently.

Protocol v2 V1 semantics (方案 A / true whole call): the totalized call is
serialized into an INDIVISIBLE canonical signature and exact-matched against
the pre-registered whole-call envelope registry
(``whole-call-envelopes.json``, a deterministic projection of the frozen
common plan cache; see ``whole_call_envelope.py`` and the registration rules
document).  The V1 comparator performs NO field decomposition, NO per-field
repair and NEVER calls the V3/E77 field-level comparator; its feedback is
opaque (``checks == []``).  It emits ALLOW or NEEDS_REPLAN only; DENY is
reachable exclusively through the shared revision-DENY recovery path, which is
identical across all four variants.

Read-only authority: the runner seeds a *private copy* of
``frozen-common-plan-cache.json`` and points ``E77_PLAN_CACHE`` at that copy,
so the frozen common cache is never written back (protocol section 3.3).
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline

from src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard import (
    agentdojo_e77_runtime_patch as e77_patch,
)
from src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard import (
    e77_runtime,
)

VARIANT_ENV = "STRICT_ATTRIB_VARIANT"
PATCHED_ENV = "STRICT_ATTRIB_VARIANT_PATCHED"
RAW_SCHEMA_REGISTRY_ENV = "STRICT_ATTRIB_RAW_SCHEMA_REGISTRY"
WHOLE_CALL_ENVELOPES_ENV = "STRICT_ATTRIB_WHOLE_CALL_ENVELOPES"

WHOLE_CALL_REGISTRY_ARTIFACT_TYPE = "whole_call_envelope_registry"
WHOLE_CALL_REGISTRY_RULE_VERSION = "whole_call_exact_match_v2"

VARIANTS = (
    "tool_identity_only",
    "opaque_whole_call",
    "raw_schema_fields",
    "validated_atom_fields",
)

ComparisonFn = Callable[..., dict[str, Any]]


def _selected_variant() -> str:
    variant = os.getenv(VARIANT_ENV, "").strip()
    if variant not in VARIANTS:
        raise RuntimeError(
            f"{VARIANT_ENV} must be one of {VARIANTS}, got {variant!r}"
        )
    return variant


def _load_raw_schema_registry() -> dict[str, dict[str, Any]]:
    """Load the frozen V2 raw-schema-field registry keyed by tool name."""
    path = os.getenv(RAW_SCHEMA_REGISTRY_ENV, "")
    if not path:
        raise RuntimeError(f"{RAW_SCHEMA_REGISTRY_ENV} is not set")
    registry: dict[str, dict[str, Any]] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        registry[str(row["tool_name"])] = row
    return registry


# ---------------------------------------------------------------------------
# V0: tool identity only.
# ---------------------------------------------------------------------------


def compare_tool_identity_only(
    user_task: str,
    descriptor: Mapping[str, Any],
    plan: Mapping[str, Any] | None,
    args: Mapping[str, Any],
    authorized_read_evidence: list[Any],
    runtime_defaults: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Authorize by planned tool identity without inspecting effect fields.

    Reuses the ``representation_closed_loop_attribution`` semantics; the
    signature intentionally matches E77's atom-level comparator.
    """
    del user_task, args, authorized_read_evidence, runtime_defaults
    tools = plan.get("tools") if isinstance(plan, Mapping) else None
    if not isinstance(tools, Mapping):
        return {
            "decision": "NEEDS_REPLAN",
            "reasons": ["task_permission_plan_unavailable"],
            "checks": [],
        }
    tool_name = str(descriptor.get("tool_name", ""))
    if tool_name not in tools:
        return {
            "decision": "NEEDS_REPLAN",
            "reasons": ["tool_not_in_initial_permission_plan"],
            "checks": [],
        }
    return {
        "decision": "ALLOW",
        "reasons": ["tool_identity_present_in_initial_permission_plan"],
        "checks": [],
    }


# ---------------------------------------------------------------------------
# V1 (protocol v2): TRUE opaque whole call -- indivisible signature
# exact-match against the pre-registered envelope registry.
#
# No field decomposition, no per-field repair, and no reuse of the V3/E77
# field comparator.  The two signature functions below are the ONLY
# serialization layer of the whole-call design; unit tests enforce
# byte-identical agreement with ``whole_call_envelope.py`` (offline
# projection half) and with ``full_atom_runtime.call_signature`` (the audit
# signature recorded in every runtime row).
# ---------------------------------------------------------------------------


def whole_call_canonical_json(obj: Any) -> str:
    """Deterministic JSON serialization used for all whole-call signatures."""
    return json.dumps(obj, sort_keys=True, default=str)


def whole_call_plan_signature(plan: Mapping[str, Any]) -> str:
    """Indivisible identity of a permission plan (key of the envelope registry).

    Runtime plans are byte-identical JSON round-trips of the frozen cache
    entries, so the same plan content hashes to the same key on both the
    offline projection side and this runtime comparator side.
    """
    return hashlib.sha256(whole_call_canonical_json(plan).encode("utf-8")).hexdigest()


def whole_call_signature(tool_name: str, args: Mapping[str, Any]) -> str:
    """Indivisible identity of a totalized whole call.

    Deliberately identical to ``full_atom_runtime.call_signature``: the
    runtime wrapper computes the audit ``call_signature`` from the SAME
    totalized argument mapping that this comparator receives.
    """
    return hashlib.sha256(
        json.dumps(
            {"tool_name": tool_name, "args": dict(args)},
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _load_whole_call_envelopes() -> dict[str, dict[str, set[str]]]:
    """Load the pre-registered whole-call envelope registry (fail closed).

    Integrity rules (protocol v2, D4): the registry path comes from
    ``STRICT_ATTRIB_WHOLE_CALL_ENVELOPES``; the ``.sha256`` sidecar must
    exist and match the file bytes; the artifact must declare the protocol v2
    artifact type and rule version.  Any violation raises before a single case
    runs.  Returns the runtime lookup ``plan_signature -> tool -> signatures``.
    """
    path = os.getenv(WHOLE_CALL_ENVELOPES_ENV, "")
    if not path:
        raise RuntimeError(
            f"{WHOLE_CALL_ENVELOPES_ENV} is not set (protocol v2 V1 requires "
            "the pre-registered whole-call envelope registry)"
        )
    payload = Path(path).read_bytes()
    sidecar = Path(f"{path}.sha256")
    if not sidecar.exists():
        raise RuntimeError(f"whole-call envelope sidecar missing: {sidecar}")
    expected = sidecar.read_text(encoding="utf-8").split()[0].strip().lower()
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise RuntimeError(
            f"whole-call envelope registry hash mismatch: {actual} != {expected}"
        )
    registry = json.loads(payload.decode("utf-8"))
    if registry.get("artifact_type") != WHOLE_CALL_REGISTRY_ARTIFACT_TYPE:
        raise RuntimeError(
            "whole-call registry artifact_type mismatch: "
            f"{registry.get('artifact_type')!r}"
        )
    if registry.get("rule_version") != WHOLE_CALL_REGISTRY_RULE_VERSION:
        raise RuntimeError(
            "whole-call registry rule_version mismatch: "
            f"{registry.get('rule_version')!r}"
        )
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


def _make_opaque_whole_call(
    envelope_lookup: Mapping[str, Mapping[str, set[str]]],
) -> ComparisonFn:
    def compare_opaque_whole_call(
        user_task: str,
        descriptor: Mapping[str, Any],
        plan: Mapping[str, Any] | None,
        args: Mapping[str, Any],
        authorized_read_evidence: list[Any],
        runtime_defaults: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Authorize a totalized call as an INDIVISIBLE whole (protocol v2).

        The call's canonical signature is exact-matched against the
        pre-registered envelope set of the current plan.  The verdict is a
        single opaque call-level decision with ``checks == []``: no per-field
        detail, no per-target expansion, no field-level repair, and the
        V3/E77 field comparator is never consulted.

        Decision semantics: ALLOW on signature equality with a registered
        envelope of the current plan; NEEDS_REPLAN otherwise (plan
        unavailable, tool not in plan, no registered envelope for the
        plan/tool -- e.g. runtime-revised plans carry no whole-call authority
        -- or signature mismatch).  DENY is never emitted here; it is
        reachable only via the shared revision-DENY recovery path.
        """
        del user_task, authorized_read_evidence, runtime_defaults
        tools = plan.get("tools") if isinstance(plan, Mapping) else None
        if not isinstance(tools, Mapping):
            return {
                "decision": "NEEDS_REPLAN",
                "reasons": ["task_permission_plan_unavailable"],
                "checks": [],
            }
        tool_name = str(descriptor.get("tool_name", ""))
        if tool_name not in tools:
            return {
                "decision": "NEEDS_REPLAN",
                "reasons": ["tool_not_in_initial_permission_plan"],
                "checks": [],
            }
        plan_key = whole_call_plan_signature(plan)
        registered = envelope_lookup.get(plan_key, {}).get(tool_name)
        if not registered:
            return {
                "decision": "NEEDS_REPLAN",
                "reasons": ["whole_call_envelope_not_registered"],
                "checks": [],
            }
        if whole_call_signature(tool_name, args) in registered:
            return {
                "decision": "ALLOW",
                "reasons": ["whole_call_within_authorized_envelope"],
                "checks": [],
            }
        return {
            "decision": "NEEDS_REPLAN",
            "reasons": ["whole_call_outside_authorized_envelope"],
            "checks": [],
        }

    return compare_opaque_whole_call


# ---------------------------------------------------------------------------
# V2: raw schema fields -- every schema parameter is a security field.
# ---------------------------------------------------------------------------


def _make_raw_schema_fields(
    base_compare: ComparisonFn,
    raw_schema_registry: Mapping[str, Mapping[str, Any]],
) -> ComparisonFn:
    def compare_raw_schema_fields(
        user_task: str,
        descriptor: Mapping[str, Any],
        plan: Mapping[str, Any] | None,
        args: Mapping[str, Any],
        authorized_read_evidence: list[Any],
        runtime_defaults: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run the shared comparator over every official schema parameter.

        The descriptor's security_fields/field_roles are replaced by the
        mechanically generated raw-schema registry (role fixed to
        ``untyped_argument``); the field-value comparator, totalization and
        recovery stay identical to V3 (protocol section 4 V2).  Unknown or
        extra parameters fail closed.
        """
        tool_name = str(descriptor.get("tool_name", ""))
        raw = raw_schema_registry.get(tool_name)
        if raw is None:
            # Only registered effectful tools are in scope; anything else is
            # handled upstream (unregistered tools never reach this view).
            return base_compare(
                user_task,
                descriptor,
                plan,
                args,
                authorized_read_evidence,
                runtime_defaults,
            )
        raw_descriptor = dict(descriptor)
        raw_descriptor["security_fields"] = list(raw.get("security_fields", []))
        raw_descriptor["field_roles"] = dict(raw.get("field_roles", {}))
        comparison = dict(
            base_compare(
                user_task,
                raw_descriptor,
                plan,
                args,
                authorized_read_evidence,
                runtime_defaults,
            )
        )
        schema_fields = set(raw.get("security_fields", []))
        extra = sorted(str(key) for key in (args or {}) if key not in schema_fields)
        if extra:
            comparison["decision"] = (
                "DENY"
                if comparison.get("decision") == "DENY"
                else "NEEDS_REPLAN"
            )
            comparison["reasons"] = list(comparison.get("reasons", [])) + [
                f"unknown_parameter:{field}" for field in extra
            ]
            comparison.setdefault("checks", [])
        return comparison

    return compare_raw_schema_fields


# ---------------------------------------------------------------------------
# Comparator selection and installation.
# ---------------------------------------------------------------------------


def select_variant_comparator(
    variant: str,
    base_compare: ComparisonFn,
    raw_schema_registry: Mapping[str, Mapping[str, Any]],
    whole_call_envelopes: Mapping[str, Mapping[str, set[str]]] | None = None,
) -> ComparisonFn:
    """Return the pre-commit comparator for ``variant`` (protocol section 4).

    Protocol v2: the V1 comparator receives the pre-registered whole-call
    envelope lookup and NEVER ``base_compare``; V0/V2/V3 wiring is unchanged.
    """
    if variant == "validated_atom_fields":
        return base_compare
    if variant == "tool_identity_only":
        return compare_tool_identity_only
    if variant == "opaque_whole_call":
        return _make_opaque_whole_call(whole_call_envelopes or {})
    if variant == "raw_schema_fields":
        return _make_raw_schema_fields(base_compare, raw_schema_registry)
    raise ValueError(f"unknown variant: {variant!r}")


def _patch_pipeline_name(variant: str) -> None:
    original = AgentPipeline.from_config.__func__
    suffix = f"-strict_{variant}"

    def named(cls: type[AgentPipeline], config: Any) -> AgentPipeline:
        pipeline = original(cls, config)
        name = getattr(pipeline, "name", None) or "local"
        if not name.endswith(suffix):
            pipeline.name = f"{name}{suffix}"
        return pipeline

    AgentPipeline.from_config = classmethod(named)


def install_variant(variant: str) -> None:
    """Swap the pre-commit comparator in the already-installed E77 runtime.

    Both the E77 patch module global (main pre-commit + planner-replan
    recheck) and the ``e77_runtime`` global (revision validation path) are
    replaced so the variant view is applied at every comparison point.

    Runtime tag: protocol v2 revises ONLY the V1 comparator (true whole-call
    semantics, tag ``_v2``); V0/V2/V3 keep the ``_v1`` tag byte-identically so
    their audit rows remain comparable with protocol v1 runs.
    """
    base_compare = e77_patch.compare_call_to_plan_with_evidence
    raw_schema_registry = (
        _load_raw_schema_registry() if variant == "raw_schema_fields" else {}
    )
    whole_call_envelopes = (
        _load_whole_call_envelopes() if variant == "opaque_whole_call" else {}
    )
    comparator = select_variant_comparator(
        variant, base_compare, raw_schema_registry, whole_call_envelopes
    )
    e77_patch.compare_call_to_plan_with_evidence = comparator
    e77_runtime.compare_call_to_plan_with_evidence = comparator
    # Tag the runtime audit so variant rows are identifiable.
    runtime_tag = "v2" if variant == "opaque_whole_call" else "v1"
    e77_patch.RUNTIME_VERSION = f"strict_representation_{variant}_{runtime_tag}"
    _patch_pipeline_name(variant)


if os.getenv(VARIANT_ENV) and os.getenv(PATCHED_ENV) != "1":
    if os.getenv(e77_patch.GUARD_ENV) != "1":
        raise RuntimeError(
            "strict representation patch must be loaded after an enabled E77 "
            f"runtime ({e77_patch.GUARD_ENV}=1)"
        )
    _variant = _selected_variant()
    install_variant(_variant)
    os.environ[PATCHED_ENV] = "1"
