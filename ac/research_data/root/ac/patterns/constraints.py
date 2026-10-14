from __future__ import annotations

from dataclasses import dataclass

from ac.core.word import ChainWord


class PatternConstraint:
    """Constraint on an increasing tuple of selected source positions."""

    def holds(self, word: ChainWord, positions: tuple[int, ...]) -> bool:
        raise NotImplementedError


@dataclass(frozen=True)
class AllOf(PatternConstraint):
    parts: tuple[PatternConstraint, ...]

    def holds(self, word: ChainWord, positions: tuple[int, ...]) -> bool:
        return all(p.holds(word, positions) for p in self.parts)


@dataclass(frozen=True)
class ValueEq(PatternConstraint):
    left: int
    right: int

    def holds(self, word: ChainWord, positions: tuple[int, ...]) -> bool:
        return word.at(positions[self.left - 1]) == word.at(positions[self.right - 1])


@dataclass(frozen=True)
class ValueLt(PatternConstraint):
    left: int
    right: int

    def holds(self, word: ChainWord, positions: tuple[int, ...]) -> bool:
        return word.at(positions[self.left - 1]) < word.at(positions[self.right - 1])


@dataclass(frozen=True)
class PositionAdjacent(PatternConstraint):
    left: int
    right: int

    def holds(self, word: ChainWord, positions: tuple[int, ...]) -> bool:
        return positions[self.right - 1] == positions[self.left - 1] + 1


@dataclass(frozen=True)
class ValueAdjacent(PatternConstraint):
    lower: int
    upper: int

    def holds(self, word: ChainWord, positions: tuple[int, ...]) -> bool:
        return word.at(positions[self.upper - 1]) == word.at(positions[self.lower - 1]) + 1
