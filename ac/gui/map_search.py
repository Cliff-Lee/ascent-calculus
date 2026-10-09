"""GUI adapter for bounded, shift-aware transformation synthesis."""

from __future__ import annotations

from time import perf_counter

from ac.algebra import (
    Compose,
    C,
    Compress,
    BlockSchemaT,
    Hat,
    HatInv,
    L,
    Linv,
    Modified111BlockBijection,
    Revised111ToModified111Inverse,
    R,
    Std,
    SweepLift,
    enumerate_block_schemas,
)
from ac.classes.theories import is_ascent_sequence, is_modified, is_revised
from ac.discovery.synthesis import synthesize_bijections
from ac.gui.experiments import FAMILY_GENERATORS, _matches, parse_experiment
from ac.logic.predicates import WordPredicate
from ac.logic.selectors import (
    AscBottom,
    AscTop,
    DescBottom,
    DescTop,
    First,
    Last,
    RawAscBottom,
    RawAscTop,
    RawDescBottom,
    RawDescTop,
    Repeat,
    RunEnd,
    RunStart,
)

FAMILY_PREDICATES = {
    "ordinary": is_ascent_sequence,
    "modified": is_modified,
    "revised": is_revised,
}


class _ExperimentClass(WordPredicate):
    def __init__(self, family, rules, condition=None):
        self.family = family
        self.rules = rules
        self.condition = condition

    def holds(self, word):
        return FAMILY_PREDICATES[self.family](word) and _matches(word, self.rules, self.condition)


def _paper_pair(spec) -> bool:
    if spec.condition is not None:
        return False
    forward = (
        spec.left.family == "modified"
        and spec.right.family == "revised"
        and spec.right.degree_offset - spec.left.degree_offset == 2
    )
    reverse = (
        spec.left.family == "revised"
        and spec.right.family == "modified"
        and spec.right.degree_offset - spec.left.degree_offset == -2
    )
    if not (forward or reverse):
        return False
    expected = (("avoid", (1, 1, 1)),)
    return (
        tuple((rule.mode, rule.pattern.values) for rule in spec.left.rules) == expected
        and tuple((rule.mode, rule.pattern.values) for rule in spec.right.rules) == expected
    )


def _candidate_atoms(degree_shift: int, include_paper_recipe: bool, fixed_pivot_limit: int):
    atoms = [R(), C(), Hat(), HatInv(), Compress(), Std()]
    for position in range(1, fixed_pivot_limit + 1):
        atoms.extend((L(position), Linv(position)))
    selectors = (
        First(), Last(), AscTop(), AscBottom(), DescTop(), DescBottom(),
        RunStart(), RunEnd(), Repeat(), RawAscTop(), RawAscBottom(),
        RawDescTop(), RawDescBottom(),
    )
    for selector in selectors:
        for inverse in (False, True):
            for direction in ("ltr", "rtl"):
                atoms.append(SweepLift(selector, inverse=inverse, direction=direction))
    atoms.extend(enumerate_block_schemas(degree_shift))
    if degree_shift == 2 and include_paper_recipe:
        atoms.append(Modified111BlockBijection())
    elif degree_shift == -2 and include_paper_recipe:
        atoms.append(Revised111ToModified111Inverse())
    return tuple(atoms)


def _candidate_label(transform) -> str:
    if isinstance(transform, Compose):
        return " → ".join(_candidate_label(part) for part in transform.parts)
    if isinstance(transform, BlockSchemaT):
        parts = [
            transform.segmentation.replace("_", " "),
            f"parent: {transform.parent_rule.replace('_', ' ')}",
            transform.block_order.replace("_", " "),
            transform.block_map.replace("_", "-"),
        ]
        if transform.extension == "max_before_first":
            parts.append("insert one new max")
        elif transform.extension == "max_pair_around_first":
            parts.append("insert max pair")
        return "Blocks · " + " · ".join(parts)
    if type(transform).__name__ == "Modified111ToRevised111":
        return "Paper block bijection · M111 → R111 · n+2"
    if type(transform).__name__ == "Revised111ToModified111Inverse":
        return "Inverse paper block map · R111 → M111 · n−2"
    names = {
        "ReverseT": "Reverse positions",
        "ComplementT": "Complement values",
        "HatT": "Hat map",
        "InverseHatT": "Inverse hat map",
        "CompressLevelsT": "Compress value levels",
        "StandardizeT": "Standardize values",
    }
    if type(transform).__name__ in names:
        return names[type(transform).__name__]
    if type(transform).__name__ == "SweepLiftT":
        selector = type(transform.selector).__name__.removesuffix("Selector")
        mode = "inverse " if transform.inverse_lift else ""
        return f"{mode}sweep lift · {selector} · {transform.direction}"
    if type(transform).__name__ == "PrefixLiftT":
        return f"Prefix lift L{transform.position}"
    if type(transform).__name__ == "InversePrefixLiftT":
        return f"Inverse prefix lift L{transform.position}"
    return type(transform).__name__


def _candidate_expression(transform) -> str:
    if isinstance(transform, Compose):
        return " → ".join(_candidate_expression(part) for part in transform.parts)
    if isinstance(transform, BlockSchemaT):
        return (
            f"{_candidate_label(transform)} "
            f"[segmentation={transform.segmentation}; parent={transform.parent_rule}; "
            f"order={transform.block_order}; block map={transform.block_map}; "
            f"extension={transform.extension}]"
        )
    if type(transform).__name__ in {"Modified111ToRevised111", "Revised111ToModified111Inverse"}:
        return _candidate_label(transform)
    return repr(transform)


def _failure_data(failure):
    if failure is None:
        return None
    return {
        "kind": failure.kind.value,
        "n": failure.n,
        "source": list(failure.source.values) if failure.source else None,
        "output": list(failure.output.values) if failure.output else None,
        "detail": failure.detail,
    }


def run_map_search(raw: dict, *, max_cost: int = 4, max_steps: int = 2, keep: int = 20) -> dict:
    """Search a bounded grammar for bijections between the requested classes."""
    started = perf_counter()
    spec = parse_experiment(raw)
    if spec.right is None:
        raise ValueError("Choose two classes before searching for a map")
    if spec.statistic != "none":
        # A statistic refinement may be useful as a later map constraint, but
        # current synthesis searches class bijections, not statistic fibres.
        raise ValueError("Clear the statistic refinement before searching for a class bijection")
    if isinstance(max_cost, bool) or not isinstance(max_cost, int) or not 0 <= max_cost <= 8:
        raise ValueError("Search cost must be between 0 and 8")
    if isinstance(max_steps, bool) or not isinstance(max_steps, int) or not 0 <= max_steps <= 5:
        raise ValueError("Composition depth must be between 0 and 5")

    source_start = spec.start + spec.left.degree_offset
    source_through = spec.stop + spec.left.degree_offset
    if max_steps <= 1 and source_through > 8:
        raise ValueError("Single-operation map searches are bounded to source degree 8 for responsive finite testing")
    if max_steps > 1 and source_through > 6:
        raise ValueError("Two-operation composition searches are bounded to source degree 6; lower the tested range")
    degree_shift = spec.right.degree_offset - spec.left.degree_offset
    source = _ExperimentClass(spec.left.family, spec.left.rules, spec.condition)
    target = _ExperimentClass(spec.right.family, spec.right.rules, spec.condition)
    paper_recipe_available = _paper_pair(spec)
    atoms = _candidate_atoms(degree_shift, paper_recipe_available, source_start)
    if degree_shift not in {0, 2}:
        atoms = tuple(atom for atom in atoms if atom.signature.delta_length == degree_shift)

    report = synthesize_bijections(
        source,
        target,
        universe=FAMILY_GENERATORS[spec.left.family],
        target_universe=FAMILY_GENERATORS[spec.right.family],
        degree_shift=degree_shift,
        atoms=atoms,
        max_cost=max_cost,
        through=source_through,
        start=source_start,
        max_steps=max_steps,
        probe_n=source_through,
        keep=keep,
    )

    def serialize(evaluation):
        diagnostics = evaluation.diagnostics
        return {
            "name": _candidate_label(evaluation.transform),
            "expression": _candidate_expression(evaluation.transform),
            "cost": evaluation.cost,
            "verified_through": evaluation.verified_through,
            "exact": evaluation.exact,
            "failure": _failure_data(evaluation.failure),
            "probe": None if diagnostics is None else {
                "n": diagnostics.n,
                "target_n": diagnostics.n + degree_shift,
                "source_count": diagnostics.source_count,
                "target_count": diagnostics.target_count,
                "defined_fraction": diagnostics.defined_fraction,
                "target_fraction": diagnostics.target_fraction,
                "injectivity_fraction": diagnostics.injectivity_fraction,
            },
            "_transform": evaluation.transform,
        }

    return {
        "specification": raw,
        "source_family": spec.left.family,
        "target_family": spec.right.family,
        "source_start": source_start,
        "source_through": source_through,
        "degree_shift": degree_shift,
        "candidate_programs": report.candidates_tested,
        "shift_compatible_programs": report.normalized_candidates,
        "exact": [serialize(candidate) for candidate in report.exact],
        "ranked": [serialize(candidate) for candidate in report.ranked],
        "paper_recipe_available": paper_recipe_available,
        "search_grammar": {
            "global_and_event_operations": ["reverse", "complement", "standardize", "compress", "hat", "inverse_hat", "fixed prefix lifts", "event-sweep lifts"],
            "generated_block_recipes": len(enumerate_block_schemas(degree_shift)),
            "block_extension_rule": {0: "none", 1: "insert one new maximum before the ordered blocks", 2: "insert a new maximum pair around the first ordered block"}.get(degree_shift),
            "maximum_cost": max_cost,
            "maximum_composition_steps": max_steps,
        },
        "runtime_seconds": round(perf_counter() - started, 4),
        "finite_only": True,
        "notice": "A finite pass means this recipe worked on every enumerated object in the requested range. It is evidence, not an all-degree proof.",
    }


def exportable_map_report(report: dict) -> dict:
    """Remove in-process transformation objects from a report for JSON export."""
    return {
        key: [
            {field: value for field, value in candidate.items() if not field.startswith("_")}
            for candidate in report[key]
        ] if key in {"exact", "ranked"} else value
        for key, value in report.items()
    }
