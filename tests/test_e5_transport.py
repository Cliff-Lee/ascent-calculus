from ac import (
    ChainWord,
    R,
    C,
    L,
    First,
    Last,
    AscTop,
    AscBottom,
    RawDescTop,
    ScopeLast,
    Cayley,
    Modified,
    Avoid,
    SameSet,
    transport_selector,
    transport_predicate,
    pushforward,
    check_transport_law,
    transport_restriction_through_lift,
    lift_fibre_profile,
    LiftCapacity,
    AvoidConstant,
    pullback,
    verify_on,
    VerificationStatus,
    check_lift_restriction_law,
    check_capacity_shift_law,
    compare_classes,
)
from ac.generate.universes import cayley_words, chain_words, modified_via_hat


def test_symbolic_selector_transport_exposes_reversed_modified_boundary_law():
    target = transport_selector(AscTop(), R())
    assert target == (ScopeLast() | RawDescTop())
    assert check_transport_law(R(), AscTop(), target, universe=cayley_words, through=6) is None


def test_modified_pushforward_under_reverse_simplifies_to_last_equals_right_desc_top():
    transported = transport_predicate(Modified(), R())
    expected = Cayley() & SameSet(Last(), ScopeLast() | RawDescTop())
    for n in range(1, 7):
        for x in cayley_words(n):
            assert transported.holds(x) == expected.holds(x)


def test_transport_predicate_handles_pattern_and_structure_together():
    source = Modified() & Avoid("2122")
    symbolic = transport_predicate(source, R())
    semantic = pushforward(R(), source)
    for n in range(1, 7):
        for x in cayley_words(n):
            assert symbolic.holds(x) == semantic.holds(x)
    # The pattern component has become 2212, while the structural component is
    # the reversed modified theory rather than Modified itself.
    expected = Cayley() & SameSet(Last(), ScopeLast() | RawDescTop()) & Avoid("2212")
    for n in range(1, 7):
        for x in cayley_words(n):
            assert symbolic.holds(x) == expected.holds(x)


def test_complement_transports_modified_ascent_top_to_descent_bottom_theory():
    transported = transport_predicate(Modified(), C())
    semantic = pushforward(C(), Modified())
    for n in range(1, 7):
        for x in cayley_words(n):
            assert transported.holds(x) == semantic.holds(x)


def test_ambient_restriction_transport_through_single_lift_exact_example():
    x = ChainWord.of([1, 3, 3, 1, 2, 2], height=4)
    tr = transport_restriction_through_lift(x, 5, [1, 2, 4, 6])
    assert tr.threshold == 2
    assert tr.selected_prefix_count == 3
    assert tr.exact
    assert tr.predicted_restriction.values == tr.actual_restriction.values
    assert tr.predicted_restriction.height == tr.actual_restriction.height


def test_ambient_restriction_transport_law_exhaustive_small_words():
    assert check_lift_restriction_law(
        universe=chain_words, through=4, height=3
    ) is None


def test_lift_fibre_profile_predicts_exact_multiplicities():
    x = ChainWord.of([1, 3, 3, 1, 2, 2], height=3)
    prof = lift_fibre_profile(x, 5)
    out = L(5).apply(x).output
    assert prof.threshold == 2
    assert prof.predicted_multiplicity_vector == out.multiplicity_vector


def test_capacity_shift_theorem_schema_exhaustive_for_several_r():
    for r in (2, 3, 4):
        assert check_capacity_shift_law(
            r, universe=chain_words, through=5, height=3
        ) is None


def test_capacity_shift_is_a_first_class_property_transport_law():
    # Under the source hypothesis Av(1^r), the capacity predicate is exactly
    # the pullback of Av(1^r) through the lift.
    r = 3
    pivot = 3
    cap = LiftCapacity(pivot, r)
    after = pullback(L(pivot), AvoidConstant(r))
    iff = cap.implies(after) & after.implies(cap)
    result = verify_on(
        iff,
        universe=lambda n: chain_words(n, 3),
        through=5,
        start=pivot,
        hypothesis=AvoidConstant(r),
    )
    assert result.status is VerificationStatus.VERIFIED


def test_refined_class_comparison_separates_equal_counts_from_equal_classes():
    comp = compare_classes(
        Avoid("2122"),
        Avoid("2212"),
        universe=modified_via_hat,
        through=7,
        statistics=("height", "ascents", "multiplicity_partition", "first_positions"),
    )
    assert comp.counts_equal
    assert comp.first_class_difference() is not None
    assert comp.first_class_difference().n == 6
    assert comp.first_profile_mismatch("height") is None
    assert comp.first_profile_mismatch("ascents") is None
    assert comp.first_profile_mismatch("multiplicity_partition") is None
    assert comp.first_profile_mismatch("first_positions") is not None
