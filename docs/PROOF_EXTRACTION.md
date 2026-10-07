# E11 proof extraction

E11 is intentionally split into smaller proof campaigns.  E10 produced a finite
bijection candidate; E11 asks which parts can now be proved from local structure
and which genuinely remain open.

## E11a — extreme-orientation calculus

For a value `v` with occurrences

\[
p_1<\cdots<p_m,
\]

let

\[
G_v(x)=\{r:\text{some entry }<v\text{ occurs between }p_r\text{ and }p_{r+1}\}.
\]

Define four fibre states:

- **LEFT**: `G_v subset {1}`;
- **RIGHT**: `G_v subset {m-1}`;
- **BOTH**: both conditions hold (for example `G_v` is empty, or `m=2`);
- **MIXED**: neither condition holds.

The repeated-sandwich characterization gives immediately

\[
\operatorname{Av}(2122)
\iff
G_v(x)\subseteq\{m_v-1\}\quad\forall v,
\]

and

\[
\operatorname{Av}(2212)
\iff
G_v(x)\subseteq\{1\}\quad\forall v.
\]

Thus `2122`-avoidance is exactly **right orientation** of every fibre, and
`2212`-avoidance is exactly **left orientation** of every fibre.

This is not merely terminology: it turns the pattern problem into an orientation
problem on fibres.

### Threshold normal form

Delete all entries greater than `v`.  In the resulting threshold projection,
`v` is the maximum.  If the fibre of `v` is extreme-oriented, then all gaps
between consecutive `v`'s except possibly one extreme gap are empty.  Hence its
span has one of the two forms

\[
v^{m-1} Bv\qquad\text{(RIGHT)}
\]

or

\[
vBv^{m-1}\qquad\text{(LEFT)},
\]

where every entry of `B` is `<v`.  `B` may be empty.

This is implemented by `maximum_extreme_normal_form` and is an immediate
reformulation of the orientation definition after deleting higher values.

### What one extreme-gap swap proves immediately

Suppose the pivot fibre `v` is RIGHT-oriented.  Swapping its first and last
complete gaps changes its threshold-`v` normal form from

\[
v^{m-1}Bv\longmapsto vBv^{m-1}.
\]

So the pivot itself becomes LEFT-oriented.

Moreover the projection to values `<v` is unchanged: the moved lower block `B`
crosses only copies of `v` and material `>=v`.  Therefore every structural fact
involving only values `<v` is invariant under this swap.  In particular the
orientations of all smaller fibres are unchanged.

### Remaining E11a lemma

The missing global step is:

> **Extreme-orientation closure lemma.**  If every fibre of a word is LEFT,
> RIGHT, or BOTH, then swapping the first and last gaps of any fibre leaves every
> fibre LEFT, RIGHT, or BOTH.

This has not yet been recorded as a symbolic proof.  It has been exhaustively
checked on all `50,717` extreme-oriented Cayley words through degree 7, covering
`11,584` nontrivial extreme-gap swaps, with no failure.

If this lemma is proved, the pattern half of the bijection follows cleanly.
Starting from a RIGHT-oriented (`2122`-avoiding) word, process the least
`2212`-offending value.  Its swap makes that fibre LEFT; all smaller fibres stay
fixed; global extreme orientation is preserved.  Consequently pivot values
strictly increase and the process terminates after at most the number of value
levels.  At termination every fibre is LEFT-oriented, hence the output avoids
`2212`.

The actual `ExtremeGapSwap(2,1)` traces on modified sources through degree 9
contain `1,703` swaps and satisfy all of these proposed invariants, including
strictly increasing pivot values.

## E11b — local defect-rotation lemma

After the gap phase the only remaining issue is the modified condition

\[
\operatorname{First}=\operatorname{AscTop}.
\]

Suppose a defect pair has positions `f<q`, common value `v`, with `f` the first
occurrence and `q` the second.  Let `s` be immediately after the nearest lower
entry before `f`, and write

\[
A=x_s\cdots x_{f-1},\qquad B=x_f\cdots x_{q-1}=vC.
\]

In every E10 repair state,

\[
x_{s-1}<v,\qquad A_i>v\text{ for all }A_i\in A,
\qquad x_{q-1}<v.
\]

The canonical repair is

\[
AB\longmapsto BA.
\]

### Lemma 1 — ascent-top identity exchange

Track occurrence IDs rather than current position numbers.  The only ascent-top
identities changed by the block swap are

\[
q\longmapsto f.
\]

Indeed:

- `f` is moved immediately after `x_{s-1}<v`, so it becomes an ascent top;
- `q` is moved immediately after the last entry of `A`, which is `>v`, so it
  ceases to be an ascent top;
- the first entry of `A` was an ascent top before the move (preceded by
  `x_{s-1}<v`) and remains an ascent top afterward (preceded by the final entry
  of `C`, also `<v`);
- all other predecessor relations are internal to one of the two blocks and do
  not change.

Therefore, in stable-ID notation,

\[
AT'=(AT\setminus\{q\})\cup\{f\}.
\]

This is a direct local proof, not an empirical conjecture.

### Lemma 2 — exactly when first-occurrence identity changes

Swapping adjacent blocks `A B` to `B A` changes the first occurrence of a value
`w` iff

1. `w` occurs in both `A` and `B`, and
2. `w` has no occurrence before `s`.

No other relative order between two occurrences of the same value changes.
Because every entry of `A` is `>v`, every such `w` satisfies

\[
w>v.
\]

Hence the pivot defect at value `v` is repaired and any genuinely new defect can
occur only at a strictly larger value.

The engine records this with `DefectRotationCertificate`.

### A simpler well-founded potential

Let `h` be the ambient height and `n` the length.  Give a false-first defect of
value `v` weight

\[
(n+1)^{h-v}.
\]

Define

\[
P(x)=\sum_{f\in First\setminus AscTop}(n+1)^{h-x_f}.
\]

If a repair removes the pivot defect at `v`, leaves all lower-valued defects
unchanged, and creates defects only at values `>v`, then `P` strictly decreases.
The choice of base `n+1` ensures one removed weight dominates every possible
collection of higher-valued new defects.  Thus termination follows once the
repair-state admissibility invariant is proved.

On all `437` degree-10 repair steps this value potential decreases strictly.

### Admissible defect states

E11 isolates the next proof obligation as a named invariant.  A repair state is
**defect-admissible** when:

1. `First\\AscTop` and `AscTop\\First` pair bijectively by common value;
2. pair values are unique;
3. each pair is the first and second occurrence of that value;
4. the canonical lower-predecessor block exists and consists entirely of values
   strictly above the pivot.

Every one of the `437` defective intermediate states in the full degree-10
benchmark is admissible, and every local certificate succeeds.

The task for E11c is therefore not “guess why the rotation works”; it is to
prove that gap-swap images enter this admissible subclass and that the subclass
is stable under canonical repair.

## Important guardrail discovered in E11b

Target-pattern preservation is **not** a consequence of left orientation plus
admissibility alone.

For example

\[
13243312
\]

is `2212`-avoiding and defect-admissible.  Its canonical repair gives

\[
12433132,
\]

which is not `2212`-avoiding.

So a valid proof must use extra provenance inherited from the preceding
extreme-gap phase.  This rules out an attractive but false over-generalization
and sharply defines E11c.

## Current proof decomposition

The candidate bijection is now separated into the following statements.

1. **Pattern orientation theorem** — proved from the repeated-sandwich gap
   characterization.
2. **Pivot toggle and lower-projection invariance** — elementary local proof.
3. **Extreme-orientation closure** — open symbolic lemma; exhaustively verified.
4. **Gap-swap images are defect-admissible** — open invariant; verified through
   degree 10 in the benchmark.
5. **Local defect rotation boundary lemma** — elementary proof completed.
6. **Weighted termination** — follows from the local lemma once admissibility is
   shown invariant.
7. **Repair preserves target avoidance on reachable states** — open and must use
   gap-swap provenance.
8. **Parameter-swapped construction is the inverse** — open symbolic proof;
   finite verification through degree 10.

This decomposition replaces one large bijection conjecture by four small,
concrete remaining proof obligations (3, 4, 7, 8).

## E11c start — the heavy-crossing obstruction

The first E11c pass found a sharper reachable-state invariant.  For a canonical
repair with blocks `A,B`, call a value `w` **heavy-crossing** if

\[
|P_w|\ge3,
\qquad P_w\cap A\ne\varnothing,
\qquad P_w\cap B\ne\varnothing.
\]

Every one of the 437 reachable degree-10 repair steps has **no** heavy-crossing
value.  Moreover the complete fibre-orientation profile is unchanged by every
one of those 437 rotations.

### Repair orientation lemma

There is a direct reason that the absence of a heavy crossing is the right local
condition.

> **Lemma.**  Let `x` be LEFT-oriented (equivalently `2212`-avoiding), and let a
> canonical defect rotation have the local form
>
> \[
> L\mid A\mid B\mid q
> \longmapsto
> L\mid B\mid A\mid q,
> \]
>
> with pivot value `v`, where `L<v`, every entry of `A` is `>v`, `B` begins with
> the first `v`, and `q` is the second `v` with value `v`.  If no value of
> multiplicity at least three occurs in both `A` and `B`, then the rotated word
> is also LEFT-oriented.

**Proof sketch.**  Values of multiplicity at most two are automatically LEFT
oriented, since they have at most one fibre gap.  Fix a value `w` of multiplicity
at least three.

- If `w<v`, then `A` contains no `w` and in fact no entry `<w`; moving `A` cannot
  change the gap containing lower-than-`w` material.
- If `w=v`, the first and second `v` remain the first two occurrences and the
  lower material remains in their first gap.
- Let `w>v`.  By the no-heavy-crossing hypothesis, `w` occurs in at most one of
  `A,B`.
  - If it occurs in neither, the two blocks lie in the same `w`-gap (or outside
    the `w`-span), so swapping them cannot change the gap index of any lower
    material.
  - If it occurs only in `A`, the lower sentinel `L<v<w` forces there to be at
    most one earlier `w`; if there is a later `w`, the lower sentinel `q=v<w`
    forces `A` to contain exactly the first `w`.  After the swap, any lower
    material moved with `B` is therefore either outside the `w`-span or in the
    first `w`-gap.
  - If it occurs only in `B`, the same two sentinels give the dual restriction:
    any lower material moved with `A` is either outside the `w`-span or remains
    in the first `w`-gap.

Thus no lower-than-`w` entry can enter a second or later `w`-gap.  This holds for
all `w`, so LEFT orientation is preserved.  QED.

The engine retains exhaustive checks of this statement on the small universes,
but the argument above is now local and length-independent.

### Why this does not finish E11c

`no-heavy-crossing` is **not itself invariant under arbitrary canonical repair**.
For example

\[
14323312\longmapsto13243312.
\]

The first state has no heavy crossing at its selected repair, but in the second
state the next repair has the multiplicity-three value `3` crossing both blocks.
That second state is exactly the earlier generic counterexample from E11b.

Hence the remaining provenance theorem is now very precise:

> **Reachable no-heavy-crossing invariant.**  Starting from an actual
> `ExtremeGapSwap(2,1)` image of a modified `2122`-avoider, every canonical
> repair state has no heavy-crossing value at its selected repair.

This one invariant, together with the repair orientation lemma, would prove that
all canonical repair steps preserve `2212` avoidance.  Degree 10 gives 437/437
reachable steps with no heavy crossing and 437/437 unchanged orientation
profiles.
