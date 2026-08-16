from __future__ import annotations

import random
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .schema import ToolEffectStressCase


@dataclass
class SplitResult:
    protocol: str
    train_indices: list[int]
    test_indices: list[int]
    heldout_values: list[str]
    leakage_report: dict[str, Any]
    cases_with_status: list[ToolEffectStressCase]


def make_split(
    cases: list[ToolEffectStressCase],
    protocol: str,
    heldout_values: list[str] | None = None,
    seed: int = 0,
    test_fraction: float = 0.25,
) -> SplitResult:
    if protocol == "random":
        train, test, heldout = _random_split(cases, seed, test_fraction)
    elif protocol == "held_out_tool":
        train, test, heldout = _heldout_by_value(cases, heldout_values, extract_tool_names)
    elif protocol == "held_out_tool_family":
        train, test, heldout = _heldout_by_value(cases, heldout_values, lambda c: sorted({tool_family(t) for t in extract_tool_names(c)}))
    elif protocol == "held_out_wrapper":
        train, test, heldout = _heldout_by_value(cases, heldout_values, extract_wrapper_names)
    elif protocol == "held_out_semantic_group":
        train, test, heldout = _heldout_by_value(cases, heldout_values, lambda c: [c.semantic_group_id])
    else:
        raise ValueError(f"Unknown split protocol: {protocol}")
    status_cases = derive_surface_seen_status(cases, train, test, protocol, heldout)
    return SplitResult(
        protocol=protocol,
        train_indices=train,
        test_indices=test,
        heldout_values=heldout,
        leakage_report=detect_leakage(status_cases, train, test, protocol),
        cases_with_status=status_cases,
    )


def extract_tool_names(case: ToolEffectStressCase) -> list[str]:
    names: set[str] = set()
    payload = case.tool_call_or_plan
    for key in ("tool_name", "function", "tool"):
        if payload.get(key):
            names.add(str(payload[key]))
    for tool in case.tool_inventory:
        if tool.get("name"):
            names.add(str(tool["name"]))
    return sorted(names)


def extract_wrapper_names(case: ToolEffectStressCase) -> list[str]:
    return [name for name in extract_tool_names(case) if name.startswith("safe_wrapper_for_") or "wrapper" in name]


def tool_family(tool_name: str) -> str:
    normalized = tool_name.removeprefix("surface_alias_").removeprefix("safe_wrapper_for_")
    for token in ("email", "message", "slack"):
        if token in normalized:
            return "messaging"
    for token in ("file", "read", "write", "delete", "append"):
        if token in normalized:
            return "file"
    for token in ("calendar", "event"):
        if token in normalized:
            return "calendar"
    for token in ("money", "bank", "transaction", "account"):
        if token in normalized:
            return "banking"
    for token in ("web", "search", "http", "url"):
        if token in normalized:
            return "web"
    return normalized.split("_", 1)[0] if normalized else "unknown"


def derive_surface_seen_status(
    cases: list[ToolEffectStressCase],
    train_indices: list[int],
    test_indices: list[int],
    protocol: str,
    heldout_values: list[str],
) -> list[ToolEffectStressCase]:
    train_tools = set()
    for idx in train_indices:
        train_tools.update(extract_tool_names(cases[idx]))
    held = set(heldout_values)
    out = [ToolEffectStressCase.from_dict(deepcopy(case.to_dict())) for case in cases]
    for idx in test_indices:
        case = out[idx]
        tools = set(extract_tool_names(case))
        wrappers = set(extract_wrapper_names(case))
        families = {tool_family(tool) for tool in tools}
        if protocol == "held_out_tool" and tools & held:
            case.surface_seen_status = "held_out_tool"
        elif protocol == "held_out_tool_family" and families & held:
            case.surface_seen_status = "held_out_tool_family"
        elif protocol == "held_out_wrapper" and wrappers & held:
            case.surface_seen_status = "held_out_wrapper"
        elif tools and tools.isdisjoint(train_tools):
            case.surface_seen_status = "held_out_tool"
        else:
            case.surface_seen_status = "seen"
    for idx in train_indices:
        out[idx].surface_seen_status = "seen"
    return out


def detect_leakage(cases: list[ToolEffectStressCase], train_indices: list[int], test_indices: list[int], protocol: str) -> dict[str, Any]:
    train_tools = _collect(cases, train_indices, extract_tool_names)
    test_held_tools = {
        tool for idx in test_indices for tool in extract_tool_names(cases[idx]) if cases[idx].surface_seen_status.startswith("held_out_tool")
    }
    train_wrappers = _collect(cases, train_indices, extract_wrapper_names)
    test_wrappers = _collect(cases, test_indices, extract_wrapper_names)
    train_semantic = {cases[idx].semantic_group_id for idx in train_indices}
    test_semantic = {cases[idx].semantic_group_id for idx in test_indices}
    semantic_overlap = sorted(train_semantic & test_semantic)
    return {
        "heldout_tool_in_train": sorted(train_tools & test_held_tools),
        "heldout_wrapper_in_train": sorted(train_wrappers & test_wrappers),
        "semantic_group_overlap": semantic_overlap,
        "semantic_group_leakage": bool(semantic_overlap) and protocol == "held_out_semantic_group",
    }


def _collect(cases: list[ToolEffectStressCase], indices: list[int], extractor) -> set[str]:
    values: set[str] = set()
    for idx in indices:
        values.update(extractor(cases[idx]))
    return values


def _random_split(cases: list[ToolEffectStressCase], seed: int, test_fraction: float) -> tuple[list[int], list[int], list[str]]:
    indices = list(range(len(cases)))
    random.Random(seed).shuffle(indices)
    n_test = max(1, int(round(len(indices) * test_fraction))) if indices else 0
    test = sorted(indices[:n_test])
    train = sorted(indices[n_test:])
    return train, test, []


def _heldout_by_value(cases: list[ToolEffectStressCase], heldout_values: list[str] | None, extractor) -> tuple[list[int], list[int], list[str]]:
    values = sorted({value for case in cases for value in extractor(case)})
    heldout = heldout_values or values[:1]
    heldout_set = set(heldout)
    test = [idx for idx, case in enumerate(cases) if set(extractor(case)) & heldout_set]
    train = [idx for idx in range(len(cases)) if idx not in set(test)]
    return train, test, heldout

