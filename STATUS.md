# AC-Engine campaign status

## Current milestone: E11c.2a1 alternating construction verified through degree 11

### Latest E11c update (2026-10-07)

The current candidate is the frozen alternating M/O repair algorithm. An exhaustive
degree-11 run checked all **1,248,595** modified `2122`-avoiders. Every source terminated
in the modified `2212`-avoiding class and produced a distinct image: **0** cycles, stalls,
unpaired defects, target failures, collisions, or missing targets. This is finite
verification, not a proof. E11c.2a2 will classify alternating repair states to support
a termination and target-preservation argument.

The earlier one-pass `GapSwapRepair(2,1)` rule remains refuted at degree 11. The witness
`12321443542` demonstrates why the old no-heavy-crossing argument does not close. It is
not a counterexample to the alternating construction.

### Historical E11c.1b1 result

The b1 campaign tested the proposed claim that the first canonical repair after the
completed gap phase is heavy-crossing-free. It found a minimum-length degree-11
counterexample. The source `12321443542` is a modified `2122`-avoider; its gap pivots are
`[2,4]`, and the terminal state `12143544232` has first defect pair `(f,q,v)=(5,10,3)`
with `A=[4]`, `B=[3,5,4,4,2]`. Value `4` has multiplicity three across both blocks.

The same source refutes the old one-pass `GapSwapRepair(2,1)` class-map claim: the completed
output `12134425432` is modified but contains `2212`. Exhaustive targeted search found no
heavy first repairs through degree 10, then found **2 among 6,043** at degree 11 after
checking **1,248,595** sources and **130,501** gap steps. The previous degree-10
verification remains correct as a finite statement; the universal map claim is false.

The E11c.1b0 anchored gap-phase proof remains valid. It does not imply repair
target-preservation. The GUI's current transformation trace still demonstrates the old
one-pass model; the alternating trace has not yet been connected to the screen.

E10 produced a deterministic finite bijection candidate through degree 10.  E11 is now
split into smaller proof campaigns rather than continuing transformation synthesis.

### E11a — extreme-orientation calculus

- Added `ExtremeOrientation` (`LEFT`, `RIGHT`, `BOTH`, `MIXED`) for lower-valued
  occupancy of repeated-value fibre gaps.
- Proved/reduced semantically:
  - `Av(2122)` iff every fibre is RIGHT/BOTH;
  - `Av(2212)` iff every fibre is LEFT/BOTH.
- Added threshold projections and the maximum extreme normal form
  `v^(m-1) B v` versus `v B v^(m-1)`.
- Added proof-oriented tracing of `ExtremeGapSwap(2,1)`.
- Verified the still-open extreme-orientation closure lemma on all **50,717**
  extreme-oriented Cayley words through degree 7, covering **11,584** nontrivial
  extreme-gap swaps with **0 failures**.
- On actual modified `2122`-avoiders through degree 9, recorded **1,703** gap swaps;
  pivot values are strictly increasing and all lower-projection/orientation invariants pass.

### E11b — local defect-rotation lemma

- Added stable-ID `DefectRotationCertificate`.
- Isolated/proved by local boundary analysis that canonical `AB -> BA` repair exchanges
  ascent-top identity exactly `q -> f`.
- Characterized first-occurrence changes exactly: a value changes first-occurrence identity
  iff it occurs in both swapped blocks and has no occurrence before the swap.  Every such
  value is strictly larger than the pivot.
- Added proof-oriented value potential

  `sum((n+1) ** (height-value) for false-first defects)`.

  Under the local admissibility invariant, this gives a direct well-founded termination
  argument.
- Added `DefectAdmissibility`: perfect by-value pairing, unique pair values, first/second
  occurrence pairs, and canonical lower-predecessor blocks.
- Full degree-10 benchmark: **437 defective intermediate states / 437 repair steps**,
  **0 admissibility failures**, all **437** pairs are rank `(1,2)`, all local certificates
  pass, and the value potential decreases on every step.
- Only **2/437** steps change any first-occurrence identity other than the pivot repair;
  in both cases exactly one higher value is transferred, matching the local theorem.

### Important E11b falsification

Left orientation plus defect admissibility is not by itself enough to preserve `2212`
avoidance under canonical repair.  The word `13243312` is a finite counterexample:
canonical repair gives `12433132`, which is no longer left-oriented.  Therefore the
remaining proof must use provenance inherited from the preceding gap-swap phase.


### E11c progress — heavy-crossing obstruction

- Defined a heavy-crossing value for a repair as a multiplicity-`>=3` fibre meeting both
  swapped blocks `A` and `B`.
- On the full degree-10 reachable benchmark: **0/437** repair steps have a heavy crossing
  and **0/437** change the fibre-orientation profile.
- Extracted a length-independent local proof: a canonical repair of a left-oriented word
  preserves left orientation whenever no heavy value crosses both blocks.  This proves
  target-pattern preservation from one clean local condition.
- Found a guardrail showing the clean condition is not automatically invariant under arbitrary
  repair: `14323312 -> 13243312`, after which the next repair has heavy value `3` crossing
  both blocks.  Therefore the remaining theorem must genuinely use reachability/provenance
  from `ExtremeGapSwap`, not just local defect admissibility.

### Tests and reproducibility

- New E11 proof-extraction test module: **9/9 passing**.
- `experiments/e11a_orientation.py` / `.out`.
- `experiments/e11b_defect_local.py` / `.out`.
- `experiments/e11c_reachable_invariant.py` / `.out`.
- Full proof decomposition: `docs/PROOF_EXTRACTION.md`.

## Next gates

### E11c.2a2 — alternating-state taxonomy
Classify what one M-repair can create in the orientation system and what one O-repair can
create in the modified-defect system. Then seek a two-component termination measure and
prove target preservation for reachable alternating states.

### E11d — symbolic inverse
After the alternating termination and preservation proof, establish the inverse behavior
of the parameter-swapped construction.

## Parallel GUI-1 campaign — design prototype complete

GUI-1 was run alongside E11c. Its dashboard distinguishes the refuted one-pass rule from
the alternating candidate verified through degree 11, and keeps the general proof status
open.

- Added a thin engine-backed research view-model layer in `ac.gui.viewmodel`.
- Added arbitrary word inspection with position explanations, stable IDs, defect sets,
  fibre gaps, and 2122/2212 orientation.
- Added engine-recorded `ExtremeGapSwap` + canonical repair traces with backward/forward
  UI stepping, block `A/B`, potential, certificate data, new defects, and heavy crossings.
- Added the provenance guardrail `14323312 -> 13243312` to demonstrate why E11c is still open.
- Added a curated bounded Conjecture Lab.  Finite success can return only
  `VERIFIED THROUGH n=k`; it cannot return `PROVED`.
- Added a proof-status dashboard separating proved local lemmas, the one-pass
  counterexample, alternating degree-11 finite evidence, and open proof obligations.
- Added a zero-dependency local HTTP prototype: `python -m ac.gui.server`.
- Added a standalone clickable review artifact generated from engine view models.
- GUI-focused regression: 6/6 tests passing.  E9+E11+GUI focused regression: 21/21 passing.
  The complete repository test suite exceeds the current execution-window timeout, so this
  GUI pass does not claim a fresh full-suite completion.

## GUI-2 — pedagogical and visual foundation (in progress)

The first implementation slice changes the launch experience from a research dashboard
to a guided introduction, while keeping the research engine one click away. The Learn /
Workbench navigation split and current-campaign status correction are now implemented:

- Added a “Learn the basics” landing view with a four-part learning path: ordinary ascent
  sequences, ascent tops/bottoms, modified and revised families, and a live try-it step.
- Added accessible hover/focus definitions and concrete, engine-checked examples, with
  direct links from lessons into the sequence inspector.
- Extended the Python view model to classify ordinary, modified, revised, and Cayley
  words in one response. The lesson does not reimplement those definitions in JavaScript.
- Restyled the app with a consistent palette, responsive lesson cards, keyboard focus
  states, reduced-motion support, and proof-status language that distinguishes the latest
  E11c target from finite degree-11 evidence.

Next GUI-2 gates: inspect the live interface at desktop and mobile widths; review the
beginner text with someone unfamiliar with the project; test keyboard navigation and
contrast; connect the alternating trace; then update the standalone review artifact and
build/install packages. E11c proof work continues independently.

## GUI-3.1 — Experiment foundation and composer (first implementation complete)

The first generic research experiment model is implemented in `ac.gui.experiments`:

- A specification records question (`count` or `compare`), one or two sequence families,
  one or more avoid/contain Cayley-pattern rules, degree range, optional degree shifts,
  optional structural filter, and optional statistic refinement.
- The composer gives a default modified `2122` versus modified `2212` comparison, plus a
  revised `3121` at degree `n+1` versus ordinary `221` at degree `n` preset. Pattern
  validation calls `ClassicalPattern` through the Python API.
- Results lead with match/divergence and a compact table; scan counts, runtime, and the
  exact normalized specification are under a disclosure. A finite result never claims
  proof.
- Safe generation limits are ordinary/modified through degree 11 and revised through
  degree 7. Generic pattern-occurrence searches have additional arity-based limits;
  the common repeated-sandwich patterns use the engine's fibre structure. The default
  modified comparison was measured through all degrees 1–11 in **18.6 seconds** in
  this environment and returned 1,248,595 on both sides at n=11.
- The existing one-pass transformation check remains available in a disclosure, clearly
  labelled as the older experiment.

The existing hat map and modified-family enumerator received an allocation-light
implementation to meet the GUI run-time target. It is checked against the original
ordered prefix-lift definition through degree 6. GUI-3.1's new experiment checks are
8/8 under direct invocation; the regular `pytest` runner is unavailable in this
execution environment. Desktop/browser visual inspection remains a separate gate.

## GUI-3.2 — Discovery workflow (implementation complete; visual review open)

Experiment results now lead to three live, engine-backed follow-ups:

- Each result row can open a paged object browser for either class (or the single
  counted class). It applies the exact family, pattern, degree shift, and optional
  structural condition from the experiment, and shows the member's rank plus ascent,
  maximum, distinct-value, multiplicity, and first-occurrence data.
- A count divergence at a shared family and degree can search the common generated
  universe for exact left-only and right-only membership witnesses. The interface
  names the finite search and reports how many words it checked. It fetches each
  witness's engine inspection and presents side-by-side sequence roles, family flags,
  defect count, fibre orientation, and lower material in fibre gaps. Cross-family or
  degree-shifted comparisons do not claim that their words are directly comparable.
- Every comparison result has quick refinement actions for ascent count, ascent-run
  count, run-length profile, run-start positions, maximum, multiplicity profile, and first/last-occurrence
  positions. Each reruns the same exact specification with that statistic. The result
  can open a bucket-by-bucket table showing counts on both sides and their difference
  for any requested degree.
- The object browser can further filter the selected experiment class by an exact
  statistic value: ascent count, run count, maximum, distinct values, multiplicity
  partition, first/last-occurrence positions, run lengths, or run-start positions. It can also filter
  by containing or avoiding an additional Cayley pattern. Pagination ranks are local to
  the filtered result, and the UI reports scanned universe size without inventing a
  filtered total.
- Selecting any browser member or mismatch witness opens the existing engine-backed
  sequence inspector.

The object browser is demand-driven; initial experiment results still return compact
counts and distributions. First-divergence witness extraction is an exact finite
membership search, not a proof or a proposed bijection. Transformation matched/unmatched
filters belong to the following transformation experiment stage. New tests cover the
browser, exact witnesses, exact filters, and the
non-comparable degree-shift guard; all 20 experiment tests passed
under direct invocation. The standard `pytest` runner is not
installed in this environment. Python compilation, JavaScript syntax validation, and
`git diff --check` pass. The live server could not be started because this environment
denies local socket binding, so browser-level visual review remains open.

## GUI-3.3 — Transformation research (parameterized-map slice)

The workbench now has a generic, bounded class-wide transformation audit for the
engine maps `reverse`, `complement`, `hat`, `inverse_hat`, `prefix_lift`,
`inverse_prefix_lift`, position insertion, and single-position deletion:

- Choose a source family and pattern restriction, a target family and target pattern
  restriction, a transformation, a degree range through 10, and an optional statistic.
- For every source member, the audit reports Cayley-output validity, target-class
  membership, distinct images and collisions, target coverage and missing targets,
  inverse recovery where a paired map is known, and statistic preservation.
- The prefix lift and its partial inverse take an explicit 1-based pivot position,
  included in the normalized specification and reused in inverse checks. Words that
  are too short for the selected pivot or fail the inverse's first-occurrence
  precondition are retained as exact failure witnesses.
- Position insertion takes a 0-based cut and existing value, and compares source
  degree `n` against target degree `n+1`. Deleting a selected 1-based position uses
  the engine's ambient restriction, retains empty value levels, and compares `n`
  against `n−1`. The audit pairs these maps for a per-word inverse check; deletion
  recovery fails when the removed value does not match the specified inserted value.
- Each failed check retains a concrete source/output witness. The interface distinguishes
  finite audit results from theorem status; no result can claim `PROVED`.
- The default example is `hat` from ordinary to modified ascent sequences. Through
  degree 6 it checks target membership, injectivity, coverage, inverse recovery, and
  ascent preservation for every enumerated member.

The map set remains a selected, engine-backed vocabulary: simultaneous multi-position
insertion, arbitrary selected-position restrictions, compression/standardization, and
user-defined transformation expressions remain for later work. Fourteen transformation-
experiment tests pass under direct invocation. The `pytest` runner and live browser
visual review remain unavailable in this environment.
