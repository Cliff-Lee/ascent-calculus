# PP-RI-03: source-indexed mathematics

This additive public API connects reviewed literature to the existing `ac` predicates, generators and hat maps. It does not change their definitions. The private research engine can later consume serialized presentations without embedding discovery strategy in the public core.

## Contracts and conventions

`ClassPresentation` records family, source value base, pattern restrictions, degree offset, citation and definition version. Word length is `degree + degree_offset`; count expressions use the declared degree. Positive engine values are translated by adding `1 - value_base`. The ordinary universe excludes the empty word; modified and revised universes include it, subject to restrictions. `includes_empty` describes the underlying universe, before restrictions.

`SourcePattern` preserves equalities and relative order, requires a contiguous rank alphabet starting at the declared base, and never silently applies first-occurrence relabeling. `adjacent_positions=(i,)` requires the selected positions for pattern entries i and i+1 to be consecutive; indices start at one. Unsupported families or definition versions require a separately audited adapter. All supported families have finite length-n search alphabet `base .. base+n-1`.

`MapContract` wraps only the existing hat and inverse-hat primitives. It checks family, inverse name, length/degree compatibility and runtime domain/codomain restrictions. Its scope is nonempty words. Declaring restrictive predicates does not establish that the map transports those predicates universally; a violating output raises an error. Finite inverse tests do not certify a new bijection.

`EnumerationStatement` preserves coefficient indexing and a review fingerprint. Exact expressions currently cover affine counts, shifted Fibonacci numbers (F0=0, F1=1), and binomial coefficients plus a constant. This is deliberately a small expression language, with no executable strings or dynamic imports from serialized input. JSON rejects duplicate/unknown fields and nonfinite numbers. Schemas are bounded and use the fixed definition version; reference envelopes carry schema version 1.

## Reviewed references

The three fixtures bind Propositions 5–7 of [Baxter and Pudwell, *Ascent sequences avoiding pairs of patterns*, version 2](https://arxiv.org/html/1406.4100v2) to precise ordinary, zero-based class presentations. Their statements, hypotheses, locators and inspected proof status are in `source_reviews_v1.json`; executable indexing and patterns are in `reference_corpus_v1.json`. PP02's snapshot remains unchanged.

`load_references` accepts only the audited canonical hashes of both snapshots and checks theorem/citation links. A valid citation cannot authorize an altered mathematical statement. Updating a source or binding requires a new explicit audit and version. This is an integrity policy, not a formal proof checker.

## Reproduction and programmatic use

From the public checkout, with the existing development environment:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python scripts/pp_reference_demo.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m pytest -o addopts='' -q tests/test_research_math.py
```

```python
from ac.research_references import load_references
from ac.research_math import evaluate
references = load_references(
    'docs/research/pp03/reference_corpus_v1.json',
    'docs/research/pp03/source_reviews_v1.json',
)
evidence = evaluate(references[0], (1, 2, 3, 4, 5, 6))
assert evidence['status'] == 'finite_verified'
assert evidence['proof_status'] == 'not_proved'
```

`evaluate` enumerates complete member sets using existing generators and a separate Cartesian-product oracle. The oracle uses independent family predicates and pairwise order/equality matching; it shares typed inputs and the declared expression. Both implementations could still misunderstand the source. Agreement is bounded evidence, never a proof. Lengths above six are rejected before enumeration. The output includes complete tested degrees, citations, source bindings, source-code hashes and the first tested failure. A disagreement between implementations is `validation_disagreement`; an agreed count contradicting the expression is `refuted`. Failed count claims report the earliest tested degree, not a claimed minimal counterexample outside the tested range.

These are three references from one ordinary-sequence family, not the multi-family PP04 benchmark laboratory. No grammar synthesis, formal kernel verification, private strategy learning, GUI integration or PP12 implementation is included. Unsupported structures should be added only when a concrete next-stage consumer needs them.
