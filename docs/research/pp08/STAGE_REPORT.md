# PP-RI-08 stage report — 2026-10-14

Public repository `Cliff-Lee/ascent-calculus`; branch `codex/pp-ri-08`; starting commit `134e246a857bdb6069b17e60913e7271fa9265fe`. Private companion remains clean at `f398f092ab1822a3bb8d0348d2363d671aa64be2`.

## Delivered capability

- `ac/research_languages.py`: small typed weighted DFA/one-counter/grammar interfaces, closed serialization, exact integer coefficient evaluation and structured equation export. Counter models explicitly retain an unbounded state component and cannot use the finite-state rational exporter.
- `ac/research_language_benchmarks.py`: regular tiling benchmark, Motzkin counter/grammar benchmark, independent object oracles, ordinary 000/101 source-class bridge, saved derivations, initial conditions and adversarial controls.
- `tests/test_research_languages.py`: 16 tests covering exact counts, complete objects, ambiguity, counter underflow/acceptance, unsupported finite-state classification, omitted branches, wrong weights/constants, schema misuse, zero-degree cycles, budget preflight and source corruption.
- `scripts/pp_language_demo.py`, `source_reviews_v1.json`, method review, usage documentation and execution evidence. Public focused CI and campaign ledger updated.

Inspected the private research language and introduction-block grammar before adding these public reference interfaces. Those tools were preserved. Primary method review covers Vatter's insertion-encoding DFA conventions/regularity conditions and IE-reducibility argument, Cayley insertion-encoding definitions, Testart's unbounded-label/kernel example and Baxter–Pudwell's recurrence/path discussion. Inspection scopes and implementation boundaries are in `METHOD_REVIEW.md`; no uninspected general theorem is promoted.

## Exact reference results

The regular model recognizes nonempty one/two tile words with weights 1/2, using the PP07/PP03 Fibonacci reference. Its linear system yields `(t+t^2)/(1-t-t^2)` and coefficients `(0,1,2,3,5,8,13)` through degree 6. Accepted object sets and counts agree with independent tiling and ascent-word oracles.

The counter model tracks nonnegative Motzkin-path height and finishes at zero. The grammar `M = epsilon | H M | U M D M` exports `F_M=1+t*F_M+t^2*F_M^2`, with explicit constant coefficient one. Complete objects, unique finite derivations, counter counts, independent paths and coefficient convolution agree through degree 6: `(1,1,2,4,9,21,51)`.

Baxter–Pudwell Proposition 10 and its displayed recurrence were inspected and recorded as an external source statement. The ordinary 000/101 engine and independent word implementation agree on full members and match positive-degree path counts. The grammar includes an empty path while the ordinary engine excludes an empty word. Comparison starts at degree 1 and records `A=F_M-1`. No sequence-to-path bijection is inferred from matching counts.

A duplicated epsilon rule fails at degree 0 despite generating the same path set; dropping the counter changes the language and fails at degree 1. Additional tests expose an incorrect accepting initial state and size weights. These controls prevent bounded samples or matching positive terms from silently establishing a stronger claim.

## Actual tests and evidence

Python 3.14.7, `/Users/cliffpackman/ascent-research-qt3b/.venv/bin/python`, with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.`:

- `python -m pytest -o addopts='' -q tests/test_research_languages.py`: **16 passed**, 0.30s; `evidence/targeted-pytest.txt`.
- `python -m pytest -o addopts='' -q`: **353 passed, 1 skipped, 1 expected ZIP-fixture warning**, 47.19s; `evidence/full-pytest.txt`. Skip is the existing PP04 opt-in deep test.
- `python scripts/pp_language_demo.py`: positive regular and counter/grammar/ordinary-class checks through degree 6; negative controls retained with first failures. Full models, equations, derivations, source and implementation hashes and actual checkout context in `evidence/demo.json`.
- Original six worktree heads/statuses, installed executable hash, private checkout, pre-existing public ac files and dependency metadata unchanged; `evidence/preservation.json`.

No existing 2122/2212 algorithm, family definition, GUI, private pin or user data changed. No package installed, default dependency added, model-provider call, push, merge or release. Hosted CI/native packaging were not executed; prior full-application preservation limitations remain.

## Dependency and proof boundaries

SymPy is absent in the existing environment. Exact convolution and explicit elimination suffice here, so third-party symbolic solving was judged unnecessary for this benchmark and remains deferred. No optional extra was added or tested. The opt-in library/exporter has no application startup coupling; default installation remains dependency-free.

Polynomial grammar equations count derivations. Algebraicity for intended objects is not automatically asserted; completeness, unambiguity, degree conventions and formal-series branch conditions remain explicit obligations. A finite control-state set does not turn a counter machine into a finite automaton. No proof kernel was run, and no source result is claimed novel.

## Gate and next stage

**PP08 gate passed:** source-grounded exact automaton/grammar benchmarks, independently validated first terms and object sets, retained derivations and explicit logical obligations. STOP.

Limitations: small productive grammars only; no zero-degree recursive productions, nondeterministic automata, general polynomial solver, insertion-encoding engine or finite-transducer implementation. These source methods were investigated with explicit adaptation requirements, not silently claimed implemented. Evaluators are degree/domain-bounded synchronous APIs without an OS timeout.

Next recommended stage: **PP-RI-09, research discovery interface**, under its own campaign gates. PP09 has not begun; PP12 remains deferred until preceding gates and design review.
