from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from ac.core.word import ChainWord
from ac.patterns.constraints import AllOf, PatternConstraint, ValueEq, ValueLt
from ac.transform.restrict import RestrictionView, restriction_view


def _parse_pattern_values(spec: str | Iterable[int] | ChainWord) -> tuple[int, ...]:
    if isinstance(spec, ChainWord):
        return spec.values
    if isinstance(spec, str):
        text = spec.strip()
        if not text:
            return ()
        if any(ch in text for ch in " ,;"):
            chunks = text.replace(",", " ").replace(";", " ").split()
            return tuple(int(c) for c in chunks)
        if not all(ch.isdigit() and ch != "0" for ch in text):
            raise ValueError("compact pattern strings must use digits 1..9")
        return tuple(int(ch) for ch in text)
    return tuple(int(v) for v in spec)


@dataclass(frozen=True)
class ClassicalPattern:
    values: tuple[int, ...]

    def __init__(self, spec: str | Iterable[int] | ChainWord):
        values = _parse_pattern_values(spec)
        if not values:
            raise ValueError("classical pattern must be nonempty")
        if any(v < 1 for v in values):
            raise ValueError("pattern values must be positive")
        used = set(values)
        if used != set(range(1, max(values) + 1)):
            raise ValueError("classical Cayley pattern must use every level 1..max")
        object.__setattr__(self, "values", values)

    @property
    def arity(self) -> int:
        return len(self.values)

    @property
    def height(self) -> int:
        return max(self.values)

    @property
    def word(self) -> ChainWord:
        return ChainWord(self.values, height=self.height)

    def compile(self) -> "CompiledPattern":
        parts: list[PatternConstraint] = []
        # Full pairwise equality/order data is an exact logical description of
        # classical Cayley-pattern standardization.
        for i in range(1, self.arity + 1):
            for j in range(i + 1, self.arity + 1):
                a, b = self.values[i - 1], self.values[j - 1]
                if a == b:
                    parts.append(ValueEq(i, j))
                elif a < b:
                    parts.append(ValueLt(i, j))
                else:
                    parts.append(ValueLt(j, i))
        return CompiledPattern(self, AllOf(tuple(parts)))

    def reverse(self) -> "ClassicalPattern":
        return ClassicalPattern(tuple(reversed(self.values)))

    def complement(self) -> "ClassicalPattern":
        m = self.height
        return ClassicalPattern(tuple(m + 1 - v for v in self.values))

    def __str__(self) -> str:
        return "".join(map(str, self.values)) if self.height <= 9 else " ".join(map(str, self.values))


@dataclass(frozen=True)
class PatternOccurrence:
    pattern: ClassicalPattern
    positions: tuple[int, ...]
    position_ids: tuple[int, ...]
    restriction: RestrictionView

    @property
    def ambient_values(self) -> tuple[int, ...]:
        return self.restriction.ambient_values

    @property
    def gap_signature(self) -> tuple[int, ...]:
        return self.restriction.gap_signature


@dataclass(frozen=True)
class CompiledPattern:
    pattern: ClassicalPattern
    constraint: PatternConstraint

    @property
    def arity(self) -> int:
        return self.pattern.arity

    def matches_positions(self, word: ChainWord, positions: Iterable[int]) -> bool:
        pos = tuple(positions)
        if len(pos) != self.arity:
            return False
        if tuple(sorted(pos)) != pos or len(set(pos)) != len(pos):
            return False
        if any(i < 1 or i > len(word) for i in pos):
            return False
        return self.constraint.holds(word, pos)

    def occurrences(self, word: ChainWord, *, limit: int | None = None) -> tuple[PatternOccurrence, ...]:
        out: list[PatternOccurrence] = []
        if self.arity > len(word):
            return ()
        for pos in combinations(range(1, len(word) + 1), self.arity):
            if self.constraint.holds(word, pos):
                view = restriction_view(word, pos)
                # Defensive equivalence check: the compiled constraints and
                # compression semantics must agree.
                if view.compressed.values != self.pattern.values:
                    raise AssertionError("compiled pattern semantics disagree with compression")
                out.append(
                    PatternOccurrence(
                        self.pattern,
                        pos,
                        tuple(word.position_id(i) for i in pos),
                        view,
                    )
                )
                if limit is not None and len(out) >= limit:
                    break
        return tuple(out)

    def contains(self, word: ChainWord) -> bool:
        if self.arity > len(word):
            return False
        for pos in combinations(range(1, len(word) + 1), self.arity):
            if self.constraint.holds(word, pos):
                return True
        return False

    def avoids(self, word: ChainWord) -> bool:
        return not self.contains(word)


def Pattern(spec: str | Iterable[int] | ChainWord) -> ClassicalPattern:
    return ClassicalPattern(spec)
