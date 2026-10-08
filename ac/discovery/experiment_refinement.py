"""Counterexample-guided design of a follow-up bounded experiment.

This module records finite engine failures as evidence for a *new search plan*.
It never edits a candidate transformation or certifies that a proposed change
repairs it.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

from ac.discovery.experiment_design import (
    EXPERIMENT_DESIGN_JSON_SCHEMA,
    ExperimentDesign,
    build_experiment_design_options,
    validate_experiment_design,
)
from ac.discovery.transformation_family import TransformationFamilySearchSpec


EXPERIMENT_REFINEMENT_SCHEMA_VERSION = 1
EXPERIMENT_REFINEMENT_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["design", "counterexample_analysis"],
    "properties": {
        "design": EXPERIMENT_DESIGN_JSON_SCHEMA,
        "counterexample_analysis": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "referenced_scenario_indices", "evidence_interpretation", "proposed_change",
            ],
            "properties": {
                "referenced_scenario_indices": {
                    "type": "array",
                    "items": {"type": "integer"},
                },
                "evidence_interpretation": {"type": "string"},
                "proposed_change": {"type": "string"},
            },
        },
    },
}


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("refinement evidence must contain finite JSON values") from exc


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _bounded_text(value: Any, name: str, maximum: int, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be text")
    value = value.strip()
    if len(value) > maximum or (not value and not allow_empty):
        raise ValueError(f"{name} must contain 1–{maximum} characters")
    return value


def _failure_record(item: dict, position: int) -> dict | None:
    evaluation = item.get("evaluation")
    if not isinstance(evaluation, dict):
        return None
    failure = evaluation.get("first_failure") or evaluation.get("counterexample")
    if not isinstance(failure, dict):
        return None
    scenario_index = item.get("scenario_index", position)
    if type(scenario_index) is not int or scenario_index < 0:
        raise ValueError("failure scenario index must be a nonnegative integer")
    safe_failure = {}
    for key in ("kind", "base_degree", "source_degree", "target_degree", "source", "other_source", "output"):
        if key in failure:
            safe_failure[key] = failure[key]
    if "kind" not in safe_failure or "base_degree" not in safe_failure:
        raise ValueError("engine failure evidence needs a kind and base degree")
    if failure.get("detail") is not None:
        safe_failure["detail"] = str(failure["detail"])[:500]
    return {
        "scenario_index": scenario_index,
        "scenario_fingerprint": item.get("specification_fingerprint"),
        "source_class": item.get("source_class"),
        "target_class": item.get("target_class"),
        "source_offset": item.get("source_offset"),
        "target_offset": item.get("target_offset"),
        "verified_through": item.get("verified_through"),
        "failure": safe_failure,
    }


def build_refinement_context(
    *,
    parent_job_id: str,
    prior_specification: dict,
    prior_specification_fingerprint: str,
    candidate: dict,
    witness_limit: int = 8,
) -> dict:
    """Build a small exact packet of parent search, candidate, and failures."""
    parent_job_id = _bounded_text(parent_job_id, "parent_job_id", 128)
    if not isinstance(prior_specification, dict):
        raise ValueError("prior_specification must be an object")
    _canonical(prior_specification)
    if not isinstance(prior_specification_fingerprint, str) or len(prior_specification_fingerprint) != 64:
        raise ValueError("prior_specification_fingerprint must be a SHA-256 fingerprint")
    if prior_specification_fingerprint != _fingerprint(prior_specification):
        raise ValueError("prior specification fingerprint does not match its exact contents")
    if type(witness_limit) is not int or not 1 <= witness_limit <= 16:
        raise ValueError("witness_limit must be from 1 through 16")
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be an object")
    program = _bounded_text(candidate.get("program"), "candidate program", 1000)
    scenario_results = candidate.get("scenario_results")
    if not isinstance(scenario_results, (list, tuple)):
        raise ValueError("candidate scenario results must be a list")
    failures = []
    for position, item in enumerate(scenario_results):
        if not isinstance(item, dict):
            continue
        row = _failure_record(item, position)
        if row is not None:
            failures.append(row)
    if not failures:
        raise ValueError("the selected candidate has no recorded engine failure to refine from")
    included = failures[:witness_limit]
    candidate_identity = {
        "parent_specification_fingerprint": prior_specification_fingerprint,
        "program": program,
        "cost": candidate.get("cost"),
        "scenario_count": candidate.get("scenario_count"),
        "matching_scenario_count": candidate.get("matching_scenario_count"),
        "failure_evidence": included,
    }
    context = {
        "schema_version": EXPERIMENT_REFINEMENT_SCHEMA_VERSION,
        "parent_job_id": parent_job_id,
        "prior_specification": prior_specification,
        "prior_specification_fingerprint": prior_specification_fingerprint,
        "candidate": {
            "program": program,
            "cost": candidate.get("cost"),
            "scenario_count": candidate.get("scenario_count"),
            "matching_scenario_count": candidate.get("matching_scenario_count"),
            "failure_evidence": included,
            "omitted_failure_count": len(failures) - len(included),
            "candidate_fingerprint": _fingerprint(candidate_identity),
        },
    }
    context["counterexample_evidence_fingerprint"] = _fingerprint(included)
    return validate_refinement_context(context)


def validate_refinement_context(context: Any) -> dict:
    """Check the bounded context and its evidence fingerprints before use."""
    required = {
        "schema_version", "parent_job_id", "prior_specification",
        "prior_specification_fingerprint", "candidate", "counterexample_evidence_fingerprint",
    }
    if not isinstance(context, dict) or set(context) != required:
        raise ValueError("refinement context does not match the version-1 schema")
    if type(context["schema_version"]) is not int or context["schema_version"] != EXPERIMENT_REFINEMENT_SCHEMA_VERSION:
        raise ValueError("unsupported refinement context version")
    parent_job_id = _bounded_text(context["parent_job_id"], "parent_job_id", 128)
    prior_spec = context["prior_specification"]
    if not isinstance(prior_spec, dict):
        raise ValueError("prior specification must be an object")
    _canonical(prior_spec)
    try:
        parent_search = TransformationFamilySearchSpec.from_dict(prior_spec)
    except (TypeError, ValueError, KeyError) as exc:
        raise ValueError("parent specification is not a supported transformation-family search") from exc
    prior_fingerprint = context["prior_specification_fingerprint"]
    if not isinstance(prior_fingerprint, str) or len(prior_fingerprint) != 64 or any(char not in "0123456789abcdef" for char in prior_fingerprint):
        raise ValueError("prior specification fingerprint is invalid")
    if prior_fingerprint != _fingerprint(prior_spec):
        raise ValueError("prior specification fingerprint does not match its exact contents")
    candidate = context["candidate"]
    expected_candidate = {
        "program", "cost", "scenario_count", "matching_scenario_count",
        "failure_evidence", "omitted_failure_count", "candidate_fingerprint",
    }
    if not isinstance(candidate, dict) or set(candidate) != expected_candidate:
        raise ValueError("parent candidate record does not match the version-1 schema")
    program = _bounded_text(candidate["program"], "candidate program", 1000)
    evidence = candidate["failure_evidence"]
    if not isinstance(evidence, list) or not 1 <= len(evidence) <= 16:
        raise ValueError("refinement needs 1–16 exact engine failure records")
    indices = []
    for row in evidence:
        if not isinstance(row, dict) or set(row) != {
            "scenario_index", "scenario_fingerprint", "source_class", "target_class",
            "source_offset", "target_offset", "verified_through", "failure",
        }:
            raise ValueError("failure record fields are invalid")
        index = row["scenario_index"]
        if type(index) is not int or index < 0 or index in indices:
            raise ValueError("failure scenario indices must be distinct nonnegative integers")
        indices.append(index)
        scenario_fingerprint = row["scenario_fingerprint"]
        if not isinstance(scenario_fingerprint, str) or len(scenario_fingerprint) != 64 or any(char not in "0123456789abcdef" for char in scenario_fingerprint):
            raise ValueError("failure scenario fingerprint is invalid")
        for name in ("source_class", "target_class"):
            _bounded_text(row[name], name, 1000)
        for name in ("source_offset", "target_offset", "verified_through"):
            if type(row[name]) is not int:
                raise ValueError(f"failure {name} must be an integer")
        if index >= len(parent_search.scenarios):
            raise ValueError("failure scenario index is outside the parent search grid")
        expected_scenario = parent_search.scenarios[index]
        if (
            scenario_fingerprint != expected_scenario.fingerprint
            or row["source_class"] != expected_scenario.source.describe()
            or row["target_class"] != expected_scenario.target.describe()
            or row["source_offset"] != expected_scenario.source_offset
            or row["target_offset"] != expected_scenario.target_offset
        ):
            raise ValueError("failure scenario details do not match the parent specification")
        failure = row["failure"]
        if (
            not isinstance(failure, dict)
            or not isinstance(failure.get("kind"), str)
            or not failure["kind"].strip()
            or type(failure.get("base_degree")) is not int
        ):
            raise ValueError("failure witness is missing its engine kind or degree")
        for name in ("source", "other_source", "output"):
            word = failure.get(name)
            if word is None:
                continue
            if (
                not isinstance(word, dict)
                or not isinstance(word.get("values"), list)
                or any(type(value) is not int for value in word["values"])
                or type(word.get("height")) is not int
            ):
                raise ValueError(f"failure witness {name} must be an exact word record")
        _canonical(row)
    if type(candidate["omitted_failure_count"]) is not int or candidate["omitted_failure_count"] < 0:
        raise ValueError("omitted failure count must be a nonnegative integer")
    candidate_identity = {
        "parent_specification_fingerprint": prior_fingerprint,
        "program": program,
        "cost": candidate["cost"],
        "scenario_count": candidate["scenario_count"],
        "matching_scenario_count": candidate["matching_scenario_count"],
        "failure_evidence": evidence,
    }
    if candidate["candidate_fingerprint"] != _fingerprint(candidate_identity):
        raise ValueError("parent candidate fingerprint does not match its exact evidence")
    if context["counterexample_evidence_fingerprint"] != _fingerprint(evidence):
        raise ValueError("counterexample evidence fingerprint does not match its records")
    return context


@dataclass(frozen=True)
class ExperimentRefinement:
    design: ExperimentDesign
    referenced_scenario_indices: tuple[int, ...]
    evidence_interpretation: str
    proposed_change: str


def validate_experiment_refinement(raw: Any, context: dict) -> ExperimentRefinement:
    """Validate a model's bounded follow-up plan and exact failure references."""
    context = validate_refinement_context(context)
    if not isinstance(raw, dict) or set(raw) != {"design", "counterexample_analysis"}:
        raise ValueError("refinement response must contain design and counterexample_analysis")
    design = validate_experiment_design(raw["design"])
    analysis = raw["counterexample_analysis"]
    if not isinstance(analysis, dict) or set(analysis) != {
        "referenced_scenario_indices", "evidence_interpretation", "proposed_change",
    }:
        raise ValueError("counterexample analysis fields do not match the refinement schema")
    cited = analysis["referenced_scenario_indices"]
    if not isinstance(cited, list) or not 1 <= len(cited) <= 8:
        raise ValueError("reference 1–8 exact failure scenarios")
    if any(type(index) is not int for index in cited) or len(set(cited)) != len(cited):
        raise ValueError("referenced scenario indices must be distinct integers")
    available = {row["scenario_index"] for row in context["candidate"]["failure_evidence"]}
    if not set(cited) <= available:
        raise ValueError("the analysis references a scenario with no supplied engine failure")
    interpretation = _bounded_text(analysis["evidence_interpretation"], "evidence_interpretation", 1000)
    proposed_change = _bounded_text(analysis["proposed_change"], "proposed_change", 1000)
    if design.status == "plan":
        if design.spec.fingerprint == context["prior_specification_fingerprint"]:
            raise ValueError("the follow-up specification is unchanged; propose a different bounded test")
    return ExperimentRefinement(design, tuple(cited), interpretation, proposed_change)


def build_experiment_refinement_options(
    *,
    design: ExperimentDesign,
    provenance: dict,
    context: dict,
    refinement: ExperimentRefinement,
    applied_spec_fingerprint: str,
) -> dict:
    """Store the exact parent, witness, proposal, and application lineage."""
    context = validate_refinement_context(context)
    if refinement.design.spec is None or design.spec is None or refinement.design.spec.fingerprint != design.spec.fingerprint:
        raise ValueError("refinement and applied proposal specifications do not agree")
    try:
        response = json.loads(provenance["response_text"])
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("refinement provenance must retain its exact structured response") from exc
    validated_response = validate_experiment_refinement(response, context)
    if (
        validated_response.design.spec.fingerprint != refinement.design.spec.fingerprint
        or validated_response.referenced_scenario_indices != refinement.referenced_scenario_indices
        or validated_response.evidence_interpretation != refinement.evidence_interpretation
        or validated_response.proposed_change != refinement.proposed_change
    ):
        raise ValueError("refinement object does not match the exact validated response")
    available = {row["scenario_index"] for row in context["candidate"]["failure_evidence"]}
    if not refinement.referenced_scenario_indices or not set(refinement.referenced_scenario_indices) <= available:
        raise ValueError("refinement scenario references do not match recorded failures")
    options = build_experiment_design_options(
        question=provenance["question"],
        endpoint=provenance["endpoint"],
        model=provenance["requested_model"],
        response_model=provenance["response_model"],
        provider_id=provenance["provider_id"],
        inference_locality=provenance["inference_locality"],
        requested_at=provenance["requested_at"],
        completed_at=provenance["completed_at"],
        system_prompt=provenance["system_prompt"],
        user_prompt=provenance["user_prompt"],
        response_text=provenance["response_text"],
        parameters=provenance["parameters"],
        design=design,
        applied_spec_fingerprint=applied_spec_fingerprint,
    )
    options["experiment_refinement"] = {
        "schema_version": EXPERIMENT_REFINEMENT_SCHEMA_VERSION,
        "verification_status": "unverified follow-up proposal; exact finite engine failures supplied; follow-up not run",
        "parent_context": context,
        "parent_job_id": context["parent_job_id"],
        "parent_specification_fingerprint": context["prior_specification_fingerprint"],
        "parent_candidate_fingerprint": context["candidate"]["candidate_fingerprint"],
        "counterexample_evidence_fingerprint": context["counterexample_evidence_fingerprint"],
        "referenced_scenario_indices": list(refinement.referenced_scenario_indices),
        "evidence_interpretation": refinement.evidence_interpretation,
        "proposed_change": refinement.proposed_change,
        "proposed_specification_fingerprint": design.spec.fingerprint,
        "applied_specification_fingerprint": applied_spec_fingerprint,
        "application_status": (
            "used_as_proposed"
            if applied_spec_fingerprint == design.spec.fingerprint
            else "edited_after_proposal"
        ),
    }
    _canonical(options)
    return options
