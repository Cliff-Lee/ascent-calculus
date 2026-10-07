from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ac.core.word import ChainWord
from ac.discovery.fibre_geometry import fibre_gaps, contains_repeated_sandwich
from ac.discovery.repairs import repeated_sandwich_offending_values
from ac.discovery.local_repair import swap_fibre_gaps


class ExtremeOrientation(str, Enum):
    """Location of lower-valued material inside one value fibre.

    LEFT  -- lower material occurs only in the first fibre gap.
    RIGHT -- lower material occurs only in the last fibre gap.
    BOTH  -- both conditions hold (for example no lower material, or a
             two-occurrence fibre whose unique gap is simultaneously first/last).
    MIXED -- neither extreme condition holds.
    """

    LEFT = "left"
    RIGHT = "right"
    BOTH = "both"
    MIXED = "mixed"


def lower_gap_indices(word: ChainWord, value: int) -> tuple[int, ...]:
    return tuple(
        gap.gap_index for gap in fibre_gaps(word, value) if gap.lower_positions
    )


def fibre_orientation(word: ChainWord, value: int) -> ExtremeOrientation:
    fibre = word.fibre(value)
    if not fibre:
        raise ValueError("value fibre is empty")
    m = len(fibre)
    indices = set(lower_gap_indices(word, value))
    if not indices:
        return ExtremeOrientation.BOTH
    left = indices <= {1}
    right = indices <= {m - 1}
    if left and right:
        return ExtremeOrientation.BOTH
    if left:
        return ExtremeOrientation.LEFT
    if right:
        return ExtremeOrientation.RIGHT
    return ExtremeOrientation.MIXED


def is_extreme_oriented(word: ChainWord) -> bool:
    return all(
        fibre_orientation(word, value) is not ExtremeOrientation.MIXED
        for value in range(1, word.height + 1)
        if word.fibre(value)
    )


def right_oriented(word: ChainWord) -> bool:
    """Every fibre has lower material only in its final gap.

    By the repeated-sandwich gap characterization this is exactly avoidance of
    2122 = 2^1 1 2^2.
    """
    return all(
        fibre_orientation(word, value)
        in {ExtremeOrientation.RIGHT, ExtremeOrientation.BOTH}
        for value in range(1, word.height + 1)
        if word.fibre(value)
    )


def left_oriented(word: ChainWord) -> bool:
    """Every fibre has lower material only in its first gap.

    By the repeated-sandwich gap characterization this is exactly avoidance of
    2212 = 2^2 1 2^1.
    """
    return all(
        fibre_orientation(word, value)
        in {ExtremeOrientation.LEFT, ExtremeOrientation.BOTH}
        for value in range(1, word.height + 1)
        if word.fibre(value)
    )


def threshold_projection(word: ChainWord, value: int) -> tuple[int, ...]:
    """Delete entries above ``value`` without relabelling the remaining values."""
    return tuple(v for v in word.values if v <= value)


def maximum_extreme_normal_form(word: ChainWord, value: int) -> bool:
    """Check the threshold-projection normal form for one value.

    In the projection to values <=v, v is the maximum.  If its fibre is
    extreme-oriented then all non-v material between the first and last v lies
    in one extreme gap, hence all other consecutive v-gaps are empty.
    """
    proj = threshold_projection(word, value)
    positions = [i for i, v in enumerate(proj) if v == value]
    if len(positions) <= 1:
        return True
    active = []
    for r, (a, b) in enumerate(zip(positions, positions[1:]), start=1):
        if b > a + 1:
            active.append(r)
    return set(active) <= {1} or set(active) <= {len(positions) - 1}


@dataclass(frozen=True)
class ExtremeGapProofStep:
    pivot: int
    before: ChainWord
    after: ChainWord
    pivot_before: ExtremeOrientation
    pivot_after: ExtremeOrientation
    lower_projection_preserved: bool
    lower_orientations_preserved: bool
    orientation_closed: bool
    smaller_target_clean: bool


@dataclass(frozen=True)
class ExtremeGapProofTrace:
    source: ChainWord
    output: ChainWord
    steps: tuple[ExtremeGapProofStep, ...]
    source_right_oriented: bool
    output_left_oriented: bool
    strictly_increasing_pivots: bool
    pattern_target_clean: bool


def extreme_gap_proof_trace_2122_to_2212(word: ChainWord) -> ExtremeGapProofTrace:
    """Instrument ExtremeGapSwap(2,1) with proof-oriented invariants.

    This routine deliberately mirrors the current ascending-value algorithm but
    records only structural statements useful for proof extraction.  It does
    not declare the still-open global orientation-closure lemma as proved.
    """
    y = word
    rows: list[ExtremeGapProofStep] = []
    pivots: list[int] = []
    for _ in range(max(1, 4 * max(1, word.height))):
        offenders = repeated_sandwich_offending_values(y, 2, 1)
        if not offenders:
            break
        pivot = min(offenders)
        before = y
        before_orients = {
            u: fibre_orientation(before, u)
            for u in range(1, before.height + 1)
            if before.fibre(u)
        }
        low_proj = threshold_projection(before, pivot - 1) if pivot > 1 else ()
        m = len(before.fibre(pivot))
        y = swap_fibre_gaps(before, pivot, 1, m - 1).output
        after_orients = {
            u: fibre_orientation(y, u)
            for u in range(1, y.height + 1)
            if y.fibre(u)
        }
        rows.append(
            ExtremeGapProofStep(
                pivot=pivot,
                before=before,
                after=y,
                pivot_before=before_orients[pivot],
                pivot_after=after_orients[pivot],
                lower_projection_preserved=(
                    threshold_projection(y, pivot - 1) if pivot > 1 else ()
                ) == low_proj,
                lower_orientations_preserved=all(
                    after_orients[u] == before_orients[u]
                    for u in before_orients
                    if u < pivot
                ),
                orientation_closed=all(
                    state is not ExtremeOrientation.MIXED
                    for state in after_orients.values()
                ),
                smaller_target_clean=all(
                    after_orients[u]
                    in {ExtremeOrientation.LEFT, ExtremeOrientation.BOTH}
                    for u in after_orients
                    if u <= pivot
                ),
            )
        )
        pivots.append(pivot)
    return ExtremeGapProofTrace(
        source=word,
        output=y,
        steps=tuple(rows),
        source_right_oriented=right_oriented(word),
        output_left_oriented=left_oriented(y),
        strictly_increasing_pivots=all(a < b for a, b in zip(pivots, pivots[1:])),
        pattern_target_clean=not contains_repeated_sandwich(y, 2, 1),
    )


def _ids_at_positions(word: ChainWord, positions) -> frozenset[int]:
    return frozenset(word.position_id(p) for p in positions)


def defect_value_potential(word: ChainWord) -> int:
    """Well-founded value potential for modified defects.

    A defect at value v receives weight (n+1)^(h-v).  Therefore deleting a
    defect at v and creating any number (at most n) of defects strictly above v
    decreases the potential.  E11 uses this as the proof-oriented replacement
    for the positional discovery measure from E10.
    """
    from ac.discovery.local_repair import modified_defect

    base = len(word) + 1
    return sum(
        base ** (word.height - word.at(f))
        for f in modified_defect(word).first_not_top
    )


@dataclass(frozen=True)
class DefectRotationCertificate:
    pivot_value: int
    first_position: int
    second_position: int
    first_is_rank1: bool
    second_is_rank2: bool
    consecutive_in_fibre: bool
    has_lower_predecessor_before_block: bool
    block_a_strictly_above_pivot: bool
    second_has_lower_predecessor: bool
    ascent_top_ids_exchange_exactly: bool
    first_identity_changes: tuple[int, ...]
    crossing_first_values: tuple[int, ...]
    first_change_characterization_exact: bool
    newly_created_defect_values: tuple[int, ...]
    new_defects_strictly_above_pivot: bool
    value_potential_decreases: bool

    @property
    def local_boundary_lemma_ready(self) -> bool:
        return all(
            (
                self.first_is_rank1,
                self.second_is_rank2,
                self.consecutive_in_fibre,
                self.has_lower_predecessor_before_block,
                self.block_a_strictly_above_pivot,
                self.second_has_lower_predecessor,
                self.ascent_top_ids_exchange_exactly,
                self.first_change_characterization_exact,
                self.new_defects_strictly_above_pivot,
                self.value_potential_decreases,
            )
        )


def certify_defect_rotation(word: ChainWord, rule) -> DefectRotationCertificate:
    """Certify the local combinatorics of one canonical defect rotation.

    This intentionally works with stable occurrence IDs.  The key local fact is
    that the rotation changes ascent-top identity only from q to f.  First-
    occurrence identity can change only for values represented in both swapped
    blocks and having no earlier occurrence; such values lie strictly above the
    pivot because block A lies before the first pivot occurrence and is >v.
    """
    from ac.discovery.local_repair import rotate_interval, modified_defect

    pair = rule.pair
    f, q, v = pair.first_position, pair.top_position, pair.value
    s = rule.start
    fibre = word.fibre(v)
    rank_f = fibre.index(f) + 1
    rank_q = fibre.index(q) + 1

    a_positions = set(range(s, f))
    b_positions = set(range(f, q))
    A = tuple(word.at(p) for p in range(s, f))

    z = rotate_interval(word, rule.start, rule.end, -rule.left_amount).output

    top_before = _ids_at_positions(word, word.ascent_tops)
    top_after = _ids_at_positions(z, z.ascent_tops)
    fid = word.position_id(f)
    qid = word.position_id(q)
    expected_top_after = (top_before - {qid}) | {fid}

    changed_first_values: list[int] = []
    crossing_values: list[int] = []
    for w in range(1, word.height + 1):
        fib = word.fibre(w)
        if not fib:
            continue
        old_first_id = word.position_id(fib[0])
        new_first_id = z.position_id(z.fibre(w)[0])
        if old_first_id != new_first_id:
            changed_first_values.append(w)
        fib_set = set(fib)
        if (
            fib_set & a_positions
            and fib_set & b_positions
            and not any(p < s for p in fib)
        ):
            crossing_values.append(w)

    before_defect_values = {
        word.at(p) for p in modified_defect(word).first_not_top
    }
    after_defect_values = {
        z.at(p) for p in modified_defect(z).first_not_top
    }
    newly_created = tuple(sorted(after_defect_values - before_defect_values))

    return DefectRotationCertificate(
        pivot_value=v,
        first_position=f,
        second_position=q,
        first_is_rank1=(rank_f == 1),
        second_is_rank2=(rank_q == 2),
        consecutive_in_fibre=(rank_q == rank_f + 1),
        has_lower_predecessor_before_block=(s > 1 and word.at(s - 1) < v),
        block_a_strictly_above_pivot=bool(A) and all(a > v for a in A),
        second_has_lower_predecessor=(q > 1 and word.at(q - 1) < v),
        ascent_top_ids_exchange_exactly=(top_after == expected_top_after),
        first_identity_changes=tuple(changed_first_values),
        crossing_first_values=tuple(crossing_values),
        first_change_characterization_exact=(
            tuple(changed_first_values) == tuple(crossing_values)
        ),
        newly_created_defect_values=newly_created,
        new_defects_strictly_above_pivot=all(w > v for w in newly_created),
        value_potential_decreases=(defect_value_potential(z) < defect_value_potential(word)),
    )

@dataclass(frozen=True)
class DefectAdmissibility:
    perfect_pairing: bool
    unique_pair_values: bool
    first_second_pairs: bool
    canonical_blocks_exist: bool

    @property
    def ok(self) -> bool:
        return all((
            self.perfect_pairing,
            self.unique_pair_values,
            self.first_second_pairs,
            self.canonical_blocks_exist,
        ))


def defect_admissibility(word: ChainWord) -> DefectAdmissibility:
    """Structural invariant isolated by E11 for the repair phase.

    An admissible state has every First/AscTop mismatch paired bijectively by
    value, each pair is the first and second occurrence of that value, and the
    canonical lower-predecessor block for every false first is nonempty.
    """
    from ac.discovery.local_repair import modified_defect, defect_pairs

    d = modified_defect(word)
    pairs = defect_pairs(word)
    perfect = (
        len(pairs) == len(d.first_not_top) == len(d.top_not_first)
    )
    unique_values = len({p.value for p in pairs}) == len(pairs)
    ranks = all(
        word.occurrence_rank(p.first_position) == 1
        and word.occurrence_rank(p.top_position) == 2
        for p in pairs
    )
    blocks = True
    for p in pairs:
        f, v = p.first_position, p.value
        j = f - 1
        while j >= 1 and word.at(j) >= v:
            j -= 1
        s = j + 1
        if not (s < f and s > 1 and word.at(s - 1) < v):
            blocks = False
            break
        if not all(word.at(k) > v for k in range(s, f)):
            blocks = False
            break
    return DefectAdmissibility(perfect, unique_values, ranks, blocks)


def orientation_profile(word: ChainWord) -> tuple[ExtremeOrientation, ...]:
    return tuple(
        fibre_orientation(word, v)
        for v in range(1, word.height + 1)
        if word.fibre(v)
    )


def repair_heavy_crossing_values(word: ChainWord, rule) -> tuple[int, ...]:
    """Multiplicity>=3 fibres meeting both blocks A and B of a repair move.

    E11c discovered that all reachable E10 repair states have no such value.
    This is stronger than defect admissibility and is exactly the obstruction in
    the smallest generic target-avoidance counterexamples found so far.
    """
    s = rule.start
    f = rule.pair.first_position
    q = rule.pair.top_position
    A = set(range(s, f))
    B = set(range(f, q))
    out = []
    for v in range(1, word.height + 1):
        fib = set(word.fibre(v))
        if len(fib) >= 3 and fib & A and fib & B:
            out.append(v)
    return tuple(out)


def repair_preserves_orientation_profile(word: ChainWord, rule) -> bool:
    from ac.discovery.local_repair import rotate_interval
    y = rotate_interval(word, rule.start, rule.end, -rule.left_amount).output
    return orientation_profile(y) == orientation_profile(word)
