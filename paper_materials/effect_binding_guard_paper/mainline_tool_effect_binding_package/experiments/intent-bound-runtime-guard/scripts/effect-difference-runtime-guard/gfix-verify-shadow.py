#!/usr/bin/env python3
"""Pre-run verification for the generalized-fix (iffix) shadow tree.

Checks (all must pass before any G-prime run):
  A. Shadow resolution: with PYTHONPATH=<shadow>:<code>, every guard module
     loads from code/shadow_iffix (first-on-path, regular-package rule), and
     the iffix markers are present.
  B. Frozen resolution: with PYTHONPATH=<code> (the V0-V3 configuration),
     the same imports load from code/src (frozen, symlinked sources) and the
     iffix markers are absent.
  C. Frozen zero-touch: the frozen tree file hashes are identical to the
     pre-build baseline recorded in audit/gfix-20260807/frozen_tree_hashes_before.json.
  D. Shadow integrity: every non-variant shadow file is hash-identical to the
     frozen tree; exactly the two variant files differ.
  E. Offline unit tests of M3 / M3b / M4-R2 logic on the shadow module.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SHADOW = ROOT / "code/shadow_iffix"
CODE = ROOT / "code"
E75PY = (
    ROOT
    / "experiments/unified-agent-security-baselines/runs/unified-agent-security-comparison/agentdojo-env/bin/python"
)
MOD_RT = "src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.e77_runtime"
MOD_PATCH = "src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.agentdojo_e77_runtime_patch"
MOD_E75 = "src.experiments.effect_binding_guard.e75_unified_agentdojo_comparison.run_e75"

results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def probe(pythonpath: str) -> dict[str, str]:
    code = (
        "import importlib, json, os\n"
        f"mods = ['{MOD_RT}', '{MOD_PATCH}', '{MOD_E75}']\n"
        "out = {}\n"
        "for m in mods:\n"
        "    mod = importlib.import_module(m)\n"
        "    out[m] = mod.__file__\n"
        "rt = importlib.import_module(mods[0])\n"
        "out['marker_collapse_fn'] = str(hasattr(rt, '_collapse_repeated_terminal_punctuation'))\n"
        "patch = importlib.import_module(mods[1])\n"
        "out['marker_repair_fn'] = str(hasattr(patch, '_revision_repair_prompt'))\n"
        "print(json.dumps(out))\n"
    )
    env = {**os.environ, "PYTHONPATH": pythonpath}
    env.pop("E77_EFFECT_DIFF_RUNTIME", None)  # do not trigger patch side effects
    proc = subprocess.run(
        [str(E75PY), "-c", code],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"probe failed (PYTHONPATH={pythonpath}): {proc.stderr[-2000:]}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


def main() -> int:
    # A. shadow resolution
    shadow_probe = probe(f"{SHADOW}:{CODE}")
    for mod in (MOD_RT, MOD_PATCH, MOD_E75):
        path = shadow_probe[mod]
        record(
            f"shadow-resolves {mod.split('.')[-1]}",
            str(SHADOW) in path,
            path,
        )
    record("shadow M3 marker present", shadow_probe["marker_collapse_fn"] == "True")
    record("shadow M4 marker present", shadow_probe["marker_repair_fn"] == "True")

    # B. frozen resolution (V0-V3 configuration)
    frozen_probe = probe(str(CODE))
    for mod in (MOD_RT, MOD_PATCH, MOD_E75):
        path = frozen_probe[mod]
        ok = str(CODE / "src") in path and str(SHADOW) not in path
        record(f"frozen-resolves {mod.split('.')[-1]}", ok, path)
    record("frozen M3 marker absent", frozen_probe["marker_collapse_fn"] == "False")
    record("frozen M4 marker absent", frozen_probe["marker_repair_fn"] == "False")

    # C. frozen zero-touch
    baseline = json.loads(
        (ROOT / "audit/gfix-20260807/frozen_tree_hashes_before.json").read_text()
    )
    frozen_pkg = ROOT / "code/src/experiments/effect_binding_guard"
    current: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(frozen_pkg, followlinks=True):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            path = Path(dirpath) / fn
            current[str(path.relative_to(frozen_pkg))] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    record(
        "frozen tree unchanged vs baseline",
        current == baseline,
        f"{len(current)} files",
    )

    # D. shadow integrity
    shadow_pkg = SHADOW / "src/experiments/effect_binding_guard"
    variants = {
        "e77_effect_diff_runtime_guard/e77_runtime.py",
        "e77_effect_diff_runtime_guard/agentdojo_e77_runtime_patch.py",
    }
    shadow_files = {
        str(p.relative_to(shadow_pkg)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in shadow_pkg.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    mismatches = [
        name
        for name, digest in baseline.items()
        if name not in variants and shadow_files.get(name) != digest
    ]
    extra = sorted(set(shadow_files) - set(baseline))
    record(
        "shadow non-variant files hash-identical to frozen",
        not mismatches and not extra,
        f"mismatch={mismatches} extra={extra}",
    )
    variant_diff = [
        name for name in variants if shadow_files.get(name) != baseline.get(name)
    ]
    record("exactly the two variant files differ", sorted(variant_diff) == sorted(variants))

    # E. offline unit tests on the shadow runtime (M3 / M3b / M4-R2)
    test_code = r"""
import importlib, json, os, sys

rt = importlib.import_module(
    'src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.e77_runtime'
)
checks = {}

# --- M3: punctuation-run collapse, symmetric, non-expanding ---
c = rt.canonical_grounding_value
checks['M3_double_period_equal'] = c('Catch up over lunch..') == c('Catch up over lunch.')
checks['M3_triple_exclaim_equal'] = c('stop!!!') == c('stop!')
checks['M3_ellipsis_collapses_to_dot'] = c('wait...') == c('wait.')
checks['M3_content_not_conflated'] = c('a.b') != c('ab') and c('lunch.') != c('dinner.')
checks['M3_different_punct_not_merged'] = c('a!?') != c('a?!')  # no reordering/merging kinds
checks['M3_datetime_branch_untouched'] = c('2026-08-02')[0] == 'datetime'
checks['M3_number_branch_untouched'] = c('2200')[0] == 'number'

# --- M3-R2 + M3: grounding symmetry on normalized source ---
task = "Create an event titled 'Lunch' and with description Catch up over lunch.. Don't forget the agenda."
checks['ground_single_dot_in_double_dot_source'] = rt.value_grounded_in_source('Catch up over lunch.', task)
checks['ground_double_dot_in_double_dot_source'] = rt.value_grounded_in_source('Catch up over lunch..', task)
checks['ground_absent_value_still_rejected'] = not rt.value_grounded_in_source('Catch up over dinner.', task)

# --- M3b: sentence-final number grounding ---
checks['M3b_rent_2200_period'] = rt.value_grounded_in_source(2200, 'Your rent is 2200. Pay it monthly.')
checks['M3b_rent_2200_plain'] = rt.value_grounded_in_source(2200, 'Your rent is 2200 per month')
checks['M3b_decimal_stays_whole'] = rt.value_grounded_in_source(3, 'use 3.14 as pi') is False
checks['M3b_decimal_whole_matches'] = rt.value_grounded_in_source(3.14, 'use 3.14 as pi')
checks['M3b_version_no_split'] = rt.value_grounded_in_source(1.2, 'version v1.2 is out') is False and rt.value_grounded_in_source(2, 'version v1.2 is out') is False
checks['M3b_dotted_triple_unchanged'] = rt.value_grounded_in_source(1.2, 'see 1.2.3 now') is False
checks['M3b_negative_number'] = rt.value_grounded_in_source(-5, 'temperature dropped to -5. Bring a coat.')
checks['M3b_candidate_pattern_synced'] = (
    rt.TEXT_CANDIDATE_PATTERNS['number'].pattern
    == r'(?<!\w)(?<!\d\.)[+-]?\d+(?:\.\d+)?(?!\w)(?!\.\d)'
)
import re as _re
checks['M3b_sentence_number_extracted'] = _re.findall(rt.TEXT_CANDIDATE_PATTERNS['number'], 'rent is 2200. thanks') == ['2200']

# --- M4-R2: /no_think prefix conditional ---
descriptor = {'tool_name': 'send_money', 'effect': 'transfer', 'operation': 'send',
              'security_fields': ['amount'], 'required_fields': ['amount'], 'registered_relations': []}
os.environ['E77_REVISION_NO_THINK_PREFIX'] = '1'
p_with = rt.revision_prompt('task', descriptor, None, {'amount': 1}, {'checks': []}, [], attempt=1, max_attempts=3)
os.environ['E77_REVISION_NO_THINK_PREFIX'] = '0'
p_without = rt.revision_prompt('task', descriptor, None, {'amount': 1}, {'checks': []}, [], attempt=1, max_attempts=3)
del os.environ['E77_REVISION_NO_THINK_PREFIX']
checks['M4R2_default_keeps_no_think'] = p_with.startswith('/no_think')
checks['M4R2_flag_zero_removes_no_think'] = not p_without.startswith('/no_think') and 'You are revising' in p_without
checks['M4R2_body_identical'] = p_with[len('/no_think\n'):] == p_without

print(json.dumps(checks))
"""
    env = {**os.environ, "PYTHONPATH": f"{SHADOW}:{CODE}"}
    env.pop("E77_EFFECT_DIFF_RUNTIME", None)
    proc = subprocess.run(
        [str(E75PY), "-c", test_code], capture_output=True, text=True, env=env, cwd=str(ROOT)
    )
    if proc.returncode != 0:
        record("unit tests executed", False, proc.stderr[-1500:])
    else:
        checks = json.loads(proc.stdout.strip().splitlines()[-1])
        for name, ok in sorted(checks.items()):
            record(f"unit:{name}", bool(ok))

    failed = [name for name, ok, _ in results if not ok]
    print()
    print(f"SUMMARY: {len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("FAILED:", failed)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
