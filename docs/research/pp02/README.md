# PP-RI-02: source inspection and claim provenance

Scope: source/model/claim review only. No bijection, tree, recurrence or automaton implementations are introduced. No new dependencies, automatic network service or GUI changes. PP-RI-03 and PP-RI-12 are not started.

## Deliverables

`ac.research_evidence` supplies distinct frozen data types for Source, Work, Claim, Definition, Theorem, Algorithm, Evidence, SourceLocation and Citation. `ReviewBundle` stores an immutable canonical JSON snapshot with a fingerprint, strict field/version/size validation and typed referential checks. Source inspection status is independent of statement proof status. File publication is atomic and exclusive; an existing review artifact is never overwritten by the save API.

`source_cards_v1.json` contains eleven P0 method cards linked to the unchanged PP01 pack hash and original IDs: PP-129, 031, 094, 073, 042, 047, 066, 074, 120, 109 and 110. Ten have inspected papers, extended abstracts or software documentation. The eleventh has a confirmed official listing plus an explicit slide-deck access blocker. Each card names family, assumptions, construction, input/output types, complexity uncertainty, proof mechanism, implementation idea, adaptation risks and blockers. Work/source/citation entities provide authors, title, selected-source year, URL/version, inspection date and precise section/page labels.

The initial 140-record metadata registry is not edited or promoted. Corrections are separate linked Work records: the vincular paper's published title and 2012 version, joint authorship for the two Cerbai/Claesson papers, and the left-growth paper's 2025 publication in the PP2024 issue. Work years identify the selected source/publication association; software entries use the reviewed-year association, not an invented release year.

## Inspection boundary

Five versioned paper sources were inspected in relevant definitions, numbered statements and arguments: pair-pattern avoidance, Burge transport, Fishburn trees, left-growing inversion trees and vincular enumeration schemes. Only three selected statements receive `PROVED_EXTERNAL`: PP-129 Proposition 5, PP-047 Proposition 4.4 and PP-120 Theorem 15. Their hypotheses, family, indexing and pattern semantics are preserved. This label records external source inspection; it does not mean proof replay or formal kernel verification.

Three extended abstracts were inspected: PP-031 printed pages 27-28 of the PP2021 programme, and the three-page PP2025 abstracts for PP-073 and PP-074. Their construction descriptions are leads, not fully checked theorems. PP-073's reported result is explicitly proposed and linked to a source marked NEEDS_REVIEW. Neither the counter-automaton claim nor the insertion-encoding criteria are promoted to independently verified mathematics.

The two software READMEs and licence texts were inspected. Both licence files contain BSD three-clause conditions, including notice retention and no endorsement. Digests and URLs are recorded. No library was installed, executed or vendored. Branch documentation is not a pinned compatibility audit; PP05 must review an exact code version and dependencies. Maple reuse rights remain unverified. The left-growth publisher's CC BY 4.0 licence is linked separately. arXiv posting licences are not assumed to authorize redistribution; no full paper is committed.

The official PP2026 slides index confirms PP-094's listing, but text retrieval of the linked Google Drive deck failed. The card records no extracted algorithm. Failed retrieval through the browser tool is not proof that the deck is globally inaccessible. The DMTCS direct-download attempt also failed; the versioned arXiv HTML supplied an accessible alternative. Initial software licence retrieval had sandbox DNS denial and succeeded after network permission. These are access observations, not mathematical counterexamples.

## Trust and current limitations

This is a hand-reviewed source bundle. Validation checks schema, citations, status eligibility and missing hypotheses; it cannot certify that a reviewer accurately transcribed or independently proved a theorem. In particular, importing self-declared review metadata is not a mathematical verifier. Formal proof and finite-validation labels are deliberately unsupported by this PP02 serializer. Later proof artifacts require their own verifier/definition bridge.

Content hashes are supplied for the actual retrieved software licence bytes. Remote paper/programme views were not retained as bytes, so their hashes remain explicitly null; stable arXiv versions or programme/source locators and inspection dates are preserved instead. No fictional content digest or theorem number is supplied. Text/formula transcription should be checked against PDFs before implementing a mathematical adapter. All complexity fields remain unverified unless explicitly reported as abstract claims.

Typed mathematical statement ASTs, source retrieval automation, full evidence database integration, cumulative orchestration, strategy learning and original theorem search remain later-stage work. This module provides provenance types, not replacements for existing universe definitions.

## Reproduction

```sh
PYTHONPATH=. python scripts/pp_source_review_demo.py
PYTHONPATH=. python scripts/pp_source_review_demo.py --work-id W-PP-129
PYTHONPATH=. python scripts/pp_source_review_demo.py --database .local-imports/pp-ri/registry.sqlite3
PYTHONPATH=. python -m pytest tests/test_research_evidence.py tests/test_pp_research_library.py -o addopts='' -q
```

```python
from ac.research_evidence import load_review, save_review
review = load_review('docs/research/pp02/source_cards_v1.json')
review.method_cards('W-PP-120')
review.entities('Theorem')
review.entities('Source')
save_review('new-review.json', review)  # refuses an existing destination
```

The database check only confirms immutable lead/pack links; it never changes PP01 record fields or verifies source statements. Tests and demos are offline. Source retrieval was a separate explicitly authorized investigation, not a side effect of these APIs.

## Gate

PP02 requires at least ten traceable cards or an explicit access-blocker report, no unsupported theorem statements and passing provenance tests. Eleven cards and a scoped blocker are supplied. Actual tests, source-link demonstration, preservation audit and commit are recorded in the stage report. Stop here; request PP-RI-03 separately after review.
