# PP-RI-06 stage report — 2026-10-14

Public repository `Cliff-Lee/ascent-calculus`; branch `codex/pp-ri-06`; starting commit `d22fe282a9c4d8afc32ec0e3b5e4f991730d4778`. Private companion remains clean at `f398f092ab1822a3bb8d0348d2363d671aa64be2`.

## Delivered and architectural scope

- `ac/research_generating_trees.py`: typed, serializable left/right inversion growth strategies and statistic-label schemas; complete edge/reachability audit, candidate transition inference, finite feature-subset minimization, deterministic shortest tested refutations, recurrence replay and a source-reviewed published demo.
- `ac/research_growth_oracle.py`: independent full-product inversion enumeration, pairwise pattern semantics and predecessor-derived edge checking.
- `tests/test_research_generating_trees.py`: 18 tests for published transitions, full left/right edges, false label witnesses and holdout failures, disconnected avoidance subtrees, incomplete generation, independence, source corruption, schema/family/budget misuse, duplicate/malformed transitions, frontier extrapolation refusal and rejection of false PROVED statuses.
- `scripts/pp_generating_tree_demo.py`, immutable `source_reviews_v1.json`, documentation and retained evidence. Focused CI and campaign ledger updated.

Inspected existing private `generating_tree.py` and workbench interfaces before implementation. Their hat-transported modified trees are mathematically different from literal append. They were preserved without refactoring or migration. The new public strategy supports inversion sequences; no modified or revised family is silently treated as an inversion class. Advanced ranking, private invention and learned policies remain outside this public slice.

## Mathematical evidence

The published reference is Testart, Sections 1.1–3, Proposition 3 and Lemma 4 of arXiv:2411.05726v3. Definitions and displayed proof were reinspected; the separate source snapshot records external provenance and exact assumptions. No abstract was promoted to a theorem. No new all-length proof or novel result is claimed.

Left and right growth agree with independent complete edges and root reachability through degree 7. The published left label s = leading zero count + indicator of nonleading zeros reproduces every observed state-transition multiplicity. Recurrence replay gives `(1,1,2,6,24,116,632,3720)`, matching independent objects and PP04's separate exact generating-function coefficients.

The bounded search evaluates 22 labels per side, trains on parent degrees 0–3 and checks heldout parents 4–6 in the recorded degree-7 run. Minimal feature subsets are reported within this grammar. Total zero count fits training but fails at parent degree 4; the shortest tested pair is `(0,0,0)` and `(0,1,0,0)`. Every right-growing candidate is refuted in this small grammar. These unsuccessful capabilities and first witnesses remain in the audit.

A separate 010-avoidance test detects disconnected left growth: the valid child `(0,0,2,1)` has the forbidden predecessor `(0,1,0)`. Complete coverage is therefore checked rather than presumed from legal local edges.

All transition inferences and execution records have `proof_status: unproved`. The finite table refuses unexpanded states. All-length label sufficiency, tree closure/coverage and exact formal-definition correspondence remain explicit unproved obligations, separate from the external source's inspected theorem.

## Executed validation

Python 3.14.7, `/Users/cliffpackman/ascent-research-qt3b/.venv/bin/python`, with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.`:

- `python -m pytest -o addopts='' -q tests/test_research_generating_trees.py`: **18 passed**, 0.73s. Log: `evidence/targeted-pytest.txt`.
- `python -m pytest -o addopts='' -q`: **317 passed, 1 skipped, 1 expected ZIP-fixture warning**, 45.55s. Log: `evidence/full-pytest.txt`. The skipped test is the prior opt-in PP04 deep profile.
- `python scripts/pp_generating_tree_demo.py --through 7`: both tree audits finite_verified, published formula/recurrence agreement true. Output: `evidence/demo.json`, including actual base-commit/dirty context, exact strategies, trial tables/witnesses, source snapshot and implementation/oracle hashes.
- Original six worktree heads/statuses, installed executable hash, private repository and all pre-existing public ac source files unchanged. Boolean-only public evidence: `evidence/preservation.json`.

No existing 2122/2212 algorithm, mathematical definition, GUI, private dependency pin or user data changed. No new dependency, provider call, merge, push or release. Hosted CI/native packaging were not run; prior full-application preservation limitations continue to apply.

## Gate and stop

**PP06 gate passed:** one source-verified published tree reconstructed; meaningful left/right growth independently explored; deliberately false inferred labels refuted; no computational transition promoted to PROVED. STOP.

This is finite, source-guided exploration with a declared feature grammar, not general all-length state minimization or unrestricted invention. The scalar label is unbounded; its finite observed table is not a finite automaton for the whole class. Runtime is domain-bounded without a hard subprocess deadline in this API. Missing richer right labels remain an explicit limitation. The source statement has not been formalized in a proof kernel.

Next recommended stage: **PP-RI-07, pattern transport and recursive bijection laboratory**, following its own public/private boundaries and gates. PP07 has not begun; PP12 remains deferred until preceding gates and design review.
