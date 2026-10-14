# PP-RI-04 stage report — 2026-10-14

Public repository: `Cliff-Lee/ascent-calculus`. Branch: `codex/pp-ri-04`. Starting commit: `cb9e1017208e0818670ac0208a851e84ad6681b3`. Private repository remains clean at `f398f092ab1822a3bb8d0348d2363d671aa64be2`, including its dependency pin.

## Delivered changes and design

- `ac/research_inversions.py`: bounded typed inversion-class adapter, reusing the existing equality-sensitive pattern compiler; separate exact coefficient evaluation of the inspected Testart generating function.
- `ac/research_fishburn.py`: the published leftmost-maximum/in-order construction, node statistics and exact Fishburn-series coefficients, limited to reference benchmark use.
- `ac/research_benchmark_oracles.py`: independent full-product inversion enumeration and recursive labelled-tree enumeration. Neither imports production generators or constructors.
- `ac/research_benchmarks.py`: audited catalogue loading, complete member comparison, duplicate/collision detection, inverse and statistic obligations, witnesses and finite evidence statuses.
- `ac/research_benchmark_runner.py`: deterministic quick/deep task profiles; one or two isolated worker processes, enforced per-cell timeout, atomic degree checkpoints, stale-source/corruption refusal, resume and retained failed attempts. No new dependency.
- `benchmarks_v1.json` and `source_reviews_v1.json`: five statements across three independent families; precise patterns, conventions, coefficient indexing, expected outcomes, algorithms, oracles and caps. Earlier source snapshots remain unchanged.
- `tests/test_research_benchmarks.py`: permanent positive/adversarial and recovery tests; focused CI includes this module. `README.md` gives three reproducible worked examples and programmatic/CLI usage. Campaign ledger updated.

The new inversion class is a distinct adapter, not an alias for ordinary, modified or revised ascent sequences. Fishburn checking compares independent complete sets and structural obligations, rather than assuming equal counts imply a bijection. All execution results retain `proof_status: not_proved`; `PROVED_EXTERNAL` belongs solely to inspected source statements. This stage adds no new theorem, novelty claim, discovery search or formal-kernel verification.

## Actual execution evidence

Interpreter: Python 3.14.7, `/Users/cliffpackman/ascent-research-qt3b/.venv/bin/python`. Commands ran from the public checkout with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.`.

| Check | Result | Evidence |
|---|---|---|
| PP03 + PP04 targeted tests | 76 passed, 1 opt-in skip, 4.75s | `evidence/targeted-pytest.txt` |
| Final full public suite | **281 passed, 1 opt-in skip, 1 expected ZIP-fixture warning**, 43.40s | `evidence/full-pytest.txt` |
| Explicit deep pytest test, `PP_RI_DEEP=1` | **1 passed**, 3.78s | `evidence/deep-pytest.txt` |
| Default quick CLI | **21/21 cells finite_verified** | `evidence/quick.json` |
| Deep CLI, two workers | **32/32 cells finite_verified** | `evidence/deep.json` |
| Identical deep CLI resumed | **32/32 cells reused**, complete | `evidence/deep-resumed.json` |
| Original checkout/executable/private preservation | All recorded checks true | `evidence/preservation.json` |

Full suite command: `python -m pytest -o addopts='' -q`. Deep command: `python -m ac.research_benchmark_runner --profile deep --workers 2 --checkpoint .local-imports/pp04-deep-final`; repeated unchanged to exercise real resume. Source fingerprints and Python/platform are in each report. Per-cell wall-time observations include process startup; resumed records preserve original timings.

Pair-avoidance checks cover complete degrees 1–6; inversion checks cover 0–7; Fishburn transport covers 1–6. Adversarial tests detect a factorial recurrence that fits inversion counts through degree 4 but fails at degree 5, shifted indexing, lost equality distinctions, incomplete/duplicated generation, collisions, wrong inverses and statistic failures. Execution tests cover interrupted-run recovery, real and simulated subprocess deadlines, failed-attempt retention, corrupt checkpoints and incompatible source/profile fingerprints.

Existing `ac` files are unchanged; only new modules were added. The original six external worktree heads/statuses and installed executable hash match their preservation baseline. No existing 2122/2212 code, mathematical definition, GUI, user data or private implementation was edited. No push, merge or release occurred.

## Gate decision and limitations

**PP04 gate passed:** three source-verified independent benchmark families, each with a reproducible worked example; all earlier ordinary/modified/revised regression checks remain green. STOP at this stage.

Independent checks are finite and can share interpretation errors. Length caps deliberately stay small. Memory is controlled by bounded domains/retained-member budgets, not an OS memory quota. Local checkpoint checksums are not tamper-proof execution attestations; one supervisor should use a checkpoint directory at a time. Runtime caps apply through the subprocess runner, not direct library calls. The default test run skips deep execution intentionally; deep was separately exercised here.

Hosted CI and native installer/window checks were not run. Earlier environment/package and full-application preservation limitations still apply; this is not release approval. No external combinatorial software was installed and no abstract was promoted to a theorem.

Next recommended stage: **PP-RI-05, recursive combinatorial specification search adapter**, starting with one of these audited benchmarks and explicitly recording unproved decomposition obligations. PP05 has not begun. PP12 remains deferred pending the earlier campaign gates and design review.
