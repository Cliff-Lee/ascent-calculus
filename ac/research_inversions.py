"""Bounded inversion-sequence reference adapter; no ascent-family aliasing."""
from dataclasses import dataclass
from ac.core.word import ChainWord
from ac.research_math import SourcePattern, integer


@dataclass(frozen=True)
class InversionClass:
    """Zero-based entries e[i] <= i; classical equality-sensitive avoidance."""
    avoid: tuple[SourcePattern, ...]

    def __post_init__(self):
        if type(self.avoid) is not tuple or len(self.avoid) > 12:
            raise ValueError('Bounded pattern tuple required')
        if any(type(p) is not SourcePattern or p.value_base != 0 or
               p.adjacent_positions for p in self.avoid):
            raise ValueError('Inversion adapter requires zero-based classical patterns')

    def words(self, length):
        integer(length, 0, 7)
        compiled = tuple(p.compile() for p in self.avoid)

        def grow(prefix):
            if len(prefix) == length:
                yield prefix
                return
            for value in range(len(prefix) + 1):
                candidate = prefix + (value,)
                positive = ChainWord(tuple(x + 1 for x in candidate))
                if not any(p.contains(positive) for p in compiled):
                    yield from grow(candidate)
        yield from grow(())


def testart_coefficients(max_degree):
    """Exact coefficients of Theorem 5, branch sqrt(1-8t)[0]=1.

    Solve S^2=1-8t, then (2-4t+4t^2)A=2-t-tS.
    This coefficient calculation is separate from either object enumerator.
    """
    from fractions import Fraction
    integer(max_degree, 0, 100)
    square_root = [Fraction(1)]
    counts = []
    for n in range(max_degree + 1):
        if n:
            convolution = sum(square_root[i] * square_root[n-i] for i in range(1,n))
            square_root.append((Fraction(-8 if n == 1 else 0) - convolution) / 2)
        rhs = Fraction(2) if n == 0 else -square_root[n-1] - (n == 1)
        coefficient = (rhs + (4*counts[n-1] if n else 0) -
                       (4*counts[n-2] if n >= 2 else 0)) / 2
        if coefficient.denominator != 1:
            raise ArithmeticError('Nonintegral reference coefficient')
        counts.append(int(coefficient))
    return tuple(counts)
