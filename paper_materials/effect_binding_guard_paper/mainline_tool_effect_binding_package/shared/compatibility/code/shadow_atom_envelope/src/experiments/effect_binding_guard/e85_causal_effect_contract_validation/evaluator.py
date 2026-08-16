"""Compare concrete sandbox effects with independently compiled atoms."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from .model import ConcreteEffect, EffectAtom, InterventionCase


ConcreteExecutor = Callable[[Mapping[str, Any]], Iterable[ConcreteEffect]]
Atomizer = Callable[[Mapping[str, Any]], Iterable[EffectAtom]]
ConcretePolicy = Callable[[frozenset[ConcreteEffect]], bool]
AtomPolicy = Callable[[frozenset[EffectAtom]], bool]


def _serialized(items: Iterable[ConcreteEffect | EffectAtom]) -> list[dict[str, str]]:
    return [item.to_dict() for item in sorted(items)]


def _effect_signature(effect: ConcreteEffect) -> tuple[str, ...]:
    return (
        effect.kind,
        effect.operation,
        effect.resource,
        effect.target,
        effect.visibility,
        effect.commit_mode,
        effect.provenance,
        effect.control_source,
    )


def _atom_signature(atom: EffectAtom) -> tuple[str, ...]:
    return (
        atom.effect,
        atom.operation,
        atom.resource,
        atom.target,
        atom.visibility,
        atom.commit_mode,
        atom.provenance,
        atom.control_source,
    )


def _effects_covered(effects: frozenset[ConcreteEffect], atoms: frozenset[EffectAtom]) -> bool:
    represented = {_atom_signature(atom) for atom in atoms}
    return all(_effect_signature(effect) in represented for effect in effects)


def evaluate_contract(
    *,
    contract_id: str,
    cases: Iterable[InterventionCase],
    execute: ConcreteExecutor,
    atomize: Atomizer,
    concrete_policy: ConcretePolicy,
    atom_policy: AtomPolicy,
) -> list[dict[str, Any]]:
    """Evaluate whether atom differences mediate concrete effect differences."""

    rows: list[dict[str, Any]] = []
    for case in cases:
        base_effects = frozenset(execute(case.base_args))
        mutated_effects = frozenset(execute(case.mutated_args))
        base_atoms = frozenset(atomize(case.base_args))
        mutated_atoms = frozenset(atomize(case.mutated_args))
        concrete_changed = base_effects != mutated_effects
        atom_changed = base_atoms != mutated_atoms
        base_effects_covered = _effects_covered(base_effects, base_atoms)
        mutated_effects_covered = _effects_covered(mutated_effects, mutated_atoms)
        contract_sound_on_pair = base_effects_covered and mutated_effects_covered
        if not contract_sound_on_pair:
            relation = "mediation_gap"
        elif concrete_changed and atom_changed:
            relation = "faithful_mediation"
        elif not concrete_changed and not atom_changed:
            relation = "true_invariance"
        elif concrete_changed:
            relation = "mediation_gap"
        else:
            relation = "over_sensitive"

        concrete_base_allow = concrete_policy(base_effects)
        concrete_mutated_allow = concrete_policy(mutated_effects)
        atom_base_allow = atom_policy(base_atoms)
        atom_mutated_allow = atom_policy(mutated_atoms)
        concrete_flip = concrete_base_allow != concrete_mutated_allow
        atom_flip = atom_base_allow != atom_mutated_allow
        rows.append(
            {
                "contract_id": contract_id,
                "case_id": case.case_id,
                "axis": case.axis,
                "intervention_fields": list(case.intervention_fields),
                "negative_control": case.negative_control,
                "concrete_changed": concrete_changed,
                "atom_changed": atom_changed,
                "base_effects_covered": base_effects_covered,
                "mutated_effects_covered": mutated_effects_covered,
                "contract_sound_on_pair": contract_sound_on_pair,
                "relation": relation,
                "concrete_authorization": {
                    "base": "ALLOW" if concrete_base_allow else "DENY",
                    "mutated": "ALLOW" if concrete_mutated_allow else "DENY",
                    "flipped": concrete_flip,
                },
                "atom_authorization": {
                    "base": "ALLOW" if atom_base_allow else "DENY",
                    "mutated": "ALLOW" if atom_mutated_allow else "DENY",
                    "flipped": atom_flip,
                },
                "authorization_flip_agreement": concrete_flip == atom_flip,
                "base_effects": _serialized(base_effects),
                "mutated_effects": _serialized(mutated_effects),
                "base_atoms": _serialized(base_atoms),
                "mutated_atoms": _serialized(mutated_atoms),
            }
        )
    return rows


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(row["relation"] for row in rows)
    concrete_changes = sum(bool(row["concrete_changed"]) for row in rows)
    atom_changes = sum(bool(row["atom_changed"]) for row in rows)
    faithful = counts["faithful_mediation"]
    negative_controls = [row for row in rows if row["negative_control"]]
    interactions = [row for row in rows if len(row["intervention_fields"]) > 1]

    def ratio(numerator: int, denominator: int) -> float | None:
        return numerator / denominator if denominator else None

    return {
        "n_cases": len(rows),
        "relation_counts": dict(sorted(counts.items())),
        "atom_mediation_recall": ratio(faithful, concrete_changes),
        "atom_mediation_precision": ratio(faithful, atom_changes),
        "mediation_gap_rate": ratio(counts["mediation_gap"], len(rows)),
        "effect_change_miss_rate": ratio(
            sum(row["relation"] == "mediation_gap" and row["concrete_changed"] for row in rows),
            concrete_changes,
        ),
        "over_sensitivity_rate": ratio(counts["over_sensitive"], len(rows) - concrete_changes),
        "surface_invariance_rate": ratio(
            sum(row["relation"] == "true_invariance" for row in negative_controls),
            len(negative_controls),
        ),
        "interaction_mediation_rate": ratio(
            sum(row["relation"] == "faithful_mediation" for row in interactions),
            sum(bool(row["concrete_changed"]) for row in interactions),
        ),
        "authorization_flip_agreement": ratio(
            sum(bool(row["authorization_flip_agreement"]) for row in rows),
            len(rows),
        ),
    }
