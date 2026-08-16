#!/usr/bin/env python3
"""Build and validate the E88 payload-separated attack dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.experiments.effect_binding_guard.e88_agentdojo_attack_dataset.dataset import (
    DEFAULT_E82,
    DEFAULT_OUTPUT,
    DEFAULT_SOURCE,
    build_dataset,
    write_dataset,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--e82-manifest", type=Path, default=DEFAULT_E82)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset = build_dataset(args.source, args.e82_manifest)
    validation = write_dataset(dataset, args.output)
    print(json.dumps(validation, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
