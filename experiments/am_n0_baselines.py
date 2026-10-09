"""Reproducible baselines for the AM-N0 research comparison.

This file reproduces small published examples at the level of their finite
mathematical claims, then contrasts them with a blind, finite transformation
search in the ascent-sequence engine.  It does not import Sage,
comb_spec_searcher, or an LLM synthesis service.

Run with::

    python experiments/am_n0_baselines.py

Every successful map result is still finite evidence, not a theorem.
"""

from __future__ import annotations

from collections import Counter
from itertools import combinations, product
from itertools import permutations
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ac import (
    Avoid,
    BlockSchemaT,
    FibreGapPack,
    Modified,
    Modified111BlockBijection,
    Revised,
    analyze_finite_map,
    enumerate_block_schemas,
    evaluate_bijection_candidate,
    synthesize_bijections,
)
from ac.generate.universes import modified_via_hat, revised_sequences


def perfect_matchings(vertices: tuple[int, ...]):
    """Generate perfect matchings of an ordered finite set."""
    if not vertices:
        yield ()
        return
    first = vertices[0]
    for index in range(1, len(vertices)):
        partner = vertices[index]
        rest = vertices[1:index] + vertices[index + 1 :]
        for matching in perfect_matchings(rest):
            yield ((first, partner),) + matching


def matching_nesting_crossing(matching: tuple[tuple[int, int], ...]) -> tuple[int, int]:
    """Return the nesting and crossing counts for one perfect matching."""
    nestings = 0
    crossings = 0
    for first, second in combinations(matching, 2):
        (a, b), (c, d) = sorted((first, second))
        if a < c < d < b:
            nestings += 1
        elif a < c < b < d:
            crossings += 1
    return nestings, crossings


def reproduce_findstat_matching_example(max_pairs: int = 4) -> dict:
    """Recompute FindStat's nesting/crossing equidistribution data locally.

    FindStat's documentation submits all perfect matchings through four pairs
    and searches the database for equidistributed statistics.  This routine
    recomputes the finite input data and exact distributions, without querying
    FindStat or reproducing its database ranking.
    """
    levels = []
    for pairs in range(max_pairs + 1):
        objects = tuple(perfect_matchings(tuple(range(2 * pairs))))
        values = tuple(matching_nesting_crossing(matching) for matching in objects)
        nesting_distribution = Counter(nestings for nestings, _ in values)
        crossing_distribution = Counter(crossings for _, crossings in values)
        levels.append(
            {
                "pairs": pairs,
                "object_count": len(objects),
                "nesting_distribution": dict(sorted(nesting_distribution.items())),
                "crossing_distribution": dict(sorted(crossing_distribution.items())),
                "equidistributed": nesting_distribution == crossing_distribution,
            }
        )
    return {
        "example": "FindStat perfect-matching nestings versus crossings",
        "pairs_tested": list(range(max_pairs + 1)),
        "total_object_inputs": sum(level["object_count"] for level in levels),
        "all_levels_equidistributed": all(level["equidistributed"] for level in levels),
        "levels": levels,
        "scope": "local exact recomputation; FindStat's online search/ranking was not run",
    }


def binary_words(degree: int):
    return ("".join(bits) for bits in product("01", repeat=degree))


def avoids_factor(word: str, pattern: str) -> bool:
    return pattern not in word


def binary_avoidance_counts(pattern: str, through: int) -> tuple[int, ...]:
    return tuple(
        sum(avoids_factor(word, pattern) for word in binary_words(degree))
        for degree in range(through + 1)
    )


def bit_complement(word: str) -> str:
    return word.translate(str.maketrans("01", "10"))


def reproduce_comb_ex_binary_word_examples(through: int = 10, bijection_through: int = 4) -> dict:
    """Recompute the published binary-word count and bijection controls.

    The Combinatorial Exploration example reports counts for words avoiding
    ``bb`` and asks its ``Bijection.construct`` routine for a map between
    ``00``- and ``11``-avoiding binary words, checking inverse recovery through
    degree four.  We verify those finite claims directly using bit complement;
    this is not a run of the external specification-search algorithm.
    """
    avoid_11 = binary_avoidance_counts("11", through)
    avoid_00 = binary_avoidance_counts("00", through)
    bijection_checks = 0
    for degree in range(bijection_through + 1):
        for word in binary_words(degree):
            if not avoids_factor(word, "00"):
                continue
            image = bit_complement(word)
            assert avoids_factor(image, "11")
            assert bit_complement(image) == word
            bijection_checks += 1
    recurrence_holds = all(
        avoid_11[degree] == avoid_11[degree - 1] + avoid_11[degree - 2]
        for degree in range(2, len(avoid_11))
    )
    return {
        "example": "Combinatorial Exploration consecutive-pattern words",
        "avoiding_11_counts_n0_to_n10": list(avoid_11),
        "avoiding_00_counts": list(avoid_00),
        "counts_equal": avoid_11 == avoid_00,
        "reported_bb_sequence_reproduced": list(avoid_11) == [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144],
        "recurrence_a_n_equals_a_n_minus_1_plus_a_n_minus_2": recurrence_holds,
        "bit_complement_bijection_checked_through": bijection_through,
        "source_objects_round_trip_checked": bijection_checks,
        "scope": "finite example outputs recomputed locally; comb_spec_searcher was not run",
    }


def longest_increasing_subsequence_length(values: tuple[int, ...]) -> int:
    """Return LIS length using the patience-sorting tails array."""
    from bisect import bisect_left

    tails: list[int] = []
    for value in values:
        index = bisect_left(tails, value)
        if index == len(tails):
            tails.append(value)
        else:
            tails[index] = value
    return len(tails)


def permutation_rotation(permutation: tuple[int, ...]) -> tuple[int, ...]:
    """Conjugate a permutation by the long cycle, as in the toolkit example."""
    size = len(permutation)
    return tuple(
        permutation[(index + 1) % size] - 1
        if permutation[(index + 1) % size] != 1
        else size
        for index in range(size)
    )


def reproduce_bijectionist_toolkit_rotation_example() -> dict:
    """Reproduce the n=4 forced-value argument in the toolkit paper.

    The paper's rotation-invariance constraint makes a candidate statistic
    constant on rotation orbits.  For S_4, parity of the LIS-value
    multiplicities forces its four values 1,2,3,4 to occur on the four
    rotation-fixed permutations, one each.  This is a finite constraint
    deduction, not a run of the Sage ILP implementation.
    """
    objects = tuple(permutations(range(1, 5)))
    fixed = tuple(permutation for permutation in objects if permutation_rotation(permutation) == permutation)
    distribution = Counter(longest_increasing_subsequence_length(permutation) for permutation in objects)
    forced_fixed_values = tuple(
        value for value, multiplicity in sorted(distribution.items()) if multiplicity % 2 == 1
    )
    return {
        "example": "Bijectionist's Toolkit S_4 rotation-invariant LIS statistic",
        "permutation_count": len(objects),
        "lis_distribution": dict(sorted(distribution.items())),
        "rotation_fixed_permutations": [list(permutation) for permutation in fixed],
        "values_forced_onto_fixed_points_by_orbit_parity": list(forced_fixed_values),
        "one_of_each_value_forced": len(fixed) == 4 and forced_fixed_values == (1, 2, 3, 4),
        "scope": "published finite deduction recomputed directly; Sage Bijectionist's Toolkit ILP was not run",
    }


def reproduce_ascent_shifted_map_search(through: int = 5) -> dict:
    """Compare counts, then search 108 generic +2 block recipes without a seed."""
    source = Modified() & Avoid("111")
    target = Revised() & Avoid("111")
    source_counts = []
    target_counts = []
    source_objects = 0
    for degree in range(1, through + 1):
        source_count = sum(source.holds(word) for word in modified_via_hat(degree))
        target_count = sum(target.holds(word) for word in revised_sequences(degree + 2))
        source_counts.append(source_count)
        target_counts.append(target_count)
        source_objects += source_count

    recipes = enumerate_block_schemas(2)
    report = synthesize_bijections(
        source,
        target,
        universe=modified_via_hat,
        target_universe=revised_sequences,
        degree_shift=2,
        atoms=recipes,
        max_cost=4,
        through=through,
        keep=len(recipes),
    )
    reference = Modified111BlockBijection()
    matches_reference = []
    for candidate in report.exact:
        if not isinstance(candidate.transform, BlockSchemaT):
            continue
        agreement = all(
            candidate.transform.apply(word).output.values == reference.apply(word).output.values
            for degree in range(1, through + 1)
            for word in modified_via_hat(degree)
            if source.holds(word)
        )
        if agreement:
            matches_reference.append(repr(candidate.transform))

    return {
        "example": "AC M_n(111) to R_(n+2)(111) bounded map search",
        "source_degrees": [1, through],
        "target_degree_shift": 2,
        "source_counts": source_counts,
        "target_counts": target_counts,
        "count_vectors_match": source_counts == target_counts,
        "source_objects_checked_per_candidate": source_objects,
        "grammar": "all generated BlockSchemaT recipes with degree shift +2",
        "grammar_size": len(recipes),
        "reference_map_seeded": False,
        "normalized_candidates_tested": report.normalized_candidates,
        "finite_bijection_candidates": [repr(candidate.transform) for candidate in report.exact],
        "candidates_agreeing_with_registered_map_on_every_source": matches_reference,
        "verified_through": through,
        "scope": "finite exhaustive search in the documented 108-recipe grammar",
    }


def reproduce_near_bijection_failure(through: int = 7) -> dict:
    """Retain a negative control where a plausible map first collides at n=7."""
    source = Modified() & Avoid("2122")
    target = Modified() & Avoid("2212")
    candidate = FibreGapPack(2, 1, side="right")
    evaluation = evaluate_bijection_candidate(
        candidate,
        source,
        target,
        universe=modified_via_hat,
        through=through,
    )
    finite = analyze_finite_map(
        candidate,
        source,
        target,
        universe=modified_via_hat,
        n=through,
    )
    return {
        "example": "AC 2122/2212 near-bijection negative control",
        "verified_through": evaluation.verified_through,
        "first_failure": evaluation.failure.kind.value if evaluation.failure else None,
        "failure_degree": evaluation.failure.n if evaluation.failure else None,
        "source_witness": list(evaluation.failure.source.values) if evaluation.failure and evaluation.failure.source else None,
        "image_witness": list(evaluation.failure.output.values) if evaluation.failure and evaluation.failure.output else None,
        "collision_detail": evaluation.failure.detail if evaluation.failure else None,
        "collision_fibres": [
            {"image": list(image.values), "sources": [list(word.values) for word in preimages]}
            for image, preimages in finite.collisions
        ],
        "missing_target_count": len(finite.missing_targets),
        "missing_targets": [list(word.values) for word in finite.missing_targets],
        "scope": "finite candidate refutation; not a refutation of the class equivalence",
    }


def run_baselines() -> dict:
    report = {
        "findstat": reproduce_findstat_matching_example(),
        "combinatorial_exploration": reproduce_comb_ex_binary_word_examples(),
        "bijectionist_toolkit": reproduce_bijectionist_toolkit_rotation_example(),
        "ascent_transformation_search": reproduce_ascent_shifted_map_search(),
        "near_bijection_negative_control": reproduce_near_bijection_failure(),
    }
    assert report["findstat"]["all_levels_equidistributed"]
    assert report["combinatorial_exploration"]["reported_bb_sequence_reproduced"]
    assert report["combinatorial_exploration"]["counts_equal"]
    assert report["bijectionist_toolkit"]["one_of_each_value_forced"]
    assert report["ascent_transformation_search"]["count_vectors_match"]
    assert report["ascent_transformation_search"]["candidates_agreeing_with_registered_map_on_every_source"]
    assert report["near_bijection_negative_control"]["first_failure"] == "collision"
    assert report["near_bijection_negative_control"]["failure_degree"] == 7
    return report


if __name__ == "__main__":
    print(json.dumps(run_baselines(), indent=2, sort_keys=True))
