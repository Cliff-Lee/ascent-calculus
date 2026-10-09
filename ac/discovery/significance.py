"""Transparent, deterministic research-priority triage for transformation results.

The score helps researchers choose what to inspect next. It is not a measure
of truth, theorem likelihood, or publication significance.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


PRIORITY_FORMAT = "ascent-machine-research-priority"
PRIORITY_VERSION = 1
PRIORITY_RUBRIC = "am-ai5-priority-v1"
_WEIGHTS = {
    "finite_match_coverage": 40,
    "family_and_offset_breadth": 20,
    "tested_degree_coverage": 15,
    "program_simplicity": 15,
    "research_memory_novelty": 10,
}
_NOVELTY_POINTS = {
    "new_transformation": 10,
    "new_application_of_known_transformation": 8,
    "same_finite_map": 4,
    "same_failure_signature": 2,
    "exact_program_duplicate": 0,
}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _class_signature(class_spec) -> tuple:
    if class_spec is None:
        return ()
    return (
        getattr(class_spec, "family", "unknown"),
        tuple(sorted((rule.mode, tuple(rule.pattern)) for rule in getattr(class_spec, "rules", ()))),
    )


def _scenarios(question) -> tuple:
    scenarios = getattr(question, "scenarios", None)
    if scenarios is not None:
        return tuple(scenarios)
    if getattr(question, "source", None) is not None and getattr(question, "target", None) is not None:
        return (question,)
    return ()


def _novelty_rows(result: dict) -> dict[str, str]:
    memory = result.get("research_memory")
    rows = memory.get("candidates", ()) if isinstance(memory, dict) else ()
    return {
        item["program"]: item["novelty"]
        for item in rows
        if isinstance(item, dict) and isinstance(item.get("program"), str) and isinstance(item.get("novelty"), str)
    }


def _candidate_rows(result: dict) -> tuple[dict, ...]:
    if isinstance(result.get("ranked_candidates"), list):
        groups = (result["ranked_candidates"], result.get("exact_candidates", ()), result.get("near_misses", ()))
    else:
        groups = (result.get("exact_candidates", ()), result.get("near_misses", ()))
    rows = {}
    for group in groups:
        if not isinstance(group, (list, tuple)):
            continue
        for row in group:
            if isinstance(row, dict) and isinstance(row.get("program"), str):
                rows.setdefault(row["program"], row)
    return tuple(rows.values())


def _scenario_plan(question) -> tuple[dict, ...]:
    output = []
    for scenario in _scenarios(question):
        degrees = getattr(scenario, "degrees", None)
        output.append({
            "family_pair": (getattr(getattr(scenario, "source", None), "family", "unknown"), getattr(getattr(scenario, "target", None), "family", "unknown")),
            "offset_pair": (getattr(scenario, "source_offset", 0), getattr(scenario, "target_offset", 0)),
            "start": getattr(degrees, "start", None),
            "stop": getattr(degrees, "stop", None),
        })
    return tuple(output)


def _ratio_points(numerator: int, denominator: int, weight: int) -> int:
    if denominator <= 0:
        return 0
    return round(weight * min(max(numerator / denominator, 0.0), 1.0))


def _review_one(question, row: dict, novelty_label: str | None) -> dict:
    planned = _scenario_plan(question)
    evidence = row.get("scenario_results")
    evidence = evidence if isinstance(evidence, list) else []
    total = row.get("scenario_count")
    if type(total) is not int or total < 1:
        total = len(planned) or len(evidence) or 1
    matched_indices = {
        item.get("scenario_index")
        for item in evidence
        if isinstance(item, dict) and type(item.get("scenario_index")) is int and item.get("finite_match") is True
    }
    if evidence:
        matches = sum(1 for item in evidence if isinstance(item, dict) and item.get("finite_match") is True)
        support_known = True
    else:
        matches = row.get("matching_scenario_count", 0)
        support_known = type(matches) is int and matches >= 0
        matches = matches if support_known else 0
    matches = min(matches, total)
    support_points = _ratio_points(matches, total, _WEIGHTS["finite_match_coverage"])

    family_keys = {item["family_pair"] for item in planned}
    offset_keys = {item["offset_pair"] for item in planned}
    matched_family_keys = set()
    matched_offset_keys = set()
    for index in matched_indices:
        if 0 <= index < len(planned):
            matched_family_keys.add(planned[index]["family_pair"])
            matched_offset_keys.add(planned[index]["offset_pair"])
    breadth_known = bool(planned) and bool(evidence)
    breadth_points = 0
    if breadth_known:
        family_points = _ratio_points(len(matched_family_keys), len(family_keys), 10)
        offset_points = _ratio_points(len(matched_offset_keys), len(offset_keys), 10)
        breadth_points = family_points + offset_points

    degree_ratios = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        index = item.get("scenario_index")
        through = item.get("verified_through")
        if type(index) is not int or not 0 <= index < len(planned) or type(through) is not int:
            continue
        window = planned[index]
        start, stop = window["start"], window["stop"]
        if type(start) is int and type(stop) is int and stop >= start:
            checked = min(max(through - start + 1, 0), stop - start + 1)
            degree_ratios.append(checked / (stop - start + 1))
    degree_known = bool(degree_ratios)
    degree_points = round(_WEIGHTS["tested_degree_coverage"] * (sum(degree_ratios) / len(degree_ratios))) if degree_known else 0

    cost = row.get("cost")
    grammar = getattr(question, "grammar", None)
    max_cost = getattr(grammar, "max_cost", None)
    simplicity_known = type(cost) is int and cost >= 0 and type(max_cost) is int and max_cost >= 0
    if simplicity_known:
        simplicity_points = _WEIGHTS["program_simplicity"] if max_cost == 0 else round(
            _WEIGHTS["program_simplicity"] * max(0.0, 1 - min(cost, max_cost) / max_cost)
        )
    else:
        simplicity_points = 0

    novelty_known = novelty_label in _NOVELTY_POINTS
    novelty_points = _NOVELTY_POINTS.get(novelty_label, 0)
    points = {
        "finite_match_coverage": support_points,
        "family_and_offset_breadth": breadth_points,
        "tested_degree_coverage": degree_points,
        "program_simplicity": simplicity_points,
        "research_memory_novelty": novelty_points,
    }
    known = {
        "finite_match_coverage": support_known,
        "family_and_offset_breadth": breadth_known,
        "tested_degree_coverage": degree_known,
        "program_simplicity": simplicity_known,
        "research_memory_novelty": novelty_known,
    }
    observed_weight = sum(_WEIGHTS[key] for key, available in known.items() if available)
    score = sum(points[key] for key, available in known.items() if available)
    confidence = "high" if observed_weight >= 100 and len(evidence) >= total else (
        "medium" if observed_weight >= 75 else "low"
    )

    components = {
        key: {
            "points": points[key] if known[key] else None,
            "weight": _WEIGHTS[key],
            "available": known[key],
        }
        for key in _WEIGHTS
    }
    reasons = []
    if support_known:
        reasons.append(f"Matches {matches}/{total} selected scenarios in the finite check.")
    if breadth_known:
        reasons.append(f"Matches {len(matched_family_keys)}/{len(family_keys)} family pairs and {len(matched_offset_keys)}/{len(offset_keys)} distinct offset pairs.")
    if degree_known:
        highest = max((item.get("verified_through", 0) for item in evidence if isinstance(item, dict)), default=0)
        reasons.append(f"The recorded checks reach reference degree n={highest} at most.")
    if simplicity_known:
        reasons.append(f"Transformation cost is {cost} of the configured maximum {max_cost}.")
    if novelty_known:
        reasons.append(f"Research memory classifies this as {novelty_label.replace('_', ' ')}.")

    uncertainties = [
        "The score is a transparent triage heuristic; it is not a probability of truth or a measure of publication value.",
        "Every match is limited to the listed finite degrees and classes; it does not prove an all-degree transformation.",
    ]
    if not novelty_known:
        uncertainties.append("No stored research-memory comparison is available for this candidate yet.")
    if not breadth_known or not degree_known:
        uncertainties.append("Some scenario-level data needed for breadth or degree coverage is missing.")
    if confidence != "high":
        uncertainties.append("The priority score has incomplete inputs; inspect its component availability before comparing candidates.")
    return {
        "program": row["program"],
        "priority_score": score,
        "confidence_in_score_inputs": confidence,
        "observed_weight": observed_weight,
        "possible_weight": sum(_WEIGHTS.values()),
        "novelty_classification": novelty_label or "not_recorded",
        "components": components,
        "reasons": reasons,
        "uncertainties": uncertainties,
    }


def build_research_priority_review(question, result: dict | None) -> dict | None:
    """Create a reproducible ranked review from a deterministic search result."""
    if not isinstance(result, dict):
        return None
    rows = _candidate_rows(result)
    if not rows:
        return None
    novelty = _novelty_rows(result)
    reviews = [_review_one(question, row, novelty.get(row["program"])) for row in rows]
    cost_by_program = {row["program"]: row.get("cost", 0) for row in rows}
    reviews.sort(key=lambda item: (-item["priority_score"], cost_by_program.get(item["program"], 0), item["program"]))
    return {
        "format": PRIORITY_FORMAT,
        "version": PRIORITY_VERSION,
        "rubric": PRIORITY_RUBRIC,
        "scope_fingerprint": getattr(question, "fingerprint", None),
        "interpretation": (
            "Research triage only. The score summarizes finite match coverage, tested class/offset breadth, "
            "degree coverage, program cost, and recorded memory novelty; it does not establish truth or significance."
        ),
        "weights": dict(_WEIGHTS),
        "ranked_candidates": reviews,
    }
