"""Pre-freeze registration contexts. This module does not import descriptors or policies."""

from __future__ import annotations

from .scenario_data import TOOL_SOURCES, make_case


def generate_registration_rows() -> list[dict]:
    return [make_case(tool, "registration", pair, side)
            for tool in TOOL_SOURCES for pair in range(12) for side in (0, 1)]

