# AC finite logic and solver semantics (E6)

E6 adds a finite first-order layer over the same chain-word objects used by the
rest of Ascent Calculus.  The logic is not a replacement for selectors or the
pattern API.  It is the common representation into which those higher-level
objects can be translated for model search and counterexample generation.

## Sorts

The core language has two finite sorts:

- `POSITION`: the chain `[1..n]`;
- `VALUE`: the ambient value chain `[1..m]`.

A word is still a map `x : [n] -> [m]`; empty ambient value levels are retained.

Position/value variables are created with `PVar(name)` and `VVar(name)`.  `At(i)`
is the value occupying position `i`.  Order and equality are represented by
`Lt`, `Le`, and `Eq` and finite quantifiers by `ForAll` / `Exists`.

## Structural atoms

The logic exposes occurrence and local-edge structure without expanding those
notions manually in user code:

- `FirstAt(i)`, `LastAt(i)`, `OccAt(i,r)`;
- raw and literature ascent/descent endpoints;
- `RunStartAt(i)`, `RunEndAt(i)`;
- `Occupied(v)`, `MultiplicityLe(v,k)`;
- `AscentAllowedAt(i)` for the positive ordinary-ascent growth rule.

Boundary positions are explicit atoms (`FirstPositionAt`, `LastPositionAt`) rather
than being silently conflated with ascent roles.

## Theory constructors

The following build closed formulas from the formal definitions:

```python
ModifiedFormula()
RevisedFormula()
AscentSequenceFormula()
AvoidConstantFormula(r)
ContainsPatternFormula("2122")
AvoidPatternFormula("2122")
```

Classical-pattern formulas are generated from existentially quantified selected
positions plus their complete equality/order constraints.  Thus the E4 pattern
compiler and the E6 logical compiler have independent reference semantics that
can cross-check one another.

## Translation from the existing AC DSL

`predicate_to_formula(P)` translates the existing class/predicate language into
finite logic for the supported E6 fragment.  Position selectors are translated
pointwise using `selector_membership`.

For example:

```python
P = Modified() & Avoid("111") & SameSet(Repeat(), RunStart() - Positions([1]))
F = predicate_to_formula(P)
```

This is important architecturally: AC now has one user-facing structural DSL,
not a separate solver-only notation.

## Reference finite solver

`solve_formula(F, n=n, height=m, backend="finite")` enumerates the fixed finite
universe in lexicographic word order.  It is deliberately simple and serves as
the executable reference semantics.

`smallest_countermodel` searches by length, then ambient height, then word order.
This makes counterexamples reproducible.

The existing predicate DSL can be sent directly through `solve_predicate`.

## Optional Z3 backend

The optional `solver` extra installs `z3-solver`.  The Z3 compiler uses the same
formula AST and fixed `(n,m)` semantics.  Finite quantifiers are expanded over
their chains, so the generated solver problem is quantifier-free.  Word values
are bounded integer variables.

```bash
pip install -e '.[solver]'
```

`backend="auto"` prefers Z3 when installed and otherwise falls back to the finite
reference solver.  `backend="z3"` reports `UNAVAILABLE` cleanly if the optional
dependency is absent.

The current execution environment for the E6 campaign had no network access and
no preinstalled `z3-solver`, so the Z3 implementation is present but the campaign
verification used the finite reference backend.  The semantics it compiles are
covered independently by the executable formula tests.

## Claims and provenance

A mathematical claim can be recorded as one of:

- `DEFINITION`
- `PROVED`
- `VERIFIED`
- `CONJECTURE`
- `REFUTED`

`PROVED` requires an explicit proof/evidence note. `VERIFIED` records a finite
bound. `REFUTED` requires a concrete counterexample.  This prevents experimental
verification from silently becoming a theorem in later research notes.

## Initial structural-law miner

`mine_selector_laws` searches simple equality/subset/disjointness relations among
a supplied selector vocabulary under a class hypothesis.  It currently uses the
finite reference theorem laboratory and a deliberately small complexity metric.

As an E6 calibration it rediscovers, without special cases,

- on modified sequences: `First = AscTop` and
  `Repeat = RunStart - {1}`;
- on revised sequences: `First = AscBottom`.

This miner is intentionally primitive.  E7 will make conjecture generation,
minimal hypotheses, parameter recognition, and law-strength comparison first-
class research operations.
