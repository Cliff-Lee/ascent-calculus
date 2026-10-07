from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ac.solvers.exhaustive import VerificationResult, VerificationStatus, verify_on


@dataclass(frozen=True)
class SchemaInstance:
    parameter: object
    statement: object
    hypothesis: object
    verification: VerificationResult

    @property
    def ok(self) -> bool:
        return self.verification.status is VerificationStatus.VERIFIED


@dataclass(frozen=True)
class SchemaReport:
    name: str
    instances: tuple[SchemaInstance, ...]

    @property
    def verified(self) -> bool:
        return all(instance.ok for instance in self.instances)

    @property
    def counterexamples(self):
        return tuple(
            (instance.parameter, instance.verification.counterexample)
            for instance in self.instances
            if not instance.ok
        )


def verify_parameterized_schema(
    name: str,
    parameters: Iterable[object],
    *,
    law_factory,
    hypothesis_factory,
    universe,
    through: int,
    start: int = 1,
) -> SchemaReport:
    rows: list[SchemaInstance] = []
    for parameter in parameters:
        law = law_factory(parameter)
        hypothesis = hypothesis_factory(parameter)
        result = verify_on(law, universe=universe, through=through, hypothesis=hypothesis, start=start)
        rows.append(SchemaInstance(parameter, law, hypothesis, result))
    return SchemaReport(name, tuple(rows))
