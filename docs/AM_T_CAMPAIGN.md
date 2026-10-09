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

**Status: passed on 2026-10-09.** Exact candidates
that induce the same complete finite maps across every requested scenario now
share a family-map fingerprint. Results count the explored candidates in each
behavior group and retain one example program. This identifies redundant
program descriptions without changing search ranking or claiming equivalence
outside the listed finite class and degree-offset windows. Proof status remains
`not_proved`.

The finite group counts are kept in a separately versioned checkpoint so an
interrupted run cannot resume with incomplete behavior-group counts. A
focused regression uses three distinct exact programs that collapse to one
finite behavior group, checks the bounded-scope language, and resumes from a
completed checkpoint. The local T1/T2 focused suite passed, as did
`compileall` and `git diff --check`.

GitHub Actions run #44 passed all three regression runners and all three
platform package jobs. Ubuntu install, launch, and desktop preview checks
passed; Windows installer smoke checks and the macOS package build passed.

## T3 — Auditable behavior vectors and schema-safe checkpoints

**Status: passed on 2026-10-09.** Each finite
behavior group now includes the scenario fingerprint and finite-map
fingerprint for every component of its combined family fingerprint. That
lets a researcher inspect exactly which bounded scenario maps define a group
without treating the combined hash as a proof.

Saved family-search questions retain schema version 1; the interim version-2
form is also accepted. The resumable checkpoint now has its own version,
separate from the saved-question schema, so future progress-state changes do
not silently change the experiment format. Regression checks cover both
specification versions, the scenario-level vector, and checkpoint resume.
The local focused suite, `compileall`, and `git diff --check` passed. GitHub
Actions run #47 passed all three regression runners and all three platform
package jobs, including Ubuntu install/startup and desktop previews.

## T4 — Scenario-by-scenario map previews

**Status: passed on 2026-10-09.** Retained
candidate rows now include one bounded input/output preview for each requested
scenario, with its scenario fingerprint. The legacy first-scenario preview
field remains available. Previews are generated only for retained exact or
ranked candidates, keeping the additional work and saved result size bounded
independently of the full candidate budget.

The T2/T3 regression now checks that all scenarios appear in exact-candidate
previews and that the compatibility preview is the first item in that list.
The T1–T4 local focused suite, `compileall`, and `git diff --check` passed.
GitHub Actions run #49 passed all three regression runners and all three
platform package jobs, including Ubuntu install/startup and desktop previews.

## T5 — Scenario evidence in the research interface

**Status: passed on 2026-10-09.** The candidate
evidence panel now displays the bounded sample input/output for each scenario
alongside its match or failure status. A finite-family fingerprint is shown
with an explicit finite-window limitation. The preview action opens the first
available scenario map, and older saved candidate records that contain only
the legacy preview remain readable.

Focused UI-formatting tests cover multiple scenario previews and the legacy
single-preview record. The release workflow now runs the AM-N10 UI regression
alongside the AM-T tests. Locally, the three UI checks were invoked directly
because `pytest` is not installed; the hosted regression ran them under pytest.
GitHub Actions run #52 passed all three regression runners and all three
platform package jobs, including Ubuntu install/startup and desktop previews.

## Remaining AM-AI target-machine gates

AM-AI's hosted regression and package gates have passed on Windows, macOS, and
Ubuntu. Its live Ollama paired benchmark, overnight soak, and interactive
review on the target Ubuntu machine remain separate open checks; AM-T work
does not mark those gates as complete.
