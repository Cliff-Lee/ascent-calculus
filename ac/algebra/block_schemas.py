"""A small, explicit grammar for discovering block-based map candidates.

The grammar combines block boundaries, value-dependency rules, canonical block
orders, and block-local value maps.  It is deliberately finite and inspectable:
every generated candidate records its choices in its constructor and repr.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from ac.core.word import ChainWord
from ac.transform.basic import TransformResult

from .transforms import TransformSignature, Transformation


LEGACY_SEGMENTATIONS = ("increasing_runs", "decreasing_runs", "monotone_runs", "firstness_runs")
LEGACY_PARENT_RULES = ("none", "first_prior_block", "last_prior_block")
LEGACY_BLOCK_ORDERS = ("stable", "reverse", "minimum_up", "safe_up", "safe_down")
LEGACY_BLOCK_MAPS = ("identity", "reverse", "reverse_complement")

# The generated grammar extends the original 108-recipe vocabulary with
# boundaries, block orderings, local maps, and extensions derived from the
# defining position/value structure of ascent sequences.
SEGMENTATIONS = LEGACY_SEGMENTATIONS + (
    "asctop_runs", "ascbottom_runs", "newness_runs", "role_runs",
    "equal_value_runs", "same_value_role_runs",
)
PARENT_RULES = LEGACY_PARENT_RULES + ("all_prior_blocks",)
BLOCK_ORDERS = LEGACY_BLOCK_ORDERS + (
    "maximum_up", "minimum_down", "length_up", "length_down",
    "first_value_up", "first_value_down", "last_value_up", "last_value_down",
    "ascent_count_up", "ascent_count_down", "lexicographic_up", "lexicographic_down",
)
BLOCK_MAPS = LEGACY_BLOCK_MAPS + (
    "complement", "rotate_left", "rotate_right", "sort_up", "sort_down",
)
BLOCK_EXTENSIONS = (
    "none", "max_before_first", "max_pair_around_first",
    "max_before_each_block", "max_after_each_block", "max_between_blocks",
)


@dataclass(frozen=True)
class BlockPiece:
    values: tuple[int, ...]
    position_ids: tuple[int, ...]
    original_index: int

    @property
    def minimum(self):
        return min(self.values)

    @property
    def maximum(self):
        return max(self.values)

    @property
    def length(self):
        return len(self.values)

    @property
    def ascent_count(self):
        return sum(left < right for left, right in zip(self.values, self.values[1:]))


def _segmentation(word: ChainWord, rule: str) -> tuple[BlockPiece, ...]:
    if rule not in SEGMENTATIONS:
        raise ValueError(f"unknown block boundary rule: {rule}")
    if not word.values:
        return ()
    starts = [0]
    if rule == "increasing_runs":
        starts.extend(i for i in range(1, len(word)) if word.values[i - 1] >= word.values[i])
    elif rule == "decreasing_runs":
        starts.extend(i for i in range(1, len(word)) if word.values[i - 1] <= word.values[i])
    elif rule == "monotone_runs":
        direction = 0
        for i in range(1, len(word)):
            delta = (word.values[i] > word.values[i - 1]) - (word.values[i] < word.values[i - 1])
            if delta == 0 or (direction and delta != direction):
                starts.append(i)
                direction = 0
            else:
                direction = delta
    elif rule == "firstness_runs":
        firstness = 1 in word.first_positions
        for i in range(1, len(word)):
            current_first = i + 1 in word.first_positions
            if current_first != firstness:
                starts.append(i)
                firstness = current_first
    else:
        asctop = word.ascent_tops
        ascbottom = word.ascent_bottoms
        first = word.first_positions
        roles = []
        for position in range(1, len(word) + 1):
            role = (
                position in first,
                position in asctop,
                position in ascbottom,
            )
            roles.append(role)
        if rule == "asctop_runs":
            roles = [(position in asctop,) for position in range(1, len(word) + 1)]
        elif rule == "ascbottom_runs":
            roles = [(position in ascbottom,) for position in range(1, len(word) + 1)]
        elif rule == "newness_runs":
            roles = [(position in first,) for position in range(1, len(word) + 1)]
        elif rule == "equal_value_runs":
            roles = [(word.at(position),) for position in range(1, len(word) + 1)]
        elif rule == "same_value_role_runs":
            roles = [
                (word.at(position), *role)
                for position, role in enumerate(roles, start=1)
            ]
        for i in range(1, len(roles)):
            if roles[i] != roles[i - 1]:
                starts.append(i)
    ends = starts[1:] + [len(word)]
    return tuple(
        BlockPiece(word.values[start:end], word.position_ids[start:end], index)
        for index, (start, end) in enumerate(zip(starts, ends))
    )


def _parents(blocks: tuple[BlockPiece, ...], rule: str) -> tuple[tuple[int, ...], ...]:
    if rule not in PARENT_RULES:
        raise ValueError(f"unknown block dependency rule: {rule}")
    if rule == "none":
        return tuple(() for _ in blocks)
    parents: list[tuple[int, ...]] = [()]
    for index, block in enumerate(blocks[1:], start=1):
        earlier = [j for j, previous in enumerate(blocks[:index]) if block.values[0] in previous.values]
        if not earlier:
            parents.append(())
        elif rule == "first_prior_block":
            parents.append((earlier[0],))
        elif rule == "last_prior_block":
            parents.append((earlier[-1],))
        else:
            parents.append(tuple(earlier))
    return tuple(parents)


def _is_ancestor(parents: tuple[tuple[int, ...], ...], first: int, second: int) -> bool:
    pending = list(parents[second])
    seen = set()
    while pending:
        current = pending.pop()
        if current == first:
            return True
        if current not in seen:
            seen.add(current)
            pending.extend(parents[current])
    return False


def _order(blocks: tuple[BlockPiece, ...], parents: tuple[tuple[int, ...], ...], rule: str) -> tuple[int, ...]:
    if rule not in BLOCK_ORDERS:
        raise ValueError(f"unknown canonical block order: {rule}")
    order = list(range(len(blocks)))
    if rule == "stable":
        return tuple(order)
    if rule == "reverse":
        return tuple(reversed(order))
    sort_rules = {
        "minimum_up": (lambda block: block.minimum, False),
        "minimum_down": (lambda block: block.minimum, True),
        "maximum_up": (lambda block: block.maximum, False),
        "length_up": (lambda block: block.length, False),
        "length_down": (lambda block: block.length, True),
        "first_value_up": (lambda block: block.values[0], False),
        "first_value_down": (lambda block: block.values[0], True),
        "last_value_up": (lambda block: block.values[-1], False),
        "last_value_down": (lambda block: block.values[-1], True),
        "ascent_count_up": (lambda block: block.ascent_count, False),
        "ascent_count_down": (lambda block: block.ascent_count, True),
        "lexicographic_up": (lambda block: block.values, False),
        "lexicographic_down": (lambda block: block.values, True),
    }
    if rule in sort_rules:
        key, reverse_order = sort_rules[rule]
        return tuple(sorted(order, key=lambda index: key(blocks[index]), reverse=reverse_order))
    direction = rule.removeprefix("safe_")
    limit = len(order) * (len(order) - 1) // 2
    moves = 0
    while True:
        changed = False
        for index in range(len(order) - 1):
            left, right = order[index], order[index + 1]
            left_block, right_block = blocks[left], blocks[right]
            left_below_right = left_block.maximum < right_block.minimum
            right_below_left = right_block.maximum < left_block.minimum
            swap = right_below_left if direction == "up" else left_below_right
            if not swap or _is_ancestor(parents, left, right) or _is_ancestor(parents, right, left):
                continue
            order[index], order[index + 1] = right, left
            moves += 1
            if moves > limit:
                raise RuntimeError("block-order rewrite exceeded its inversion bound")
            changed = True
        if not changed:
            break
    positions = {block: index for index, block in enumerate(order)}
    if any(positions[parent] > positions[index] for index, dependencies in enumerate(parents) for parent in dependencies):
        raise RuntimeError("safe block order violated a dependency")
    return tuple(order)


@dataclass(frozen=True)
class BlockSchemaT(Transformation):
    """One generated block recipe with explicit, reviewable design choices."""

    segmentation: str
    parent_rule: str
    block_order: str
    block_map: str
    extension: str = "none"

    search_cost = 3

    @property
    def signature(self):
        if self.extension == "max_pair_around_first":
            return TransformSignature(delta_length=2, delta_height=1, partial=True)
        if self.extension == "max_before_first":
            return TransformSignature(delta_length=1, delta_height=1, partial=True)
        if self.extension in {"max_before_each_block", "max_after_each_block"}:
            return TransformSignature(delta_length=None, delta_height=1, partial=True)
        if self.extension == "max_between_blocks":
            return TransformSignature(delta_length=None, delta_height=None, partial=True)
        return TransformSignature(delta_length=0, delta_height=0, partial=True)

    def __post_init__(self):
        if self.segmentation not in SEGMENTATIONS:
            raise ValueError("unsupported block segmentation rule")
        if self.parent_rule not in PARENT_RULES:
            raise ValueError("unsupported block dependency rule")
        if self.block_order not in BLOCK_ORDERS:
            raise ValueError("unsupported canonical block order")
        if self.block_map not in BLOCK_MAPS:
            raise ValueError("unsupported block-local map")
        if self.extension not in BLOCK_EXTENSIONS:
            raise ValueError("unsupported length-extension rule")

    def apply(self, word: ChainWord) -> TransformResult:
        blocks = _segmentation(word, self.segmentation)
        if not blocks:
            raise ValueError("block recipes require a nonempty word")
        parents = _parents(blocks, self.parent_rule)
        order = _order(blocks, parents, self.block_order)
        pivot = word.height + 1
        mapped = []
        for index in order:
            block = blocks[index]
            if self.block_map == "identity":
                values, pids = block.values, block.position_ids
            elif self.block_map == "reverse":
                values, pids = tuple(reversed(block.values)), tuple(reversed(block.position_ids))
            elif self.block_map == "reverse_complement":
                values = tuple(pivot - value for value in reversed(block.values))
                pids = tuple(reversed(block.position_ids))
            elif self.block_map == "complement":
                values, pids = tuple(pivot - value for value in block.values), block.position_ids
            elif self.block_map in {"rotate_left", "rotate_right"}:
                shift = 1 if self.block_map == "rotate_left" else -1
                values = block.values[shift:] + block.values[:shift]
                pids = block.position_ids[shift:] + block.position_ids[:shift]
            else:
                pairs = list(enumerate(zip(block.values, block.position_ids)))
                pairs.sort(key=lambda item: (
                    -item[1][0] if self.block_map == "sort_down" else item[1][0],
                    item[0],
                ))
                values = tuple(value for _, (value, _) in pairs)
                pids = tuple(position_id for _, (_, position_id) in pairs)
            mapped.append((values, pids))

        maximum = word.height + 1
        if self.extension == "none":
            new_count = 0
        elif self.extension == "max_before_first":
            new_count = 1
        elif self.extension == "max_pair_around_first":
            new_count = 2
        elif self.extension == "max_before_each_block":
            new_count = len(mapped)
        elif self.extension == "max_after_each_block":
            new_count = len(mapped)
        else:
            new_count = max(0, len(mapped) - 1)
        new_ids = iter(word.fresh_position_ids(new_count))
        values_list: list[int] = []
        ids_list: list[int] = []
        created_ids_list: list[int] = []
        created_positions_list: list[int] = []

        def append_maximum() -> None:
            position_id = next(new_ids)
            values_list.append(maximum)
            ids_list.append(position_id)
            created_ids_list.append(position_id)
            created_positions_list.append(len(values_list))

        if self.extension == "max_before_first":
            append_maximum()
        elif self.extension == "max_pair_around_first":
            append_maximum()
        for index, (block_values, block_ids) in enumerate(mapped):
            if self.extension == "max_before_each_block":
                append_maximum()
            values_list.extend(block_values)
            ids_list.extend(block_ids)
            if self.extension == "max_pair_around_first" and index == 0:
                append_maximum()
            elif self.extension == "max_after_each_block":
                append_maximum()
            elif self.extension == "max_between_blocks" and index < len(mapped) - 1:
                append_maximum()
        values = tuple(values_list)
        position_ids = tuple(ids_list)
        height = word.height + (1 if new_count else 0)
        value_map = (
            tuple(pivot - value for value in range(1, word.height + 1))
            if self.block_map in {"complement", "reverse_complement"}
            else tuple(range(1, word.height + 1))
        )
        created_ids = tuple(created_ids_list)

        output = ChainWord(values, height=height, position_ids=position_ids)
        output_positions = {pid: index for index, pid in enumerate(output.position_ids, start=1)}
        position_map = tuple(output_positions.get(pid) for pid in word.position_ids)
        created_positions = tuple(output_positions[pid] for pid in created_ids)
        return TransformResult(output, position_map, value_map, created_positions, created_ids)

    def inverse(self):
        raise TypeError("generated block recipes are tested as candidates; no inverse is assumed")

    def trace(self, word: ChainWord) -> dict:
        """Return a one-based, inspectable explanation of this block map."""
        blocks = _segmentation(word, self.segmentation)
        parents = _parents(blocks, self.parent_rule)
        order = _order(blocks, parents, self.block_order)
        position_index = {position_id: index for index, position_id in enumerate(word.position_ids, start=1)}
        new = word.first_positions
        asctop = word.ascent_tops
        ascbottom = word.ascent_bottoms
        block_rows = []
        for index, block in enumerate(blocks):
            positions = tuple(position_index[pid] for pid in block.position_ids)
            block_rows.append({
                "block": index + 1,
                "positions": list(positions),
                "values": list(block.values),
                "roles": [
                    {
                        "position": position,
                        "new": position in new,
                        "asctop": position in asctop,
                        "ascbot": position in ascbottom,
                    }
                    for position in positions
                ],
                "depends_on": [parent + 1 for parent in parents[index]],
            })
        result = self.apply(word)
        output_index = {position_id: index for index, position_id in enumerate(result.output.position_ids, start=1)}
        return {
            "schema": {
                "segmentation": self.segmentation,
                "parent_rule": self.parent_rule,
                "block_order": self.block_order,
                "block_map": self.block_map,
                "extension": self.extension,
            },
            "blocks": block_rows,
            "output_block_order": [index + 1 for index in order],
            "output_positions_by_block": [
                [output_index[pid] for pid in blocks[index].position_ids]
                for index in order
            ],
            "created_positions": list(result.created_positions),
            "output_values": list(result.output.values),
            "output_height": result.output.height,
        }


def enumerate_block_schemas(degree_shift: int = 0) -> tuple[BlockSchemaT, ...]:
    """Generate the finite block-recipe vocabulary compatible with a shift."""
    if degree_shift not in {0, 1, 2}:
        return ()
    extension = {0: "none", 1: "max_before_first", 2: "max_pair_around_first"}[degree_shift]
    recipes = []
    for segmentation, block_order, block_map in product(
        LEGACY_SEGMENTATIONS, LEGACY_BLOCK_ORDERS, LEGACY_BLOCK_MAPS,
    ):
        parent_choices = LEGACY_PARENT_RULES if block_order.startswith("safe_") else ("none",)
        for parent_rule in parent_choices:
            recipes.append(BlockSchemaT(segmentation, parent_rule, block_order, block_map, extension))
    return tuple(recipes)


def generate_block_schemas(
    degree_shift: int | None = None,
    *,
    max_candidates: int = 200_000,
) -> tuple[BlockSchemaT, ...]:
    """Systematically enumerate the expanded, inspectable block grammar.

    For shifts 0, 1, or 2, include the fixed-length extension matching that
    shift plus all variable block-boundary extensions. Other shifts use the
    variable extensions, whose exact lengths are checked on each input word.
    ``None`` requests every registered extension.
    """
    if degree_shift is not None and type(degree_shift) is not int:
        raise ValueError("degree_shift must be an integer or None")
    if type(max_candidates) is not int or max_candidates < 1:
        raise ValueError("max_candidates must be a positive integer")
    fixed_extension = {0: "none", 1: "max_before_first", 2: "max_pair_around_first"}
    variable_extensions = ("max_before_each_block", "max_after_each_block", "max_between_blocks")
    if degree_shift is None:
        extensions = BLOCK_EXTENSIONS
    elif degree_shift in fixed_extension:
        extensions = (fixed_extension[degree_shift],) + variable_extensions
    else:
        extensions = variable_extensions

    recipes = []
    for segmentation, block_order, block_map, extension in product(
        SEGMENTATIONS, BLOCK_ORDERS, BLOCK_MAPS, extensions,
    ):
        parent_choices = PARENT_RULES if block_order.startswith("safe_") else ("none",)
        for parent_rule in parent_choices:
            if len(recipes) >= max_candidates:
                raise ValueError(
                    f"expanded block grammar exceeds max_candidates={max_candidates}; "
                    "reduce grammar dimensions or increase the limit"
                )
            recipes.append(BlockSchemaT(segmentation, parent_rule, block_order, block_map, extension))
    return tuple(recipes)
