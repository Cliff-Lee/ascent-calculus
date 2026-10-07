from ac import ChainWord, is_ascent_sequence, is_modified, is_revised
from ac.generate.universes import ascent_sequences, modified_sequences, revised_sequences


def test_133122_is_modified():
    x = ChainWord.of([1, 3, 3, 1, 2, 2])
    assert is_modified(x)


def test_ascent_sequence_counts_first_terms():
    expected = [1, 2, 5, 15, 53, 217]
    got = [sum(1 for _ in ascent_sequences(n)) for n in range(1, 7)]
    assert got == expected


def test_modified_counts_first_terms():
    expected = [1, 2, 5, 15, 53]
    got = [sum(1 for _ in modified_sequences(n)) for n in range(1, 6)]
    assert got == expected


def test_revised_shift_first_terms():
    # Revised sequences of length n+1 correspond to ascent sequences of length n.
    expected = [1, 2, 5, 15]
    got = [sum(1 for _ in revised_sequences(n + 1)) for n in range(1, 5)]
    assert got == expected


def test_positive_ascent_definition_examples():
    assert is_ascent_sequence(ChainWord.of([1]))
    assert is_ascent_sequence(ChainWord.of([1, 2, 1, 2, 4]))
    assert not is_ascent_sequence(ChainWord.of([2]))
