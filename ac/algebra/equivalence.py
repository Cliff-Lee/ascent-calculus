from __future__ import annotations

from dataclasses import dataclass

from ac.core.word import ChainWord
from ac.logic.predicates import Always, WordPredicate
from ac.algebra.transforms import Transformation


@dataclass(frozen=True)
class TransformCounterexample:
    source: ChainWord
    left_output: ChainWord | None
    right_output: ChainWord | None
    left_defined: bool
    right_defined: bool


def transformation_counterexample(
    left: Transformation,
    right: Transformation,
    *,
    universe,
    through: int,
    hypothesis: WordPredicate | None = None,
    start: int = 1,
) -> TransformCounterexample | None:
    """Return the first word on which two symbolic transformations differ."""
    hypothesis = Always() if hypothesis is None else hypothesis
    for n in range(start, through + 1):
        for word in universe(n):
            if not hypothesis.holds(word):
                continue
            ld = left.defined_on(word)
            rd = right.defined_on(word)
            if ld != rd:
                return TransformCounterexample(word, None, None, ld, rd)
            if not ld:
                continue
            lo = left.apply(word).output
            ro = right.apply(word).output
            if lo.values != ro.values or lo.height != ro.height:
                return TransformCounterexample(word, lo, ro, True, True)
    return None
