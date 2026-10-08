"""Bounded discovery of count conjectures among generated pattern classes."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from hashlib import sha256
import json
from typing import Literal

from ac.discovery.specification import (
    FAMILIES,
    RULE_MODES,
    SEMANTICS_VERSION,
    SPEC_VERSION,
    ClassSpec,
    DegreeWindow,
)
from ac.discovery.wilf import PATTERN_DEGREE_LIMITS, cayley_patterns, pattern_avoidance_counts


DISCOVERY_FORMAT = "ascent-machine-conjecture-search"
DISCOVERY_VERSION = 1
MAX_PAIR_CHECKS = 1_000_000
MAX_RESULTS = 1_000


@dataclass(frozen=True)
class ConjectureSearchSpec:
    """Versioned grammar for automatic single-pattern class-count search."""

    families: tuple[Literal["ordinary", "modified", "revised"], ...]
    degrees: DegreeWindow
    pattern_lengths: tuple[int, ...] = (2, 3)
    modes: tuple[Literal["avoid", "contain"], ...] = ("avoid", "contain")
    offsets: tuple[int, ...] = (0,)

    def __post_init__(self) -> None:
        if not isinstance(self.families, tuple) or not self.families or any(family not in FAMILIES for family in self.families):
            raise ValueError("choose one or more ascent-sequence families")
        if not isinstance(self.degrees, DegreeWindow):
            raise ValueError("degrees must be an inclusive DegreeWindow")
        if not isinstance(self.pattern_lengths, tuple) or not self.pattern_lengths:
            raise ValueError("choose one or more Cayley pattern lengths")
        if any(type(length) is not int or length not in PATTERN_DEGREE_LIMITS for length in self.pattern_lengths):
            raise ValueError("supported pattern lengths are 2, 3, and 4")
        if not isinstance(self.modes, tuple) or not self.modes or any(mode not in RULE_MODES for mode in self.modes):
            raise ValueError("choose avoidance, containment, or both")
        if not isinstance(self.offsets, tuple) or not self.offsets:
            raise ValueError("choose one or more degree offsets")
        if any(type(offset) is not int or not -5 <= offset <= 5 for offset in self.offsets):
            raise ValueError("degree offsets must be integers from -5 to +5")
        object.__setattr__(self, "families", tuple(family for family in FAMILIES if family in set(self.families)))
        object.__setattr__(self, "pattern_lengths", tuple(sorted(set(self.pattern_lengths))))
        object.__setattr__(self, "modes", tuple(mode for mode in RULE_MODES if mode in set(self.modes)))
        object.__setattr__(self, "offsets", tuple(sorted(set(self.offsets))))

    @classmethod
    def build(
        cls,
        families=("ordinary", "modified", "revised"),
        *,
        start: int = 1,
        stop: int = 7,
        pattern_lengths=(2, 3),
        modes=("avoid", "contain"),
        offsets=(0,),
    ) -> "ConjectureSearchSpec":
        return cls(tuple(families), DegreeWindow(start, stop), tuple(pattern_lengths), tuple(modes), tuple(offsets))

    def for_pattern_length(self, length: int) -> "ConjectureSearchSpec":
        if length not in self.pattern_lengths:
            raise ValueError("pattern length is outside this discovery grammar")
        return replace(self, pattern_lengths=(length,))

    def to_dict(self) -> dict:
        return {
            "format": DISCOVERY_FORMAT,
            "version": DISCOVERY_VERSION,
            "semantics": SEMANTICS_VERSION,
            "families": list(self.families),
            "degrees": self.degrees.to_dict(),
            "pattern_lengths": list(self.pattern_lengths),
            "modes": list(self.modes),
            "offsets": list(self.offsets),
        }

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @property
    def fingerprint(self) -> str:
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def describe(self) -> str:
        mode_text = " and ".join(self.modes)
        offset_text = ", ".join(f"{value:+d}" for value in self.offsets)
        return (
            f"Search {mode_text} classes from {', '.join(self.families)} ascent sequences, "
            f"pattern lengths {', '.join(map(str, self.pattern_lengths))}, "
            f"base degrees {self.degrees.start}…{self.degrees.stop}, offsets {offset_text}."
        )

    @classmethod
    def from_dict(cls, raw: dict) -> "ConjectureSearchSpec":
        expected = {"format", "version", "semantics", "families", "degrees", "pattern_lengths", "modes", "offsets"}
        if not isinstance(raw, dict) or set(raw) != expected:
            raise ValueError("conjecture-search fields do not match the version-1 schema")
        if raw["format"] != DISCOVERY_FORMAT or type(raw["version"]) is not int or raw["version"] != DISCOVERY_VERSION:
            raise ValueError("unsupported conjecture-search format or version")
        if raw["semantics"] != SEMANTICS_VERSION:
            raise ValueError("conjecture search uses an unknown ascent-sequence semantics version")
        if any(not isinstance(raw[key], list) for key in ("families", "pattern_lengths", "modes", "offsets")):
            raise ValueError("conjecture-search families, lengths, modes, and offsets must be arrays")
        return cls(
            tuple(raw["families"]),
            DegreeWindow.from_dict(raw["degrees"]),
            tuple(raw["pattern_lengths"]),
            tuple(raw["modes"]),
            tuple(raw["offsets"]),
        )

    @classmethod
    def from_json(cls, payload: str) -> "ConjectureSearchSpec":
        try:
            raw = json.loads(payload)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid conjecture-search JSON: {exc}") from exc
        return cls.from_dict(raw)


def _candidate_id(family: str, mode: str, pattern: tuple[int, ...]) -> str:
    class_spec = ClassSpec.build(family, [{"mode": mode, "pattern": pattern}])
    encoded = json.dumps(class_spec.to_dict(), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _pattern_class_count(family: str, degree: int, mode: str, pattern: tuple[int, ...], catalogs: dict) -> int:
    length = len(pattern)
    catalog_key = (family, degree, length)
    if catalog_key not in catalogs:
        catalogs[catalog_key] = pattern_avoidance_counts(family, degree, length)
    total, avoid_counts = catalogs[catalog_key]
    avoided = avoid_counts[pattern]
    return avoided if mode == "avoid" else total - avoided


def _rank_key(item: dict):
    return (
        item["matched_degrees"] == item["tested_degrees"],
        item["matched_degrees"],
        item["tested_degrees"],
        -abs(item["degree_offset"]),
        item["source_class"]["family"],
        item["source_class"]["rule"]["mode"],
        tuple(item["source_class"]["rule"]["pattern"]),
        item["target_class"]["family"],
        item["target_class"]["rule"]["mode"],
        tuple(item["target_class"]["rule"]["pattern"]),
    )


def discover_count_conjectures(
    spec: ConjectureSearchSpec,
    *,
    keep: int = 100,
    minimum_prefix_degrees: int = 2,
    pair_budget: int = MAX_PAIR_CHECKS,
) -> dict:
    """Search generated pattern classes for exact or initial count matches.

    This deliberately proposes class-count conjectures only. It does not infer
    transformations, prove equinumerosity, or rank by an objectwise map.
    ``pair_budget`` bounds candidate-vector comparisons; a hit at that budget
    is explicitly marked as a truncated search.
    """
    from ac.gui.experiments import FAMILY_LIMITS

    if not isinstance(spec, ConjectureSearchSpec):
        raise ValueError("spec must be a ConjectureSearchSpec")
    if type(keep) is not int or not 1 <= keep <= MAX_RESULTS:
        raise ValueError(f"keep must be between 1 and {MAX_RESULTS}")
    if type(minimum_prefix_degrees) is not int or minimum_prefix_degrees < 1:
        raise ValueError("minimum matched prefix must be a positive integer")
    if type(pair_budget) is not int or not 1 <= pair_budget <= MAX_PAIR_CHECKS:
        raise ValueError(f"pair budget must be between 1 and {MAX_PAIR_CHECKS}")

    keys = [
        (mode, pattern.values)
        for length in spec.pattern_lengths
        for pattern in cayley_patterns(length)
        for mode in spec.modes
    ]
    catalogs: dict[tuple[str, int, int], tuple[int, dict[tuple[int, ...], int]]] = {}
    found: dict[tuple[str, str, int, int, int], dict] = {}
    pair_checks = 0
    valid_comparisons = 0
    exact_found = 0
    prefix_found = 0
    budget_exhausted = False

    def remember(item: dict) -> None:
        marker = (
            item["source_class"]["id"], item["target_class"]["id"],
            item["degree_offset"], item["tested_base_degrees"][0], item["tested_base_degrees"][-1],
        )
        found[marker] = item
        buffer_limit = min(MAX_RESULTS * 20, max(keep * 10, 1000))
        if len(found) > buffer_limit * 2:
            best = sorted(found.values(), key=_rank_key, reverse=True)[:buffer_limit]
            found.clear()
            for candidate in best:
                candidate_marker = (
                    candidate["source_class"]["id"], candidate["target_class"]["id"],
                    candidate["degree_offset"], candidate["tested_base_degrees"][0], candidate["tested_base_degrees"][-1],
                )
                found[candidate_marker] = candidate

    family_pairs = [
        (left, right)
        for left_index, left in enumerate(spec.families)
        for right in spec.families[left_index:]
    ]
    for left_family, right_family in family_pairs:
        for offset in spec.offsets:
            pattern_cap = PATTERN_DEGREE_LIMITS[max(spec.pattern_lengths)]
            first_degree = max(spec.degrees.start, 1, 1 - offset)
            last_degree = min(
                spec.degrees.stop,
                FAMILY_LIMITS[left_family],
                pattern_cap,
                FAMILY_LIMITS[right_family] - offset,
                pattern_cap - offset,
            )
            degrees = tuple(range(first_degree, last_degree + 1))
            if len(degrees) < minimum_prefix_degrees:
                continue
            valid_comparisons += 1

            left_vectors: dict[tuple[str, tuple[int, ...]], tuple[int, ...]] = {}
            right_vectors: dict[tuple[str, tuple[int, ...]], tuple[int, ...]] = {}
            for mode, pattern in keys:
                left_vector = tuple(
                    _pattern_class_count(left_family, degree, mode, pattern, catalogs)
                    for degree in degrees
                )
                right_vector = tuple(
                    _pattern_class_count(right_family, degree + offset, mode, pattern, catalogs)
                    for degree in degrees
                )
                if any(left_vector):
                    left_vectors[(mode, pattern)] = left_vector
                if any(right_vector):
                    right_vectors[(mode, pattern)] = right_vector

            left_groups: dict[tuple[int, ...], list[tuple[str, tuple[int, ...]]]] = defaultdict(list)
            right_groups: dict[tuple[int, ...], list[tuple[str, tuple[int, ...]]]] = defaultdict(list)
            for key, vector in left_vectors.items():
                left_groups[vector].append(key)
            for key, vector in right_vectors.items():
                right_groups[vector].append(key)

            pair_seen: set[tuple[tuple[str, tuple[int, ...]], tuple[str, tuple[int, ...]]]] = set()
            for signature in sorted(set(left_groups) & set(right_groups)):
                for left_key in left_groups[signature]:
                    for right_key in right_groups[signature]:
                        if left_family == right_family and offset == 0 and left_key >= right_key:
                            continue
                        pair_checks += 1
                        if pair_checks > pair_budget:
                            budget_exhausted = True
                            break
                        pair_seen.add((left_key, right_key))
                        exact_found += 1
                        remember(_make_candidate(
                            left_family, right_family, left_key, right_key, offset,
                            degrees, left_vectors[left_key], right_vectors[right_key], len(degrees),
                        ))
                    if budget_exhausted:
                        break
                if budget_exhausted:
                    break
            if budget_exhausted:
                break

            for matched_prefix in range(len(degrees) - 1, minimum_prefix_degrees - 1, -1):
                left_prefix_groups: dict[tuple[int, ...], list[tuple[str, tuple[int, ...]]]] = defaultdict(list)
                right_prefix_groups: dict[tuple[int, ...], list[tuple[str, tuple[int, ...]]]] = defaultdict(list)
                for key, vector in left_vectors.items():
                    prefix = vector[:matched_prefix]
                    if any(prefix):
                        left_prefix_groups[prefix].append(key)
                for key, vector in right_vectors.items():
                    prefix = vector[:matched_prefix]
                    if any(prefix):
                        right_prefix_groups[prefix].append(key)
                for prefix in sorted(set(left_prefix_groups) & set(right_prefix_groups)):
                    for left_key in left_prefix_groups[prefix]:
                        for right_key in right_prefix_groups[prefix]:
                            if left_family == right_family and offset == 0 and left_key >= right_key:
                                continue
                            if (left_key, right_key) in pair_seen:
                                continue
                            pair_checks += 1
                            if pair_checks > pair_budget:
                                budget_exhausted = True
                                break
                            pair_seen.add((left_key, right_key))
                            left_vector, right_vector = left_vectors[left_key], right_vectors[right_key]
                            if left_vector == right_vector:
                                continue
                            prefix_found += 1
                            remember(_make_candidate(
                                left_family, right_family, left_key, right_key, offset,
                                degrees, left_vector, right_vector, matched_prefix,
                            ))
                        if budget_exhausted:
                            break
                    if budget_exhausted:
                        break
                if budget_exhausted:
                    break
            if budget_exhausted:
                break
        if budget_exhausted:
            break

    ranked = sorted(found.values(), key=_rank_key, reverse=True)[:keep]
    for rank, item in enumerate(ranked, start=1):
        item["rank"] = rank
    return {
        "search_fingerprint": spec.fingerprint,
        "search_description": spec.describe(),
        "search_status": "budget_exhausted" if budget_exhausted else "completed",
        "interpretation": "finite count evidence only; no bijection or theorem is inferred",
        "tested": {
            "candidate_classes_generated": len(keys) * len(spec.families),
            "family_offset_windows": valid_comparisons,
            "pattern_catalogues": len(catalogs),
            "objects_enumerated_in_catalogues": sum(total for total, _ in catalogs.values()),
            "candidate_pair_checks": min(pair_checks, pair_budget),
            "candidate_pair_budget": pair_budget,
        },
        "exact_match_count_observed": exact_found,
        "prefix_match_count_observed": prefix_found,
        "matches_found_observed": exact_found + prefix_found,
        "matches_truncated_to_keep": exact_found + prefix_found > len(ranked),
        "matches": ranked,
    }


def _make_candidate(left_family, right_family, left_key, right_key, offset, degrees, left_vector, right_vector, matched):
    left_mode, left_pattern = left_key
    right_mode, right_pattern = right_key
    left_spec = ClassSpec.build(left_family, [{"mode": left_mode, "pattern": left_pattern}])
    right_spec = ClassSpec.build(right_family, [{"mode": right_mode, "pattern": right_pattern}])
    exact = matched == len(degrees)
    first_divergence = None if exact else degrees[matched]
    rows = [
        {
            "base_degree": degree,
            "source_degree": degree,
            "source_count": left_count,
            "target_degree": degree + offset,
            "target_count": right_count,
        }
        for degree, left_count, right_count in zip(degrees, left_vector, right_vector)
    ]
    return {
        "evidence": "count_match" if exact else "matching_prefix",
        "status": "verified_through_tested_range" if exact else "refuted_by_counterexample",
        "proof_status": "not_proved",
        "matched_degrees": matched,
        "tested_degrees": len(degrees),
        "matched_through": degrees[matched - 1],
        "first_divergence": first_divergence,
        "tested_base_degrees": list(degrees),
        "degree_offset": offset,
        "source_class": {
            "id": _candidate_id(left_family, left_mode, left_pattern),
            "specification": left_spec.to_dict(),
            "description": left_spec.describe(),
            "family": left_family,
            "rule": {"mode": left_mode, "pattern": list(left_pattern)},
        },
        "target_class": {
            "id": _candidate_id(right_family, right_mode, right_pattern),
            "specification": right_spec.to_dict(),
            "description": right_spec.describe(),
            "family": right_family,
            "rule": {"mode": right_mode, "pattern": list(right_pattern)},
        },
        "degree_rows": rows,
        "counterexample": None if exact else rows[matched],
    }


def run_worker_search(job, context) -> dict:
    """Checkpoint each searched pattern length for the autonomous worker."""
    question = job.question
    if not isinstance(question, ConjectureSearchSpec):
        raise ValueError("discover-pattern-classes requires a ConjectureSearchSpec")
    options = job.options
    keep = options.get("keep", 100)
    minimum_prefix = options.get("minimum_prefix_degrees", 2)
    pair_budget = options.get("pair_budget", MAX_PAIR_CHECKS)
    checkpoint = dict(job.checkpoint)
    next_index = checkpoint.get("next_pattern_index", 0)
    if type(next_index) is not int or next_index < 0:
        raise ValueError("discovery checkpoint has an invalid pattern index")
    all_matches = list(checkpoint.get("matches", []))
    completed_lengths = list(checkpoint.get("completed_pattern_lengths", []))
    budget_exhausted_lengths = list(checkpoint.get("budget_exhausted_pattern_lengths", []))
    summaries = list(checkpoint.get("pattern_length_summaries", []))
    for index in range(next_index, len(question.pattern_lengths)):
        length = question.pattern_lengths[index]
        result = discover_count_conjectures(
            question.for_pattern_length(length),
            keep=keep,
            minimum_prefix_degrees=minimum_prefix,
            pair_budget=pair_budget,
        )
        if result["search_status"] == "budget_exhausted":
            budget_exhausted_lengths.append(length)
        summaries.append({
            "pattern_length": length,
            "search_status": result["search_status"],
            "tested": result["tested"],
            "exact_match_count_observed": result["exact_match_count_observed"],
            "prefix_match_count_observed": result["prefix_match_count_observed"],
            "matches_found_observed": result["matches_found_observed"],
        })
        known = {
            (item["source_class"]["id"], item["target_class"]["id"], item["degree_offset"], tuple(item["tested_base_degrees"]))
            for item in all_matches
        }
        for item in result["matches"]:
            marker = (item["source_class"]["id"], item["target_class"]["id"], item["degree_offset"], tuple(item["tested_base_degrees"]))
            if marker not in known:
                all_matches.append(item)
                known.add(marker)
        completed_lengths.append(length)
        context.checkpoint(
            {
                "next_pattern_index": index + 1,
                "completed_pattern_lengths": completed_lengths,
                "budget_exhausted_pattern_lengths": budget_exhausted_lengths,
                "pattern_length_summaries": summaries,
                "matches": all_matches,
            },
            {"completed_pattern_lengths": completed_lengths, "total_pattern_lengths": len(question.pattern_lengths)},
        )
    all_matches.sort(key=_rank_key, reverse=True)
    all_matches = all_matches[:keep]
    for rank, item in enumerate(all_matches, start=1):
        item["rank"] = rank
    return {
        "search_fingerprint": question.fingerprint,
        "search_description": question.describe(),
        "search_status": "budget_exhausted" if budget_exhausted_lengths else "finite_search_completed",
        "interpretation": "generated class-count conjectures; no transformations or theorems are inferred",
        "completed_pattern_lengths": completed_lengths,
        "budget_exhausted_pattern_lengths": budget_exhausted_lengths,
        "tested": {
            "candidate_classes_generated": sum(item["tested"]["candidate_classes_generated"] for item in summaries),
            "family_offset_windows": sum(item["tested"]["family_offset_windows"] for item in summaries),
            "pattern_catalogues": sum(item["tested"]["pattern_catalogues"] for item in summaries),
            "objects_enumerated_in_catalogues": sum(item["tested"]["objects_enumerated_in_catalogues"] for item in summaries),
            "candidate_pair_checks": sum(item["tested"]["candidate_pair_checks"] for item in summaries),
            "candidate_pair_budget_per_pattern_length": pair_budget,
        },
        "exact_match_count_observed": sum(item["exact_match_count_observed"] for item in summaries),
        "prefix_match_count_observed": sum(item["prefix_match_count_observed"] for item in summaries),
        "matches_found_observed": sum(item["matches_found_observed"] for item in summaries),
        "matches_truncated_to_keep": sum(item["matches_found_observed"] for item in summaries) > len(all_matches),
        "pattern_length_summaries": summaries,
        "matches": all_matches,
    }
