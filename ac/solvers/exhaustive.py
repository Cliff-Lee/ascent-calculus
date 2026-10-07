from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Iterable

from ac.core.word import ChainWord
from ac.logic.predicates import Always, WordPredicate


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    COUNTEREXAMPLE = "counterexample"


@dataclass(frozen=True)
class VerificationResult:
    status: VerificationStatus
    max_n: int
    tested: int
    hypotheses_matched: int
    counterexample: ChainWord | None = None
    counterexample_n: int | None = None

    @property
    def ok(self) -> bool:
        return self.status is VerificationStatus.VERIFIED


UniverseFactory = Callable[[int], Iterable[ChainWord]]


def verify_on(
    law: WordPredicate,
    *,
    universe: UniverseFactory,
    through: int,
    hypothesis: WordPredicate | None = None,
    start: int = 1,
) -> VerificationResult:
    """Finite verification with smallest-length, generator-order counterexample."""
    if through < start:
        raise ValueError("through must be >= start")
    hypothesis = Always() if hypothesis is None else hypothesis
    tested = 0
    matched = 0
    for n in range(start, through + 1):
        for word in universe(n):
            tested += 1
            if not hypothesis.holds(word):
                continue
            matched += 1
            if not law.holds(word):
                return VerificationResult(
                    VerificationStatus.COUNTEREXAMPLE,
                    max_n=through,
                    tested=tested,
                    hypotheses_matched=matched,
                    counterexample=word,
                    counterexample_n=n,
                )
    return VerificationResult(
        VerificationStatus.VERIFIED,
        max_n=through,
        tested=tested,
        hypotheses_matched=matched,
    )
