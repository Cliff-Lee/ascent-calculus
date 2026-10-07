from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ac.discovery.profiles import BUILTIN_STATS, Statistic, compare_profile


@dataclass(frozen=True)
class StatisticDiscrimination:
    name: str
    first_mismatch_n: int | None
    equal_through: int
    distinct_profile_keys_at_mismatch: int

    @property
    def discriminates(self) -> bool:
        return self.first_mismatch_n is not None


def rank_discriminating_statistics(
    left,
    right,
    *,
    universe,
    through: int,
    statistics: Iterable[str | tuple[str, Statistic]],
    start: int = 1,
) -> tuple[StatisticDiscrimination, ...]:
    """Rank statistics by the first degree where class profiles differ.

    The class membership scan is shared across all statistics.  This matters for
    pattern-defined classes, where testing membership is much more expensive than
    evaluating the statistics themselves.
    """

    specs: list[tuple[str, Statistic]] = []
    for item in statistics:
        if isinstance(item, str):
            specs.append((item, BUILTIN_STATS[item]))
        else:
            specs.append(item)

    unresolved = {name: stat for name, stat in specs}
    mismatch: dict[str, tuple[int, int]] = {}

    for n in range(start, through + 1):
        if not unresolved:
            break
        words = list(universe(n))
        left_words = [x for x in words if left.holds(x)]
        right_words = [x for x in words if right.holds(x)]
        for name, stat in tuple(unresolved.items()):
            comparison = compare_profile(left_words, right_words, stat, name=name)
            if comparison.equal:
                continue
            distinct = len(set(comparison.left) ^ set(comparison.right))
            mismatch[name] = (n, distinct)
            del unresolved[name]

    rows: list[StatisticDiscrimination] = []
    for name, _stat in specs:
        if name in mismatch:
            n, distinct = mismatch[name]
            rows.append(
                StatisticDiscrimination(
                    name=name,
                    first_mismatch_n=n,
                    equal_through=n - 1,
                    distinct_profile_keys_at_mismatch=distinct,
                )
            )
        else:
            rows.append(
                StatisticDiscrimination(
                    name=name,
                    first_mismatch_n=None,
                    equal_through=through,
                    distinct_profile_keys_at_mismatch=0,
                )
            )
    rows.sort(
        key=lambda row: (
            row.first_mismatch_n is None,
            row.first_mismatch_n if row.first_mismatch_n is not None else through + 1,
            -row.distinct_profile_keys_at_mismatch,
            row.name,
        )
    )
    return tuple(rows)
