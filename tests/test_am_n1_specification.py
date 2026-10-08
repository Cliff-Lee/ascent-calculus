import itertools

import pytest

from ac.core.word import ChainWord
from ac.discovery.specification import (
    ClassSpec,
    DegreeWindow,
    PatternRuleSpec,
    SearchSpec,
)
from ac.discovery.statistics import STATISTICS, statistic_value
from ac.generate.universes import ascent_sequences, modified_sequences, modified_via_hat, revised_sequences
from ac.patterns.classical import ClassicalPattern
from experiments.reference_ascent import (
    all_tuples,
    contains_pattern,
    modified as reference_modified,
    ordinary as reference_ordinary,
    revised as reference_revised,
)


def test_production_generators_agree_with_literal_definitions_through_degree_five():
    for degree in range(1, 6):
        assert {word.values for word in ascent_sequences(degree)} == reference_ordinary(degree)
        expected_modified = reference_modified(degree)
        assert {word.values for word in modified_sequences(degree)} == expected_modified
        assert {word.values for word in modified_via_hat(degree)} == expected_modified
        assert {word.values for word in revised_sequences(degree)} == reference_revised(degree)


def test_class_specification_predicates_match_independent_pattern_and_class_definitions():
    specifications = (
        ClassSpec.build("ordinary", [{"mode": "avoid", "pattern": "212"}]),
        ClassSpec.build("modified", [{"mode": "contain", "pattern": "121"}]),
        ClassSpec.build("revised", [
            {"mode": "avoid", "pattern": "11"},
            {"mode": "contain", "pattern": "12"},
        ]),
    )
    for degree in range(1, 5):
        for values in all_tuples(degree):
            word = ChainWord(values)
            for spec in specifications:
                if spec.family == "ordinary":
                    family_holds = values in reference_ordinary(degree)
                elif spec.family == "modified":
                    family_holds = values in reference_modified(degree)
                else:
                    family_holds = values in reference_revised(degree)
                rules_hold = all(
                    contains_pattern(values, rule.pattern) == (rule.mode == "contain")
                    for rule in spec.rules
                )
                assert spec.predicate().holds(word) == (family_holds and rules_hold)


def test_search_spec_round_trip_offsets_and_canonical_fingerprint():
    left = ClassSpec.build("modified", [
        {"mode": "avoid", "pattern": "2122"},
        {"mode": "avoid", "pattern": "111"},
    ])
    same_left_different_input_order = ClassSpec.build("modified", [
        {"mode": "avoid", "pattern": "111"},
        {"mode": "avoid", "pattern": "2122"},
        {"mode": "avoid", "pattern": "111"},
    ])
    target = ClassSpec.build("revised", [{"mode": "avoid", "pattern": "111"}])
    spec = SearchSpec(
        "bijection_search", left, DegreeWindow(1, 5), target,
        source_offset=1, target_offset=3,
    )
    equivalent_input = SearchSpec(
        "bijection_search", same_left_different_input_order, DegreeWindow(1, 5), target,
        source_offset=1, target_offset=3,
    )
    assert spec.degree_shift == 2
    assert spec.degrees_for(4) == (5, 7)
    assert spec.fingerprint == equivalent_input.fingerprint
    assert SearchSpec.from_json(spec.canonical_json()) == spec
    assert "degree n+1" in spec.describe()
    assert "degree n+3" in spec.describe()


@pytest.mark.parametrize("value", [True, 1.0, "2"])
def test_degree_windows_reject_non_integer_values(value):
    with pytest.raises(ValueError):
        DegreeWindow(value, 3)


def test_search_spec_rejects_invalid_goals_offsets_and_statistics():
    ordinary = ClassSpec("ordinary")
    revised = ClassSpec("revised")
    with pytest.raises(ValueError, match="requires a target"):
        SearchSpec("count_equivalence", ordinary, DegreeWindow(1, 3))
    with pytest.raises(ValueError, match="less than 1"):
        SearchSpec("count_equivalence", ordinary, DegreeWindow(1, 3), revised, source_offset=-1)
    with pytest.raises(ValueError, match="non-count statistic"):
        SearchSpec("profile_equivalence", ordinary, DegreeWindow(1, 3), revised)
    with pytest.raises(ValueError, match="supported non-count statistic"):
        SearchSpec("profile_equivalence", ordinary, DegreeWindow(1, 3), revised, statistic="none")
    with pytest.raises(ValueError, match="supported AC statistic"):
        SearchSpec("count_equivalence", ordinary, DegreeWindow(1, 3), revised, statistic="typo")


def test_pattern_rule_rejects_bool_and_non_canonical_patterns():
    with pytest.raises(ValueError):
        PatternRuleSpec("avoid", (True,))
    with pytest.raises(ValueError):
        PatternRuleSpec("avoid", (1, 3))


def test_spec_json_rejects_unknown_version_and_extra_fields():
    spec = SearchSpec("enumerate", ClassSpec("ordinary"), DegreeWindow(1, 2))
    value = spec.to_dict()
    value["version"] = 999
    with pytest.raises(ValueError, match="unsupported"):
        SearchSpec.from_dict(value)
    value = spec.to_dict()
    value["unrecognized"] = True
    with pytest.raises(ValueError, match="version-1 schema"):
        SearchSpec.from_dict(value)


def test_statistic_registry_preserves_gui_identifiers_and_values():
    assert "Number of distinct values" == STATISTICS["distinct_values"]
    for degree in range(1, 5):
        for values in itertools.product(range(1, degree + 1), repeat=degree):
            word = ChainWord(values)
            assert statistic_value(word, "ascents") == sum(a < b for a, b in zip(values, values[1:]))
            assert statistic_value(word, "maximum") == max(values)
            assert statistic_value(word, "distinct_values") == len(set(values))
            assert statistic_value(word, "first_occurrence_positions") == tuple(
                i for i, value in enumerate(values, 1) if value not in values[: i - 1]
            )
    with pytest.raises(ValueError, match="unknown statistic"):
        statistic_value(ChainWord((1,)), "not-a-statistic")

