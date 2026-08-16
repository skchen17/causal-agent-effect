from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def find_root(path: Path) -> Path:
    for candidate in path.resolve().parents:
        if (candidate / "experiments").is_dir() and (candidate / "paper").is_dir():
            return candidate
    raise RuntimeError("could not locate consolidated package root")


ROOT = find_root(Path(__file__))
SCRIPT = ROOT / "scripts/normalize_authority_review_semantics.py"
OUTPUT = (
    ROOT
    / "experiments/human-authority-and-causal-validation/evaluation/"
    "authority-manifest-human-review/semantic-polarity-v2"
)


def load_module():
    spec = importlib.util.spec_from_file_location("authority_semantics", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_only_unambiguous_forbidden_rationales_are_fixable() -> None:
    module = load_module()
    safe = {
        "mode": "forbidden",
        "review": {
            "decision": "REJECT",
            "rationale": (
                "No participants were requested; adding participants is not authorized."
            ),
        },
    }
    unsafe = {
        "mode": "forbidden",
        "review": {
            "decision": "REJECT",
            "rationale": (
                "The user explicitly asked to invite Dora, so the target-user "
                "field is authorized and should not be marked forbidden."
            ),
        },
    }
    assert module.polarity_fixable(safe) is True
    assert module.polarity_fixable(unsafe) is False


def test_normalization_never_widens_authority() -> None:
    report = json.loads(
        (OUTPUT / "normalization_report.json").read_text(encoding="utf-8")
    )
    assert report["status"] == "passed"
    assert report["authority_widened"] is False
    assert report["n_binding_polarity_corrections"] == 8
    assert report["n_newly_accepted_tasks"] >= 1


def test_corrected_packet_still_passes_strict_validator() -> None:
    report = json.loads(
        (OUTPUT / "validation_report.json").read_text(encoding="utf-8")
    )
    assert report["status"] == "passed_with_rejections"
    assert report["n_errors"] == 0
    assert report["compiled_trusted_manifests"] >= 45
