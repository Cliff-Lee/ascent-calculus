from __future__ import annotations

from itertools import product

from ac.core.word import ChainWord
from ac.classes.theories import is_ascent_sequence, is_modified, is_revised


def chain_words(n: int, height: int):
    if n < 0 or height < 0:
        raise ValueError
    if n == 0:
        yield ChainWord((), height=height)
        return
    if height == 0:
        return
    for vals in product(range(1, height + 1), repeat=n):
        yield ChainWord(vals, height=height)


def cayley_words(n: int):
    """Generate Cayley words by brute force; intended for small verification only."""
    if n == 0:
        yield ChainWord((), height=0)
        return
    for h in range(1, n + 1):
        for x in chain_words(n, h):
            if x.is_cayley:
                yield x


def ascent_sequences(n: int):
    """Generate positive ordinary ascent sequences recursively."""
    for values in ascent_sequence_values(n):
        yield ChainWord(values)


def ascent_sequence_values(n: int):
    """Generate the raw tuples underlying ``ascent_sequences``.

    This avoids constructing a temporary ChainWord when a conversion such as
    ``modified_via_hat`` immediately maps each generated sequence.
    """
    if n <= 0:
        return

    def rec(prefix: tuple[int, ...]):
        if len(prefix) == n:
            yield prefix
            return
        asc = sum(1 for a, b in zip(prefix, prefix[1:]) if a < b)
        upper = asc + 2
        for v in range(1, upper + 1):
            yield from rec(prefix + (v,))

    yield from rec((1,))


def modified_sequences(n: int):
    for x in cayley_words(n):
        if is_modified(x):
            yield x


def revised_sequences(n: int):
    for x in cayley_words(n):
        if is_revised(x):
            yield x


def modified_via_hat(n: int):
    """Generate modified ascent sequences as hat images of A_n.

    This is a fast conversion-based universe, deliberately separate from the
    brute-force recognizer ``modified_sequences`` so the two can cross-check
    one another in tests.
    """
    from ac.transform.hat import hat_values
    for values in ascent_sequence_values(n):
        yield ChainWord(hat_values(values))
