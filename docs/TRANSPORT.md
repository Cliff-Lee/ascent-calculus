# AC property transport semantics

E5 separates three different questions that are easy to conflate in combinatorial work.

1. **Apply a transformation to an object**: `T.apply(x)`.
2. **Transport old occurrences/features by provenance**: `transport_positions(T, x, S)`.
3. **Transport a property/class through a transformation**: `transport_predicate(P, T)`.

For a deterministic transformation `T` and target predicate `P`, the pullback is

\[
T^*P(x) \iff T(x)\text{ is defined and }P(T(x)).
\]

For a transformation with a known functional inverse, the pushforward is

\[
T_*P(y) \iff T^{-1}(y)\text{ is defined and }P(T^{-1}(y)).
\]

AC represents these by `pullback(T, P)` and `pushforward(T, P)`.  The higher-level
`transport_predicate(P, T)` simplifies the result when an exact symbolic law is known,
and otherwise retains the inverse-based semantics rather than guessing.

## Example: reversal of the modified theory

Modified ascent sequences satisfy

\[
\mathrm{First}=\{1\}\cup\mathrm{RawAscTop}.
\]

Under reversal, first occurrences become last occurrences and raw ascent tops become
raw descent tops, while the left boundary becomes the right boundary.  Hence AC derives

\[
R_*(\mathsf M):\qquad
\mathrm{Last}=\{n\}\cup\mathrm{RawDescTop}.
\]

Thus reversal sends

\[
\mathsf M\cap\operatorname{Av}(2122)
\]

to

\[
R_*(\mathsf M)\cap\operatorname{Av}(2212),
\]

not directly to `Modified & Avoid(2212)`.  This isolates the structural mismatch that
any further bijection must repair.

## Ambient restriction and a single prefix lift

Let `L_i` be the prefix lift with threshold `t=x_i`, and let
`J={j_1<...<j_k}` be selected source positions.  If

\[
c=|\{j\in J:j<i\}|,
\]

then the selected point values obey the exact law

\[
(L_i x)|_J
=
\Lambda_{c,t}(x|_J),
\]

where `Lambda` raises by one exactly the first `c` selected entries whose ambient value
is at least `t`.

The **ambient value-chain height is global context**: an unselected maximum to the left
of the pivot can create a new top level.  Therefore AC transports the output ambient
height from the global lift rather than pretending it can always be inferred from the
selected subsequence.  This is why compressed Cayley patterns alone are insufficient
for lift transport.

## Fibre/capacity transport

For pivot `i` with threshold `t=x_i`, split each fibre `P_v` into

\[
P_v^- = P_v\cap[1,i-1],\qquad P_v^+=P_v\cap[i,n].
\]

The output fibre sizes are

\[
\mu'_v=
\begin{cases}
|P_v^-|+|P_v^+|,&v<t,\\
|P_t^+|,&v=t,\\
|P_v^+|+|P_{v-1}^-|,&t<v\le m,\\
|P_m^-|,&v=m+1.
\end{cases}
\]

Consequently, conditional on the source avoiding `1^r`, the lift preserves avoidance
exactly when every new neighbouring-fibre merge fits capacity:

\[
|P_{v-1}^-|+|P_v^+|\le r-1\qquad(t<v\le m).
\]

`LiftCapacity(i,r)` is the executable source-side predicate for this condition.  E5
checks the theorem schema

\[
\operatorname{Av}(1^r)\models
\bigl(\mathrm{LiftCapacity}(i,r)\leftrightarrow L_i^*\operatorname{Av}(1^r)\bigr)
\]

on finite universes.

## Exactness policy

Property transport is deliberately conservative.  If AC cannot justify an exact
symbolic simplification, it either keeps the exact inverse-based predicate (when a
functional inverse is known) or raises.  It never silently treats empirical pattern
transport as a theorem.
