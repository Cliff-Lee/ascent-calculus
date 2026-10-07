from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from ac.core.word import ChainWord
from ac.patterns.constraints import PatternConstraint
from ac.transform.restrict import RestrictionView, restriction_view


@dataclass(frozen=True)
class ConstraintOccurrence:
    positions: tuple[int, ...]
    position_ids: tuple[int, ...]
    restriction: RestrictionView


@dataclass(frozen=True)
class ConstraintPattern:
    """A generalized structural pattern over selected positions.

    Unlike ``ClassicalPattern``, this need not specify all pairwise value
    relations.  It can therefore represent vincular/value-adjacency fragments
    and later mesh/structural constraints without changing the occurrence
    engine.
    """

    arity: int
    constraint: PatternConstraint
    name: str | None = None

    def __post_init__(self) -> None:
        if self.arity < 1:
            raise ValueError("pattern arity must be >= 1")

    def matches_positions(self, word: ChainWord, positions: Iterable[int]) -> bool:
        pos = tuple(positions)
        if len(pos) != self.arity:
            return False
        if tuple(sorted(pos)) != pos or len(set(pos)) != len(pos):
            return False
        if any(i < 1 or i > len(word) for i in pos):
            return False
        return self.constraint.holds(word, pos)

    def contains(self, word: ChainWord) -> bool:
        if self.arity > len(word):
            return False
        return any(
            self.constraint.holds(word, pos)
            for pos in combinations(range(1, len(word) + 1), self.arity)
        )

    def avoids(self, word: ChainWord) -> bool:
        return not self.contains(word)

    def occurrences(self, word: ChainWord, *, limit: int | None = None) -> tuple[ConstraintOccurrence, ...]:
        out: list[ConstraintOccurrence] = []
        if self.arity > len(word):
            return ()
        for pos in combinations(range(1, len(word) + 1), self.arity):
            if not self.constraint.holds(word, pos):
                continue
            out.append(
                ConstraintOccurrence(
                    pos,
                    tuple(word.position_id(i) for i in pos),
                    restriction_view(word, pos),
                )
            )
            if limit is not None and len(out) >= limit:
                break
        return tuple(out)
