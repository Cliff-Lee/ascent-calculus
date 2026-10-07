from __future__ import annotations

"""Finite first-order layer for Ascent Calculus.

The language has two finite sorts, positions and ambient value levels.  It is
intentionally small: order/equality, evaluation x(i), occurrence predicates,
local edge roles, multiplicity bounds, Boolean connectives, and finite
quantifiers.  The executable evaluator is the reference semantics.  Solver
backends compile the same immutable AST.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from ac.core.word import ChainWord


class Sort(str, Enum):
    POSITION = "position"
    VALUE = "value"


Env = Mapping["Var", int]


class Term:
    sort: Sort

    def eval(self, word: ChainWord, env: Env) -> int:
        raise NotImplementedError


@dataclass(frozen=True)
class Var(Term):
    name: str
    sort: Sort

    def eval(self, word: ChainWord, env: Env) -> int:
        if self not in env:
            raise ValueError(f"unbound variable {self.name!r}")
        return int(env[self])


@dataclass(frozen=True)
class Const(Term):
    value: int
    sort: Sort

    def __post_init__(self) -> None:
        if self.value < 1:
            raise ValueError("finite-chain constants are 1-based")

    def eval(self, word: ChainWord, env: Env) -> int:
        return self.value


@dataclass(frozen=True)
class At(Term):
    position: Term
    sort: Sort = Sort.VALUE

    def __post_init__(self) -> None:
        if self.position.sort is not Sort.POSITION:
            raise TypeError("At expects a position term")

    def eval(self, word: ChainWord, env: Env) -> int:
        return word.at(self.position.eval(word, env))


def PVar(name: str) -> Var:
    return Var(name, Sort.POSITION)


def VVar(name: str) -> Var:
    return Var(name, Sort.VALUE)


def P(value: int) -> Const:
    return Const(value, Sort.POSITION)


def V(value: int) -> Const:
    return Const(value, Sort.VALUE)


class Formula:
    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        raise NotImplementedError

    def __and__(self, other: "Formula") -> "Formula":
        if not isinstance(other, Formula):
            raise TypeError("formula conjunction requires another Formula")
        return And((self, other))

    def __or__(self, other: "Formula") -> "Formula":
        if not isinstance(other, Formula):
            raise TypeError("formula disjunction requires another Formula")
        return Or((self, other))

    def __invert__(self) -> "Formula":
        return Not(self)

    def implies(self, other: "Formula") -> "Formula":
        if not isinstance(other, Formula):
            raise TypeError("implication requires another Formula")
        return Implies(self, other)

    def iff(self, other: "Formula") -> "Formula":
        if not isinstance(other, Formula):
            raise TypeError("biconditional requires another Formula")
        return Iff(self, other)


@dataclass(frozen=True)
class Bool(Formula):
    value: bool

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        return self.value


TRUE = Bool(True)
FALSE = Bool(False)


@dataclass(frozen=True)
class Not(Formula):
    child: Formula

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        return not self.child.holds(word, {} if env is None else env)


@dataclass(frozen=True)
class And(Formula):
    parts: tuple[Formula, ...]

    def __init__(self, parts):
        flat: list[Formula] = []
        for part in parts:
            if isinstance(part, And):
                flat.extend(part.parts)
            else:
                if not isinstance(part, Formula):
                    raise TypeError("And parts must be Formula objects")
                flat.append(part)
        object.__setattr__(self, "parts", tuple(flat))

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        return all(p.holds(word, env) for p in self.parts)


@dataclass(frozen=True)
class Or(Formula):
    parts: tuple[Formula, ...]

    def __init__(self, parts):
        flat: list[Formula] = []
        for part in parts:
            if isinstance(part, Or):
                flat.extend(part.parts)
            else:
                if not isinstance(part, Formula):
                    raise TypeError("Or parts must be Formula objects")
                flat.append(part)
        object.__setattr__(self, "parts", tuple(flat))

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        return any(p.holds(word, env) for p in self.parts)


@dataclass(frozen=True)
class Implies(Formula):
    premise: Formula
    conclusion: Formula

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        return (not self.premise.holds(word, env)) or self.conclusion.holds(word, env)


@dataclass(frozen=True)
class Iff(Formula):
    left: Formula
    right: Formula

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        return self.left.holds(word, env) == self.right.holds(word, env)


@dataclass(frozen=True)
class Compare(Formula):
    op: str
    left: Term
    right: Term

    def __post_init__(self) -> None:
        if self.left.sort is not self.right.sort:
            raise TypeError("ordered/equality comparisons require equal term sorts")
        if self.op not in {"eq", "lt", "le"}:
            raise ValueError(self.op)

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        a = self.left.eval(word, env)
        b = self.right.eval(word, env)
        if self.op == "eq":
            return a == b
        if self.op == "lt":
            return a < b
        return a <= b


def Eq(left: Term, right: Term) -> Formula:
    return Compare("eq", left, right)


def Lt(left: Term, right: Term) -> Formula:
    return Compare("lt", left, right)


def Le(left: Term, right: Term) -> Formula:
    return Compare("le", left, right)


@dataclass(frozen=True)
class Adjacent(Formula):
    left: Term
    right: Term

    def __post_init__(self) -> None:
        if self.left.sort is not self.right.sort:
            raise TypeError("adjacency requires equal sorts")

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        return self.right.eval(word, env) == self.left.eval(word, env) + 1


# ---- Structural atoms on positions / values ----


@dataclass(frozen=True)
class FirstPositionAt(Formula):
    position: Term

    def __post_init__(self) -> None:
        if self.position.sort is not Sort.POSITION:
            raise TypeError("FirstPositionAt expects a position")

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        return self.position.eval(word, env) == 1


@dataclass(frozen=True)
class LastPositionAt(Formula):
    position: Term

    def __post_init__(self) -> None:
        if self.position.sort is not Sort.POSITION:
            raise TypeError("LastPositionAt expects a position")

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        return self.position.eval(word, env) == len(word)


@dataclass(frozen=True)
class FirstAt(Formula):
    position: Term

    def __post_init__(self) -> None:
        if self.position.sort is not Sort.POSITION:
            raise TypeError("FirstAt expects a position")

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        i = self.position.eval(word, env)
        return i in word.first_positions


@dataclass(frozen=True)
class LastAt(Formula):
    position: Term

    def __post_init__(self) -> None:
        if self.position.sort is not Sort.POSITION:
            raise TypeError("LastAt expects a position")

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        i = self.position.eval(word, env)
        return i in word.last_positions


@dataclass(frozen=True)
class OccAt(Formula):
    position: Term
    rank: int

    def __post_init__(self) -> None:
        if self.position.sort is not Sort.POSITION:
            raise TypeError("OccAt expects a position")
        if self.rank < 1:
            raise ValueError("occurrence rank must be >= 1")

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        i = self.position.eval(word, env)
        return word.occurrence_rank(i) == self.rank


@dataclass(frozen=True)
class RawAscTopAt(Formula):
    position: Term

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        return self.position.eval(word, env) in word.raw_ascent_tops


@dataclass(frozen=True)
class RawAscBottomAt(Formula):
    position: Term

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        return self.position.eval(word, env) in word.raw_ascent_bottoms


@dataclass(frozen=True)
class RawDescTopAt(Formula):
    position: Term

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        return self.position.eval(word, env) in word.raw_descent_tops


@dataclass(frozen=True)
class RawDescBottomAt(Formula):
    position: Term

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        return self.position.eval(word, env) in word.raw_descent_bottoms


@dataclass(frozen=True)
class AscTopAt(Formula):
    position: Term

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        return self.position.eval(word, env) in word.ascent_tops


@dataclass(frozen=True)
class AscBottomAt(Formula):
    position: Term

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        return self.position.eval(word, env) in word.ascent_bottoms


@dataclass(frozen=True)
class RunStartAt(Formula):
    position: Term

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        return self.position.eval(word, env) in word.run_starts


@dataclass(frozen=True)
class RunEndAt(Formula):
    position: Term

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        return self.position.eval(word, env) in word.run_ends


@dataclass(frozen=True)
class Occupied(Formula):
    value: Term

    def __post_init__(self) -> None:
        if self.value.sort is not Sort.VALUE:
            raise TypeError("Occupied expects a value term")

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        v = self.value.eval(word, env)
        return bool(word.fibre(v))


@dataclass(frozen=True)
class MultiplicityLe(Formula):
    value: Term
    bound: int

    def __post_init__(self) -> None:
        if self.value.sort is not Sort.VALUE:
            raise TypeError("MultiplicityLe expects a value term")
        if self.bound < 0:
            raise ValueError("multiplicity bound must be nonnegative")

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        return len(word.fibre(self.value.eval(word, env))) <= self.bound


@dataclass(frozen=True)
class AscentAllowedAt(Formula):
    """Positive-convention ordinary ascent-sequence local growth rule."""

    position: Term

    def __post_init__(self) -> None:
        if self.position.sort is not Sort.POSITION:
            raise TypeError("AscentAllowedAt expects a position")

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        env = {} if env is None else env
        i = self.position.eval(word, env)
        if i == 1:
            return word.at(1) == 1
        asc_before = sum(1 for j in range(1, i - 1) if word.at(j) < word.at(j + 1))
        return 1 <= word.at(i) <= asc_before + 2


# ---- Finite quantifiers ----


@dataclass(frozen=True)
class Quantifier(Formula):
    kind: str
    var: Var
    body: Formula

    def __post_init__(self) -> None:
        if self.kind not in {"forall", "exists"}:
            raise ValueError(self.kind)

    def holds(self, word: ChainWord, env: Env | None = None) -> bool:
        base = {} if env is None else dict(env)
        domain = range(1, len(word) + 1) if self.var.sort is Sort.POSITION else range(1, word.height + 1)
        if self.kind == "forall":
            for value in domain:
                child_env = dict(base)
                child_env[self.var] = value
                if not self.body.holds(word, child_env):
                    return False
            return True
        for value in domain:
            child_env = dict(base)
            child_env[self.var] = value
            if self.body.holds(word, child_env):
                return True
        return False


def ForAll(var: Var, body: Formula) -> Formula:
    return Quantifier("forall", var, body)


def Exists(var: Var, body: Formula) -> Formula:
    return Quantifier("exists", var, body)


def ForAllPos(var: Var | str, body_fn) -> Formula:
    v = PVar(var) if isinstance(var, str) else var
    if v.sort is not Sort.POSITION:
        raise TypeError("ForAllPos requires a position variable")
    body = body_fn(v) if callable(body_fn) else body_fn
    return ForAll(v, body)


def ExistsPos(var: Var | str, body_fn) -> Formula:
    v = PVar(var) if isinstance(var, str) else var
    if v.sort is not Sort.POSITION:
        raise TypeError("ExistsPos requires a position variable")
    body = body_fn(v) if callable(body_fn) else body_fn
    return Exists(v, body)


def ForAllVal(var: Var | str, body_fn) -> Formula:
    v = VVar(var) if isinstance(var, str) else var
    if v.sort is not Sort.VALUE:
        raise TypeError("ForAllVal requires a value variable")
    body = body_fn(v) if callable(body_fn) else body_fn
    return ForAll(v, body)


def ExistsVal(var: Var | str, body_fn) -> Formula:
    v = VVar(var) if isinstance(var, str) else var
    if v.sort is not Sort.VALUE:
        raise TypeError("ExistsVal requires a value variable")
    body = body_fn(v) if callable(body_fn) else body_fn
    return Exists(v, body)


# ---- Theory / pattern constructors in the same logic ----


def CayleyFormula() -> Formula:
    v = VVar("v")
    return ForAll(v, Occupied(v))


def ModifiedFormula() -> Formula:
    i = PVar("i")
    return CayleyFormula() & ForAll(i, Iff(FirstAt(i), AscTopAt(i)))


def RevisedFormula() -> Formula:
    i = PVar("i")
    return CayleyFormula() & ForAll(i, Iff(FirstAt(i), AscBottomAt(i)))


def AscentSequenceFormula() -> Formula:
    i = PVar("i")
    # Ordinary ascent sequences are nonempty in the positive convention.
    return Exists(i, TRUE) & ForAll(i, AscentAllowedAt(i))


def AvoidConstantFormula(r: int) -> Formula:
    if r < 1:
        raise ValueError("r must be >= 1")
    v = VVar("v")
    return ForAll(v, MultiplicityLe(v, r - 1))


def ContainsPatternFormula(pattern) -> Formula:
    from ac.patterns.classical import ClassicalPattern

    p = pattern if isinstance(pattern, ClassicalPattern) else ClassicalPattern(pattern)
    vars_ = tuple(PVar(f"p{k}") for k in range(1, p.arity + 1))
    parts: list[Formula] = []
    for a, b in zip(vars_, vars_[1:]):
        parts.append(Lt(a, b))
    for i in range(p.arity):
        for j in range(i + 1, p.arity):
            if p.values[i] == p.values[j]:
                parts.append(Eq(At(vars_[i]), At(vars_[j])))
            elif p.values[i] < p.values[j]:
                parts.append(Lt(At(vars_[i]), At(vars_[j])))
            else:
                parts.append(Lt(At(vars_[j]), At(vars_[i])))
    body: Formula = And(tuple(parts)) if parts else TRUE
    for var in reversed(vars_):
        body = Exists(var, body)
    return body


def AvoidPatternFormula(pattern) -> Formula:
    return Not(ContainsPatternFormula(pattern))
