"""Independent structural fingerprints and feature profiles for AC words."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from typing import Iterable

from ac.classes.theories import is_ascent_sequence, is_modified, is_revised
from ac.core.word import ChainWord
from ac.discovery.specification import ClassSpec
from ac.discovery.specification import SEMANTICS_VERSION


FINGERPRINT_FORMAT = "ascent-machine-structural-fingerprint"
FINGERPRINT_VERSION = 1

FEATURE_LABELS = {
    "new_positions": "New positions (first appearances)",
    "asctop_positions": "Ascent-top positions",
    "ascbot_positions": "Ascent-bottom positions",
    "new_count": "Number of new positions",
    "asctop_count": "Number of ascent tops",
    "ascbot_count": "Number of ascent bottoms",
    "new_asctop_overlap": "New positions that are ascent tops",
    "new_ascbot_overlap": "New positions that are ascent bottoms",
    "new_only_count": "New positions that are not ascent tops",
    "asctop_only_count": "Ascent tops that are not new positions",
    "edge_word": "Adjacent edge directions",
    "ascent_count": "Number of adjacent rises",
    "descent_count": "Number of adjacent descents",
    "equal_edge_count": "Number of equal adjacent values",
    "ascent_run_lengths": "Lengths of increasing runs",
    "multiplicity_profile": "Value multiplicities in value order",
    "multiplicity_partition": "Multiplicities sorted by size",
    "distinct_value_count": "Number of used values",
    "repeated_value_count": "Number of repeated values",
    "first_last_overlap": "Values whose first and last occurrence coincide",
    "new_value_order": "Values in order of first appearance",
    "fibre_gap_profile": "Occurrence gaps for each value",
    "fibre_span_profile": "First-to-last span for each value",
}

DEFAULT_FEATURES = (
    "new_positions",
    "asctop_positions",
    "ascbot_positions",
    "new_count",
    "asctop_count",
    "ascbot_count",
    "new_asctop_overlap",
    "new_ascbot_overlap",
    "new_only_count",
    "asctop_only_count",
    "edge_word",
    "ascent_count",
    "descent_count",
    "equal_edge_count",
    "ascent_run_lengths",
    "multiplicity_profile",
    "multiplicity_partition",
    "fibre_gap_profile",
    "fibre_span_profile",
)


def _values_and_height(word: ChainWord | Iterable[int]) -> tuple[tuple[int, ...], int]:
    if isinstance(word, ChainWord):
        return word.values, word.height
    values = tuple(word)
    if any(type(value) is not int or value < 1 for value in values):
        raise ValueError("structural fingerprints require positive integer values")
    return values, max(values, default=0)


def structural_features(word: ChainWord | Iterable[int]) -> dict[str, object]:
    """Calculate named structural data directly from the value tuple.

    This intentionally does not call ``ChainWord``'s cached role sets. It is a
    second implementation of new positions and the literature top/bottom
    conventions, suitable for cross-checking the production engine.
    """
    values, height = _values_and_height(word)
    positions_by_value: dict[int, list[int]] = {value: [] for value in range(1, height + 1)}
    first: dict[int, int] = {}
    last: dict[int, int] = {}
    new_value_order: list[int] = []
    for position, value in enumerate(values, start=1):
        if value not in positions_by_value:
            raise ValueError("ambient height is smaller than a value")
        positions_by_value[value].append(position)
        if value not in first:
            first[value] = position
            new_value_order.append(value)
        last[value] = position

    new_positions = frozenset(first.values())
    asctop_positions = {1} if values else set()
    ascbot_positions = {1} if values else set()
    edge_directions: list[str] = []
    ascent_count = descent_count = equal_edge_count = 0
    ascent_run_lengths: list[int] = []
    current_run_length = 1 if values else 0
    for index, (left, right) in enumerate(zip(values, values[1:]), start=1):
        if left < right:
            edge_directions.append("U")
            ascent_count += 1
            asctop_positions.add(index + 1)
            ascbot_positions.add(index)
            current_run_length += 1
        else:
            if left > right:
                edge_directions.append("D")
                descent_count += 1
            else:
                edge_directions.append("E")
                equal_edge_count += 1
            if current_run_length:
                ascent_run_lengths.append(current_run_length)
            current_run_length = 1
    if current_run_length:
        ascent_run_lengths.append(current_run_length)

    multiplicities = tuple(len(positions_by_value[value]) for value in range(1, height + 1))
    used_multiplicities = tuple(count for count in multiplicities if count)
    first_last_overlap = tuple(
        value for value in range(1, height + 1)
        if value in first and first[value] == last[value]
    )
    fibre_gaps = tuple(
        (value, tuple(right - left - 1 for left, right in zip(positions_by_value[value], positions_by_value[value][1:])))
        for value in range(1, height + 1) if positions_by_value[value]
    )
    fibre_spans = tuple(
        (value, positions_by_value[value][-1] - positions_by_value[value][0])
        for value in range(1, height + 1) if positions_by_value[value]
    )
    top = frozenset(asctop_positions)
    bottom = frozenset(ascbot_positions)
    return {
        "new_positions": tuple(sorted(new_positions)),
        "asctop_positions": tuple(sorted(top)),
        "ascbot_positions": tuple(sorted(bottom)),
        "new_count": len(new_positions),
        "asctop_count": len(top),
        "ascbot_count": len(bottom),
        "new_asctop_overlap": tuple(sorted(new_positions & top)),
        "new_ascbot_overlap": tuple(sorted(new_positions & bottom)),
        "new_only_count": len(new_positions - top),
        "asctop_only_count": len(top - new_positions),
        "edge_word": "".join(edge_directions),
        "ascent_count": ascent_count,
        "descent_count": descent_count,
        "equal_edge_count": equal_edge_count,
        "ascent_run_lengths": tuple(ascent_run_lengths),
        "multiplicity_profile": multiplicities,
        "multiplicity_partition": tuple(sorted(used_multiplicities, reverse=True)),
        "distinct_value_count": len(used_multiplicities),
        "repeated_value_count": sum(count > 1 for count in used_multiplicities),
        "first_last_overlap": first_last_overlap,
        "new_value_order": tuple(new_value_order),
        "fibre_gap_profile": fibre_gaps,
        "fibre_span_profile": fibre_spans,
    }


def _json_value(value):
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def _canonical_value(value) -> str:
    return json.dumps(_json_value(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def structural_fingerprint(word: ChainWord | Iterable[int]) -> dict:
    """Return a readable role trace and stable structural SHA-256 digest."""
    if not isinstance(word, ChainWord):
        values, height = _values_and_height(word)
        word = ChainWord(values, height=height)
    features = structural_features(word)
    core = {
        "semantics": SEMANTICS_VERSION,
        "degree": len(word),
        "height": word.height,
        "features": _json_value(features),
    }
    encoded = json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    new = set(features["new_positions"])
    tops = set(features["asctop_positions"])
    bottoms = set(features["ascbot_positions"])
    return {
        "format": FINGERPRINT_FORMAT,
        "version": FINGERPRINT_VERSION,
        "degree": len(word),
        "height": word.height,
        "values": list(word.values),
        "sha256": sha256(encoded.encode("utf-8")).hexdigest(),
        "features": _json_value(features),
        "positions": [
            {
                "position": position,
                "value": value,
                "new": position in new,
                "asctop": position in tops,
                "ascbot": position in bottoms,
            }
            for position, value in enumerate(word.values, start=1)
        ],
        "classification": {
            "ordinary": is_ascent_sequence(word),
            "modified": is_modified(word),
            "revised": is_revised(word),
        },
    }


def _family_generator(family: str):
    if family == "ordinary":
        from ac.generate.universes import ascent_sequences
        return ascent_sequences
    if family == "modified":
        from ac.generate.universes import modified_via_hat
        return modified_via_hat
    if family == "revised":
        from ac.generate.universes import revised_sequences
        return revised_sequences
    raise ValueError(f"unsupported sequence family: {family}")


def _checked_features(features: Iterable[str]) -> tuple[str, ...]:
    names = tuple(features)
    if not names or any(name not in FEATURE_LABELS for name in names):
        raise ValueError("choose one or more registered structural features")
    if len(set(names)) != len(names):
        raise ValueError("structural feature names must be unique")
    return names


def class_structural_profile(
    class_spec: ClassSpec,
    degree: int,
    *,
    features: Iterable[str] = DEFAULT_FEATURES,
    joint_features: Iterable[tuple[str, ...]] = (),
    max_profile_values: int = 200_000,
) -> dict:
    """Count exact feature distributions in one generated class and degree."""
    from ac.gui.experiments import FAMILY_LIMITS

    if not isinstance(class_spec, ClassSpec):
        raise ValueError("class profile requires a ClassSpec")
    if type(degree) is not int or degree < 1:
        raise ValueError("degree must be a positive integer")
    if degree > FAMILY_LIMITS[class_spec.family]:
        raise ValueError(f"{class_spec.family} generation is currently bounded to degree {FAMILY_LIMITS[class_spec.family]}")
    if type(max_profile_values) is not int or not 1 <= max_profile_values <= 2_000_000:
        raise ValueError("max_profile_values must be between 1 and 2000000")
    names = _checked_features(features)
    joint_specs = tuple(sorted(tuple(sorted(group)) for group in joint_features))
    if len(joint_specs) > 6 or any(not 2 <= len(group) <= 3 or any(name not in names for name in group) for group in joint_specs):
        raise ValueError("choose at most six joint profiles, each combining two or three selected features")
    if len(set(joint_specs)) != len(joint_specs):
        raise ValueError("joint feature groups must be unique")

    predicate = class_spec.predicate()
    counters = {name: Counter() for name in names}
    examples: dict[str, dict[str, tuple[int, ...]]] = {name: {} for name in names}
    joint_counters = {group: Counter() for group in joint_specs}
    joint_examples: dict[tuple[str, ...], dict[str, tuple[int, ...]]] = {group: {} for group in joint_specs}
    count = 0
    unique_profile_values = 0
    for word in _family_generator(class_spec.family)(degree):
        if not predicate.holds(word):
            continue
        count += 1
        values = structural_features(word)
        for name in names:
            value = values[name]
            key = _canonical_value(value)
            if value not in counters[name]:
                unique_profile_values += 1
                if unique_profile_values > max_profile_values:
                    raise ValueError(
                        f"structural profile exceeded its {max_profile_values} distinct-value budget; "
                        "select fewer features or a smaller degree"
                    )
            counters[name][value] += 1
            examples[name].setdefault(key, word.values)
        for group in joint_specs:
            value = tuple(values[name] for name in group)
            key = _canonical_value(value)
            if value not in joint_counters[group]:
                unique_profile_values += 1
                if unique_profile_values > max_profile_values:
                    raise ValueError(
                        f"structural profile exceeded its {max_profile_values} distinct-value budget; "
                        "select fewer features or a smaller degree"
                    )
            joint_counters[group][value] += 1
            joint_examples[group].setdefault(key, word.values)

    def rows_for(counter: Counter, examples_by_value: dict[str, tuple[int, ...]]) -> list[dict]:
        rows = []
        for value, frequency in sorted(counter.items(), key=lambda pair: _canonical_value(pair[0])):
            rows.append({
                "value": _json_value(value),
                "count": frequency,
                "example_word": list(examples_by_value[_canonical_value(value)]),
            })
        return rows

    return {
        "class": class_spec.to_dict(),
        "class_description": class_spec.describe(),
        "degree": degree,
        "count": count,
        "distinct_profile_values": unique_profile_values,
        "max_profile_values": max_profile_values,
        "features": {
            name: {"label": FEATURE_LABELS[name], "distribution": rows_for(counters[name], examples[name])}
            for name in names
        },
        "joint_features": {
            "+".join(group): {
                "members": list(group),
                "distribution": rows_for(joint_counters[group], joint_examples[group]),
            }
            for group in joint_specs
        },
    }


def compare_structural_profiles(left: dict, right: dict) -> dict:
    """Explain which structural profiles match and show sample witnesses."""
    if left.get("degree") is None or right.get("degree") is None:
        raise ValueError("both structural profiles must include a degree")
    left_features, right_features = left.get("features", {}), right.get("features", {})
    common = tuple(name for name in left_features if name in right_features)
    if not common:
        raise ValueError("structural profiles have no common features")

    def compare_distribution(left_rows, right_rows):
        lmap = {_canonical_value(row["value"]): row for row in left_rows}
        rmap = {_canonical_value(row["value"]): row for row in right_rows}
        keys = sorted(set(lmap) | set(rmap))
        changes = [
            {
                "value": (lmap.get(key) or rmap[key])["value"],
                "left_count": lmap[key]["count"] if key in lmap else 0,
                "right_count": rmap[key]["count"] if key in rmap else 0,
                "left_example": lmap[key]["example_word"] if key in lmap else None,
                "right_example": rmap[key]["example_word"] if key in rmap else None,
            }
            for key in keys
            if (lmap[key]["count"] if key in lmap else 0) != (rmap[key]["count"] if key in rmap else 0)
        ]
        difference_mass = sum(abs(row["left_count"] - row["right_count"]) for row in changes)
        return changes, difference_mass

    feature_rows = []
    for name in common:
        changes, difference_mass = compare_distribution(
            left_features[name]["distribution"], right_features[name]["distribution"]
        )
        feature_rows.append({
            "feature": name,
            "label": left_features[name]["label"],
            "equal": difference_mass == 0,
            "difference_mass": difference_mass,
            "changed_values": len(changes),
            "examples": changes[:5],
        })
    feature_rows.sort(key=lambda row: (row["equal"], -row["difference_mass"], -row["changed_values"], row["feature"]))

    left_joint, right_joint = left.get("joint_features", {}), right.get("joint_features", {})
    joint_rows = []
    for name in left_joint.keys() & right_joint.keys():
        changes, difference_mass = compare_distribution(
            left_joint[name]["distribution"], right_joint[name]["distribution"]
        )
        joint_rows.append({
            "features": left_joint[name]["members"],
            "label": " and ".join(FEATURE_LABELS[feature] for feature in left_joint[name]["members"]),
            "equal": difference_mass == 0,
            "difference_mass": difference_mass,
            "changed_values": len(changes),
            "examples": changes[:5],
        })
    joint_rows.sort(key=lambda row: (row["equal"], -row["difference_mass"], -row["changed_values"], row["features"]))
    return {
        "source_degree": left["degree"],
        "target_degree": right["degree"],
        "source_class": left["class"],
        "target_class": right["class"],
        "source_count": left["count"],
        "target_count": right["count"],
        "class_counts_equal": left["count"] == right["count"],
        "feature_profiles": feature_rows,
        "joint_profiles": joint_rows,
        "interpretation": "equal feature distributions are necessary evidence for preserving those features, not evidence of an objectwise bijection",
    }


def analyze_count_match_structure(
    match: dict,
    *,
    features: Iterable[str] = DEFAULT_FEATURES,
    joint_features: Iterable[tuple[str, ...]] = (),
) -> dict:
    """Attach role/invariant profile comparisons to a bounded count candidate."""
    try:
        source = ClassSpec.from_dict(match["source_class"]["specification"])
        target = ClassSpec.from_dict(match["target_class"]["specification"])
        rows = match["degree_rows"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"match record is missing exact class/count data: {exc}") from exc
    comparisons = []
    first_feature_mismatch: dict[str, int] = {}
    for row in rows:
        left = class_structural_profile(
            source, row["source_degree"], features=features, joint_features=joint_features
        )
        right = class_structural_profile(
            target, row["target_degree"], features=features, joint_features=joint_features
        )
        comparison = compare_structural_profiles(left, right)
        comparison["base_degree"] = row["base_degree"]
        comparison["count_match"] = row["source_count"] == row["target_count"]
        for feature in comparison["feature_profiles"]:
            if not feature["equal"]:
                first_feature_mismatch.setdefault(feature["feature"], row["base_degree"])
        comparisons.append(comparison)
    feature_summary = []
    names = _checked_features(features)
    for name in names:
        mismatch_at = first_feature_mismatch.get(name)
        feature_summary.append({
            "feature": name,
            "label": FEATURE_LABELS[name],
            "equal_through": rows[-1]["base_degree"] if mismatch_at is None and rows else (rows[0]["base_degree"] - 1 if rows else None),
            "first_mismatch": mismatch_at,
        })
    feature_summary.sort(key=lambda row: (row["first_mismatch"] is None, row["first_mismatch"] or 0, row["feature"]))
    return {
        "candidate_evidence": match.get("evidence"),
        "candidate_proof_status": match.get("proof_status", "not_proved"),
        "source_class": source.to_dict(),
        "target_class": target.to_dict(),
        "degree_offset": match.get("degree_offset"),
        "tested_base_degrees": [row["base_degree"] for row in rows],
        "feature_summary": feature_summary,
        "degree_comparisons": comparisons,
        "explanation": "The profiles describe which structural data could be transported by a map; profile agreement does not construct or prove a bijection.",
    }


def run_structural_profile_analysis(job, context) -> dict:
    """Checkpoint exact source/target structural profiles by base degree."""
    from ac.discovery.specification import SearchSpec

    spec = job.spec
    if not isinstance(spec, SearchSpec) or spec.target is None or spec.goal == "enumerate":
        raise ValueError("structural profile analysis requires a two-class SearchSpec")
    raw_features = job.options.get("features", list(DEFAULT_FEATURES))
    raw_joint = job.options.get("joint_features", [])
    if not isinstance(raw_features, list) or not isinstance(raw_joint, list):
        raise ValueError("features and joint_features options must be arrays")
    features = _checked_features(raw_features)
    joint_features = tuple(tuple(group) for group in raw_joint if isinstance(group, list))
    if len(joint_features) != len(raw_joint):
        raise ValueError("each joint feature group must be an array")

    checkpoint = dict(job.checkpoint)
    rows = list(checkpoint.get("rows", []))
    next_base = checkpoint.get("next_base_degree", spec.degrees.start)
    if type(next_base) is not int:
        raise ValueError("structural-analysis checkpoint has an invalid next degree")
    first_mismatch: dict[str, int] = {}
    max_profile_values = job.options.get("max_profile_values", 200_000)
    if type(max_profile_values) is not int or not 1 <= max_profile_values <= 2_000_000:
        raise ValueError("max_profile_values must be between 1 and 2000000")
    for row in rows:
        for feature in row.get("feature_profiles", []):
            if not feature["equal"]:
                first_mismatch.setdefault(feature["feature"], row["base_degree"])

    for base_degree in range(max(spec.degrees.start, next_base), spec.degrees.stop + 1):
        source_degree, target_degree = spec.degrees_for(base_degree)
        left = class_structural_profile(
            spec.source, source_degree, features=features, joint_features=joint_features,
            max_profile_values=max_profile_values,
        )
        right = class_structural_profile(
            spec.target, target_degree, features=features, joint_features=joint_features,
            max_profile_values=max_profile_values,
        )
        comparison = compare_structural_profiles(left, right)
        comparison["base_degree"] = base_degree
        comparison["count_match"] = comparison["source_count"] == comparison["target_count"]
        rows = [row for row in rows if row["base_degree"] != base_degree]
        rows.append(comparison)
        rows.sort(key=lambda row: row["base_degree"])
        for feature in comparison["feature_profiles"]:
            if not feature["equal"]:
                first_mismatch.setdefault(feature["feature"], base_degree)
        context.checkpoint(
            {"next_base_degree": base_degree + 1, "rows": rows},
            {"completed_degrees": len(rows), "total_degrees": spec.degrees.stop - spec.degrees.start + 1,
             "current_base_degree": base_degree},
        )

    feature_summary = [
        {
            "feature": name,
            "label": FEATURE_LABELS[name],
            "first_mismatch": first_mismatch.get(name),
            "equal_through": (first_mismatch[name] - 1) if name in first_mismatch else spec.degrees.stop,
        }
        for name in features
    ]
    feature_summary.sort(key=lambda row: (row["first_mismatch"] is None, row["first_mismatch"] or 0, row["feature"]))
    return {
        "spec_fingerprint": spec.fingerprint,
        "status": "finite_structural_profile_analysis",
        "proof_status": "not_proved",
        "feature_summary": feature_summary,
        "rows": rows,
        "interpretation": "feature-profile agreement is not an objectwise map or proof; finite disagreements show only that a feature is not preserved on these classes and bounds",
    }

