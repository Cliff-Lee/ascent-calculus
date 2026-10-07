from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ac.core.word import ChainWord
from ac.logic.predicates import WordPredicate
from ac.transform.basic import prefix_lift, ambient_prefix_shift
from ac.transform.restrict import restrict_positions


@dataclass(frozen=True)
class LiftRestrictionTransport:
    source: ChainWord
    pivot: int
    selected_positions: tuple[int, ...]
    threshold: int
    selected_prefix_count: int
    restricted_source: ChainWord
    predicted_restriction: ChainWord
    actual_restriction: ChainWord

    @property
    def exact(self) -> bool:
        return (
            self.predicted_restriction.values == self.actual_restriction.values
            and self.predicted_restriction.height == self.actual_restriction.height
            and self.predicted_restriction.position_ids == self.actual_restriction.position_ids
        )


def transport_restriction_through_lift(
    word: ChainWord,
    pivot: int,
    positions: Iterable[int],
) -> LiftRestrictionTransport:
    """Compute the exact ambient restriction law for one prefix lift.

    If J={j_1<...<j_k}, restriction of L_i(x) to J equals the ambient shift of
    x|_J on exactly those selected entries lying to the left of i, with external
    threshold x_i.  Crucially, no Cayley compression is performed here.
    """
    pos = tuple(int(p) for p in positions)
    restricted = restrict_positions(word, pos).output
    threshold = word.at(pivot)
    c = sum(1 for p in pos if p < pivot)
    lifted = prefix_lift(word, pivot).output
    # The restricted point set alone does not know whether an unselected old
    # maximum was lifted to create a fresh top ambient level.  Ambient height is
    # therefore transported from the global lift, while selected point values
    # obey the purely local shift law.
    predicted = ambient_prefix_shift(
        restricted, c, threshold, target_height=lifted.height
    ).output
    actual = restrict_positions(lifted, pos).output
    return LiftRestrictionTransport(
        word,
        pivot,
        pos,
        threshold,
        c,
        restricted,
        predicted,
        actual,
    )


@dataclass(frozen=True)
class LiftFibreProfile:
    source: ChainWord
    pivot: int
    threshold: int
    left_counts: tuple[int, ...]
    right_counts: tuple[int, ...]
    predicted_counts_full: tuple[int, ...]
    predicted_height: int

    @property
    def predicted_multiplicity_vector(self) -> tuple[int, ...]:
        return self.predicted_counts_full[: self.predicted_height]

    def capacity_ok(self, r: int) -> bool:
        """Capacity-shift condition, assuming the source already avoids 1^r."""
        if r < 1:
            raise ValueError("r must be >= 1")
        m = self.source.height
        t = self.threshold
        # New collisions occur only at levels v=t+1,...,m, where the right
        # piece of P_v merges with the left piece of P_{v-1}.
        return all(
            self.left_counts[v - 2] + self.right_counts[v - 1] < r
            for v in range(t + 1, m + 1)
        )

    def predicts_output_avoidance(self, r: int) -> bool:
        if r < 1:
            raise ValueError("r must be >= 1")
        return all(c < r for c in self.predicted_multiplicity_vector)


@dataclass(frozen=True)
class LiftCapacityPredicate(WordPredicate):
    """Source-side capacity condition for preserving avoidance of ``1^r``."""

    pivot: int
    r: int

    def __post_init__(self) -> None:
        if self.pivot < 1:
            raise ValueError("pivot must be >= 1")
        if self.r < 1:
            raise ValueError("r must be >= 1")

    def holds(self, word: ChainWord) -> bool:
        if self.pivot > len(word):
            return False
        return lift_fibre_profile(word, self.pivot).capacity_ok(self.r)


def LiftCapacity(pivot: int, r: int) -> LiftCapacityPredicate:
    return LiftCapacityPredicate(pivot, r)


def lift_fibre_profile(word: ChainWord, pivot: int) -> LiftFibreProfile:
    if pivot < 1 or pivot > len(word):
        raise IndexError(pivot)
    m = word.height
    t = word.at(pivot)
    left = tuple(sum(1 for j in range(1, pivot) if word.at(j) == v) for v in range(1, m + 1))
    right = tuple(sum(1 for j in range(pivot, len(word) + 1) if word.at(j) == v) for v in range(1, m + 1))

    q = [0] * (m + 1)  # output levels 1..m+1
    for v in range(1, m + 2):
        if v < t:
            q[v - 1] = left[v - 1] + right[v - 1]
        elif v == t:
            q[v - 1] = right[t - 1]
        elif v <= m:
            q[v - 1] = right[v - 1] + left[v - 2]
        else:  # m+1
            q[v - 1] = left[m - 1]
    height = m + 1 if q[m] else m
    return LiftFibreProfile(word, pivot, t, left, right, tuple(q), height)


@dataclass(frozen=True)
class LiftLawCounterexample:
    source: ChainWord
    pivot: int
    detail: str


def check_lift_restriction_law(*, universe, through: int, height: int | None = None) -> LiftLawCounterexample | None:
    """Exhaustively check restriction/lift commutation on all selected subsets."""
    from itertools import combinations

    for n in range(1, through + 1):
        words = universe(n) if height is None else universe(n, height)
        for word in words:
            for pivot in range(1, n + 1):
                for k in range(0, n + 1):
                    for pos in combinations(range(1, n + 1), k):
                        tr = transport_restriction_through_lift(word, pivot, pos)
                        if not tr.exact:
                            return LiftLawCounterexample(word, pivot, f"restriction positions={pos}")
    return None


def check_capacity_shift_law(
    r: int,
    *,
    universe,
    through: int,
    height: int | None = None,
) -> LiftLawCounterexample | None:
    """Check the exact 1^r capacity law for every valid pivot.

    The theorem schema is conditional on the source already avoiding 1^r:
    L_i(x) avoids 1^r iff every new neighbouring-fibre merge fits capacity.
    """
    for n in range(1, through + 1):
        words = universe(n) if height is None else universe(n, height)
        for word in words:
            if not word.avoids_constant_pattern(r):
                continue
            for pivot in range(1, n + 1):
                prof = lift_fibre_profile(word, pivot)
                out = prefix_lift(word, pivot).output
                if tuple(out.multiplicity_vector) != prof.predicted_multiplicity_vector:
                    return LiftLawCounterexample(word, pivot, "fibre transport prediction failed")
                if prof.capacity_ok(r) != out.avoids_constant_pattern(r):
                    return LiftLawCounterexample(word, pivot, f"capacity equivalence failed for r={r}")
    return None
