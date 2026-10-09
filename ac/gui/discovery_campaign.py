"""Input parsing for native Discover class/offset transformation campaigns."""

from __future__ import annotations

import json
import re

from ac.discovery.specification import ClassSpec, DegreeWindow
from ac.discovery.transformation_search import TransformationGrammarSpec
from ac.discovery.transformation_family import TransformationFamilySearchSpec


def _classes(text: str, mode: str, family: str) -> tuple[ClassSpec, ...]:
    if mode not in {"avoid", "contain"}:
        raise ValueError("Choose whether each pattern is avoided or contained.")
    tokens = tuple(token.strip() for token in text.split(",") if token.strip())
    if not tokens:
        raise ValueError("Enter at least one pattern. Use * for the unrestricted class.")
    classes = []
    for token in tokens:
        classes.append(
            ClassSpec(family) if token == "*"
            else ClassSpec.build(family, [{"mode": mode, "pattern": token}])
        )
    canonical = {
        json.dumps(item.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")): item
        for item in classes
    }
    return tuple(canonical[key] for key in sorted(canonical))


def _offset_pairs(text: str) -> tuple[tuple[int, int], ...]:
    pairs = []
    for token in (part.strip() for part in text.split(",")):
        if not token:
            continue
        match = re.fullmatch(r"([+-]?\d+)\s*:\s*([+-]?\d+)", token)
        if not match:
            raise ValueError("Offsets use source:target pairs, such as 0:0 or 0:+2.")
        source_offset, target_offset = map(int, match.groups())
        if not -10 <= source_offset <= 10 or not -10 <= target_offset <= 10:
            raise ValueError("Each degree offset must be between −10 and +10.")
        pairs.append((source_offset, target_offset))
    if not pairs:
        raise ValueError("Enter at least one source:target offset pair.")
    if len(set(pairs)) != len(pairs):
        raise ValueError("Offset pairs must be unique.")
    return tuple(pairs)


def build_transformation_family_spec(
    *,
    source_family: str,
    target_family: str,
    rule_mode: str,
    source_patterns: str,
    target_patterns: str,
    offsets: str,
    start: int,
    stop: int,
    max_cost: int = 4,
    max_steps: int = 2,
    candidate_budget: int = 250,
    expansion_budget: int = 25_000,
) -> TransformationFamilySearchSpec:
    """Build a validated Cartesian scan over class and degree-offset grids.

    Pattern lists are comma-separated. A literal ``*`` selects the
    unrestricted family alongside any other listed pattern class.
    """
    source_classes = _classes(source_patterns, rule_mode, source_family)
    target_classes = _classes(target_patterns, rule_mode, target_family)
    offset_pairs = _offset_pairs(offsets)
    grammar = TransformationGrammarSpec(
        max_cost=max_cost,
        max_steps=max_steps,
        candidate_budget=candidate_budget,
        expansion_budget=expansion_budget,
    )
    return TransformationFamilySearchSpec.from_grid(
        source_classes,
        target_classes,
        DegreeWindow(start, stop),
        grammar,
        offset_pairs=offset_pairs,
        candidate_budget=candidate_budget,
        enumeration_budget=5_000_000,
        class_object_budget=1_000_000,
        evaluation_budget=10_000_000,
    )
