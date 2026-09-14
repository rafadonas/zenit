"""Inter-annotator agreement statistics for the GEO-002 ground truth protocol.

Pure standard-library implementations so the pilot report does not depend on a
scientific stack. Undefined statistics return ``None`` instead of a misleading number.
"""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass
from itertools import permutations
from statistics import fmean, stdev

THRESHOLDS_CM = (10.0, 30.0)


def cohen_kappa(pairs: Sequence[tuple[Hashable, Hashable]]) -> float | None:
    """Unweighted Cohen's kappa for two annotators over nominal labels."""
    if not pairs:
        return None
    total = len(pairs)
    observed = sum(1 for first, second in pairs if first == second) / total
    first_counts = Counter(first for first, _ in pairs)
    second_counts = Counter(second for _, second in pairs)
    expected = sum(first_counts[label] * second_counts[label] for label in first_counts) / (
        total * total
    )
    if expected == 1:
        return None
    return (observed - expected) / (1 - expected)


def weighted_kappa(pairs: Sequence[tuple[str, str]], ordered_labels: Sequence[str]) -> float | None:
    """Quadratic-weighted Cohen's kappa for ordinal labels such as N1/N2/N3."""
    if not pairs or len(ordered_labels) < 2:
        return None
    rank = {label: index for index, label in enumerate(ordered_labels)}
    unknown = {label for pair in pairs for label in pair if label not in rank}
    if unknown:
        raise ValueError(f"labels outside the ordinal scale: {sorted(unknown)}")
    scale = (len(ordered_labels) - 1) ** 2

    def weight(first: str, second: str) -> float:
        return (rank[first] - rank[second]) ** 2 / scale

    total = len(pairs)
    observed = sum(weight(first, second) for first, second in pairs) / total
    first_counts = Counter(first for first, _ in pairs)
    second_counts = Counter(second for _, second in pairs)
    expected = sum(
        first_counts[first] * second_counts[second] * weight(first, second)
        for first in first_counts
        for second in second_counts
    ) / (total * total)
    if expected == 0:
        return None
    return 1 - observed / expected


def krippendorff_alpha_nominal(units: Sequence[Sequence[Hashable | None]]) -> float | None:
    """Nominal Krippendorff's alpha; ``None`` entries are missing annotations."""
    coincidences: Counter[tuple[Hashable, Hashable]] = Counter()
    for unit in units:
        values = [value for value in unit if value is not None]
        if len(values) < 2:
            continue
        for first, second in permutations(values, 2):
            coincidences[(first, second)] += 1 / (len(values) - 1)
    pairable = sum(coincidences.values())
    if pairable == 0:
        return None
    marginals: Counter[Hashable] = Counter()
    for (first, _), count in coincidences.items():
        marginals[first] += count
    observed = sum(count for (first, second), count in coincidences.items() if first != second)
    expected = sum(
        marginals[first] * marginals[second]
        for first in marginals
        for second in marginals
        if first != second
    ) / (pairable - 1)
    if expected == 0:
        return None
    return 1 - observed / expected


def icc_2_1(ratings: Sequence[Sequence[float]]) -> float | None:
    """ICC(2,1): two-way random effects, absolute agreement, single rater.

    ``ratings`` is subjects x raters and must be complete.
    """
    subjects = len(ratings)
    if subjects < 2:
        return None
    raters = len(ratings[0])
    if raters < 2 or any(len(row) != raters for row in ratings):
        raise ValueError("ICC requires a complete subjects x raters matrix with >= 2 raters")
    grand = fmean(value for row in ratings for value in row)
    row_means = [fmean(row) for row in ratings]
    column_means = [fmean(row[column] for row in ratings) for column in range(raters)]
    ss_rows = raters * sum((mean - grand) ** 2 for mean in row_means)
    ss_columns = subjects * sum((mean - grand) ** 2 for mean in column_means)
    ss_total = sum((value - grand) ** 2 for row in ratings for value in row)
    ss_error = ss_total - ss_rows - ss_columns
    ms_rows = ss_rows / (subjects - 1)
    ms_columns = ss_columns / (raters - 1)
    ms_error = ss_error / ((subjects - 1) * (raters - 1))
    denominator = (
        ms_rows + (raters - 1) * ms_error + raters * (ms_columns - ms_error) / subjects
    )
    if denominator == 0:
        return None
    return (ms_rows - ms_error) / denominator


@dataclass(frozen=True, slots=True)
class BlandAltman:
    count: int
    bias: float
    sd_difference: float | None
    lower_limit: float | None
    upper_limit: float | None


def bland_altman(pairs: Sequence[tuple[float, float]]) -> BlandAltman | None:
    """Mean difference (first - second) and 95% limits of agreement."""
    if not pairs:
        return None
    differences = [first - second for first, second in pairs]
    bias = fmean(differences)
    if len(differences) < 2:
        return BlandAltman(len(differences), bias, None, None, None)
    spread = stdev(differences)
    return BlandAltman(len(differences), bias, spread, bias - 1.96 * spread, bias + 1.96 * spread)


def threshold_agreement(
    pairs: Sequence[tuple[float, float]], thresholds: Sequence[float] = THRESHOLDS_CM
) -> dict[float, float | None]:
    """Share of pairs on the same side of each exceedance threshold (``> threshold``)."""
    return {
        threshold: (
            sum(1 for first, second in pairs if (first > threshold) == (second > threshold))
            / len(pairs)
            if pairs
            else None
        )
        for threshold in thresholds
    }


def height_class(height_cm: float) -> str:
    """Historical class used only for ordinal agreement: N1 < 10, N2 10-30, N3 > 30."""
    if height_cm < 10:
        return "N1"
    if height_cm <= 30:
        return "N2"
    return "N3"


@dataclass(frozen=True, slots=True)
class ConfidenceInterval:
    estimate: float | None
    lower: float | None
    upper: float | None
    resamples: int


def cluster_bootstrap[T](
    items: Sequence[T],
    cluster_of: Callable[[T], Hashable],
    statistic: Callable[[Sequence[T]], float | None],
    *,
    resamples: int = 1000,
    seed: int = 0,
    level: float = 0.95,
) -> ConfidenceInterval:
    """Percentile CI resampling whole clusters (cells) with replacement."""
    if resamples < 1 or not 0 < level < 1:
        raise ValueError("resamples must be >= 1 and level must be in (0, 1)")
    estimate = statistic(items)
    clusters: dict[Hashable, list[T]] = {}
    for item in items:
        clusters.setdefault(cluster_of(item), []).append(item)
    keys = list(clusters)
    if not keys or estimate is None:
        return ConfidenceInterval(estimate, None, None, 0)
    generator = random.Random(seed)
    values: list[float] = []
    for _ in range(resamples):
        sample = [item for key in generator.choices(keys, k=len(keys)) for item in clusters[key]]
        value = statistic(sample)
        if value is not None:
            values.append(value)
    if not values:
        return ConfidenceInterval(estimate, None, None, 0)
    values.sort()
    tail = (1 - level) / 2
    lower = values[round(tail * (len(values) - 1))]
    upper = values[round((1 - tail) * (len(values) - 1))]
    return ConfidenceInterval(estimate, lower, upper, len(values))
