from __future__ import annotations

from ac.core.word import ChainWord
from ac.transform.basic import inverse_prefix_lift


def hat_values(values: tuple[int, ...]) -> tuple[int, ...]:
    """Apply the classical hat map to raw values without intermediate words."""
    # A prefix lift changes entries strictly before its pivot, so later pivots
    # retain their original value.  Apply the same ordered updates to one value
    # buffer instead of allocating a ChainWord for every elementary lift.
    output = list(values)
    tops = tuple(i + 2 for i in range(len(values) - 1) if values[i] < values[i + 1])
    for i in tops:
        threshold = output[i - 1]
        for j in range(i - 1):
            if output[j] >= threshold:
                output[j] += 1
    return tuple(output)


def hat(x: ChainWord) -> ChainWord:
    """Classical hat map as left-to-right lifts at raw ascent-top positions."""
    return ChainWord(hat_values(x.values), position_ids=x.position_ids)


def inverse_hat(x: ChainWord) -> ChainWord:
    """Inverse hat map using the preserved raw ascent-top set, right-to-left."""
    y = x
    for i in sorted(x.raw_ascent_tops, reverse=True):
        y = inverse_prefix_lift(y, i).output
    return ChainWord(y.values, position_ids=y.position_ids)
