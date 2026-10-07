# AC-E7 discovery layer

E7 adds structure-aware conjecture mining on top of the E6 finite logic and theorem lab.
The aim is not just to test isolated identities, but to discover useful normal forms,
minimal hypotheses, parameterized laws, and structural invariants that distinguish classes.

## 1. Fibre-gap geometry

For a value `v` with occurrences

\[
p_1<p_2<\cdots<p_m,
\]

AC records the open gaps

\[
(p_r,p_{r+1}),\qquad 1\le r<m.
\]

A gap carries two capacities:

\[
L=r,\qquad R=m-r,
\]

and AC records whether entries in that gap are lower than `v`, equal to `v`, or higher
than `v`.

This gives a structural normal form for the repeated-letter family

\[
2^a1\,2^b.
\]

### Repeated-sandwich theorem

A chain word contains the classical pattern `2^a 1 2^b` if and only if there is a value
`v` and a gap between its `r`-th and `(r+1)`-st occurrences such that

\[
r\ge a,\qquad m-r\ge b,
\]

and the gap contains an entry smaller than `v`.

**Proof.** If such a gap exists, choose any `a` occurrences of `v` among the `r` copies to
the left, the lower-valued entry in the gap, and any `b` occurrences of `v` among the
`m-r` copies to the right. Their compressed pattern is `2^a 1 2^b`.
Conversely, an occurrence of `2^a 1 2^b` uses one lower-valued entry lying between two
consecutive occurrences of the repeated value in the full fibre; the gap containing it has
at least `a` copies to its left and at least `b` to its right.  QED.

Consequences:

- `2122` is the case `(a,b)=(1,2)`;
- `2212` is `(a,b)=(2,1)`;
- positional reversal swaps the left and right capacities, hence swaps the two conditions.

This gives AC a much sharper description of the residual `2122/2212` problem: reversal
handles the repeated-letter pattern exactly, while the modified-sequence structural theory
is what must be repaired afterward.

AC also records fibre-span geometry (`disjoint`, `nested`, `crossing`) as a coarser invariant.

## 2. Minimal-hypothesis mining

`mine_minimal_hypotheses` searches bounded conjunctions of candidate restrictions that make
a proposed law true. Results are inclusion-minimal among the supplied candidates and are
ranked by empirical weakness: on the tested finite universe, a restriction admitting more
objects is preferred.

Calibration example:

\[
\operatorname{Occ}_2=\operatorname{Repeat}
\]

is false on unrestricted modified ascent sequences, with `111` as the smallest failure.
Among `Av(11)`, `Av(111)`, and `Av(1111)`, E7 correctly identifies `Av(111)` as the weakest
supplied repair through the tested range.

This is intended as a conjecture-generation tool, not as proof of logical minimality beyond
the candidate family and finite range.

## 3. Parameterized theorem schemas

`verify_parameterized_schema` keeps a family of finite verifications together instead of
producing unrelated observations for each parameter.

The first calibration schema is

\[
\mathsf M\cap\operatorname{Av}(1^r)
\vdash
\operatorname{RunStart}\setminus\{1\}
=
\bigcup_{k=2}^{r-1}\operatorname{Occ}_k.
\]

This is in fact a derived theorem schema:

1. Modified gives `RunStart-{1} = Repeat`.
2. `Av(1^r)` means every fibre has multiplicity at most `r-1`.
3. Therefore every repeat has occurrence rank in `2,...,r-1`, and every such occurrence is
   a repeat.

The engine verifies the schema instance-by-instance and retains the parameterized statement
as one research object.

## 4. Selector-expression synthesis and semantic normal forms

E7 can generate small selector expressions using set difference/intersection/union and then
group expressions that are extensionally equal on a chosen theory.

On modified ascent sequences it independently recovers semantic classes containing

\[
\operatorname{First}=\operatorname{AscTop}
\]

and

\[
\operatorname{Repeat}=\operatorname{RunStart}\setminus\{1\}.
\]

This avoids reporting dozens of redundant pairwise equalities: a semantic equivalence class
has one simplest representative and a collection of alternative structural descriptions.

## 5. Discriminating invariants

`rank_discriminating_statistics` shares class-membership computation across all candidate
statistics and ranks them by the first degree at which their distributions differ.

For

\[
\widehat{\mathcal A}(2122)
\quad\text{and}\quad
\widehat{\mathcal A}(2212),
\]

E7 finds experimentally:

- lower-gap profiles differ already at `n=6`;
- first- and last-occurrence position profiles differ at `n=6`;
- fibre-span profiles first differ at `n=7`;
- ascent count, height, and multiplicity partition remain equidistributed through `n=9`.

These are finite experimental statements except where separately proved.

## 6. Current role of E7

E7 is deliberately a discovery layer rather than an automated theorem prover. It produces
four kinds of output:

- compact structural normal forms;
- counterexamples and repaired hypotheses;
- parameterized candidate/theorem schemas;
- ranked invariants for separating or matching classes.

E8 can use these outputs to constrain bounded transformation synthesis, so that the search
space is guided by structure rather than blind enumeration.
