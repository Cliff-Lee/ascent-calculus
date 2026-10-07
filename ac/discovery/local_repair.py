from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ac.algebra.transforms import TransformSignature, Transformation
from ac.core.word import ChainWord
from ac.core.scope import Scope
from ac.core.typed import Position, ValueLevel
from ac.logic.selectors import PositionSelector, ValueSelector, SelectionKind
from ac.discovery.fibre_geometry import fibre_gaps
from ac.discovery.repairs import repeated_sandwich_offending_values
from ac.transform.basic import TransformResult


def _result_from_reordered(source: ChainWord, values: list[int], ids: list[int]) -> TransformResult:
    y = ChainWord(tuple(values), height=source.height, position_ids=tuple(ids))
    pos = {pid: i for i, pid in enumerate(y.position_ids, start=1)}
    return TransformResult(
        y,
        position_map=tuple(pos[pid] for pid in source.position_ids),
        value_map=tuple(range(1, source.height + 1)),
    )


def rotate_interval(word: ChainWord, start: int, end: int, amount: int = -1) -> TransformResult:
    """Cyclically rotate the closed positional interval [start,end].

    ``amount=-1`` is a one-step left rotation, ``amount=+1`` a one-step right
    rotation.  Position IDs travel with entries.
    """
    if not (1 <= start <= end <= len(word)):
        raise ValueError("invalid interval")
    length = end - start + 1
    if length <= 1:
        return _result_from_reordered(word, list(word.values), list(word.position_ids))
    k = amount % length
    if k == 0:
        return _result_from_reordered(word, list(word.values), list(word.position_ids))
    vals = list(word.values)
    ids = list(word.position_ids)
    segv = vals[start - 1:end]
    segi = ids[start - 1:end]
    segv = segv[-k:] + segv[:-k]
    segi = segi[-k:] + segi[:-k]
    vals[start - 1:end] = segv
    ids[start - 1:end] = segi
    return _result_from_reordered(word, vals, ids)


def move_interval(word: ChainWord, start: int, end: int, cut: int) -> TransformResult:
    """Move [start,end] to source cut ``cut`` (0..n), preserving order.

    The cut is interpreted in the source word.  Cuts strictly inside the moved
    interval are undefined because they do not specify a genuine relocation.
    """
    if not (1 <= start <= end <= len(word)):
        raise ValueError("invalid interval")
    if not (0 <= cut <= len(word)):
        raise ValueError("invalid cut")
    if start - 1 <= cut <= end:
        raise ValueError("cut lies inside/adjacent to moved interval")
    items = list(zip(word.values, word.position_ids))
    seg = items[start - 1:end]
    rest = items[:start - 1] + items[end:]
    if cut < start - 1:
        dest = cut
    else:
        dest = cut - len(seg)
    new = rest[:dest] + seg + rest[dest:]
    return _result_from_reordered(word, [v for v,_ in new], [pid for _,pid in new])


def swap_intervals(word: ChainWord, a1: int, a2: int, b1: int, b2: int) -> TransformResult:
    """Swap two disjoint closed intervals while preserving internal order."""
    if not (1 <= a1 <= a2 < b1 <= b2 <= len(word)):
        raise ValueError("intervals must be ordered and disjoint")
    items = list(zip(word.values, word.position_ids))
    A = items[a1 - 1:a2]
    M = items[a2:b1 - 1]
    B = items[b1 - 1:b2]
    new = items[:a1 - 1] + B + M + A + items[b2:]
    return _result_from_reordered(word, [v for v,_ in new], [pid for _,pid in new])


def swap_fibre_gaps(word: ChainWord, value: int, gap_a: int, gap_b: int) -> TransformResult:
    """Swap complete open gaps between occurrences of one repeated value.

    If P_v=(p1<...<pm), gap r is the material strictly between p_r and p_{r+1}.
    The copies of v remain separators, retain their order/IDs, and the two gap
    payloads are exchanged intact.  This is reversible even when gap lengths differ.
    """
    fibre = word.fibre(value)
    if len(fibre) < 2:
        return _result_from_reordered(word, list(word.values), list(word.position_ids))
    max_gap = len(fibre) - 1
    if not (1 <= gap_a <= max_gap and 1 <= gap_b <= max_gap):
        raise ValueError("gap index out of range")
    if gap_a == gap_b:
        return _result_from_reordered(word, list(word.values), list(word.position_ids))
    if gap_a > gap_b:
        gap_a, gap_b = gap_b, gap_a

    # Parse the whole fibre span into separators and gap payloads.
    first, last = fibre[0], fibre[-1]
    items = list(zip(word.values, word.position_ids))
    span = items[first - 1:last]
    gaps: list[list[tuple[int,int]]] = [[] for _ in range(max_gap)]
    separators: list[tuple[int,int]] = []
    gi = -1
    for item in span:
        if item[0] == value:
            separators.append(item)
            gi += 1
        else:
            if gi < 0 or gi >= max_gap:
                raise AssertionError("malformed fibre span")
            gaps[gi].append(item)
    gaps[gap_a - 1], gaps[gap_b - 1] = gaps[gap_b - 1], gaps[gap_a - 1]
    rebuilt: list[tuple[int,int]] = []
    for r, sep in enumerate(separators):
        rebuilt.append(sep)
        if r < max_gap:
            rebuilt.extend(gaps[r])
    new = items[:first - 1] + rebuilt + items[last:]
    return _result_from_reordered(word, [v for v,_ in new], [pid for _,pid in new])


@dataclass(frozen=True)
class RepeatedSandwichOccurrence:
    repeated_value: int
    lower_position: int
    gap_index: int
    multiplicity: int
    left_repeats: int
    right_repeats: int


def repeated_sandwich_witnesses(word: ChainWord, left_repeats: int, right_repeats: int) -> tuple[RepeatedSandwichOccurrence, ...]:
    if left_repeats < 1 or right_repeats < 1:
        raise ValueError("capacities must be positive")
    out: list[RepeatedSandwichOccurrence] = []
    for value in range(1, word.height + 1):
        fibre = word.fibre(value)
        m = len(fibre)
        if m < left_repeats + right_repeats:
            continue
        for gap in fibre_gaps(word, value):
            if gap.gap_index < left_repeats or m - gap.gap_index < right_repeats:
                continue
            for p in gap.lower_positions:
                out.append(RepeatedSandwichOccurrence(value, p, gap.gap_index, m, left_repeats, right_repeats))
    return tuple(out)


@dataclass(frozen=True)
class RepeatedSandwichLower(PositionSelector):
    left_repeats: int
    right_repeats: int
    kind = SelectionKind.POSITION

    def _evaluate(self, word: ChainWord, scope: Scope):
        allowed = {int(p) for p in scope.positions(word)}
        return frozenset(Position(w.lower_position) for w in repeated_sandwich_witnesses(word, self.left_repeats, self.right_repeats) if w.lower_position in allowed)


@dataclass(frozen=True)
class RepeatedSandwichValues(ValueSelector):
    left_repeats: int
    right_repeats: int
    kind = SelectionKind.VALUE

    def _evaluate(self, word: ChainWord, scope: Scope):
        allowed_pos = {int(p) for p in scope.positions(word)}
        vals = {w.repeated_value for w in repeated_sandwich_witnesses(word, self.left_repeats, self.right_repeats) if w.lower_position in allowed_pos}
        return frozenset(ValueLevel(v) for v in vals)


@dataclass(frozen=True)
class RotateT(Transformation):
    start: int
    end: int
    amount: int = -1
    signature = TransformSignature(delta_length=0, delta_height=0, partial=True)
    search_cost = 2

    def apply(self, word: ChainWord) -> TransformResult:
        return rotate_interval(word, self.start, self.end, self.amount)

    def inverse(self) -> Transformation:
        return RotateT(self.start, self.end, -self.amount)


@dataclass(frozen=True)
class SwapFibreGapsT(Transformation):
    value: int
    gap_a: int
    gap_b: int
    signature = TransformSignature(delta_length=0, delta_height=0, partial=True)
    search_cost = 2

    def apply(self, word: ChainWord) -> TransformResult:
        return swap_fibre_gaps(word, self.value, self.gap_a, self.gap_b)

    def inverse(self) -> Transformation:
        return self


@dataclass(frozen=True)
class ExtremeGapSwapT(Transformation):
    """Iteratively eliminate 2^a 1 2^b witnesses by swapping extreme fibre gaps.

    For an offending value, swap its first and last complete gaps.  This preserves
    all entries and their provenance, unlike packing.  The first offending value
    in the chosen value order is processed, then witnesses are recomputed.
    """
    left_repeats: int
    right_repeats: int
    value_order: str = "asc"
    max_rounds: int | None = None
    signature = TransformSignature(delta_length=0, delta_height=0, partial=False)
    search_cost = 3

    def __post_init__(self):
        if self.left_repeats < 1 or self.right_repeats < 1:
            raise ValueError("capacities must be positive")
        if self.value_order not in {"asc", "desc"}:
            raise ValueError("value_order must be asc/desc")

    def apply(self, word: ChainWord) -> TransformResult:
        y = word
        rounds = self.max_rounds if self.max_rounds is not None else max(1, 4 * max(1, word.height))
        seen = set()
        for _ in range(rounds):
            key = (y.values, y.position_ids)
            if key in seen:
                break
            seen.add(key)
            offenders = repeated_sandwich_offending_values(y, self.left_repeats, self.right_repeats)
            if not offenders:
                break
            value = min(offenders) if self.value_order == "asc" else max(offenders)
            m = len(y.fibre(value))
            if m < 3:
                break
            z = swap_fibre_gaps(y, value, 1, m - 1).output
            if z.values == y.values:
                break
            y = z
        pos = {pid: i for i, pid in enumerate(y.position_ids, start=1)}
        return TransformResult(y, position_map=tuple(pos[pid] for pid in word.position_ids), value_map=tuple(range(1, word.height + 1)))


def Rotate(start: int, end: int, amount: int = -1) -> RotateT:
    return RotateT(start, end, amount)


def SwapFibreGaps(value: int, gap_a: int, gap_b: int) -> SwapFibreGapsT:
    return SwapFibreGapsT(value, gap_a, gap_b)


def ExtremeGapSwap(left_repeats: int, right_repeats: int, *, value_order: str = "asc") -> ExtremeGapSwapT:
    return ExtremeGapSwapT(left_repeats, right_repeats, value_order=value_order)

@dataclass(frozen=True)
class ModifiedDefect:
    """Mismatch between first-occurrence and literature ascent-top sets."""
    first_not_top: tuple[int, ...]
    top_not_first: tuple[int, ...]

    @property
    def empty(self) -> bool:
        return not self.first_not_top and not self.top_not_first

    @property
    def size(self) -> int:
        return len(self.first_not_top) + len(self.top_not_first)


def modified_defect(word: ChainWord) -> ModifiedDefect:
    return ModifiedDefect(
        tuple(sorted(word.first_positions - word.ascent_tops)),
        tuple(sorted(word.ascent_tops - word.first_positions)),
    )


@dataclass(frozen=True)
class DefectPair:
    """A false first occurrence paired with a false ascent top of the same value."""
    first_position: int
    top_position: int
    value: int

    @property
    def span(self) -> int:
        return self.top_position - self.first_position


def defect_pairs(word: ChainWord) -> tuple[DefectPair, ...]:
    d = modified_defect(word)
    out: list[DefectPair] = []
    used: set[int] = set()
    for f in d.first_not_top:
        v = word.at(f)
        candidates = [q for q in d.top_not_first if q not in used and q > f and word.at(q) == v]
        if candidates:
            q = min(candidates)
            used.add(q)
            out.append(DefectPair(f, q, v))
    return tuple(out)


@dataclass(frozen=True)
class DefectRotation:
    pair: DefectPair
    start: int
    end: int
    left_amount: int

    @property
    def interval_length(self) -> int:
        return self.end - self.start + 1


def canonical_defect_rotation(word: ChainWord, *, choose: str = "leftmost") -> DefectRotation | None:
    """Infer the canonical adjacent-block rotation for one modified defect.

    Choose a paired defect f<q with value v.  Let s be the position immediately
    after the nearest entry left of f whose value is <v.  Then every entry in
    [s,f-1] is >=v.  Swap the adjacent blocks

        A = x[s:f-1],   B = x[f:q-1]

    by left-rotating [s,q-1] by |A|=f-s.  This moves the first v to the first
    position after a lower predecessor while retaining every occurrence ID.
    """
    pairs = defect_pairs(word)
    if not pairs:
        return None
    if choose == "leftmost":
        pair = min(pairs, key=lambda p: (p.first_position, p.value, p.top_position))
    elif choose == "rightmost":
        pair = max(pairs, key=lambda p: (p.first_position, p.value, p.top_position))
    elif choose == "value":
        pair = min(pairs, key=lambda p: (p.value, p.first_position, p.top_position))
    else:
        raise ValueError("choose must be leftmost/rightmost/value")
    f, q, v = pair.first_position, pair.top_position, pair.value
    j = f - 1
    while j >= 1 and word.at(j) >= v:
        j -= 1
    s = j + 1
    if s >= f:
        return None
    return DefectRotation(pair, start=s, end=q - 1, left_amount=f - s)


@dataclass(frozen=True)
class DefectRepairTrace:
    source: ChainWord
    output: ChainWord | None
    rotations: tuple[DefectRotation, ...]
    states: tuple[ChainWord, ...]
    terminated: bool
    reason: str

    @property
    def steps(self) -> int:
        return len(self.rotations)


def defect_measure(word: ChainWord) -> tuple[int, int, int]:
    """Discovery measure used to monitor canonical-repair termination.

    Lexicographically: total structural mismatch, total paired span, then total
    false-first position.  E10 verifies strict descent on the benchmark through
    degree 10; this is currently a discovered invariant, not a declared proof.
    """
    pairs = defect_pairs(word)
    return (
        modified_defect(word).size,
        sum(p.span for p in pairs),
        sum(p.first_position for p in pairs),
    )


def repair_modified_defects(
    word: ChainWord,
    *,
    choose: str = "leftmost",
    max_steps: int | None = None,
) -> DefectRepairTrace:
    """Iterate canonical defect rotations until First=AscTop or repair fails."""
    y = word
    limit = max_steps if max_steps is not None else max(1, 2 * len(word))
    states = [word]
    rotations: list[DefectRotation] = []
    seen = {word.values}
    for _ in range(limit):
        if modified_defect(y).empty:
            return DefectRepairTrace(word, y, tuple(rotations), tuple(states), True, "modified")
        rule = canonical_defect_rotation(y, choose=choose)
        if rule is None:
            return DefectRepairTrace(word, None, tuple(rotations), tuple(states), False, "unpaired defect")
        z = rotate_interval(y, rule.start, rule.end, -rule.left_amount).output
        rotations.append(rule)
        states.append(z)
        if z.values in seen:
            return DefectRepairTrace(word, None, tuple(rotations), tuple(states), False, "cycle")
        seen.add(z.values)
        y = z
    return DefectRepairTrace(word, None, tuple(rotations), tuple(states), False, "step limit")


@dataclass(frozen=True)
class GapSwapRepairT(Transformation):
    """Extreme fibre-gap swap followed by canonical modified-defect bubbling."""
    left_repeats: int
    right_repeats: int
    value_order: str = "asc"
    choose: str = "leftmost"
    max_repair_steps: int | None = None
    signature = TransformSignature(delta_length=0, delta_height=0, partial=True)
    search_cost = 5

    def dual(self) -> "GapSwapRepairT":
        """Return the parameter-swapped candidate inverse.

        E10 verifies this as a two-sided inverse on the 2122/2212 benchmark
        through degree 10.  It is intentionally named ``dual`` rather than
        overriding ``Transformation.inverse`` until a general proof is recorded.
        """
        return GapSwapRepairT(
            self.right_repeats,
            self.left_repeats,
            value_order=self.value_order,
            choose=self.choose,
            max_repair_steps=self.max_repair_steps,
        )

    def apply(self, word: ChainWord) -> TransformResult:
        swapped = ExtremeGapSwap(
            self.left_repeats,
            self.right_repeats,
            value_order=self.value_order,
        ).apply(word).output
        trace = repair_modified_defects(
            swapped,
            choose=self.choose,
            max_steps=self.max_repair_steps,
        )
        if not trace.terminated or trace.output is None:
            raise ValueError(f"canonical local repair failed: {trace.reason}")
        y = trace.output
        pos = {pid: i for i, pid in enumerate(y.position_ids, start=1)}
        return TransformResult(
            y,
            position_map=tuple(pos[pid] for pid in word.position_ids),
            value_map=tuple(range(1, word.height + 1)),
        )


def GapSwapRepair(
    left_repeats: int,
    right_repeats: int,
    *,
    value_order: str = "asc",
    choose: str = "leftmost",
) -> GapSwapRepairT:
    return GapSwapRepairT(left_repeats, right_repeats, value_order=value_order, choose=choose)
