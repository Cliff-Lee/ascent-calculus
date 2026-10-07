# AC-Engine campaign status

## Current milestone: E11a–E11b complete; E11c provenance invariant — started

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

### E11c — provenance invariant
Prove the now-specific **reachable no-heavy-crossing invariant**: every selected canonical
repair arising from an actual `ExtremeGapSwap(2,1)` image has no multiplicity-`>=3` fibre
crossing both repair blocks.  Together with the completed repair-orientation lemma this
would prove preservation of `2212` avoidance.  In parallel, prove initial and iterative
defect admissibility.

### E11d — symbolic inverse
Once E11c is closed, prove that the parameter-swapped construction reverses the gap and
repair moves locally, yielding the two-sided inverse already verified through degree 10.

## Parallel GUI-1 campaign — design prototype complete

GUI-1 was run alongside E11c without changing the proof status of the candidate bijection.

- Added a thin engine-backed research view-model layer in `ac.gui.viewmodel`.
- Added arbitrary word inspection with position explanations, stable IDs, defect sets,
  fibre gaps, and 2122/2212 orientation.
- Added engine-recorded `ExtremeGapSwap` + canonical repair traces with backward/forward
  UI stepping, block `A/B`, potential, certificate data, new defects, and heavy crossings.
- Added the provenance guardrail `14323312 -> 13243312` to demonstrate why E11c is still open.
- Added a curated bounded Conjecture Lab.  Finite success can return only
  `VERIFIED THROUGH n=k`; it cannot return `PROVED`.
- Added a proof-status dashboard separating proved local lemmas, degree-10 finite evidence,
  open E11c/E11d obligations, the generic counterexample, and the incomplete degree-11 run.
- Added a zero-dependency local HTTP prototype: `python -m ac.gui.server`.
- Added a standalone clickable review artifact generated from engine view models.
- GUI-focused regression: 6/6 tests passing.  E9+E11+GUI focused regression: 21/21 passing.
  The complete repository test suite exceeds the current execution-window timeout, so this
  GUI pass does not claim a fresh full-suite completion.

Next GUI campaign is GUI-2 implementation hardening after design review; E11c proof work
continues independently.
