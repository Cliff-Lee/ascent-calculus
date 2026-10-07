from ac import (
    ChainWord,
    Pattern,
    Avoid,
    AvoidConstant,
    Modified,
    restriction_view,
    restrict_positions,
    compress_levels,
    standardize,
    R,
    C,
    verify_on,
    VerificationStatus,
)
from ac.generate.universes import cayley_words


def test_ambient_restriction_retains_gap_information_before_compression():
    a = ChainWord.of([1, 1, 3], height=3)
    b = ChainWord.of([2, 1, 3], height=3)
    va = restriction_view(a, [1, 3])
    vb = restriction_view(b, [1, 3])
    assert va.ambient.values == (1, 3)
    assert vb.ambient.values == (2, 3)
    assert va.compressed.values == (1, 2)
    assert vb.compressed.values == (1, 2)
    assert va.gap_signature != vb.gap_signature


def test_restriction_preserves_occurrence_ids_and_marks_deleted_positions():
    x = ChainWord.of([1, 3, 3, 1, 2, 2])
    result = restrict_positions(x, [1, 3, 6])
    assert result.output.values == (1, 3, 2)
    assert result.output.position_ids == (x.position_id(1), x.position_id(3), x.position_id(6))
    assert result.position_map == (1, None, 2, None, None, 3)


def test_compress_levels_and_standardize_are_distinct_operations():
    x = ChainWord.of([1, 3, 3, 1, 2, 2], height=4)
    assert compress_levels(x).output.values == (1, 3, 3, 1, 2, 2)
    assert compress_levels(x).output.height == 3
    # Equal letters are resolved left-to-right under Stanley standardization.
    assert standardize(x).output.values == (1, 5, 6, 2, 3, 4)
    assert standardize(x).output.height == 6


def test_2122_compiles_to_exact_classical_pattern_semantics():
    p = Pattern("2122")
    compiled = p.compile()
    x = ChainWord.of([2, 1, 2, 2])
    y = ChainWord.of([2, 1, 2, 3])
    assert compiled.contains(x)
    assert not compiled.contains(y)
    occ = compiled.occurrences(x)
    assert len(occ) == 1
    assert occ[0].positions == (1, 2, 3, 4)
    assert occ[0].restriction.compressed.values == (2, 1, 2, 2)


def test_pattern_avoidance_111_agrees_with_constant_multiplicity_predicate():
    law = Avoid("111").implies(AvoidConstant(3)) & AvoidConstant(3).implies(Avoid("111"))
    result = verify_on(law, universe=cayley_words, through=6)
    assert result.status is VerificationStatus.VERIFIED


def test_modified_111_class_can_now_be_written_with_general_pattern_predicate():
    # Calibration of the general pattern compiler against the old optimized predicate.
    general = Modified() & Avoid("111")
    optimized = Modified() & AvoidConstant(3)
    for n in range(1, 7):
        a = [x.values for x in cayley_words(n) if general.holds(x)]
        b = [x.values for x in cayley_words(n) if optimized.holds(x)]
        assert a == b


def test_reverse_and_complement_transport_classical_patterns():
    p = Pattern("2122")
    rp = p.reverse()
    cp = p.complement()
    assert rp.values == (2, 2, 1, 2)  # 2212
    assert cp.values == (1, 2, 1, 1)  # 1211

    for n in range(4, 7):
        for x in cayley_words(n):
            rx = R().apply(x).output
            cx = C().apply(x).output
            assert p.compile().contains(x) == rp.compile().contains(rx)
            assert p.compile().contains(x) == cp.compile().contains(cx)


def test_general_constraint_pattern_supports_vincular_and_value_adjacency_atoms():
    from ac import ConstraintPattern, AllOf, ValueLt, PositionAdjacent, ValueAdjacent

    # Two selected entries must be adjacent positions, increasing, and occupy
    # consecutive value levels.  This is a tiny bivincular-style calibration.
    q = ConstraintPattern(
        2,
        AllOf((ValueLt(1, 2), PositionAdjacent(1, 2), ValueAdjacent(1, 2))),
        name="adjacent-consecutive-ascent",
    )
    assert q.contains(ChainWord.of([1, 2, 4], height=4))
    assert not q.contains(ChainWord.of([1, 3, 5], height=5))


def test_compiled_classical_pattern_agrees_with_restriction_compression_exhaustively():
    from itertools import combinations

    for spec in ("11", "12", "21", "111", "121", "212", "123", "2122", "2212"):
        p = Pattern(spec)
        c = p.compile()
        for n in range(p.arity, 6):
            for x in cayley_words(n):
                direct = False
                for pos in combinations(range(1, n + 1), p.arity):
                    if restriction_view(x, pos).compressed.values == p.values:
                        direct = True
                        break
                assert c.contains(x) == direct


def test_symbolic_pattern_transport_through_klein_four_symmetries():
    from ac import transport_classical_pattern

    p = Pattern("2122")
    assert transport_classical_pattern(p, R()).values == (2, 2, 1, 2)
    assert transport_classical_pattern(p, C()).values == (1, 2, 1, 1)
    assert transport_classical_pattern(p, R() >> C()).values == (1, 1, 2, 1)


def test_lift_refuses_false_compressed_pattern_transport_claim():
    from ac import L, transport_classical_pattern
    import pytest

    with pytest.raises(TypeError):
        transport_classical_pattern(Pattern("12"), L(2))


def test_conversion_based_modified_generator_matches_bruteforce_through_6():
    from ac.generate.universes import modified_sequences, modified_via_hat

    for n in range(1, 7):
        brute = [x.values for x in modified_sequences(n)]
        via_hat = [x.values for x in modified_via_hat(n)]
        assert sorted(brute) == sorted(via_hat)
