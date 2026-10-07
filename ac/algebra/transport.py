from __future__ import annotations

from dataclasses import dataclass

from ac.core.typed import Position
from ac.core.word import ChainWord
from ac.logic.predicates import Always, WordPredicate
from ac.logic.selectors import SelectionKind, Selector
from ac.logic.snapshot import PositionSnapshot, snapshot
from ac.algebra.transforms import Transformation


@dataclass(frozen=True)
class TransportedPositions:
    source_ids: tuple[int, ...]
    output_positions: frozenset[Position]


def transport_positions(
    transform: Transformation,
    word: ChainWord,
    selector: Selector,
) -> tuple[object, TransportedPositions]:
    """Transport selected *occurrences* by persistent ID, without recomputation."""
    if selector.kind is not SelectionKind.POSITION:
        raise TypeError("transport_positions requires a position selector")
    snap = snapshot(word, selector)
    if not isinstance(snap, PositionSnapshot):
        raise AssertionError("unexpected snapshot type")
    result = transform.apply(word)
    output = result.output
    out: set[Position] = set()
    for pid in snap.position_ids:
        try:
            out.add(Position(output.position_of_id(pid)))
        except KeyError:
            pass
    return result, TransportedPositions(snap.position_ids, frozenset(out))


@dataclass(frozen=True)
class TransportLawCounterexample:
    source: ChainWord
    output: ChainWord
    transported: frozenset[Position]
    recomputed: frozenset[Position]


def check_transport_law(
    transform: Transformation,
    source_selector: Selector,
    target_selector: Selector,
    *,
    universe,
    through: int,
    hypothesis: WordPredicate | None = None,
    start: int = 1,
) -> TransportLawCounterexample | None:
    if source_selector.kind is not SelectionKind.POSITION or target_selector.kind is not SelectionKind.POSITION:
        raise TypeError("transport laws currently compare position selectors")
    hypothesis = Always() if hypothesis is None else hypothesis
    for n in range(start, through + 1):
        for word in universe(n):
            if not hypothesis.holds(word) or not transform.defined_on(word):
                continue
            result, transported = transport_positions(transform, word, source_selector)
            recomputed = target_selector.evaluate(result.output)
            if transported.output_positions != recomputed:
                return TransportLawCounterexample(
                    word,
                    result.output,
                    transported.output_positions,
                    frozenset(recomputed),
                )
    return None
