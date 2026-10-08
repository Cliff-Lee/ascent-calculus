"""Bounded, provenance-aware proof-plan assistance for finite map candidates.

The validator checks only structure, obligation references, and plan dependency
integrity. It does not check a mathematical claim or certify any proof step.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any


PROOF_PLAN_FORMAT = "ascent-machine-proof-plan"
PROOF_PLAN_VERSION = 1
MAX_PROOF_OBLIGATIONS = 16
MAX_PROOF_STEPS = 24
MAX_PLAN_TEXT = 2_000

_ROLES = {
    "main_claim",
    "candidate_lemma",
    "case_split",
    "inverse_formula",
    "induction_hypothesis",
}
_FALLBACK_OBLIGATIONS = (
    "Treat agreement through the tested bound as finite evidence, not an all-degree theorem.",
    "Prove that the proposed map is defined on every object in the claimed source class.",
    "Prove that every image belongs to the target class at the stated degree offset.",
    "Prove injectivity and surjectivity, or give an explicit inverse and prove both compositions are identities.",
)


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("proof-assistance context must contain finite JSON values") from exc


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _reject_json_constant(value: str):
    raise ValueError(f"non-finite JSON constant {value} is not allowed")


def _bounded_text(value: Any, field: str, *, maximum: int = MAX_PLAN_TEXT) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise ValueError(f"{field} must be non-empty text no longer than {maximum} characters")
    return value.strip()


@dataclass(frozen=True)
class ProofPlan:
    """A structurally checked, explicitly unverified assistant proposal."""

    title: str
    goal: str
    steps: tuple[dict, ...]
    unresolved_gaps: tuple[str, ...]
    useful_checks: tuple[str, ...]
    context_fingerprint: str


def build_proof_assistance_context(candidate_evidence: dict, proof_obligations=()) -> dict:
    """Bind a candidate's exact bounded record to the job's proof obligations."""
    if not isinstance(candidate_evidence, dict):
        raise TypeError("candidate evidence must be an object")
    if candidate_evidence.get("evidence_status") != "finite computation; not a proof":
        raise ValueError("proof planning requires an explicitly finite, unproved candidate record")
    # Round-trip through JSON to reject custom objects and ensure no shared mutable
    # references survive into the saved provenance packet.
    evidence = json.loads(_canonical(candidate_evidence))
    if not isinstance(evidence.get("candidate"), dict) or not isinstance(evidence["candidate"].get("program"), str):
        raise ValueError("proof planning requires a specific candidate transformation")
    if not isinstance(proof_obligations, (list, tuple)) and proof_obligations:
        raise TypeError("proof obligations must be a list or tuple of statements")
    source = tuple(proof_obligations) if proof_obligations else _FALLBACK_OBLIGATIONS
    if len(source) > MAX_PROOF_OBLIGATIONS:
        raise ValueError(f"proof assistance supports at most {MAX_PROOF_OBLIGATIONS} obligations")
    rows = []
    seen = set()
    for raw in source:
        text = _bounded_text(raw, "proof obligation", maximum=1_000)
        if text in seen:
            continue
        seen.add(text)
        rows.append({"id": f"O{len(rows) + 1}", "statement": text})
    if not rows:
        raise ValueError("proof assistance needs at least one proof obligation")
    base = {
        "format": PROOF_PLAN_FORMAT,
        "version": PROOF_PLAN_VERSION,
        "verification_status": "unverified assistant proposal",
        "proof_status": "not_proved",
        "candidate_evidence": evidence,
        "proof_obligations": rows,
    }
    context = {**base, "context_fingerprint": _fingerprint(base)}
    if len(_canonical(context).encode("utf-8")) > 100_000:
        raise ValueError("proof-assistance evidence exceeds the 100 KB context limit")
    return context


def validate_proof_assistance_context(context: dict) -> dict:
    """Validate context shape and reject edits to evidence or obligation text."""
    required = {
        "format", "version", "verification_status", "proof_status",
        "candidate_evidence", "proof_obligations", "context_fingerprint",
    }
    if not isinstance(context, dict) or set(context) != required:
        raise ValueError("proof-assistance context fields are invalid")
    if context["format"] != PROOF_PLAN_FORMAT or type(context["version"]) is not int or context["version"] != PROOF_PLAN_VERSION:
        raise ValueError("unsupported proof-assistance context format")
    if context["verification_status"] != "unverified assistant proposal" or context["proof_status"] != "not_proved":
        raise ValueError("proof assistance must preserve the unverified, not-proved status")
    evidence = context["candidate_evidence"]
    if (
        not isinstance(evidence, dict)
        or evidence.get("evidence_status") != "finite computation; not a proof"
        or not isinstance(evidence.get("candidate"), dict)
        or not isinstance(evidence["candidate"].get("program"), str)
    ):
        raise ValueError("proof-assistance candidate evidence must remain finite and unproved")
    obligations = context["proof_obligations"]
    if not isinstance(obligations, list) or not 1 <= len(obligations) <= MAX_PROOF_OBLIGATIONS:
        raise ValueError("proof-assistance obligations are invalid")
    for index, item in enumerate(obligations, 1):
        if not isinstance(item, dict) or set(item) != {"id", "statement"}:
            raise ValueError("proof-assistance obligation row is invalid")
        if item["id"] != f"O{index}":
            raise ValueError("proof-assistance obligation identifiers must be ordered O1, O2, ...")
        _bounded_text(item["statement"], f"proof obligation {item['id']}", maximum=1_000)
    base = {key: context[key] for key in required if key != "context_fingerprint"}
    if context["context_fingerprint"] != _fingerprint(base):
        raise ValueError("proof-assistance context fingerprint does not match its exact evidence")
    _canonical(context)
    return context


_STEP_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["id", "role", "statement", "strategy", "obligation_refs", "depends_on"],
    "properties": {
        "id": {"type": "string", "pattern": "^S[1-9][0-9]*$"},
        "role": {"type": "string", "enum": sorted(_ROLES)},
        "statement": {"type": "string", "minLength": 1, "maxLength": MAX_PLAN_TEXT},
        "strategy": {"type": "string", "minLength": 1, "maxLength": MAX_PLAN_TEXT},
        "obligation_refs": {"type": "array", "items": {"type": "string", "pattern": "^O[1-9][0-9]*$"}, "minItems": 1, "maxItems": MAX_PROOF_OBLIGATIONS, "uniqueItems": True},
        "depends_on": {"type": "array", "items": {"type": "string", "pattern": "^S[1-9][0-9]*$"}, "maxItems": MAX_PROOF_STEPS, "uniqueItems": True},
    },
}

PROOF_PLAN_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["context_fingerprint", "title", "goal", "steps", "unresolved_gaps", "useful_checks"],
    "properties": {
        "context_fingerprint": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "title": {"type": "string", "minLength": 1, "maxLength": 180},
        "goal": {"type": "string", "minLength": 1, "maxLength": MAX_PLAN_TEXT},
        "steps": {"type": "array", "items": _STEP_SCHEMA, "minItems": 1, "maxItems": MAX_PROOF_STEPS},
        "unresolved_gaps": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": MAX_PLAN_TEXT}, "maxItems": 16},
        "useful_checks": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": MAX_PLAN_TEXT}, "minItems": 1, "maxItems": 16},
    },
}


def validate_proof_plan(raw: Any, context: dict) -> ProofPlan:
    """Check exact context references and a dependency DAG; never check truth."""
    context = validate_proof_assistance_context(context)
    if not isinstance(raw, dict):
        raise ValueError("assistant proof plan must be a JSON object")
    required = {"context_fingerprint", "title", "goal", "steps", "unresolved_gaps", "useful_checks"}
    if set(raw) != required:
        raise ValueError("assistant proof-plan fields do not match the required schema")
    if raw["context_fingerprint"] != context["context_fingerprint"]:
        raise ValueError("assistant proof plan refers to a different evidence context")
    title = _bounded_text(raw["title"], "proof-plan title", maximum=180)
    goal = _bounded_text(raw["goal"], "proof-plan goal")
    steps = raw["steps"]
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_PROOF_STEPS:
        raise ValueError(f"proof plan must contain 1 to {MAX_PROOF_STEPS} steps")
    obligation_ids = {item["id"] for item in context["proof_obligations"]}
    parsed_steps = []
    ids = set()
    coverage = set()
    for row in steps:
        if not isinstance(row, dict) or set(row) != {"id", "role", "statement", "strategy", "obligation_refs", "depends_on"}:
            raise ValueError("proof-plan step fields do not match the required schema")
        identifier = row["id"]
        if not isinstance(identifier, str) or not re.fullmatch(r"S[1-9][0-9]*", identifier) or identifier in ids:
            raise ValueError("proof-plan step identifiers must be unique S1, S2, ... labels")
        ids.add(identifier)
        if not isinstance(row["role"], str) or row["role"] not in _ROLES:
            raise ValueError(f"proof-plan step {identifier} has an unsupported role")
        statement = _bounded_text(row["statement"], f"proof-plan statement {identifier}")
        strategy = _bounded_text(row["strategy"], f"proof strategy {identifier}")
        refs = row["obligation_refs"]
        deps = row["depends_on"]
        if not isinstance(refs, list) or not refs or len(refs) > MAX_PROOF_OBLIGATIONS or any(not isinstance(ref, str) for ref in refs):
            raise ValueError(f"proof-plan step {identifier} needs distinct obligation references")
        if len(set(refs)) != len(refs):
            raise ValueError(f"proof-plan step {identifier} needs distinct obligation references")
        if any(ref not in obligation_ids for ref in refs):
            raise ValueError(f"proof-plan step {identifier} cites an obligation not supplied in the context")
        if not isinstance(deps, list) or len(deps) > MAX_PROOF_STEPS or any(not isinstance(dep, str) for dep in deps):
            raise ValueError(f"proof-plan step {identifier} has invalid dependencies")
        if len(set(deps)) != len(deps):
            raise ValueError(f"proof-plan step {identifier} has invalid dependencies")
        if any(not isinstance(dep, str) or not re.fullmatch(r"S[1-9][0-9]*", dep) or dep == identifier for dep in deps):
            raise ValueError(f"proof-plan step {identifier} has an invalid dependency identifier")
        coverage.update(refs)
        parsed_steps.append({
            "id": identifier,
            "role": row["role"],
            "statement": statement,
            "strategy": strategy,
            "obligation_refs": list(refs),
            "depends_on": list(deps),
        })
    if coverage != obligation_ids:
        missing = ", ".join(sorted(obligation_ids - coverage))
        raise ValueError(f"proof plan must account for every supplied obligation; missing {missing}")
    by_id = {item["id"]: item for item in parsed_steps}
    for item in parsed_steps:
        if any(dep not in by_id for dep in item["depends_on"]):
            raise ValueError(f"proof-plan step {item['id']} depends on a missing step")
    visiting, visited = set(), set()

    def visit(identifier):
        if identifier in visiting:
            raise ValueError("proof-plan dependencies contain a cycle")
        if identifier in visited:
            return
        visiting.add(identifier)
        for dependency in by_id[identifier]["depends_on"]:
            visit(dependency)
        visiting.remove(identifier)
        visited.add(identifier)

    for identifier in by_id:
        visit(identifier)
    gaps = _string_list(raw["unresolved_gaps"], "unresolved gaps", maximum=16)
    checks = _string_list(raw["useful_checks"], "useful checks", maximum=16, minimum=1)
    return ProofPlan(
        title=title,
        goal=goal,
        steps=tuple(parsed_steps),
        unresolved_gaps=tuple(gaps),
        useful_checks=tuple(checks),
        context_fingerprint=context["context_fingerprint"],
    )


def _string_list(value: Any, field: str, *, maximum: int, minimum: int = 0) -> list[str]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ValueError(f"{field} must contain {minimum} to {maximum} entries")
    return [_bounded_text(item, field) for item in value]


def parse_proof_plan_json(response_text: str, context: dict) -> ProofPlan:
    """Parse and locally structure-check JSON returned by the advisory model."""
    if not isinstance(response_text, str) or len(response_text) > 100_000:
        raise ValueError("assistant proof-plan response is missing or too large")
    try:
        raw = json.loads(response_text, parse_constant=_reject_json_constant)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError("assistant response is not valid JSON") from exc
    return validate_proof_plan(raw, context)


def render_proof_plan(plan: ProofPlan) -> str:
    """Render an advisory outline with a fixed, non-promotable verification label."""
    lines = [
        f"PROOF PLAN · {plan.title}",
        "AI-PROPOSED · UNVERIFIED. No mathematical claim or step has been checked by the engine.",
        f"Evidence context: {plan.context_fingerprint}",
        "",
        "Goal",
        plan.goal,
        "",
        "Proposed steps",
    ]
    for row in plan.steps:
        refs = ", ".join(row["obligation_refs"])
        dependencies = ", ".join(row["depends_on"]) or "none"
        lines.extend((
            f"\n{row['id']} · {row['role'].replace('_', ' ')} · {refs} · depends on {dependencies}",
            row["statement"],
            f"Possible route · {row['strategy']}",
            "Researcher status · proposed, not verified",
        ))
    lines.extend(("", "Unresolved gaps"))
    if plan.unresolved_gaps:
        lines.extend(f"• {item}" for item in plan.unresolved_gaps)
    else:
        lines.append("• None listed by the assistant; review the obligations independently.")
    lines.extend(("", "Useful follow-up checks"))
    lines.extend(f"• {item}" for item in plan.useful_checks)
    lines.extend(("", "The local checker validated only schema, evidence-context identity, obligation references, and dependency acyclicity. It did not validate any statement or proof."))
    return "\n".join(lines)

