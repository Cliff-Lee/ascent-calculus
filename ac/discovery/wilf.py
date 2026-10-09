"""Bounded search for Wilf and shifted-Wilf matches among pattern classes.

The scanner enumerates each sequence family once per degree.  For every word it
standardizes all subsequences of the requested length and records which Cayley
patterns occur.  This makes a catalogue scan substantially cheaper than running
one separate pattern search for every pattern.

All matches are finite evidence.  They are returned with the compared degree
windows and counts so a researcher can turn any row into an explicit conjecture.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations, product
from time import perf_counter
from typing import Iterable

from ac.gui.experiments import FAMILY_GENERATORS, FAMILY_LIMITS, Family
from ac.patterns.classical import ClassicalPattern


MAX_PATTERN_LENGTH = 4
PATTERN_DEGREE_LIMITS = {2: 11, 3: 9, 4: 8}
DEFAULT_OFFSETS = (0,)


@dataclass(frozen=True)
class WilfMatch:
    left_pattern: tuple[int, ...]
    right_pattern: tuple[int, ...]
    degree_offset: int
    start: int
    stop: int
    matched_through: int
    first_divergence: int | None
    counts: tuple[tuple[int, int, int, int], ...]

    @property
    def all_match(self) -> bool:
        return self.first_divergence is None

    @property
    def matched_degrees(self) -> int:
        return self.matched_through - self.start + 1


def cayley_patterns(length: int) -> tuple[ClassicalPattern, ...]:
    """Return all surjective Cayley patterns of the requested length."""
    if isinstance(length, bool) or not isinstance(length, int) or not 2 <= length <= MAX_PATTERN_LENGTH:
        raise ValueError(f"Pattern length must be between 2 and {MAX_PATTERN_LENGTH}")
    patterns = []
    for height in range(1, length + 1):
        required = set(range(1, height + 1))
        for values in product(range(1, height + 1), repeat=length):
            if set(values) == required:
                patterns.append(ClassicalPattern(values))
    return tuple(patterns)


def _standardize(values: tuple[int, ...]) -> tuple[int, ...]:
    levels = {value: index + 1 for index, value in enumerate(sorted(set(values)))}
    return tuple(levels[value] for value in values)


@lru_cache(maxsize=96)
def _avoidance_counts(family: Family, degree: int, pattern_length: int) -> tuple[int, tuple[tuple[tuple[int, ...], int], ...]]:
    """Count every single-pattern avoidance class in one family and degree."""
    patterns = cayley_patterns(pattern_length)
    pattern_index = {pattern.values: index for index, pattern in enumerate(patterns)}
    contains = [0] * len(patterns)
    total = 0

    for word in FAMILY_GENERATORS[family](degree):
        total += 1
        if degree < pattern_length:
            continue
        present: set[int] = set()
        values = word.values
        for positions in combinations(range(degree), pattern_length):
            pattern = _standardize(tuple(values[position] for position in positions))
            index = pattern_index.get(pattern)
            if index is not None:
                present.add(index)
        for index in present:
            contains[index] += 1

    return total, tuple((pattern.values, total - contains[index]) for index, pattern in enumerate(patterns))


def _count_map(family: Family, degree: int, pattern_length: int) -> dict[tuple[int, ...], int]:
    return dict(_avoidance_counts(family, degree, pattern_length)[1])


def pattern_avoidance_counts(
    family: Family,
    degree: int,
    pattern_length: int,
) -> tuple[int, dict[tuple[int, ...], int]]:
    """Return the family size and avoidance count of each Cayley pattern.

    This public finite catalogue primitive is shared by Wilf scans and the
    broader class-conjecture search. It retains the same generator and degree
    safety limits as the existing GUI search.
    """
    if family not in FAMILY_GENERATORS:
        raise ValueError("Choose ordinary, modified, or revised ascent sequences")
    if isinstance(degree, bool) or not isinstance(degree, int) or degree < 1:
        raise ValueError("Degree must be a positive whole number")
    if isinstance(pattern_length, bool) or not isinstance(pattern_length, int) or pattern_length not in PATTERN_DEGREE_LIMITS:
        raise ValueError("Pattern length must be 2, 3, or 4")
    limit = min(FAMILY_LIMITS[family], PATTERN_DEGREE_LIMITS[pattern_length])
    if degree > limit:
        raise ValueError(f"For length-{pattern_length} pattern scans, {family} degrees are bounded to 1–{limit}")
    total, counts = _avoidance_counts(family, degree, pattern_length)
    return total, dict(counts)


def search_wilf_matches(
    source_family: Family,
    target_family: Family,
    *,
    pattern_length: int = 3,
    start: int = 1,
    stop: int = 7,
    offsets: Iterable[int] = DEFAULT_OFFSETS,
    keep: int = 100,
) -> dict:
    """Search single-pattern avoidance classes for equal count prefixes.

    ``degree_offset=d`` compares source objects of degree ``n`` with target
    objects of degree ``n+d``.  Invalid edge degrees are omitted separately for
    each offset, and the returned rows make the actual range explicit.
    """
    if source_family not in FAMILY_GENERATORS or target_family not in FAMILY_GENERATORS:
        raise ValueError("Choose ordinary, modified, or revised ascent sequences")
    if isinstance(start, bool) or isinstance(stop, bool) or not isinstance(start, int) or not isinstance(stop, int):
        raise ValueError("Degree bounds must be whole numbers")
    if not 2 <= pattern_length <= MAX_PATTERN_LENGTH:
        raise ValueError(f"Pattern length must be between 2 and {MAX_PATTERN_LENGTH}")
    source_limit = min(FAMILY_LIMITS[source_family], PATTERN_DEGREE_LIMITS[pattern_length])
    if start < 1 or stop < start or stop > source_limit:
        raise ValueError(f"For length-{pattern_length} catalogue scans, source degrees are bounded to 1–{source_limit}")
    normalized_offsets = tuple(sorted(set(int(value) for value in offsets)))
    if not normalized_offsets or any(value < -5 or value > 5 for value in normalized_offsets):
        raise ValueError("Choose one or more degree shifts between -5 and +5")
    if isinstance(keep, bool) or not isinstance(keep, int) or keep < 1 or keep > 1000:
        raise ValueError("Result limit must be between 1 and 1000")

    patterns = tuple(pattern.values for pattern in cayley_patterns(pattern_length))
    started = perf_counter()
    tested_objects = 0
    count_cache: dict[tuple[str, int], dict[tuple[int, ...], int]] = {}

    def counts(family: Family, degree: int):
        nonlocal tested_objects
        key = (family, degree)
        if key not in count_cache:
            total, values = _avoidance_counts(family, degree, pattern_length)
            count_cache[key] = dict(values)
            tested_objects += total
        return count_cache[key]

    results: list[WilfMatch] = []
    pairs_examined = 0
    for offset in normalized_offsets:
        first_n = max(start, 1 - offset)
        target_limit = min(FAMILY_LIMITS[target_family], PATTERN_DEGREE_LIMITS[pattern_length])
        last_n = min(stop, FAMILY_LIMITS[source_family], target_limit - offset)
        if first_n > last_n:
            continue
        same_class_comparison = source_family == target_family and offset == 0
        pairs_examined += len(patterns) * (len(patterns) - 1) // 2 if same_class_comparison else len(patterns) * len(patterns)
        left_vectors = {pattern: [] for pattern in patterns}
        right_vectors = {pattern: [] for pattern in patterns}
        for n in range(first_n, last_n + 1):
            left_degree_counts = counts(source_family, n)
            right_degree_counts = counts(target_family, n + offset)
            for pattern in patterns:
                left_vectors[pattern].append(left_degree_counts[pattern])
                right_vectors[pattern].append(right_degree_counts[pattern])

        left_signatures: dict[tuple[int, ...], list[tuple[int, ...]]] = {}
        right_signatures: dict[tuple[int, ...], list[tuple[int, ...]]] = {}
        for pattern, vector in left_vectors.items():
            left_signatures.setdefault(tuple(vector), []).append(pattern)
        for pattern, vector in right_vectors.items():
            right_signatures.setdefault(tuple(vector), []).append(pattern)

        for signature, left_patterns in left_signatures.items():
            right_patterns = right_signatures.get(signature, ())
            for left_pattern in left_patterns:
                for right_pattern in right_patterns:
                    if source_family == target_family and offset == 0 and left_pattern >= right_pattern:
                        continue
                    results.append(WilfMatch(
                        left_pattern=left_pattern,
                        right_pattern=right_pattern,
                        degree_offset=offset,
                        start=first_n,
                        stop=last_n,
                        matched_through=last_n,
                        first_divergence=None,
                        counts=tuple(
                            (n, left_vectors[left_pattern][i], n + offset, right_vectors[right_pattern][i])
                            for i, n in enumerate(range(first_n, last_n + 1))
                        ),
                    ))

        # Near matches are useful too: retain the pattern pairs whose count
        # vectors agree for the longest initial segment before their first
        # counterexample.  Pair signatures avoid comparing every pair at every
        # degree when the catalogue is large.
        prefix_left: dict[tuple[int, ...], list[tuple[int, ...]]] = {}
        prefix_right: dict[tuple[int, ...], list[tuple[int, ...]]] = {}
        for pattern, vector in left_vectors.items():
            for length in range(1, len(vector)):
                prefix_left.setdefault(tuple(vector[:length]), []).append(pattern)
        for pattern, vector in right_vectors.items():
            for length in range(1, len(vector)):
                prefix_right.setdefault(tuple(vector[:length]), []).append(pattern)
        seen_pairs = {(item.left_pattern, item.right_pattern, offset) for item in results if item.degree_offset == offset}
        for prefix_length in range(len(range(first_n, last_n + 1)) - 1, 0, -1):
            for signature, left_patterns in prefix_left.items():
                if len(signature) != prefix_length:
                    continue
                right_patterns = prefix_right.get(signature, ())
                for left_pattern in left_patterns:
                    for right_pattern in right_patterns:
                        marker = (left_pattern, right_pattern, offset)
                        if marker in seen_pairs:
                            continue
                        if source_family == target_family and offset == 0 and left_pattern >= right_pattern:
                            continue
                        left_vector = left_vectors[left_pattern]
                        right_vector = right_vectors[right_pattern]
                        divergence_index = next((i for i, (a, b) in enumerate(zip(left_vector, right_vector)) if a != b), None)
                        if divergence_index is None:
                            continue
                        results.append(WilfMatch(
                            left_pattern=left_pattern,
                            right_pattern=right_pattern,
                            degree_offset=offset,
                            start=first_n,
                            stop=last_n,
                            matched_through=first_n + divergence_index - 1,
                            first_divergence=first_n + divergence_index,
                            counts=tuple(
                                (n, left_vector[i], n + offset, right_vector[i])
                                for i, n in enumerate(range(first_n, last_n + 1))
                            ),
                        ))
                        seen_pairs.add(marker)
            # Only the longest common prefix for each pair is retained.

    results.sort(key=lambda item: (
        item.all_match,
        item.matched_through,
        -abs(item.degree_offset),
        item.left_pattern,
        item.right_pattern,
    ), reverse=True)
    serialized = [
        {
            "left_pattern": list(item.left_pattern),
            "right_pattern": list(item.right_pattern),
            "degree_offset": item.degree_offset,
            "start": item.start,
            "stop": item.stop,
            "matched_through": item.matched_through,
            "first_divergence": item.first_divergence,
            "all_match": item.all_match,
            "counts": [
                {"left_degree": left_n, "left_count": left_count, "right_degree": right_n, "right_count": right_count}
                for left_n, left_count, right_n, right_count in item.counts
            ],
        }
        for item in results[:keep]
    ]
    return {
        "source_family": source_family,
        "target_family": target_family,
        "pattern_length": pattern_length,
        "pattern_classes": len(patterns),
        "offsets": list(normalized_offsets),
        "pairs_examined": pairs_examined,
        "tested_objects": tested_objects,
        "candidate_matches": sum(item.all_match for item in results),
        "candidate_near_matches": sum(not item.all_match for item in results),
        "shown": serialized,
        "runtime_seconds": round(perf_counter() - started, 3),
        "finite_only": True,
        "notice": "Count matches are finite evidence only. They do not prove Wilf equivalence or provide a bijection.",
    }
