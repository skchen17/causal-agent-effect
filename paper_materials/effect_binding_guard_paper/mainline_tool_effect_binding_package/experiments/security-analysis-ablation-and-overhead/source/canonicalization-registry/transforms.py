"""Pure, deterministic transform functions for the canonicalization registry.

Every transform is:
  - a pure function (same input -> same output, no I/O, RNG, or network);
  - O(len) for string inputs (single regex / parse pass);
  - referenced by name from rule specs; the runtime never executes untrusted code.

Transform functions may accept keyword parameters declared in the rule spec
(``params``). The ``TRANSFORMS`` registry maps names to functions.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

_WS_RUN = re.compile(r"\s+")
_PUNCT_RUN = re.compile(r"([.!?:;,])\1+")
# M3b boundary policy (mirrors the iffix number regex): exclude word/decimal
# contexts only, not sentence-final punctuation.
_NUMBER_TOKEN = re.compile(r"(?<!\w)(?<!\d\.)[+-]?\d+(?:\.\d+)?(?!\w)(?!\.\d)")
_ISO_DATE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
_SLASH_DATE = re.compile(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$")


def _decimal(value: Any) -> Decimal | None:
    """Parse a numeric value (int/float/numeric string) to Decimal, else None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value.strip())
        except InvalidOperation:
            return None
    return None


def amount_trailing_zeros(value: Any) -> Any:
    """Render a numeric amount without trailing zeros: '2200.00' -> '2200'."""
    d = _decimal(value)
    if d is None:
        return value
    if d == d.to_integral_value():
        return str(int(d))
    return format(d.normalize(), "f")


def amount_round_to_int(value: Any) -> Any:
    """REJECT control: truncate decimal amounts to integers ('2200.5' -> '2200')."""
    d = _decimal(value)
    if d is None:
        return value
    return str(int(d))


def parse_calendar_date(value: Any, slash_convention: str = "MM/DD/YYYY") -> date | None:
    """Parse a date value to a calendar date (or None if unparseable).

    Supports ISO YYYY-MM-DD, slash/day-first forms under the declared
    convention, and ISO datetime (date part taken).
    """
    if value is None:
        return None
    text = str(value).strip()
    m = _ISO_DATE.match(text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = _SLASH_DATE.match(text)
    if m:
        first, second, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if slash_convention == "MM/DD/YYYY":
            month, day = first, second
        elif slash_convention == "DD/MM/YYYY":
            month, day = second, first
        else:
            return None
        try:
            return date(year, month, day)
        except ValueError:
            return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def date_iso(value: Any, slash_convention: str = "MM/DD/YYYY") -> Any:
    """Normalize a date to ISO YYYY-MM-DD under the declared convention."""
    parsed = parse_calendar_date(value, slash_convention)
    if parsed is None:
        return value
    return parsed.isoformat()


def date_swap_day_month(value: Any) -> Any:
    """REJECT control: swap month and day ('2022-03-07' -> '2022-07-03')."""
    parsed = parse_calendar_date(value, "MM/DD/YYYY")
    if parsed is None:
        return value
    return date(parsed.year, parsed.day, parsed.month).isoformat()


def fold_repeated_punctuation(value: Any) -> Any:
    """M3-R1: collapse runs of the same terminal punctuation char."""
    if not isinstance(value, str):
        return value
    return _PUNCT_RUN.sub(r"\1", value)


def fold_whitespace(value: Any) -> Any:
    """Collapse whitespace runs to single spaces and strip ends."""
    if not isinstance(value, str):
        return value
    return _WS_RUN.sub(" ", value).strip()


def casefold_value(value: Any) -> Any:
    """Unicode casefold (the frozen guard's string-branch behavior)."""
    if not isinstance(value, str):
        return value
    return value.casefold()


def iban_truncate_last(value: Any) -> Any:
    """REJECT control: truncate the last character of an identifier string."""
    if isinstance(value, str) and len(value) > 1:
        return value[:-1]
    return value


def permission_to_read(value: Any) -> Any:
    """REJECT control: merge read/write permission enums to 'read'."""
    if value in ("r", "rw"):
        return "read"
    return value


def negation_flip(value: Any) -> Any:
    """REJECT control: flip negation markers ('不'->'是', 'not'->'yes')."""
    if not isinstance(value, str):
        return value
    return value.replace("不", "是").replace("not", "yes")


def number_boundary_punctuation(value: Any) -> Any:
    """M3b: extract the leading numeric token, treating sentence-final
    punctuation as transparent ('2200.' -> '2200'; '3.14' stays '3.14')."""
    if isinstance(value, (int, float)):
        return value
    if not isinstance(value, str):
        return value
    match = _NUMBER_TOKEN.search(value)
    if match is None:
        return value
    return match.group(0)


TRANSFORMS: dict[str, Callable[..., Any]] = {
    "amount_trailing_zeros": amount_trailing_zeros,
    "amount_round_to_int": amount_round_to_int,
    "date_iso": date_iso,
    "date_swap_day_month": date_swap_day_month,
    "fold_repeated_punctuation": fold_repeated_punctuation,
    "fold_whitespace": fold_whitespace,
    "casefold_value": casefold_value,
    "iban_truncate_last": iban_truncate_last,
    "permission_to_read": permission_to_read,
    "negation_flip": negation_flip,
    "number_boundary_punctuation": number_boundary_punctuation,
}


def apply_transform(spec: dict[str, Any], value: Any) -> Any:
    """Apply a transform named by ``spec`` (with ``spec['params']``) to value."""
    name = spec["name"]
    if name not in TRANSFORMS:
        raise KeyError(f"unknown transform: {name}")
    params = dict(spec.get("params") or {})
    return TRANSFORMS[name](value, **params)
