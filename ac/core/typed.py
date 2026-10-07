from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Position:
    """A 1-based position in a chain word."""

    index: int

    def __post_init__(self) -> None:
        if self.index < 1:
            raise ValueError("position index must be >= 1")

    def __int__(self) -> int:
        return self.index


@dataclass(frozen=True, order=True)
class PositionCut:
    """A cut after ``index`` positions; 0 is before the first position."""

    index: int

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("position-cut index must be >= 0")

    def __int__(self) -> int:
        return self.index


@dataclass(frozen=True, order=True)
class ValueLevel:
    """A 1-based ambient value level."""

    index: int

    def __post_init__(self) -> None:
        if self.index < 1:
            raise ValueError("value level must be >= 1")

    def __int__(self) -> int:
        return self.index


@dataclass(frozen=True, order=True)
class ValueCut:
    """A cut after ``index`` value levels; 0 is below the minimum level."""

    index: int

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("value-cut index must be >= 0")

    def __int__(self) -> int:
        return self.index
