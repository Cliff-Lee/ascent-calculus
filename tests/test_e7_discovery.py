from ac import (
    Avoid,
    AvoidConstant,
    AscTop,
    ChainWord,
    First,
    HypothesisCandidate,
    Modified,
    Occ,
    Positions,
    Repeat,
    RunStart,
    SameSet,
    SpanRelation,
    contains_repeated_sandwich,
    discover_monotone_threshold,
    fibre_span_relation,
    generate_selector_expressions,
    mine_minimal_hypotheses,
    mine_selector_expression_laws,
    rank_discriminating_statistics,
    repeated_sandwich_pattern,
    verify_parameterized_schema,
)
from ac.generate.universes import cayley_words, modified_via_hat


def _occ_union(r: int):
    out = Positions([])
    for k in range(2, r):
        out = out | Occ(k)
    return out


def test_repeated_sandwich_gap_theorem_matches_classical_patterns_small_cayley_words():
    for a, b in ((1, 1), (1, 2), (2, 1), (2, 2)):
        pattern = repeated_sandwich_pattern(a, b)
        for n in range(1, 7):
            for x in cayley_words(n):
                assert contains_repeated_sandwich(x, a, b) == (not Avoid(pattern).holds(x))


def test_2122_and_2212_are_the_first_and_second_relevant_lower_gap_sides_for_triples():
    # 121322 has a triple 2-fibre at positions 2,5,6 and a lower 1 in
    # the first relevant gap, hence 2122 but not 2212.
    x = ChainWord.of([1, 2, 1, 3, 2, 2])
    assert contains_repeated_sandwich(x, 1, 2)
    assert not contains_repeated_sandwich(x, 2, 1)


def test_fibre_span_geometry_distinguishes_crossing_and_nesting():
    crossing = ChainWord.of([1, 2, 1, 2])
    nesting = ChainWord.of([1, 2, 2, 1])
    assert fibre_span_relation(crossing, 1, 2) is SpanRelation.CROSS_UV
    assert fibre_span_relation(nesting, 1, 2) is SpanRelation.U_CONTAINS_V


def test_minimal_hypothesis_miner_finds_111_avoidance_as_weakest_supplied_repair():
    law = SameSet(Occ(2), Repeat())
    results = mine_minimal_hypotheses(
        law,
        base=Modified(),
        candidates=(
            HypothesisCandidate("avoid-11", AvoidConstant(2)),
            HypothesisCandidate("avoid-111", AvoidConstant(3)),
            HypothesisCandidate("avoid-1111", AvoidConstant(4)),
        ),
        universe=cayley_words,
        through=6,
        max_terms=1,
    )
    assert any(r.names == ("avoid-111",) for r in results)
    best = results[0]
    # Both avoid-11 and avoid-111 make the law true, but avoid-111 is the
    # empirically weaker hypothesis because it admits more modified words.
    assert best.names == ("avoid-111",)


def test_parameterized_modified_runstart_occurrence_schema_for_1r_avoidance():
    report = verify_parameterized_schema(
        "modified-1r-runstart-occurrence-union",
        range(2, 6),
        law_factory=lambda r: SameSet(RunStart() - Positions([1]), _occ_union(r)),
        hypothesis_factory=lambda r: Modified() & AvoidConstant(r),
        universe=cayley_words,
        through=6,
    )
    assert report.verified


def test_threshold_discovery_locates_occ2_repeat_break_at_r3():
    result = discover_monotone_threshold(
        range(2, 6),
        law_factory=lambda r: SameSet(Occ(2), Repeat()),
        hypothesis_factory=lambda r: Modified() & AvoidConstant(r),
        universe=cayley_words,
        through=6,
    )
    assert result.working_parameters == (2, 3)
    assert result.failing_parameters == (4, 5)
    assert result.boundary == 3


def test_selector_expression_miner_can_synthesize_modified_runstart_law():
    expressions = generate_selector_expressions(
        (Repeat(), RunStart(), Positions([1])),
        max_cost=3,
        operations=("difference",),
    )
    assert RunStart() - Positions([1]) in expressions

    laws = mine_selector_expression_laws(
        (Repeat(), RunStart(), Positions([1])),
        universe=cayley_words,
        through=6,
        hypothesis=Modified(),
        max_cost=3,
        expression_operations=("difference",),
        relations=("eq",),
    )
    # The public miner's relations argument remains mathematical relation types;
    # expression generation itself uses its default union/intersection/difference.
    assert any(
        law.relation == "eq"
        and {law.left, law.right} == {Repeat(), RunStart() - Positions([1])}
        for law in laws
    )


def test_discriminating_statistic_ranker_finds_where_2122_2212_profiles_diverge():
    left = Modified() & Avoid("2122")
    right = Modified() & Avoid("2212")
    rows = rank_discriminating_statistics(
        left,
        right,
        universe=modified_via_hat,
        through=6,
        statistics=("height", "first_positions", "last_positions", "lower_gap_profile"),
    )
    by_name = {r.name: r for r in rows}
    assert not by_name["height"].discriminates
    assert by_name["first_positions"].first_mismatch_n == 6
    assert by_name["last_positions"].first_mismatch_n == 6
    assert by_name["lower_gap_profile"].first_mismatch_n == 6


def test_lower_gap_profile_reflects_exactly_under_reversal():
    from ac import lower_gap_profile, reflect_gap_profile, reverse

    for n in range(1, 7):
        for x in cayley_words(n):
            assert lower_gap_profile(reverse(x).output) == reflect_gap_profile(lower_gap_profile(x))


def test_semantic_selector_classes_compactly_recover_modified_normal_forms():
    from ac import mine_selector_equivalence_classes

    expressions = generate_selector_expressions(
        (First(), AscTop(), Repeat(), RunStart(), Positions([1])),
        max_cost=3,
        operations=("difference",),
    )
    classes = mine_selector_equivalence_classes(
        expressions,
        universe=cayley_words,
        through=6,
        hypothesis=Modified(),
    )
    repeat_class = next(c for c in classes if c.representative == Repeat())
    assert RunStart() - Positions([1]) in repeat_class.aliases
    first_class = next(c for c in classes if c.representative in {First(), AscTop()})
    assert {First(), AscTop()} <= {first_class.representative, *first_class.aliases}
