from __future__ import annotations

from dataclasses import dataclass

from ac.core.typed import Position, PositionCut


class Scope:
    """A contiguous positional scope.

    AC v0.1 deliberately permits only contiguous scopes.  This keeps local
    adjacency unambiguous.  Arbitrary subsequences will enter later through an
    explicit restriction transformation rather than by overloading scope.
    """

    def bounds(self, word) -> tuple[int, int] | None:
        raise NotImplementedError

    def positions(self, word) -> tuple[Position, ...]:
        b = self.bounds(word)
        if b is None:
            return ()
        lo, hi = b
        return tuple(Position(i) for i in range(lo, hi + 1))

    def cuts(self, word) -> tuple[PositionCut, ...]:
        b = self.bounds(word)
        if b is None:
            return (PositionCut(0),) if len(word) == 0 else ()
        lo, hi = b
        return tuple(PositionCut(i) for i in range(lo - 1, hi + 1))


@dataclass(frozen=True)
class WholeScope(Scope):
    def bounds(self, word) -> tuple[int, int] | None:
        if len(word) == 0:
            return None
        return 1, len(word)


@dataclass(frozen=True)
class IntervalScope(Scope):
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 1:
            raise ValueError("scope start must be >= 1")
        if self.end < self.start:
            raise ValueError("scope end must be >= scope start")

    def bounds(self, word) -> tuple[int, int] | None:
        if self.end > len(word):
            raise ValueError("scope extends beyond word")
        return self.start, self.end


WHOLE = WholeScope()
