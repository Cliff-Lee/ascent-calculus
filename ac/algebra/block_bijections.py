"""Block-structural transformations used as finite research candidates.

The first registered recipe is the modified/revised 111-avoider bijection from
Packman's manuscript.  It is a normal transformation atom so the same finite
map auditor and bounded synthesis code can test it alongside other recipes.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ac.classes.theories import is_modified, is_revised
from ac.core.word import ChainWord
from ac.transform.basic import TransformResult

from .transforms import TransformSignature, Transformation


@dataclass(frozen=True)
class IncreasingBlock:
    values: tuple[int, ...]
    position_ids: tuple[int, ...]

    @property
    def minimum(self) -> int:
        return self.values[0]

    @property
    def maximum(self) -> int:
        return self.values[-1]


def increasing_blocks(word: ChainWord) -> tuple[IncreasingBlock, ...]:
    """Split a word at every nonrise into maximal strictly increasing blocks."""
    if not word.values:
        return ()
    starts = [0]
    starts.extend(i for i in range(1, len(word)) if word.values[i - 1] >= word.values[i])
    ends = starts[1:] + [len(word)]
    return tuple(
        IncreasingBlock(word.values[start:end], word.position_ids[start:end])
        for start, end in zip(starts, ends)
    )


def _repeated_value_parent_tree(blocks: tuple[IncreasingBlock, ...], word: ChainWord) -> tuple[int | None, ...]:
    """Recover the unique earlier block containing each repeated block start."""
    multiplicities = Counter(word.values)
    if any(count > 2 for count in multiplicities.values()):
        raise ValueError("the block-tree recipe requires every value to occur at most twice")
    if not blocks:
        raise ValueError("the block-tree recipe requires a nonempty word")
    if blocks[0].values[0] != 1:
        raise ValueError("the root block must begin with 1")

    first_block: dict[int, int] = {}
    seen_count: Counter[int] = Counter()
    parents: list[int | None] = [None]
    for value in blocks[0].values:
        if seen_count[value]:
            raise ValueError("the root block must contain first occurrences")
        seen_count[value] += 1
        first_block[value] = 0

    for index, block in enumerate(blocks[1:], start=1):
        repeated = block.values[0]
        parent = first_block.get(repeated)
        if parent is None or multiplicities[repeated] != 2 or seen_count[repeated] != 1:
            raise ValueError("each nonroot block must begin with a value repeated in an earlier block")
        parents.append(parent)
        seen_count[repeated] += 1
        for value in block.values[1:]:
            if seen_count[value]:
                raise ValueError("entries after a nonroot block start must be first occurrences")
            seen_count[value] += 1
            first_block[value] = index

    if set(first_block) != set(range(1, word.height + 1)) or seen_count != multiplicities:
        raise ValueError("the block tree does not account for every value level")
    for value, count in multiplicities.items():
        if count == 2 and sum(value in block.values for block in blocks) != 2:
            raise ValueError("a repeated value must occur in exactly two blocks")
    return tuple(parents)


def _is_ancestor(parents: tuple[int | None, ...], first: int, second: int) -> bool:
    parent = parents[second]
    while parent is not None:
        if parent == first:
            return True
        parent = parents[parent]
    return False


def _safe_normal_order(
    blocks: tuple[IncreasingBlock, ...],
    parents: tuple[int | None, ...],
    *,
    direction: str,
) -> tuple[int, ...]:
    """Apply the paper's oriented safe adjacent swaps to a block order."""
    if direction not in {"up", "down"}:
        raise ValueError("block order direction must be 'up' or 'down'")
    order = list(range(len(blocks)))
    move_limit = len(order) * (len(order) - 1) // 2
    moves = 0
    while True:
        changed = False
        for index in range(len(order) - 1):
            left, right = order[index], order[index + 1]
            left_block, right_block = blocks[left], blocks[right]
            left_below_right = left_block.maximum < right_block.minimum
            right_below_left = right_block.maximum < left_block.minimum
            should_swap = right_below_left if direction == "up" else left_below_right
            if not should_swap:
                continue
            # A parent must remain before its child.  The paper's interval
            # criterion makes parent/child pairs ineligible; retain the check
            # here as an executable guard on the structural invariant.
            if _is_ancestor(parents, left, right) or _is_ancestor(parents, right, left):
                continue
            order[index], order[index + 1] = right, left
            moves += 1
            if moves > move_limit:
                raise RuntimeError("safe-swap normalisation exceeded its inversion bound")
            changed = True
        if not changed:
            break
    position = {block: index for index, block in enumerate(order)}
    if any(parent is not None and position[parent] > position[index] for index, parent in enumerate(parents)):
        raise RuntimeError("safe swaps violated the parent-before-child order")
    return tuple(order)


def _reverse_complement(block: IncreasingBlock, new_maximum: int) -> IncreasingBlock:
    return IncreasingBlock(
        tuple(new_maximum - value for value in reversed(block.values)),
        tuple(reversed(block.position_ids)),
    )


def _make_result(source: ChainWord, values: tuple[int, ...], position_ids: tuple[int, ...], *, height: int, value_map, created_ids=()):
    output = ChainWord(values, height=height, position_ids=position_ids)
    new_positions = {pid: index for index, pid in enumerate(output.position_ids, start=1)}
    position_map = tuple(new_positions.get(pid) for pid in source.position_ids)
    created_positions = tuple(new_positions[pid] for pid in created_ids)
    return TransformResult(
        output,
        position_map=position_map,
        value_map=value_map,
        created_positions=created_positions,
        created_position_ids=tuple(created_ids),
    )


class Revised111ToModified111Inverse(Transformation):
    """Partial inverse of the modified-to-revised length +2 block map."""

    signature = TransformSignature(delta_length=-2, delta_height=-1, partial=True)
    search_cost = 4

    def __repr__(self) -> str:
        return "Revised111ToModified111Inverse()"

    def apply(self, word: ChainWord) -> TransformResult:
        if not is_revised(word) or any(count > 2 for count in Counter(word.values).values()):
            raise ValueError("inverse block map is defined on revised 111-avoiders")
        if len(word) < 3:
            raise ValueError("inverse block map requires length at least 3")
        maximum = word.height
        if word.values[0] != maximum or word.values.count(maximum) != 2:
            raise ValueError("the revised word does not have the two distinguished maxima")
        blocks = increasing_blocks(word)
        if len(blocks) < 2 or blocks[0].values != (maximum,):
            raise ValueError("the first distinguished maximum is not a singleton block")
        first_tail = blocks[1]
        if len(first_tail.values) < 2 or first_tail.values[-1] != maximum:
            raise ValueError("the second maximum is not the end of the second increasing block")
        if first_tail.values[-2] != maximum - 1:
            raise ValueError("the second block does not end its prefix at maximum−1")

        recovered = [
            _reverse_complement(IncreasingBlock(first_tail.values[:-1], first_tail.position_ids[:-1]), maximum)
        ]
        recovered.extend(_reverse_complement(block, maximum) for block in blocks[2:])
        recovered_blocks = tuple(recovered)
        recovered_word = ChainWord(
            tuple(value for block in recovered_blocks for value in block.values),
            height=maximum - 1,
            position_ids=tuple(pid for block in recovered_blocks for pid in block.position_ids),
        )
        parents = _repeated_value_parent_tree(recovered_blocks, recovered_word)
        up_order = _safe_normal_order(recovered_blocks, parents, direction="up")
        if up_order != tuple(range(len(recovered_blocks))):
            raise ValueError("the recovered blocks are not in the required up-normal order")
        down_order = _safe_normal_order(recovered_blocks, parents, direction="down")
        ordered = tuple(recovered_blocks[index] for index in down_order)
        values = tuple(value for block in ordered for value in block.values)
        pids = tuple(pid for block in ordered for pid in block.position_ids)
        value_map = tuple(maximum - value if value < maximum else None for value in range(1, maximum + 1))
        return _make_result(word, values, pids, height=maximum - 1, value_map=value_map)

    def inverse(self) -> Transformation:
        return Modified111ToRevised111()


class Modified111ToRevised111(Transformation):
    """Packman's explicit ``M_n(111) → R_{n+2}(111)`` block bijection."""

    signature = TransformSignature(delta_length=2, delta_height=1, partial=True)
    search_cost = 4

    def __repr__(self) -> str:
        return "Modified111ToRevised111()"

    def apply(self, word: ChainWord) -> TransformResult:
        if not is_modified(word) or any(count > 2 for count in Counter(word.values).values()):
            raise ValueError("block bijection is defined on modified 111-avoiders")
        blocks = increasing_blocks(word)
        parents = _repeated_value_parent_tree(blocks, word)
        order = _safe_normal_order(blocks, parents, direction="up")
        new_maximum = word.height + 1
        transformed = tuple(_reverse_complement(blocks[index], new_maximum) for index in order)
        first, remainder = transformed[0], transformed[1:]
        fresh_ids = word.fresh_position_ids(2)
        values = (new_maximum,) + first.values + (new_maximum,) + tuple(
            value for block in remainder for value in block.values
        )
        pids = (fresh_ids[0],) + first.position_ids + (fresh_ids[1],) + tuple(
            pid for block in remainder for pid in block.position_ids
        )
        value_map = tuple(new_maximum - value for value in range(1, word.height + 1))
        return _make_result(word, values, pids, height=new_maximum, value_map=value_map, created_ids=fresh_ids)

    def inverse(self) -> Transformation:
        return Revised111ToModified111Inverse()


def Modified111BlockBijection() -> Modified111ToRevised111:
    """Construct the registered, shift-2 modified/revised block recipe."""
    return Modified111ToRevised111()
