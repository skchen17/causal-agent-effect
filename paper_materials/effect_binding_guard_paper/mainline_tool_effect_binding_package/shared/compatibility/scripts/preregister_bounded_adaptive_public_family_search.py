#!/usr/bin/env python3
"""Freeze the balanced AgentDojo bounded-search protocol before execution."""

from __future__ import annotations

import json

from src.experiments.effect_binding_guard.e88_agentdojo_attack_dataset.bounded_search import (
    write_preregistration,
)


if __name__ == "__main__":
    print(json.dumps(write_preregistration(), indent=2, sort_keys=True))
