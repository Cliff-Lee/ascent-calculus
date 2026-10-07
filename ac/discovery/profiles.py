from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Callable, Hashable, Iterable

from ac.core.word import ChainWord
from ac.discovery.fibre_geometry import fibre_span_profile, lower_gap_profile, higher_gap_profile


Statistic = Callable[[ChainWord], Hashable]


@dataclass(frozen=True)
class ProfileComparison:
    name: str
    equal: bool
    left: Counter
    right: Counter


def profile(words: Iterable[ChainWord], statistic: Statistic) -> Counter:
    return Counter(statistic(x) for x in words)


def compare_profile(
    left_words: Iterable[ChainWord],
    right_words: Iterable[ChainWord],
    statistic: Statistic,
    *,
    name: str = "statistic",
) -> ProfileComparison:
    left = profile(left_words, statistic)
    right = profile(right_words, statistic)
    return ProfileComparison(name, left == right, left, right)


BUILTIN_STATS: dict[str, Statistic] = {
    "height": lambda x: x.height,
    "ascents": lambda x: x.ascent_count,
    "multiplicity_partition": lambda x: x.integer_partition,
    "first_positions": lambda x: tuple(sorted(x.first_positions)),
    "last_positions": lambda x: tuple(sorted(x.last_positions)),
    "height+partition": lambda x: (x.height, x.integer_partition),
    "ascents+partition": lambda x: (x.ascent_count, x.integer_partition),
    "fibre_span_profile": fibre_span_profile,
    "lower_gap_profile": lower_gap_profile,
    "lower_gap_count_profile": lambda x: lower_gap_profile(x, counts=True),
    "higher_gap_profile": higher_gap_profile,
}
