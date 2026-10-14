# PP-RI-06 finite generating-tree rule discovery

The public reference experiment reconstructs Testart's left-growing tree for inversion sequences avoiding 201 and 210, and compares it with ordinary right extension. [Sections 1.1–3, especially Proposition 3 and Lemma 4](https://arxiv.org/html/2411.05726v3), supply the inspected definitions and succession rule. The immutable review snapshot records external source status; implementation evidence always retains `proof_status: unproved`.

## Reproduction

From the public checkout, using the existing development environment:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python scripts/pp_generating_tree_demo.py
# Explicit larger bounded reference replay:
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python scripts/pp_generating_tree_demo.py --through 7
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m pytest -o addopts='' -q tests/test_research_generating_trees.py
```

```python
from ac.research_generating_trees import reference_demo
report = reference_demo(6)
left = report['sides']['left']['published_replay']
assert left['counts'] == (1, 1, 2, 6, 24, 116, 632)
assert left['counts_match']
assert left['proof_status'] == 'unproved'
```

`GrowthStrategy` has explicit inversion-class and side contracts with closed versioned serialization. Its right operation appends a value in `0..n` to a length-n parent. Its left operation prepends zero, increments positive entries, and increments a chosen subset of the parent's zero entries. Both restrict outputs using existing equality-sensitive pattern compilation. Strategies operate on words directly, without finite target lookup.

`research_growth_oracle.py` independently enumerates all position-alphabet words and checks pairwise equalities/order. It assigns target objects to predecessors by deleting the final entry on the right, or deleting the initial zero and decrementing positive entries on the left. It imports no production membership, matching or growth implementation. The evaluator compares entire edge sets, duplicates, orphan targets and reachability from the empty root at every tested level. For a disconnected avoidance subtree it records the failure even if individual legal edges match.

The new adapter supports inversion sequences only. The private engine's existing modified-family trees are hat-transported ordinary growth; inspection confirmed that literal append is not equivalent. Those tools, their GUI and the 2122/2212 investigation remain unchanged.

## Labels, witnesses and recurrence candidates

Labels are explicit `LabelSchema` hypotheses assembled from supported statistics. The reference search explores 22 schemas: the empty label, each of six statistics and each pair. Features include leading zeros, a flag for nonleading zeros, total zeros, the published composite s, last entry and ascent count. Additional evaluator features cover maximum, repeats, runs and first occurrences. No advanced ranking or learned search policy is included.

Training expands parent degrees 0–3; holdout expands 4 through `through-1`. A label must determine the entire child-state multiset, including multiplicities and comparisons across degrees. Frontier children are not classified as leaves. Counterexamples use the smallest maximum parent degree in the tested range, followed by deterministic degree/word visit order; this is not a claim of shortest witnesses outside the complete tested range.

The published scalar is s = number of leading zeros + indicator of a later zero. On the left it reconstructs the observed transition table. The label using total zero count fits training but fails at parent degree 4: `(0,0,0)` and `(0,1,0,0)` share three zeros and have different child-label multisets. The right experiment refutes every schema in this small grammar. That result says nothing about richer right-growing labels.

For example, a left parent with s=3 has child labels 1 once, 2 four times, 3 twice and 4 once. Its eight children arise from actual zero-subset choices, not a count-only construction. The published formula is checked against every observed scalar-state row. Finite label tables yield the recurrence candidate

```text
population[n+1,j] = sum_s population[n,s] * multiplicity(s,j)
population[0,0] = 1.
```

`table_counts` replays this table and refuses unexpanded states, refuted labels, invalid multiplicities and `PROVED` status. At degree 7 the replay gives `(1,1,2,6,24,116,632,3720)`, agreeing with independently enumerated objects and the separate exact generating-function calculation from PP04. This table is a bounded instance, not a finite automaton for the infinite class. The underlying published s label is unbounded.

The report records minimal feature subsets among finite survivors and observed-state counts. This is finite redundancy minimization within the declared grammar, not a canonical minimal all-length state space. Source-informed labels are included openly; the experiment is not blind rediscovery. Each trial retains its configuration, training evidence, holdout evidence where applicable and first refutation witness. All-length sufficiency, closure/coverage and correspondence of formal definitions remain explicit unproved implementation obligations.

## Limits and preservation

Parent degree is at most 6 and target degree at most 7; unsupported strategies, indices and malformed definitions fail before enumeration. Runtime is synchronous and bounded by these domains, without a hard wall-time limit in this API. A separate subprocess wrapper is needed for externally imposed deadlines. No new package or model provider is used.

The included 010 negative control demonstrates that left avoidance pruning can disconnect a class: `(0,0,2,1)` avoids 010, but its left predecessor `(0,1,0)` does not. The evaluator preserves this obstruction rather than assuming hereditary closure.

PP06 public code owns typed strategies, finite evaluators and source-reviewed demonstrations. Private advanced heuristics remain untouched. No universal transitions receive a proved label, no source result is claimed novel, and PP07/PP12 are not implemented here.
