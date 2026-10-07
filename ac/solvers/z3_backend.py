from __future__ import annotations

"""Optional fixed-length Z3 compiler for AC finite logic.

Quantifiers are expanded over the finite position/value chains.  This keeps the
compiled fragment quantifier-free while preserving exactly the executable AC
semantics at a specified ``(n, height)``.
"""

from ac.core.word import ChainWord
from ac.logic import fo
from ac.solvers.models import ModelResult, ModelStatus


def _z3():
    import z3  # type: ignore
    return z3


class Z3Compiler:
    def __init__(self, n: int, height: int):
        z3 = _z3()
        self.z3 = z3
        self.n = n
        self.height = height
        self.x = tuple(z3.Int(f"x_{i}") for i in range(1, n + 1))

    def bounds(self):
        z3 = self.z3
        if self.n == 0:
            return z3.BoolVal(True)
        if self.height == 0:
            return z3.BoolVal(False)
        return z3.And(*(z3.And(1 <= x, x <= self.height) for x in self.x))

    def _term(self, term: fo.Term, env: dict[fo.Var, int]):
        z3 = self.z3
        if isinstance(term, fo.Var):
            if term not in env:
                raise ValueError(f"unbound variable {term.name!r}")
            return z3.IntVal(env[term])
        if isinstance(term, fo.Const):
            return z3.IntVal(term.value)
        if isinstance(term, fo.At):
            p = self._concrete(term.position, env)
            if p < 1 or p > self.n:
                raise ValueError(f"position {p} outside fixed word")
            return self.x[p - 1]
        raise TypeError(f"unsupported term {type(term).__name__}")

    def _concrete(self, term: fo.Term, env: dict[fo.Var, int]) -> int:
        if isinstance(term, fo.Var):
            if term not in env:
                raise ValueError(f"unbound variable {term.name!r}")
            return env[term]
        if isinstance(term, fo.Const):
            return term.value
        raise TypeError("structural atoms require concrete finite-chain indices")

    def formula(self, formula: fo.Formula, env: dict[fo.Var, int] | None = None):
        z3 = self.z3
        env = {} if env is None else env
        if isinstance(formula, fo.Bool):
            return z3.BoolVal(formula.value)
        if isinstance(formula, fo.Not):
            return z3.Not(self.formula(formula.child, env))
        if isinstance(formula, fo.And):
            return z3.And(*(self.formula(p, env) for p in formula.parts))
        if isinstance(formula, fo.Or):
            return z3.Or(*(self.formula(p, env) for p in formula.parts))
        if isinstance(formula, fo.Implies):
            return z3.Implies(self.formula(formula.premise, env), self.formula(formula.conclusion, env))
        if isinstance(formula, fo.Iff):
            return self.formula(formula.left, env) == self.formula(formula.right, env)
        if isinstance(formula, fo.Compare):
            a = self._term(formula.left, env)
            b = self._term(formula.right, env)
            return {"eq": a == b, "lt": a < b, "le": a <= b}[formula.op]
        if isinstance(formula, fo.Adjacent):
            return self._term(formula.right, env) == self._term(formula.left, env) + 1
        if isinstance(formula, fo.Quantifier):
            domain = range(1, self.n + 1) if formula.var.sort is fo.Sort.POSITION else range(1, self.height + 1)
            parts = []
            for value in domain:
                child = dict(env)
                child[formula.var] = value
                parts.append(self.formula(formula.body, child))
            return z3.And(*parts) if formula.kind == "forall" else z3.Or(*parts)

        # Structural atoms compile directly from the fixed word variables.
        if isinstance(formula, fo.FirstPositionAt):
            i = self._concrete(formula.position, env)
            return z3.BoolVal(i == 1)
        if isinstance(formula, fo.LastPositionAt):
            i = self._concrete(formula.position, env)
            return z3.BoolVal(i == self.n)
        if isinstance(formula, fo.FirstAt):
            i = self._concrete(formula.position, env)
            return z3.And(*(self.x[j - 1] != self.x[i - 1] for j in range(1, i)))
        if isinstance(formula, fo.LastAt):
            i = self._concrete(formula.position, env)
            return z3.And(*(self.x[j - 1] != self.x[i - 1] for j in range(i + 1, self.n + 1)))
        if isinstance(formula, fo.OccAt):
            i = self._concrete(formula.position, env)
            count = z3.Sum(*(z3.If(self.x[j - 1] == self.x[i - 1], 1, 0) for j in range(1, i)))
            return count == formula.rank - 1
        if isinstance(formula, fo.RawAscTopAt):
            i = self._concrete(formula.position, env)
            return z3.BoolVal(False) if i <= 1 else self.x[i - 2] < self.x[i - 1]
        if isinstance(formula, fo.RawAscBottomAt):
            i = self._concrete(formula.position, env)
            return z3.BoolVal(False) if i >= self.n else self.x[i - 1] < self.x[i]
        if isinstance(formula, fo.RawDescTopAt):
            i = self._concrete(formula.position, env)
            return z3.BoolVal(False) if i >= self.n else self.x[i - 1] > self.x[i]
        if isinstance(formula, fo.RawDescBottomAt):
            i = self._concrete(formula.position, env)
            return z3.BoolVal(False) if i <= 1 else self.x[i - 2] > self.x[i - 1]
        if isinstance(formula, fo.AscTopAt):
            i = self._concrete(formula.position, env)
            return z3.BoolVal(True) if i == 1 else self.x[i - 2] < self.x[i - 1]
        if isinstance(formula, fo.AscBottomAt):
            i = self._concrete(formula.position, env)
            if i == 1:
                return z3.BoolVal(True)
            return z3.BoolVal(False) if i >= self.n else self.x[i - 1] < self.x[i]
        if isinstance(formula, fo.RunStartAt):
            i = self._concrete(formula.position, env)
            return z3.BoolVal(True) if i == 1 else self.x[i - 2] >= self.x[i - 1]
        if isinstance(formula, fo.RunEndAt):
            i = self._concrete(formula.position, env)
            return z3.BoolVal(True) if i == self.n else self.x[i - 1] >= self.x[i]
        if isinstance(formula, fo.Occupied):
            v = self._term(formula.value, env)
            return z3.Or(*(x == v for x in self.x))
        if isinstance(formula, fo.MultiplicityLe):
            v = self._term(formula.value, env)
            return z3.Sum(*(z3.If(x == v, 1, 0) for x in self.x)) <= formula.bound
        if isinstance(formula, fo.AscentAllowedAt):
            i = self._concrete(formula.position, env)
            if i == 1:
                return self.x[0] == 1
            count = z3.Sum(*(z3.If(self.x[j - 1] < self.x[j], 1, 0) for j in range(1, i - 1)))
            return self.x[i - 1] <= count + 2
        raise TypeError(f"unsupported formula node {type(formula).__name__}")


def solve_z3(formula: fo.Formula, *, n: int, height: int) -> ModelResult:
    z3 = _z3()
    compiler = Z3Compiler(n, height)
    solver = z3.Solver()
    solver.add(compiler.bounds())
    solver.add(compiler.formula(formula))
    if solver.check() != z3.sat:
        return ModelResult(ModelStatus.UNSAT, n, height, "z3")

    # Canonicalize to lexicographically smallest model by fixing one coordinate
    # at a time.  This keeps counterexamples stable across solver versions.
    fixed = []
    values: list[int] = []
    for i, x in enumerate(compiler.x):
        chosen = None
        for value in range(1, height + 1):
            trial = z3.Solver()
            trial.add(compiler.bounds(), compiler.formula(formula), *fixed, x == value)
            if trial.check() == z3.sat:
                chosen = value
                fixed.append(x == value)
                values.append(value)
                break
        if chosen is None:
            raise AssertionError("SAT model lost during lexicographic reconstruction")
    return ModelResult(ModelStatus.SAT, n, height, "z3", model=ChainWord(tuple(values), height=height))
