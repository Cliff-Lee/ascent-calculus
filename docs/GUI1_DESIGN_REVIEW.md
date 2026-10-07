# GUI-1 Design Review

## Workflow

The prototype uses four tabs in the order a researcher normally works:

1. **Sequence inspector** — understand one word.
2. **Transformation trace** — understand one computation and its provenance.
3. **Conjecture lab** — test a finite claim over a class.
4. **Proof status** — distinguish established lemmas, finite evidence, open obligations,
   and falsified generalizations.

The global header always shows the current overall theorem as **OPEN**, even when a
particular bounded test succeeds.

## Successful walkthrough

Use source `12321432`.

`ExtremeGapSwap(2,1)` gives

`12321432 -> 12143232`,

which is target-pattern clean but not modified.  The trace then records one canonical
repair

`12143232 -> 12132432`.

The repair screen exposes the paired defect, blocks `A,B`, stable IDs, proof-oriented
potential decrease, no heavy crossing, and the exact ascent-top identity exchange.

This demonstrates the intended distinction between:

- a transformation that solves the pattern orientation;
- a structural defect introduced by that transformation;
- a local repair of the modified condition.

## Open/failure walkthrough

Load `14323312` in the trace tab.  The first canonical move is

`14323312 -> 13243312`.

It passes the local repair certificate.  However the following generic repair can contain
heavy value `3` across both repair blocks.  This is presented as a **provenance guardrail**,
not as a failure of the reachable E10 computation.  It shows why E11c must prove an
invariant for states actually produced by `ExtremeGapSwap`.

In the Conjecture Lab, choose raw `ExtremeGapSwap(2,1)` from `M(2122)` to `M(2212)` through
`n=8`.  The workbench returns **COUNTEREXAMPLE FOUND** at degree 8 because a raw image is
outside the modified target class.  Choosing `GapSwapRepair(2,1)` instead returns
**VERIFIED THROUGH n=8**.

## Current research cards

The status dashboard deliberately mixes four epistemic states:

- **PROVED:** `Av(2122)` = right-oriented fibres; `Av(2212)` = left-oriented fibres;
  local canonical repair exchanges ascent-top identity `q -> f`.
- **VERIFIED THROUGH n=10:** the complete degree-10 finite bijection calculation for
  `GapSwapRepair(2,1)`.
- **OPEN:** reachable no-heavy-crossing; symbolic inverse proof; unfinished n=11 run.
- **COUNTEREXAMPLE FOUND:** local admissibility without gap-swap provenance is insufficient
  for a general repeated-repair theorem.

## Design gate assessment

1. **Interface contract — PASS.** Fixed labels are defined; bounded computation cannot
   emit `PROVED`.
2. **Sequence inspector — PASS.** Position-level reasons and fibre-gap orientation are
   engine-generated.
3. **Transformation trace — PASS.** Stable occurrence IDs, defect pairs, block rotation,
   potential, new defects, and heavy crossings are visible.  The guardrail example is
   included.
4. **Conjecture lab — PASS for prototype scope.** Curated classes/transforms support
   bounded checks with counts and witnesses.  The incomplete n=11 result is displayed only
   as open status metadata, not as a completed check.
5. **Clickable prototype — PASS.** A standalone engine-generated review file and a live
   local-server version are supplied.  Browser code renders view models and does not own
   the combinatorial rules.

## Implementation campaign after GUI-1

GUI-2 should turn the prototype into the maintained workbench.  Priorities:

- asynchronous bounded runs with cancellation/progress;
- persistent experiment records and export/import;
- transformation-expression builder over the AC AST;
- richer provenance overlays (fibres/gaps/blocks as linked objects);
- side-by-side comparison of two words/classes;
- counterexample queue and annotation;
- only after the research workflow settles, an optional teaching presentation mode.
