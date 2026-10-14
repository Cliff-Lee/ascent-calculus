# PP08 method investigation and scope

Primary sources were inspected on 2026-10-14. This is a method-design review, not a claim that every cited paper's proofs or all software implementations were audited.

| Method | Source and actual scope inspected | Consequence for this stage |
|---|---|---|
| Regular languages and insertion encoding | [Vatter, arXiv:0911.2683v1](https://arxiv.org/html/0911.2683v1), Sections 3–4: DFA conventions, slot configurations, regularity conditions, IE-reducibility and Proposition 3's argument | Finite automata export linear generating-function systems. A finite sampled slot/state inventory is insufficient to establish regularity. No insertion-class regularity theorem is newly certified here. |
| Equality-sensitive insertion encodings | [The insertion encoding of Cayley permutations, arXiv:2505.08480v1](https://arxiv.org/html/2505.08480v1), introduction and Section 2 definitions only | Repeated values require different encoding conventions. Vertical and horizontal approaches must not be identified by assuming an inverse symmetry available for permutations. Further proof/software review is needed before an adapter. |
| Unbounded state methods and algebraic generating functions | [Testart, arXiv:2411.05726v3](https://arxiv.org/html/2411.05726v3), Lemma 4 and Theorem 5 proof, including its kernel equation | PP06's unbounded label cannot be converted to a finite-state model merely because tested labels are finite. The inspected algebraic solution uses source-specific equations and assumptions. |
| Recursive enumeration and path encodings | [Baxter–Pudwell, arXiv:1406.4100v2](https://arxiv.org/html/1406.4100v2), Propositions 6/10 and their displayed arguments; Section 3 path definitions/encoding discussion | Reuse the Fibonacci reference and add a small Motzkin counter/grammar benchmark. Preserve initial conditions explicitly. A count identity alone does not construct a sequence-to-path bijection. |

A finite-transducer interface was considered for transporting finite-alphabet encodings. This stage does not establish a finite transducer for raw ascent words: the alphabet is unbounded, and PP07's recursive map is not automatically a finite-state transducer. Such an adapter requires an explicit encoding, output/weight semantics, completeness and inverse obligations. No finite-transducer or general insertion-encoding engine is implemented in this slice.

The `comb_spec_searcher` interface/licence review from PP05 remains applicable. Its pinned local README was already read; a new web read of that pinned page was unavailable. Nothing here assumes new API compatibility or installs its dependencies.

SymPy is absent in the existing environment. Exact integer convolution suffices to evaluate these exported systems; the rational reference is obtained by explicit elimination of two linear equations. We chose no symbolic dependency or optional extra. General polynomial solving, branch selection, factorization and algebraicity certification are deferred. This satisfies the benchmark/export objective while keeping default installation unchanged; it does not claim third-party symbolic integration was tested.

The machine/grammar module is opt-in library code, with no GUI/startup coupling. Advanced strategy selection, encoding invention and unpublished findings remain private. The investigation identifies extension requirements without implementing PP12 or expanding the current public campaign beyond PP08.
