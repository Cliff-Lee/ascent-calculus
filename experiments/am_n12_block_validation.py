"""Independently re-enumerate and validate the seeded block reconstruction.

Run this after ``am_n12_block_reconstruction.py`` has saved its result. The
validation is independent of production class generators and the registered
paper map, though it deliberately validates a seeded-operation reconstruction.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ac.algebra.block_schemas import enumerate_block_schemas
from ac.core.word import ChainWord
from ac.discovery.specification import ClassSpec
from experiments.reference_ascent import contains_pattern, modified, revised


SEARCH_FORMAT = "ascent-machine-am-n12-block-reconstruction"
VALIDATION_FORMAT = "ascent-machine-am-n12-block-validation"
VALIDATION_VERSION = 1
HELD_OUT_DEGREE = 6


def _fingerprint(value) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _class_data(degree: int):
    source = {values for values in modified(degree) if not contains_pattern(values, (1, 1, 1))}
    target = {values for values in revised(degree + 2) if not contains_pattern(values, (1, 1, 1))}
    return source, target


def validate(search_record: dict) -> dict:
    if search_record.get("format") != SEARCH_FORMAT or search_record.get("version") != 1:
        raise ValueError("input is not a supported AM-N12 block-reconstruction result")
    question = search_record.get("benchmark_question")
    if not isinstance(question, dict) or _fingerprint(question) != search_record.get("benchmark_fingerprint"):
        raise ValueError("block-reconstruction question fingerprint is invalid")
    if search_record.get("search_guidance", {}).get("reference_map_provided") is not False:
        raise ValueError("block-reconstruction record does not document a withheld reference map")
    expected_question = {
        "format": SEARCH_FORMAT,
        "version": 1,
        "source": ClassSpec.build("modified", [{"mode": "avoid", "pattern": "111"}]).to_dict(),
        "target": ClassSpec.build("revised", [{"mode": "avoid", "pattern": "111"}]).to_dict(),
        "degrees": {"start": 1, "stop": 4},
        "source_offset": 0,
        "target_offset": 2,
        "maximum_cost": 4,
        "candidate_catalogue_count": 108,
    }
    if any(question.get(key) != value for key, value in expected_question.items()):
        raise ValueError("block-reconstruction question differs from the registered AM-N12 benchmark")

    recipes = enumerate_block_schemas(2)
    catalogue_fingerprint = sha256(
        json.dumps([repr(recipe) for recipe in recipes], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if (
        len(recipes) != question.get("candidate_catalogue_count")
        or catalogue_fingerprint != question.get("candidate_catalogue_fingerprint")
    ):
        raise ValueError("candidate recipe catalogue does not match the reconstruction record")
    by_program = {repr(recipe): recipe for recipe in recipes}
    candidates = search_record.get("finite_bijection_candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("block reconstruction did not retain any finite map candidates")
    if any(item.get("program") not in by_program for item in candidates):
        raise ValueError("a reported candidate is not in the recorded recipe catalogue")

    start, training_stop = question["degrees"]["start"], question["degrees"]["stop"]
    if (start, training_stop) != (1, 4):
        raise ValueError("this validator expects the fixed training window n=1..4")
    candidate_status = {item["program"]: {"program": item["program"], "degrees": []} for item in candidates}
    degree_counts = []
    for degree in range(start, HELD_OUT_DEGREE + 1):
        source, target = _class_data(degree)
        row = {
            "base_degree": degree,
            "source_degree": degree,
            "target_degree": degree + 2,
            "source_count": len(source),
            "target_count": len(target),
            "count_match": len(source) == len(target),
            "held_out": degree > training_stop,
        }
        degree_counts.append(row)
        for candidate in candidates:
            program = candidate["program"]
            recipe = by_program[program]
            images = []
            failure = None
            for values in sorted(source):
                try:
                    image = recipe.apply(ChainWord.of(values)).output.values
                except (ValueError, IndexError, TypeError) as exc:
                    failure = {"kind": "undefined", "source": list(values), "detail": str(exc)}
                    break
                if image not in target:
                    failure = {"kind": "outside_target", "source": list(values), "output": list(image)}
                    break
                images.append(image)
            if failure is None and len(images) != len(set(images)):
                failure = {"kind": "collision", "image_count": len(set(images)), "source_count": len(source)}
            if failure is None and set(images) != target:
                failure = {"kind": "not_surjective", "image_count": len(set(images)), "target_count": len(target)}
            candidate_status[program]["degrees"].append({
                "base_degree": degree,
                "held_out": degree > training_stop,
                "source_count": len(source),
                "target_count": len(target),
                "verified_bijection": failure is None,
                "failure": failure,
            })

    training_rows = [row for row in degree_counts if not row["held_out"]]
    if search_record.get("source_counts") != [row["source_count"] for row in training_rows]:
        raise ValueError("block-search source counts disagree with the independent training enumeration")
    if search_record.get("target_counts") != [row["target_count"] for row in training_rows]:
        raise ValueError("block-search target counts disagree with the independent training enumeration")

    summaries = []
    for program, status in candidate_status.items():
        all_rows = status["degrees"]
        summaries.append({
            "program": program,
            "passes_training_window": all(row["verified_bijection"] for row in all_rows if not row["held_out"]),
            "passes_held_out_degrees": all(row["verified_bijection"] for row in all_rows if row["held_out"]),
            "verified_through_base_degree": max(
                (row["base_degree"] for row in all_rows if row["verified_bijection"]), default=0,
            ),
            "degree_results": all_rows,
        })
    return {
        "format": VALIDATION_FORMAT,
        "version": VALIDATION_VERSION,
        "benchmark_fingerprint": search_record["benchmark_fingerprint"],
        "search_classification": search_record["classification"],
        "validation_classification": "independent_enumeration_with_held_out_degree",
        "independent_enumerator": "experiments.reference_ascent literal all-tuples definitions",
        "target_map_imported": False,
        "training_degrees_rechecked": [start, training_stop],
        "held_out_degrees": list(range(training_stop + 1, HELD_OUT_DEGREE + 1)),
        "degree_counts": degree_counts,
        "count_vectors_match": all(row["count_match"] for row in degree_counts),
        "candidate_results": summaries,
        "all_candidates_pass_training_window": all(row["passes_training_window"] for row in summaries),
        "any_candidate_passes_held_out_degrees": any(row["passes_held_out_degrees"] for row in summaries),
        "proof_status": "not_proved",
        "interpretation": (
            "Candidates were independently re-enumerated on the training window and held-out degree. "
            "The map implementation remains the generated Ascent Machine block recipe; this finite audit is not a proof."
        ),
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("search_record", type=Path, help="JSON output from am_n12_block_reconstruction.py")
    parser.add_argument("--output", type=Path, help="write independent validation JSON here")
    args = parser.parse_args(argv)
    record = json.loads(args.search_record.read_text(encoding="utf-8"))
    result = validate(record)
    encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    if not result["count_vectors_match"] or not result["all_candidates_pass_training_window"]:
        raise SystemExit("independent training-window validation failed")
    if not result["any_candidate_passes_held_out_degrees"]:
        raise SystemExit("no blind-search candidate passed the held-out degree")


if __name__ == "__main__":
    main()
