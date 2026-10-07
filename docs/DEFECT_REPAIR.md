# E10 defect calculus and canonical local repair

E10 studies the only remaining failure of the E9 reversible fibre-gap transform on
`Modified & Avoid(2122) -> Modified & Avoid(2212)`.

## Defect sets

For a chain word `y`, write

\[
D_F(y)=\operatorname{First}(y)\setminus\operatorname{AscTop}(y),\qquad
D_T(y)=\operatorname{AscTop}(y)\setminus\operatorname{First}(y).
\]

The modified condition is exactly `D_F=D_T=empty`.

A **paired defect** is `(f,q;v)` with

- `f in D_F`,
- `q in D_T`,
- `f<q`, and
- `y_f=y_q=v`.

For every defective E9 `ExtremeGapSwap(2,1)` image through degree 10, all
modified defects pair in this way.

## Canonical local rotation

Given the leftmost paired defect `(f,q;v)`, let

\[
s=1+\max\{j<f:y_j<v\},
\]

with `s=1` if the set is empty.  Equivalently, `s` begins the maximal block
immediately preceding `f` whose values are all at least `v`.

Write

\[
A=y_s\cdots y_{f-1},\qquad B=y_f\cdots y_{q-1}.
\]

The canonical repair replaces `AB` by `BA`, i.e. left-rotates the interval
`[s,q-1]` by `f-s` entries.  All occurrence IDs travel with their entries.

This is implemented by `canonical_defect_rotation` and
`repair_modified_defects`.  The repair is iterated until `First=AscTop`.

## Discovery measure

E10 monitors

\[
M(y)=\left(
 |D_F|+|D_T|,
 \sum_{(f,q;v)}(q-f),
 \sum_{(f,q;v)} f
\right)
\]

lexicographically.  On every canonical repair step arising from the degree-10
benchmark, `M` decreases strictly.  This is currently **verified discovery
evidence**, not yet recorded as a general proof.

## Degree-10 benchmark

Let

\[
S_{2,1}=\operatorname{ExtremeGapSwap}(2,1)
\]

and `Repair` be the canonical iterative defect repair.  Define

\[
\Phi_{2,1}=\operatorname{Repair}\circ S_{2,1}.
\]

On all degree-10 modified `2122`-avoiders:

- source size: `183931`;
- `S_{2,1}` already sends every source to a `2212`-avoider;
- `434` intermediate images fail only the modified structural condition;
- defect sizes are `2` for `433` words and `4` for `1` word;
- canonical repair takes 0 steps for `183497`, 1 step for `431`, and 2 steps
  for `3` words;
- all `437` repair steps preserve `2212` avoidance and strictly decrease the
  discovery measure;
- the final images are all modified `2212`-avoiders;
- the final image set has size `183931`, equal to the target class.

Moreover the parameter-swapped transform

\[
\Phi_{1,2}
\]

is a two-sided inverse of `Phi_{2,1}` through degree 10 by exhaustive finite
verification.  The API exposes this as `GapSwapRepair(2,1).dual()` rather than
claiming a proved symbolic inverse.

## Current theorem candidate

The computational evidence suggests the following proof target.

> **Defect-bubble conjecture.**  On a modified `2^a 1 2^b`-avoider, swapping
> the extreme gaps of every offending `2^b 1 2^a` fibre produces a word in the
> target avoidance class whose `First/AscTop` defects pair by value.  Repeated
> canonical adjacent-block rotations terminate, preserve target avoidance, and
> yield a modified target word.  Swapping `a,b` gives the inverse map.

For `(a,b)=(2,1)` this is verified exhaustively through degree 10.  The next
mathematical task is to prove the pairing, descent, pattern preservation, and
dual-inverse lemmas from the fibre-gap geometry.
