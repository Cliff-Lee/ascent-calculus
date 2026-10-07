from __future__ import annotations

from dataclasses import dataclass

from ac.core.scope import Scope, WHOLE
from ac.core.typed import Position, PositionCut
from ac.logic.selectors import SelectionKind, Selector


@dataclass(frozen=True)
class PositionSnapshot:
    """Snapshot of selected source occurrences.

    ``position_ids`` survive subsequent position edits and therefore identify
    the selected occurrences independently of their later numerical indices.
    """

    positions: tuple[Position, ...]
    position_ids: tuple[int, ...]


@dataclass(frozen=True)
class PositionCutSnapshot:
    """Snapshot of source cuts.

    Cuts are stored by source index for simultaneous edits.  The adjacent source
    position IDs are included when present so future sequential/sweep semantics
    can re-anchor a cut after earlier position edits.
    """

    cuts: tuple[PositionCut, ...]
    left_ids: tuple[int | None, ...]
    right_ids: tuple[int | None, ...]


def snapshot(word, selector: Selector, *, scope: Scope = WHOLE):
    selected = sorted(selector.evaluate(word, scope=scope), key=int)
    if selector.kind is SelectionKind.POSITION:
        positions = tuple(selected)
        ids = tuple(word.position_id(int(p)) for p in positions)
        return PositionSnapshot(positions, ids)
    if selector.kind is SelectionKind.POSITION_CUT:
        cuts = tuple(selected)
        left: list[int | None] = []
        right: list[int | None] = []
        for c in cuts:
            j = int(c)
            left.append(word.position_id(j) if j >= 1 else None)
            right.append(word.position_id(j + 1) if j + 1 <= len(word) else None)
        return PositionCutSnapshot(cuts, tuple(left), tuple(right))
    # Value snapshots do not yet need persistent identities because lifts can
    # split/merge value classes.  Return the immutable typed selection itself.
    return tuple(selected)
