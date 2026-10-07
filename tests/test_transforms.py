from ac import ChainWord, reverse, complement, prefix_lift, inverse_prefix_lift, hat, inverse_hat, is_modified
from ac.generate.universes import ascent_sequences


def test_v4_relations():
    x = ChainWord.of([1, 3, 3, 1, 2, 2])
    assert reverse(reverse(x).output).output.values == x.values
    assert complement(complement(x).output).output.values == x.values
    rc = reverse(complement(x).output).output
    cr = complement(reverse(x).output).output
    assert rc.values == cr.values


def test_reverse_first_last_transport():
    x = ChainWord.of([1, 3, 3, 1, 2, 2])
    y = reverse(x).output
    n = len(x)
    rho_last = {n + 1 - i for i in x.last_positions}
    assert y.first_positions == rho_last


def test_prefix_lift_preserves_ascents_and_roundtrips_when_new():
    x = ChainWord.of([1, 1, 3])
    y = prefix_lift(x, 2).output
    assert y.values == (2, 1, 3)
    assert y.up_edges == x.up_edges
    assert 2 in y.first_positions
    z = inverse_prefix_lift(y, 2).output
    assert z.values == x.values


def test_hat_roundtrip_small():
    for n in range(1, 7):
        for a in ascent_sequences(n):
            m = hat(a)
            assert is_modified(m)
            assert m.up_edges == a.up_edges
            assert inverse_hat(m).values == a.values


def test_lift_does_not_create_unused_ambient_level_when_no_value_moves():
    x = ChainWord.of([1, 2])
    y = prefix_lift(x, 2).output
    assert y.values == (1, 2)
    assert y.height == 2
    assert inverse_prefix_lift(y, 2).output.values == x.values
