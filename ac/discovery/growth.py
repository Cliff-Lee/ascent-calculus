from __future__ import annotations

from ac.core.word import ChainWord
from ac.transform.basic import insert_value_level
from ac.transform.restrict import compress_levels


def modified_parent(word: ChainWord) -> ChainWord | None:
    """Natural delete-last/compress parent of a nonempty modified word."""
    if len(word) <= 1:
        return None
    vals = word.values[:-1]
    ids = word.position_ids[:-1]
    raw = ChainWord(vals, height=word.height, position_ids=ids)
    return compress_levels(raw).output


def modified_children(word: ChainWord) -> tuple[ChainWord, ...]:
    """All natural one-position right children preserving the modified theory.

    Existing final values `v<=last` are repeats and therefore non-ascent-tops.
    Fresh final values `v>last` require insertion of a new value level at rank v
    before appending; this handles fresh nonmaximum values (e.g. 121 -> 1312).
    """
    if len(word) == 0:
        return (ChainWord.of([1]),)
    last = word.at(len(word))
    out: list[ChainWord] = []
    new_id = word.fresh_position_ids(1)[0]

    # Existing repeated final values: must not be reached by an ascent.
    for v in range(1, last + 1):
        out.append(ChainWord(
            word.values + (v,),
            height=word.height,
            position_ids=word.position_ids + (new_id,),
        ))

    # Fresh value levels: must be reached by an ascent. Insert the new level
    # first so old levels >=v are shifted upward.
    for v in range(last + 1, word.height + 2):
        base = insert_value_level(word, v - 1).output
        out.append(ChainWord(
            base.values + (v,),
            height=base.height,
            position_ids=base.position_ids + (new_id,),
        ))
    return tuple(out)


def grow_modified_level(level: tuple[ChainWord, ...]) -> tuple[ChainWord, ...]:
    seen = {}
    for x in level:
        for y in modified_children(x):
            seen[(y.values, y.height)] = y
    return tuple(seen[k] for k in sorted(seen))
