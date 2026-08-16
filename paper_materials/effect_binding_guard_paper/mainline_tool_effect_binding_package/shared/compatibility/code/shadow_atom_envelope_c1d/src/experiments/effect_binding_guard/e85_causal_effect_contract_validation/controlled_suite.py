"""Finite controlled suite with defaults, interactions, and placebo fields."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .model import ConcreteEffect, EffectAtom, InterventionCase


def totalize(args: Mapping[str, Any]) -> dict[str, Any]:
    result = {
        "resources": ["doc-1"],
        "recipients": ["alice@example.com"],
        "operation": "share",
        "commit_mode": "commit",
        "visibility": "private",
        "share_mode": "direct",
        "provenance": "trusted_user",
        "control_source": "user_task",
        "notify_owner": True,
        "display_label": "Share document",
    }
    result.update(dict(args))
    return result


def execute(args: Mapping[str, Any]) -> frozenset[ConcreteEffect]:
    call = totalize(args)
    if call["commit_mode"] != "commit":
        return frozenset()
    effects: set[ConcreteEffect] = set()
    for resource in call["resources"]:
        for target in call["recipients"]:
            effects.add(
                ConcreteEffect(
                    "resource_disclosed",
                    call["operation"],
                    resource,
                    target,
                    call["visibility"],
                    call["commit_mode"],
                    call["provenance"],
                    call["control_source"],
                )
            )
        if call["notify_owner"]:
            effects.add(
                ConcreteEffect(
                    "owner_notified",
                    "notify",
                    resource,
                    "resource_owner",
                    "private",
                    "commit",
                    call["provenance"],
                    call["control_source"],
                )
            )
        if call["share_mode"] == "link" and call["visibility"] == "public":
            effects.add(
                ConcreteEffect(
                    "public_link_created",
                    "publish",
                    resource,
                    "public",
                    "public",
                    "commit",
                    call["provenance"],
                    call["control_source"],
                )
            )
    return frozenset(effects)


def atomize(args: Mapping[str, Any], *, ablation: str = "none") -> frozenset[EffectAtom]:
    call = totalize(args)
    if call["commit_mode"] != "commit":
        return frozenset()
    atoms: set[EffectAtom] = set()
    resources = call["resources"] if ablation != "collapse_multi_resource" else call["resources"][:1]
    for resource in resources:
        for target in call["recipients"]:
            atoms.add(
                EffectAtom(
                    "resource_disclosed",
                    call["operation"],
                    resource,
                    "*" if ablation == "omit_target" else target,
                    call["visibility"],
                    call["commit_mode"],
                    call["provenance"],
                    call["control_source"],
                )
            )
        if call["notify_owner"] and ablation != "omit_default_effect":
            atoms.add(
                EffectAtom(
                    "owner_notified",
                    "notify",
                    resource,
                    "resource_owner",
                    "private",
                    "commit",
                    call["provenance"],
                    call["control_source"],
                )
            )
        if (
            call["share_mode"] == "link"
            and call["visibility"] == "public"
            and ablation != "omit_compound_effect"
        ):
            atoms.add(
                EffectAtom(
                    "public_link_created",
                    "publish",
                    resource,
                    "public",
                    "public",
                    "commit",
                    call["provenance"],
                    call["control_source"],
                )
            )
        if ablation == "include_placebo":
            atoms.add(
                EffectAtom(
                    "display_metadata",
                    "render",
                    call["display_label"],
                    "local_ui",
                    "private",
                    "preview",
                    "static_schema",
                    "runtime",
                )
            )
    return frozenset(atoms)


def concrete_policy(effects: frozenset[ConcreteEffect]) -> bool:
    return all(
        effect.resource == "doc-1"
        and effect.target in {"alice@example.com", "resource_owner"}
        and effect.visibility == "private"
        and effect.provenance == "trusted_user"
        and effect.control_source == "user_task"
        for effect in effects
    )


def atom_policy(atoms: frozenset[EffectAtom]) -> bool:
    return all(
        atom.resource == "doc-1"
        and atom.target in {"alice@example.com", "resource_owner"}
        and atom.visibility == "private"
        and atom.provenance == "trusted_user"
        and atom.control_source == "user_task"
        for atom in atoms
        if atom.effect != "display_metadata"
    )


def intervention_cases() -> list[InterventionCase]:
    base = {"resources": ["doc-1"], "recipients": ["alice@example.com"]}
    return [
        InterventionCase("resource", "resource", base, {**base, "resources": ["doc-2"]}, ("resources",)),
        InterventionCase(
            "target", "target", base, {**base, "recipients": ["bob@example.com"]}, ("recipients",)
        ),
        InterventionCase(
            "commit", "commit_mode", base, {**base, "commit_mode": "draft"}, ("commit_mode",)
        ),
        InterventionCase(
            "provenance", "provenance", base, {**base, "provenance": "tool_output"}, ("provenance",)
        ),
        InterventionCase(
            "multi-resource", "multi_resource", base, {**base, "resources": ["doc-1", "doc-2"]}, ("resources",)
        ),
        InterventionCase(
            "default-effect", "default", base, {**base, "notify_owner": False}, ("notify_owner",)
        ),
        InterventionCase(
            "default-equivalence",
            "default",
            base,
            {**base, "notify_owner": True},
            ("notify_owner",),
            True,
        ),
        InterventionCase(
            "compound-public-link",
            "compound",
            base,
            {**base, "share_mode": "link", "visibility": "public"},
            ("share_mode", "visibility"),
        ),
        InterventionCase(
            "surface-placebo",
            "surface_invariant",
            base,
            {**base, "display_label": "Send the document"},
            ("display_label",),
            True,
        ),
    ]


def atomizer_for(ablation: str):
    def configured(args: Mapping[str, Any]) -> Iterable[EffectAtom]:
        return atomize(args, ablation=ablation)

    return configured

