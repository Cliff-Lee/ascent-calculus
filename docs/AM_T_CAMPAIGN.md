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

**Status: implemented; hosted CI pending.** Every transformation-family search
result now includes a versioned, fingerprinted manifest describing all
registered operations and selectors, which entries were enabled, and the
active grammar and resource bounds. The manifest explicitly labels the search
as bounded and the grammar as incomplete. It does not change candidate
generation, mathematical semantics, or proof status.

Validation:

- Four focused tests check full registry coverage, enabled/disabled entries,
  stable fingerprints, legacy grammar compatibility, and inclusion in a real
  family-search result.
- python -m unittest -v tests.test_am_t1_transformation_manifest,
  compileall, and git diff --check passed locally.
- The cross-platform focused regression will include the new test module.

## Remaining AM-AI target-machine gates

AM-AI's hosted regression and package gates have passed on Windows, macOS, and
Ubuntu. Its live Ollama paired benchmark, overnight soak, and interactive
review on the target Ubuntu machine remain separate open checks; AM-T work
does not mark those gates as complete.
