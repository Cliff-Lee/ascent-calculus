"""Versioned, self-contained JSON exports for bounded research jobs."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tomllib
import uuid

from ac.discovery.specification import SEMANTICS_VERSION

DOSSIER_FORMAT = "ascent-machine-research-dossier"
DOSSIER_VERSION = 3
_DOSSIER_V1_FIELDS = {
    "format", "version", "exported_at", "engine", "runtime_environment",
    "mathematical_question", "tested_bounds", "execution", "finite_result",
    "interpretation", "proof_status", "proof_obligations",
}
_DOSSIER_V2_FIELDS = _DOSSIER_V1_FIELDS | {"assistant_reviews"}
_DOSSIER_V3_FIELDS = _DOSSIER_V2_FIELDS | {"research_priority_review"}
SEMANTICS_DEFINITION = {
    "ordinary_ascent_sequence": (
        "A nonempty positive word x with x_1=1; for i>1, x_i is at most "
        "2 plus the number of strict adjacent rises in x_1,...,x_{i-1}."
    ),
    "cayley_word": (
        "The used values are exactly 1,...,max(x). The empty word is Cayley "
        "at ambient height zero."
    ),
    "modified_ascent_sequence": (
        "A Cayley word whose first-occurrence positions equal its ascent-top set."
    ),
    "revised_ascent_sequence": (
        "A Cayley word whose first-occurrence positions equal its ascent-bottom set."
    ),
    "ascent_top_bottom_convention": (
        "For nonempty words, both sets include position 1. Each strict rise "
        "x_i<x_{i+1} contributes top i+1 and bottom i. Positions are one-based."
    ),
    "classical_pattern": (
        "Choose increasing positions and standardize selected values by their "
        "order and equality. Pattern rules in one class are conjunctive."
    ),
    "degree_offsets": (
        "At reference degree n, the source is evaluated at n+a and the target "
        "at n+b. Offsets change word length only, not values, labels, or statistics."
    ),
    "evidence_status": (
        "A bounded computational match is finite evidence and is not an all-degree proof."
    ),
}


def _canonical_json(value) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"dossier must contain finite JSON values: {exc}") from exc


def _utc_timestamp(value: float | None = None) -> str | None:
    return None if value is None else datetime.fromtimestamp(value, timezone.utc).isoformat()


def _engine_metadata() -> dict:
    root = Path(__file__).resolve().parents[2]
    version = "source-unversioned"
    project_file = root / "pyproject.toml"
    try:
        project = tomllib.loads(project_file.read_text(encoding="utf-8"))
        version = str(project.get("project", {}).get("version", version))
    except (OSError, tomllib.TOMLDecodeError):
        pass
    revision = os.environ.get("ASCENT_ENGINE_REVISION")
    if not revision:
        try:
            completed = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                text=True, timeout=1, check=True,
            )
            revision = completed.stdout.strip() or None
        except (OSError, subprocess.SubprocessError):
            revision = None
    return {"name": "Ascent Engine", "package": "ascent-calculus", "version": version, "source_revision": revision}


def _planned_windows(specification: dict) -> list[dict]:
    scenarios = specification.get("scenarios")
    if isinstance(scenarios, list):
        windows = []
        for index, scenario in enumerate(scenarios):
            degrees = scenario.get("degrees", {})
            windows.append({
                "scenario_index": index,
                "start": degrees.get("start"),
                "stop": degrees.get("stop"),
                "source_offset": scenario.get("source_offset"),
                "target_offset": scenario.get("target_offset"),
            })
        return windows
    degrees = specification.get("degrees", {})
    if isinstance(degrees, dict):
        return [{
            "scenario_index": 0,
            "start": degrees.get("start"),
            "stop": degrees.get("stop"),
            "source_offset": specification.get("source_offset", 0),
            "target_offset": specification.get("target_offset", 0),
        }]
    return []


def _proof_obligations(result: dict | None) -> list[str]:
    if result and isinstance(result.get("proof_obligations"), list):
        return list(result["proof_obligations"])
    obligations = [
        "Treat every agreement as bounded computational evidence, not an all-degree theorem.",
        "Check the proposed statement and definitions independently, then prove it for all requested degrees.",
    ]
    if result and (result.get("exact_candidates") or result.get("ranked_candidates")):
        obligations.extend((
            "Prove that each proposed map is defined on every source object in the claimed class.",
            "Prove target membership, injectivity, and surjectivity for all degrees in the claimed range.",
        ))
    return obligations


def _validate_overnight_dossier(dossier: dict, question) -> None:
    result = dossier.get("finite_result") or {}
    campaign = result.get("overnight_campaign")
    indexed_rounds = dossier["tested_bounds"].get("overnight_rounds")
    if campaign is None:
        if indexed_rounds is not None:
            raise ValueError("dossier has overnight-round bounds without an overnight result")
        return
    from ac.discovery.transformation_family import TransformationFamilySearchSpec

    if not isinstance(question, TransformationFamilySearchSpec):
        raise ValueError("overnight campaign root question must be a transformation-family specification")
    if not isinstance(campaign, dict) or campaign.get("version") != 1:
        raise ValueError("unsupported overnight campaign report version")
    root_spec = campaign.get("root_specification")
    if not isinstance(root_spec, dict):
        raise ValueError("overnight report must retain its exact root specification")
    parsed_root = TransformationFamilySearchSpec.from_dict(root_spec)
    if (
        parsed_root.fingerprint != question.fingerprint
        or campaign.get("root_specification_fingerprint") != question.fingerprint
    ):
        raise ValueError("overnight report root specification does not match the dossier question")
    rounds = campaign.get("completed_rounds")
    if not isinstance(rounds, list):
        raise ValueError("overnight completed rounds must be an array")
    if not isinstance(indexed_rounds, list) or len(indexed_rounds) != len(rounds):
        raise ValueError("dossier tested bounds do not index every overnight search round")
    if result.get("proof_status") != "not_proved":
        raise ValueError("overnight finite search reports must retain proof_status not_proved")
    for index, (round_record, index_record) in enumerate(zip(rounds, indexed_rounds)):
        if not isinstance(round_record, dict):
            raise ValueError("overnight round record must be an object")
        if round_record.get("round_index") != index:
            raise ValueError("overnight round indices must be consecutive from zero")
        round_spec_data = round_record.get("specification")
        if not isinstance(round_spec_data, dict):
            raise ValueError("overnight round must retain its typed search specification")
        round_spec = TransformationFamilySearchSpec.from_dict(round_spec_data)
        round_fingerprint = round_record.get("specification_fingerprint")
        if round_fingerprint != round_spec.fingerprint:
            raise ValueError("overnight round specification fingerprint is invalid")
        search = round_record.get("search_result")
        if not isinstance(search, dict) or search.get("specification_fingerprint") != round_fingerprint:
            raise ValueError("overnight finite result does not match its exact round specification")
        if search.get("proof_status") != "not_proved":
            raise ValueError("overnight search round must retain proof_status not_proved")
        tested = round_record.get("candidates_tested")
        if type(tested) is not int or tested < 0 or search.get("candidates_tested") != tested:
            raise ValueError("overnight candidate count does not match its round result")
        if (
            index_record.get("round_index") != index
            or index_record.get("specification_fingerprint") != round_fingerprint
            or index_record.get("specification") != round_spec_data
            or index_record.get("candidates_tested") != tested
        ):
            raise ValueError("dossier overnight-round index does not match its exact campaign result")


def build_research_dossier(job, *, events=(), assistant_reviews=()) -> dict:
    """Capture the exact question, finite computation, and durable worker state."""
    question = job.question
    specification = question.to_dict()
    canonical = question.canonical_json()
    if canonical != _canonical_json(specification):
        raise ValueError("research question canonical serialization is inconsistent")
    result = job.result
    if result is not None and not isinstance(result, dict):
        raise ValueError("research result must be a JSON object")
    result = None if result is None else dict(result)
    scenario_specs = result.get("scenario_specifications", ()) if result else ()
    planned = _planned_windows(specification)
    if scenario_specs:
        tested_windows = [dict(item) for item in scenario_specs]
    else:
        tested_windows = planned
    candidates_tested = (
        result.get("candidates_tested") if result else None
    )
    if candidates_tested is None:
        candidates_tested = job.progress.get("candidates_tested", job.checkpoint.get("examined"))
    grammar = specification.get("grammar", {})
    if not isinstance(grammar, dict) and specification.get("scenarios"):
        grammar = specification["scenarios"][0].get("grammar", {})
    elif not grammar and specification.get("scenarios"):
        grammar = specification["scenarios"][0].get("grammar", {})
    search_budgets = {
        key: specification[key]
        for key in ("candidate_budget", "enumeration_budget", "class_object_budget", "evaluation_budget")
        if key in specification
    }
    if isinstance(grammar, dict):
        for key in ("candidate_budget", "expansion_budget", "enumeration_budget", "class_object_budget", "evaluation_budget", "max_cost", "max_steps"):
            if key in grammar:
                search_budgets.setdefault(key, grammar[key])
    candidate_budget = None
    if result:
        candidate_budget = result.get("effective_candidate_budget", result.get("candidate_budget"))
    if candidate_budget is None:
        candidate_budget = specification.get("candidate_budget", grammar.get("candidate_budget") if isinstance(grammar, dict) else None)

    dossier = {
        "format": DOSSIER_FORMAT,
        "version": DOSSIER_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "engine": _engine_metadata(),
        "runtime_environment": {
            "python_version": sys.version,
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "system": platform.system(),
            "architecture": platform.machine(),
        },
        "mathematical_question": {
            "format": specification.get("format"),
            "schema_version": specification.get("version"),
            "semantics_version": specification.get("semantics", SEMANTICS_VERSION),
            "semantics_definition": SEMANTICS_DEFINITION,
            "semantics_fingerprint": sha256(_canonical_json(SEMANTICS_DEFINITION).encode("utf-8")).hexdigest(),
            "fingerprint": question.fingerprint,
            "canonical_json": canonical,
            "specification": specification,
        },
        "tested_bounds": {
            "planned_degree_windows": planned,
            "tested_degree_windows": tested_windows,
            "scenario_count": result.get("scenario_count", len(planned)) if result else len(planned),
            "search_budgets": search_budgets,
            "candidate_budget": candidate_budget,
            "candidates_tested": candidates_tested,
            "grammar_version": result.get("grammar_version") if result else getattr(question, "grammar_version", None),
            "proof_status": result.get("proof_status", "not_proved") if result else "not_proved",
        },
        "execution": {
            "job_id": job.id,
            "handler": job.handler,
            "status": job.status,
            "control": job.control,
            "options": job.options,
            "created_at": _utc_timestamp(job.created_at),
            "updated_at": _utc_timestamp(job.updated_at),
            "heartbeat_at": _utc_timestamp(job.heartbeat_at),
            "worker_id": job.worker_id,
            "progress": job.progress,
            "checkpoint": job.checkpoint,
            "error": job.error,
            "events": [dict(event) for event in events],
        },
        "finite_result": result,
        "interpretation": (
            result.get("interpretation") if result and result.get("interpretation")
            else "This dossier records a finite computation. No general theorem is claimed."
        ),
        "proof_status": result.get("proof_status", "not_proved") if result else "not_proved",
        "proof_obligations": _proof_obligations(result),
        "assistant_reviews": [dict(item) for item in assistant_reviews],
        "research_priority_review": None,
    }
    overnight = (result or {}).get("overnight_campaign")
    if isinstance(overnight, dict):
        # Preserve every applied typed specification as an immediately
        # inspectable tested bound. The full result already includes the raw
        # searches and AI requests; this concise index prevents the dossier's
        # root question window from hiding later class/offset refinements.
        dossier["tested_bounds"]["overnight_rounds"] = [
            {
                "round_index": item.get("round_index"),
                "specification_fingerprint": item.get("specification_fingerprint"),
                "specification": item.get("specification"),
                "candidates_tested": item.get("candidates_tested"),
                "effective_candidate_budget": (item.get("search_result") or {}).get("effective_candidate_budget"),
                "proof_status": (item.get("search_result") or {}).get("proof_status", "not_proved"),
            }
            for item in overnight.get("completed_rounds", ())
            if isinstance(item, dict)
        ]
    from ac.discovery.significance import build_research_priority_review
    dossier["research_priority_review"] = build_research_priority_review(question, result)
    validate_dossier(dossier)
    return dossier


def validate_dossier(dossier: dict) -> dict:
    """Validate schema version, spec/evidence provenance, and finite JSON."""
    if not isinstance(dossier, dict):
        raise ValueError("research dossier must be a JSON object")
    version = dossier.get("version")
    schemas = {1: _DOSSIER_V1_FIELDS, 2: _DOSSIER_V2_FIELDS, DOSSIER_VERSION: _DOSSIER_V3_FIELDS}
    required = schemas.get(version)
    if required is None:
        raise ValueError("unsupported research-dossier format or version")
    if set(dossier) != required:
        raise ValueError(f"research dossier fields do not match the version-{version} schema")
    if dossier["format"] != DOSSIER_FORMAT or type(version) is not int:
        raise ValueError("unsupported research-dossier format or version")
    question = dossier["mathematical_question"]
    if not isinstance(question, dict) or set(question) != {
        "format", "schema_version", "semantics_version", "semantics_definition",
        "semantics_fingerprint", "fingerprint", "canonical_json", "specification",
    }:
        raise ValueError("mathematical question does not match the dossier schema")
    specification = question["specification"]
    canonical = _canonical_json(specification)
    if canonical != question["canonical_json"]:
        raise ValueError("dossier canonical specification does not match its serialized question")
    fingerprint = sha256(canonical.encode("utf-8")).hexdigest()
    if question["fingerprint"] != fingerprint:
        raise ValueError("dossier specification fingerprint does not match its question")
    semantics_fingerprint = sha256(_canonical_json(question["semantics_definition"]).encode("utf-8")).hexdigest()
    if question["semantics_fingerprint"] != semantics_fingerprint:
        raise ValueError("dossier semantics fingerprint does not match its definitions")
    if question["format"] != specification.get("format") or question["schema_version"] != specification.get("version"):
        raise ValueError("dossier question header does not match its specification")
    parser = {
        "ascent-machine-search-spec": ("ac.discovery.specification", "SearchSpec"),
        "ascent-machine-conjecture-search": ("ac.discovery.conjecture_search", "ConjectureSearchSpec"),
        "ascent-machine-transformation-search": ("ac.discovery.transformation_search", "TransformationSearchSpec"),
        "ascent-machine-transformation-family-search": ("ac.discovery.transformation_family", "TransformationFamilySearchSpec"),
    }.get(question["format"])
    if parser is None:
        raise ValueError("dossier contains an unsupported mathematical-question format")
    import importlib
    spec_type = getattr(importlib.import_module(parser[0]), parser[1])
    parsed_question = spec_type.from_dict(specification)
    if parsed_question.fingerprint != fingerprint:
        raise ValueError("dossier parsed question does not reproduce its fingerprint")
    if version >= 2:
        from ac.ai.provenance import validate_assistant_review
        reviews = dossier["assistant_reviews"]
        if not isinstance(reviews, list):
            raise ValueError("dossier assistant reviews must be a list")
        review_ids = set()
        for review in reviews:
            validate_assistant_review(review)
            if review["review_id"] in review_ids:
                raise ValueError("dossier contains a duplicate assistant review")
            review_ids.add(review["review_id"])
    if version >= 3:
        from ac.discovery.significance import build_research_priority_review
        expected_priority = build_research_priority_review(parsed_question, dossier["finite_result"])
        if dossier["research_priority_review"] != expected_priority:
            raise ValueError("dossier research-priority review does not match its finite results and rubric")
    _validate_overnight_dossier(dossier, parsed_question)
    _canonical_json(dossier)
    return dossier


def write_dossier(path: str | os.PathLike[str], dossier: dict) -> Path:
    """Write a validated dossier atomically to the requested JSON file."""
    validate_dossier(dossier)
    destination = Path(path).expanduser().resolve()
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    encoded = json.dumps(dossier, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except OSError:
        try:
            temporary.unlink()
        except OSError:
            pass
        raise
    return destination


def read_dossier(path: str | os.PathLike[str]) -> dict:
    try:
        with Path(path).expanduser().open("r", encoding="utf-8") as handle:
            dossier = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read research dossier: {exc}") from exc
    return validate_dossier(dossier)
