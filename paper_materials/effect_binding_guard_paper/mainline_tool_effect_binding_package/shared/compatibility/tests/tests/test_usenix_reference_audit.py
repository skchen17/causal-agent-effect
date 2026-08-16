"""Tests for active-paper citation closure and frozen identifiers."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "paper/current-usenix/reproduction/audit_references.py"


def module():
    spec = importlib.util.spec_from_file_location("audit_references", SCRIPT)
    assert spec and spec.loader
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def test_citation_set_is_closed() -> None:
    audit = module()
    assert audit.citation_keys() == set(audit.entries())


def test_public_identifiers_match_frozen_values() -> None:
    audit = module()
    entries = audit.entries()
    for key, identifier in audit.ARXIV_IDS.items():
        assert audit.field(entries[key], "eprint") == identifier
        assert audit.field(entries[key], "url") == f"https://arxiv.org/abs/{identifier}"
    for key, doi in audit.DOIS.items():
        assert audit.field(entries[key], "doi") == doi
