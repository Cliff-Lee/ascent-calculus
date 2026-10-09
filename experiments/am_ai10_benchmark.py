"""Paired deterministic versus AI-guided transformation-family benchmark.

Offline by default. With ``--with-ai``, the same finite root specification and
candidate cap are run through the overnight campaign using the explicitly
selected loopback Ollama model. Every AI proposal remains advisory; the local
engine evaluates all search rounds.

Examples::

    python experiments/am_ai10_benchmark.py --spec question.json --output baseline.json
    python experiments/am_ai10_benchmark.py --spec question.json --with-ai \
        --model qwen3.5:9b --output paired.json
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys
import tempfile
import time
from types import SimpleNamespace

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ac.ai import ProviderLocality
from ac.ai.ollama import DEFAULT_OLLAMA_URL
from ac.discovery.overnight_campaign import (
    MAX_TOTAL_CANDIDATES,
    run_overnight_campaign,
)
from ac.discovery.transformation_family import (
    FAMILY_SEARCH_FORMAT,
    TransformationFamilySearchSpec,
    run_worker_search,
)
from ac.discovery.transformation_search import TransformationSearchSpec


BENCHMARK_FORMAT = "ascent-machine-am-ai10-paired-benchmark"
BENCHMARK_VERSION = 1


class _InlineContext:
    """Small synchronous context for bounded, reproducible benchmark runs."""

    def __init__(self, database_path: Path):
        self.store = SimpleNamespace(path=database_path)
        self.checkpoint_state: dict = {}
        self.progress: dict = {}

    def checkpoint(self, state: dict, progress: dict | None = None) -> None:
        self.checkpoint_state = deepcopy(state)
        self.progress = dict(progress or {})

    def check_control(self) -> None:
        return None


def _runtime_environment() -> dict:
    script_hash = sha256(Path(__file__).read_bytes()).hexdigest()
    return {
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "benchmark_script_sha256": script_hash,
    }


def load_family_spec(path: str | Path) -> TransformationFamilySearchSpec:
    """Load a direct spec, campaign report, or exported research dossier."""
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("benchmark specification file could not be read as JSON") from exc
    raw = document
    if isinstance(document, dict):
        if isinstance(document.get("mathematical_question"), dict):
            raw = document["mathematical_question"].get("specification")
        elif isinstance(document.get("overnight_campaign"), dict):
            raw = document["overnight_campaign"].get("root_specification")
        elif isinstance(document.get("finite_result"), dict):
            campaign = document["finite_result"].get("overnight_campaign")
            if isinstance(campaign, dict):
                raw = campaign.get("root_specification")
    if not isinstance(raw, dict) or raw.get("format") != FAMILY_SEARCH_FORMAT:
        raise ValueError("input must contain a transformation-family specification")
    return TransformationFamilySearchSpec.from_dict(raw)


def _candidate_scenario_pairs(result: dict, specification: dict) -> set[tuple[str, str]]:
    """Return (program, mathematical scenario fingerprint) finite matches.

    Operational budget fields do not change the finite mathematical question,
    so removing them lets a 12-candidate guided round compare to a 24-candidate
    deterministic baseline on the same class, offsets, and degree window.
    """
    pairs: set[tuple[str, str]] = set()
    scenarios = specification.get("scenarios", ())
    fingerprints = {}
    for item in scenarios:
        if not isinstance(item, dict):
            continue
        scenario = TransformationSearchSpec.from_dict(item)
        semantic = json.loads(scenario.canonical_json())
        grammar = semantic.get("grammar", {})
        for field in (
            "candidate_budget", "expansion_budget", "enumeration_budget",
            "class_object_budget", "evaluation_budget",
        ):
            grammar.pop(field, None)
        fingerprint = sha256(
            json.dumps(semantic, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        fingerprints[scenario.fingerprint] = fingerprint
    for candidate in result.get("exact_candidates", ()):
        if not isinstance(candidate, dict) or not isinstance(candidate.get("program"), str):
            continue
        program = candidate["program"]
        rows = candidate.get("scenario_results", ())
        matched = {
            fingerprints.get(row.get("specification_fingerprint"))
            for row in rows
            if isinstance(row, dict) and row.get("finite_match") is True
        }
        if not rows:
            matched = set(fingerprints.values())
        pairs.update((program, fingerprint) for fingerprint in matched if isinstance(fingerprint, str))
    return pairs


def _guided_scenario_pairs(campaign: dict) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for round_record in campaign.get("completed_rounds", ()):
        if not isinstance(round_record, dict):
            continue
        spec = round_record.get("specification")
        result = round_record.get("search_result")
        if isinstance(spec, dict) and isinstance(result, dict):
            pairs.update(_candidate_scenario_pairs(result, spec))
    return pairs


def _campaign_exact_counts(campaign: dict) -> tuple[int, int]:
    total = 0
    retained = 0
    for round_record in campaign.get("completed_rounds", ()):
        if not isinstance(round_record, dict):
            continue
        result = round_record.get("search_result")
        if not isinstance(result, dict):
            continue
        candidates = result.get("exact_candidates", ())
        retained += len(candidates) if isinstance(candidates, list) else 0
        total += int(result.get("exact_candidate_count", len(candidates) if isinstance(candidates, list) else 0))
    return total, retained


def run_benchmark(
    spec: TransformationFamilySearchSpec,
    *,
    candidate_budget: int | None = None,
    with_ai: bool = False,
    model: str | None = None,
    endpoint: str = DEFAULT_OLLAMA_URL,
    model_locality: str = "unknown",
    max_refinements: int = 1,
    max_wall_seconds: int = 3600,
    timeout_seconds: float = 180.0,
) -> dict:
    """Run a deterministic baseline and optionally the paired AI workflow.

    Both arms share the same root question, grammar, and total candidate cap.
    The guided arm can spend that cap across follow-up specifications. This is
    a finite experimental comparison, not a model-quality theorem or a proof.
    """
    if not isinstance(spec, TransformationFamilySearchSpec):
        raise TypeError("spec must be a TransformationFamilySearchSpec")
    if candidate_budget is None:
        candidate_budget = spec.candidate_budget
    if type(candidate_budget) is not int or not 1 <= candidate_budget <= MAX_TOTAL_CANDIDATES:
        raise ValueError(f"candidate_budget must be from 1 through {MAX_TOTAL_CANDIDATES}")
    effective_budget = candidate_budget
    if with_ai and (not isinstance(model, str) or not model.strip()):
        raise ValueError("an explicit Ollama model is required when --with-ai is selected")
    locality = ProviderLocality(model_locality)

    with tempfile.TemporaryDirectory(prefix="ac-ai10-benchmark-") as directory:
        context = _InlineContext(Path(directory) / "benchmark.sqlite3")
        baseline_grammar = replace(spec.grammar, candidate_budget=effective_budget)
        baseline_scenarios = tuple(
            replace(scenario, grammar=baseline_grammar) for scenario in spec.scenarios
        )
        baseline_spec = replace(
            spec,
            scenarios=baseline_scenarios,
            candidate_budget=effective_budget,
        )
        baseline_started = time.perf_counter()
        baseline = run_worker_search(
            SimpleNamespace(question=baseline_spec, checkpoint={}), context,
        )
        baseline_seconds = time.perf_counter() - baseline_started
        baseline_pairs = _candidate_scenario_pairs(baseline, baseline_spec.to_dict())

        guided_report = None
        guided_seconds = None
        if with_ai:
            options = {
                "endpoint": endpoint,
                "model": model,
                "timeout_seconds": timeout_seconds,
                "model_locality": locality.value,
                "max_refinements": max_refinements,
                "max_total_candidates": effective_budget,
                "max_wall_seconds": max_wall_seconds,
            }
            context.checkpoint_state = {}
            job = SimpleNamespace(
                id="am-ai10-benchmark",
                question=spec,
                options=options,
                checkpoint={},
            )
            guided_started = time.perf_counter()
            guided_report = run_overnight_campaign(job, context)
            guided_seconds = time.perf_counter() - guided_started

    guided_campaign = (guided_report or {}).get("overnight_campaign") or {}
    guided_pairs = _guided_scenario_pairs(guided_campaign) if with_ai else set()
    guided_exact_count, guided_retained_count = _campaign_exact_counts(guided_campaign)
    additional_pairs = sorted(guided_pairs - baseline_pairs)
    root_fingerprint = spec.fingerprint
    record = {
        "format": BENCHMARK_FORMAT,
        "version": BENCHMARK_VERSION,
        "classification": "paired_ai_guided_comparison" if with_ai else "offline_deterministic_baseline",
        "runtime_environment": _runtime_environment(),
        "proof_status": "not_proved",
        "interpretation": (
            "This compares finite search records under the same root specification and total candidate cap. "
            "A guided-only match is a bounded additional result, not evidence that the AI found the best map or a theorem."
        ),
        "question": {
            "root_specification": spec.to_dict(),
            "root_specification_fingerprint": root_fingerprint,
        },
        "budget": {
            "requested_total_candidate_cap": candidate_budget,
            "effective_total_candidate_cap": effective_budget,
            "root_spec_candidate_cap": spec.candidate_budget,
            "baseline_budget_expanded_above_root_spec": effective_budget > spec.candidate_budget,
            "max_refinements": max_refinements if with_ai else 0,
            "max_wall_seconds": max_wall_seconds if with_ai else None,
        },
        "deterministic_baseline": {
            "specification": baseline_spec.to_dict(),
            "specification_fingerprint": baseline_spec.fingerprint,
            "candidates_tested": int(baseline.get("candidates_tested", 0)),
            "exact_candidate_count": int(baseline.get("exact_candidate_count", len(baseline.get("exact_candidates", ())))),
            "retained_exact_candidate_count": len(baseline.get("exact_candidates", ())),
            "finite_program_scenario_pairs": [list(item) for item in sorted(baseline_pairs)],
            "scenario_fingerprint_kind": "budget_independent_mathematical_question",
            "elapsed_seconds": round(baseline_seconds, 6),
            "result": baseline,
        },
        "ai_guided": None,
        "comparison": None,
    }
    if with_ai:
        guided_pairs = _guided_scenario_pairs(guided_campaign)
        record["ai_guided"] = {
            "provider_id": "ollama-loopback",
            "endpoint": endpoint,
            "requested_model": model.strip(),
            "declared_inference_locality": locality.value,
            "candidates_tested": int((guided_report or {}).get("candidates_tested", 0)),
            "exact_candidate_count": guided_exact_count,
            "retained_exact_candidate_count": guided_retained_count,
            "round_count": int(guided_campaign.get("round_count", 0)),
            "assistant_iteration_count": len(guided_campaign.get("assistant_iterations", ())),
            "validated_follow_up_count": sum(
                item.get("validation_status") == "validated_bounded_experiment"
                for item in guided_campaign.get("assistant_iterations", ())
                if isinstance(item, dict)
            ),
            "stop_reason": guided_campaign.get("stop_reason"),
            "finite_program_scenario_pairs": [list(item) for item in sorted(guided_pairs)],
            "scenario_fingerprint_kind": "budget_independent_mathematical_question",
            "elapsed_seconds": round(guided_seconds or 0.0, 6),
            "result": guided_report,
        }
        record["comparison"] = {
            "same_root_specification": guided_campaign.get("root_specification_fingerprint") == root_fingerprint,
            "same_total_candidate_cap": (
                int((guided_report or {}).get("effective_candidate_budget", -1)) == effective_budget
            ),
            "additional_finite_program_scenario_pairs": [list(item) for item in additional_pairs],
            "additional_pair_count": len(additional_pairs),
            "pair_comparison_scope": (
                "Additional pairs are computed from retained exact-candidate records; total exact-candidate counts are reported separately."
            ),
            "guided_candidate_cap_used": int((guided_report or {}).get("candidates_tested", 0)),
            "baseline_candidate_cap_used": int(baseline.get("candidates_tested", 0)),
            "effort_note": (
                "Candidate caps are matched; wall time and enumerated class objects are reported separately. "
                "The AI arm includes model latency and can distribute candidates across multiple specifications."
            ),
        }
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path, help="family-search JSON, campaign report, or research dossier")
    parser.add_argument("--output", type=Path, help="write the complete benchmark dossier as JSON")
    parser.add_argument("--candidate-budget", type=int, help="total candidate cap for both arms; defaults to the spec cap")
    parser.add_argument("--with-ai", action="store_true", help="explicitly send the bounded search evidence to the selected Ollama model")
    parser.add_argument("--model", help="installed Ollama model, required with --with-ai")
    parser.add_argument("--endpoint", default=DEFAULT_OLLAMA_URL, help="loopback Ollama origin")
    parser.add_argument("--model-locality", choices=[item.value for item in ProviderLocality], default="unknown")
    parser.add_argument("--max-refinements", type=int, default=1)
    parser.add_argument("--max-wall-seconds", type=int, default=3600)
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    args = parser.parse_args(argv)
    try:
        spec = load_family_spec(args.spec)
        result = run_benchmark(
            spec,
            candidate_budget=args.candidate_budget,
            with_ai=args.with_ai,
            model=args.model,
            endpoint=args.endpoint,
            model_locality=args.model_locality,
            max_refinements=args.max_refinements,
            max_wall_seconds=args.max_wall_seconds,
            timeout_seconds=args.timeout_seconds,
        )
        encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded, encoding="utf-8")
        else:
            print(encoded, end="")
        return 0
    except (OSError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
