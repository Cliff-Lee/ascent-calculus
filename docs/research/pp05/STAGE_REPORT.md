# PP-RI-05 stage report — 2026-10-14

Public repository `Cliff-Lee/ascent-calculus`; branch `codex/pp-ri-05`; starting commit `8f0438b6c867eca59d444d25674a87a26b080a96`. Private companion remains clean at `f398f092ab1822a3bb8d0348d2363d671aa64be2`.

## Delivered

- `ac/research_specifications.py`: typed insertion strategies, atom/rule recursive specifications, guarded constructors/decompositions, an object interpreter, derivation-count equations, independent replay, bounded constructor search and an explicit universal-obligation ledger.
- `tests/test_research_specifications.py`: 18 tests for roundtrip, all small complete object sets, holdout evaluation, inverse and membership guards, overlaps, incomplete atoms, wrong constructors with equal coefficients, oracle disagreement, unsafe schema fields, budgets and transfer to a different ordinary class.
- `scripts/pp_specification_demo.py`: offline reproducible search and readable specification/evidence output, including source hash and actual checkout context.
- `docs/research/pp05/README.md`, `upstream_audit.json`, retained search/test/preservation evidence and this report. Focused public CI and stage ledger updated.

The PP04 Fibonacci benchmark (`PP129-P6`) supplies the class and source motivation. Sixteen combinations of four insertion primitives for one-copy/two-copy branches are tested on degrees 3–4. One survives and passes independently enumerated holdout degrees 5–6: insert the new maximum after the first old maximum. All fifteen failed candidates and their first tested failures are preserved. Complete replay through degrees 1–6 covers closure, coverage, branch uniqueness, collisions, parent membership and both reconstruction directions. Matching coefficients alone is insufficient: the deliberately incorrect prepend construction matches the survivor's derivation counts and fails object checks.

The readable conditional equation is `A=t+2t^2+t(A-t)+t^2*A`, hence `(1-t-t^2)A=t+t^2` if universal obligations hold. All seven obligations remain `unproved`; structural hypotheses are expressly `not_tested`. The published reference proof is not automatically a proof of the synthesized implementation. This is source-guided reconstruction, not blind rediscovery or novelty.

## Upstream compatibility decision

Inspected `comb_spec_searcher` README, pyproject and full BSD-3-Clause licence at develop commit `826a16cc6b40b48eac1c334c777e2cc3da30740d`, plus current PyPI release 4.3.0 metadata. Documented interfaces include class identity/serialization, strategy packs, constructor maps and automatic search. Released dependencies differ from develop. Python metadata permits >=3.10, but runtime compatibility with this project's >=3.11 environment and local 3.14.7 was not tested.

Decision: an independently authored small rule interface. No upstream implementation was installed, imported or vendored; no new dependency or optional extra was added. Consequently the default installation remains isolated from upstream dependencies. A future optional package adapter must undergo its own runtime compatibility tests. Sources, versions and hashes are recorded in `upstream_audit.json`; full retrieved material remains ignored local inspection data.

## Actual execution

Interpreter `/Users/cliffpackman/ascent-research-qt3b/.venv/bin/python`, Python 3.14.7, with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.`:

- `python -m pytest -o addopts='' -q tests/test_research_specifications.py`: **18 passed**, 0.94s; `evidence/targeted-pytest.txt`.
- `python -m pytest -o addopts='' -q`: **299 passed, 1 skipped, 1 expected ZIP-fixture warning**, 47.67s; `evidence/full-pytest.txt`. The skipped case is the existing explicit deep-profile test; the full suite retains earlier ordinary/modified/revised and PP04 quick checks.
- `python scripts/pp_specification_demo.py`: 16 trials, 15 refuted, 1 finite survivor with passing holdout and six-degree replay; `evidence/search.json`.
- Preservation inspection: original six worktree heads/statuses, installed executable hash, private checkout and all pre-existing public `ac` files unchanged; `evidence/preservation.json`.

No changes to the 2122/2212 construction, GUI, existing mathematical definitions, saved data or private engine/dependency pin. No push, merge, release or replacement of an installed application. Hosted CI, native packaging and upstream runtime integration were not executed; prior application-preservation limitations remain.

## Gate and stop

**PP05 gate passed:** one reproducible class adapter, independent small-degree object/count checks, serialized readable rules/equation and explicit unproved obligations. Optional third-party integration remains absent from default install.

The interpreter supports a bounded insertion grammar and degrees at most six, not general specification search. Holdout is independently enumerated but source-guided, and no all-length proof or strategy learning is claimed. Source references in generic specifications are provenance metadata, not a certified mathematical binding. Advanced private heuristics, proof formalization and cumulative knowledge orchestration remain future work.

Next recommended stage: **PP-RI-06, automatic generating-tree rule discovery**, following its own gates. PP06 has not begun; PP12 remains deferred until earlier gates and design review. STOP here.
