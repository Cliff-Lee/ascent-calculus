from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from ac.core.word import ChainWord
from ac.generate.universes import chain_words
from ac.logic.fo import Formula, TRUE


class ModelStatus(str, Enum):
    SAT = "sat"
    UNSAT = "unsat"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ModelResult:
    status: ModelStatus
    n: int
    height: int
    backend: str
    tested: int = 0
    model: ChainWord | None = None
    detail: str | None = None

    @property
    def sat(self) -> bool:
        return self.status is ModelStatus.SAT


@dataclass(frozen=True)
class CountermodelSearch:
    result: ModelResult | None
    searched_through: int
    models_tested: int

    @property
    def found(self) -> bool:
        return self.result is not None and self.result.sat


def _finite_solve(formula: Formula, *, n: int, height: int) -> ModelResult:
    tested = 0
    for word in chain_words(n, height):
        tested += 1
        if formula.holds(word):
            return ModelResult(ModelStatus.SAT, n, height, "finite", tested, word)
    return ModelResult(ModelStatus.UNSAT, n, height, "finite", tested)


def solve_formula(
    formula: Formula,
    *,
    n: int,
    height: int,
    backend: str = "auto",
) -> ModelResult:
    """Find a model at fixed length/ambient height.

    ``auto`` prefers Z3 when the optional dependency is available and otherwise
    falls back to the executable finite reference semantics.
    """
    if n < 0 or height < 0:
        raise ValueError("n and height must be nonnegative")
    if backend not in {"auto", "finite", "z3"}:
        raise ValueError("backend must be auto, finite, or z3")
    if backend in {"auto", "z3"}:
        try:
            from ac.solvers.z3_backend import solve_z3
            return solve_z3(formula, n=n, height=height)
        except ModuleNotFoundError as exc:
            if backend == "z3":
                return ModelResult(
                    ModelStatus.UNAVAILABLE,
                    n,
                    height,
                    "z3",
                    detail=f"optional z3-solver dependency unavailable: {exc}",
                )
    return _finite_solve(formula, n=n, height=height)


def find_countermodel(
    law: Formula,
    *,
    assumptions: Formula = TRUE,
    n: int,
    height: int,
    backend: str = "auto",
) -> ModelResult:
    return solve_formula(assumptions & ~law, n=n, height=height, backend=backend)


def smallest_model(
    formula: Formula,
    *,
    through: int,
    start: int = 1,
    max_height: int | None = None,
    backend: str = "auto",
) -> CountermodelSearch:
    """Search length, then height, then backend word order for a smallest model."""
    total = 0
    for n in range(start, through + 1):
        top = n if max_height is None else max_height
        for h in range(1, top + 1):
            result = solve_formula(formula, n=n, height=h, backend=backend)
            total += result.tested
            if result.status is ModelStatus.SAT:
                return CountermodelSearch(result, through, total)
            if result.status is ModelStatus.UNAVAILABLE and backend == "z3":
                return CountermodelSearch(result, through, total)
    return CountermodelSearch(None, through, total)


def smallest_countermodel(
    law: Formula,
    *,
    assumptions: Formula = TRUE,
    through: int,
    start: int = 1,
    max_height: int | None = None,
    backend: str = "auto",
) -> CountermodelSearch:
    return smallest_model(
        assumptions & ~law,
        through=through,
        start=start,
        max_height=max_height,
        backend=backend,
    )


def solve_predicate(predicate, *, n: int, height: int, backend: str = "auto") -> ModelResult:
    from ac.logic.translate import predicate_to_formula
    return solve_formula(predicate_to_formula(predicate), n=n, height=height, backend=backend)


def smallest_predicate_model(predicate, *, through: int, start: int = 1, max_height: int | None = None, backend: str = "auto") -> CountermodelSearch:
    from ac.logic.translate import predicate_to_formula
    return smallest_model(predicate_to_formula(predicate), through=through, start=start, max_height=max_height, backend=backend)
