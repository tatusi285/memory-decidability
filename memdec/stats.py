"""Small-sample statistics, standard library only.

Everything here exists because the original analysis used one hard-coded
``t = 2.776`` for every interval, which is only correct for ``df = 4``.  Cells in
this study have 2, 3 or 12 batches, so the constant was simultaneously too wide
and too narrow depending on the table.  The helpers below take ``n`` seriously.

Two interval families are provided:

* ``clopper_pearson`` -- exact (conservative) binomial interval.  Correct when the
  independent unit really is the query.
* ``wilson`` -- score interval.  Narrower, still sane at 0% and 100%.

Neither is the right interval for the *core* grid, because there the 480 queries
are 40 chains measured 12 times each; see :func:`effective_sample_size` and
``memdec.analysis.audit``.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Iterable, Sequence

# Two-sided 95% Student-t critical values, indexed by degrees of freedom.
_T975: dict[int, float] = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
    8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160,
    14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093,
    20: 2.086, 21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060,
    26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042, 40: 2.021,
    60: 2.000, 120: 1.980,
}


def t_critical(df: int, confidence: float = 0.95) -> float:
    """Two-sided Student-t critical value, linearly interpolated between table rows.

    Only the 95% table is tabulated; other levels fall back to the normal
    approximation with a small-sample correction.
    """
    if df < 1:
        raise ValueError("df must be >= 1")
    if confidence != 0.95:
        z = _normal_critical(confidence)
        return z * (1.0 + (z * z + 1.0) / (4.0 * df))
    if df in _T975:
        return _T975[df]
    if df > 120:
        return 1.960
    keys = sorted(_T975)
    lo = max(k for k in keys if k <= df)
    hi = min(k for k in keys if k >= df)
    if lo == hi:
        return _T975[lo]
    return _T975[lo] + (_T975[hi] - _T975[lo]) * (df - lo) / (hi - lo)


def _normal_critical(confidence: float) -> float:
    """Inverse standard normal CDF by bisection (enough precision for reporting)."""
    target = 0.5 + confidence / 2.0

    def cdf(x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    lo, hi = -10.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if cdf(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def mean_ci(values: Sequence[float], confidence: float = 0.95) -> tuple[float, float]:
    """Mean and half-width of a t interval over the supplied batch values."""
    n = len(values)
    if n < 2:
        return (values[0] if values else float("nan"), 0.0)
    mean = statistics.fmean(values)
    sd = statistics.stdev(values)
    return mean, t_critical(n - 1, confidence) * sd / math.sqrt(n)


# --------------------------------------------------------------------------- #
# Binomial intervals
# --------------------------------------------------------------------------- #
def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Lentz's method)."""
    maxit, eps, fpmin = 300, 3e-12, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, maxit + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _betainc(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log1p(-x) * b - lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def _beta_ppf(q: float, a: float, b: float) -> float:
    """Quantile of the Beta(a, b) distribution by bisection on the CDF."""
    lo, hi = 0.0, 1.0
    for _ in range(90):
        mid = (lo + hi) / 2.0
        if _betainc(a, b, mid) < q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact Clopper-Pearson interval for ``k`` successes in ``n`` trials."""
    if n <= 0:
        raise ValueError("n must be positive")
    if not 0 <= k <= n:
        raise ValueError("require 0 <= k <= n")
    lo = 0.0 if k == 0 else _beta_ppf(alpha / 2.0, k, n - k + 1)
    hi = 1.0 if k == n else _beta_ppf(1.0 - alpha / 2.0, k + 1, n - k)
    return lo, hi


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson score interval for ``k`` successes in ``n`` trials."""
    if n <= 0:
        raise ValueError("n must be positive")
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


# --------------------------------------------------------------------------- #
# Sample-size honesty
# --------------------------------------------------------------------------- #
def effective_sample_size(n_probes: int, n_chains: int) -> int:
    """Independent-unit count for a design that repeats each chain many times.

    The core grid measures 40 chains at 4 delays x 3 seeds.  Because a chain's
    verdict is constant across delays and seeds (verified in
    ``memdec.analysis.audit``), the 480 probes carry little more information than
    the 40 chains.  The chain count is therefore the honest denominator.
    """
    return min(n_probes, n_chains)


def design_effect(n_probes: int, n_chains: int) -> float:
    """Factor by which a binomial interval over probes understates uncertainty."""
    if n_chains <= 0:
        raise ValueError("n_chains must be positive")
    return math.sqrt(n_probes / n_chains)


def pooled_rate(rows: Iterable[Sequence[float]], n_per_batch: int) -> tuple[int, int]:
    """Sum per-batch rates into an integer ``(k, n)`` pair.

    Rates in ``results.csv`` are proportions over a whole chain set, so
    ``k = round(mean * n_per_batch)`` recovers the underlying count exactly for
    every denominator used in this study.
    """
    rates = list(rows)
    k = round(sum(rates) * n_per_batch)
    return k, n_per_batch * len(rates)


def holm(pvalues: Sequence[float]) -> list[float]:
    """Holm-Bonferroni adjusted p-values (kept simple; input order preserved)."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        value = min(1.0, (m - rank) * pvalues[idx])
        running = max(running, value)
        adjusted[idx] = running
    return adjusted
