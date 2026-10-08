"""Validate bounded AI proposals for transformation-family experiments.

The model proposes only search inputs.  This module converts them into the
same typed specification used by the deterministic discovery worker; it does
not create transformation programs or certify any mathematical statement.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from ac.discovery.specification import ClassSpec, DegreeWindow
from ac.discovery.transformation_family import (
    MAX_FAMILY_SCENARIOS,
    TransformationFamilySearchSpec,
)
from ac.discovery.transformation_search import TransformationGrammarSpec


EXPERIMENT_DESIGN_SCHEMA_VERSION = 1
EXPERIMENT_DESIGN_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "status", "scope_note", "title", "research_interpretation",
        "assumptions", "experiment",
    ],
    "properties": {
        "status": {"type": "string", "enum": ["plan", "outside_scope"]},
        "scope_note": {"type": "string"},
        "title": {"type": "string"},
        "research_interpretation": {"type": "string"},
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "experiment": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "source_family", "target_family", "rule_mode",
                "source_patterns", "target_patterns", "offset_pairs",
                "degree_start", "degree_stop", "max_cost", "max_steps",
                "candidate_budget",
            ],
            "properties": {
                "source_family": {"type": "string", "enum": ["ordinary", "modified", "revised"]},
                "target_family": {"type": "string", "enum": ["ordinary", "modified", "revised"]},
                "rule_mode": {"type": "string", "enum": ["avoid", "contain"]},
                "source_patterns": {"type": "array", "items": {"type": "string"}},
                "target_patterns": {"type": "array", "items": {"type": "string"}},
                "offset_pairs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["source", "target"],
                        "properties": {"source": {"type": "integer"}, "target": {"type": "integer"}},
                    },
                },
                "degree_start": {"type": "integer"},
                "degree_stop": {"type": "integer"},
                "max_cost": {"type": "integer"},
                "max_steps": {"type": "integer"},
                "candidate_budget": {"type": "integer"},
            },
        },
    },
}


@dataclass(frozen=True)
class ExperimentDesign:
    """A schema-checked response and, for supported plans, its exact spec."""

    status: str
    scope_note: str
    title: str
    research_interpretation: str
    assumptions: tuple[str, ...]
    spec: TransformationFamilySearchSpec | None
    form_values: dict[str, str]


def _text(value: Any, name: str, *, maximum: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be text")
    value = value.strip()
    if (not value and not allow_empty) or len(value) > maximum:
        raise ValueError(f"{name} must contain 1–{maximum} characters")
    return value


def _strict_int(value: Any, name: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer from {low} through {high}")
    return value


def _pattern_list(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not 1 <= len(value) <= 8:
        raise ValueError(f"{name} must contain 1–8 patterns")
    patterns = tuple(_text(item, name, maximum=12) for item in value)
    if len(set(patterns)) != len(patterns):
        raise ValueError(f"{name} must not contain duplicate patterns")
    for pattern in patterns:
        if "," in pattern:
            raise ValueError(f"each {name} item must be one pattern, not a comma-separated list")
    return patterns


def _offset_pairs(value: Any) -> tuple[tuple[int, int], ...]:
    if not isinstance(value, list) or not 1 <= len(value) <= 8:
        raise ValueError("offset_pairs must contain 1–8 pairs")
    pairs = []
    for index, item in enumerate(value):
        if not isinstance(item, dict) or set(item) != {"source", "target"}:
            raise ValueError(f"offset pair {index + 1} must have exactly source and target")
        pairs.append((
            _strict_int(item["source"], f"offset pair {index + 1} source", -10, 10),
            _strict_int(item["target"], f"offset pair {index + 1} target", -10, 10),
        ))
    if len(set(pairs)) != len(pairs):
        raise ValueError("offset_pairs must not contain duplicates")
    return tuple(pairs)


def _pattern_classes(family: str, mode: str, patterns: tuple[str, ...]) -> tuple[ClassSpec, ...]:
    classes = []
    for pattern in patterns:
        classes.append(ClassSpec(family) if pattern == "*" else ClassSpec.build(
            family, [{"mode": mode, "pattern": pattern}],
        ))
    # Repeated mathematical classes (including equivalent pattern spellings)
    # do not create duplicate grid rows.
    by_json = {
        json.dumps(item.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")): item
        for item in classes
    }
    return tuple(by_json[key] for key in sorted(by_json))


def validate_experiment_design(raw: Any) -> ExperimentDesign:
    """Reject anything outside the supported bounded transformation search."""
    if not isinstance(raw, dict):
        raise ValueError("the model response must be a JSON object")
    expected = {
        "status", "scope_note", "title", "research_interpretation",
        "assumptions", "experiment",
    }
    if set(raw) != expected:
        raise ValueError("the model response fields do not match the experiment-design schema")
    status = raw["status"]
    if not isinstance(status, str) or status not in {"plan", "outside_scope"}:
        raise ValueError("status must be plan or outside_scope")
    scope_note = _text(raw["scope_note"], "scope_note", maximum=500)
    title = _text(raw["title"], "title", maximum=120, allow_empty=status == "outside_scope")
    interpretation = _text(raw["research_interpretation"], "research_interpretation", maximum=1200, allow_empty=status == "outside_scope")
    assumptions_raw = raw["assumptions"]
    if not isinstance(assumptions_raw, list) or len(assumptions_raw) > 8:
        raise ValueError("assumptions must be an array of at most 8 short notes")
    assumptions = tuple(_text(item, "assumption", maximum=240) for item in assumptions_raw)
    experiment = raw["experiment"]
    exp_fields = {
        "source_family", "target_family", "rule_mode", "source_patterns",
        "target_patterns", "offset_pairs", "degree_start", "degree_stop",
        "max_cost", "max_steps", "candidate_budget",
    }
    if not isinstance(experiment, dict) or set(experiment) != exp_fields:
        raise ValueError("experiment fields do not match the supported search controls")
    if status == "outside_scope":
        return ExperimentDesign(status, scope_note, title, interpretation, assumptions, None, {})

    source_family = experiment["source_family"]
    target_family = experiment["target_family"]
    rule_mode = experiment["rule_mode"]
    if not isinstance(source_family, str) or source_family not in {"ordinary", "modified", "revised"}:
        raise ValueError("source_family must be ordinary, modified, or revised")
    if not isinstance(target_family, str) or target_family not in {"ordinary", "modified", "revised"}:
        raise ValueError("target_family must be ordinary, modified, or revised")
    if not isinstance(rule_mode, str) or rule_mode not in {"avoid", "contain"}:
        raise ValueError("rule_mode must be avoid or contain")
    source_patterns = _pattern_list(experiment["source_patterns"], "source_patterns")
    target_patterns = _pattern_list(experiment["target_patterns"], "target_patterns")
    offset_pairs = _offset_pairs(experiment["offset_pairs"])
    degree_start = _strict_int(experiment["degree_start"], "degree_start", 1, 20)
    degree_stop = _strict_int(experiment["degree_stop"], "degree_stop", degree_start, 20)
    max_cost = _strict_int(experiment["max_cost"], "max_cost", 0, 8)
    max_steps = _strict_int(experiment["max_steps"], "max_steps", 0, 4)
    candidate_budget = _strict_int(experiment["candidate_budget"], "candidate_budget", 1, 1000)

    source_classes = _pattern_classes(source_family, rule_mode, source_patterns)
    target_classes = _pattern_classes(target_family, rule_mode, target_patterns)
    scenario_count = len(source_classes) * len(target_classes) * len(offset_pairs)
    if not 2 <= scenario_count <= MAX_FAMILY_SCENARIOS:
        raise ValueError(
            f"the design must create 2–{MAX_FAMILY_SCENARIOS} distinct class/offset scenarios; got {scenario_count}"
        )
    grammar = TransformationGrammarSpec(
        max_cost=max_cost,
        max_steps=max_steps,
        candidate_budget=candidate_budget,
        expansion_budget=25_000,
    )
    spec = TransformationFamilySearchSpec.from_grid(
        source_classes,
        target_classes,
        DegreeWindow(degree_start, degree_stop),
        grammar,
        offset_pairs=offset_pairs,
        candidate_budget=candidate_budget,
        enumeration_budget=5_000_000,
        class_object_budget=1_000_000,
        evaluation_budget=10_000_000,
    )
    form_values = {
        "source_family": source_family,
        "target_family": target_family,
        "rule_mode": rule_mode,
        "source_patterns": ", ".join(source_patterns),
        "target_patterns": ", ".join(target_patterns),
        "offsets": ", ".join(f"{source}:{target:+d}" for source, target in offset_pairs),
        "start": str(degree_start),
        "stop": str(degree_stop),
        "max_cost": str(max_cost),
        "max_steps": str(max_steps),
        "candidate_budget": str(candidate_budget),
    }
    return ExperimentDesign(status, scope_note, title, interpretation, assumptions, spec, form_values)


def build_experiment_design_options(
    *,
    question: str,
    endpoint: str,
    model: str,
    response_model: str,
    provider_id: str,
    inference_locality: str,
    requested_at: str,
    completed_at: str,
    system_prompt: str,
    user_prompt: str,
    response_text: str,
    parameters: dict,
    design: ExperimentDesign,
    applied_spec_fingerprint: str,
) -> dict:
    """Build bounded, replayable provenance for the accepted proposal."""
    if design.status != "plan" or design.spec is None:
        raise ValueError("only a validated plan can be attached to a campaign")
    question = _text(question, "question", maximum=2000)
    response_text = _text(response_text, "response_text", maximum=40_000)
    try:
        decoded = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError("response_text must contain valid JSON") from exc
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be an object")
    try:
        json.dumps(parameters, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("parameters must contain finite JSON values") from exc
    if not isinstance(applied_spec_fingerprint, str) or re.fullmatch(r"[0-9a-f]{64}", applied_spec_fingerprint) is None:
        raise ValueError("applied_spec_fingerprint must be a lowercase SHA-256 fingerprint")
    # Keep the exact bounded model response as well as the locally normalized
    # typed spec used by the worker.
    return {
        "experiment_design": {
            "schema_version": EXPERIMENT_DESIGN_SCHEMA_VERSION,
            "verification_status": "unverified model proposal; search specification validated locally",
            "question": question,
            "endpoint": _text(endpoint, "endpoint", maximum=2048),
            "provider_id": _text(provider_id, "provider_id", maximum=64),
            "model": _text(model, "model", maximum=200),
            "response_model": _text(response_model, "response_model", maximum=200),
            "inference_locality": _text(inference_locality, "inference_locality", maximum=16),
            "requested_at": _text(requested_at, "requested_at", maximum=80),
            "completed_at": _text(completed_at, "completed_at", maximum=80),
            "system_prompt": _text(system_prompt, "system_prompt", maximum=6000),
            "user_prompt": _text(user_prompt, "user_prompt", maximum=4000),
            "parameters": dict(parameters),
            "response_text": response_text,
            "response_json": decoded,
            "proposal": {
                "title": design.title,
                "research_interpretation": design.research_interpretation,
                "scope_note": design.scope_note,
                "assumptions": list(design.assumptions),
                "proposed_specification": design.spec.to_dict(),
                "proposed_specification_fingerprint": design.spec.fingerprint,
            },
            "applied_specification_fingerprint": applied_spec_fingerprint,
            "application_status": (
                "used_as_proposed"
                if applied_spec_fingerprint == design.spec.fingerprint
                else "edited_after_proposal"
            ),
        }
    }
