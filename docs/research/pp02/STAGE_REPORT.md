# PP-RI-02 stage report — 2026-10-14

Public starting commit: `ffc83d75151dbaa0ceebd1dbda5e36db94550b7d`. Development branch: `codex/pp-ri-02`. Private companion stays at `f398f092ab1822a3bb8d0348d2363d671aa64be2`; private code, dependency pin and unpublished research are unchanged.

## Changes

- `ac/research_evidence.py`: nine distinct provenance entity types, strict versioned serialization, typed links and conditional external-status eligibility; bounded offline loading and exclusive snapshot publication.
- `docs/research/pp02/source_cards_v1.json`: eleven P0 cards with explicit citations and inspection limits; ten inspected works and one partially accessible slide lead; three selected externally inspected statements.
- `tests/test_research_evidence.py`: 24 tests for roundtrip, status/type misuse, dangling sources, unsupported proof labels, missing hypotheses, immutable/detached snapshots, exclusive writes, budget limits, blockers, licence provenance and no side effects.
- `scripts/pp_source_review_demo.py`: offline summary, individual card display and optional read-only PP01 lead-link check.
- Existing public CI focused suite now includes these tests. No hosted run or release performed.

No existing definitions, transformations, 2122/2212 construction, GUI code or saved user data changed. No external research software was installed. Full-text sources/licence downloads remain uncommitted local inspection material; cards contain concise original summaries and locators.

## Actual evidence

- Focused provenance plus registry tests: **59 passed**, one intentionally duplicated-ZIP-name fixture warning, 0.56s. Log: `evidence/targeted-pytest.txt`.
- Earlier full suite before two final link tests/formatting additions: **203 passed**, one warning, 38.31s. Log retained as `evidence/pre-final-full-pytest.txt`.
- Final full public suite after all dataset and test additions: **205 passed**, one expected ZIP fixture warning, 38.42s. Log: `evidence/full-pytest.txt`.
- All eleven Work references were checked against a fresh PP01 import of the actual supplied pack; result true. No existing registry database was mutated.
- Offline demonstration output: `evidence/demo.json`. Source snapshot fingerprint is canonical JSON identity, not a hash of remote paper content.
- Original checkout heads/statuses and installed executable hash remain unchanged; private companion is clean at its prior commit, and mathematical engine/GUI source paths are unchanged. Report: `evidence/preservation.json`.
- Software licence bytes were read and hashed; no full-paper content hashes were invented. Sources/versions/locations and access limitations are in the bundle and README.

Test interpreter: `/Users/cliffpackman/ascent-research-qt3b/.venv/bin/python`, Python 3.14.7, `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.`. Full command: `python -m pytest -o addopts='' -q`. No existing environment changed. Packaging/native-window limitations from PP00 remain; those were not rerun for this non-GUI stage.

## Stop decision

**PP02 gate passed subject to the explicit source-inspection boundary:** >=10 traceable cards, a recorded deck blocker, no abstract promoted to a proved theorem, and passing provenance/regression tests. `PROVED_EXTERNAL` denotes inspected external statement/hypotheses and displayed argument only. Schema validation is not independent mathematical validation, source extraction automation or formal proof checking.

Remaining work includes readable PP094 slides, full proofs behind PP073/074, pinned software API compatibility and Maple rights. The next stage is PP-RI-03: typed mathematical representations and independently checked reference fixtures derived from reviewed sources. PP-RI-03 and the deferred PP-RI-12 proposal have not been implemented. No merge, push or release occurred.
