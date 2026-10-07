from __future__ import annotations

from dataclasses import dataclass

from ac.core.word import ChainWord
from ac.core.scope import Scope, WHOLE
from ac.logic.selectors import PositionCutSelector
from ac.logic.snapshot import PositionCutSnapshot, snapshot


@dataclass(frozen=True)
class TransformResult:
    output: ChainWord
    # old 1-based position -> new 1-based position; None means deleted
    position_map: tuple[int | None, ...]
    # old value level -> new value level; None means deleted / not globally defined
    value_map: tuple[int | None, ...] | None = None
    created_positions: tuple[int, ...] = ()
    created_position_ids: tuple[int, ...] = ()


def reverse(x: ChainWord) -> TransformResult:
    n = len(x)
    y = ChainWord(
        tuple(reversed(x.values)),
        height=x.height,
        position_ids=tuple(reversed(x.position_ids)),
    )
    return TransformResult(
        y,
        position_map=tuple(n + 1 - i for i in range(1, n + 1)),
        value_map=tuple(range(1, x.height + 1)),
    )


def complement(x: ChainWord) -> TransformResult:
    m = x.height
    y = ChainWord(
        tuple(m + 1 - v for v in x.values),
        height=m,
        position_ids=x.position_ids,
    )
    return TransformResult(
        y,
        position_map=tuple(range(1, len(x) + 1)),
        value_map=tuple(m + 1 - v for v in range(1, m + 1)),
    )


def insert_value_level(x: ChainWord, cut: int) -> TransformResult:
    """Insert one empty value level after ``cut`` existing levels.

    cut ranges from 0 (new minimum level) to height (new maximum level).
    """
    if cut < 0 or cut > x.height:
        raise ValueError("value cut out of range")
    yvals = tuple(v if v <= cut else v + 1 for v in x.values)
    y = ChainWord(yvals, height=x.height + 1, position_ids=x.position_ids)
    vmap = tuple(v if v <= cut else v + 1 for v in range(1, x.height + 1))
    return TransformResult(
        y,
        position_map=tuple(range(1, len(x) + 1)),
        value_map=vmap,
    )


def prefix_lift(x: ChainWord, position: int) -> TransformResult:
    """Elementary prefix lift L_i.

    At pivot i with threshold t=x_i, increase each earlier value >=t by one.
    The numerical ambient height grows only when an actual value grows beyond it.
    """
    if position < 1 or position > len(x):
        raise IndexError(position)
    t = x.at(position)
    vals = list(x.values)
    for j in range(position - 1):
        if vals[j] >= t:
            vals[j] += 1
    y = ChainWord(
        tuple(vals),
        height=max(x.height, max(vals, default=0)),
        position_ids=x.position_ids,
    )
    # No single global old-value map exists because the action depends on position.
    return TransformResult(
        y,
        position_map=tuple(range(1, len(x) + 1)),
        value_map=None,
    )


def ambient_prefix_shift(
    x: ChainWord,
    prefix_count: int,
    threshold: int,
    *,
    target_height: int | None = None,
) -> TransformResult:
    """Shift selected ambient entries without requiring the pivot to be present.

    This is the restriction-level action induced by a prefix lift.  The first
    ``prefix_count`` entries whose value is at least ``threshold`` are raised by
    one.  Unlike ``prefix_lift``, the threshold is supplied externally and need
    not occur in ``x``.  Empty ambient value levels are retained.
    """
    if prefix_count < 0 or prefix_count > len(x):
        raise ValueError("prefix_count outside word")
    if threshold < 1 or threshold > x.height:
        raise ValueError("threshold outside ambient value chain")
    vals = list(x.values)
    for j in range(prefix_count):
        if vals[j] >= threshold:
            vals[j] += 1
    minimum_height = max(x.height, max(vals, default=0))
    if target_height is None:
        target_height = minimum_height
    if target_height < minimum_height:
        raise ValueError("target_height too small for shifted ambient word")
    y = ChainWord(tuple(vals), height=target_height, position_ids=x.position_ids)
    return TransformResult(
        y,
        position_map=tuple(range(1, len(x) + 1)),
        value_map=None,
    )


def inverse_prefix_lift(x: ChainWord, position: int) -> TransformResult:
    """Partial inverse of L_i on words where pivot i is a first occurrence."""
    if position < 1 or position > len(x):
        raise IndexError(position)
    if position not in x.first_positions:
        raise ValueError("inverse prefix lift requires the pivot to be a first occurrence")
    t = x.at(position)
    vals = list(x.values)
    for j in range(position - 1):
        if vals[j] > t:
            vals[j] -= 1
    # Exact preimage ambient empty levels are separate value-cut structure.
    y = ChainWord(tuple(vals), position_ids=x.position_ids)
    return TransformResult(
        y,
        position_map=tuple(range(1, len(x) + 1)),
        value_map=None,
    )


def insert_position(
    x: ChainWord,
    cut: int,
    value: int,
    *,
    fresh_level: bool = False,
) -> TransformResult:
    """Insert an entry after ``cut`` old positions (cut 0..n).

    If ``fresh_level`` is true, ``value`` is interpreted as the new level rank in
    the resulting word and an empty level is first inserted at value-1.
    """
    if cut < 0 or cut > len(x):
        raise ValueError("position cut out of range")
    base = x
    if fresh_level:
        if value < 1 or value > x.height + 1:
            raise ValueError("fresh value rank out of range")
        base = insert_value_level(x, value - 1).output
    elif value < 1 or value > x.height:
        raise ValueError("existing value out of range")

    new_id = base.fresh_position_ids(1)[0]
    vals = list(base.values)
    ids = list(base.position_ids)
    vals.insert(cut, value)
    ids.insert(cut, new_id)
    y = ChainWord(tuple(vals), height=base.height, position_ids=tuple(ids))
    pmap = tuple(i if i <= cut else i + 1 for i in range(1, len(x) + 1))
    return TransformResult(
        y,
        position_map=pmap,
        value_map=None if fresh_level else tuple(range(1, x.height + 1)),
        created_positions=(cut + 1,),
        created_position_ids=(new_id,),
    )


def insert_at_snapshot_cuts(
    x: ChainWord,
    cut_snapshot: PositionCutSnapshot,
    value: int,
) -> TransformResult:
    """Simultaneously insert one copy of an existing value at each snapshotted cut.

    All cuts refer to the *source* word.  This is AC's snapshot semantics: the
    selector is not recomputed after individual insertions.
    """
    cuts = tuple(sorted({int(c) for c in cut_snapshot.cuts}))
    if any(c < 0 or c > len(x) for c in cuts):
        raise ValueError("position cut outside source word")
    if value < 1 or value > x.height:
        raise ValueError("existing value out of range")

    new_ids = x.fresh_position_ids(len(cuts))
    cut_to_id = dict(zip(cuts, new_ids))
    vals: list[int] = []
    ids: list[int] = []
    created_positions: list[int] = []

    # Cut c is after c source entries.  Emit the insertion at cut 0, then each
    # source entry i followed by the insertion at cut i.
    if 0 in cut_to_id:
        vals.append(value)
        ids.append(cut_to_id[0])
        created_positions.append(len(vals))
    for i, (v, pid) in enumerate(zip(x.values, x.position_ids), start=1):
        vals.append(v)
        ids.append(pid)
        if i in cut_to_id:
            vals.append(value)
            ids.append(cut_to_id[i])
            created_positions.append(len(vals))

    y = ChainWord(tuple(vals), height=x.height, position_ids=tuple(ids))
    pmap = tuple(i + sum(1 for c in cuts if c < i) for i in range(1, len(x) + 1))
    return TransformResult(
        y,
        position_map=pmap,
        value_map=tuple(range(1, x.height + 1)),
        created_positions=tuple(created_positions),
        created_position_ids=new_ids,
    )


def insert_at_selected_cuts(
    x: ChainWord,
    selector: PositionCutSelector,
    value: int,
    *,
    scope: Scope = WHOLE,
) -> TransformResult:
    """Evaluate a cut selector once, then insert simultaneously at those cuts."""
    snap = snapshot(x, selector, scope=scope)
    if not isinstance(snap, PositionCutSnapshot):
        raise TypeError("selector did not produce a position-cut snapshot")
    return insert_at_snapshot_cuts(x, snap, value)
