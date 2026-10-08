# AM-Next N3 — Bounded class-count conjecture discovery

N3 adds a reproducible search plan and a generated catalogue of single-pattern
classes in `ac/discovery/conjecture_search.py`. The search compares ordinary,
modified, and revised ascent sequences with classical Cayley patterns in either
**avoidance** or **containment** mode. It searches degree offsets from `−5` to
`+5`, subject to explicit degree and comparison budgets.

## Candidate grammar

The v1 plan chooses:

- one or more sequence families;
- pattern lengths 2, 3, and/or 4;
- `avoid`, `contain`, or both;
- an inclusive base-degree window;
- one or more degree offsets.

The search generates every Cayley pattern of each selected length. For lengths
2, 3, and 4 there are respectively 3, 13, and 75 patterns. With both modes
and all three families, the full grammar has 546 candidate classes. Rules are
single-pattern in N3; conjunctions and structural filters are later work.

For a source at degree `n` and target at `n+d`, the search computes full count
vectors. Equal vectors are reported as **count matches**. Candidate pairs that
match for an initial prefix and then diverge include the exact first differing
row as a counterexample. Results are ranked by matched degrees, tested range,
and smaller offset. Empty classes are omitted to avoid flooding the list with
vacuous `0 = 0` matches.

The search reuses one pattern-occurrence catalogue per family, degree, and
pattern length. This supports both avoidance counts and containment counts
(family total minus avoidance count), and makes class comparisons much cheaper
than enumerating each candidate class independently. A hard candidate-pair
budget of at most 1,000,000 bounds signature comparisons. If reached, the
result says `budget_exhausted`; its reported matches remain finite evidence,
but the candidate space was not fully searched.

Pattern-length limits are 11 for length 2, 9 for length 3, and 8 for length 4;
the ordinary/modified/revised generator limits also apply. A search plan may
request a larger range, but each match reports the degrees actually tested.
There is no silent extrapolation over unsupported degrees.

## Persistent use

`ConjectureSearchSpec` is stored as a versioned mathematical question in the
same durable job database as N2. Queue it under the registered handler id
`discover-pattern-classes`; the worker checkpoints after each selected pattern
length. For example:

```python
from ac.discovery.conjecture_search import ConjectureSearchSpec
from ac.discovery.jobs import ResearchJobStore, default_job_database

plan = ConjectureSearchSpec.build(
    families=("modified", "revised"),
    start=1, stop=5,
    pattern_lengths=(3,),
    modes=("avoid", "contain"),
    offsets=(0, 1, 2),
)
jobs = ResearchJobStore(default_job_database())
job = jobs.create_job(plan, handler="discover-pattern-classes", options={"keep": 100})
```

Run `ac-research-worker` or `python -m ac.discovery.worker` to process the
queue. The JSON result includes the search fingerprint, generated class
definitions, tested count vectors, first divergences, ranking, and whether the
comparison budget truncated the search.

## Reproduction check

With modified and revised families, length-3 avoidance classes, base degrees
1 through 5, and offset `+2`, the search independently selects modified
`111`-avoiders and revised `111`-avoiders among the generated count matches.
The reported vectors are `(1, 2, 4, 10, 29)` on both sides. A separate literal
tuple enumerator confirms each reported degree, including revised degree 7.
This is **count-conjecture rediscovery** only: it does not find the block map,
and it does not prove the two classes are equinumerous in general. N5-N7 add
transformation generation and counterexample-guided map search.

## Limits of this stage

N3 searches only generated single-pattern avoid/contain classes and compares
counts. It does not yet search arbitrary class predicates, statistics,
intersections of patterns, transformations, or block decompositions. Structural
features, broader typed class formulas, and map synthesis arrive in later
stages. Bounded success never implies a theorem.
