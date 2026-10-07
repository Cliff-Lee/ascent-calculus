from ac import (
    ChainWord, ExtremeGapSwap, GapSwapRepair, Modified, Avoid,
    modified_defect, repair_modified_defects, defect_measure,
    swap_fibre_gaps, rotate_interval,
)
from ac.discovery.synthesis import analyze_finite_map
from ac.generate.universes import modified_via_hat


def test_swap_fibre_gaps_reproduces_e9_exception_and_is_involutive_on_fixed_gap_indices():
    x = ChainWord.of([1,2,2,1,3,2])
    y = swap_fibre_gaps(x, 2, 1, 2).output
    assert y.values == (1,2,1,3,2,2)
    z = swap_fibre_gaps(y, 2, 1, 2).output
    assert z.values == x.values


def test_extreme_gap_swap_is_exact_through_n7_and_has_single_structural_failure_at_n8():
    source = Modified() & Avoid("2122")
    target = Modified() & Avoid("2212")
    t = ExtremeGapSwap(2,1)
    d7 = analyze_finite_map(t, source, target, universe=modified_via_hat, n=7)
    assert d7.bijective
    d8 = analyze_finite_map(t, source, target, universe=modified_via_hat, n=8)
    assert len(d8.outside_target) == 1
    assert len(d8.collisions) == 0
    assert len(d8.missing_targets) == 1


def test_canonical_e10_rotation_repairs_unique_n8_defect():
    bad = ChainWord.of([1,2,1,4,3,2,3,2])
    d = modified_defect(bad)
    assert d.first_not_top == (5,)
    assert d.top_not_first == (7,)
    trace = repair_modified_defects(bad)
    assert trace.terminated
    assert trace.steps == 1
    assert trace.output.values == (1,2,1,3,2,4,3,2)


def test_defect_measure_decreases_in_two_step_blind_n10_example():
    y = ChainWord.of([1,2,1,4,3,5,4,2,3,2])
    trace = repair_modified_defects(y)
    assert trace.terminated
    assert trace.steps == 2
    measures = [defect_measure(w) for w in trace.states]
    assert all(b < a for a,b in zip(measures, measures[1:]))


def test_gap_swap_plus_canonical_repair_is_bijection_at_n9():
    source = Modified() & Avoid("2122")
    target = Modified() & Avoid("2212")
    d = analyze_finite_map(
        GapSwapRepair(2,1), source, target,
        universe=modified_via_hat, n=9,
    )
    assert d.bijective


def test_natural_modified_growth_handles_fresh_nonmaximum_value_and_matches_level_7():
    from ac import modified_children, modified_parent
    x = ChainWord.of([1,2,1])
    vals = {y.values for y in modified_children(x)}
    assert (1,3,1,2) in vals
    y = ChainWord.of([1,3,1,2])
    assert modified_parent(y).values == x.values

    level = tuple(modified_via_hat(6))
    children = {y.values for x in level for y in modified_children(x)}
    expected = {y.values for y in modified_via_hat(7)}
    assert children == expected
