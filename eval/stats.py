"""Assignment 7, Part B: the statistics of a result (checks/FORMATS.md, section 15.5).

Every function here is yours to write. The checker calls each one on cases of its
own, so keep the names, the arguments and what each returns. Slide numbers are
Lecture 7's.

    from eval.stats import pass_at_k, pass_hat_k, spread, margin, interval, sweeps_needed
    pass_at_k(8, 6, 2)                     # about 0.96 (slide 10)
    interval([63.5, 65.0, ...], [61.0, 63.5, ...])   # (gain, low, high), slide 19's four steps
    margin(1.5, 10, 1.5, 10)               # about 1.31: slide 19, from the spreads alone
"""

from __future__ import annotations

from math import ceil, comb, sqrt  # noqa: F401  (you will want both)

Z95 = 1.96        # 95% of a bell curve lies within 1.96 SE of its middle (slide 17)
POWER_Z = 2.80    # 1.96 + 0.84: 95% confidence and 80% power (Activity 2)


def pass_at_k(n: int, c: int, k: int) -> float:
    """The chance that at least one of k runs picked from n passed, when c of the n
    passed: 1 - C(n - c, k) / C(n, k) (slide 10). k is at most n."""
    _counts(n, c, k)
    return 1 - comb(n-c, k) / comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """The chance that all k runs picked from n passed, when c of the n passed:
    C(c, k) / C(n, k) (slide 10). Never pass@1 to the kth power."""
    _counts(n, c, k)
    return comb(c, k) / comb(n, k)


def over_tasks(counts: dict[str, tuple[int, int]], k: int) -> tuple[float, float]:
    """pass@k and pass^k averaged over tasks, from each task's (n, c)."""
    if not counts:
        raise ValueError("at least one task is required")
    return (sum(pass_at_k(n, c, k) for n, c in counts.values()) / len(counts),
            sum(pass_hat_k(n, c, k) for n, c in counts.values()) / len(counts))


def spread(values: list[float]) -> float:
    """The SD of the values: sqrt(sum((v - average)^2) / (n - 1)) (slide 17); 0.0 for
    a single value."""
    if not values:
        raise ValueError("at least one value is required")
    mean = sum(values) / len(values)
    return sqrt(sum((v-mean)**2 for v in values)/(len(values)-1)) if len(values)>1 else 0.0


def margin(s_first: float, n_first: int, s_second: float, n_second: int) -> float:
    """Slide 19's margin from two arms' spreads and sweep counts: 1.96 x the SE of the
    difference, where each arm's SE is s / sqrt(n) and the difference's is
    sqrt(SE_first^2 + SE_second^2). margin(1.5, 10, 1.5, 10) is about 1.31."""
    if min(n_first, n_second) < 1 or min(s_first, s_second) < 0:
        raise ValueError("positive run counts and nonnegative spreads required")
    return Z95 * sqrt(s_first**2/n_first + s_second**2/n_second)


def interval(first: list[float], second: list[float]) -> tuple[float, float, float]:
    """Slide 19's four steps for two arms' sweep values: the gain, the average of
    `first` minus the average of `second`, and the low and high ends of its 95%
    interval. The SE of each average is s / sqrt(n); the SE of the difference is
    sqrt(SE_first^2 + SE_second^2); the interval is the gain +/- 1.96 x that SE."""
    if not first or not second:
        raise ValueError("both arms need observations")
    gain = sum(first)/len(first) - sum(second)/len(second)
    width = margin(spread(first), len(first), spread(second), len(second))
    return gain, gain-width, gain+width


def sweeps_needed(s_a: float, s_b: float, delta: float) -> int:
    """Activity 2's arithmetic: the smallest whole n with
    n >= (s_a^2 + s_b^2) x (2.80 / delta)^2 (Part C, task 4)."""
    if delta <= 0 or min(s_a, s_b) < 0:
        raise ValueError("positive delta and nonnegative spreads required")
    return max(1, ceil((s_a*s_a+s_b*s_b)*(POWER_Z/delta)**2))


def _counts(n, c, k):
    if any(not isinstance(x, int) or isinstance(x, bool) for x in (n, c, k)) or not (0 <= c <= n and 1 <= k <= n):
        raise ValueError("require integers with 0 <= c <= n and 1 <= k <= n")
