"""Pytest configuration: make the module directory importable.

Tests import the sibling modules (registry, validation, runtime, cegar,
domain_oracle, transforms, paths) as top-level packages, so the parent
directory of this file is inserted into sys.path.
"""
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
