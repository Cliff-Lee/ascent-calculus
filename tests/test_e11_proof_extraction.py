from ac import ChainWord
from ac.discovery.proof_extraction import (
    ExtremeOrientation,
    fibre_orientation,
    is_extreme_oriented,
    right_oriented,
    left_oriented,
    maximum_extreme_normal_form,
    extreme_gap_proof_trace_2122_to_2212,
)
from ac.discovery.fibre_geometry import contains_repeated_sandwich
from ac.discovery.local_repair import swap_fibre_gaps
from ac.generate.universes import cayley_words, modified_via_hat


def test_orientation_is_exact_repeated_sandwich_characterization():
    for n in range(1, 7):
        for x in cayley_words(n):
            assert right_oriented(x) == (not contains_repeated_sandwich(x, 1, 2))
            assert left_oriented(x) == (not contains_repeated_sandwich(x, 2, 1))


def test_threshold_maximum_normal_form_matches_extreme_orientation():
    for n in range(1, 7):
        for x in cayley_words(n):
            for v in range(1, x.height + 1):
                if not x.fibre(v):
                    continue
                assert maximum_extreme_normal_form(x, v) == (
                    fibre_orientation(x, v) is not ExtremeOrientation.MIXED
                )


def test_extreme_oriented_class_closed_under_extreme_gap_swaps_small():
    # E11 proof-obligation stress test: this is finite evidence for the local
    # closure lemma that remains to be proved symbolically.
    for n in range(1, 7):
        for x in cayley_words(n):
            if not is_extreme_oriented(x):
                continue
            for v in range(1, x.height + 1):
                m = len(x.fibre(v))
                if m < 3:
                    continue
                y = swap_fibre_gaps(x, v, 1, m - 1).output
                assert is_extreme_oriented(y)


def test_e11_trace_invariants_on_modified_sources():
    for n in range(1, 9):
        for x in modified_via_hat(n):
            if contains_repeated_sandwich(x, 1, 2):
                continue
            tr = extreme_gap_proof_trace_2122_to_2212(x)
            assert tr.source_right_oriented
            assert tr.output_left_oriented
            assert tr.pattern_target_clean
            assert tr.strictly_increasing_pivots
            for step in tr.steps:
                assert step.pivot_before in {ExtremeOrientation.RIGHT, ExtremeOrientation.BOTH}
                assert step.pivot_after in {ExtremeOrientation.LEFT, ExtremeOrientation.BOTH}
                assert step.lower_projection_preserved
                assert step.lower_orientations_preserved
                assert step.orientation_closed
                assert step.smaller_target_clean


def test_defect_rotation_local_certificates_on_e10_training_range():
    from ac.discovery.local_repair import (
        ExtremeGapSwap, modified_defect, repair_modified_defects,
    )
    from ac.discovery.proof_extraction import certify_defect_rotation

    # n<=9 contains all E9 defect shapes while keeping the unit suite quick.
    seen = 0
    for n in range(6, 10):
        for x in modified_via_hat(n):
            if contains_repeated_sandwich(x, 1, 2):
                continue
            y = ExtremeGapSwap(2, 1).apply(x).output
            if modified_defect(y).empty:
                continue
            tr = repair_modified_defects(y)
            for state, rule in zip(tr.states, tr.rotations):
                cert = certify_defect_rotation(state, rule)
                assert cert.local_boundary_lemma_ready
                seen += 1
    assert seen > 0


def test_gap_swap_repair_states_are_defect_admissible_training_range():
    from ac.discovery.local_repair import ExtremeGapSwap, modified_defect, repair_modified_defects
    from ac.discovery.proof_extraction import defect_admissibility

    seen = 0
    for n in range(6, 10):
        for x in modified_via_hat(n):
            if contains_repeated_sandwich(x, 1, 2):
                continue
            y = ExtremeGapSwap(2, 1).apply(x).output
            if modified_defect(y).empty:
                continue
            tr = repair_modified_defects(y)
            for state in tr.states[:-1]:
                assert defect_admissibility(state).ok
                seen += 1
    assert seen > 0


def test_target_avoidance_is_not_a_generic_consequence_of_admissibility():
    # E11b guardrail: left orientation + defect admissibility alone is not
    # sufficient for the canonical rotation to preserve 2212 avoidance.
    # Therefore E11c must use provenance inherited from the gap-swap image.
    from ac.discovery.local_repair import canonical_defect_rotation, rotate_interval
    from ac.discovery.proof_extraction import left_oriented, defect_admissibility

    x = ChainWord((1, 3, 2, 4, 3, 3, 1, 2))
    assert left_oriented(x)
    assert defect_admissibility(x).ok
    rule = canonical_defect_rotation(x)
    assert rule is not None
    y = rotate_interval(x, rule.start, rule.end, -rule.left_amount).output
    assert not left_oriented(y)


def test_reachable_repairs_have_no_heavy_crossing_training_range():
    from ac.discovery.local_repair import ExtremeGapSwap, repair_modified_defects
    from ac.discovery.proof_extraction import (
        repair_heavy_crossing_values, repair_preserves_orientation_profile,
    )

    seen = 0
    for n in range(6, 10):
        for x in modified_via_hat(n):
            if contains_repeated_sandwich(x, 1, 2):
                continue
            y = ExtremeGapSwap(2, 1).apply(x).output
            tr = repair_modified_defects(y)
            for state, rule in zip(tr.states, tr.rotations):
                assert repair_heavy_crossing_values(state, rule) == ()
                assert repair_preserves_orientation_profile(state, rule)
                seen += 1
    assert seen > 0


def test_no_heavy_crossing_is_not_itself_an_invariant_of_arbitrary_repairs():
    # A safe-looking admissible state can repair into the earlier generic
    # target-avoidance counterexample.  Thus E11c still needs gap-swap provenance.
    from ac.discovery.local_repair import canonical_defect_rotation, rotate_interval
    from ac.discovery.proof_extraction import repair_heavy_crossing_values

    x = ChainWord((1, 4, 3, 2, 3, 3, 1, 2))
    r1 = canonical_defect_rotation(x)
    assert r1 is not None
    assert repair_heavy_crossing_values(x, r1) == ()
    y = rotate_interval(x, r1.start, r1.end, -r1.left_amount).output
    r2 = canonical_defect_rotation(y)
    assert r2 is not None
    assert repair_heavy_crossing_values(y, r2) == (3,)
