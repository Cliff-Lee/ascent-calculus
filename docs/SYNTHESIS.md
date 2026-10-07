# E8 — bounded transformation synthesis

E8 turns the AC transformation algebra into a finite program-search laboratory.
The purpose is not to enumerate arbitrary Python functions.  Search is restricted to
mathematically meaningful AC transformations, normalized before evaluation, and tested
against explicit source and target classes.

## Search objects

A candidate is a symbolic `Transformation`.  Atomic transforms carry a search cost and
coarse signature; compositions have additive cost.  `enumerate_transform_programs`
performs a bounded breadth-first search and deduplicates programs after AC normalization.
The Klein-four relations for reversal/complement are therefore removed before execution.

A seed may be supplied.  For the first benchmark we use `Reverse()` because E7 proves
that reversal transports the classical pattern `2122` to `2212` exactly; synthesis then
searches only for a structural repair of the reversed modified theory.

## Candidate semantics

`evaluate_bijection_candidate` checks a candidate degree by degree.  A first failure is
classified as one of:

- `UNDEFINED`: the partial transform is not defined on a source object;
- `OUTSIDE_TARGET`: an image leaves the requested target class;
- `COLLISION`: two source objects have the same image;
- `NOT_SURJECTIVE`: the image misses a target object.

`analyze_finite_map` retains the complete finite defect at one degree: all undefined
sources, all outside-target images, all collision fibres, and all missing targets.  This is
important for discovery because a near-bijection is often more informative than a Boolean
pass/fail result.

`diagnose_candidate` also records the modified-structure defect

```
| First(output) Δ Asctop(output) |
```

and can separately score a target pattern condition.  Thus pattern transport and structural
repair can be diagnosed independently.

## Generic event-driven transforms

E8 exposes the classical hat map and inverse hat map as symbolic transformations and adds
`SweepLift(selector, inverse=False, direction=...)`.  The selector is snapshotted on the
source word and prefix lifts are then applied in the chosen order.  This is the generic
search primitive behind hat-like constructions; the search grammar does not need a named
bijection for every event set.

## 2122 / 2212 benchmark

Let

```
C = Modified & Avoid(2122)
D = Modified & Avoid(2212).
```

A reversal-seeded grammar containing complement, hat/inverse-hat, compression, and lift
sweeps over the main structural selectors produced **3192 normalized candidate programs**
within the first E8 budget.  None is a bijection through degree 6.  This negative result is
useful: the simple global/sweep grammar does not repair the modified structural condition.

Reversal itself has a very sharp diagnosis at `n=6`:

- it maps every source word to a `2212`-avoider;
- it is injective;
- only about 12% of its images are modified;
- the failure is therefore almost purely structural, exactly as predicted by E5/E7.

## E7-guided fibre-gap repair

E7 identifies `2122` and `2212` as the repeated-sandwich patterns with gap capacities
`(1,2)` and `(2,1)`.  E8 therefore adds an explicitly experimental discovery primitive
`FibreGapPack(a,b,side=...)` which packs internal copies of an offending repeated value.
It is deliberately kept in `ac.discovery.repairs`: it is a candidate schema, not a theorem.

For the orientation relevant to the benchmark,

```
FibreGapPack(2,1,side="right")
```

is an exact bijection from `C_n` to `D_n` through `n=6`.  It sends the unique degree-6
class difference

```
122132  ->  121322.
```

At `n=7` it still sends **every** source object into the target class and keeps the modified
condition exactly, but it first fails by two collision fibres (and therefore two missing
targets).  One collision is

```
1223142  ->  1231422
1232142  ->  1231422.
```

The lost information is the relative location of non-fibre entries that are erased by naive
packing.  This is a strong design signal for the next synthesis language: a successful
repair needs an information-preserving local move/rotation rather than a many-to-one pack.

## Interpretation

E8 does not claim a new bijection for `2122 ~ 2212`.  It establishes the machinery needed
to search for one and produces a useful near-bijection with a minimal, explicit obstruction.
The next natural synthesis extension is to add reversible local fibre-gap moves (block
rotations/splices controlled by gap witnesses) or to attack the same equivalence through
its generating-tree structure.
