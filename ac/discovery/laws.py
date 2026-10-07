from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from ac.logic.predicates import SameSet, Subset, Disjoint, WordPredicate
from ac.logic.selectors import Selector
from ac.solvers.exhaustive import VerificationResult, VerificationStatus, verify_on


@dataclass(frozen=True)
class MinedLaw:
    relation: str
    left: Selector
    right: Selector
    verification: VerificationResult
    score: int

    @property
    def statement(self):
        if self.relation == "eq":
            return SameSet(self.left, self.right)
        if self.relation == "subset":
            return Subset(self.left, self.right)
        if self.relation == "disjoint":
            return Disjoint(self.left, self.right)
        raise ValueError(self.relation)


def _complexity(selector: Selector) -> int:
    # A deliberately transparent first cost model: AST repr length is stable
    # enough for ranking the tiny E6 search space, without pretending to be a
    # mathematical complexity measure.
    return len(repr(selector))


def mine_selector_laws(
    selectors: Iterable[Selector],
    *,
    universe,
    through: int,
    hypothesis: WordPredicate | None = None,
    relations: tuple[str, ...] = ("eq", "subset", "disjoint"),
    start: int = 1,
) -> tuple[MinedLaw, ...]:
    selectors = tuple(selectors)
    out: list[MinedLaw] = []
    for left, right in combinations(selectors, 2):
        if left.kind is not right.kind:
            continue
        for relation in relations:
            if relation == "eq":
                law = SameSet(left, right)
            elif relation == "subset":
                law = Subset(left, right)
            elif relation == "disjoint":
                law = Disjoint(left, right)
            else:
                raise ValueError(relation)
            result = verify_on(law, universe=universe, through=through, hypothesis=hypothesis, start=start)
            if result.status is VerificationStatus.VERIFIED:
                out.append(MinedLaw(relation, left, right, result, _complexity(left) + _complexity(right)))

            # Subset is directional, so test the opposite direction too.
            if relation == "subset":
                reverse = Subset(right, left)
                rresult = verify_on(reverse, universe=universe, through=through, hypothesis=hypothesis, start=start)
                if rresult.status is VerificationStatus.VERIFIED:
                    out.append(MinedLaw("subset", right, left, rresult, _complexity(left) + _complexity(right)))
    out.sort(key=lambda law: (law.score, law.relation, repr(law.left), repr(law.right)))
    return tuple(out)


def selector_complexity(selector: Selector) -> int:
    """Small structural cost used by the E7 expression miner."""
    from ac.logic.selectors import SetBinary, SetComplement

    if isinstance(selector, SetBinary):
        return 1 + selector_complexity(selector.left) + selector_complexity(selector.right)
    if isinstance(selector, SetComplement):
        return 1 + selector_complexity(selector.child)
    return 1


def generate_selector_expressions(
    base: Iterable[Selector],
    *,
    max_cost: int = 3,
    operations: tuple[str, ...] = ("difference", "intersection", "union"),
) -> tuple[Selector, ...]:
    """Generate a bounded symbolic closure of selectors.

    Expressions are deduplicated syntactically.  Semantic deduplication belongs
    to the law miner because it depends on the chosen theory/universe.
    """

    pool = list(dict.fromkeys(base))
    seen = {repr(s) for s in pool}
    changed = True
    while changed:
        changed = False
        current = tuple(pool)
        for left in current:
            for right in current:
                if left.kind is not right.kind:
                    continue
                for op in operations:
                    if op == "difference":
                        expr = left - right
                    elif op == "intersection":
                        expr = left & right
                    elif op == "union":
                        expr = left | right
                    else:
                        raise ValueError(op)
                    if selector_complexity(expr) > max_cost:
                        continue
                    key = repr(expr)
                    if key in seen:
                        continue
                    seen.add(key)
                    pool.append(expr)
                    changed = True
    pool.sort(key=lambda s: (selector_complexity(s), repr(s)))
    return tuple(pool)


def mine_selector_expression_laws(
    base_selectors: Iterable[Selector],
    *,
    universe,
    through: int,
    hypothesis: WordPredicate | None = None,
    max_cost: int = 3,
    expression_operations: tuple[str, ...] = ("difference", "intersection", "union"),
    relations: tuple[str, ...] = ("eq", "subset"),
    start: int = 1,
) -> tuple[MinedLaw, ...]:
    """Mine laws after synthesizing small selector expressions.

    This is the first AC miner capable of discovering a law such as
    ``Repeat = RunStart - {1}`` without being handed the compound selector.
    """

    expressions = generate_selector_expressions(
        base_selectors, max_cost=max_cost, operations=expression_operations
    )
    laws = mine_selector_laws(
        expressions,
        universe=universe,
        through=through,
        hypothesis=hypothesis,
        relations=relations,
        start=start,
    )
    # Prefer simpler expressions and discard tautological syntactic self-laws
    # (the pairwise miner already avoids identical expression objects).
    return tuple(
        sorted(
            laws,
            key=lambda law: (
                selector_complexity(law.left) + selector_complexity(law.right),
                law.relation,
                repr(law.left),
                repr(law.right),
            ),
        )
    )


@dataclass(frozen=True)
class SelectorEquivalenceClass:
    representative: Selector
    aliases: tuple[Selector, ...]
    matched_words: int

    @property
    def size(self) -> int:
        return 1 + len(self.aliases)


def mine_selector_equivalence_classes(
    selectors: Iterable[Selector],
    *,
    universe,
    through: int,
    hypothesis: WordPredicate | None = None,
    start: int = 1,
    min_size: int = 2,
) -> tuple[SelectorEquivalenceClass, ...]:
    """Group selector expressions that are extensionally equal on a finite theory.

    Unlike pairwise law mining, this produces one compact semantic class rather
    than dozens of redundant equalities.  The simplest expression is chosen as
    representative; the remaining expressions are retained as aliases, which is
    useful for discovering structural normal forms such as
    ``Repeat == RunStart-{1}``.
    """

    hypothesis = hypothesis or __import__('ac.logic.predicates', fromlist=['Always']).Always()
    selectors = tuple(selectors)
    samples = []
    for n in range(start, through + 1):
        for word in universe(n):
            if hypothesis.holds(word):
                samples.append(word)

    groups: dict[tuple[tuple[int, ...], ...], list[Selector]] = {}
    for selector in selectors:
        signature = tuple(
            tuple(sorted(int(item) for item in selector.evaluate(word)))
            for word in samples
        )
        groups.setdefault(signature, []).append(selector)

    out: list[SelectorEquivalenceClass] = []
    for expressions in groups.values():
        if len(expressions) < min_size:
            continue
        expressions.sort(key=lambda s: (selector_complexity(s), repr(s)))
        out.append(
            SelectorEquivalenceClass(
                representative=expressions[0],
                aliases=tuple(expressions[1:]),
                matched_words=len(samples),
            )
        )
    out.sort(
        key=lambda cls: (
            selector_complexity(cls.representative),
            -cls.size,
            repr(cls.representative),
        )
    )
    return tuple(out)
