# AC typed structural semantics (E0.2)

## Four index sorts

AC distinguishes four coordinate types:

- `Position(i)`, `1 <= i <= n`
- `PositionCut(c)`, `0 <= c <= n`
- `ValueLevel(v)`, `1 <= v <= m`
- `ValueCut(c)`, `0 <= c <= m`

A selector carries one of these sorts. Boolean selector algebra (`|`, `&`, `-`, `~`)
is only defined between selectors of the same sort.

## Scopes

E0.2 supports contiguous positional scopes only. `WholeScope` is the default and
`IntervalScope(a,b)` gives the induced contiguous subword. This deliberately avoids
ambiguous notions of adjacency on arbitrary subsets. Arbitrary subsequences will enter
through an explicit restriction transformation in the pattern phase.

Occurrence selectors (`First`, `Last`, `Occ(r)`) are relative to the scope. Local edge
selectors use adjacency inside the contiguous scoped subword. Literature ascent-top and
ascent-bottom conventions adjoin the first position of the scope.

## Snapshot semantics

Selector-controlled editing defaults to **snapshot semantics**:

1. evaluate the selector once on the source word;
2. store the selected source positions/cuts;
3. perform all requested edits relative to that source selection;
4. do not re-evaluate the selector during the edit.

`insert_at_selected_cuts` is the first executable example. `Before(RunStart())` is
resolved on the original word, then all insertions happen simultaneously.

The language reserves two additional modes:

- `SEQUENTIAL`: evaluate once, visit the snapshotted targets in order, re-anchoring by
  stable source occurrence IDs after earlier edits;
- `DYNAMIC`: re-evaluate after every edit. This may loop and will only be available
  through explicit iteration/fixed-point constructs.

## Persistent occurrence identity

`ChainWord` now carries stable `position_ids` separate from current numerical indices.
Initial positions receive IDs `1..n`; newly created occurrences receive decreasing
negative IDs. Reversal, complement, lifts, and hat conversion preserve occurrence IDs.
Position insertion creates fresh IDs.

This lets AC distinguish:

- *where an old occurrence moved* (transport), from
- *which current positions satisfy a structural selector* (recomputation).

Value-class provenance is intentionally not represented by a single stable ID yet:
prefix lifts can split and merge value classes, so value provenance must ultimately be a
relation rather than a scalar identifier.
