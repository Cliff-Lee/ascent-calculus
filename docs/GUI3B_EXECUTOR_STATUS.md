# GUI-3B Executor — progress, cancellation, and finite-result checkpoint

Date: 2026-10-09

Status: **executor foundation implemented; browser job lifecycle remains open**

## Scope completed

- Count and class-comparison runs now emit progress updates while enumerating,
  including degree, completed degrees, objects checked in the current pass, and
  cumulative work.
- Native desktop experiments expose a Cancel control and display live scan
  progress without blocking the interface.
- Class-wide transformation audits use the same progress callback and
  cancellation contract.
- Cancellation stops at bounded batches. A partially enumerated degree is
  discarded; only fully completed degree rows are returned.
- Count, comparison, and transformation results include an
  `ac.finite-result.v1` evidence record with status (`verified`,
  `counterexample`, or `incomplete`), requested range, completed degrees, and
  object totals. No status implies an all-degree theorem.

## Validation

- GUI experiment, transformation, and GUI-1 compatibility tests: **45/45 pass**.
- Default modified `2122` versus modified `2212` comparison through degree 11:
  **1,248,595** objects on each side; all degree counts match; elapsed **14.749 s**.
- Python compilation and `git diff --check`: pass.
- The full repository suite was started but did not complete within the available
  run window, so this checkpoint does not claim a full-suite pass.

## Open GUI-3B work

The browser endpoint currently waits for a run to finish before returning JSON.
The next executor slice should add a cancellable run lifecycle for browser
clients (start, progress polling, cancel, final finite result) while keeping all
enumeration and pattern semantics in the Python engine.
