"""Generated, typed transformation search for finite ascent-sequence questions.

The grammar is deliberately explicit and bounded. It combines definitions of
ascent-sequence structure (first/last occurrences, ascents, descents, and runs)
with the existing transformation calculus. A match is finite evidence only.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import heapq
import json
from itertools import combinations, count, islice
from typing import Iterator

from ac.algebra.transforms import (
    ComplementT,
    CompressLevelsT,
    HatT,
    Identity,
    InsertFreshMaximumT,
    InsertSelectedT,
    InverseHatT,
    InversePrefixLiftT,
    PrefixLiftT,
    RestrictSelectedT,
    ReverseT,
    StandardizeT,
    SweepLiftT,
    Transformation,
)
from ac.discovery.specification import ClassSpec, DegreeWindow, FAMILIES
from ac.discovery.synthesis import (
    CandidateEvaluation,
    FailureKind,
    SynthesisFailure,
    _candidate_key,
    _word_key,
    transformation_cost,
)
from ac.logic.selectors import (
    After,
    AscBottom,
    AscTop,
    Before,
    DescBottom,
    DescTop,
    First,
    Last,
    PositionCuts,
    RawAscBottom,
    RawAscTop,
    RawDescBottom,
    RawDescTop,
    Repeat,
    RunEnd,
    RunStart,
    ScopeFirst,
    ScopeLast,
    Selector,
    SetBinary,
    SetComplement,
    Occ,
)


TRANSFORM_SEARCH_FORMAT = "ascent-machine-transformation-search"
TRANSFORM_SEARCH_VERSION = 1
PREVIOUS_GRAMMAR_VERSION = "ac-definition-grammar-v1"
GRAMMAR_VERSION = "ac-definition-grammar-v2"
SUPPORTED_GRAMMAR_VERSIONS = (PREVIOUS_GRAMMAR_VERSION, GRAMMAR_VERSION)
MAX_TRANSFORM_CANDIDATES = 1_000_000
MAX_TRANSFORM_ATOMS = 25_000
CEGIS_VERSION = 1
MAX_CEGIS_WITNESSES = 512


class ProgramExpansionLimit(RuntimeError):
    """The bounded grammar traversal used its full node budget."""

OPERATION_IDS = (
    "symmetry",
    "canonicalize",
    "hat_sweeps",
    "prefix_lifts",
    "selector_sweeps",
    "selector_restrictions",
    "insert_existing_values",
    "insert_fresh_maximum",
    "block_schemas",
)
DEFAULT_OPERATION_IDS = OPERATION_IDS
SELECTOR_IDS = (
    "scope_first", "scope_last", "first", "last", "repeat",
    "asc_top", "asc_bottom", "raw_asc_top", "raw_asc_bottom",
    "desc_top", "desc_bottom", "raw_desc_top", "raw_desc_bottom",
    "run_start", "run_end",
)


@dataclass(frozen=True)
class TransformationGrammarSpec:
    """Reproducible controls for the generated transformation vocabulary."""

    operations: tuple[str, ...] = DEFAULT_OPERATION_IDS
    selectors: tuple[str, ...] = SELECTOR_IDS
    boolean_selector_algebra: bool = True
    position_bound: int = 6
    occurrence_rank: int = 3
    inserted_value_bound: int = 3
    max_selectors: int = 4_000
    max_atoms: int = MAX_TRANSFORM_ATOMS
    max_cost: int = 4
    max_steps: int = 3
    candidate_budget: int = 5_000
    expansion_budget: int = 25_000
    class_object_budget: int = 250_000
    enumeration_budget: int = 1_000_000
    evaluation_budget: int = 10_000_000

    def __post_init__(self) -> None:
        operations = tuple(sorted(set(self.operations)))
        selectors = tuple(sorted(set(self.selectors)))
        if not operations or any(name not in OPERATION_IDS for name in operations):
            raise ValueError("grammar operations must be chosen from the registered operation ids")
        if any(name not in SELECTOR_IDS for name in selectors):
            raise ValueError("grammar selectors must be chosen from the registered selector ids")
        if type(self.boolean_selector_algebra) is not bool:
            raise ValueError("boolean_selector_algebra must be a boolean")
        for name in (
            "position_bound", "occurrence_rank", "inserted_value_bound", "max_selectors", "max_atoms",
            "max_cost", "max_steps", "candidate_budget", "expansion_budget", "class_object_budget",
            "enumeration_budget", "evaluation_budget",
        ):
            if type(getattr(self, name)) is not int:
                raise ValueError(f"{name} must be an integer")
        if not 1 <= self.position_bound <= 100:
            raise ValueError("position_bound must be between 1 and 100")
        if not 1 <= self.occurrence_rank <= 20:
            raise ValueError("occurrence_rank must be between 1 and 20")
        if not 1 <= self.inserted_value_bound <= 100:
            raise ValueError("inserted_value_bound must be between 1 and 100")
        if not 1 <= self.max_selectors <= 20_000:
            raise ValueError("max_selectors must be between 1 and 20000")
        if not 1 <= self.max_atoms <= MAX_TRANSFORM_ATOMS:
            raise ValueError(f"max_atoms must be between 1 and {MAX_TRANSFORM_ATOMS}")
        if not 0 <= self.max_cost <= 100:
            raise ValueError("max_cost must be between 0 and 100")
        if not 0 <= self.max_steps <= 20:
            raise ValueError("max_steps must be between 0 and 20")
        if not 1 <= self.candidate_budget <= MAX_TRANSFORM_CANDIDATES:
            raise ValueError(f"candidate_budget must be between 1 and {MAX_TRANSFORM_CANDIDATES}")
        if not 1 <= self.expansion_budget <= 10_000_000:
            raise ValueError("expansion_budget must be between 1 and 10000000")
        if not 1 <= self.class_object_budget <= 10_000_000:
            raise ValueError("class_object_budget must be between 1 and 10000000")
        if not 1 <= self.enumeration_budget <= 50_000_000:
            raise ValueError("enumeration_budget must be between 1 and 50000000")
        if not 1 <= self.evaluation_budget <= 1_000_000_000:
            raise ValueError("evaluation_budget must be between 1 and 1000000000")
        object.__setattr__(self, "operations", operations)
        object.__setattr__(self, "selectors", selectors)

    def to_dict(self) -> dict:
        return {
            "operations": list(self.operations),
            "selectors": list(self.selectors),
            "boolean_selector_algebra": self.boolean_selector_algebra,
            "position_bound": self.position_bound,
            "occurrence_rank": self.occurrence_rank,
            "inserted_value_bound": self.inserted_value_bound,
            "max_selectors": self.max_selectors,
            "max_atoms": self.max_atoms,
            "max_cost": self.max_cost,
            "max_steps": self.max_steps,
            "candidate_budget": self.candidate_budget,
            "expansion_budget": self.expansion_budget,
            "class_object_budget": self.class_object_budget,
            "enumeration_budget": self.enumeration_budget,
            "evaluation_budget": self.evaluation_budget,
        }

    @classmethod
    def from_dict(cls, raw: dict) -> "TransformationGrammarSpec":
        expected = {
            "operations", "selectors", "boolean_selector_algebra", "position_bound",
            "occurrence_rank", "inserted_value_bound", "max_selectors", "max_atoms",
            "max_cost", "max_steps", "candidate_budget", "expansion_budget", "class_object_budget",
            "enumeration_budget", "evaluation_budget",
        }
        if not isinstance(raw, dict) or set(raw) != expected:
            raise ValueError("transformation grammar fields do not match the version-1 schema")
        if not isinstance(raw["operations"], list) or not isinstance(raw["selectors"], list):
            raise ValueError("grammar operations and selectors must be arrays")
        return cls(
            tuple(raw["operations"]), tuple(raw["selectors"]), raw["boolean_selector_algebra"],
            raw["position_bound"], raw["occurrence_rank"], raw["inserted_value_bound"],
            raw["max_selectors"], raw["max_atoms"], raw["max_cost"], raw["max_steps"],
            raw["candidate_budget"], raw["expansion_budget"], raw["class_object_budget"],
            raw["enumeration_budget"], raw["evaluation_budget"],
        )


@dataclass(frozen=True)
class TransformationSearchSpec:
    """A class-to-class map search with explicit offsets and grammar bounds."""

    source: ClassSpec
    target: ClassSpec
    degrees: DegreeWindow
    grammar: TransformationGrammarSpec = TransformationGrammarSpec()
    source_offset: int = 0
    target_offset: int = 0
    grammar_version: str = GRAMMAR_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.source, ClassSpec) or not isinstance(self.target, ClassSpec):
            raise ValueError("source and target must be ClassSpec objects")
        if not isinstance(self.degrees, DegreeWindow):
            raise ValueError("degrees must be a DegreeWindow")
        if not isinstance(self.grammar, TransformationGrammarSpec):
            raise ValueError("grammar must be a TransformationGrammarSpec")
        if self.grammar_version not in SUPPORTED_GRAMMAR_VERSIONS:
            raise ValueError("unsupported transformation grammar version")
        if self.grammar_version == PREVIOUS_GRAMMAR_VERSION and "block_schemas" in self.grammar.operations:
            raise ValueError("grammar version 1 specifications cannot select block_schemas")
        if self.source.family not in FAMILIES or self.target.family not in FAMILIES:
            raise ValueError("unsupported ascent-sequence family")
        if type(self.source_offset) is not int or type(self.target_offset) is not int:
            raise ValueError("degree offsets must be integers")
        if self.degrees.start + self.source_offset < 1 or self.degrees.start + self.target_offset < 1:
            raise ValueError("degree offsets make the first tested degree less than 1")

    @property
    def degree_shift(self) -> int:
        return self.target_offset - self.source_offset

    def to_dict(self) -> dict:
        return {
            "format": TRANSFORM_SEARCH_FORMAT,
            "version": TRANSFORM_SEARCH_VERSION,
            "grammar_version": self.grammar_version,
            "source": self.source.to_dict(),
            "target": self.target.to_dict(),
            "degrees": self.degrees.to_dict(),
            "source_offset": self.source_offset,
            "target_offset": self.target_offset,
            "grammar": self.grammar.to_dict(),
        }

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @property
    def fingerprint(self) -> str:
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, raw: dict) -> "TransformationSearchSpec":
        expected = {
            "format", "version", "grammar_version", "source", "target", "degrees",
            "source_offset", "target_offset", "grammar",
        }
        if not isinstance(raw, dict) or set(raw) != expected:
            raise ValueError("transformation-search specification fields do not match the version-1 schema")
        if raw["format"] != TRANSFORM_SEARCH_FORMAT or type(raw["version"]) is not int or raw["version"] != TRANSFORM_SEARCH_VERSION:
            raise ValueError("unsupported transformation-search specification format or version")
        if raw["grammar_version"] not in SUPPORTED_GRAMMAR_VERSIONS:
            raise ValueError("transformation-search specification uses an unknown grammar semantics version")
        return cls(
            ClassSpec.from_dict(raw["source"]), ClassSpec.from_dict(raw["target"]),
            DegreeWindow.from_dict(raw["degrees"]), TransformationGrammarSpec.from_dict(raw["grammar"]),
            raw["source_offset"], raw["target_offset"], raw["grammar_version"],
        )


def _base_selector_catalogue(spec: TransformationGrammarSpec) -> dict[str, Selector]:
    constructors = {
        "scope_first": ScopeFirst,
        "scope_last": ScopeLast,
        "first": First,
        "last": Last,
        "repeat": Repeat,
        "asc_top": AscTop,
        "asc_bottom": AscBottom,
        "raw_asc_top": RawAscTop,
        "raw_asc_bottom": RawAscBottom,
        "desc_top": DescTop,
        "desc_bottom": DescBottom,
        "raw_desc_top": RawDescTop,
        "raw_desc_bottom": RawDescBottom,
        "run_start": RunStart,
        "run_end": RunEnd,
    }
    out = {name: constructors[name]() for name in spec.selectors}
    out.update({f"occ_{rank}": Occ(rank) for rank in range(2, spec.occurrence_rank + 1)})
    return out


def _selector_catalogue(spec: TransformationGrammarSpec) -> tuple[tuple[str, Selector], ...]:
    positions = _base_selector_catalogue(spec)
    result: dict[str, Selector] = dict(positions)
    if spec.boolean_selector_algebra:
        for name, selector in positions.items():
            result[f"not({name})"] = ~selector
        for (left_name, left), (right_name, right) in combinations(sorted(positions.items()), 2):
            # IDs are canonical so reversing the user-facing expression cannot
            # duplicate a commutative union or intersection.
            result[f"and({left_name},{right_name})"] = left & right
            result[f"or({left_name},{right_name})"] = left | right
            result[f"diff({left_name},{right_name})"] = left - right
            result[f"diff({right_name},{left_name})"] = right - left
    if len(result) > spec.max_selectors:
        raise ValueError(
            f"selector grammar generated {len(result)} expressions, above max_selectors={spec.max_selectors}; "
            "reduce selectors or disable boolean selector algebra"
        )
    return tuple(sorted(result.items()))


def generate_transformation_atoms(
    spec: TransformationGrammarSpec,
    *,
    expected_length_shift: int | None = None,
) -> tuple[Transformation, ...]:
    """Generate concrete transformation atoms from a bounded definition grammar."""
    atoms: dict[tuple[str, str], Transformation] = {}
    operations = set(spec.operations)

    def add(transform: Transformation) -> None:
        key = _candidate_key(transform)
        atoms[key] = transform
        if len(atoms) > spec.max_atoms:
            raise ValueError(
                f"transformation grammar generated more than max_atoms={spec.max_atoms}; "
                "reduce selector or parameter bounds"
            )

    if "symmetry" in operations:
        add(ReverseT())
        add(ComplementT())
    if "canonicalize" in operations:
        add(CompressLevelsT())
        add(StandardizeT())
    if "hat_sweeps" in operations:
        add(HatT())
        add(InverseHatT())
    if "prefix_lifts" in operations:
        for position in range(1, spec.position_bound + 1):
            add(PrefixLiftT(position))
            add(InversePrefixLiftT(position))

    if "block_schemas" in operations:
        from ac.algebra.block_schemas import generate_block_schemas
        for block_schema in generate_block_schemas(
            expected_length_shift,
            max_candidates=spec.max_atoms,
        ):
            add(block_schema)

    selector_items = _selector_catalogue(spec)
    if "selector_sweeps" in operations:
        for _, selector in selector_items:
            if not hasattr(selector, "kind") or selector.kind.value != "position":
                continue
            for inverse in (False, True):
                for direction in ("ltr", "rtl"):
                    add(SweepLiftT(selector, inverse_lift=inverse, direction=direction))
    if "selector_restrictions" in operations:
        for _, selector in selector_items:
            if hasattr(selector, "kind") and selector.kind.value == "position":
                add(RestrictSelectedT(selector))

    cut_selectors: dict[str, Selector] = {}
    if "insert_existing_values" in operations or "insert_fresh_maximum" in operations:
        for name, selector in selector_items:
            if name.startswith(("not(", "and(", "or(", "diff(")):
                continue
            if hasattr(selector, "kind") and selector.kind.value == "position":
                cut_selectors[f"before({name})"] = Before(selector)
                cut_selectors[f"after({name})"] = After(selector)
        for cut in range(spec.position_bound + 1):
            cut_selectors[f"cut({cut})"] = PositionCuts((cut,))
        if spec.boolean_selector_algebra:
            base_cuts = tuple(sorted(cut_selectors.items()))
            for _, selector in base_cuts:
                cut_selectors[f"not({selector!r})"] = ~selector
            for (left_name, left), (right_name, right) in combinations(base_cuts, 2):
                cut_selectors[f"and({left_name},{right_name})"] = left & right
                cut_selectors[f"or({left_name},{right_name})"] = left | right
                cut_selectors[f"diff({left_name},{right_name})"] = left - right
                cut_selectors[f"diff({right_name},{left_name})"] = right - left
        if len(cut_selectors) > spec.max_selectors:
            raise ValueError(
                f"cut-selector grammar generated {len(cut_selectors)} expressions, above max_selectors={spec.max_selectors}; "
                "reduce selectors or disable boolean selector algebra"
            )
        for _, selector in sorted(cut_selectors.items()):
            if "insert_fresh_maximum" in operations:
                add(InsertFreshMaximumT(selector))
            if "insert_existing_values" in operations:
                for value in range(1, spec.inserted_value_bound + 1):
                    add(InsertSelectedT(selector, value))

    return tuple(sorted(atoms.values(), key=lambda atom: (transformation_cost(atom), repr(atom))))


def iter_typed_transform_programs(
    atoms: tuple[Transformation, ...],
    *,
    max_cost: int,
    max_steps: int,
    expected_length_shift: int | None,
    max_candidates: int,
    expansion_budget: int,
) -> Iterator[Transformation]:
    """Yield unique normalized programs in deterministic weighted-cost order.

    A signature is a safe pruning fact only when its length effect is known.
    Unknown effects remain in the grammar and are decided by exact finite map
    evaluation, preserving variable-length restrictions and insertions.
    """
    if type(max_candidates) is not int or max_candidates < 1:
        raise ValueError("max_candidates must be positive")
    seed = Identity()
    if transformation_cost(seed) > max_cost:
        return
    serial = count()
    initial_key = _candidate_key(seed)
    best = {initial_key: (transformation_cost(seed), 0)}
    heap = [(0, 0, repr(initial_key), next(serial), seed)]
    emitted: set[tuple[str, str]] = set()
    produced = 0
    scheduled = 1
    expansion_limited = False
    while heap and produced < max_candidates:
        cost, steps, _, _, current = heapq.heappop(heap)
        key = _candidate_key(current)
        if best.get(key) != (cost, steps) or key in emitted:
            continue
        emitted.add(key)
        shift = current.signature.delta_length
        if expected_length_shift is None or shift is None or shift == expected_length_shift:
            yield current
            produced += 1
        if steps >= max_steps:
            continue
        if expansion_limited:
            continue
        for atom in atoms:
            candidate = (current >> atom).normal_form()
            candidate_cost = transformation_cost(candidate)
            candidate_steps = steps + 1
            if candidate_cost > max_cost:
                continue
            candidate_key = _candidate_key(candidate)
            pair = (candidate_cost, candidate_steps)
            if pair >= best.get(candidate_key, (max_cost + 1, max_steps + 1)):
                continue
            if scheduled >= expansion_budget:
                expansion_limited = True
                break
            best[candidate_key] = pair
            scheduled += 1
            heapq.heappush(
                heap,
                (candidate_cost, candidate_steps, repr(candidate_key), next(serial), candidate),
            )
    if expansion_limited and produced < max_candidates:
        raise ProgramExpansionLimit


def _family_generator(family: str):
    if family == "ordinary":
        from ac.generate.universes import ascent_sequences
        return ascent_sequences
    if family == "modified":
        from ac.generate.universes import modified_via_hat
        return modified_via_hat
    if family == "revised":
        from ac.generate.universes import revised_sequences
        return revised_sequences
    raise ValueError(f"unsupported ascent-sequence family: {family}")


def _family_limit(family: str) -> int:
    from ac.gui.experiments import FAMILY_LIMITS
    return FAMILY_LIMITS[family]


def _precompute(
    spec: TransformationSearchSpec,
    *,
    context=None,
    checkpoint: dict | None = None,
    enumeration_budget: int | None = None,
    class_object_budget: int | None = None,
):
    requests: dict[tuple[str, int], set[ClassSpec]] = {}
    for base_degree in range(spec.degrees.start, spec.degrees.stop + 1):
        source_degree = base_degree + spec.source_offset
        target_degree = base_degree + spec.target_offset
        if source_degree > _family_limit(spec.source.family):
            raise ValueError(f"source {spec.source.family} generator is bounded to degree {_family_limit(spec.source.family)}")
        if target_degree > _family_limit(spec.target.family):
            raise ValueError(f"target {spec.target.family} generator is bounded to degree {_family_limit(spec.target.family)}")
        requests.setdefault((spec.source.family, source_degree), set()).add(spec.source)
        requests.setdefault((spec.target.family, target_degree), set()).add(spec.target)

    cache: dict[tuple[str, int, ClassSpec], tuple] = {}
    predicates: dict[ClassSpec, object] = {}
    enumerated = retained = 0
    enumeration_limit = min(
        spec.grammar.enumeration_budget,
        spec.grammar.enumeration_budget if enumeration_budget is None else enumeration_budget,
    )
    class_object_limit = min(
        spec.grammar.class_object_budget,
        spec.grammar.class_object_budget if class_object_budget is None else class_object_budget,
    )
    groups = sorted(requests.items())
    checkpoint = {} if checkpoint is None else dict(checkpoint)
    for group_index, ((family, degree), classes) in enumerate(groups, start=1):
        ordered_classes = sorted(classes, key=lambda item: json.dumps(item.to_dict(), sort_keys=True))
        buckets = {class_spec: [] for class_spec in ordered_classes}
        class_predicates = {class_spec: predicates.setdefault(class_spec, class_spec.predicate()) for class_spec in ordered_classes}
        for word in _family_generator(family)(degree):
            enumerated += 1
            if context is not None and enumerated % 10_000 == 0:
                context.check_control()
            if enumerated > enumeration_limit:
                raise ValueError(
                    "transformation-search enumeration budget exceeded before class preparation; "
                    "reduce the degree window or raise enumeration_budget"
                )
            for class_spec in ordered_classes:
                if class_predicates[class_spec].holds(word):
                    buckets[class_spec].append(word)
                    retained += 1
                    if retained > class_object_limit:
                        raise ValueError(
                            "transformation-search class-object budget exceeded; "
                            "reduce the degree window or raise class_object_budget"
                        )
        for class_spec, words in buckets.items():
            cache[(family, degree, class_spec)] = tuple(words)
        if context is not None:
            state = dict(checkpoint)
            state.update({"grammar_version": spec.grammar_version, "preparation_group": group_index})
            context.checkpoint(
                state,
                {
                    "stage": "preparing classes",
                    "prepared_groups": group_index,
                    "total_groups": len(groups),
                    "enumerated_universe_objects": enumerated,
                    "retained_class_objects": retained,
                },
            )

    data = {}
    for base_degree in range(spec.degrees.start, spec.degrees.stop + 1):
        source_degree = base_degree + spec.source_offset
        target_degree = base_degree + spec.target_offset
        source = cache[(spec.source.family, source_degree, spec.source)]
        target = cache[(spec.target.family, target_degree, spec.target)]
        data[base_degree] = (source, target, frozenset(_word_key(word) for word in target))
    metrics = {
        "enumerated_universe_objects": enumerated,
        "retained_class_objects": retained,
        "source_class_objects": sum(len(data[n][0]) for n in data),
        "target_class_objects": sum(len(data[n][1]) for n in data),
    }
    return data, metrics


def _evaluate(transform: Transformation, data, spec: TransformationSearchSpec, *, context=None) -> CandidateEvaluation:
    verified = spec.degrees.start - 1
    checked = 0
    finite_map_digest = sha256()
    for base_degree in range(spec.degrees.start, spec.degrees.stop + 1):
        source, target, target_keys = data[base_degree]
        images: set[tuple[tuple[int, ...], int]] = set()
        preimages: dict[tuple[tuple[int, ...], int], object] = {}
        for word in source:
            checked += 1
            if context is not None and checked % 10_000 == 0:
                context.check_control()
            if not transform.defined_on(word):
                return CandidateEvaluation(
                    transform, transformation_cost(transform), verified,
                    SynthesisFailure(FailureKind.UNDEFINED, base_degree, source=word),
                )
            output = transform.apply(word).output
            key = _word_key(output)
            if key not in target_keys:
                return CandidateEvaluation(
                    transform, transformation_cost(transform), verified,
                    SynthesisFailure(FailureKind.OUTSIDE_TARGET, base_degree, source=word, output=output),
                )
            if key in preimages:
                return CandidateEvaluation(
                    transform, transformation_cost(transform), verified,
                    SynthesisFailure(
                        FailureKind.COLLISION, base_degree, source=word, output=output,
                        detail=f"also image of {preimages[key].values}",
                        other_source=preimages[key],
                    ),
                )
            preimages[key] = word
            images.add(key)
            finite_map_digest.update(json.dumps(
                [base_degree, list(word.values), word.height, list(output.values), output.height],
                separators=(",", ":"),
            ).encode("utf-8"))
            finite_map_digest.update(b"\n")
        if images != target_keys:
            return CandidateEvaluation(
                transform, transformation_cost(transform), verified,
                SynthesisFailure(
                    FailureKind.NOT_SURJECTIVE, base_degree,
                    detail=f"image={len(images)}, target={len(target_keys)}",
                ),
            )
        verified = base_degree
    return CandidateEvaluation(
        transform, transformation_cost(transform), verified, None,
        finite_map_fingerprint=finite_map_digest.hexdigest(),
    )


def _witness_failure_for_word(transform, word, base_degree, target_keys):
    """Check one known source witness against a candidate map."""
    if not transform.defined_on(word):
        return SynthesisFailure(FailureKind.UNDEFINED, base_degree, source=word)
    output = transform.apply(word).output
    if _word_key(output) not in target_keys:
        return SynthesisFailure(FailureKind.OUTSIDE_TARGET, base_degree, source=word, output=output)
    return None


def _witness_failure_for_pair(transform, first, second, base_degree, target_keys):
    first_failure = _witness_failure_for_word(transform, first, base_degree, target_keys)
    second_failure = _witness_failure_for_word(transform, second, base_degree, target_keys)
    if first_failure is not None:
        return first_failure
    if second_failure is not None:
        return second_failure
    first_output = transform.apply(first).output
    second_output = transform.apply(second).output
    if _word_key(first_output) == _word_key(second_output):
        return SynthesisFailure(
            FailureKind.COLLISION, base_degree, source=first, output=first_output,
            detail=f"also image of {second.values}", other_source=second,
        )
    return None


def _source_class_holds(spec: TransformationSearchSpec, word) -> bool:
    return spec.source.predicate().holds(word)


def _minimize_counterexample(transform, failure, spec, data):
    """Lower source values until no single-entry lowering preserves failure.

    The result is deletion-free and class-valid at the same tested degree, so
    all replay constraints continue to use the original finite target set.
    This is a local minimality certificate, not a global ordering claim.
    """
    if failure.source is None or failure.n not in data:
        return failure
    target_keys = data[failure.n][2]
    kind = failure.kind

    if kind in {FailureKind.UNDEFINED, FailureKind.OUTSIDE_TARGET}:
        current = failure.source
        while True:
            reductions = []
            for index, value in enumerate(current.values):
                for replacement in range(1, value):
                    values = list(current.values)
                    values[index] = replacement
                    candidate = type(current).of(values)
                    if not _source_class_holds(spec, candidate):
                        continue
                    candidate_failure = _witness_failure_for_word(
                        transform, candidate, failure.n, target_keys,
                    )
                    if candidate_failure is not None:
                        reductions.append((candidate.values, candidate_failure))
            if not reductions:
                return _witness_failure_for_word(transform, current, failure.n, target_keys)
            _, failure = min(reductions, key=lambda row: row[0])
            current = failure.source

    if kind is FailureKind.COLLISION and failure.other_source is not None:
        first, second = failure.source, failure.other_source
        while True:
            reductions = []
            for which, current in ((0, first), (1, second)):
                for index, value in enumerate(current.values):
                    for replacement in range(1, value):
                        values = list(current.values)
                        values[index] = replacement
                        candidate = type(current).of(values)
                        if candidate.values == (second if which == 0 else first).values:
                            continue
                        if not _source_class_holds(spec, candidate):
                            continue
                        pair = (candidate, second) if which == 0 else (first, candidate)
                        candidate_failure = _witness_failure_for_pair(
                            transform, pair[0], pair[1], failure.n, target_keys,
                        )
                        if candidate_failure is not None and candidate_failure.kind is FailureKind.COLLISION:
                            reductions.append(((pair[0].values, pair[1].values), candidate_failure))
            if not reductions:
                return _witness_failure_for_pair(transform, first, second, failure.n, target_keys)
            _, failure = min(reductions, key=lambda row: row[0])
            first, second = failure.source, failure.other_source
            if first is None or second is None:
                return failure
    return failure


def _replay_counterexample(transform, witness, data, *, unverified_through):
    """Use one accumulated counterexample to reject a later candidate cheaply."""
    base_degree = witness["base_degree"]
    if base_degree not in data:
        return None
    from ac.core.word import ChainWord
    source = ChainWord(tuple(witness["source"]["values"]), height=witness["source"]["height"])
    target_keys = data[base_degree][2]
    other_data = witness.get("other_source")
    if other_data is None:
        failure = _witness_failure_for_word(transform, source, base_degree, target_keys)
    else:
        other = ChainWord(tuple(other_data["values"]), height=other_data["height"])
        failure = _witness_failure_for_pair(transform, source, other, base_degree, target_keys)
    if failure is None:
        return None
    return CandidateEvaluation(
        transform, transformation_cost(transform), unverified_through, failure,
    )


def _counterexample_record(failure, transform, candidate_index, witness_id):
    return {
        "id": witness_id,
        "base_degree": failure.n,
        "kind": failure.kind.value,
        "source": _word_data(failure.source),
        "other_source": _word_data(failure.other_source),
        "output": _word_data(failure.output),
        "origin_program": repr(transform),
        "origin_candidate_index": candidate_index,
        "minimality": "single-entry-lowering-minimal within the source class at fixed degree",
    }


def _counterexample_id(failure) -> str:
    canonical = {
        "base_degree": failure.n,
        "kind": failure.kind.value,
        "source": _word_data(failure.source),
        "other_source": _word_data(failure.other_source),
        "output": _word_data(failure.output),
    }
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()[:16]


def _word_data(word) -> dict | None:
    if word is None:
        return None
    return {"values": list(word.values), "height": word.height}


def _evaluation_data(
    evaluation: CandidateEvaluation,
    spec: TransformationSearchSpec,
    example_source=None,
    *,
    evaluation_mode: str = "full_class_evaluation",
    witness_id: str | None = None,
) -> dict:
    failure = evaluation.failure
    signature = evaluation.transform.signature
    row = {
        "program": repr(evaluation.transform),
        "cost": evaluation.cost,
        "signature": {
            "delta_length": signature.delta_length,
            "delta_height": signature.delta_height,
            "partial": signature.partial,
            "preserves_occurrence_ids": signature.preserves_occurrence_ids,
        },
        "verified_through": evaluation.verified_through,
        "finite_match_through_window": evaluation.exact,
        "proof_status": "not_proved",
        "evaluation_mode": evaluation_mode,
    }
    if evaluation.finite_map_fingerprint is not None:
        row["finite_map_fingerprint"] = evaluation.finite_map_fingerprint
    if witness_id is not None:
        row["counterexample_id"] = witness_id
    if failure is not None:
        failure_data = {
            "kind": failure.kind.value,
            "base_degree": failure.n,
            "source_degree": failure.n + spec.source_offset,
            "target_degree": failure.n + spec.target_offset,
            "source": _word_data(failure.source),
            "other_source": _word_data(failure.other_source),
            "output": _word_data(failure.output),
            "detail": failure.detail,
        }
        row["counterexample" if evaluation_mode == "counterexample_replay" else "first_failure"] = failure_data
    from ac.algebra.block_schemas import BlockSchemaT
    if isinstance(evaluation.transform, BlockSchemaT):
        row["block_schema"] = {
            "segmentation": evaluation.transform.segmentation,
            "parent_rule": evaluation.transform.parent_rule,
            "block_order": evaluation.transform.block_order,
            "block_map": evaluation.transform.block_map,
            "extension": evaluation.transform.extension,
        }
        trace_source = failure.source if failure is not None and failure.source is not None else example_source
        if trace_source is not None:
            row["example_trace"] = {
                "source": _word_data(trace_source),
                **evaluation.transform.trace(trace_source),
            }
    return row


def run_transformation_search(job, context) -> dict:
    """Worker handler: generate, evaluate, and checkpoint transformation maps."""
    spec = job.question
    if not isinstance(spec, TransformationSearchSpec):
        raise ValueError("transformation worker requires a transformation-search specification")
    checkpoint = dict(job.checkpoint)
    if checkpoint and checkpoint.get("grammar_version") != spec.grammar_version:
        raise ValueError("saved checkpoint uses a different transformation grammar version")
    checkpoint_cursor = checkpoint.get("next_candidate_index", 0)
    if (
        type(checkpoint_cursor) is int
        and checkpoint_cursor > 0
        and checkpoint.get("cegis_version") != CEGIS_VERSION
    ):
        # Older v2 checkpoints have no witness suite. Restart candidate
        # evaluation so resumed results have the same refinement history.
        checkpoint = {}
    data, preparation_metrics = _precompute(spec, context=context, checkpoint=checkpoint)
    atoms = generate_transformation_atoms(spec.grammar, expected_length_shift=spec.degree_shift)
    evaluation_work_per_candidate = preparation_metrics["source_class_objects"]
    screening_witness_limit = (
        min(MAX_CEGIS_WITNESSES, max(1, evaluation_work_per_candidate // 8))
        if evaluation_work_per_candidate
        else 0
    )
    affordable_candidates = (
        spec.grammar.candidate_budget
        if evaluation_work_per_candidate == 0
        else min(
            spec.grammar.candidate_budget,
            spec.grammar.evaluation_budget // evaluation_work_per_candidate,
        )
    )
    if affordable_candidates == 0:
        raise ValueError(
            "evaluation_budget is smaller than one complete candidate pass over the source classes; "
            "reduce the degree window or raise evaluation_budget"
        )
    start_index = checkpoint.get("next_candidate_index", 0)
    if type(start_index) is not int or not 0 <= start_index <= affordable_candidates:
        raise ValueError("transformation-search checkpoint has an invalid candidate cursor")
    exact = list(checkpoint.get("exact", []))
    near = list(checkpoint.get("near_misses", []))
    exact_count = int(checkpoint.get("exact_count", 0))
    examined = int(checkpoint.get("examined", start_index))
    counterexample_suite = list(checkpoint.get("counterexample_suite", []))
    cegis_trace = list(checkpoint.get("cegis_trace", []))
    known_witnesses = {witness["id"] for witness in counterexample_suite}
    screened_candidates = int(checkpoint.get("screened_candidates", 0))
    fully_evaluated_candidates = int(checkpoint.get("fully_evaluated_candidates", start_index))
    failure_not_added_to_suite_count = int(checkpoint.get("failure_not_added_to_suite_count", 0))
    witness_limit_reached = bool(checkpoint.get("witness_limit_reached", False))
    keep = 25
    iterator = iter_typed_transform_programs(
        atoms,
        max_cost=spec.grammar.max_cost,
        max_steps=spec.grammar.max_steps,
        expected_length_shift=spec.degree_shift,
        max_candidates=affordable_candidates,
        expansion_budget=spec.grammar.expansion_budget,
    )
    interval = 25
    next_index = start_index
    exhausted = True
    expansion_limited = False
    try:
        for index, transform in enumerate(iterator):
            if index < start_index:
                continue
            if index >= affordable_candidates:
                exhausted = False
                break
            replayed_witness = None
            evaluation = None
            for witness in counterexample_suite[:screening_witness_limit]:
                replayed = _replay_counterexample(
                    transform, witness, data,
                    unverified_through=spec.degrees.start - 1,
                )
                if replayed is not None:
                    evaluation = replayed
                    replayed_witness = witness
                    screened_candidates += 1
                    break
            evaluation_mode = "counterexample_replay" if replayed_witness is not None else "full_class_evaluation"
            witness_id = None if replayed_witness is None else replayed_witness["id"]
            if evaluation is None:
                evaluation = _evaluate(transform, data, spec, context=context)
                fully_evaluated_candidates += 1
            discovered_witness_id = None
            witness_added = False
            if evaluation.failure is not None:
                if evaluation.failure.kind in {
                    FailureKind.UNDEFINED, FailureKind.OUTSIDE_TARGET, FailureKind.COLLISION,
                } and len(counterexample_suite) < MAX_CEGIS_WITNESSES:
                    minimized = _minimize_counterexample(evaluation.transform, evaluation.failure, spec, data)
                    discovered_witness_id = _counterexample_id(minimized)
                    if discovered_witness_id not in known_witnesses:
                        witness = _counterexample_record(
                            minimized, transform, index, discovered_witness_id,
                        )
                        counterexample_suite.append(witness)
                        known_witnesses.add(discovered_witness_id)
                        witness_added = True
                        cegis_trace.append({
                            "round": len(cegis_trace) + 1,
                            "candidate_index": index,
                            "trigger_program": repr(transform),
                            "counterexample_id": discovered_witness_id,
                            "kind": minimized.kind.value,
                            "base_degree": minimized.n,
                            "source": _word_data(minimized.source),
                            "other_source": _word_data(minimized.other_source),
                        })
                else:
                    failure_not_added_to_suite_count += 1
                    if len(counterexample_suite) >= MAX_CEGIS_WITNESSES:
                        witness_limit_reached = True
            source_rows = data[spec.degrees.start][0]
            example_source = source_rows[0] if source_rows else None
            item = _evaluation_data(
                evaluation, spec, example_source,
                evaluation_mode=evaluation_mode,
                witness_id=witness_id,
            )
            if discovered_witness_id is not None:
                item["minimized_counterexample_id"] = discovered_witness_id
            next_index = index + 1
            examined += 1
            if evaluation.exact:
                exact_count += 1
                exact.append(item)
                exact.sort(key=lambda row: (row["cost"], row["program"]))
                exact = exact[:keep]
            else:
                near.append(item)
                near.sort(key=lambda row: (-row["verified_through"], row["cost"], row["program"]))
                near = near[:keep]
            if examined % interval == 0 or (witness_added and len(cegis_trace) == 1):
                context.checkpoint(
                    {
                        "grammar_version": spec.grammar_version,
                        "cegis_version": CEGIS_VERSION,
                        "next_candidate_index": next_index,
                        "examined": examined,
                        "exact_count": exact_count,
                        "exact": exact,
                        "near_misses": near,
                        "counterexample_suite": counterexample_suite,
                        "cegis_trace": cegis_trace,
                        "screened_candidates": screened_candidates,
                        "fully_evaluated_candidates": fully_evaluated_candidates,
                        "failure_not_added_to_suite_count": failure_not_added_to_suite_count,
                        "witness_limit_reached": witness_limit_reached,
                    },
                    {
                        "candidates_tested": examined,
                        "candidate_budget": affordable_candidates,
                        "exact_candidates": exact_count,
                        "counterexample_refinements": len(cegis_trace),
                        "screened_candidates": screened_candidates,
                    },
                )
    except ProgramExpansionLimit:
        expansion_limited = True
    if next_index < affordable_candidates and exhausted:
        search_space_exhausted = not expansion_limited
    else:
        search_space_exhausted = False
    evaluation_budget_limited = (
        affordable_candidates < spec.grammar.candidate_budget
        and next_index >= affordable_candidates
        and not search_space_exhausted
    )
    return {
        "spec_fingerprint": spec.fingerprint,
        "grammar_version": spec.grammar_version,
        "source_description": spec.source.describe(),
        "target_description": spec.target.describe(),
        "source_offset": spec.source_offset,
        "target_offset": spec.target_offset,
        "degree_shift": spec.degree_shift,
        "base_degrees": [spec.degrees.start, spec.degrees.stop],
        "generated_atom_count": len(atoms),
        **preparation_metrics,
        "candidates_tested": examined,
        "candidate_budget": spec.grammar.candidate_budget,
        "effective_candidate_budget": affordable_candidates,
        "evaluation_budget": spec.grammar.evaluation_budget,
        "evaluation_budget_limited": evaluation_budget_limited,
        "expansion_budget": spec.grammar.expansion_budget,
        "search_ended_by_expansion_budget": expansion_limited,
        "candidate_space_exhausted": search_space_exhausted,
        "exact_candidate_count": exact_count,
        "exact_candidates": exact,
        "near_misses": near,
        "counterexample_guided_evaluation": {
            "version": CEGIS_VERSION,
            "screened_candidate_count": screened_candidates,
            "fully_evaluated_candidate_count": fully_evaluated_candidates,
            "refinement_round_count": len(cegis_trace),
            "counterexample_suite": counterexample_suite,
            "refinement_trace": cegis_trace,
            "failure_not_added_to_suite_count": failure_not_added_to_suite_count,
            "witness_limit": MAX_CEGIS_WITNESSES,
            "screening_witness_limit_per_candidate": screening_witness_limit,
            "witness_limit_reached": witness_limit_reached,
            "minimality_scope": "single-entry value lowering while remaining in the source class at the same tested degree",
        },
        "status": "finite_computational_search",
        "interpretation": "A candidate passing the listed finite window is not a proof; prove the map and its inverse or bijectivity argument separately.",
        "proof_obligations": [
            "prove the transformation is defined on every source object in the claimed class",
            "prove every output lies in the target class at the stated degree offset",
            "prove injectivity and surjectivity, or give a proved inverse",
            "justify that the generated grammar contains the proposed map family",
        ],
    }
