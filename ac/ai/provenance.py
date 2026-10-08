"""Reproducible provenance for advisory AI reviews attached to research runs."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import uuid
from typing import Any, Mapping, Sequence


AI_REVIEW_FORMAT = "ascent-machine-ai-review"
AI_REVIEW_VERSION = 1
_LOCALITIES = {"local", "remote", "unknown"}


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("AI review provenance must contain finite JSON values") from exc


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _timestamp(value: str | None) -> str:
    result = value or datetime.now(timezone.utc).isoformat()
    if not isinstance(result, str):
        raise ValueError("AI review timestamps must be ISO-8601 text")
    try:
        parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("AI review timestamps must be ISO-8601 text") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("AI review timestamps must include a UTC offset")
    return result


def create_assistant_review(
    *,
    provider_id: str,
    provider_name: str,
    endpoint: str,
    requested_model: str,
    response_model: str | None,
    evidence: Mapping[str, Any],
    messages: Sequence[Mapping[str, str]],
    parameters: Mapping[str, Any],
    response_text: str,
    inference_locality: str = "unknown",
    requested_at: str | None = None,
    completed_at: str | None = None,
) -> dict:
    """Capture the exact bounded request and its unverified response."""
    if not all(isinstance(value, str) and value.strip() for value in (provider_id, provider_name, endpoint, requested_model)):
        raise ValueError("AI review provider and model identity must be non-empty text")
    if response_model is not None and not isinstance(response_model, str):
        raise ValueError("AI review response model must be text when present")
    if inference_locality not in _LOCALITIES:
        raise ValueError("AI review inference locality is invalid")
    if not isinstance(evidence, Mapping) or not isinstance(parameters, Mapping):
        raise ValueError("AI review evidence and parameters must be objects")
    if not isinstance(response_text, str):
        raise ValueError("AI review response must be text")
    message_rows = [dict(item) for item in messages]
    parameter_values = dict(parameters)
    request = {
        "model": requested_model,
        "messages": message_rows,
        "evidence_record": dict(evidence),
        "parameters": parameter_values,
    }
    provider = {
        "id": provider_id,
        "name": provider_name,
        "endpoint": endpoint,
        "response_model": response_model,
        "inference_locality": inference_locality,
    }
    request_identity = {"provider_id": provider_id, "endpoint": endpoint, "request": request}
    review = {
        "format": AI_REVIEW_FORMAT,
        "version": AI_REVIEW_VERSION,
        "review_id": uuid.uuid4().hex,
        "requested_at": _timestamp(requested_at),
        "completed_at": _timestamp(completed_at),
        "provider": provider,
        "request": request,
        "request_fingerprint": _fingerprint(request_identity),
        "evidence_fingerprint": _fingerprint(dict(evidence)),
        "response": {"text": response_text, "verification_status": "unverified"},
    }
    validate_assistant_review(review)
    return review


def validate_assistant_review(review: dict) -> dict:
    """Reject malformed or tampered assistant provenance before persistence/export."""
    required = {
        "format", "version", "review_id", "requested_at", "completed_at", "provider", "request",
        "request_fingerprint", "evidence_fingerprint", "response",
    }
    if not isinstance(review, dict) or set(review) != required:
        raise ValueError("AI review fields do not match the version-1 schema")
    if review["format"] != AI_REVIEW_FORMAT or type(review["version"]) is not int or review["version"] != AI_REVIEW_VERSION:
        raise ValueError("unsupported AI review format or version")
    if not isinstance(review["review_id"], str) or len(review["review_id"]) != 32:
        raise ValueError("AI review identifier is invalid")
    _timestamp(review["requested_at"])
    _timestamp(review["completed_at"])
    provider = review["provider"]
    if not isinstance(provider, dict) or set(provider) != {"id", "name", "endpoint", "response_model", "inference_locality"}:
        raise ValueError("AI review provider metadata is invalid")
    for key in ("id", "name", "endpoint"):
        if not isinstance(provider[key], str) or not provider[key].strip():
            raise ValueError("AI review provider metadata is invalid")
    if provider["response_model"] is not None and not isinstance(provider["response_model"], str):
        raise ValueError("AI review response model is invalid")
    if provider["inference_locality"] not in _LOCALITIES:
        raise ValueError("AI review inference locality is invalid")
    request = review["request"]
    if not isinstance(request, dict) or set(request) != {"model", "messages", "evidence_record", "parameters"}:
        raise ValueError("AI review request metadata is invalid")
    if not isinstance(request["model"], str) or not request["model"].strip():
        raise ValueError("AI review requested model is invalid")
    messages = request["messages"]
    if not isinstance(messages, list) or len(messages) != 2:
        raise ValueError("AI review must preserve the system and user messages")
    if any(not isinstance(item, dict) or set(item) != {"role", "content"} or not isinstance(item["content"], str) for item in messages):
        raise ValueError("AI review message history is invalid")
    if messages[0]["role"] != "system" or messages[1]["role"] != "user":
        raise ValueError("AI review message roles are invalid")
    evidence = request["evidence_record"]
    if not isinstance(evidence, dict):
        raise ValueError("AI review evidence record is invalid")
    evidence_text = json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
    if evidence_text not in messages[1]["content"]:
        raise ValueError("AI review message does not contain its recorded evidence")
    parameters = request["parameters"]
    if not isinstance(parameters, dict) or set(parameters) != {"temperature", "max_tokens", "timeout_seconds", "output_mode"}:
        raise ValueError("AI review request parameters are invalid")
    temperature = parameters["temperature"]
    timeout = parameters["timeout_seconds"]
    tokens = parameters["max_tokens"]
    if isinstance(temperature, bool) or not isinstance(temperature, (int, float)) or not math.isfinite(temperature) or not 0 <= temperature <= 2:
        raise ValueError("AI review temperature is invalid")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("AI review timeout is invalid")
    if type(tokens) is not int or tokens < 1 or parameters["output_mode"] != "text":
        raise ValueError("AI review output settings are invalid")
    response = review["response"]
    if not isinstance(response, dict) or set(response) != {"text", "verification_status"}:
        raise ValueError("AI review response is invalid")
    if not isinstance(response["text"], str) or response["verification_status"] != "unverified":
        raise ValueError("AI review response must remain explicitly unverified")
    request_identity = {"provider_id": provider["id"], "endpoint": provider["endpoint"], "request": request}
    if review["request_fingerprint"] != _fingerprint(request_identity):
        raise ValueError("AI review request fingerprint does not match its provenance")
    if review["evidence_fingerprint"] != _fingerprint(evidence):
        raise ValueError("AI review evidence fingerprint does not match its recorded evidence")
    _canonical(review)
    return review
