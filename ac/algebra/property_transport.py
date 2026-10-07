from __future__ import annotations

from dataclasses import dataclass

from ac.algebra.transforms import (
    Transformation,
    Identity,
    ReverseT,
    ComplementT,
    PrefixLiftT,
    Compose,
)
from ac.logic.predicates import (
    WordPredicate,
    PredicateBinary,
    PredicateNot,
    PredicateImplies,
    Always,
    Cayley,
    Modified,
    Revised,
    AvoidConstant,
    SameSet,
    ContainsPattern,
    AvoidPattern,
)
from ac.logic.selectors import (
    Selector,
    SetBinary,
    SetComplement,
    Positions,
    ScopeFirst,
    ScopeLast,
    First,
    Last,
    Occ,
    Repeat,
    RawAscBottom,
    RawAscTop,
    RawDescTop,
    RawDescBottom,
    AscTop,
    AscBottom,
    DescTop,
    DescBottom,
)


@dataclass(frozen=True)
class PullbackPredicate(WordPredicate):
    """Predicate ``T^*(P)`` on the source: ``P(T(x))``.

    Pullback is always meaningful for a deterministic transformation.  AC treats
    points outside the transformation's domain as not satisfying the pullback.
    """

    transform: Transformation
    predicate: WordPredicate

    def holds(self, word) -> bool:
        if not self.transform.defined_on(word):
            return False
        return self.predicate.holds(self.transform.apply(word).output)


@dataclass(frozen=True)
class PushforwardPredicate(WordPredicate):
    """Predicate ``T_*(P)`` on the target of an invertible/partially invertible T.

    Semantically, y satisfies the predicate exactly when the known functional
    inverse is defined at y and its preimage satisfies P.  Relational inverses
    (standardization, restriction, ...) are intentionally excluded for now.
    """

    transform: Transformation
    predicate: WordPredicate

    def holds(self, word) -> bool:
        inv = self.transform.inverse()
        if not inv.defined_on(word):
            return False
        return self.predicate.holds(inv.apply(word).output)


def pullback(transform: Transformation, predicate: WordPredicate) -> WordPredicate:
    return PullbackPredicate(transform.normal_form(), predicate)


def pushforward(transform: Transformation, predicate: WordPredicate) -> WordPredicate:
    # Calling inverse here is a deliberate early domain check.
    transform.inverse()
    return PushforwardPredicate(transform.normal_form(), predicate)


def _transport_selector_atom(selector: Selector, transform: Transformation) -> Selector:
    """Exact symbolic transport for selector atoms under currently known laws."""
    t = transform.normal_form()
    if isinstance(t, Identity):
        return selector
    if isinstance(t, Compose):
        out = selector
        for part in t.parts:
            out = transport_selector(out, part)
        return out

    # Boolean set expressions transport homomorphically when each child does.
    if isinstance(selector, SetBinary):
        a = transport_selector(selector.left, t)
        b = transport_selector(selector.right, t)
        if selector.op == "union":
            return a | b
        if selector.op == "intersection":
            return a & b
        if selector.op == "difference":
            return a - b
        raise ValueError(selector.op)
    if isinstance(selector, SetComplement):
        return ~transport_selector(selector.child, t)

    if isinstance(t, ReverseT):
        table = {
            ScopeFirst: ScopeLast,
            ScopeLast: ScopeFirst,
            First: Last,
            Last: First,
            RawAscTop: RawDescTop,
            RawAscBottom: RawDescBottom,
            RawDescTop: RawAscTop,
            RawDescBottom: RawAscBottom,
            AscTop: lambda: ScopeLast() | RawDescTop(),
            AscBottom: lambda: ScopeLast() | RawDescBottom(),
            DescTop: RawAscTop,
            DescBottom: RawAscBottom,
        }
        ctor = table.get(type(selector))
        if ctor is not None:
            return ctor()
        # Repeat is the complement of first occurrences in the positional scope.
        if isinstance(selector, Repeat):
            return ~Last()
        raise TypeError(f"no exact symbolic reversal law registered for {type(selector).__name__}")

    if isinstance(t, ComplementT):
        table = {
            ScopeFirst: ScopeFirst,
            ScopeLast: ScopeLast,
            First: First,
            Last: Last,
            Occ: lambda: Occ(selector.rank),
            Repeat: Repeat,
            RawAscTop: RawDescBottom,
            RawAscBottom: RawDescTop,
            RawDescTop: RawAscBottom,
            RawDescBottom: RawAscTop,
            AscTop: lambda: ScopeFirst() | RawDescBottom(),
            AscBottom: lambda: ScopeFirst() | RawDescTop(),
            DescTop: RawAscBottom,
            DescBottom: RawAscTop,
        }
        ctor = table.get(type(selector))
        if ctor is not None:
            return ctor()
        if isinstance(selector, Positions):
            return selector
        raise TypeError(f"no exact symbolic complement law registered for {type(selector).__name__}")

    if isinstance(t, PrefixLiftT):
        # Prefix lifts preserve positions and the entire ascent-edge set.  No
        # analogous blanket law holds for descent/equality or occurrence data.
        if isinstance(selector, (ScopeFirst, ScopeLast, RawAscTop, RawAscBottom, AscTop, AscBottom, Positions)):
            return selector
        raise TypeError(f"no exact symbolic lift law registered for {type(selector).__name__}")

    raise TypeError(f"selector transport not implemented for {type(t).__name__}")


def transport_selector(selector: Selector, transform: Transformation) -> Selector:
    """Return a target selector selecting exactly the transported old positions.

    This is a symbolic theorem, not recomputation by provenance.  If AC does not
    know an exact selector-level law it raises rather than guessing.
    """
    return _transport_selector_atom(selector, transform)


def _expand_theory(predicate: WordPredicate) -> WordPredicate:
    if isinstance(predicate, Modified):
        return Cayley() & SameSet(First(), AscTop())
    if isinstance(predicate, Revised):
        return Cayley() & SameSet(First(), AscBottom())
    return predicate


def transport_predicate(predicate: WordPredicate, transform: Transformation) -> WordPredicate:
    """Symbolically push a predicate through a transformation when laws are known.

    Unsupported atoms fall back to the exact inverse-based pushforward when the
    transformation has a functional inverse.  This keeps the semantics correct
    while allowing the simplifier to expose useful structural formulas.
    """
    t = transform.normal_form()
    p = _expand_theory(predicate)

    if isinstance(t, Compose):
        out = p
        for part in t.parts:
            out = transport_predicate(out, part)
        return out
    if isinstance(t, Identity):
        return p

    if isinstance(p, PredicateBinary):
        left = transport_predicate(p.left, t)
        right = transport_predicate(p.right, t)
        return left & right if p.op == "and" else left | right
    if isinstance(p, PredicateNot):
        return ~transport_predicate(p.child, t)
    if isinstance(p, PredicateImplies):
        return transport_predicate(p.premise, t).implies(transport_predicate(p.conclusion, t))
    if isinstance(p, Always):
        return p

    if isinstance(p, Cayley) and isinstance(t, (ReverseT, ComplementT)):
        return p
    if isinstance(p, AvoidConstant) and isinstance(t, (ReverseT, ComplementT)):
        return p
    if isinstance(p, SameSet):
        try:
            return SameSet(
                transport_selector(p.left, t),
                transport_selector(p.right, t),
                scope=p.scope,
            )
        except TypeError:
            pass
    if isinstance(p, ContainsPattern) and isinstance(t, (ReverseT, ComplementT)):
        from ac.patterns.transport import transport_classical_pattern
        return ContainsPattern(transport_classical_pattern(p.pattern, t))
    if isinstance(p, AvoidPattern) and isinstance(t, (ReverseT, ComplementT)):
        from ac.patterns.transport import transport_classical_pattern
        return AvoidPattern(transport_classical_pattern(p.pattern, t))

    # Exact semantic fallback for reversible transformations.
    return pushforward(t, p)
