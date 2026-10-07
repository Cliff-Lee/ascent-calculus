from __future__ import annotations

from dataclasses import dataclass

from ac.algebra.transforms import TransformSignature, Transformation
from ac.core.word import ChainWord
from ac.discovery.fibre_geometry import fibre_gaps
from ac.transform.basic import TransformResult


def pack_internal_occurrences(word: ChainWord, value: int, *, side: str = "right") -> ChainWord:
    """Pack the internal copies of one value to one side of its fibre span.

    The first and last occurrence stay fixed.  All other entries inside the span
    retain their relative order, and all internal copies of ``value`` retain
    their relative order.  Position IDs travel with occurrences, so provenance
    survives the move.

    This is deliberately a generic fibre operation, not a claimed bijection.
    It is useful as a synthesis primitive for repeated-letter gap problems.
    """

    if side not in {"left", "right"}:
        raise ValueError("side must be 'left' or 'right'")
    fibre = word.fibre(value)
    if len(fibre) < 3:
        return word
    first, last = fibre[0], fibre[-1]
    segment = list(zip(word.values[first - 1 : last], word.position_ids[first - 1 : last]))
    interior = segment[1:-1]
    copies = [item for item in interior if item[0] == value]
    others = [item for item in interior if item[0] != value]
    middle = copies + others if side == "left" else others + copies
    new_segment = [segment[0], *middle, segment[-1]]
    values = list(word.values)
    ids = list(word.position_ids)
    values[first - 1 : last] = [v for v, _ in new_segment]
    ids[first - 1 : last] = [pid for _, pid in new_segment]
    return ChainWord(tuple(values), height=word.height, position_ids=tuple(ids))


def repeated_sandwich_offending_values(
    word: ChainWord,
    left_repeats: int,
    right_repeats: int,
) -> tuple[int, ...]:
    """Values whose fibre gaps witness ``2^a 1 2^b`` structurally."""

    if left_repeats < 1 or right_repeats < 1:
        raise ValueError("capacities must be positive")
    out: list[int] = []
    for value in range(1, word.height + 1):
        multiplicity = len(word.fibre(value))
        if multiplicity < left_repeats + right_repeats:
            continue
        for gap in fibre_gaps(word, value):
            if (
                gap.lower_positions
                and gap.gap_index >= left_repeats
                and multiplicity - gap.gap_index >= right_repeats
            ):
                out.append(value)
                break
    return tuple(out)


@dataclass(frozen=True)
class FibreGapPackT(Transformation):
    """Heuristic capacity-shift repair for a repeated-sandwich pattern.

    Repeatedly choose a value whose fibre witnesses ``2^a 1 2^b`` and pack its
    internal copies left or right.  This is intentionally kept in the discovery
    layer: it is a low-complexity *candidate schema*, not a theorem or a declared
    bijection.
    """

    left_repeats: int
    right_repeats: int
    side: str = "right"
    value_order: str = "asc"
    max_rounds: int | None = None

    signature = TransformSignature(delta_length=0, delta_height=0, partial=False)
    search_cost = 3

    def __post_init__(self) -> None:
        if self.left_repeats < 1 or self.right_repeats < 1:
            raise ValueError("capacities must be positive")
        if self.side not in {"left", "right"}:
            raise ValueError("side must be left/right")
        if self.value_order not in {"asc", "desc"}:
            raise ValueError("value_order must be asc/desc")

    def apply(self, word: ChainWord) -> TransformResult:
        y = word
        rounds = self.max_rounds if self.max_rounds is not None else max(1, 2 * max(1, word.height))
        for _ in range(rounds):
            offenders = repeated_sandwich_offending_values(
                y, self.left_repeats, self.right_repeats
            )
            if not offenders:
                break
            value = min(offenders) if self.value_order == "asc" else max(offenders)
            z = pack_internal_occurrences(y, value, side=self.side)
            if z.values == y.values:
                break
            y = z
        output_by_id = {pid: i for i, pid in enumerate(y.position_ids, start=1)}
        pmap = tuple(output_by_id[pid] for pid in word.position_ids)
        return TransformResult(
            y,
            position_map=pmap,
            value_map=tuple(range(1, word.height + 1)),
        )


def FibreGapPack(
    left_repeats: int,
    right_repeats: int,
    *,
    side: str = "right",
    value_order: str = "asc",
) -> FibreGapPackT:
    return FibreGapPackT(left_repeats, right_repeats, side=side, value_order=value_order)
