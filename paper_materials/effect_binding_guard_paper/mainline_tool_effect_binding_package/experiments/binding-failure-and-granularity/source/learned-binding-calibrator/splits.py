from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from src.experiments.effect_binding_guard.schema import split_name

from .features import FeatureRow


@dataclass(frozen=True)
class SplitSpec:
    name: str
    train_groups: tuple[str, ...]
    validation_groups: tuple[str, ...]
    test_groups: tuple[str, ...]
    protocol: str
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "train_groups": list(self.train_groups),
            "validation_groups": list(self.validation_groups),
            "test_groups": list(self.test_groups),
            "protocol": self.protocol,
            "notes": self.notes,
        }


def build_e49_splits(rows: list[FeatureRow], *, seeds: list[int] | None = None) -> list[SplitSpec]:
    seeds = seeds or [0, 1, 2, 3, 4]
    out = []
    for seed in seeds:
        out.append(source_balanced_split(rows, seed=seed))
    out.append(e48_hashed_split(rows))
    out.extend(leave_one_source_splits(rows))
    return out


def source_balanced_split(rows: list[FeatureRow], *, seed: int) -> SplitSpec:
    by_group = group_sources(rows)
    shared = sorted(group for group, sources in by_group.items() if {"phase4", "ipiguard"} <= sources)
    camel = sorted(group for group, sources in by_group.items() if sources == {"camel"})
    other = sorted(group for group, sources in by_group.items() if group not in shared and group not in camel)
    rng = random.Random(seed)
    rng.shuffle(shared)
    rng.shuffle(camel)
    train = shared[:14] + camel[:4] + other
    validation = shared[14:19] + camel[4:5]
    test = shared[19:24] + camel[5:6]
    spec = SplitSpec(
        name=f"source_balanced_seed{seed}",
        train_groups=tuple(sorted(train)),
        validation_groups=tuple(sorted(validation)),
        test_groups=tuple(sorted(test)),
        protocol="source_balanced_group_split",
        notes="Shared Phase4/IPIGuard anchors are split together; CaMeL groups are rotated 4/1/1.",
    )
    validate_no_overlap(spec)
    return spec


def e48_hashed_split(rows: list[FeatureRow]) -> SplitSpec:
    groups = sorted({row.split_group_id for row in rows})
    train = [group for group in groups if split_name(group) == "train"]
    validation = [group for group in groups if split_name(group) == "validation"]
    test = [group for group in groups if split_name(group) == "test"]
    spec = SplitSpec(
        name="e48_hashed_split",
        train_groups=tuple(train),
        validation_groups=tuple(validation),
        test_groups=tuple(test),
        protocol="legacy_e48_hashed_split",
        notes="For comparability only; the held-out test split has no CaMeL group.",
    )
    validate_no_overlap(spec)
    return spec


def leave_one_source_splits(rows: list[FeatureRow]) -> list[SplitSpec]:
    by_group = group_sources(rows)
    groups = sorted(by_group)
    out = []
    for target in ("camel", "phase4", "ipiguard"):
        test = [group for group, sources in by_group.items() if target in sources]
        strict_train = [group for group in groups if group not in test]
        train, validation = train_validation_partition(strict_train, seed=sum(map(ord, target)))
        protocol = "strict_leave_one_source_out" if target == "camel" else "strict_source_holdout_tiny_train"
        notes = (
            "Strict source holdout; Phase4/IPIGuard share anchors, so holding one out strictly leaves mostly CaMeL training groups."
            if target != "camel"
            else "Strict source holdout with Phase4+IPIGuard train and CaMeL test."
        )
        spec = SplitSpec(
            name=f"strict_loso_{target}",
            train_groups=tuple(sorted(train)),
            validation_groups=tuple(sorted(validation)),
            test_groups=tuple(sorted(test)),
            protocol=protocol,
            notes=notes,
        )
        validate_no_overlap(spec)
        out.append(spec)

    return out


def train_validation_partition(groups: list[str], *, seed: int) -> tuple[list[str], list[str]]:
    groups = sorted(groups)
    rng = random.Random(seed)
    rng.shuffle(groups)
    if len(groups) <= 1:
        return groups, []
    n_validation = max(1, min(len(groups) // 4, len(groups) - 1))
    return groups[n_validation:], groups[:n_validation]


def group_sources(rows: list[FeatureRow]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        out[row.split_group_id].add(row.source_scope)
    return out


def rows_for_groups(rows: list[FeatureRow], groups: set[str] | tuple[str, ...]) -> list[FeatureRow]:
    selected = set(groups)
    return [row for row in rows if row.split_group_id in selected]


def validate_no_overlap(spec: SplitSpec) -> None:
    train, validation, test = set(spec.train_groups), set(spec.validation_groups), set(spec.test_groups)
    overlap = (train & validation) | (train & test) | (validation & test)
    if overlap:
        raise ValueError(f"Group leakage in split {spec.name}: {sorted(overlap)}")


def split_summary(rows: list[FeatureRow], spec: SplitSpec) -> dict[str, Any]:
    output: dict[str, Any] = {"name": spec.name, "protocol": spec.protocol, "notes": spec.notes}
    for name, groups in (
        ("train", spec.train_groups),
        ("validation", spec.validation_groups),
        ("test", spec.test_groups),
    ):
        items = rows_for_groups(rows, groups)
        output[name] = {
            "n_groups": len(set(groups)),
            "n_rows": len(items),
            "source_counts": dict(Counter(row.source_scope for row in items)),
            "label_counts": dict(Counter(row.expected_decision for row in items)),
        }
    return output
