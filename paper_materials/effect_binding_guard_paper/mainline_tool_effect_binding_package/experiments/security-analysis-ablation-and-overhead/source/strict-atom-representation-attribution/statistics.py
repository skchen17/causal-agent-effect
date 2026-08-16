"""Paired statistics for the strict atom representation attribution protocol.

Implements protocol section 2.2 with no third-party dependency (the e75 env
has neither numpy nor scipy), using exact integer-safe arithmetic:

- two-sided exact McNemar test over paired binary outcomes (ASR);
- Holm-Bonferroni correction for the three V3-vs-control ASR comparisons;
- paired bootstrap for utility differences (10,000 resamples, fixed seed
  ``20260803``), reporting the absolute percentage-point difference and a
  95% percentile CI.

Every function reports the discordant-pair counts alongside p values; the
protocol forbids reporting proportions or p values alone.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence

BOOTSTRAP_SEED = 20260803
BOOTSTRAP_N = 10_000
CI_LEVEL = 0.95


def _binom_cdf_leq(k: int, n: int, p: float = 0.5) -> float:
    """Return P(X <= k) for X ~ Binomial(n, p), computed iteratively.

    Avoids constructing huge binomial coefficients for n up to the 629
    attack-case pairing.
    """
    if n <= 0:
        return 1.0
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    term = (1.0 - p) ** n  # P(X = 0)
    total = term
    for i in range(0, k):
        term *= (n - i) / (i + 1) * (p / (1.0 - p))
        total += term
    return min(1.0, max(0.0, total))


def exact_mcnemar_two_sided(
    x: Sequence[int],
    y: Sequence[int],
) -> dict[str, float | int]:
    """Two-sided exact McNemar test for paired binary outcomes.

    ``x`` and ``y`` are paired 0/1 outcomes (e.g. attack success under two
    variants) aligned by case key.  Discordant pairs are

        b = #(x_i = 1, y_i = 0)
        c = #(x_i = 0, y_i = 1)

    and the exact two-sided p value is ``min(1, 2 * P(Bin(b + c, 1/2) <=
    min(b, c)))``.  Returns the counts and p value; never a bare proportion.
    """
    if len(x) != len(y):
        raise ValueError("paired sequences must have equal length")
    b = sum(1 for xi, yi in zip(x, y) if xi == 1 and yi == 0)
    c = sum(1 for xi, yi in zip(x, y) if xi == 0 and yi == 1)
    n_disc = b + c
    if n_disc == 0:
        p_value = 1.0
    else:
        smaller = min(b, c)
        p_value = min(1.0, 2.0 * _binom_cdf_leq(smaller, n_disc, 0.5))
    return {
        "n_pairs": len(x),
        "discordant_b_x_only": b,
        "discordant_c_y_only": c,
        "n_discordant": n_disc,
        "p_value": p_value,
        "method": "exact_mcnemar_two_sided",
    }


def holm_adjust(p_values: Sequence[float]) -> list[float]:
    """Holm-Bonferroni adjusted p values (step-down), preserving order."""
    m = len(p_values)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running_max = 0.0
    for rank, index in enumerate(order):
        corrected = (m - rank) * p_values[index]
        corrected = min(1.0, corrected)
        running_max = max(running_max, corrected)
        adjusted[index] = running_max
    return adjusted


def paired_bootstrap_mean_diff(
    x: Sequence[float],
    y: Sequence[float],
    *,
    n_boot: int = BOOTSTRAP_N,
    seed: int = BOOTSTRAP_SEED,
    ci_level: float = CI_LEVEL,
) -> dict[str, float | int]:
    """Paired bootstrap CI for the mean difference ``mean(x) - mean(y)``.

    Resamples case indices with replacement using a fixed seed so the result
    is reproducible.  Reports the observed absolute difference (percentage
    points when inputs are 0/1) and the percentile CI.
    """
    if len(x) != len(y):
        raise ValueError("paired sequences must have equal length")
    n = len(x)
    if n == 0:
        raise ValueError("cannot bootstrap an empty pairing")
    diffs = [float(xi) - float(yi) for xi, yi in zip(x, y)]
    observed = sum(diffs) / n
    rng = random.Random(seed)
    samples = []
    for _ in range(n_boot):
        total = 0.0
        for _ in range(n):
            total += diffs[rng.randrange(n)]
        samples.append(total / n)
    samples.sort()
    alpha = (1.0 - ci_level) / 2.0
    lower_index = max(0, min(n_boot - 1, int(math.floor(alpha * n_boot))))
    upper_index = max(0, min(n_boot - 1, int(math.ceil((1.0 - alpha) * n_boot)) - 1))
    return {
        "n_pairs": n,
        "observed_diff": observed,
        "ci_lower": samples[lower_index],
        "ci_upper": samples[upper_index],
        "ci_level": ci_level,
        "n_boot": n_boot,
        "seed": seed,
        "method": "paired_bootstrap_percentile",
    }


def noninferior_from_bootstrap(
    bootstrap: dict[str, float | int],
    margin: float = -0.05,
) -> bool:
    """Protocol H2/H3: non-inferior iff the CI lower bound exceeds ``margin``."""
    return float(bootstrap["ci_lower"]) > margin
