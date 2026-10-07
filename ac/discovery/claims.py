from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ac.core.word import ChainWord


class ClaimStatus(str, Enum):
    DEFINITION = "definition"
    PROVED = "proved"
    VERIFIED = "verified"
    CONJECTURE = "conjecture"
    REFUTED = "refuted"


@dataclass(frozen=True)
class ClaimRecord:
    name: str
    statement: object
    status: ClaimStatus
    evidence: str = ""
    dependencies: tuple[str, ...] = ()
    verified_through: int | None = None
    counterexample: ChainWord | None = None

    def __post_init__(self) -> None:
        if self.status is ClaimStatus.PROVED and not self.evidence:
            raise ValueError("PROVED claims require an explicit proof/evidence note")
        if self.status is ClaimStatus.VERIFIED and self.verified_through is None:
            raise ValueError("VERIFIED claims require verified_through")
        if self.status is ClaimStatus.REFUTED and self.counterexample is None:
            raise ValueError("REFUTED claims require a counterexample")


@dataclass
class ClaimRegistry:
    records: dict[str, ClaimRecord] = field(default_factory=dict)

    def add(self, record: ClaimRecord) -> ClaimRecord:
        if record.name in self.records:
            raise ValueError(f"claim {record.name!r} already registered")
        self.records[record.name] = record
        return record

    def get(self, name: str) -> ClaimRecord:
        return self.records[name]

    def by_status(self, status: ClaimStatus) -> tuple[ClaimRecord, ...]:
        return tuple(r for r in self.records.values() if r.status is status)


def claim_from_verification(name: str, statement: object, result, *, evidence: str = "exhaustive reference semantics") -> ClaimRecord:
    """Promote an exhaustive VerificationResult to a provenance-bearing claim."""
    from ac.solvers.exhaustive import VerificationStatus

    if result.status is VerificationStatus.VERIFIED:
        return ClaimRecord(
            name,
            statement,
            ClaimStatus.VERIFIED,
            evidence=evidence,
            verified_through=result.max_n,
        )
    return ClaimRecord(
        name,
        statement,
        ClaimStatus.REFUTED,
        evidence=evidence,
        counterexample=result.counterexample,
    )
