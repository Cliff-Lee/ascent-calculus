from collections import Counter

from ac import (
    Avoid,
    ChainWord,
    Modified,
    Modified111BlockBijection,
    Revised,
    analyze_finite_map,
    evaluate_bijection_candidate,
    synthesize_bijections,
)
from ac.generate.universes import modified_via_hat, revised_sequences


def test_paper_block_bijection_matches_published_examples_and_inverse():
    transform = Modified111BlockBijection()
    examples = {
        (1, 2, 2, 1): (3, 1, 2, 3, 2, 1),
        (1, 3, 3, 1, 2, 2): (4, 1, 3, 4, 2, 3, 2, 1),
    }
    for source, expected in examples.items():
        word = ChainWord.of(source)
        result = transform.apply(word)
        assert result.output.values == expected
        assert len(result.output) == len(word) + 2
        assert transform.inverse().apply(result.output).output.values == source
        assert len(result.created_positions) == 2


def test_paper_map_is_a_shift_two_bijection_through_degree_five():
    source = Modified() & Avoid("111")
    target = Revised() & Avoid("111")
    transform = Modified111BlockBijection()
    report = evaluate_bijection_candidate(
        transform,
        source,
        target,
        universe=modified_via_hat,
        target_universe=revised_sequences,
        degree_shift=2,
        through=5,
    )
    assert report.exact
    assert report.verified_through == 5

    for degree in range(1, 6):
        finite = analyze_finite_map(
            transform,
            source,
            target,
            universe=modified_via_hat,
            target_universe=revised_sequences,
            degree_shift=2,
            n=degree,
        )
        assert finite.bijective

    for word in modified_via_hat(5):
        if source.holds(word):
            image = transform.apply(word).output
            assert image.multiplicity_vector == tuple(reversed(word.multiplicity_vector)) + (2,)


def test_shift_aware_synthesis_can_find_the_paper_recipe():
    source = Modified() & Avoid("111")
    target = Revised() & Avoid("111")
    recipe = Modified111BlockBijection()
    report = synthesize_bijections(
        source,
        target,
        universe=modified_via_hat,
        target_universe=revised_sequences,
        degree_shift=2,
        atoms=(recipe,),
        max_cost=4,
        through=5,
        keep=5,
    )
    assert report.exact
    assert any(type(candidate.transform).__name__ == "Modified111ToRevised111" for candidate in report.exact)


def test_block_tree_domain_rejects_triple_occurrences():
    transform = Modified111BlockBijection()
    try:
        transform.apply(ChainWord.of((1, 2, 2, 2, 1)))
    except ValueError as exc:
        assert "111-avoiders" in str(exc) or "at most twice" in str(exc)
    else:
        raise AssertionError("the 111 block map must reject a triple occurrence")
