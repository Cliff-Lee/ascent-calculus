"""Deliberately simple, independent finite definitions for AM-Next validation.

This module favors literal definitions over the production generators and
selectors.  It is intended for small degrees and held-out cross-checks, not as
an efficient search backend.
"""

from __future__ import annotations

from itertools import combinations, product


def ascents(values: tuple[int, ...]) -> int:
    return sum(left < right for left, right in zip(values, values[1:]))


def is_cayley(values: tuple[int, ...]) -> bool:
    if not values:
        return True
    used = set(values)
    return used == set(range(1, max(values) + 1))


def first_occurrences(values: tuple[int, ...]) -> frozenset[int]:
    seen: set[int] = set()
    positions: set[int] = set()
    for index, value in enumerate(values, start=1):
        if value not in seen:
            seen.add(value)
            positions.add(index)
    return frozenset(positions)


def ascent_tops(values: tuple[int, ...]) -> frozenset[int]:
    if not values:
        return frozenset()
    return frozenset({1, *(index + 2 for index, (left, right) in enumerate(zip(values, values[1:])) if left < right)})


def ascent_bottoms(values: tuple[int, ...]) -> frozenset[int]:
    if not values:
        return frozenset()
    return frozenset({1, *(index + 1 for index, (left, right) in enumerate(zip(values, values[1:])) if left < right)})


def is_ordinary(values: tuple[int, ...]) -> bool:
    """Literal prefix inequality: x1=1 and xi <= 2 + asc(x1...x(i-1))."""
    if not values or values[0] != 1:
        return False
    for end in range(2, len(values) + 1):
        prefix = values[: end - 1]
        if not 1 <= values[end - 1] <= 2 + ascents(prefix):
            return False
    return True


def is_modified(values: tuple[int, ...]) -> bool:
    return is_cayley(values) and first_occurrences(values) == ascent_tops(values)


def is_revised(values: tuple[int, ...]) -> bool:
    return is_cayley(values) and first_occurrences(values) == ascent_bottoms(values)


def all_tuples(degree: int):
    """Enumerate all words with entries at most the degree, including repeats."""
    if type(degree) is not int or degree < 0:
        raise ValueError("degree must be a nonnegative integer")
    if degree == 0:
        yield ()
    else:
        yield from product(range(1, degree + 1), repeat=degree)


def ordinary(degree: int) -> set[tuple[int, ...]]:
    return {values for values in all_tuples(degree) if is_ordinary(values)}


def modified(degree: int) -> set[tuple[int, ...]]:
    return {values for values in all_tuples(degree) if is_modified(values)}


def revised(degree: int) -> set[tuple[int, ...]]:
    return {values for values in all_tuples(degree) if is_revised(values)}


def standardize(values: tuple[int, ...]) -> tuple[int, ...]:
    ranks = {value: rank for rank, value in enumerate(sorted(set(values)), start=1)}
    return tuple(ranks[value] for value in values)


def contains_pattern(values: tuple[int, ...], pattern: tuple[int, ...]) -> bool:
    """Classical subsequence containment, independently via rank standardization."""
    if not pattern or len(pattern) > len(values):
        return False
    return any(standardize(tuple(values[i] for i in positions)) == pattern
               for positions in combinations(range(len(values)), len(pattern)))

