"""Bounded search for transformation families across class/offset scenarios.

Each candidate program is evaluated against every requested scenario. Results
therefore distinguish a map that fits one avoidance class from a reusable map
family that survives several class and degree-offset tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

from ac.discovery.synthesis import transformation_cost, _candidate_key
from ac.discovery.transformation_search import (
    GRAMMAR_VERSION,
    ProgramExpansionLimit,
    TransformationGrammarSpec,
    TransformationSearchSpec,
    _evaluate,
    _evaluation_data,
    _precompute,
    generate_transformation_atoms,
    iter_typed_transform_programs,
    transformation_grammar_manifest,
)


FAMILY_SEARCH_FORMAT = "ascent-machine-transformation-family-search"
FAMILY_SEARCH_VERSION = 2
MAX_FAMILY_SCENARIOS = 32
MAX_FAMILY_CANDIDATES = 1_000_000
MAX_FAMILY_ENUMERATION = 50_000_000
MAX_FAMILY_CLASS_OBJECTS = 10_000_000
MAX_FAMILY_EVALUATION = 1_000_000_000


@dataclass(frozen=True)
class TransformationFamilySearchSpec:
    """A reproducible matrix of class and degree-offset map questions."""

    scenarios: tuple[TransformationSearchSpec, ...]
    candidate_budget: int = 1_000
    enumeration_budget: int = 5_000_000
    class_object_budget: int = 1_000_000
    evaluation_budget: int = 10_000_000

    def __post_init__(self) -> None:
        scenarios = tuple(self.scenarios)
        if not 2 <= len(scenarios) <= MAX_FAMILY_SCENARIOS:
            raise ValueError(f"family search requires 2–{MAX_FAMILY_SCENARIOS} scenarios")
        if any(not isinstance(scenario, TransformationSearchSpec) for scenario in scenarios):
            raise ValueError("every family scenario must be a TransformationSearchSpec")
        if len({scenario.fingerprint for scenario in scenarios}) != len(scenarios):
            raise ValueError("family scenarios must have distinct fingerprints")
        first = scenarios[0]
        if any(
            scenario.grammar != first.grammar or scenario.grammar_version != first.grammar_version
            for scenario in scenarios[1:]
        ):
            raise ValueError("family scenarios must share one transformation grammar")
        for name, value, low, high in (
            ("candidate_budget", self.candidate_budget, 1, MAX_FAMILY_CANDIDATES),
            ("enumeration_budget", self.enumeration_budget, 1, MAX_FAMILY_ENUMERATION),
            ("class_object_budget", self.class_object_budget, 1, MAX_FAMILY_CLASS_OBJECTS),
            ("evaluation_budget", self.evaluation_budget, 1, MAX_FAMILY_EVALUATION),
        ):
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{name} must be an integer from {low} through {high}")
        object.__setattr__(self, "scenarios", scenarios)

    @property
    def grammar(self):
        return self.scenarios[0].grammar

    @property
    def grammar_version(self) -> str:
        return self.scenarios[0].grammar_version

    @classmethod
    def from_grid(
        cls,
        source_classes,
        target_classes,
        degrees,
        grammar: TransformationGrammarSpec,
        *,
        offset_pairs=((0, 0),),
        candidate_budget: int = 1_000,
        enumeration_budget: int = 5_000_000,
        class_object_budget: int = 1_000_000,
        evaluation_budget: int = 10_000_000,
        grammar_version: str = GRAMMAR_VERSION,
    ) -> "TransformationFamilySearchSpec":
        """Build a bounded Cartesian scan over classes and source/target offsets."""
        source_classes = tuple(source_classes)
        target_classes = tuple(target_classes)
        offset_pairs = tuple(tuple(pair) for pair in offset_pairs)
        if not source_classes or not target_classes or not offset_pairs:
            raise ValueError("class and offset grids must be nonempty")
        scenario_count = len(source_classes) * len(target_classes) * len(offset_pairs)
        if scenario_count > MAX_FAMILY_SCENARIOS:
            raise ValueError(
                f"class/offset grid has {scenario_count} scenarios; limit is {MAX_FAMILY_SCENARIOS}"
            )
        scenarios = tuple(
            TransformationSearchSpec(
                source, target, degrees, grammar,
                source_offset, target_offset, grammar_version,
            )
            for source in source_classes
            for target in target_classes
            for source_offset, target_offset in offset_pairs
        )
        return cls(
            scenarios, candidate_budget, enumeration_budget,
            class_object_budget, evaluation_budget,
        )

    def to_dict(self) -> dict:
        return {
            "format": FAMILY_SEARCH_FORMAT,
            "version": FAMILY_SEARCH_VERSION,
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
            "candidate_budget": self.candidate_budget,
            "enumeration_budget": self.enumeration_budget,
            "class_object_budget": self.class_object_budget,
            "evaluation_budget": self.evaluation_budget,
        }

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @property
    def fingerprint(self) -> str:
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, raw: dict) -> "TransformationFamilySearchSpec":
        expected = {
            "format", "version", "scenarios", "candidate_budget", "enumeration_budget",
            "class_object_budget", "evaluation_budget",
        }
        if not isinstance(raw, dict) or set(raw) != expected:
            raise ValueError("transformation-family fields do not match the version-1 schema")
        if raw["format"] != FAMILY_SEARCH_FORMAT or type(raw["version"]) is not int or raw["version"] != FAMILY_SEARCH_VERSION:
            raise ValueError("unsupported transformation-family format or version")
        if not isinstance(raw["scenarios"], list):
            raise ValueError("family scenarios must be an array")
        return cls(
            tuple(TransformationSearchSpec.from_dict(item) for item in raw["scenarios"]),
            raw["candidate_budget"], raw["enumeration_budget"],
            raw["class_object_budget"], raw["evaluation_budget"],
        )


class _PreparationContext:
    def __init__(self, context, state, scenario_index, scenario_count):
        self.context = context
        self.state = state
        self.scenario_index = scenario_index
        self.scenario_count = scenario_count

    def checkpoint(self, state, progress=None):
        combined = dict(self.state)
        combined["stage"] = "preparing_scenarios"
        combined["scenario_index"] = self.scenario_index
        combined["scenario_preparation"] = dict(progress or {})
        self.context.checkpoint(combined, {
            "stage": "preparing scenarios",
            "scenario_index": self.scenario_index,
            "scenario_count": self.scenario_count,
            **(progress or {}),
        })

    def check_control(self):
        self.context.check_control()


def _interleaved_programs(spec, shifts, atoms_by_shift, candidate_limit, state):
    streams = {}
    for shift in shifts:
        streams[shift] = iter(iter_typed_transform_programs(
            atoms_by_shift[shift],
            max_cost=spec.grammar.max_cost,
            max_steps=spec.grammar.max_steps,
            expected_length_shift=shift,
            max_candidates=candidate_limit,
            expansion_budget=spec.grammar.expansion_budget,
        ))
    active = list(shifts)
    seen = set()
    while active and len(seen) < candidate_limit:
        made_progress = False
        for shift in tuple(active):
            if shift not in active:
                continue
            try:
                program = next(streams[shift])
            except StopIteration:
                active.remove(shift)
                continue
            except ProgramExpansionLimit:
                active.remove(shift)
                state["expansion_limited_shifts"].append(shift)
                continue
            made_progress = True
            key = _candidate_key(program)
            if key in seen:
                continue
            seen.add(key)
            yield program, shift
            if len(seen) >= candidate_limit:
                break
        if not made_progress and active:
            break
    state["streams_exhausted"] = not active


def _example_map_preview(transform, data, scenario):
    """Return one auditable, bounded application trace without evaluating the map again."""
    base_degree = scenario.degrees.start
    source_words = data[base_degree][0]
    for source in source_words[:16]:
        if not transform.defined_on(source):
            continue
        applied = transform.apply(source)
        preview = {
            "scenario_fingerprint": scenario.fingerprint,
            "base_degree": base_degree,
            "source_degree": base_degree + scenario.source_offset,
            "target_degree": base_degree + scenario.target_offset,
            "source": {"values": list(source.values), "height": source.height},
            "output": {
                "values": list(applied.output.values),
                "height": applied.output.height,
            },
            "position_map": list(applied.position_map),
            "value_map": None if applied.value_map is None else list(applied.value_map),
            "created_positions": list(applied.created_positions),
        }
        from ac.algebra.block_schemas import BlockSchemaT
        if isinstance(transform, BlockSchemaT):
            preview["block_trace"] = transform.trace(source)
        return preview
    return None


def run_worker_search(job, context) -> dict:
    """Worker handler: test generated programs across a bounded scenario matrix."""
    spec = job.question
    if not isinstance(spec, TransformationFamilySearchSpec):
        raise ValueError("transformation-family worker requires a family-search specification")

    saved = dict(job.checkpoint)
    if saved.get("family_search_version") != FAMILY_SEARCH_VERSION:
        saved = {}
    prep_state = saved or {
        "family_search_version": FAMILY_SEARCH_VERSION,
        "next_candidate_index": 0,
        "examined": 0,
        "exact_candidate_count": 0,
        "exact_candidates": [],
        "finite_behavior_groups": {},
        "ranked_candidates": [],
        "scenario_match_counts": [0] * len(spec.scenarios),
    }
    datasets = []
    scenario_metrics = []
    total_enumerated = 0
    total_retained = 0
    for index, scenario in enumerate(spec.scenarios, start=1):
        remaining_enumeration = spec.enumeration_budget - total_enumerated
        remaining_class_objects = spec.class_object_budget - total_retained
        if remaining_enumeration < 1 or remaining_class_objects < 1:
            raise ValueError("family preparation exceeded its aggregate enumeration or class-object budget")
        prep_context = _PreparationContext(context, prep_state, index, len(spec.scenarios))
        data, metrics = _precompute(
            scenario,
            context=prep_context,
            checkpoint={},
            enumeration_budget=remaining_enumeration,
            class_object_budget=remaining_class_objects,
        )
        total_enumerated += metrics["enumerated_universe_objects"]
        total_retained += metrics["retained_class_objects"]
        datasets.append(data)
        scenario_metrics.append(metrics)
        prep_state = dict(prep_state)
        prep_state.update({"stage": "preparing_scenarios", "scenario_index": index})
        context.checkpoint(prep_state, {
            "stage": "prepared scenario",
            "scenario_index": index,
            "scenario_count": len(spec.scenarios),
            "enumerated_universe_objects": total_enumerated,
            "retained_class_objects": total_retained,
        })

    total_source_objects = sum(metric["source_class_objects"] for metric in scenario_metrics)
    affordable_candidates = (
        spec.candidate_budget
        if total_source_objects == 0
        else min(spec.candidate_budget, spec.evaluation_budget // total_source_objects)
    )
    if affordable_candidates == 0:
        raise ValueError("family evaluation budget is smaller than one candidate pass across its scenarios")

    start_index = saved.get("next_candidate_index", 0)
    if type(start_index) is not int or not 0 <= start_index <= affordable_candidates:
        raise ValueError("family-search checkpoint has an invalid candidate cursor")
    examined = int(saved.get("examined", start_index))
    exact_count = int(saved.get("exact_candidate_count", 0))
    exact_candidates = list(saved.get("exact_candidates", []))
    finite_behavior_groups = dict(saved.get("finite_behavior_groups", {}))
    ranked_candidates = [
        (
            row["matching_scenario_count"],
            sum(item["verified_through"] for item in row["scenario_results"]),
            row,
        )
        for row in saved.get("ranked_candidates", [])
    ]
    scenario_match_counts = list(saved.get("scenario_match_counts", [0] * len(spec.scenarios)))
    if len(scenario_match_counts) != len(spec.scenarios):
        raise ValueError("family-search checkpoint has an invalid scenario counter table")

    shifts = tuple(sorted({scenario.degree_shift for scenario in spec.scenarios}))
    atoms_by_shift = {
        shift: generate_transformation_atoms(spec.grammar, expected_length_shift=shift)
        for shift in shifts
    }
    generation_state = {"expansion_limited_shifts": [], "streams_exhausted": False}
    iterator = _interleaved_programs(
        spec, shifts, atoms_by_shift, affordable_candidates, generation_state,
    )
    next_index = start_index
    interval = 25
    keep = 25
    for index, (transform, seed_shift) in enumerate(iterator):
        if index < start_index:
            continue
        if index >= affordable_candidates:
            break
        if examined % 10 == 0:
            context.check_control()
        scenario_results = []
        matching_scenarios = []
        verified_sum = 0
        for scenario_index, (scenario, data) in enumerate(zip(spec.scenarios, datasets)):
            evaluation = _evaluate(transform, data, scenario, context=context)
            source_words = data[scenario.degrees.start][0]
            example_source = source_words[0] if source_words else None
            evaluation_row = _evaluation_data(evaluation, scenario, example_source)
            scenario_results.append({
                "scenario_index": scenario_index,
                "specification_fingerprint": scenario.fingerprint,
                "source_class": scenario.source.describe(),
                "target_class": scenario.target.describe(),
                "source_offset": scenario.source_offset,
                "target_offset": scenario.target_offset,
                "degree_shift": scenario.degree_shift,
                "finite_match": evaluation.exact,
                "verified_through": evaluation.verified_through,
                "evaluation": evaluation_row,
            })
            verified_sum += evaluation.verified_through
            if evaluation.exact:
                scenario_match_counts[scenario_index] += 1
                matching_scenarios.append(scenario.fingerprint)
        match_count = len(matching_scenarios)
        finite_map_fingerprints = [
            scenario_result["evaluation"].get("finite_map_fingerprint")
            for scenario_result in scenario_results
        ]
        finite_family_fingerprint = None
        if match_count == len(spec.scenarios) and all(finite_map_fingerprints):
            finite_family_payload = [
                [scenario.fingerprint, finite_map_fingerprint]
                for scenario, finite_map_fingerprint in zip(spec.scenarios, finite_map_fingerprints)
            ]
            finite_family_fingerprint = sha256(json.dumps(
                finite_family_payload, sort_keys=True, separators=(",", ":"),
            ).encode("utf-8")).hexdigest()
        signature = transform.signature
        row = {
            "program": repr(transform),
            "cost": transformation_cost(transform),
            "signature": {
                "delta_length": signature.delta_length,
                "delta_height": signature.delta_height,
                "partial": signature.partial,
                "preserves_occurrence_ids": signature.preserves_occurrence_ids,
            },
            "first_generated_in_shift_group": seed_shift,
            "scenario_count": len(spec.scenarios),
            "matching_scenario_count": match_count,
            "matching_scenarios": matching_scenarios,
            "bijection_on_every_scenario": match_count == len(spec.scenarios),
            "finite_family_map_fingerprint": finite_family_fingerprint,
            "scenario_results": scenario_results,
            "proof_status": "not_proved",
        }
        example_preview = _example_map_preview(transform, datasets[0], spec.scenarios[0])
        if example_preview is not None:
            row["example_map_preview"] = example_preview
        next_index = index + 1
        examined += 1
        if match_count == len(spec.scenarios):
            exact_count += 1
            if finite_family_fingerprint is not None:
                group = finite_behavior_groups.setdefault(finite_family_fingerprint, {
                    "finite_family_map_fingerprint": finite_family_fingerprint,
                    "candidate_count": 0,
                    "example_program": row["program"],
                })
                group["candidate_count"] += 1
            exact_candidates.append(row)
            exact_candidates.sort(key=lambda candidate: (candidate["cost"], candidate["program"]))
            exact_candidates = exact_candidates[:keep]
        ranked_candidates.append((match_count, verified_sum, row))
        ranked_candidates.sort(key=lambda item: (-item[0], -item[1], item[2]["cost"], item[2]["program"]))
        ranked_candidates = ranked_candidates[:keep]

        if examined % interval == 0 or (start_index == 0 and next_index == 1):
            checkpoint_state = {
                "family_search_version": FAMILY_SEARCH_VERSION,
                "next_candidate_index": next_index,
                "examined": examined,
                "exact_candidate_count": exact_count,
                "exact_candidates": exact_candidates,
                "finite_behavior_groups": finite_behavior_groups,
                "ranked_candidates": [item[2] for item in ranked_candidates],
                "scenario_match_counts": scenario_match_counts,
            }
            context.checkpoint(checkpoint_state, {
                "stage": "testing programs across scenarios",
                "candidates_tested": examined,
                "candidate_budget": affordable_candidates,
                "all_scenario_matches": exact_count,
            })

    candidate_space_exhausted = (
        generation_state["streams_exhausted"]
        and not generation_state["expansion_limited_shifts"]
        and next_index < affordable_candidates
    )
    evaluation_budget_limited = (
        affordable_candidates < spec.candidate_budget
        and next_index >= affordable_candidates
        and not candidate_space_exhausted
    )
    final_state = {
        "family_search_version": FAMILY_SEARCH_VERSION,
        "next_candidate_index": next_index,
        "examined": examined,
        "exact_candidate_count": exact_count,
        "exact_candidates": exact_candidates,
        "finite_behavior_groups": finite_behavior_groups,
        "ranked_candidates": [item[2] for item in ranked_candidates],
        "scenario_match_counts": scenario_match_counts,
    }
    context.checkpoint(final_state, {
        "stage": "family search complete",
        "candidates_tested": examined,
        "candidate_budget": affordable_candidates,
        "all_scenario_matches": exact_count,
    })

    return {
        "specification_fingerprint": spec.fingerprint,
        "family_search_version": FAMILY_SEARCH_VERSION,
        "grammar_version": spec.grammar_version,
        "grammar_manifest": transformation_grammar_manifest(
            spec.grammar, grammar_version=spec.grammar_version,
        ),
        "scenario_count": len(spec.scenarios),
        "scenario_specifications": [
            {
                "index": index,
                "fingerprint": scenario.fingerprint,
                "source_class": scenario.source.describe(),
                "target_class": scenario.target.describe(),
                "source_offset": scenario.source_offset,
                "target_offset": scenario.target_offset,
                "degree_shift": scenario.degree_shift,
                "base_degrees": [scenario.degrees.start, scenario.degrees.stop],
            }
            for index, scenario in enumerate(spec.scenarios)
        ],
        "degree_shifts_searched": list(shifts),
        "generated_atom_count_by_shift": {str(shift): len(atoms_by_shift[shift]) for shift in shifts},
        "generated_atom_count_total_by_shift": sum(len(atoms_by_shift[shift]) for shift in shifts),
        "enumerated_universe_objects": total_enumerated,
        "retained_class_objects": total_retained,
        "source_class_objects": total_source_objects,
        "candidate_budget": spec.candidate_budget,
        "effective_candidate_budget": affordable_candidates,
        "evaluation_budget": spec.evaluation_budget,
        "candidates_tested": examined,
        "evaluation_budget_limited": evaluation_budget_limited,
        "search_ended_by_expansion_budget": bool(generation_state["expansion_limited_shifts"]),
        "expansion_limited_degree_shifts": generation_state["expansion_limited_shifts"],
        "candidate_space_exhausted": candidate_space_exhausted,
        "scenario_match_counts": scenario_match_counts,
        "exact_candidate_count": exact_count,
        "exact_candidates": exact_candidates,
        "finite_behavior_group_count": len(finite_behavior_groups),
        "finite_behavior_groups": sorted(
            finite_behavior_groups.values(),
            key=lambda group: (-group["candidate_count"], group["finite_family_map_fingerprint"]),
        ),
        "finite_behavior_scope": (
            "Fingerprints identify identical complete maps only over the listed finite class and degree-offset windows; "
            "they do not establish equivalence outside those windows."
        ),
        "ranked_candidates": [item[2] for item in ranked_candidates],
        "status": "finite_cross_scenario_search",
        "proof_status": "not_proved",
        "interpretation": "A program matching every listed class and offset scenario is finite evidence only; it does not prove a general transformation family.",
        "proof_obligations": [
            "prove the map works for every source object in each class family",
            "prove the requested degree offset for every input size",
            "prove injectivity and surjectivity or provide a valid inverse",
            "justify extension from the searched class and offset scenarios to any broader family",
        ],
    }
