from ac import (
    Avoid,
    BlockSchemaT,
    ChainWord,
    Modified,
    Revised,
    enumerate_block_schemas,
    evaluate_bijection_candidate,
)
from ac.generate.universes import modified_via_hat, revised_sequences


def test_block_schema_grammar_is_finite_and_shift_aware():
    assert len(enumerate_block_schemas(0)) == 108
    assert len(enumerate_block_schemas(1)) == 108
    assert len(enumerate_block_schemas(2)) == 108
    assert enumerate_block_schemas(3) == ()


def test_generated_paper_recipe_is_found_and_passes_a_finite_check():
    recipe = BlockSchemaT(
        "increasing_runs",
        "first_prior_block",
        "safe_up",
        "reverse_complement",
        "max_pair_around_first",
    )
    assert recipe in enumerate_block_schemas(2)
    assert recipe.apply(ChainWord.of((1, 2, 2, 1))).output.values == (3, 1, 2, 3, 2, 1)
    assert recipe.apply(ChainWord.of((1, 3, 3, 1, 2, 2))).output.values == (4, 1, 3, 4, 2, 3, 2, 1)

    report = evaluate_bijection_candidate(
        recipe,
        Modified() & Avoid("111"),
        Revised() & Avoid("111"),
        universe=modified_via_hat,
        target_universe=revised_sequences,
        degree_shift=2,
        through=4,
    )
    assert report.exact
    assert report.verified_through == 4


def test_generated_extension_records_accurate_value_map():
    word = ChainWord.of((1, 2, 1))
    identity = BlockSchemaT("increasing_runs", "none", "stable", "identity", "max_pair_around_first")
    reverse_complement = BlockSchemaT("increasing_runs", "none", "stable", "reverse_complement", "max_pair_around_first")

    assert identity.apply(word).value_map == (1, 2)
    assert reverse_complement.apply(word).value_map == (2, 1)

    single_max = BlockSchemaT("increasing_runs", "none", "stable", "identity", "max_before_first")
    assert single_max.signature.delta_length == 1
    assert single_max.apply(word).output.values[0] == word.height + 1
    assert single_max.apply(word).created_positions == (1,)
