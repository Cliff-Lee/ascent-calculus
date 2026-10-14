# PP-RI-00 / PP-RI-01 acceptance report

Only the first two stages were implemented. The supplied `/Users/cliffpackman/Desktop/codex_PP_resarch.md` is the campaign reference, despite its different filename from the originally requested document. The ZIP SHA-256 matches its declared `d254e7db1b3ca4cea306d0a295db0128ec3dbdde426c3e36f97619bc971d7bd7`.

## Changes

- `ac/research_library.py`: offline secure importer, dedicated transactional SQLite store, immutable original metadata/source bytes, hashes, UTC import timestamp, versioned keyword index, read-only search API, JSON/CSV exports and CLI.
- `pyproject.toml`: `ac-research-library` entry point. No new dependencies.
- `.gitignore`: `.local-imports/` staging excluded from source/distribution.
- `tests/test_pp_research_library.py`: 35 acceptance/security tests; CI uses synthetic 140-record metadata without requiring downloads or private fixtures. `PP_RESEARCH_PACK` selects a supplied pack.
- `.github/workflows/release.yml`: registry tests included in the existing focused test job. Hosted CI was not run here.
- `scripts/pp_registry_demo.py`: disposable-store demonstration against an explicit source path and expected hash.
- Architecture, input schema, usage documentation and actual evidence logs in `docs/research/`.

No current engine definitions, generators, transformations, GUI implementation, saved user data or 2122/2212 algorithm changed. Public source does not contain private algorithms, research dossiers or raw ZIP contents. The private dependency remains pinned and unchanged; its future integration should consume this public API after review.

## Executed validation

Interpreter: existing Python 3.14.7 environment. Public code selected with `PYTHONPATH=.`.

| Check | Result | Evidence |
|---|---|---|
| Public full suite, including registry tests | 181 passed, one expected duplicate-ZIP-name test warning, 40.37s | `evidence/pp-full-pytest.txt` |
| Real-pack focused registry suite | 35 passed | `evidence/pp-targeted-pytest.txt` (double-quiet mode omits count) |
| No-download synthetic fixture suite | 35 passed, one expected warning, 0.42s | `evidence/pp-synthetic-pytest.txt` |
| Actual source-pack demo | 140 records; 46 P0, 60 P1, 34 P2; second import `already_ingested` with same timestamp/hash | `evidence/pp-real-pack-demo.json` |
| GUI model/import smoke | Models and metadata module imported; native import blocked by missing `_tkinter` | `evidence/pp-gui-smoke.json` |
| Packaging smoke | Build could not load `setuptools.build_meta` in this environment | `evidence/pp-build-smoke.txt` |

Exact test commands:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m pytest -o addopts='' -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PP_RESEARCH_PACK=/private/tmp/pp-missing-fixture.zip python -m pytest tests/test_pp_research_library.py -o addopts='' -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m build --no-isolation --outdir .local-imports/pp-ri/dist
```

The first two commands used `/Users/cliffpackman/ascent-research-qt3b/.venv/bin/python`. Packaging was attempted with the same interpreter. No existing environment was changed or unnecessary package installed. Model smoke imports `ac.gui.research_state`, `ac.gui.experiments` and `ac.research_library`; a native window was not launched. System Python can create a Tcl 8.5.9 interpreter, which does not substitute for native application acceptance.

Test coverage includes exact 140-record/source-byte roundtrip, Unicode author search, all filter dimensions, deterministic exports, formula-safe CSV, detached results, version retention, duplicate IDs/keys/names, malformed counts/dates/years/URLs/status fields, source-hash mismatch, traversal/absolute/extra/symlink members, expansion limits, corrupt archives/JSON, foreign-store preservation, concurrent imports, rollback and refusal to silently repair altered stored records.

## Gate decision and stop

**PP00 inventory/test-baseline gate: passed**, with environment-limited native/packaging smoke explicitly recorded. The architecture is additive and baseline mathematical behavior remains covered by the existing suite. This is not a release/installer preservation gate.

**PP01 acceptance gate: passed**: 140 records, correct priorities, unique original IDs within pack, exact field/source roundtrip, deterministic export, secure malformed-input handling and idempotent second import validated against actual supplied data and synthetic tests.

Native window, distribution build and hosted CI remain unverified due to environment limits; perform those checks in the existing supported packaging environment before release. Existing broader ADP preservation blockers still apply. No source has been retrieved or inspected beyond the supplied metadata/audit. All entries remain CATALOGUED, not source-verified mathematics. Keyword family tags are heuristic, and future index/schema changes need versioned contracts. CSV formula escaping is deliberate; JSON/source export is lossless.

**STOP: PP-RI-02 was not started.** It requires a separate stage request and legitimate primary-source inspection. The proposed PP-RI-12 design remains deferred pending earlier gates and human review.

## Subsequent stage ledger

The stop decisions above describe the original PP00–01 execution. Later authorized stages:

- PP02: source verification completed; see `pp02/STAGE_REPORT.md`.
- PP03: typed representations and independent reference checks completed; see `pp03/STAGE_REPORT.md`.
- PP04: published benchmark laboratory completed; see `pp04/STAGE_REPORT.md` for the current gate and exact evidence.
- PP05: recursive specification adapter completed; see `pp05/STAGE_REPORT.md`.
- PP06: generating-tree rule discovery completed; see `pp06/STAGE_REPORT.md`.
- PP07: pattern transport and recursive bijection laboratory completed; see `pp07/STAGE_REPORT.md`.
- PP08: language/automata and symbolic equation exporter completed; see `pp08/STAGE_REPORT.md`.
- PP09 has not begun. PP12 remains deferred until prior gates and design review.
