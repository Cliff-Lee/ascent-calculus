from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ac.core.word import ChainWord


class SpanRelation(str, Enum):
    DISJOINT_UV = "u_before_v"
    DISJOINT_VU = "v_before_u"
    U_CONTAINS_V = "u_contains_v"
    V_CONTAINS_U = "v_contains_u"
    CROSS_UV = "u_crosses_v"
    CROSS_VU = "v_crosses_u"
    TOUCH = "touch"


@dataclass(frozen=True)
class FibreGap:
    """One open positional gap between consecutive occurrences of a value."""

    value: int
    gap_index: int
    left_position: int
    right_position: int
    lower_positions: tuple[int, ...]
    equal_positions: tuple[int, ...]
    higher_positions: tuple[int, ...]

    @property
    def lower_count(self) -> int:
        return len(self.lower_positions)

    @property
    def higher_count(self) -> int:
        return len(self.higher_positions)


@dataclass(frozen=True)
class RepeatedSandwichWitness:
    """Witness for 2^a 1 2^b: a lower value lies in a suitable fibre gap."""

    repeated_value: int
    lower_position: int
    gap_index: int
    multiplicity: int
    left_repeats: int
    right_repeats: int


def fibre_gaps(word: ChainWord, value: int) -> tuple[FibreGap, ...]:
    fibre = word.fibre(value)
    out: list[FibreGap] = []
    for r, (left, right) in enumerate(zip(fibre, fibre[1:]), start=1):
        lower: list[int] = []
        equal: list[int] = []
        higher: list[int] = []
        for p in range(left + 1, right):
            v = word.at(p)
            if v < value:
                lower.append(p)
            elif v == value:
                equal.append(p)
            else:
                higher.append(p)
        # Equal entries cannot occur strictly between consecutive occurrences of
        # the fibre, but retaining the field makes the record self-checking and
        # useful for generalized, non-consecutive gap views later.
        out.append(
            FibreGap(
                value=value,
                gap_index=r,
                left_position=left,
                right_position=right,
                lower_positions=tuple(lower),
                equal_positions=tuple(equal),
                higher_positions=tuple(higher),
            )
        )
    return tuple(out)


def lower_gap_profile(word: ChainWord, *, counts: bool = False) -> tuple[tuple[int, int, int, int], ...]:
    """Canonical profile of lower-valued occupancy between repeated occurrences.

    Each record is ``(multiplicity, gap_index, right_capacity, occupancy)`` where
    ``right_capacity = multiplicity-gap_index``.  With ``counts=False`` the last
    field is only 0/1.  Values are intentionally omitted so complement/relabel
    experiments can compare the structural geometry itself.
    """

    rows: list[tuple[int, int, int, int]] = []
    for value in range(1, word.height + 1):
        fibre = word.fibre(value)
        m = len(fibre)
        for gap in fibre_gaps(word, value):
            occ = gap.lower_count if counts else int(gap.lower_count > 0)
            rows.append((m, gap.gap_index, m - gap.gap_index, occ))
    return tuple(sorted(rows))


def reflect_gap_profile(profile: tuple[tuple[int, int, int, int], ...]) -> tuple[tuple[int, int, int, int], ...]:
    """Reflect a gap profile under positional reversal.

    A gap with ``r`` repeated occurrences to its left and ``m-r`` to its
    right becomes a gap with those capacities exchanged.
    """

    return tuple(sorted((m, right, left, occ) for m, left, right, occ in profile))


def higher_gap_profile(word: ChainWord, *, counts: bool = False) -> tuple[tuple[int, int, int, int], ...]:
    rows: list[tuple[int, int, int, int]] = []
    for value in range(1, word.height + 1):
        fibre = word.fibre(value)
        m = len(fibre)
        for gap in fibre_gaps(word, value):
            occ = gap.higher_count if counts else int(gap.higher_count > 0)
            rows.append((m, gap.gap_index, m - gap.gap_index, occ))
    return tuple(sorted(rows))


def repeated_sandwich_pattern(left_repeats: int, right_repeats: int) -> str:
    if left_repeats < 1 or right_repeats < 1:
        raise ValueError("left_repeats and right_repeats must be >= 1")
    return "2" * left_repeats + "1" + "2" * right_repeats


def repeated_sandwich_witness(
    word: ChainWord,
    left_repeats: int,
    right_repeats: int,
) -> RepeatedSandwichWitness | None:
    """Return a structural witness for a pattern 2^a 1 2^b.

    If a lower-valued entry lies between the r-th and (r+1)-st occurrences of
    value v, then it supports ``2^a 1 2^b`` exactly when r>=a and m-r>=b,
    where m is the multiplicity of v.  This is independent of which particular
    occurrences are selected, and is therefore a useful normal form for this
    whole repeated-letter pattern family.
    """

    if left_repeats < 1 or right_repeats < 1:
        raise ValueError("left_repeats and right_repeats must be >= 1")
    for value in range(1, word.height + 1):
        fibre = word.fibre(value)
        m = len(fibre)
        if m < left_repeats + right_repeats:
            continue
        for gap in fibre_gaps(word, value):
            if gap.gap_index < left_repeats:
                continue
            if m - gap.gap_index < right_repeats:
                continue
            if gap.lower_positions:
                return RepeatedSandwichWitness(
                    repeated_value=value,
                    lower_position=gap.lower_positions[0],
                    gap_index=gap.gap_index,
                    multiplicity=m,
                    left_repeats=left_repeats,
                    right_repeats=right_repeats,
                )
    return None


def contains_repeated_sandwich(word: ChainWord, left_repeats: int, right_repeats: int) -> bool:
    return repeated_sandwich_witness(word, left_repeats, right_repeats) is not None


def fibre_span_relation(word: ChainWord, u: int, v: int) -> SpanRelation:
    """Classify the interval spans of two nonempty value fibres."""

    if u == v:
        raise ValueError("distinct values required")
    fu = word.fibre(u)
    fv = word.fibre(v)
    if not fu or not fv:
        raise ValueError("both fibres must be nonempty")
    a, b = fu[0], fu[-1]
    c, d = fv[0], fv[-1]
    if b < c:
        return SpanRelation.DISJOINT_UV
    if d < a:
        return SpanRelation.DISJOINT_VU
    if a < c and d < b:
        return SpanRelation.U_CONTAINS_V
    if c < a and b < d:
        return SpanRelation.V_CONTAINS_U
    if a < c < b < d:
        return SpanRelation.CROSS_UV
    if c < a < d < b:
        return SpanRelation.CROSS_VU
    return SpanRelation.TOUCH


def fibre_span_profile(word: ChainWord) -> tuple[tuple[int, int, str], ...]:
    occupied = [v for v in range(1, word.height + 1) if word.fibre(v)]
    return tuple(
        (u, v, fibre_span_relation(word, u, v).value)
        for idx, u in enumerate(occupied)
        for v in occupied[idx + 1 :]
    )
