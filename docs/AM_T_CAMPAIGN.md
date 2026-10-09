# AM-T — Transformation calculus campaign

AM-T improves the public, bounded transformation calculus and makes its
searches easier to inspect and reproduce. Candidate matches remain finite
evidence, and the registered grammar remains explicitly incomplete.

The public AM-T track covers documented operations, their typed composition,
search provenance, and validation over finite classes. Before AM-T6 adds new
primitive invention or evolutionary synthesis, that work moves to a separate
independent private repository. It will not be developed on a private branch
or public fork of this repository.

## T1 — Search-scope manifest

**Status: passed on 2026-10-09.** Every transformation-family search
result now includes a versioned, fingerprinted manifest describing all
registered operations and selectors, which entries were enabled, and the
active grammar and resource bounds. The manifest explicitly labels the search
as bounded and the grammar as incomplete. It does not change candidate
generation, mathematical semantics, or proof status.

Validation:

- Four focused tests check full registry coverage, enabled/disabled entries,
  stable fingerprints, legacy grammar compatibility, and inclusion in a real
  family-search result.
- `python -m unittest -v tests.test_am_t1_transformation_manifest`,
  `compileall`, and `git diff --check` passed locally.
- GitHub Actions run #41 passed the new test on Windows, macOS, and Ubuntu.
  All three platform package jobs passed as well, including Ubuntu install,
  launch, and preview checks.

## T2 — Finite behavior equivalence

**Status: implementation added; hosted regression pending.** Exact candidates
that induce the same complete finite maps across every requested scenario now
share a family-map fingerprint. Results count the explored candidates in each
behavior group and retain one example program. This identifies redundant
program descriptions without changing search ranking or claiming equivalence
outside the listed finite class and degree-offset windows. Proof status remains
`not_proved`.

The family checkpoint version is now 2 so an interrupted run cannot resume
with incomplete behavior-group counts from the older checkpoint schema. A
focused regression uses three distinct exact programs that collapse to one
finite behavior group, checks the bounded-scope language, and resumes from a
completed checkpoint.

## Remaining AM-AI target-machine gates

AM-AI's hosted regression and package gates have passed on Windows, macOS, and
Ubuntu. Its live Ollama paired benchmark, overnight soak, and interactive
review on the target Ubuntu machine remain separate open checks; AM-T work
does not mark those gates as complete.
