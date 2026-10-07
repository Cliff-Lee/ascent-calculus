from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import Iterable


@dataclass(frozen=True)
class ChainWord:
    """A finite chain word x:[n]->[m].

    Values are positive integers. ``height`` records the ambient value-chain
    size and may exceed ``max(values)`` so that empty value levels are retained.
    Positions exposed by the public API are 1-based, matching the literature.
    """

    values: tuple[int, ...]
    height: int | None = None
    position_ids: tuple[int, ...] | None = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        if any((not isinstance(v, int)) or v < 1 for v in self.values):
            raise ValueError("values must be positive integers")
        inferred = max(self.values, default=0)
        h = inferred if self.height is None else self.height
        if h < inferred:
            raise ValueError("height cannot be smaller than max(values)")
        if h < 0:
            raise ValueError("height must be nonnegative")
        object.__setattr__(self, "height", h)

        pids = self.position_ids
        if pids is None:
            pids = tuple(range(1, len(self.values) + 1))
        if len(pids) != len(self.values):
            raise ValueError("position_ids must have one ID per position")
        if len(set(pids)) != len(pids):
            raise ValueError("position_ids must be unique")
        object.__setattr__(self, "position_ids", tuple(pids))

    @classmethod
    def of(cls, values: Iterable[int], *, height: int | None = None) -> "ChainWord":
        return cls(tuple(values), height=height)

    def __len__(self) -> int:
        return len(self.values)

    def position_id(self, position: int) -> int:
        if position < 1 or position > len(self):
            raise IndexError(position)
        return self.position_ids[position - 1]

    def position_of_id(self, position_id: int) -> int:
        try:
            return self.position_ids.index(position_id) + 1
        except ValueError as exc:
            raise KeyError(position_id) from exc

    def fresh_position_ids(self, count: int) -> tuple[int, ...]:
        if count < 0:
            raise ValueError("count must be nonnegative")
        floor = min((0, *self.position_ids))
        return tuple(floor - i for i in range(1, count + 1))

    def at(self, position: int) -> int:
        if position < 1 or position > len(self):
            raise IndexError(position)
        return self.values[position - 1]

    @cached_property
    def fibres(self) -> tuple[tuple[int, ...], ...]:
        """Fibres P_v as tuples of 1-based positions, including empty levels."""
        buckets: list[list[int]] = [[] for _ in range(self.height)]
        for i, v in enumerate(self.values, start=1):
            buckets[v - 1].append(i)
        return tuple(tuple(b) for b in buckets)

    def fibre(self, value: int) -> tuple[int, ...]:
        if value < 1 or value > self.height:
            raise IndexError(value)
        return self.fibres[value - 1]

    @cached_property
    def multiplicity_vector(self) -> tuple[int, ...]:
        return tuple(len(f) for f in self.fibres)

    @cached_property
    def composition(self) -> tuple[int, ...]:
        """Positive fibre sizes in value order (empty levels deleted)."""
        return tuple(m for m in self.multiplicity_vector if m)

    @cached_property
    def integer_partition(self) -> tuple[int, ...]:
        return tuple(sorted(self.composition, reverse=True))

    @cached_property
    def is_cayley(self) -> bool:
        return all(self.fibres) if self.height else len(self) == 0

    @cached_property
    def first_positions(self) -> frozenset[int]:
        return frozenset(f[0] for f in self.fibres if f)

    @cached_property
    def last_positions(self) -> frozenset[int]:
        return frozenset(f[-1] for f in self.fibres if f)

    def occurrence_rank(self, position: int) -> int:
        value = self.at(position)
        f = self.fibre(value)
        return f.index(position) + 1

    def occurrence_positions(self, rank: int) -> frozenset[int]:
        if rank < 1:
            raise ValueError("rank must be >= 1")
        return frozenset(f[rank - 1] for f in self.fibres if len(f) >= rank)

    @cached_property
    def up_edges(self) -> frozenset[int]:
        """Left endpoints i of ascent edges x_i < x_{i+1}."""
        return frozenset(
            i for i in range(1, len(self)) if self.at(i) < self.at(i + 1)
        )

    @cached_property
    def equal_edges(self) -> frozenset[int]:
        return frozenset(
            i for i in range(1, len(self)) if self.at(i) == self.at(i + 1)
        )

    @cached_property
    def down_edges(self) -> frozenset[int]:
        return frozenset(
            i for i in range(1, len(self)) if self.at(i) > self.at(i + 1)
        )

    @cached_property
    def raw_ascent_bottoms(self) -> frozenset[int]:
        return self.up_edges

    @cached_property
    def raw_ascent_tops(self) -> frozenset[int]:
        return frozenset(i + 1 for i in self.up_edges)

    @cached_property
    def raw_descent_tops(self) -> frozenset[int]:
        return self.down_edges

    @cached_property
    def raw_descent_bottoms(self) -> frozenset[int]:
        return frozenset(i + 1 for i in self.down_edges)

    @cached_property
    def ascent_tops(self) -> frozenset[int]:
        """Literature convention: position 1 is adjoined."""
        return frozenset({1}) | self.raw_ascent_tops if self.values else frozenset()

    @cached_property
    def ascent_bottoms(self) -> frozenset[int]:
        """Literature convention: position 1 is adjoined."""
        return frozenset({1}) | self.raw_ascent_bottoms if self.values else frozenset()

    @cached_property
    def run_starts(self) -> frozenset[int]:
        if not self.values:
            return frozenset()
        return frozenset({1}) | frozenset(i + 1 for i in range(1, len(self)) if i not in self.up_edges)

    @cached_property
    def run_ends(self) -> frozenset[int]:
        if not self.values:
            return frozenset()
        return frozenset({len(self)}) | frozenset(i for i in range(1, len(self)) if i not in self.up_edges)

    @cached_property
    def ascent_count(self) -> int:
        return len(self.up_edges)

    def avoids_constant_pattern(self, r: int) -> bool:
        """Avoids 1^r iff each value occurs at most r-1 times."""
        if r < 1:
            raise ValueError("r must be >= 1")
        return all(m < r for m in self.multiplicity_vector)

    def __str__(self) -> str:
        return "".join(map(str, self.values))
