"""Generic, bounded research experiments built from existing AC engine objects.

This module is an adapter: family generation, pattern semantics, and word
statistics all come from the engine.  The GUI submits a serializable question
model and receives a reproducible finite result.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from time import perf_counter
import re
from typing import Literal

from ac.core.word import ChainWord
from ac.generate.universes import ascent_sequences, modified_via_hat, revised_sequences
from ac.patterns.classical import ClassicalPattern


Family = Literal["ordinary", "modified", "revised"]
Question = Literal["count", "compare"]
Statistic = Literal[
    "none",
    "ascents",
    "ascent_runs",
    "run_start_positions",
    "run_lengths",
    "maximum",
    "distinct_values",
    "multiplicity_partition",
    "first_occurrence_positions",
    "last_occurrence_positions",
]

FAMILY_GENERATORS = {
    "ordinary": ascent_sequences,
    "modified": modified_via_hat,
    "revised": revised_sequences,
}
FAMILY_LIMITS = {"ordinary": 11, "modified": 11, "revised": 7}
STATISTICS = {
    "none": "Overall count",
    "ascents": "Number of ascents",
    "ascent_runs": "Number of ascent runs",
    "run_start_positions": "Ascent-run start positions",
    "run_lengths": "Ascent-run lengths",
    "maximum": "Maximum value",
    "distinct_values": "Number of distinct values",
    "multiplicity_partition": "Multiplicity partition",
    "first_occurrence_positions": "First-occurrence positions",
    "last_occurrence_positions": "Last-occurrence positions",
}
GENERIC_PATTERN_MAX_DEGREE = 12


@dataclass(frozen=True)
class PatternRule:
    mode: Literal["avoid", "contain"]
    pattern: ClassicalPattern


@dataclass(frozen=True)
class ExperimentSide:
    family: Family
    rules: tuple[PatternRule, ...]
    degree_offset: int = 0


@dataclass(frozen=True)
class StructuralCondition:
    statistic: Literal["ascents", "maximum", "distinct_values"]
    operator: Literal["eq", "ge", "le"]
    value: int


@dataclass(frozen=True)
class ExperimentSpec:
    question: Question
    left: ExperimentSide
    right: ExperimentSide | None
    start: int
    stop: int
    statistic: Statistic = "none"
    condition: StructuralCondition | None = None


def validate_pattern(spec: str) -> dict:
    """Validate and standardize a user-supplied classical Cayley pattern."""
    pattern = ClassicalPattern(spec)
    values = list(pattern.values)
    return {
        "valid": True,
        "values": values,
        "arity": pattern.arity,
        "height": pattern.height,
        "notation": "⟨" + ", ".join(map(str, values)) + "⟩",
    }


def _parse_side(raw: dict, name: str) -> ExperimentSide:
    if not isinstance(raw, dict):
        raise ValueError(f"{name}: expected a class specification")
    family = raw.get("family")
    if family not in FAMILY_GENERATORS:
        raise ValueError(f"{name}: choose ordinary, modified, or revised ascent sequences")
    offset = int(raw.get("degree_offset", 0))
    if not -10 <= offset <= 10:
        raise ValueError(f"{name}: degree shift must be between -10 and 10")
    rules: list[PatternRule] = []
    raw_rules = raw.get("rules", [])
    if not isinstance(raw_rules, list):
        raise ValueError(f"{name}: pattern rules must be a list")
    for item in raw_rules:
        if not isinstance(item, dict):
            raise ValueError(f"{name}: each pattern rule must be an object")
        mode = item.get("mode")
        if mode not in {"avoid", "contain"}:
            raise ValueError(f"{name}: pattern rule must say avoid or contain")
        try:
            pattern = ClassicalPattern(item.get("pattern", ""))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name}: {exc}") from exc
        rules.append(PatternRule(mode, pattern))
    return ExperimentSide(family, tuple(rules), offset)


def parse_experiment(raw: dict) -> ExperimentSpec:
    """Validate the small experiment language submitted by the GUI."""
    if not isinstance(raw, dict):
        raise ValueError("Experiment specification must be an object")
    question = raw.get("question", "compare")
    if question not in {"count", "compare"}:
        raise ValueError("GUI-3.1 supports count and compare experiments")
    start, stop = int(raw.get("start", 1)), int(raw.get("stop", 8))
    if not (1 <= start <= stop <= 11):
        raise ValueError("Choose a range with 1 ≤ start ≤ stop ≤ 11")
    statistic = raw.get("statistic", "none")
    if statistic not in STATISTICS:
        raise ValueError("Unknown refinement statistic")
    raw_condition = raw.get("condition")
    condition = None
    if raw_condition:
        if not isinstance(raw_condition, dict):
            raise ValueError("Additional condition must be an object")
        condition_stat = raw_condition.get("statistic")
        operator = raw_condition.get("operator")
        if condition_stat not in {"ascents", "maximum", "distinct_values"}:
            raise ValueError("Additional conditions can use ascent count, maximum, or distinct values")
        if operator not in {"eq", "ge", "le"}:
            raise ValueError("Choose an exact, minimum, or maximum condition")
        value = int(raw_condition.get("value", 0))
        if value < 0:
            raise ValueError("Condition values must be nonnegative")
        condition = StructuralCondition(condition_stat, operator, value)
    left = _parse_side(raw.get("left", {}), "First class")
    right = _parse_side(raw.get("right", {}), "Second class") if question == "compare" else None
    sides = [left] + ([right] if right is not None else [])
    for side, title in zip(sides, ("First class", "Second class")):
        first_degree, last_degree = start + side.degree_offset, stop + side.degree_offset
        if first_degree < 1:
            raise ValueError(f"{title}: the degree shift makes the first requested degree less than 1")
        limit = FAMILY_LIMITS[side.family]
        if last_degree > limit:
            raise ValueError(
                f"{title}: {side.family} generation is currently bounded to degree {limit}; "
                "lower the range or degree shift"
            )
        for rule in side.rules:
            if _sandwich_parameters(rule.pattern.values) is None and rule.pattern.arity >= 3:
                pattern_limit = max(5, GENERIC_PATTERN_MAX_DEGREE - rule.pattern.arity)
                if last_degree > pattern_limit:
                    raise ValueError(
                        f"{title}: general length-{rule.pattern.arity} pattern searches are currently "
                        f"bounded to degree {pattern_limit}; lower the range or use a supported "
                        "repeated-sandwich pattern"
                    )
    return ExperimentSpec(question, left, right, start, stop, statistic, condition)


def _pattern_present(word: ChainWord, pattern: ClassicalPattern) -> bool:
    # The engine already has an exact fibre-gap characterization for this
    # repeated-sandwich pattern family; use it for these common cases.
    params = _sandwich_parameters(pattern.values)
    if params is not None:
        left, right = params
        for pivot in range(pattern.height, word.height + 1):
            total = len(word.fibre(pivot))
            if total < left + right:
                continue
            seen = 0
            for value in word.values:
                if value < pivot and seen >= left and total - seen >= right:
                    return True
                if value == pivot:
                    seen += 1
        return False
    return _compile_pattern(pattern.values).contains(word)


def _sandwich_parameters(values: tuple[int, ...]) -> tuple[int, int] | None:
    if len(values) < 3 or values[0] != values[-1]:
        return None
    pivot_label = values[0]
    left = 0
    while left < len(values) and values[left] == pivot_label:
        left += 1
    right = 0
    while right < len(values) and values[len(values) - right - 1] == pivot_label:
        right += 1
    middle = values[left:len(values) - right]
    if len(middle) == 1 and middle[0] < pivot_label:
        return left, right
    return None


@lru_cache(maxsize=256)
def _compile_pattern(values: tuple[int, ...]):
    return ClassicalPattern(values).compile()


def _matches(word: ChainWord, rules: tuple[PatternRule, ...], condition: StructuralCondition | None = None) -> bool:
    for rule in rules:
        found = _pattern_present(word, rule.pattern)
        if (rule.mode == "avoid" and found) or (rule.mode == "contain" and not found):
            return False
    if condition is not None:
        value = _statistic(word, condition.statistic)
        if condition.operator == "eq" and value != condition.value:
            return False
        if condition.operator == "ge" and value < condition.value:
            return False
        if condition.operator == "le" and value > condition.value:
            return False
    return True


def _run_blocks(word: ChainWord) -> list[list[int]]:
    starts = sorted(word.run_starts)
    boundaries = starts[1:] + [len(word.values) + 1]
    return [list(word.values[start - 1:end - 1]) for start, end in zip(starts, boundaries)]


def _statistic(word: ChainWord, name: Statistic):
    if name == "ascents":
        return len(word.up_edges)
    if name == "ascent_runs":
        return len(word.run_starts)
    if name == "run_start_positions":
        return tuple(sorted(word.run_starts))
    if name == "run_lengths":
        return tuple(len(block) for block in _run_blocks(word))
    if name == "maximum":
        return max(word.values, default=0)
    if name == "distinct_values":
        return len(word.first_positions)
    if name == "multiplicity_partition":
        return word.integer_partition
    if name == "first_occurrence_positions":
        return tuple(sorted(word.first_positions))
    if name == "last_occurrence_positions":
        return tuple(sorted(word.last_positions))
    return None


def _new_distribution() -> Counter:
    return Counter()


def _json_distribution(counter: Counter) -> list[dict]:
    def convert(key):
        return list(key) if isinstance(key, tuple) else key
    return [
        {"value": convert(key), "count": count}
        for key, count in sorted(counter.items(), key=lambda item: repr(item[0]))
    ]


def _count_side(side: ExperimentSide, degree: int, statistic: Statistic, condition: StructuralCondition | None = None):
    generator = FAMILY_GENERATORS[side.family]
    count = 0
    tested = 0
    distribution = _new_distribution()
    for word in generator(degree):
        tested += 1
        if _matches(word, side.rules, condition):
            count += 1
            if statistic != "none":
                distribution[_statistic(word, statistic)] += 1
    return count, tested, distribution


def _count_pair_same_universe(left: ExperimentSide, right: ExperimentSide, degree: int, statistic: Statistic, condition: StructuralCondition | None = None):
    count_left = count_right = tested = 0
    dist_left, dist_right = _new_distribution(), _new_distribution()
    for word in FAMILY_GENERATORS[left.family](degree):
        tested += 1
        if _matches(word, left.rules, condition):
            count_left += 1
            if statistic != "none":
                dist_left[_statistic(word, statistic)] += 1
        if _matches(word, right.rules, condition):
            count_right += 1
            if statistic != "none":
                dist_right[_statistic(word, statistic)] += 1
    return (count_left, tested, dist_left), (count_right, 0, dist_right)


def _word_record(word: ChainWord, index: int) -> dict:
    """Compact, stable record used by the experiment object browser."""
    run_blocks = _run_blocks(word)
    return {
        "index": index,
        "word": list(word.values),
        "length": len(word.values),
        "height": word.height,
        "ascents": _statistic(word, "ascents"),
        "maximum": _statistic(word, "maximum"),
        "distinct_values": _statistic(word, "distinct_values"),
        "multiplicity_partition": list(_statistic(word, "multiplicity_partition")),
        "first_occurrence_positions": list(_statistic(word, "first_occurrence_positions")),
        "last_occurrence_positions": list(_statistic(word, "last_occurrence_positions")),
        "run_start_positions": list(_statistic(word, "run_start_positions")),
        "run_lengths": list(_statistic(word, "run_lengths")),
        "run_blocks": run_blocks,
    }


def _parse_browser_filters(raw: dict | None, side: ExperimentSide, degree: int):
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError("Object-browser filters must be an object")
    statistic = raw.get("statistic") or None
    expected = None
    if statistic:
        allowed = {"ascents", "ascent_runs", "maximum", "distinct_values", "multiplicity_partition", "first_occurrence_positions", "last_occurrence_positions", "run_start_positions", "run_lengths"}
        if statistic not in allowed:
            raise ValueError("Choose a supported object statistic filter")
        value = raw.get("value", "")
        if statistic in {"ascents", "ascent_runs", "maximum", "distinct_values"}:
            try:
                expected = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError("Enter a whole-number value for this statistic filter") from exc
            if expected < 0:
                raise ValueError("Statistic filter values must be nonnegative")
        else:
            try:
                expected = tuple(int(part) for part in re.split(r"[,\s]+", str(value).strip()) if part)
            except ValueError as exc:
                raise ValueError("Enter a comma-separated list of whole numbers") from exc
            if not expected or any(part < 1 for part in expected):
                raise ValueError("List-valued statistic filters need positive whole numbers")
    pattern_rule = None
    pattern_mode = raw.get("pattern_mode", "none")
    pattern_text = str(raw.get("pattern", "")).strip()
    if pattern_mode not in {"none", "avoid", "contain"}:
        raise ValueError("Pattern filter must be contains, avoids, or off")
    if pattern_mode != "none":
        try:
            pattern = ClassicalPattern(pattern_text)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Object-browser pattern: {exc}") from exc
        if _sandwich_parameters(pattern.values) is None and pattern.arity >= 3:
            pattern_limit = max(5, GENERIC_PATTERN_MAX_DEGREE - pattern.arity)
            if degree > pattern_limit:
                raise ValueError(
                    f"General length-{pattern.arity} object-browser pattern filters are bounded to degree {pattern_limit}"
                )
        pattern_rule = PatternRule(pattern_mode, pattern)
    return statistic, expected, pattern_rule


def browse_objects(
    raw: dict,
    side_name: str,
    n: int,
    offset: int = 0,
    limit: int = 25,
    filters: dict | None = None,
) -> dict:
    """Return one page of members from a class in a submitted experiment.

    ``n`` is the experiment's displayed degree; side degree offsets are applied
    here exactly as they are in the count result. Pages are generated lazily.
    """
    spec = parse_experiment(raw)
    if side_name not in {"left", "right"} or (side_name == "right" and spec.right is None):
        raise ValueError("Choose a class that exists in this experiment")
    if not spec.start <= int(n) <= spec.stop:
        raise ValueError("Choose a degree from the experiment's requested range")
    offset, limit = int(offset), int(limit)
    if offset < 0 or offset > 100_000:
        raise ValueError("Object-browser offset must be between 0 and 100,000")
    if not 1 <= limit <= 100:
        raise ValueError("Object-browser page size must be between 1 and 100")
    side = spec.left if side_name == "left" else spec.right
    assert side is not None
    degree = int(n) + side.degree_offset
    filter_stat, filter_value, pattern_filter = _parse_browser_filters(filters, side, degree)

    def included(word):
        if not _matches(word, side.rules, spec.condition):
            return False
        if filter_stat and _statistic(word, filter_stat) != filter_value:
            return False
        if pattern_filter:
            found = _pattern_present(word, pattern_filter.pattern)
            if (pattern_filter.mode == "avoid" and found) or (pattern_filter.mode == "contain" and not found):
                return False
        return True

    matches = 0
    objects = []
    tested = 0
    has_more = False
    for word in FAMILY_GENERATORS[side.family](degree):
        tested += 1
        if not included(word):
            continue
        matches += 1
        if matches > offset + limit:
            has_more = True
            break
        if offset < matches <= offset + limit:
            objects.append(_word_record(word, matches))
    return {
        "side": side_name,
        "display_degree": int(n),
        "degree": degree,
        "offset": offset,
        "page_size": limit,
        "objects": objects,
        "next_offset": offset + len(objects) if has_more else None,
        "scanned_objects": tested,
        "filters_active": bool(filter_stat or pattern_filter),
        "filter_summary": {
            "statistic": filter_stat,
            "value": list(filter_value) if isinstance(filter_value, tuple) else filter_value,
            "pattern_mode": pattern_filter.mode if pattern_filter else "none",
            "pattern": list(pattern_filter.pattern.values) if pattern_filter else None,
        },
        "specification": _serial_side(side),
    }


def find_unmatched_objects(raw: dict, n: int) -> dict:
    """Find the first exact set-difference witnesses for a same-universe pair."""
    spec = parse_experiment(raw)
    if spec.right is None:
        raise ValueError("Unmatched-object search requires a comparison experiment")
    if not spec.start <= int(n) <= spec.stop:
        raise ValueError("Choose a degree from the experiment's requested range")
    left_degree = int(n) + spec.left.degree_offset
    right_degree = int(n) + spec.right.degree_offset
    if spec.left.family != spec.right.family or left_degree != right_degree:
        raise ValueError("Exact unmatched-word search currently requires both classes to use the same family and degree")
    left_only = right_only = None
    tested = 0
    for word in FAMILY_GENERATORS[spec.left.family](left_degree):
        tested += 1
        in_left = _matches(word, spec.left.rules, spec.condition)
        in_right = _matches(word, spec.right.rules, spec.condition)
        if in_left and not in_right and left_only is None:
            left_only = _word_record(word, 0)
        elif in_right and not in_left and right_only is None:
            right_only = _word_record(word, 0)
        if left_only is not None and right_only is not None:
            break
    return {
        "n": int(n),
        "left_degree": left_degree,
        "right_degree": right_degree,
        "left_only": left_only,
        "right_only": right_only,
        "tested_objects": tested,
        "exact": True,
        "finite_only": True,
    }


def run_experiment(raw: dict) -> dict:
    """Run a bounded count or class comparison and return a compact result."""
    spec = parse_experiment(raw)
    rows = []
    total_tested = 0
    started = perf_counter()

    for n in range(spec.start, spec.stop + 1):
        left_n = n + spec.left.degree_offset
        if spec.right is None:
            left_count, tested, left_dist = _count_side(spec.left, left_n, spec.statistic, spec.condition)
            total_tested += tested
            rows.append({
                "n": n,
                "left_degree": left_n,
                "left_count": left_count,
                "left_distribution": _json_distribution(left_dist) if spec.statistic != "none" else None,
            })
            continue

        right_n = n + spec.right.degree_offset
        if spec.left.family == spec.right.family and left_n == right_n:
            (left_count, tested, left_dist), (right_count, _, right_dist) = _count_pair_same_universe(
                spec.left, spec.right, left_n, spec.statistic, spec.condition
            )
            total_tested += tested
        else:
            left_count, left_tested, left_dist = _count_side(spec.left, left_n, spec.statistic, spec.condition)
            right_count, right_tested, right_dist = _count_side(spec.right, right_n, spec.statistic, spec.condition)
            total_tested += left_tested + right_tested

        difference = left_count - right_count
        row = {
            "n": n,
            "left_degree": left_n,
            "left_count": left_count,
            "right_degree": right_n,
            "right_count": right_count,
            "difference": difference,
            "counts_match": difference == 0,
        }
        if spec.statistic != "none":
            left_serial, right_serial = _json_distribution(left_dist), _json_distribution(right_dist)
            row.update({
                "left_distribution": left_serial,
                "right_distribution": right_serial,
                "distributions_match": left_serial == right_serial,
            })
        rows.append(row)

    first_divergence = next((row for row in rows if not row["counts_match"]), None) if spec.right else None
    first_statistic_divergence = (
        next((row for row in rows if not row.get("distributions_match", True)), None)
        if spec.right and spec.statistic != "none" else None
    )
    all_match = spec.right is not None and first_divergence is None
    if spec.right is None:
        headline = f"Counted {rows[-1]['left_count']:,} objects at n={rows[-1]['n']}"
    elif all_match:
        if spec.statistic == "none":
            prefix = "Match"
        elif first_statistic_divergence is None:
            prefix = "Counts and distributions match"
        else:
            prefix = f"Counts match; {STATISTICS[spec.statistic].lower()} first differs at n={first_statistic_divergence['n']}"
        suffix = f"through n={spec.stop}" if spec.start == 1 else f"for n={spec.start}–{spec.stop}"
        headline = f"{prefix} {suffix}"
    else:
        headline = f"First divergence at n={first_divergence['n']}"

    return {
        "question": spec.question,
        "headline": headline,
        "all_counts_match": all_match if spec.right else None,
        "first_divergence": first_divergence,
        "first_statistic_divergence": first_statistic_divergence,
        "statistic": spec.statistic,
        "statistic_label": STATISTICS[spec.statistic],
        "rows": rows,
        "tested_objects": total_tested,
        "runtime_seconds": round(perf_counter() - started, 3),
        "finite_only": True,
        "notice": "Finite computation only. Matching through a bounded range is not a proof for all degrees.",
        "specification": {
            "question": spec.question,
            "start": spec.start,
            "stop": spec.stop,
            "statistic": spec.statistic,
            "condition": _serial_condition(spec.condition),
            "left": _serial_side(spec.left),
            "right": _serial_side(spec.right) if spec.right else None,
        },
    }


def _serial_side(side: ExperimentSide) -> dict:
    return {
        "family": side.family,
        "degree_offset": side.degree_offset,
        "rules": [
            {"mode": rule.mode, "pattern": list(rule.pattern.values)}
            for rule in side.rules
        ],
    }


def _serial_condition(condition: StructuralCondition | None):
    if condition is None:
        return None
    return {"statistic": condition.statistic, "operator": condition.operator, "value": condition.value}
