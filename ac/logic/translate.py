from __future__ import annotations

"""Translation from the original AC selector/predicate DSL into finite logic."""

from ac.logic import selectors as sel
from ac.logic import predicates as pred
from ac.logic.fo import (
    Formula,
    TRUE,
    FALSE,
    P,
    PVar,
    Eq,
    Iff,
    ForAll,
    FirstPositionAt,
    LastPositionAt,
    FirstAt,
    LastAt,
    OccAt,
    RawAscTopAt,
    RawAscBottomAt,
    RawDescTopAt,
    RawDescBottomAt,
    AscTopAt,
    AscBottomAt,
    RunStartAt,
    RunEndAt,
    CayleyFormula,
    AscentSequenceFormula,
    ModifiedFormula,
    RevisedFormula,
    AvoidConstantFormula,
    ContainsPatternFormula,
    AvoidPatternFormula,
)


def selector_membership(selector: sel.Selector, position) -> Formula:
    """Compile a whole-word position selector to a membership formula."""
    if selector.kind is not sel.SelectionKind.POSITION:
        raise TypeError("E6 selector translation currently targets position selectors")
    if isinstance(selector, sel.ScopeFirst):
        return FirstPositionAt(position)
    if isinstance(selector, sel.ScopeLast):
        return LastPositionAt(position)
    if isinstance(selector, sel.Positions):
        parts = tuple(Eq(position, P(i)) for i in selector.indices)
        from ac.logic.fo import Or
        return Or(parts) if parts else FALSE
    if isinstance(selector, sel.First):
        return FirstAt(position)
    if isinstance(selector, sel.Last):
        return LastAt(position)
    if isinstance(selector, sel.Occ):
        return OccAt(position, selector.rank)
    if isinstance(selector, sel.Repeat):
        return ~FirstAt(position)
    if isinstance(selector, sel.RawAscTop):
        return RawAscTopAt(position)
    if isinstance(selector, sel.RawAscBottom):
        return RawAscBottomAt(position)
    if isinstance(selector, sel.RawDescTop):
        return RawDescTopAt(position)
    if isinstance(selector, sel.RawDescBottom):
        return RawDescBottomAt(position)
    if isinstance(selector, sel.AscTop):
        return AscTopAt(position)
    if isinstance(selector, sel.AscBottom):
        return AscBottomAt(position)
    if isinstance(selector, sel.DescTop):
        return RawDescTopAt(position)
    if isinstance(selector, sel.DescBottom):
        return RawDescBottomAt(position)
    if isinstance(selector, sel.RunStart):
        return RunStartAt(position)
    if isinstance(selector, sel.RunEnd):
        return RunEndAt(position)
    if isinstance(selector, sel.SetBinary):
        a = selector_membership(selector.left, position)
        b = selector_membership(selector.right, position)
        if selector.op == "union":
            return a | b
        if selector.op == "intersection":
            return a & b
        if selector.op == "difference":
            return a & ~b
        raise ValueError(selector.op)
    if isinstance(selector, sel.SetComplement):
        return ~selector_membership(selector.child, position)
    raise TypeError(f"unsupported selector for finite-logic translation: {type(selector).__name__}")


def predicate_to_formula(predicate: pred.WordPredicate) -> Formula:
    if isinstance(predicate, pred.Always):
        return TRUE
    if isinstance(predicate, pred.Cayley):
        return CayleyFormula()
    if isinstance(predicate, pred.AscentSequence):
        return AscentSequenceFormula()
    if isinstance(predicate, pred.Modified):
        return ModifiedFormula()
    if isinstance(predicate, pred.Revised):
        return RevisedFormula()
    if isinstance(predicate, pred.AvoidConstant):
        return AvoidConstantFormula(predicate.r)
    if isinstance(predicate, pred.ContainsPattern):
        return ContainsPatternFormula(predicate.pattern)
    if isinstance(predicate, pred.AvoidPattern):
        return AvoidPatternFormula(predicate.pattern)
    if isinstance(predicate, pred.PredicateBinary):
        a = predicate_to_formula(predicate.left)
        b = predicate_to_formula(predicate.right)
        return a & b if predicate.op == "and" else a | b
    if isinstance(predicate, pred.PredicateNot):
        return ~predicate_to_formula(predicate.child)
    if isinstance(predicate, pred.PredicateImplies):
        return predicate_to_formula(predicate.premise).implies(predicate_to_formula(predicate.conclusion))
    if isinstance(predicate, (pred.SameSet, pred.Subset, pred.Disjoint)):
        i = PVar("i")
        a = selector_membership(predicate.left, i)
        b = selector_membership(predicate.right, i)
        if isinstance(predicate, pred.SameSet):
            body = Iff(a, b)
        elif isinstance(predicate, pred.Subset):
            body = a.implies(b)
        else:
            body = ~(a & b)
        return ForAll(i, body)
    raise TypeError(f"unsupported predicate for finite-logic translation: {type(predicate).__name__}")
