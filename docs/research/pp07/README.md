# PP-RI-07 conversion and recursive bijection laboratory

This stage extends the existing word/selector transport tools with a bounded conversion graph for different mathematical representations. It reuses PP04's Fishburn conversion and PP05's source specification. The existing core symmetry transport, private formal transport, synthesis tools and 2122/2212 construction remain unchanged.

## Reproduce the public reference experiments

From the public checkout, using the existing environment:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python scripts/pp_conversion_demo.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m pytest -o addopts='' -q tests/test_research_conversion_graph.py
```

```python
from ac.research_conversion_audit import load_reference_graph, audit_conversion
from ac.research_recursive_bijections import to_tiles, from_tiles

graph = load_reference_graph()
word = (0, 1, 2, 2, 1)
assert to_tiles(word) == (1, 2, 2)
assert from_tiles(to_tiles(word)) == word
assert graph.apply_path(('fibonacci-to-tiles', 'tiles-to-fibonacci'), word) == word
assert audit_conversion(graph, 'modified-to-tree', (1,2,3,4,5,6))['status'] == 'finite_verified'
```

## Exact conversion contracts

`Endpoint` records the representation, precise versioned word family where applicable and finite nonempty scope. `ConversionEdge` records domain/codomain, primitive/inverse references, two-sided inverse obligation, degree shift, source snapshot/citations, applicable pattern encodings, statistic pairs and proof status. Reciprocal inverse edges and typed path boundaries are validated; a revised sequence cannot silently stand in for a modified sequence. The only supported primitives are the four declared reference maps, with zero degree shift. All endpoints use degrees 1–6.

`graph_v1.json` is an immutable, hash-bound reference graph. Its `tested_degrees` fields begin empty: the file declares hypotheses; actual tested coverage and results are attached in `evidence/demo.json`, rather than trusting a prefilled coverage assertion. Generic graph serialization validates structure and supported constructions; only `load_reference_graph` enforces the audited reference/source binding. Metadata alone is not proof or execution attestation.

Word families retain their existing definitions. Fishburn trees are immutable `(left, positive_label, right)` triples, with `None` empty; labels are regular, decrease weakly down the tree and strictly into left subtrees, and first-label occurrences coincide with the initial in-order node plus nodes having a left child. Endpoint checks enforce these conventions. Tile words are nonempty tuples of 1 and 2, with degree equal to their sum. Degree zero is excluded throughout this experiment, including tile objects, to match the existing ordinary-sequence convention.

## Literature-grounded transport

[Cerbai–Claesson, Definitions 2.1/3.1, Proposition 4.4 and Corollary 4.5](https://arxiv.org/html/2211.07200v2) provide the positive modified-word/Fishburn-tree correspondence. We reinspected the exact in-order and inverse conventions. The map recursively splits at the leftmost maximum; the inverse reads in-order labels. Both implementations already exist in PP04 and are reused here.

The graph's pattern correspondences use **classical word containment in the tree's in-order encoding**. They do not assert avoidance of a tree-shape pattern. Registered examples are 111, 121 and 321, with equalities preserved. The engine compiler checks the source word; an independently written iterative traversal and pairwise matcher check the tree encoding. Additional tests cover every normalized pattern of arity at most three at degree four.

The audit compares source production with independent word enumeration, and word-engine tree images with independent recursive labelled-tree enumeration. Injectivity, coverage, both compositions, endpoint membership, node count, maximum, first-occurrence positions and ascent-top positions are checked separately. Exact pattern transport follows the declared encoding; no broader structural transport theorem is inferred from these examples.

## Two-way recursive experiment

[Baxter–Pudwell Proposition 6 and its displayed argument](https://arxiv.org/html/1406.4100v2) motivate the source class avoiding 000 and 001. The PP05 specification pairs its one/two-maximum branches with appending a tile of size one/two. This is a source-guided experiment on a published class, not a new source claim that the particular implementation was published or proved.

Three structural bases are paired: `(0,) <-> (1,)`, `(0,0) <-> (2,)`, `(0,1) <-> (1,1)`. Beyond those bases, forward recursion removes all maxima and appends the appropriate tile. Inverse recursion removes the final tile and uses the PP05 insertion constructor. Neither direction enumerates a target set or consults a matching table.

The parallel specifications both satisfy the conditional equation `X=t+2t^2+t(X-t)+t^2*X`. Equal equations do not establish a bijection: complete object and inverse tests are required. At degrees 1–6 both classes have `(1,2,3,5,8,13)` objects. The worked word `(0,1,2,2,1)` removes two copies of maximum 2, then two copies of maximum 1, leaving base `(0,)`; its tile image is `(1,2,2)`.

The statistics tested are length/total tile size, repeated-entry count/number of size-two tiles, and distinct-entry count/number of tiles. The target specification interpreter is compared with a separate full-product tiling oracle. Source membership uses both the existing engine and the PP03 independent oracle. No generator is invoked by the map itself.

## Failures and proof boundaries

The demo retains three negative controls. A constant inverse and an all-size-one forward map first fail at degree 2. The latter loses injectivity and coverage. A false statistic link (distinct entries equal total tile size) fails at degree 2 while the bijection and both compositions still pass. Every failure includes the first tested degree and witnesses; no minimality outside tested scope is implied. Backend disagreement is distinguished from a mathematical refutation.

All conversion executions and recursive implementation obligations remain `unproved` with finite evidence statuses. Published source provenance is separate. All-length source decomposition, branch disjointness/coverage, mutual inverses, statistic preservation and exact formal-definition correspondence remain open implementation proof obligations. No proof kernel was run.

The graph supports only these canonical reference conversions and bounded paths of at most four edges. It is not a theorem knowledge graph, general conversion synthesis engine or implementation of PP12. Complexity/simplicity is descriptive evidence, not a proof criterion. The APIs are synchronous with bounded mathematical domains, without an OS wall-clock deadline.

The private modified 2122/2212 experiment remains opt-in and was not run or enabled here. Public benchmark success supplies the prerequisite gate, not an automatic private research action. PP08 and PP12 remain separate stages.
