#!/usr/bin/env python3
"""Inline local LaTeX inputs while leaving bibliography and graphics external."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INPUT_RE = re.compile(r"^(?P<indent>\s*)\\input\{(?P<path>[^}]+)\}\s*$")


def inline_file(path: Path, stack: tuple[Path, ...] = ()) -> str:
    resolved = path.resolve()
    if resolved in stack:
        raise ValueError(f"cyclic LaTeX input: {resolved}")
    output: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = INPUT_RE.match(line)
        if not match:
            output.append(line)
            continue
        child = ROOT / match.group("path")
        if child.suffix != ".tex":
            child = child.with_suffix(".tex")
        if not child.exists():
            raise FileNotFoundError(f"missing LaTeX input: {child}")
        output.append(f"% BEGIN INLINED {child.relative_to(ROOT)}")
        output.extend(inline_file(child, (*stack, resolved)).splitlines())
        output.append(f"% END INLINED {child.relative_to(ROOT)}")
    return "\n".join(output) + "\n"


def main() -> int:
    output = ROOT / "main_single.tex"
    output.write_text(inline_file(ROOT / "main.tex"), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
