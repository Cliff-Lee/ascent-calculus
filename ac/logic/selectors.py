from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from ac.core.scope import Scope, WHOLE
from ac.core.typed import Position, PositionCut, ValueCut, ValueLevel


class SelectionKind(str, Enum):
    POSITION = "position"
    POSITION_CUT = "position_cut"
    VALUE = "value"
    VALUE_CUT = "value_cut"


TypedItem = Position | PositionCut | ValueLevel | ValueCut


def _coerce_scope(scope: Scope | None) -> Scope:
    return WHOLE if scope is None else scope


def _scope_indices(word, scope: Scope) -> tuple[int, ...]:
    return tuple(int(p) for p in scope.positions(word))


def _scope_bounds(word, scope: Scope) -> tuple[int, int] | None:
    return scope.bounds(word)


class Selector:
    """Typed symbolic selector AST.

    Selectors are immutable mathematical expressions.  ``evaluate`` is the
    executable reference semantics.  Boolean operations require equal selector
    kinds, preventing position/value/cut expressions from being mixed silently.
    """

    kind: SelectionKind

    def evaluate(self, word, *, scope: Scope | None = None) -> frozenset[TypedItem]:
        return self._evaluate(word, _coerce_scope(scope))

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        raise NotImplementedError

    def universe(self, word, *, scope: Scope | None = None) -> frozenset[TypedItem]:
        scope = _coerce_scope(scope)
        if self.kind is SelectionKind.POSITION:
            return frozenset(scope.positions(word))
        if self.kind is SelectionKind.POSITION_CUT:
            return frozenset(scope.cuts(word))
        if self.kind is SelectionKind.VALUE:
            return frozenset(ValueLevel(v) for v in range(1, word.height + 1))
        if self.kind is SelectionKind.VALUE_CUT:
            return frozenset(ValueCut(v) for v in range(0, word.height + 1))
        raise AssertionError(self.kind)

    def _check_same_kind(self, other: "Selector") -> None:
        if not isinstance(other, Selector):
            raise TypeError("selector operation requires another selector")
        if self.kind is not other.kind:
            raise TypeError(f"cannot combine {self.kind.value} with {other.kind.value}")

    def __or__(self, other: "Selector") -> "Selector":
        self._check_same_kind(other)
        return SetBinary("union", self, other, self.kind)

    def __and__(self, other: "Selector") -> "Selector":
        self._check_same_kind(other)
        return SetBinary("intersection", self, other, self.kind)

    def __sub__(self, other: "Selector") -> "Selector":
        self._check_same_kind(other)
        return SetBinary("difference", self, other, self.kind)

    def __invert__(self) -> "Selector":
        return SetComplement(self, self.kind)


@dataclass(frozen=True)
class SetBinary(Selector):
    op: str
    left: Selector
    right: Selector
    kind: SelectionKind

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        a = self.left._evaluate(word, scope)
        b = self.right._evaluate(word, scope)
        if self.op == "union":
            return a | b
        if self.op == "intersection":
            return a & b
        if self.op == "difference":
            return a - b
        raise ValueError(self.op)


@dataclass(frozen=True)
class SetComplement(Selector):
    child: Selector
    kind: SelectionKind

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        return self.child.universe(word, scope=scope) - self.child._evaluate(word, scope)


# ---------- Position selectors ----------


class PositionSelector(Selector):
    kind = SelectionKind.POSITION


@dataclass(frozen=True)
class ScopeFirst(PositionSelector):
    """First position of the current positional scope."""

    kind = SelectionKind.POSITION

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        b = _scope_bounds(word, scope)
        if b is None:
            return frozenset()
        lo, _ = b
        return frozenset({Position(lo)})


@dataclass(frozen=True)
class ScopeLast(PositionSelector):
    """Last position of the current positional scope."""

    kind = SelectionKind.POSITION

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        b = _scope_bounds(word, scope)
        if b is None:
            return frozenset()
        _, hi = b
        return frozenset({Position(hi)})


@dataclass(frozen=True)
class Positions(PositionSelector):
    indices: tuple[int, ...]
    kind = SelectionKind.POSITION

    def __init__(self, indices: Iterable[int]):
        object.__setattr__(self, "indices", tuple(indices))

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        allowed = {int(p) for p in scope.positions(word)}
        out = set()
        for i in self.indices:
            if i < 1 or i > len(word):
                raise ValueError(f"position {i} outside word")
            if i in allowed:
                out.add(Position(i))
        return frozenset(out)


@dataclass(frozen=True)
class First(PositionSelector):
    kind = SelectionKind.POSITION

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        indices = _scope_indices(word, scope)
        seen: set[int] = set()
        out: list[Position] = []
        for i in indices:
            v = word.at(i)
            if v not in seen:
                seen.add(v)
                out.append(Position(i))
        return frozenset(out)


@dataclass(frozen=True)
class Last(PositionSelector):
    kind = SelectionKind.POSITION

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        indices = _scope_indices(word, scope)
        seen: set[int] = set()
        out: list[Position] = []
        for i in reversed(indices):
            v = word.at(i)
            if v not in seen:
                seen.add(v)
                out.append(Position(i))
        return frozenset(out)


@dataclass(frozen=True)
class Occ(PositionSelector):
    rank: int
    kind = SelectionKind.POSITION

    def __post_init__(self) -> None:
        if self.rank < 1:
            raise ValueError("occurrence rank must be >= 1")

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        counts: dict[int, int] = {}
        out: list[Position] = []
        for i in _scope_indices(word, scope):
            v = word.at(i)
            counts[v] = counts.get(v, 0) + 1
            if counts[v] == self.rank:
                out.append(Position(i))
        return frozenset(out)


@dataclass(frozen=True)
class Repeat(PositionSelector):
    kind = SelectionKind.POSITION

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        all_pos = frozenset(scope.positions(word))
        return all_pos - First()._evaluate(word, scope)


@dataclass(frozen=True)
class RawAscBottom(PositionSelector):
    kind = SelectionKind.POSITION

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        b = _scope_bounds(word, scope)
        if b is None:
            return frozenset()
        lo, hi = b
        return frozenset(Position(i) for i in range(lo, hi) if word.at(i) < word.at(i + 1))


@dataclass(frozen=True)
class RawAscTop(PositionSelector):
    kind = SelectionKind.POSITION

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        return frozenset(Position(int(i) + 1) for i in RawAscBottom()._evaluate(word, scope))


@dataclass(frozen=True)
class RawDescTop(PositionSelector):
    kind = SelectionKind.POSITION

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        b = _scope_bounds(word, scope)
        if b is None:
            return frozenset()
        lo, hi = b
        return frozenset(Position(i) for i in range(lo, hi) if word.at(i) > word.at(i + 1))


@dataclass(frozen=True)
class RawDescBottom(PositionSelector):
    kind = SelectionKind.POSITION

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        return frozenset(Position(int(i) + 1) for i in RawDescTop()._evaluate(word, scope))


@dataclass(frozen=True)
class AscTop(PositionSelector):
    """Literature ascent-top selector: adjoin the first position of the scope."""

    kind = SelectionKind.POSITION

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        return ScopeFirst()._evaluate(word, scope) | RawAscTop()._evaluate(word, scope)


@dataclass(frozen=True)
class AscBottom(PositionSelector):
    """Literature ascent-bottom selector: adjoin the first position of the scope."""

    kind = SelectionKind.POSITION

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        return ScopeFirst()._evaluate(word, scope) | RawAscBottom()._evaluate(word, scope)


@dataclass(frozen=True)
class DescTop(PositionSelector):
    kind = SelectionKind.POSITION

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        return RawDescTop()._evaluate(word, scope)


@dataclass(frozen=True)
class DescBottom(PositionSelector):
    kind = SelectionKind.POSITION

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        return RawDescBottom()._evaluate(word, scope)


@dataclass(frozen=True)
class RunStart(PositionSelector):
    kind = SelectionKind.POSITION

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        b = _scope_bounds(word, scope)
        if b is None:
            return frozenset()
        lo, hi = b
        out = {Position(lo)}
        out.update(Position(i) for i in range(lo + 1, hi + 1) if word.at(i - 1) >= word.at(i))
        return frozenset(out)


@dataclass(frozen=True)
class RunEnd(PositionSelector):
    kind = SelectionKind.POSITION

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        b = _scope_bounds(word, scope)
        if b is None:
            return frozenset()
        lo, hi = b
        out = {Position(hi)}
        out.update(Position(i) for i in range(lo, hi) if word.at(i) >= word.at(i + 1))
        return frozenset(out)


# ---------- Position-cut selectors ----------


class PositionCutSelector(Selector):
    kind = SelectionKind.POSITION_CUT


@dataclass(frozen=True)
class PositionCuts(PositionCutSelector):
    indices: tuple[int, ...]
    kind = SelectionKind.POSITION_CUT

    def __init__(self, indices: Iterable[int]):
        object.__setattr__(self, "indices", tuple(indices))

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        allowed = {int(c) for c in scope.cuts(word)}
        out = set()
        for i in self.indices:
            if i < 0 or i > len(word):
                raise ValueError(f"position cut {i} outside word")
            if i in allowed:
                out.add(PositionCut(i))
        return frozenset(out)


@dataclass(frozen=True)
class Before(PositionCutSelector):
    selector: Selector
    kind = SelectionKind.POSITION_CUT

    def __post_init__(self) -> None:
        if self.selector.kind is not SelectionKind.POSITION:
            raise TypeError("Before requires a position selector")

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        return frozenset(PositionCut(int(p) - 1) for p in self.selector._evaluate(word, scope))


@dataclass(frozen=True)
class After(PositionCutSelector):
    selector: Selector
    kind = SelectionKind.POSITION_CUT

    def __post_init__(self) -> None:
        if self.selector.kind is not SelectionKind.POSITION:
            raise TypeError("After requires a position selector")

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        return frozenset(PositionCut(int(p)) for p in self.selector._evaluate(word, scope))


# ---------- Value selectors ----------


class ValueSelector(Selector):
    kind = SelectionKind.VALUE


@dataclass(frozen=True)
class Values(ValueSelector):
    indices: tuple[int, ...]
    kind = SelectionKind.VALUE

    def __init__(self, indices: Iterable[int]):
        object.__setattr__(self, "indices", tuple(indices))

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        out = set()
        for v in self.indices:
            if v < 1 or v > word.height:
                raise ValueError(f"value level {v} outside ambient chain")
            out.add(ValueLevel(v))
        return frozenset(out)


def _scoped_multiplicities(word, scope: Scope) -> tuple[int, ...]:
    counts = [0] * word.height
    for p in scope.positions(word):
        counts[word.at(int(p)) - 1] += 1
    return tuple(counts)


@dataclass(frozen=True)
class OccupiedValues(ValueSelector):
    kind = SelectionKind.VALUE

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        return frozenset(ValueLevel(v) for v, m in enumerate(_scoped_multiplicities(word, scope), start=1) if m)


@dataclass(frozen=True)
class EmptyValues(ValueSelector):
    kind = SelectionKind.VALUE

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        return frozenset(ValueLevel(v) for v, m in enumerate(_scoped_multiplicities(word, scope), start=1) if not m)


@dataclass(frozen=True)
class Multiplicity(ValueSelector):
    count: int
    kind = SelectionKind.VALUE

    def __post_init__(self) -> None:
        if self.count < 0:
            raise ValueError("multiplicity must be >= 0")

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        return frozenset(ValueLevel(v) for v, m in enumerate(_scoped_multiplicities(word, scope), start=1) if m == self.count)


# ---------- Value-cut selectors ----------


class ValueCutSelector(Selector):
    kind = SelectionKind.VALUE_CUT


@dataclass(frozen=True)
class ValueCuts(ValueCutSelector):
    indices: tuple[int, ...]
    kind = SelectionKind.VALUE_CUT

    def __init__(self, indices: Iterable[int]):
        object.__setattr__(self, "indices", tuple(indices))

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        out = set()
        for v in self.indices:
            if v < 0 or v > word.height:
                raise ValueError(f"value cut {v} outside ambient chain")
            out.add(ValueCut(v))
        return frozenset(out)


@dataclass(frozen=True)
class BeforeValue(ValueCutSelector):
    selector: Selector
    kind = SelectionKind.VALUE_CUT

    def __post_init__(self) -> None:
        if self.selector.kind is not SelectionKind.VALUE:
            raise TypeError("BeforeValue requires a value selector")

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        return frozenset(ValueCut(int(v) - 1) for v in self.selector._evaluate(word, scope))


@dataclass(frozen=True)
class AfterValue(ValueCutSelector):
    selector: Selector
    kind = SelectionKind.VALUE_CUT

    def __post_init__(self) -> None:
        if self.selector.kind is not SelectionKind.VALUE:
            raise TypeError("AfterValue requires a value selector")

    def _evaluate(self, word, scope: Scope) -> frozenset[TypedItem]:
        return frozenset(ValueCut(int(v)) for v in self.selector._evaluate(word, scope))


def indices(items: Iterable[TypedItem]) -> frozenset[int]:
    """Convenience conversion for notebooks/tests while keeping the AST typed."""
    return frozenset(int(item) for item in items)
