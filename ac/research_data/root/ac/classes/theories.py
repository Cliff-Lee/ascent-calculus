from __future__ import annotations

from ac.core.word import ChainWord


def is_ascent_sequence(x: ChainWord) -> bool:
    """Positive convention for ordinary ascent sequences.

    y_1=1 and, for i>1,
        1 <= y_i <= 2 + asc(y_1...y_{i-1}).
    Empty words are excluded.
    """
    if len(x) == 0 or x.at(1) != 1:
        return False
    for i in range(2, len(x) + 1):
        prefix_asc = sum(
            1 for j in range(1, i - 1) if x.at(j) < x.at(j + 1)
        )
        if not (1 <= x.at(i) <= prefix_asc + 2):
            return False
    return True


def is_modified(x: ChainWord) -> bool:
    """Modified ascent sequence via the Cayley first=ascent-top characterization."""
    return x.is_cayley and x.first_positions == x.ascent_tops


def is_revised(x: ChainWord) -> bool:
    """Revised ascent sequence via the Cayley first=ascent-bottom characterization."""
    return x.is_cayley and x.first_positions == x.ascent_bottoms
