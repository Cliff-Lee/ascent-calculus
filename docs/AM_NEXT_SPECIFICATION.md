# AM-Next N1 — Formal finite-search specification

N1 introduces a stable, serializable statement of a mathematical experiment.
The implementation is in `ac/discovery/specification.py`, with the named
statistic registry in `ac/discovery/statistics.py`.

## Search object

`SearchSpec` records:

- a goal: `enumerate`, `count_equivalence`, `profile_equivalence`, or
  `bijection_search`;
- a source and optional target class;
- an inclusive base-degree range;
- source and target degree offsets;
- an optional registered statistic.

At base degree `n`, the source objects have length `n + source_offset`; target
objects have length `n + target_offset`. The net degree change is the target
offset minus the source offset. The range is always expressed in base degrees,
so an offset does not silently alter how many cases the experiment covers.

For `enumerate`, exactly one class is present. `count_equivalence` requires a
target and checks counts at every base degree; with a statistic, it additionally
checks the full statistic distributions. `profile_equivalence` requires a
registered statistic and compares its full distributions. `bijection_search`
requires two classes but does not promise that any candidate exists. The
runtime will later attach a candidate grammar, resource budget, checkpoint, and
evidence status to this mathematical specification.

## Class language

`ClassSpec` combines one base family (`ordinary`, `modified`, or `revised`)
with zero or more conjunctive `PatternRuleSpec` requirements. A pattern is a
nonempty classical Cayley pattern with positive integer labels using every
level through its maximum. A rule is either `avoid` or `contain`. Therefore a
class can express, for example, modified words avoiding both `111` and `2122`,
or revised words containing `121` while avoiding `11`.

Pattern occurrences are subsequences on strictly increasing positions;
standardization retains equalities and strict order but ignores the actual value
labels in the ambient word. This is the same convention used by
`ClassicalPattern.compile()` and the current AC experiment builder.

The class language is deliberately narrower than the eventual discovery
system. It does not yet represent disjunction, arbitrary structural conditions,
or the transformation language. Those must be added through schema versions or
separate typed expression nodes, not by giving an existing JSON field a new
meaning.

## Canonical storage

Every serialized object includes:

```json
{
  "format": "ascent-machine-search-spec",
  "version": 1,
  "semantics": "ac-positive-cayley-v1"
}
```

The full schema is validated strictly. Unknown fields and semantics versions
are rejected. Rules are sorted and duplicate conjuncts removed before
serialization; the canonical JSON is hashed with SHA-256 for a stable
question fingerprint. Fingerprints do not claim that two different formulas
are mathematically equivalent; they canonicalize only the equivalences proved
by this schema (rule ordering and duplicate conjunctions).

## Bounded validation

`experiments/reference_ascent.py` contains deliberately direct finite
definitions. It enumerates all words with entries at most their degree, then
tests the ordinary prefix inequality, Cayley support, first occurrences, and
adjoined ascent top/bottom sets without calling production generators. It also
checks classical pattern containment by explicit subsequences and
standardization. The N1 tests compare this reference to the production ordinary,
modified, revised, and modified-via-hat generators through degree 5. This
validates the finite implementation against independent code; it is not a proof
of the definitions or of any all-degree result.

## Example

```python
from ac.discovery.specification import ClassSpec, DegreeWindow, SearchSpec

source = ClassSpec.build("modified", [
    {"mode": "avoid", "pattern": "111"},
])
target = ClassSpec.build("revised", [
    {"mode": "avoid", "pattern": "111"},
])
question = SearchSpec(
    "bijection_search", source, DegreeWindow(1, 5), target,
    source_offset=0, target_offset=2,
)
assert question.degree_shift == 2
restored = SearchSpec.from_json(question.canonical_json())
assert restored.fingerprint == question.fingerprint
```

The example specifies a finite search question only. It does not encode a map,
run an overnight job, or upgrade a bounded match into a proof.
