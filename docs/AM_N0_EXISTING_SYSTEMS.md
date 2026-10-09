# AM-N0 — Existing research and baseline comparison

**Status:** completed as a bounded literature review and local reproduction suite.  The
reproduction code is `experiments/am_n0_baselines.py`; its regression checks are in
`tests/test_am_n0_baselines.py`.

This baseline answers two questions before the next discovery-system expansion:

1. What has already been automated for finding statistics, class specifications, and
   bijections?
2. What would count as evidence that AC found a transformation, rather than merely
   noticing equal counts?

The systems below solve related but different problems.  AC should connect to them where
they strengthen a research workflow, rather than present itself as a replacement for
their databases, specification provers, or general-purpose constrained solvers.

## 1. Existing systems

| System | Main object searched | Core method | What its result gives a researcher |
|---|---|---|---|
| [FindStat](https://www.findstat.org/) | Statistics and maps on registered combinatorial collections | Search finite object/value or object/image data against a curated database; allow bounded compositions of registered maps and statistics | Known formulas, maps, references, and candidate identifications. Match quality records database coverage and distinct values; it is evidence of a database match, not a new all-degree theorem. |
| [Combinatorial Exploration](https://arxiv.org/abs/2202.07715), implemented in [`comb_spec_searcher`](https://github.com/PermutaTriangle/comb_spec_searcher) | Decompositions/specifications of a combinatorial class | Generate an interconnected universe of classes using constructors and search for a valid specification; formal strategy maps support counting and object generation | A recurrence, generating function, enumeration algorithm, and sometimes a recursive bijection between classes with compatible specifications. |
| [A Bijectionist’s Toolkit](https://www.mat.univie.ac.at/~slc/wpapers/FPSAC2023/91.pdf) | Constrained bijections/statistics between finite sets | Encode assignments and distribution/equivariance requirements as a 0–1 integer linear program; enumerate solutions or minimal forced subdistributions | Whether finite constraints are feasible, which statistic fibers must match, and which assignments are forced by the constraints. |
| [OpenEvolve bijection study](https://proceedings.mlr.press/v334/jenne26a.html) | Executable programs intended to be bijections | LLM-generated program mutations, finite injectivity/surjectivity/validity scoring, diverse candidate populations, and LLM review | Interpretable candidate code and a measured finite score. The study finds one known Dyck-path bijection, but reports failures on other known/open problems and emphasizes human review. |

### FindStat

FindStat defines collections, maps between collections, and statistics as functions on
objects.  Its query engine searches supplied samples against those stored functions and
their bounded compositions.  The documentation explicitly reports separate coverage and
distinct-value match quality, and illustrates both single-object statistic lookup and
equidistribution queries.  Its map inventory is deliberately a curated collection of
research-significant maps; a query can rediscover a composition represented in that
inventory, but it does not synthesize an arbitrary new map from the input samples.

**Reusable ideas:** the level-by-level collection abstraction; compact object-to-statistic
and object-to-image datasets; map/statistic composition; offsets on statistic values;
coverage and diversity measures; permanent records with definitions, code, and references.
These support AC’s need for portable, inspectable experiment records and optional searches
for known results.  AC already has degree-indexed classes and map composition, but has no
FindStat-scale external catalogue or database matching service.

### Combinatorial Exploration

Combinatorial Exploration turns user-defined combinatorial classes and constructors into
a search space of related classes.  Its search derives specifications; verified
decomposition rules then support counts, generating functions, and object generation.
Its scope includes permutation patterns and proof-of-concept applications to other
families, including words.  `comb_spec_searcher` also shows how parallel specifications
can be converted into a bijection and how an inverse can be checked on generated objects.

**Reusable ideas:** constructor-based class descriptions; a graph of related subclasses;
formal decomposition strategies with forward/backward object maps; specification
verification; efficient recurrence-based counting and random generation.  These are
complementary to AC’s current brute-force small-degree enumeration and would be the right
route to higher degree limits and structural counting formulas.  AC currently searches
maps among specified classes; it does not infer a general combinatorial specification or
generating function.

### Bijectionist’s Toolkit

This Sage tool addresses a useful middle layer between “the counts agree” and “here is a
structural map.” A user supplies finite sets plus constraints such as statistic
preservation, intertwining an action, involution, or homomesy.  The implementation encodes
the assignment with a 0–1 ILP; its minimal-subdistribution analysis can report constraints
that force parts of any solution.  The paper’s motivating rotation/LIS example establishes
finite existence through (n\leq 9), while its (S_4) discussion shows how orbit parity
forces values on rotation-fixed permutations.

**Reusable ideas:** let a researcher add equations/invariants to the finite search;
report forced fibers and infeasibility certificates; and distinguish an unconstrained
finite pairing from one compatible with useful statistics or symmetries.  AC’s candidate
diagnostics already expose collisions, missing targets, and target violations.  However,
the map search does not yet accept statistic-preservation or equivariance constraints as
hard filters, and it does not solve a general assignment ILP.  That is a concrete
follow-on integration point.

### Automated program synthesis

The 2026 OpenEvolve study represents each candidate as executable code, measures validity,
injectivity, and surjectivity on small degrees, and evolves programs using LLMs. It also
uses an LLM judge for structural quality and “cheating” checks.  It found a known
odd-diagonal-path/Dyck-path bijection after 60 iterations; in reported runs it did not
find a bijection for 321-avoiding permutations versus Dyck paths or the open area-bounce
extension.  The authors identify coarse scores, objective hacking, and the need for expert
inspection as ongoing challenges.

**Reusable ideas:** finite map-quality metrics; a population of diverse candidates;
counterexample-driven feedback; anti-enumeration safeguards; and explicit human-readable
candidate algorithms.  AC’s finite auditor uses the same basic map properties but retains
exact collision fibers and missing targets as concrete witnesses.  AC currently uses a
deterministic, typed vocabulary of AC transformations and block recipes, rather than
LLM-generated arbitrary Python.  This is more reproducible and easier to normalize, but
searches a much narrower space.  A future stochastic or language-model proposal layer could
suggest new typed recipes, but should never be confused with proof or bypass finite checks.

## 2. Local reproductions

Run the baseline suite from the project root:

```bash
python experiments/am_n0_baselines.py
```

It needs only the project’s Python code.  SageMath, `comb_spec_searcher`, an ILP solver,
and a hosted LLM service are not required.  The output is JSON so that the observations
can be archived or diffed.  Each entry states whether it recomputes a published finite
claim or reproduces only the underlying finite data.  The external search algorithms
themselves are not claimed to have been rerun.

### FindStat: nesting and crossing data

FindStat’s documentation gives the query that submits perfect matchings of sizes
0, 2, 4, 6, and 8 with their nesting counts, then searches for an equidistributed
statistic.  The published query identifies crossings and nestings.  The local script
re-enumerates all **125** matchings at those five levels and compares the full
distributions exactly.  At four pairs, for example, the shared distribution is

| Value | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Matchings with that many crossings | 14 | 28 | 28 | 20 | 10 | 4 | 1 |
| Matchings with that many nestings | 14 | 28 | 28 | 20 | 10 | 4 | 1 |

This reproduces the finite mathematical input/result, not FindStat’s live database
ranking or its reported sample-coverage percentage.  It also illustrates a limit of
count-only experiments: equal distributions identify an equidistribution, not a
particular objectwise bijection.

### Combinatorial Exploration: words avoiding adjacent repeats

The official code example reports the counts for binary words avoiding `bb` through
length 10 as

```text
1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144
```

The local check recomputes those counts by enumeration and confirms the recurrence
$a_n=a_{n−1}+a_{n−2}$, with $a_0=1,a_1=2$.  The same example asks
`ParallelSpecFinder` to discover a bijection between words avoiding `00` and words
avoiding `11`, then verifies inverse recovery through length 4.  Our local control checks
that the two classes have equal counts and verifies bit complement as an explicit
bijection on all 19 source words through length 4.  **This does not claim to reproduce
the map produced by `comb_spec_searcher`;** that dependency is not installed here and
the published example does not specify that its generated map is bit complement.

### Bijectionist’s Toolkit: a finite forced-value deduction

For $S_4$, the paper’s rotation action has four fixed permutations.  The locally
recomputed longest-increasing-subsequence distribution is `{1: 1, 2: 13, 3: 9, 4: 1}`.
If a candidate statistic is constant on rotation orbits and has this distribution,
every non-fixed orbit contributes an even number of copies of each value.  The odd
multiplicity of each value forces the four values 1, 2, 3, and 4 to occur once each on
the four fixed permutations.  The script reconstructs these permutations and counts.
This reproduces the paper’s finite orbit-parity deduction directly, not its Sage ILP
solver or the full $n≤9$ feasibility computation.

### AC: equal counts followed by blind transformation synthesis

The AC positive benchmark compares modified `111`-avoiders of degree $n$ with revised
`111`-avoiders of degree $n+2$.  At $n=1, …, 5$, both count vectors are

```text
1, 2, 4, 10, 29
```

That is the **enumeration-only baseline**.  The next stage searches all 108 generated
`BlockSchemaT` recipes of net shift +2, without seeding the named
`Modified111BlockBijection`.  Each candidate is checked on all 46 source objects in
degrees 1 through 5 for definedness, target membership, injectivity, and surjectivity.
The bounded search returns three exact recipes.  All three have increasing-run blocks,
safe-up block order, reverse-complemented block values, and a new-maximum pair around
the first block; they differ only in a parent rule that is redundant on these tested
inputs.  Each candidate gives the same outputs as the separately registered reference
map on all 46 inputs.

This is a genuine **rediscovery within a bounded grammar**: a rule was selected by
searching a generated recipe space and passed exact finite map checks.  It is not a proof
that the recipe works at all degrees, nor a claim that the search space contains every
reasonable transformation.

### AC: a near-bijection negative control

The existing `FibreGapPack(2,1,right)` candidate between modified `2122`- and `2212`-
avoiders passes the map checks through degree 6, but has a collision at degree 7.  The
baseline records the first colliding source pair and shared image.  This prevents a
high finite score or matching initial counts from being presented as a successful map,
and gives a concrete clue about the information the candidate loses.  It does not
refute the class equivalence or other transformations.

## 3. Benchmarks: enumeration versus transformation discovery

Every AC search result should report which evidence level it reached.  The following
labels are intentionally distinct:

| Evidence level | Required computation | Permitted interpretation |
|---|---|---|
| Count match | Source and target cardinalities agree at each tested degree | A finite enumeration coincidence; candidate for a conjecture |
| Map into target | A named candidate is defined and every tested image lies in the target class | Candidate respects the target condition |
| Finite bijection | Map into target, no collisions, and no missing target objects at every tested degree (including shifts) | Verified bijection on the enumerated degrees |
| Inverse check | A proposed inverse round-trips all tested source and target objects | Independent executable inverse evidence |
| Proof | General argument covering all degrees | Theorem; never inferred from finite tests |

For every transformation-discovery benchmark, retain:

- exact source and target predicates and degree shift;
- universe generators and tested degree window;
- candidate grammar, grammar size, cost/depth bound, normalization rules, and seed;
- candidates evaluated, count-only baseline, map-test outcomes, and first counterexample;
- exact collision fibers and missing targets on failure;
- a serialized, inspectable recipe and the finite verification statement.

The two AC cases above form positive and negative controls.  The
$M_n(111) → R_{n+2}(111)$ run must recover at least one recipe without the named map atom; the
`FibreGapPack` run must stop with its degree-7 collision.  A change that reports only
the equal count vector fails this benchmark.  Search time is recorded for performance
tracking, but should not be the correctness criterion because it depends on hardware and
cache state.

## 4. What AC does differently

The most precise description is that AC is currently a **domain-specific finite
transformation laboratory**.

| Capability | Existing systems | Current AC workbench |
|---|---|---|
| Scope | Broad registered collections (FindStat), constructor-driven classes (Combinatorial Exploration), arbitrary finite constrained sets (Bijectionist’s Toolkit/OpenEvolve) | Ordinary, modified, and revised ascent-sequence classes with structural and pattern predicates |
| Main search target | Known database entry, a class specification, any finite constrained assignment, or executable program | A typed composition of AC transforms or generated block recipes connecting selected classes |
| Degree shifts | Vary by system/query | Class comparisons support offsets; current map grammar searches net shifts 0, +1, +2, and the registered inverse at −2 |
| Evidence | Database match quality, verified specification, ILP feasibility/forced constraints, or program scores | Exact degree-by-degree definedness, target membership, collision and coverage audit, with witnesses and failure degree |
| Interpretability | Database records, formal specifications, ILP constraints, or generated code | Normalized symbolic recipe with visible selector, block, local-map, and extension choices |
| General result | Can identify known facts, derive recurrences, or solve finite constraint systems | A successful result is explicitly “verified through n=k”; proof obligations remain for the researcher |

AC’s main difference is not that the other systems fail to check maps.  It is the
combination of ascent-sequence definitions, a generated domain-specific operation
grammar, degree-changing block rules, and exact map-failure witnesses in one local
workflow.  Its narrow grammar is also its present ceiling: it cannot find a rule that
cannot be expressed by the enabled transformations and recipes.  It does not infer
arbitrary code, build general recursive specifications, or prove conjectures.

## 5. Concrete reuse decisions

**Reuse in the next stages**

1. Adopt FindStat-style named statistics and maps as optional external references, with
   citations and source attribution.  Keep database-match scores separate from finite
   bijection verification.
2. Add a formal constructor/specification layer for ascent-sequence subclasses so count
   matches can be pushed to higher degrees and recursive decompositions can become
   machine-checkable certificates.
3. Add Bijectionist’s-Toolkit-style user constraints to map search: statistic transport,
   symmetry/intertwining, involution, and selected profile preservation.  First implement
   them as exact finite filters over the current enumerated classes; later consider a
   matching/ILP backend when finite assignment constraints are more expressive than the
   transformation grammar.
4. Reuse the standard validity/injectivity/surjectivity metrics, but rank candidates with
   separate defect data rather than one aggregate score.  Keep exact witnesses visible.
5. Keep every automatically proposed operation in a typed grammar with a declared degree
   signature and domain of definition.  Candidate generation may be broadened, but
   executable candidates must remain replayable and independently testable.

**Do not claim as current capabilities**

- complete coverage of all mathematically sensible transformations;
- all-degree bijection proofs from finite enumeration;
- automatic discovery of arbitrary generating functions or structural recurrences;
- FindStat-like global identification of known maps/statistics;
- proof-level support from a sampled or aggregate bijection score.

## References

- Martin Rubey and Christian Stump. [“FindStat — a database and search engine for
  combinatorial statistics and maps.”](https://www.mat.univie.ac.at/~slc/wpapers/FPSAC2019/103.html)
  FPSAC 2019, Séminaire Lotharingien de Combinatoire 82B, Article 103 (2019). See also
  the [FindStat Sage documentation](https://doc.sagemath.org/html/en/reference/databases/sage/databases/findstat.html)
  for query semantics and examples.
- Michael H. Albert, Christian Bean, Anders Claesson, Émile Nadeau, Jay Pantone, and
  Henning Ulfarsson. [“Combinatorial Exploration: An Algorithmic Framework for
  Enumeration.”](https://arxiv.org/abs/2202.07715) Memoirs of the AMS 293 (2024), no. 1457.
  See the [`comb_spec_searcher` published examples](https://github.com/PermutaTriangle/comb_spec_searcher/blob/develop/example.py)
  for the binary-word count and `ParallelSpecFinder` bijection checks.
- Alexander Grosz, Tobias Kietreiber, Stephan Pfannerer, and Martin Rubey.
  [“A bijectionist’s toolkit.”](https://www.mat.univie.ac.at/~slc/wpapers/FPSAC2023/91.pdf)
  Séminaire Lotharingien de Combinatoire 89B (2023), Article 91.
- Helen Jenne, Davis Brown, Jesse He, Max Vargas, and Henry Kvinge. [“Even with AI,
  Bijection Discovery is Still Hard: The Opportunities and Challenges of OpenEvolve for
  Novel Bijection Construction.”](https://proceedings.mlr.press/v334/jenne26a.html)
  Proceedings of TAG-DS 2026, PMLR 334(2):108–122.
