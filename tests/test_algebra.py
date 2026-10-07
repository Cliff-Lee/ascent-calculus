from ac import (
    ChainWord,
    R,
    C,
    L,
    Identity,
    Compose,
    First,
    Last,
    transformation_counterexample,
    check_transport_law,
)
from ac.generate.universes import cayley_words


def test_klein_four_normal_forms():
    assert isinstance((R() >> R()).normal_form(), Identity)
    assert isinstance((C() >> C()).normal_form(), Identity)
    assert (R() >> C()).normal_form() == (C() >> R()).normal_form()
    assert isinstance((R() >> C() >> R() >> C()).normal_form(), Identity)


def test_klein_four_relations_executable():
    assert transformation_counterexample(R() >> R(), Identity(), universe=cayley_words, through=5) is None
    assert transformation_counterexample(C() >> C(), Identity(), universe=cayley_words, through=5) is None
    assert transformation_counterexample(R() >> C(), C() >> R(), universe=cayley_words, through=5) is None


def test_composition_tracks_original_occurrence_ids():
    x = ChainWord.of([1, 3, 3, 1, 2, 2])
    result = (R() >> C()).apply(x)
    assert set(result.output.position_ids) == set(x.position_ids)
    assert tuple(result.output.position_of_id(pid) for pid in x.position_ids) == result.position_map


def test_transport_is_distinct_from_recompute_and_encodes_reverse_first_last():
    # Reversal transports old Last occurrences exactly onto new First occurrences.
    assert check_transport_law(
        R(), Last(), First(), universe=cayley_words, through=6
    ) is None


def test_complement_transports_first_to_first():
    assert check_transport_law(
        C(), First(), First(), universe=cayley_words, through=6
    ) is None


def test_lift_symbolic_transform_executes():
    x = ChainWord.of([1, 1, 3])
    assert L(2).apply(x).output.values == (2, 1, 3)
