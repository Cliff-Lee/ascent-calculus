from ac import (
    Avoid,
    AscTop,
    CandidateEvaluation,
    First,
    Hat,
    HatInv,
    Modified,
    R,
    C,
    RunStart,
    SweepLift,
    evaluate_bijection_candidate,
    enumerate_transform_programs,
    diagnose_candidate,
    synthesize_bijections,
)
from ac.generate.universes import modified_via_hat


def test_hat_symbolic_transform_round_trips_on_modified_small():
    t = HatInv() >> Hat()
    ev = evaluate_bijection_candidate(
        t,
        Modified(),
        Modified(),
        universe=modified_via_hat,
        through=7,
    )
    assert ev.exact


def test_program_enumerator_normalizes_klein_four_duplicates():
    programs = enumerate_transform_programs((R(), C()), max_cost=3)
    reps = {repr(p.normal_form()) for p in programs}
    assert len(reps) == len(programs)
    # The subgroup contains only I,R,C,RC despite a larger raw word search.
    assert len(programs) == 4


def test_sweep_lift_is_available_as_generic_event_driven_transform():
    t = SweepLift(AscTop(), direction="ltr")
    # On modified words this need not be an automorphism, but it must be an
    # executable same-length AC transformation suitable for synthesis.
    diag = diagnose_candidate(
        t,
        Modified(),
        Modified(),
        universe=modified_via_hat,
        n=4,
    )
    assert diag.source_count == 15
    assert diag.defined_count == 15


def test_reverse_perfectly_repairs_pattern_side_but_not_modified_structure_at_n6():
    source = Modified() & Avoid("2122")
    target = Modified() & Avoid("2212")
    diag = diagnose_candidate(
        R(),
        source,
        target,
        universe=modified_via_hat,
        n=6,
        target_pattern=Avoid("2212"),
    )
    assert diag.source_count == 216
    assert diag.target_pattern_avoid_count == diag.defined_count
    assert diag.target_member_count < diag.source_count
    assert diag.modified_defect > 0


def test_bounded_synthesis_framework_can_rediscover_identity_on_same_class():
    cls = Modified() & Avoid("111")
    report = synthesize_bijections(
        cls,
        cls,
        universe=modified_via_hat,
        atoms=(R(), C()),
        max_cost=2,
        through=5,
        keep=10,
    )
    assert report.exact
    assert any(ev.cost == 0 for ev in report.exact)


def test_fibre_gap_pack_is_exact_through_n6_and_first_fails_by_collision_at_n7():
    from ac import FibreGapPack

    source = Modified() & Avoid("2122")
    target = Modified() & Avoid("2212")
    candidate = FibreGapPack(2, 1, side="right")
    ev = evaluate_bijection_candidate(
        candidate,
        source,
        target,
        universe=modified_via_hat,
        through=7,
    )
    assert ev.verified_through == 6
    assert ev.failure is not None
    assert ev.failure.kind.value == "collision"
    assert ev.failure.n == 7
    assert ev.failure.output is not None


def test_fibre_gap_pack_maps_the_unique_n6_difference_correctly():
    from ac import ChainWord, FibreGapPack

    source_only = ChainWord.of([1, 2, 2, 1, 3, 2])
    target_only = ChainWord.of([1, 2, 1, 3, 2, 2])
    assert FibreGapPack(2, 1, side="right").apply(source_only).output.values == target_only.values


def test_complete_finite_map_diagnostics_expose_capacity_shift_collision_and_missing_targets():
    from ac import FibreGapPack, analyze_finite_map

    source = Modified() & Avoid("2122")
    target = Modified() & Avoid("2212")
    report = analyze_finite_map(
        FibreGapPack(2, 1, side="right"),
        source,
        target,
        universe=modified_via_hat,
        n=7,
    )
    assert report.into_target
    assert not report.injective
    assert not report.surjective
    assert len(report.collisions) == 2
    assert len(report.missing_targets) == 2
