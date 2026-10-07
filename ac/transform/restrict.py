from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ac.core.word import ChainWord
from ac.transform.basic import TransformResult


def _validate_positions(x: ChainWord, positions: Iterable[int]) -> tuple[int, ...]:
    pos = tuple(positions)
    if len(set(pos)) != len(pos):
        raise ValueError("restriction positions must be distinct")
    if tuple(sorted(pos)) != pos:
        raise ValueError("restriction positions must be strictly increasing")
    if any(i < 1 or i > len(x) for i in pos):
        raise ValueError("restriction position outside word")
    return pos


def restrict_positions(x: ChainWord, positions: Iterable[int]) -> TransformResult:
    """Restrict a word to selected source positions, retaining ambient value levels.

    The selected entries are reindexed from 1 in their original order, while
    stable occurrence IDs are retained.  This is the *ambient* restriction: it
    deliberately preserves empty value levels and hence the gap information
    that ordinary Cayley-pattern compression forgets.
    """
    pos = _validate_positions(x, positions)
    vals = tuple(x.at(i) for i in pos)
    ids = tuple(x.position_id(i) for i in pos)
    y = ChainWord(vals, height=x.height, position_ids=ids)
    new_index = {old: new for new, old in enumerate(pos, start=1)}
    pmap = tuple(new_index.get(i) for i in range(1, len(x) + 1))
    return TransformResult(
        y,
        position_map=pmap,
        value_map=tuple(range(1, x.height + 1)),
    )


def compress_levels(x: ChainWord) -> TransformResult:
    """Delete empty value levels while preserving value order.

    This is the canonical compression used for Cayley-word patterns.  It is
    intentionally distinct from Stanley standardization, which resolves equal
    letters and returns a permutation.
    """
    occupied = [v for v in range(1, x.height + 1) if x.fibre(v)]
    rank = {v: r for r, v in enumerate(occupied, start=1)}
    vals = tuple(rank[v] for v in x.values)
    y = ChainWord(vals, height=len(occupied), position_ids=x.position_ids)
    vmap = tuple(rank.get(v) for v in range(1, x.height + 1))
    return TransformResult(
        y,
        position_map=tuple(range(1, len(x) + 1)),
        value_map=vmap,
    )


def standardize(x: ChainWord) -> TransformResult:
    """Stanley standardization of a word to a permutation.

    Equal letters are resolved from left to right.  Thus positions are ranked
    by the lexicographic key ``(value, position)``.  Stable occurrence IDs are
    retained; the result has height ``len(x)``.
    """
    order = sorted(range(1, len(x) + 1), key=lambda i: (x.at(i), i))
    rank = {pos: r for r, pos in enumerate(order, start=1)}
    vals = tuple(rank[i] for i in range(1, len(x) + 1))
    y = ChainWord(vals, height=len(x), position_ids=x.position_ids)
    return TransformResult(
        y,
        position_map=tuple(range(1, len(x) + 1)),
        value_map=None,
    )


@dataclass(frozen=True)
class RestrictionView:
    """Both ambient and compressed views of a selected subsequence."""

    source_positions: tuple[int, ...]
    source_position_ids: tuple[int, ...]
    ambient: ChainWord
    compressed: ChainWord

    @property
    def ambient_values(self) -> tuple[int, ...]:
        return self.ambient.values

    @property
    def pattern_values(self) -> tuple[int, ...]:
        return self.compressed.values

    @property
    def occupied_ambient_levels(self) -> tuple[int, ...]:
        return tuple(v for v in range(1, self.ambient.height + 1) if self.ambient.fibre(v))

    @property
    def gap_signature(self) -> tuple[int, ...]:
        """Numbers of skipped ambient levels before/between/after used levels."""
        used = self.occupied_ambient_levels
        if not used:
            return (self.ambient.height,)
        gaps = [used[0] - 1]
        gaps.extend(b - a - 1 for a, b in zip(used, used[1:]))
        gaps.append(self.ambient.height - used[-1])
        return tuple(gaps)


def restriction_view(x: ChainWord, positions: Iterable[int]) -> RestrictionView:
    pos = _validate_positions(x, positions)
    ambient = restrict_positions(x, pos).output
    compressed = compress_levels(ambient).output
    return RestrictionView(
        source_positions=pos,
        source_position_ids=tuple(x.position_id(i) for i in pos),
        ambient=ambient,
        compressed=compressed,
    )
