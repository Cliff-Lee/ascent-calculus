# GUI-3B Executor — progress, cancellation, and finite-result checkpoint

Date: 2026-10-09

Status: **executor and browser job lifecycle implemented; visual review remains open**

## Scope completed

- Count and class-comparison runs now emit progress updates while enumerating,
  including degree, completed degrees, objects checked in the current pass, and
  cumulative work.
- Native desktop experiments expose a Cancel control and display live scan
  progress without blocking the interface.
- Class-wide transformation audits use the same progress callback and
  cancellation contract.
- Browser clients can start count or transformation jobs with `POST /api/jobs`,
  poll progress/results with `GET /api/jobs/{job_id}`, and request cancellation
  with `POST /api/jobs/{job_id}/cancel`. Both browser experiment panels use the
  job lifecycle and show checked-object and completed-degree progress.
- The local job manager bounds active runs and retained results, and reports
  worker failures as structured job state.
- Cancellation stops at bounded batches. A partially enumerated degree is
  discarded; only fully completed degree rows are returned.
- Count, comparison, and transformation results include an
  `ac.finite-result.v1` evidence record with status (`verified`,
  `counterexample`, or `incomplete`), requested range, completed degrees, and
  object totals. No status implies an all-degree theorem.

## Validation

- GUI experiment, transformation, job lifecycle, and GUI-1 compatibility tests:
  **48/48 pass**.
- Default modified `2122` versus modified `2212` comparison through degree 11:
  **1,248,595** objects on each side; all degree counts match; elapsed **14.749 s**.
- Python compilation and `git diff --check`: pass.
- Browser JavaScript syntax check: pass.
- The full repository suite was started but did not complete within the available
  run window, so this checkpoint does not claim a full-suite pass.

## Remaining GUI-3B work

Review the desktop and browser progress/cancel interactions visually at the
target window sizes. Preserve the current rule that cancellation returns only
complete degree rows and a finite `incomplete` result record.
