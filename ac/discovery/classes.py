from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ac.core.word import ChainWord
from ac.discovery.profiles import BUILTIN_STATS, Statistic, compare_profile
from ac.logic.predicates import Always, WordPredicate


@dataclass(frozen=True)
class ClassComparisonRow:
    n: int
    left_count: int
    right_count: int
    equal_count: bool
    profile_equal: tuple[tuple[str, bool], ...]
    first_membership_difference: ChainWord | None


@dataclass(frozen=True)
class ClassComparison:
    rows: tuple[ClassComparisonRow, ...]

    @property
    def counts_equal(self) -> bool:
        return all(r.equal_count for r in self.rows)

    def first_count_mismatch(self) -> ClassComparisonRow | None:
        return next((r for r in self.rows if not r.equal_count), None)

    def first_profile_mismatch(self, name: str) -> ClassComparisonRow | None:
        return next((r for r in self.rows if not dict(r.profile_equal).get(name, True)), None)

    def first_class_difference(self) -> ClassComparisonRow | None:
        return next((r for r in self.rows if r.first_membership_difference is not None), None)


def compare_classes(
    left: WordPredicate,
    right: WordPredicate,
    *,
    universe,
    through: int,
    statistics: Iterable[str | tuple[str, Statistic]] = (),
    start: int = 1,
) -> ClassComparison:
    """Compare two predicates on one finite universe, degree by degree.

    Besides counts, AC can compare any registered statistic profile and return
    the first actual member on which the classes differ.  This intentionally
    separates "same class", "same count", and "same refined distribution".
    """
    stat_specs: list[tuple[str, Statistic]] = []
    for item in statistics:
        if isinstance(item, str):
            try:
                stat_specs.append((item, BUILTIN_STATS[item]))
            except KeyError as exc:
                raise KeyError(f"unknown built-in statistic {item!r}") from exc
        else:
            stat_specs.append(item)

    rows: list[ClassComparisonRow] = []
    for n in range(start, through + 1):
        words = list(universe(n))
        left_words = [x for x in words if left.holds(x)]
        right_words = [x for x in words if right.holds(x)]
        left_keys = {(x.values, x.height) for x in left_words}
        right_keys = {(x.values, x.height) for x in right_words}
        diff_key = next(iter(sorted(left_keys ^ right_keys)), None)
        witness = None
        if diff_key is not None:
            vals, height = diff_key
            witness = ChainWord(vals, height=height)

        prof = tuple(
            (name, compare_profile(left_words, right_words, stat, name=name).equal)
            for name, stat in stat_specs
        )
        rows.append(
            ClassComparisonRow(
                n=n,
                left_count=len(left_words),
                right_count=len(right_words),
                equal_count=len(left_words) == len(right_words),
                profile_equal=prof,
                first_membership_difference=witness,
            )
        )
    return ClassComparison(tuple(rows))
