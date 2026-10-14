# PP-RI-04 published-results benchmark laboratory

This public, offline laboratory exercises five reference statements across three independent mathematical families. It extends the PP03 adapters without changing ascent-family definitions, the 2122/2212 algorithm, GUI code or private research-engine dependencies. It is a benchmark suite, not a conjecture discovery or proof-certification engine.

## Sources and reproducible examples

| Family | Source-reviewed result | Worked example |
|---|---|---|
| Ordinary pair avoidance | Baxter–Pudwell, [Propositions 5–7](https://arxiv.org/html/1406.4100v2), using PP03's audited bindings | Degrees 1–4 produce `(1,2,3,4)`, `(1,2,3,5)`, `(1,2,4,7)` for the three catalogued pairs. |
| Inversion sequences avoiding 201 and 210 | Testart, [Section 1.1 and Theorem 5](https://arxiv.org/html/2411.05726v3), with the proof and its preceding succession rule inspected | Degrees 0–7 produce `(1,1,2,6,24,116,632,3720)`. The degree-zero coefficient includes the empty word. |
| Fishburn-tree transport | Cerbai–Claesson, [Definitions 2.1/3.1, Proposition 4.4 and Corollary 4.5](https://arxiv.org/html/2211.07200v2), with inverse construction and proof inspected | At degree 4 there are 15 trees and 15 modified sequences; `(1,2,1,3)` maps to `(((None,1,None),2,(None,1,None)),3,None)`. Both sides have first/ascent-top positions `[1,2,4]`. |

Each row can be reproduced from the public checkout:

```python
from ac.research_benchmarks import run_case
for key in ('PP129-P5', 'testart-201-210', 'fishburn-inorder'):
    result = run_case(key, 4)
    assert result['status'] == 'finite_verified'
    print(result)
```

`benchmarks_v1.json` preserves exact forbidden patterns, conventions, start degree, zero degree offset, coefficient formula, expected counts, source links, reference algorithm, oracle, finite profiles, runtime caps and expected outcome. `source_reviews_v1.json` is a separate versioned review; earlier snapshots remain unchanged. Hash-bound loading prevents changed hypotheses from inheriting a source review. It is an explicit maintainer audit boundary, not cryptographic attestation of theorem truth.

## Independent checks

Ordinary benchmarks retain PP03's existing generators versus direct Cartesian membership and equality-sensitive matching. Inversion sequences use a new bounded, zero-based `InversionClass` adapter with position-dependent alphabets and existing classical-pattern compilation. Its independent oracle enumerates the full product of position alphabets and uses direct triple inequalities, including inequality of the last two values. A third calculation extracts exact rational coefficients from the published generating function; floating-point arithmetic is never used.

For Fishburn transport, the production side starts from existing modified-sequence generation and recursively splits at the leftmost maximum. The oracle independently enumerates decreasing labelled shapes, restricts left subtrees strictly, and tests node conditions. It does not derive trees from source words. Complete membership, duplicate generation, target membership, collisions, coverage, both inverse identities and statistic preservation are checked. Tree statistics use node topology, while word statistics use positions and adjacent comparisons. Exact coefficients of the cited Fishburn counting series provide an additional count check.

The oracles share problem definitions and expected statements, not enumeration or membership code. They can still share a human interpretation error. Every execution has `proof_status: not_proved`; passing results are `finite_verified`. Source review's `PROVED_EXTERNAL` remains a separate provenance statement. Nothing here establishes novelty or a new all-length proof.

## Quick, deep and recovery

Use the existing Python environment with no added dependencies:

```sh
# Default quick: 21 cells, degrees at most 4, one process at a time.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m ac.research_benchmark_runner

# Explicit deep: 32 cells, pair/tree degrees at most 6, inversion at most 7.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m ac.research_benchmark_runner \
  --profile deep --workers 2 --checkpoint .local-imports/pp04-run

# Repeat that command to resume. Optional deep pytest entry point:
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. PP_RI_DEEP=1 python -m pytest \
  -o addopts='' -q tests/test_research_benchmarks.py::test_deep_published_benchmarks
```

A subprocess enforces each catalogued wall-time cap (quick: 10s; deep: 60s). Timeout kills that worker and records `budget_exhausted`, never success. There are at most two workers. Maximum degrees bound the search space; retained comparison inputs are capped at 10,000 members. Memory is bounded by these problem-size limits, not an OS-level memory quota. No degree-11 enumeration runs in CI. Library `run_case` is synchronous and does not itself impose a wall-clock deadline; use the runner for enforced limits.

Checkpoint manifests bind the profile, Python/platform, entire public `ac` source fingerprint and audited datasets. Successful cells are reused; interrupted cells are rerun; failed attempts remain recorded (up to ten per cell). Atomic writes protect committed cells from a mid-write crash. A source/profile mismatch or checksum corruption requires inspection and a fresh directory; the runner does not repair it silently. Use one supervising invocation per checkpoint directory. Previously persisted `wall_seconds` remain the original execution timings after resume, not resume timings. No network, model-provider calls, random choices or automatic external transmission occur.

Checksums detect accidental corruption, not forged execution evidence. Checkpoints are local trusted-workspace artifacts, not proof certificates. Source changes require a fresh run. The suite's semantic outputs and task ordering are deterministic; wall-clock observations vary.

## Scope and next gate

This stage adds only the bounded implementations needed for published benchmarks. It does not introduce a general grammar searcher, Fishburn-matrix machinery, automated source retrieval, generalized inversion-family support in PP03, or a discovery orchestrator. PP05 and the deferred PP12 design remain separate stages. New benchmarks require audited source bindings and a genuinely independent validation route.
