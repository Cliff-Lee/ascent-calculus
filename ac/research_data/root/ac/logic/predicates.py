from __future__ import annotations

from dataclasses import dataclass

from ac.classes.theories import is_ascent_sequence, is_modified, is_revised
from ac.core.scope import Scope, WHOLE
from ac.logic.selectors import Selector


class WordPredicate:
    """Symbolic/executable predicate on chain words."""

    def holds(self, word) -> bool:
        raise NotImplementedError

    def __and__(self, other: "WordPredicate") -> "WordPredicate":
        if not isinstance(other, WordPredicate):
            raise TypeError("predicate conjunction requires another WordPredicate")
        return PredicateBinary("and", self, other)

    def __or__(self, other: "WordPredicate") -> "WordPredicate":
        if not isinstance(other, WordPredicate):
            raise TypeError("predicate disjunction requires another WordPredicate")
        return PredicateBinary("or", self, other)

    def __invert__(self) -> "WordPredicate":
        return PredicateNot(self)

    def implies(self, other: "WordPredicate") -> "WordPredicate":
        if not isinstance(other, WordPredicate):
            raise TypeError("implication requires another WordPredicate")
        return PredicateImplies(self, other)


@dataclass(frozen=True)
class PredicateBinary(WordPredicate):
    op: str
    left: WordPredicate
    right: WordPredicate

    def holds(self, word) -> bool:
        if self.op == "and":
            return self.left.holds(word) and self.right.holds(word)
        if self.op == "or":
            return self.left.holds(word) or self.right.holds(word)
        raise ValueError(self.op)


@dataclass(frozen=True)
class PredicateNot(WordPredicate):
    child: WordPredicate

    def holds(self, word) -> bool:
        return not self.child.holds(word)


@dataclass(frozen=True)
class PredicateImplies(WordPredicate):
    premise: WordPredicate
    conclusion: WordPredicate

    def holds(self, word) -> bool:
        return (not self.premise.holds(word)) or self.conclusion.holds(word)


@dataclass(frozen=True)
class Always(WordPredicate):
    def holds(self, word) -> bool:
        return True


@dataclass(frozen=True)
class Cayley(WordPredicate):
    def holds(self, word) -> bool:
        return word.is_cayley


@dataclass(frozen=True)
class AscentSequence(WordPredicate):
    def holds(self, word) -> bool:
        return is_ascent_sequence(word)


@dataclass(frozen=True)
class Modified(WordPredicate):
    def holds(self, word) -> bool:
        return is_modified(word)


@dataclass(frozen=True)
class Revised(WordPredicate):
    def holds(self, word) -> bool:
        return is_revised(word)


@dataclass(frozen=True)
class AvoidConstant(WordPredicate):
    r: int

    def __post_init__(self) -> None:
        if self.r < 1:
            raise ValueError("r must be >= 1")

    def holds(self, word) -> bool:
        return word.avoids_constant_pattern(self.r)


@dataclass(frozen=True)
class SameSet(WordPredicate):
    left: Selector
    right: Selector
    scope: Scope = WHOLE

    def __post_init__(self) -> None:
        if self.left.kind is not self.right.kind:
            raise TypeError("set equality requires selectors of the same kind")

    def holds(self, word) -> bool:
        return self.left.evaluate(word, scope=self.scope) == self.right.evaluate(word, scope=self.scope)


@dataclass(frozen=True)
class Subset(WordPredicate):
    left: Selector
    right: Selector
    scope: Scope = WHOLE

    def __post_init__(self) -> None:
        if self.left.kind is not self.right.kind:
            raise TypeError("subset requires selectors of the same kind")

    def holds(self, word) -> bool:
        return self.left.evaluate(word, scope=self.scope) <= self.right.evaluate(word, scope=self.scope)


@dataclass(frozen=True)
class Disjoint(WordPredicate):
    left: Selector
    right: Selector
    scope: Scope = WHOLE

    def __post_init__(self) -> None:
        if self.left.kind is not self.right.kind:
            raise TypeError("disjointness requires selectors of the same kind")

    def holds(self, word) -> bool:
        return not (self.left.evaluate(word, scope=self.scope) & self.right.evaluate(word, scope=self.scope))


@dataclass(frozen=True)
class ContainsPattern(WordPredicate):
    pattern: object

    def __post_init__(self) -> None:
        from ac.patterns.classical import ClassicalPattern
        if not isinstance(self.pattern, ClassicalPattern):
            object.__setattr__(self, "pattern", ClassicalPattern(self.pattern))

    def holds(self, word) -> bool:
        return self.pattern.compile().contains(word)


@dataclass(frozen=True)
class AvoidPattern(WordPredicate):
    pattern: object

    def __post_init__(self) -> None:
        from ac.patterns.classical import ClassicalPattern
        if not isinstance(self.pattern, ClassicalPattern):
            object.__setattr__(self, "pattern", ClassicalPattern(self.pattern))

    def holds(self, word) -> bool:
        return self.pattern.compile().avoids(word)


def Contains(pattern) -> ContainsPattern:
    return ContainsPattern(pattern)


def Avoid(pattern) -> AvoidPattern:
    return AvoidPattern(pattern)


@dataclass(frozen=True)
class ContainsConstraint(WordPredicate):
    pattern: object

    def holds(self, word) -> bool:
        return self.pattern.contains(word)


@dataclass(frozen=True)
class AvoidConstraint(WordPredicate):
    pattern: object

    def holds(self, word) -> bool:
        return self.pattern.avoids(word)
