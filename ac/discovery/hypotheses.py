from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from ac.logic.predicates import Always, WordPredicate
from ac.solvers.exhaustive import VerificationResult, VerificationStatus, verify_on


@dataclass(frozen=True)
class HypothesisCandidate:
    name: str
    predicate: WordPredicate
    cost: int = 1


@dataclass(frozen=True)
class HypothesisDiscovery:
    candidates: tuple[HypothesisCandidate, ...]
    verification: VerificationResult
    finite_support: int
    cost: int

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(c.name for c in self.candidates)


def _and_all(predicates: Iterable[WordPredicate]) -> WordPredicate:
    out: WordPredicate = Always()
    for predicate in predicates:
        out = out & predicate
    return out


def _finite_support(*, universe, through: int, hypothesis: WordPredicate, start: int) -> int:
    count = 0
    for n in range(start, through + 1):
        for word in universe(n):
            if hypothesis.holds(word):
                count += 1
    return count


def mine_minimal_hypotheses(
    law: WordPredicate,
    *,
    base: WordPredicate | None,
    candidates: Iterable[HypothesisCandidate],
    universe,
    through: int,
    start: int = 1,
    max_terms: int = 2,
) -> tuple[HypothesisDiscovery, ...]:
    """Search small conjunctions that repair a false/general law.

    Results are inclusion-minimal among the supplied candidate conjunctions.
    Within that set they are ranked by empirical weakness: the hypothesis that
    admits more finite examples is preferred, followed by declared cost.
    """

    base = Always() if base is None else base
    candidates = tuple(candidates)
    verified: list[HypothesisDiscovery] = []
    verified_name_sets: list[frozenset[str]] = []

    for size in range(0, max_terms + 1):
        for combo in combinations(candidates, size):
            names = frozenset(c.name for c in combo)
            if any(prev < names for prev in verified_name_sets):
                continue
            extra = _and_all(c.predicate for c in combo)
            hypothesis = base & extra
            result = verify_on(law, universe=universe, through=through, hypothesis=hypothesis, start=start)
            if result.status is not VerificationStatus.VERIFIED:
                continue
            support = _finite_support(universe=universe, through=through, hypothesis=hypothesis, start=start)
            discovery = HypothesisDiscovery(combo, result, support, sum(c.cost for c in combo))
            verified.append(discovery)
            verified_name_sets.append(names)

    # Remove any result that acquired a strict verified subset later (normally
    # impossible with size-order traversal, but this makes the contract robust).
    minimal: list[HypothesisDiscovery] = []
    for result in verified:
        names = frozenset(result.names)
        if any(frozenset(other.names) < names for other in verified):
            continue
        minimal.append(result)
    minimal.sort(key=lambda r: (-r.finite_support, r.cost, r.names))
    return tuple(minimal)


@dataclass(frozen=True)
class ThresholdDiscovery:
    working_parameters: tuple[int, ...]
    failing_parameters: tuple[int, ...]
    boundary: int | None
    results: tuple[tuple[int, VerificationResult], ...]


def discover_monotone_threshold(
    parameters: Iterable[int],
    *,
    law_factory,
    hypothesis_factory,
    universe,
    through: int,
    start: int = 1,
) -> ThresholdDiscovery:
    """Empirically locate a parameter boundary for a family of laws.

    This does not assume which direction is monotone; ``boundary`` is returned
    only when the successful parameter values form an initial segment of the
    sorted supplied values.  The complete per-parameter results are retained.
    """

    params = tuple(sorted(set(parameters)))
    rows: list[tuple[int, VerificationResult]] = []
    working: list[int] = []
    failing: list[int] = []
    for parameter in params:
        result = verify_on(
            law_factory(parameter),
            universe=universe,
            through=through,
            hypothesis=hypothesis_factory(parameter),
            start=start,
        )
        rows.append((parameter, result))
        (working if result.status is VerificationStatus.VERIFIED else failing).append(parameter)

    boundary = None
    if working:
        k = len(working)
        if tuple(working) == params[:k] and tuple(failing) == params[k:]:
            boundary = working[-1]
    return ThresholdDiscovery(tuple(working), tuple(failing), boundary, tuple(rows))
