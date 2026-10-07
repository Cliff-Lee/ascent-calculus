from __future__ import annotations

from ac.algebra.transforms import ComplementT, Compose, Identity, ReverseT, Transformation
from ac.patterns.classical import ClassicalPattern


def transport_classical_pattern(
    pattern: ClassicalPattern,
    transform: Transformation,
) -> ClassicalPattern:
    """Transport a classical pattern through the global R/C symmetry algebra.

    This intentionally supports only transformations whose action on every
    selected occurrence is exact at the compressed-pattern level.  Lifts are
    excluded because compression forgets the ambient gap information needed to
    determine their pattern transport.
    """
    t = transform.normal_form()
    if isinstance(t, Identity):
        return pattern
    if isinstance(t, ReverseT):
        return pattern.reverse()
    if isinstance(t, ComplementT):
        return pattern.complement()
    if isinstance(t, Compose):
        p = pattern
        for part in t.parts:
            p = transport_classical_pattern(p, part)
        return p
    raise TypeError(
        f"classical pattern transport is not determined by compressed pattern alone under {type(t).__name__}"
    )
