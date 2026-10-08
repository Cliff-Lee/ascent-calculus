"""Independently validate AM-N12 blind-search candidates through held-out degrees.

Class sets come from literal all-tuples definitions in ``reference_ascent``;
validation does not use production ascent-sequence generators or the named hat
map.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ac.discovery.transformation_search import (
    TransformationSearchSpec,
    generate_transformation_atoms,
)
from ac.core.word import ChainWord
from experiments.reference_ascent import modified, ordinary


SEARCH_FORMAT = "ascent-machine-am-n12-blind-search"
VALIDATION_FORMAT = "ascent-machine-am-n12-independent-validation"
VALIDATION_VERSION = 1
HELD_OUT_THROUGH = 7


def _fingerprint(value) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def validate(search_record: dict) -> dict:
    if search_record.get("format") != SEARCH_FORMAT or search_record.get("version") != 1:
        raise ValueError("input is not a supported AM-N12 blind-search result")
    question = search_record.get("benchmark_question")
    if not isinstance(question, dict) or _fingerprint(question) != search_record.get("benchmark_fingerprint"):
        raise ValueError("blind-search question fingerprint is invalid")
    if search_record.get("search_guidance", {}).get("target_map_provided") is not False:
        raise ValueError("blind-search record does not document a withheld target map")
    spec = TransformationSearchSpec.from_dict(question)
    if spec.fingerprint != search_record.get("spec_fingerprint"):
        raise ValueError("candidate result does not match its recorded question")
    if (
        spec.source.family != "ordinary"
        or spec.target.family != "modified"
        or spec.degree_shift != 0
        or (spec.degrees.start, spec.degrees.stop) != (1, 5)
        or spec.grammar.operations != ("selector_sweeps",)
        or spec.grammar.selectors != ("raw_asc_top",)
        or spec.grammar.boolean_selector_algebra
        or search_record["search_guidance"].get("target_map_atom_enabled") is not False
    ):
        raise ValueError("blind-search question differs from the registered N12 benchmark")

    atoms = generate_transformation_atoms(spec.grammar, expected_length_shift=0)
    by_program = {repr(atom): atom for atom in atoms}
    candidates = search_record.get("finite_bijection_candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("blind search did not retain a finite map candidate")
    if any(row.get("program") not in by_program for row in candidates):
        raise ValueError("a reported candidate is not in the recorded generated grammar")
    if search_record.get("generated_atom_count") != len(atoms):
        raise ValueError("generated atom count differs from the recorded search grammar")

    training_stop = spec.degrees.stop
    candidate_results = []
    degree_counts = []
    for candidate in candidates:
        program = candidate["program"]
        transform = by_program[program]
        degree_results = []
        for degree in range(spec.degrees.start, HELD_OUT_THROUGH + 1):
            source = ordinary(degree)
            target = modified(degree)
            outputs = []
            failure = None
            for values in sorted(source):
                try:
                    output = transform.apply(ChainWord.of(values)).output.values
                except (ValueError, IndexError, TypeError) as exc:
                    failure = {"kind": "undefined", "source": list(values), "detail": str(exc)}
                    break
                if output not in target:
                    failure = {"kind": "outside_target", "source": list(values), "output": list(output)}
                    break
                outputs.append(output)
            if failure is None and len(outputs) != len(set(outputs)):
                failure = {"kind": "collision", "image_count": len(set(outputs)), "source_count": len(source)}
            if failure is None and set(outputs) != target:
                failure = {"kind": "not_surjective", "image_count": len(set(outputs)), "target_count": len(target)}
            row = {
                "degree": degree,
                "held_out": degree > training_stop,
                "source_count": len(source),
                "target_count": len(target),
                "verified_bijection": failure is None,
                "failure": failure,
            }
            degree_results.append(row)
            if not candidate_results:
                degree_counts.append({key: row[key] for key in ("degree", "held_out", "source_count", "target_count")})
        candidate_results.append({
            "program": program,
            "passes_training_window": all(row["verified_bijection"] for row in degree_results if not row["held_out"]),
            "passes_held_out_degrees": all(row["verified_bijection"] for row in degree_results if row["held_out"]),
            "verified_through_degree": max(
                (row["degree"] for row in degree_results if row["verified_bijection"]), default=0,
            ),
            "degree_results": degree_results,
        })

    training_rows = [row for row in candidate_results[0]["degree_results"] if not row["held_out"]]
    expected_training_window = [row["degree"] for row in training_rows]
    if expected_training_window != list(range(spec.degrees.start, training_stop + 1)):
        raise ValueError("independent validator did not cover the entire training window")
    if any(row["verified_through"] != training_stop for row in candidates):
        raise ValueError("search candidate's claimed verified degree differs from its question window")

    return {
        "format": VALIDATION_FORMAT,
        "version": VALIDATION_VERSION,
        "benchmark_fingerprint": search_record["benchmark_fingerprint"],
        "search_classification": search_record["classification"],
        "validation_classification": "independent_all_tuples_enumeration_with_held_out_degrees",
        "independent_enumerator": "experiments.reference_ascent literal all-tuples definitions",
        "target_map_imported": False,
        "production_class_generators_imported": False,
        "training_degrees_rechecked": [spec.degrees.start, training_stop],
        "held_out_degrees": list(range(training_stop + 1, HELD_OUT_THROUGH + 1)),
        "degree_counts": degree_counts,
        "count_vectors_match": all(row["source_count"] == row["target_count"] for row in degree_counts),
        "candidate_results": candidate_results,
        "all_candidates_pass_training_window": all(row["passes_training_window"] for row in candidate_results),
        "any_candidate_passes_held_out_degrees": any(row["passes_held_out_degrees"] for row in candidate_results),
        "proof_status": "not_proved",
        "interpretation": (
            "The search result was checked against independently enumerated class sets, including held-out degrees. "
            "The transformation implementation is the generated selector sweep; finite verification is not a proof."
        ),
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("search_record", type=Path, help="JSON output from am_n12_blind_search.py")
    parser.add_argument("--output", type=Path, help="write independent validation JSON here")
    args = parser.parse_args(argv)
    result = validate(json.loads(args.search_record.read_text(encoding="utf-8")))
    encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    if not result["count_vectors_match"] or not result["all_candidates_pass_training_window"]:
        raise SystemExit("independent training-window validation failed")
    if not result["any_candidate_passes_held_out_degrees"]:
        raise SystemExit("no blind-search candidate passed the held-out degrees")


if __name__ == "__main__":
    main()
