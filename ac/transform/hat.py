from __future__ import annotations

from ac.core.word import ChainWord
from ac.transform.basic import prefix_lift, inverse_prefix_lift


def hat(x: ChainWord) -> ChainWord:
    """Classical hat map as left-to-right lifts at raw ascent-top positions."""
    y = x
    for i in sorted(x.raw_ascent_tops):
        y = prefix_lift(y, i).output
    return ChainWord(y.values, position_ids=y.position_ids)


def inverse_hat(x: ChainWord) -> ChainWord:
    """Inverse hat map using the preserved raw ascent-top set, right-to-left."""
    y = x
    for i in sorted(x.raw_ascent_tops, reverse=True):
        y = inverse_prefix_lift(y, i).output
    return ChainWord(y.values, position_ids=y.position_ids)
