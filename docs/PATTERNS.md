# AC pattern semantics (E4)

AC deliberately separates **ambient restriction** from **pattern compression**.

For a source word `x` and increasing selected positions `J`:

1. `restrict_positions(x, J)` keeps the selected entries with their original
   ambient value levels and stable occurrence IDs.
2. `compress_levels(...)` deletes empty value levels while preserving value
   order.  This is the ordinary Cayley-pattern view.
3. `standardize(...)` is different again: Stanley standardization resolves
   equal letters from left to right and returns a permutation.

Thus two restrictions can have the same classical pattern while retaining
recoverable ambient-gap data.  This is essential for lift transport, because a
prefix lift is not determined by the compressed pattern alone.

## Classical patterns

`Pattern("2122")` compiles to an exact pairwise value-relation constraint AST.
Occurrences are increasing tuples of source positions satisfying those
constraints.  Each reported occurrence stores both its ambient restriction and
its compressed pattern view.

`Avoid("111")` is now a general symbolic `WordPredicate`; it has been checked
against the optimized multiplicity condition `AvoidConstant(3)` on all Cayley
words through length 6.

## Generalized structural patterns

`ConstraintPattern` allows a pattern to specify only selected relations.
Current atoms include:

- `ValueEq(i,j)`
- `ValueLt(i,j)`
- `PositionAdjacent(i,j)`
- `ValueAdjacent(i,j)`

This is the base on which vincular, bivincular, mesh, and AC-specific structural
patterns can be built without a separate occurrence engine.

## Symmetry transport

Classical patterns transport exactly through the global reversal/complement
symmetry algebra:

- reversal reverses the pattern word;
- complement complements its value order;
- compositions are handled symbolically.

AC explicitly refuses to claim compressed-pattern transport through a prefix
lift, because ambient gap information is required.  This is a deliberate
safety property, not a missing convenience method.
