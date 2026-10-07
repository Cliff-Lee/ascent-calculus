from ac import ChainWord


def test_133122_core_data():
    x = ChainWord.of([1, 3, 3, 1, 2, 2])
    assert x.first_positions == frozenset({1, 2, 5})
    assert x.last_positions == frozenset({3, 4, 6})
    assert x.raw_ascent_bottoms == frozenset({1, 4})
    assert x.raw_ascent_tops == frozenset({2, 5})
    assert x.ascent_bottoms == frozenset({1, 4})
    assert x.ascent_tops == frozenset({1, 2, 5})
    assert x.run_starts == frozenset({1, 3, 4, 6})
    assert x.run_ends == frozenset({2, 3, 5, 6})
    assert x.multiplicity_vector == (2, 2, 2)
    assert x.integer_partition == (2, 2, 2)
    assert x.avoids_constant_pattern(3)


def test_empty_levels_are_retained():
    x = ChainWord.of([1, 2, 1, 2, 4], height=4)
    assert x.fibres == ((1, 3), (2, 4), (), (5,))
    assert x.multiplicity_vector == (2, 2, 0, 1)
    assert x.composition == (2, 2, 1)
    assert x.integer_partition == (2, 2, 1)
    assert not x.is_cayley
