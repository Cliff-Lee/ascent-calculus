# AM-Next N12 validation and release decision

N12 is split into four reviewable gates. A bounded map match is not a proof,
and a source-level desktop check is not a packaged-application launch check.

| Gate | Scope | Status |
|---|---|---|
| N12a | Blind bounded transformation rediscovery | Passed |
| N12b | Independent enumeration and held-out degrees | Passed |
| N12c | Crash recovery, desktop startup, and packaging | Source checks passed; package and visual checks unavailable here |
| N12d | Release decision | Complete: not release ready |

## N12a: blind bounded rediscovery

The search asks whether ordinary ascent sequences of degree `n` map to
modified ascent sequences of degree `n`. It receives only those class
definitions and a generated grammar containing snapshot-selected prefix-lift
sweeps over the raw ascent-top selector. The named `HatT` atom and target map
are excluded. The candidate budget is 32, the cost limit is 2, and the search
exhausts the candidate space after testing five normalized programs (identity
plus four generated sweep variants).

The search returns one finite candidate:

```text
SweepLiftT(selector=RawAscTop(), inverse_lift=False, direction='ltr')
```

This is classified as `blind_bounded_rediscovery`: the candidate is selected
by the grammar and finite map evaluator, not supplied as a map. The grammar is
still a finite, human-designed vocabulary and the result establishes no
all-degree theorem. The exact question and search result are recorded in
`experiments/results/am_n12_blind_search.json`.

The earlier modified-`111` to revised-`111` degree-`+2` run is not classified as
blind. Its 108-recipe catalogue contains increasing-run segmentation,
reverse-complement block mapping, and insertion of a maximum pair around the
first block—the structural ingredients of the target map. It is recorded
separately as `reconstruction_from_seeded_operations` in
`experiments/results/am_n12_block_reconstruction.json`. This distinction
prevents grammar leakage from being presented as independent discovery.

## N12b: independent enumeration and held-out checks

The validator uses literal all-tuples definitions in
`experiments/reference_ascent.py`, not production class generators or the
named Hat map. It rechecks the blind search's training window `n=1..5` and
held-out degrees `n=6,7`. Ordinary and modified class counts agree at every
degree:

| Degree | 1 | 2 | 3 | 4 | 5 | 6 (held out) | 7 (held out) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Ordinary | 1 | 2 | 5 | 15 | 53 | 217 | 1,014 |
| Modified | 1 | 2 | 5 | 15 | 53 | 217 | 1,014 |

The generated map is defined on every independently enumerated source, lands
in the target, has no collisions, and covers the target through degree 7. This
is finite computational evidence only. The full independent record is
`experiments/results/am_n12_independent_validation.json`.

The seeded block reconstruction was independently re-enumerated for base
degrees `n=1..6`, comparing modified `111`-avoiders at degree `n` with revised
`111`-avoiders at degree `n+2`. The counts agree as `1, 2, 4, 10, 29, 97`.
Twelve candidates pass the training window through `n=4`; three survive both
held-out degrees `n=5,6` (target degrees 7,8). The other nine fail by a
collision or an image outside the revised class. The result and first failures
are in `experiments/results/am_n12_block_validation.json`.

## N12c: recovery and launch checks

The real worker crash-recovery test passed: a worker was terminated after a
durable checkpoint, the job recovered as interrupted, and a second worker
resumed and completed it with its saved progress and event history. All three
tests in `tests/test_am_n2_worker.py` passed. The desktop
`python -m ac.gui.desktop --startup-check` and worker
`python -m ac.discovery.worker --help` checks also passed.

This environment is Linux with Python 3.12.14 and Tk 9.0, but has no
`DISPLAY`, `xvfb-run`, pytest, or PyInstaller. Consequently, it was not possible
to review the interactive desktop, build a packaged application, or test
packaged launch and multiprocessing on Mac or Windows. These are incomplete
release checks, not passing checks.

## N12d: release decision

**AM-Next is not release ready.** The mathematical blind-search and
independent held-out gates passed, and the source-level worker and desktop
checks passed. The release gate remains open until the desktop receives visual
review and a packaged build passes launch and worker checks on supported
platforms. The repository should be treated as a research-engineering branch,
not a released desktop application.

The direct compatibility harness is not pytest. The N12-focused cases passed
and the complete harness result is recorded in `AM_NEXT_CAMPAIGN.md` after the
full run. No package was built and no theorem is claimed.

## Linux package follow-up (2026-10-08)

After the N12d decision, the Ubuntu 24.04 amd64 `.deb` was built from commit
`bcbbd1b`. Its package metadata and dependencies were inspected, the package
was extracted, and its desktop `--startup-check` passed against the packaged
source with the available Python/Tk runtime. The launcher and desktop entry
are present. The optional Python wheel also built using the installed local
setuptools. The normal isolated wheel build could not fetch build dependencies
because this environment blocks network access.

This does not close the interactive packaged-launch gate: the container has
no desktop display, and the Ubuntu system interpreter here lacks `python3-tk`.
The `.deb` declares `python3-tk`; installing it on the target Ubuntu machine
and opening the window there remains the manual visual check.
