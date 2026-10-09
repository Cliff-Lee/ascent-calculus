from ac.algebra.block_schemas import (
    BLOCK_MAPS,
    BLOCK_ORDERS,
    BLOCK_EXTENSIONS,
    PARENT_RULES,
    SEGMENTATIONS,
    BlockSchemaT,
    enumerate_block_schemas,
    generate_block_schemas,
)
from ac.core.word import ChainWord
from ac.discovery.specification import ClassSpec, DegreeWindow
from ac.discovery.transformation_search import (
    GRAMMAR_VERSION,
    PREVIOUS_GRAMMAR_VERSION,
    TransformationGrammarSpec,
    TransformationSearchSpec,
    generate_transformation_atoms,
)
from ac.discovery.transformation_search import run_transformation_search


def test_expanded_block_grammar_is_systematic_and_preserves_legacy_recipe_space():
    # The original published-paper recipe catalogue remains stable for earlier
    # experiments, while the generated N6 grammar adds definition-based axes.
    assert len(enumerate_block_schemas(0)) == 108
    assert len(enumerate_block_schemas(1)) == 108
    assert len(enumerate_block_schemas(2)) == 108
    assert len(enumerate_block_schemas(3)) == 0
    assert "role_runs" in SEGMENTATIONS
    assert "newness_runs" in SEGMENTATIONS
    assert "all_prior_blocks" in PARENT_RULES
    assert "ascent_count_up" in BLOCK_ORDERS
    assert "rotate_left" in BLOCK_MAPS
    assert "max_before_each_block" in BLOCK_EXTENSIONS

    generated = generate_block_schemas(2)
    assert len(generated) == 7_360
    assert len(set(generated)) == len(generated)
    assert all(schema.extension in {
        "max_pair_around_first", "max_before_each_block", "max_after_each_block", "max_between_blocks",
    } for schema in generated)


def test_new_maximum_block_extension_and_trace_keep_original_occurrence_ids():
    word = ChainWord.of((1, 2, 1))
    schema = BlockSchemaT(
        "equal_value_runs", "none", "stable", "identity", "max_before_each_block",
    )
    result = schema.apply(word)
    assert result.output.values == (3, 1, 3, 2, 3, 1)
    assert result.output.height == 3
    assert result.position_map == (2, 4, 6)
    assert result.created_positions == (1, 3, 5)
    assert result.output.position_ids == (-1, 1, -2, 2, -3, 3)

    trace = schema.trace(word)
    assert [block["values"] for block in trace["blocks"]] == [[1], [2], [1]]
    assert trace["blocks"][0]["roles"][0] == {
        "position": 1, "new": True, "asctop": True, "ascbot": True,
    }
    assert trace["output_values"] == list(result.output.values)


def test_all_prior_block_dependencies_and_local_rotation_are_visible():
    word = ChainWord.of((1, 2, 1, 2, 1))
    schema = BlockSchemaT("equal_value_runs", "all_prior_blocks", "safe_up", "rotate_left")
    trace = schema.trace(word)
    assert trace["blocks"][4]["depends_on"] == [1, 3]
    assert sorted(pid for row in trace["output_positions_by_block"] for pid in row) == [1, 2, 3, 4, 5]

    rotated = BlockSchemaT("increasing_runs", "none", "stable", "rotate_left")
    source = ChainWord.of((1, 3, 4))
    transformed = rotated.apply(source)
    assert transformed.output.values == (3, 4, 1)
    assert transformed.position_map == (3, 1, 2)


def test_block_only_search_reconstructs_the_seeded_modified_to_revised_map():
    """This is a reconstruction benchmark, not a blind rediscovery claim."""
    grammar = TransformationGrammarSpec(
        operations=("block_schemas",),
        selectors=(),
        boolean_selector_algebra=False,
        max_selectors=10,
        max_atoms=10_000,
        max_cost=3,
        max_steps=1,
        candidate_budget=10_000,
        expansion_budget=10_000,
        evaluation_budget=1_000_000,
    )
    assert len(generate_transformation_atoms(grammar, expected_length_shift=2)) == 7_360
    source = ClassSpec.build("modified", [{"mode": "avoid", "pattern": "111"}])
    target = ClassSpec.build("revised", [{"mode": "avoid", "pattern": "111"}])
    spec = TransformationSearchSpec(
        source, target, DegreeWindow(1, 4), grammar, source_offset=0, target_offset=2,
    )
    assert spec.grammar_version == GRAMMAR_VERSION

    job = type("Job", (), {"question": spec, "checkpoint": {}})()

    class Context:
        def checkpoint(self, state, progress):
            pass

        def check_control(self):
            pass

    result = run_transformation_search(job, Context())
    known_recipe = BlockSchemaT(
        "increasing_runs", "first_prior_block", "safe_up", "reverse_complement",
        "max_pair_around_first",
    )
    found = {row["program"] for row in result["exact_candidates"]}
    assert repr(known_recipe) in found
    explanation = next(
        row for row in result["exact_candidates"]
        if row["program"] == repr(known_recipe)
    )
    assert explanation["block_schema"] == {
        "segmentation": "increasing_runs",
        "parent_rule": "first_prior_block",
        "block_order": "safe_up",
        "block_map": "reverse_complement",
        "extension": "max_pair_around_first",
    }
    assert explanation["example_trace"]["blocks"]
    assert explanation["example_trace"]["output_values"]
    assert result["exact_candidate_count"] >= 1
    assert result["candidate_space_exhausted"] is True
    assert result["candidates_tested"] == 7_360
    assert result["degree_shift"] == 2
    assert result["exact_candidates"][0]["proof_status"] == "not_proved"


def test_n5_search_specs_remain_readable_after_the_n6_grammar_version_bump():
    old_grammar = TransformationGrammarSpec(
        operations=("symmetry",), selectors=(), boolean_selector_algebra=False,
        max_atoms=20, candidate_budget=20,
    )
    old_spec = TransformationSearchSpec(
        ClassSpec("ordinary"), ClassSpec("ordinary"), DegreeWindow(1, 2),
        old_grammar, grammar_version=PREVIOUS_GRAMMAR_VERSION,
    )
    assert TransformationSearchSpec.from_dict(old_spec.to_dict()) == old_spec
