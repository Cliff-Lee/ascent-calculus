# GUI-1 — AC Research Workbench Interface Contract

Status: **design prototype**, not a theorem prover UI.

The browser is a thin view layer.  It must not independently encode AC combinatorial
semantics.  Word analysis, transformations, defect detection, proof-oriented invariants,
and bounded searches are returned by the Python engine as view models.

## First research tasks

1. **Inspect a word.**  Enter or select a chain word and inspect its fibres, first/last
   occurrences, ascent roles, run boundaries, modified defects, fibre orientation, and
   current proof-oriented defect potential.
2. **Apply `ExtremeGapSwap`.**  Show the engine-recorded pivot sequence and before/after
   states.  Do not infer a theorem from a successful finite trace.
3. **Replay `CanonicalRepair`.**  Preserve stable occurrence IDs, display the defect pair,
   blocks `A,B`, the exact rotation, potential before/after, heavy-crossing values, and
   the local E11 certificate.
4. **Run a bounded check.**  Select source class, target class, transformation, and a
   maximum degree.  Display counts, completed degrees, failure kind, and a witness.

## Result labels

The following labels have fixed semantics and must be visually distinct.

- **PROVED** — a general statement supported by a recorded mathematical argument in the
  current proof layer.  This label must never be inferred from enumeration.
- **VERIFIED THROUGH n=k** — every case in the declared finite universe through degree
  `k` was checked successfully.  This is finite evidence only.
- **OPEN** — not established.  Use this both for proof obligations and for incomplete
  computational runs.
- **COUNTEREXAMPLE FOUND** — a general statement is false and the UI has a concrete
  witness.

A bounded search endpoint is forbidden from returning `PROVED`.

## Screen contract

### Sequence inspector

For each position the engine view model supplies: current index, stable occurrence ID,
value, occurrence rank, First/Last, AscTop/AscBottom, RunStart/RunEnd, defect membership,
and human-readable reasons.  Fibre rows supply the positions in each value class, gap
contents, lower positions, and orientation (`LEFT`, `RIGHT`, `BOTH`, `MIXED`).

**Gate:** clicking a position explains why each displayed structural role holds.

### Transformation trace

The trace is built from engine states.  Stable IDs travel with entries.  Each canonical
repair exposes `f,q,v`, interval `[s,q-1]`, blocks `A,B`, the value potential before/after,
heavy-crossing values, and the recorded local certificate.  Back/forward navigation is
purely presentational.

The research guardrail `14323312 -> 13243312` must be available as an example.  The UI
must explain that the next generic repair can have a heavy crossing, so reachability from
`ExtremeGapSwap` is part of the open theorem.

**Gate:** the displayed move is reconstructed solely from the engine trace; no browser
copy of the repair rule is used.

### Conjecture lab

The initial prototype exposes a curated class/transform registry.  A result table shows,
for every completed degree: source count, target count, unique images, outside-target
outputs, collisions, and finite bijection status.  The first failure carries a witness.

**Gate:** successful output is labelled `VERIFIED THROUGH n=k`; unfinished work is
`OPEN`; a witness is `COUNTEREXAMPLE FOUND`.

### Proof status

The dashboard currently separates:

- proved fibre-orientation characterizations;
- proved local ascent-top exchange for one canonical repair;
- the degree-10 finite bijection evidence;
- the open reachable no-heavy-crossing invariant;
- the generic-repair counterexample/provenance warning;
- the incomplete degree-11 stress run.

## Prototype/live split

`AC-GUI1-clickable-prototype.html` is a static review artifact containing engine-generated
sample view models.  It is intentionally sample-bound.

The live prototype is run from the repository with:

```bash
python -m ac.gui.server
```

and provides arbitrary word inspection/trace plus bounded checks through degree 10 via a
zero-dependency local HTTP server.

## Non-goals for GUI-1

- no teaching mode;
- no claim that `GapSwapRepair(2,1)` is proved in general;
- no browser-side reimplementation of selectors, pattern tests, or transformations;
- no arbitrary transformation-expression editor yet;
- no background/remote computation service.
