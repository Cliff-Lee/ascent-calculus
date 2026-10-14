# PP-RI-03 stage report — 2026-10-14

Repository: `Cliff-Lee/ascent-calculus`, branch `codex/pp-ri-03`, starting commit `dfd00f59c7e1e7846eb612e597fb5f2ff039176d`. The private companion remains clean at `f398f092ab1822a3bb8d0348d2363d671aa64be2`; its dependency pin and unpublished research are unchanged.

## Delivered

- `ac/research_math.py`: exact typed source conventions, equality-sensitive and position-adjacent patterns, distinct family adapters, degree shifts, guarded existing hat/inverse contracts and finite count statements.
- `ac/research_math_oracle.py`: independently implemented finite enumeration, membership and pattern checks.
- `ac/research_references.py`: immutable audited source/statement bindings; altered mathematics cannot inherit an external proof label merely by retaining its citation.
- `source_reviews_v1.json` and `reference_corpus_v1.json`: three source-reviewed ordinary-sequence reference statements with exact coefficient indexing. The earlier PP02 dataset is preserved.
- `tests/test_research_math.py`: 38 tests covering serialization, all three families in both source bases, all rank-normalized patterns of arity at most three at length four with classical/consecutive matching, map restrictions and inverse behavior, false formulas, shifted claims, backend disagreement, corruption, and preflight budgets.
- `scripts/pp_reference_demo.py`, usage documentation and retained execution evidence. Focused public CI includes the new tests.

## Executed checks

Using Python 3.14.7 in the existing environment, with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.`:

- `python -m pytest -o addopts='' -q tests/test_research_math.py`: **38 passed**, 0.88s.
- `python -m pytest -o addopts='' -q`: **243 passed**, 38.71s, one expected duplicate-ZIP fixture warning. Exact log: `evidence/full-pytest.txt`.
- `python scripts/pp_reference_demo.py`: all three reference fixtures independently agree on complete member sets and declared counts for degrees 1–6. Output: `evidence/demo.json`; it truthfully records the base commit plus dirty working state and hashes of evaluated source files.
- Preservation inspection: original six checkout heads/statuses, installed executable hash, private checkout and existing engine/GUI sources unchanged. Boolean-only public evidence: `evidence/preservation.json`.

No new runtime dependency, external service transmission, application replacement, release, merge or push. The existing 2122/2212 algorithm was not edited. Hosted CI and native packaging were not run; prior missing setuptools/Tk and application parity limitations remain outside this additive stage.

## Gate and remaining limits

**PP03 gate passed:** definitions round-trip; incompatible families, inverse contracts and conventions are rejected; cited fixtures pass independent finite checks. The source's `PROVED_EXTERNAL` review status is separate from this run's `finite_verified` evidence and `not_proved` proof status. No theorem was formally verified or newly discovered here.

The count corpus currently covers one source and one family; other families have independent semantic checks, not new published enumeration fixtures. The oracle deliberately stops at length six. General expressions, arbitrary transforms, grammar composition, proof transport and statistic mappings await concrete consumers. Earlier PP02 source-access/software-rights limitations remain recorded there.

Stop at PP03. Next recommended slice: **PP-RI-04, published-results benchmark laboratory**, following its separate campaign acceptance gates. The proposed **PP-RI-12: Cumulative Mathematical Discovery** remains deferred until earlier gates and design review. Typed definitions, source fingerprints and explicit evidence records provide extension points without adding its orchestrator or strategy learning now.
