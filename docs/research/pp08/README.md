# PP-RI-08 exact languages, counters and grammar equations

This optional library layer represents weighted deterministic finite automata, deterministic one-counter machines and small productive context-free grammars. It exports equations as structured data and evaluates coefficients using exact integer arithmetic. The default package dependency list and application startup remain unchanged.

## Reproduce

From the public checkout with the existing development environment:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python scripts/pp_language_demo.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m pytest -o addopts='' -q tests/test_research_languages.py
```

```python
from ac.research_language_benchmarks import tile_automaton, motzkin_models
from ac.research_languages import equation_coefficients

regular = tile_automaton()
assert regular.counts(6) == (0,1,2,3,5,8,13)
counter, grammar = motzkin_models()
assert counter.counts(6) == (1,1,2,4,9,21,51)
assert equation_coefficients(grammar.equations(),6)['M'] == counter.counts(6)
```

## Exact model semantics

Terminals have positive integer weights; degree is their total weight, not necessarily string length. Finite automata contain bounded declared control states and deterministic labelled transitions. Missing transitions reject. They export linear equations for generating functions of accepted suffixes, including explicit final-state constants. Positive weights exclude zero-degree cycles. Their weighted accepted-word GFs are rational; relating that machine to an intended combinatorial class is a separate obligation.

One-counter machines keep the same finite control-state representation but also have a genuinely unbounded nonnegative counter. A transition changes it by -1, 0 or 1; underflow rejects and acceptance requires counter zero. The finite evaluator only visits the heights possible at the tested degree. This finite test domain is not a finite-state model of the whole language. A one-counter model may happen to recognize a regular language, but the generic finite-state rational exporter refuses it rather than discarding the counter.

Grammar symbols are explicitly tagged terminal/nonterminal. Each nonempty production consumes positive terminal degree; recursive zero-degree/unit productions are unsupported. The interpreter preserves all derivations, including duplicates, and exposes ambiguity under independent object comparison. An epsilon production contributes an empty object. Polynomial equations count derivations until completeness and unambiguity are justified for intended objects. The exporter does not label an arbitrary class algebraic merely because it produced an equation.

All interfaces use closed versioned JSON. No executable expression strings or dynamic class imports are accepted. The coefficient evaluator consumes typed-export monomial data and uses exact convolution; it does not solve arbitrary polynomial systems or formally certify algebraicity. Bounds are four states/nonterminals, three terminals, twelve transitions, eight productions, eight-degree coefficient/counter evaluation and six-degree grammar/object experiments. A derivation budget prevents excessive ambiguity from exhausting memory. Runtime is synchronous without an OS-level timeout.

## Regular reference: one/two tilings

The weighted language is all **nonempty** words on symbols `one` and `two`, of weights 1 and 2. A two-state DFA separates the nonaccepting initial state I from accepting state A. Its equations are

```text
F_I = (t+t^2)*F_A
F_A = 1+(t+t^2)*F_A
F_I = (t+t^2)/(1-t-t^2).
```

The degree-zero coefficient is zero. Complete accepted words and counts through degree 6 are compared with PP07's independent tiling oracle and the PP03 independent ordinary-class oracle. The source class is the [Baxter–Pudwell Proposition 6](https://arxiv.org/html/1406.4100v2) reference avoiding 000 and 001. The raw unbounded ascent-word alphabet is not declared regular; this is a statement about its tile encoding, with PP07's universal implementation obligations still open.

## Counter/grammar reference: Motzkin paths

The counter model reads H, U and D, all of weight one, and changes height by 0, +1 and -1. The grammar is

```text
M = epsilon | H M | U M D M
F_M = 1+t*F_M+t^2*F_M^2, F_M(0)=1.
```

The arch rule splits a path into its first up/down excursion and the following path. Its exact derivation coefficients are `(1,1,2,4,9,21,51)` through degree 6. A separate full-product path oracle tests prefix balance and final height using counts of U/D. The grammar's full object sets, uniqueness of derivations, counter acceptance and coefficient evaluator agree.

[Baxter–Pudwell Proposition 10 and its displayed recurrence](https://arxiv.org/html/1406.4100v2) are separately source-reviewed in `source_reviews_v1.json`. Independent complete ordinary-word checks for 000/101 avoidance agree with these counts for degrees 1–6. The ordinary engine excludes the empty word while the path grammar includes it. The benchmark explicitly compares from degree 1 and records the class relation `A(t)=F_M(t)-1`; it does not silently replace the engine's degree-zero convention. No new sequence-to-path map is claimed.

The report saves equation systems, elimination/grammar derivations, exact initial conditions, source snapshots and logical obligations. This is finite evidence plus external source review, not a new proof-kernel result.

## Adversarial checks and remaining work

A duplicated epsilon production generates the correct path set but overcounts its derivations starting at degree zero. Discarding the counter admits invalid paths and fails at degree one. Tests additionally detect omitted grammar branches, incorrect terminal weights, an incorrect accepting initial state, nondeterminism, dangling symbols, zero-degree recursion, unsupported proof fields and source changes.

`METHOD_REVIEW.md` records inspected regular/insertion, counter, grammar, path and potential transducer methods, with boundaries for adaptation. SymPy is absent; optional third-party symbolic solving is deferred because the current exact benchmark does not require it. No dependency was added or installed.

All-length encoding completeness, grammar unambiguity, exact source hypotheses and selected formal-series branches remain explicit obligations. The public layer provides reusable semantics and exporters; private strategy learning and invention remain untouched. PP09 and PP12 are not implemented here.
