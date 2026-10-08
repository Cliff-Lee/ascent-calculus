# AM-Next campaign ledger

AM-Next is a gated research-engineering programme. A stage is complete only
when its implementation and evidence are committed and its exit checks pass.
Finite matches are always labeled with their tested range; only a general proof
can be labeled a theorem.

## Baseline and preceding campaign

- AM-N0’s existing-systems review and reproduction baselines are recorded in
  [`AM_N0_EXISTING_SYSTEMS.md`](AM_N0_EXISTING_SYSTEMS.md), with executable
  controls in `experiments/am_n0_baselines.py` and
  `tests/test_am_n0_baselines.py`.
- The preceding engine campaign’s latest reported milestone is E11c.2a1: its
  alternating M/O construction was exhaustively checked on 1,248,595 modified
  `2122`-avoiders through degree 11, with no failures, collisions, or missing
  targets. This remains bounded evidence; the all-degree proof is open. The
  historical one-pass repair is refuted at degree 11. GUI visual review and
  packaged Mac manual launch checks remain open in `STATUS.md`.
- This workspace did not contain usable Git history or a configured remote.
  The AM-Next work starts from local baseline commit `4dceba4` on branch
  `am-next`; `baseline/am-n0` points to the same snapshot. This records the
  actual starting files, not a reconstruction of upstream history.
- Baseline environment: Python 3.12.14 and Tkinter are available. `pytest`,
  Hypothesis, Z3, and PyInstaller are not installed in this environment. Native
  desktop source runs here, but release packaging is platform-specific.

## Mathematical contract (N1)

The versioned `ascent-machine-search-spec` separates a mathematical question
from its execution budget and worker checkpoint. Version 1 uses semantics
`ac-positive-cayley-v1`:

- **Ordinary ascent sequence:** a nonempty positive word with `x_1 = 1`; for
  every `i > 1`, `x_i <= 2 + asc(x_1,...,x_{i-1})`, where `asc` counts strict
  adjacent rises in that prefix.
- **Cayley word:** the set of used values is exactly `{1,...,max(x)}`. The
  empty word is Cayley at ambient height zero, though search windows in this
  specification begin at degree one.
- **Modified ascent sequence:** a Cayley word whose set of first-occurrence
  positions equals its ascent-top set.
- **Revised ascent sequence:** a Cayley word whose set of first-occurrence
  positions equals its ascent-bottom set.
- For nonempty words, the literature ascent-top and ascent-bottom sets each
  adjoin position 1. A strict rise `x_i < x_{i+1}` contributes top `i+1` and
  bottom `i`. Public positions are one-based.
- Pattern rules are classical subsequence patterns: select increasing
  positions, then standardize by the order and equality of selected values.
  Rules in one class are conjunctive (`avoid` or `contain`); rule order and
  duplicates do not change the class.
- The base-degree window is inclusive. A source is evaluated at `n + a` and
  the target at `n + b`, so the net map degree shift is `b-a`. Offsets change
  object length only; they do not shift values, pattern labels, or statistics.
- A count comparison checks cardinalities at every requested base degree. If a
  statistic is selected, it also compares its full value distribution. A
  profile comparison checks the full distribution of one registered statistic.
  A bijection-search goal describes the finite classes and degrees; the
  candidate grammar and computational budget are runtime settings, not part of
  the mathematical class definition.

The current specification supports ordinary, modified, and revised families
with finite conjunctions of classical pattern requirements. It does not yet
express arbitrary Boolean class formulas, structural predicates, or generated
block rules; those are later-stage work. The shared statistic registry keeps
the GUI and discovery records on the same identifiers and formulas.

Each spec serializes to JSON with an explicit format, schema version, and
semantics version. Its canonical SHA-256 fingerprint ignores the order and
duplication of conjunctive rules. Loading a different schema or semantics
version fails closed. A spec fingerprint identifies the question, not the
result, budget, engine build, or proof status; those belong in the research
dossier.

## Twelve subcampaigns and release gates

| Stage | Scope | Exit evidence |
|---|---|---|
| N1 | Formal mathematical search specification | Independent definitions, strict serialization, offset semantics, bounded production cross-checks |
| N2 | Persistent autonomous worker and checkpoints | Kill/restart recovery at a safe boundary, durable state and progress, deterministic resume test |
| N3 | Bounded conjecture discovery | Ranked candidates with counterexamples and exact finite evidence, not count-only noise |
| N4 | Structural fingerprints and invariant analysis | Independent feature calculations, useful discriminators, readable candidate explanations |
| N5 | Generative typed transformation language | Normalized, typed candidate programs generated beyond a fixed map list; safety and cost bounds |
| N6 | Automatic block-decomposition synthesis | Block boundaries and local rules synthesized systematically and auditable |
| N7 | Counterexample-guided synthesis | Failed candidates feed minimized witnesses back into search; replayable CEGIS trace |
| N8 | Avoidance classes and offsets | Search class families over supported pattern conjunctions and degree offsets with correct limits |
| N9 | Research memory and novelty | Canonical candidates/results, provenance, duplicate and near-duplicate detection |
| N10 | Investigate/Discover desktop experience | Responsive workflows for explicit tests and background discovery, interpretable traces |
| N11 | Research dossiers and exports | Self-contained exact specs, environment, bounds, candidates, failures, checkpoints, and proof obligations |
| N12a | Blind bounded rediscovery | Target map withheld; generated candidate and bounded search record |
| N12b | Independent held-out validation | Separate all-tuples enumeration on training and held-out degrees |
| N12c | Recovery and launch checks | Worker crash recovery, desktop startup, packaged and visual checks where available |
| N12d | Release decision | Explicit release-readiness decision with open platform gates |

Dependencies are enforced in order: worker/checkpoint primitives precede
autonomous search; generated transformation candidates precede CEGIS; class
generalization consumes the N5-N7 candidate model; canonical memory consumes
the versioned specs and candidate normal forms; UI and dossiers expose those
stable records; N12 validates the assembled workflow. A later interface cannot
mark an earlier mathematical or persistence gate as passed.

## Benchmark evidence labels

Every benchmark record must distinguish:

1. **Independent discovery:** the target recipe/map was withheld from synthesis
   guidance and generated by the search grammar.
2. **Reconstruction:** the search rediscovered an equivalent candidate using
   seeded operations or an exposed structural hint.
3. **Supplied verification:** a human supplied the map and the system checked
   it on finite sets.
4. **Enumeration only:** class counts or statistic distributions matched, but
   no object map was synthesized and checked.

Blind rediscovery targets include ordinary/modified/revised relationships and
the published block-based examples. Target code and recipes must not enter the
candidate generator for the independent-discovery runs. Separate enumeration
implementations and held-out degrees are required before interpreting a
candidate as robust computational evidence.

## Gate record: N1

**Status: passed; safe to begin N2.** The formal v1 spec, shared statistic
registry, and direct reference definitions are implemented. The independent
reference enumerator agrees with the ordinary, brute-force modified,
conversion-based modified, and revised generators through degree 5; pattern
predicates agree against explicit subsequence standardization through degree 4.
Canonical serialization, offsets, strict validation, class predicates, and
statistic identifiers have focused coverage in
`tests/test_am_n1_specification.py`.

Validation completed on 2026-10-08:

- `python -m compileall -q ac tests experiments` passed.
- The repository’s direct test-function harness passed **171 cases, 0 failed**.
  It supplied only `pytest.raises` and `pytest.mark.parametrize` compatibility
  for the plain test functions; this is not reported as a `pytest` run.
- The actual `pytest` command remains unavailable because pytest is not
  installed. No package installation was attempted.
- No platform package was built as part of N1.

N4-N12 have not passed their gates. The existing GUI’s finite experiment and
map-search functions remain useful, but they do not constitute a persistent
overnight discovery system. The campaign will report each gate separately;
there is no release status until N12’s required tests pass.

## Gate record: N2

**Status: passed; safe to begin N3.** A SQLite/WAL job store persists the
canonical N1 question, registered handler, progress, checkpoint, result,
failure detail, and transition events. A spawned worker process drains the
queue, sends heartbeats, supports pause/cancel at handler checkpoints, and
recovers/resumes jobs left by a terminated worker. The initial built-in handler
performs streaming finite enumeration, count comparisons, and selected
statistic-profile comparisons one base degree at a time. The desktop has not
been connected to this queue yet; that is N10.

Validation completed on 2026-10-08:

- `python -m compileall -q ac tests experiments` passed.
- Three targeted N2 cases passed, including terminating a real worker process
  after a committed checkpoint and resuming it in a second process.
- The repository’s direct test-function harness passed **174 cases, 0 failed**
  after N1 and N2 changes. As with N1, it is not reported as a `pytest` run;
  pytest is unavailable in this environment.
- `python -m ac.discovery.worker --help` passed without warnings.
- No platform package was built. Packaged multiprocessing needs Mac and
  Windows checks later in N12.

The worker is not yet an autonomous transformation-discovery engine. It can
persist and resume only tasks represented by registered handlers; N3 now adds
generated class-count discovery, and N5-N7 add generated maps and
counterexample-guided search. N4 may begin, with GUI and packaged-worker
verification still open.

## Gate record: N3

**Status: passed; safe to begin N4.** A versioned candidate-space spec now
generates all selected single-pattern avoidance and containment classes, then
searches count vectors across families and degree offsets. It reports exact
matches, initial matches with first differing count rows, ranking, tested
degrees, and candidate-pair budget exhaustion. The search runs in the N2 worker
and checkpoints at pattern-length boundaries.

The benchmark query over modified and revised length-3 avoiders at offset
`+2` independently selected the `111` pair with counts `(1, 2, 4, 10, 29)`
through base degree 5. A separate literal tuple enumerator checked the source
and target rows, including target degree 7. This is a **count conjecture**
rediscovery; the block transformation was not searched or discovered here.

Validation completed on 2026-10-08:

- `python -m compileall -q ac tests experiments` passed.
- Five targeted N3 cases passed, including queued execution by the registered
  worker handler and the `+2` rediscovery benchmark.
- The direct repository harness passed **179 cases, 0 failed** after N1-N3
  changes; pytest remains unavailable.
- The independent comparison search was run with the full selected length-3
  candidate catalogue and completed without exhausting its pair budget.
- No release package was built. The desktop does not yet expose this search.

N4 passed its gate as recorded below. N3 did not add objectwise maps; N5-N7
address generated transformation candidates and their validation.

## Gate record: N4

**Status: passed; safe to begin N5.** `ac/discovery/fingerprints.py` derives
new positions, ascent tops and bottoms, their overlaps, edge words, run
lengths, multiplicity profiles, and fibre gaps directly from values. It emits
readable one-based position traces and stable, semantics-versioned fingerprints.
Class profiling compares exact feature distributions and optional joint
profiles, with example words for every changed value. The same work is
available as a checkpointed persistent-worker job over degree offsets.

Validation completed on 2026-10-08:

- `python -m compileall -q ac tests experiments` passed.
- Six targeted N4 cases passed. The role sets agree with literal independent
  definitions on every positive word of degrees 1–4; tests cover class and
  joint distributions, visible classifications, count-match explanations,
  bounded profile memory, and the registered worker handler.
- The direct repository harness passed **185 cases, 0 failed** after N1-N4.
  It remains a compatibility harness rather than a pytest run.
- No package was built. Structural profiles do not generate an objectwise map;
  matching profiles remain equidistribution evidence only.

N5 passed its gate as recorded below. GUI and packaged-worker review remain
open for N10/N12.

## Gate record: N5

**Status: passed; safe to begin N6.** The new transformation-search
specification records source and target classes, offsets, grammar semantics,
selector and operation choices, and explicit selector, atom, cost, depth,
candidate, expansion, class-object, universe-enumeration, and map-evaluation
bounds. The worker generates normalized programs from a typed grammar and
checks whole finite class maps. The grammar combines established operations
with definition-driven sweeps over first/last occurrences, ascent/descent roles,
and run boundaries; it also generates Boolean selector combinations, selected
restrictions, existing-value insertions, and a new-maximum insertion rule.
Known degree effects prune incompatible programs; unknown effects are retained
for exact finite evaluation. Results include first failures, finite bounds,
proof obligations, and an explicit `not_proved` status.

Validation completed on 2026-10-08:

- `python -m compileall -q ac tests experiments` passed.
- Four targeted N5 cases passed, including fresh-maximum position-identity
  checks, strict specification round-trip, degree-shift type pruning, and a
  real spawned `search-transformations` worker that found the identity map and
  respected its work budget.
- The full direct repository compatibility harness passed **189 cases, 0
  failed** after N1-N5. This is not a pytest run; pytest remains unavailable.
- `git diff --check` passed. No platform package was built.

N5 does not claim grammar completeness. Its generated vocabulary does not yet
systematically synthesize block decompositions, use counterexample-guided
program repair, or search families of maps across classes and offsets. Those
are N6-N8. The worker's generated search is not yet exposed in the desktop UI
(N10), and blind map rediscovery and packaged-launch checks remain for N12.

## Gate record: N6

**Status: passed; safe to begin N7.** The block recipe grammar now synthesizes
boundary rules from increasing/decreasing/monotone runs, newness, ascent-top
and ascent-bottom roles, role changes, and equal values. It combines these
segments with value-dependency rules, stable/reverse/safe or feature-sorted
block orders, local reversal/complement/rotation/sorting, and new-maximum
extensions at block boundaries. Recipes retain their choices in a structured
record, preserve occurrence identities, and can emit one-based explanations
showing each position's roles, block dependencies, output order, and inserted
positions. The expanded generator is separate from the legacy 108-recipe
catalogue, and transformation grammar v1 specs remain loadable without gaining
the v2 block operation.

Validation completed on 2026-10-08:

- `python -m compileall -q ac` and `git diff --check` passed.
- Five targeted N6 cases passed, covering the generated recipe space, block
  traces and occurrence identities, dependency handling, finite whole-class
  map search, and v1 spec compatibility.
- `python experiments/am_n6_block_rediscovery.py` exhausted all 7,360
  generated +2 block recipes. Seventeen candidates matched modified
  `111`-avoiders at degrees 1–4 to revised `111`-avoiders at degrees 3–6; the
  known block recipe appears among them. This is explicitly a reconstruction
  from seeded operations, not blind rediscovery. Every match is marked
  `not_proved`.
- The full direct repository compatibility harness passed **194 cases, 0
  failed** after N1-N6. It is a compatibility harness, not pytest; pytest is
  unavailable. No package was built.

The expanded grammar is a finite, definition-driven vocabulary, not a claim
that it contains every sensible block transformation. N6 does not yet use
counterexamples to repair candidates or generalize successful maps over class
families and offsets. Those remain N7–N8; the interface and independent blind
validation remain N10–N12.

## Gate record: N7

**Status: passed; safe to begin N8.** Transformation search now maintains a
versioned counterexample suite. A fully evaluated candidate that is undefined,
maps a source outside the target, or collides contributes a replayable witness.
Before later candidates receive a full class-map pass, the worker tests them
against a bounded prefix of that suite; a replayed witness rejects the map
without enumerating its remaining source objects. Collision records preserve
both source words. Source witnesses are minimized by repeatedly lowering one
entry while the source remains in the specified class and the same-degree
failure remains. The reported minimality is explicitly local to this lowering
relation, not global minimality.

The suite is capped at 512 entries, and each candidate checks at most one
eighth of the total prepared source objects (with a minimum of one) before
falling back to full evaluation. Non-surjectivity-only failures do not create a
cheap source constraint and are counted separately. The CEGIS version, suite,
refinement trace, results, and counters are checkpointed together. Older v2
transformation checkpoints without CEGIS state restart candidate evaluation
from the beginning so their search history cannot silently omit witnesses.

Validation completed on 2026-10-08:

- Targeted N7 cases passed for local witness minimization, collision-pair
  replay, candidate screening, and deterministic checkpoint resume. The
  resumed result matched the uninterrupted exact candidates, near misses,
  trace, and candidate counts.
- The direct repository compatibility harness passed **197 cases, 0 failed**
  after N1–N7. It is not pytest; pytest is unavailable.
- The N6 +2 block-reconstruction benchmark still exhausted all 7,360 recipes
  and returned the same 17 finite matches after CEGIS was added.
- `python -m compileall -q ac tests experiments` and `git diff --check` passed.
  No package was built.

CEGIS accelerates rejection and produces replayable evidence within the
registered finite grammar; it does not synthesize arbitrary operations or
prove a general map. Independent blind rediscovery and held-out-degree checks
remain N12 requirements.

## Gate record: N8

**Status: passed; safe to begin N9.** A new persistent family-search job accepts
multiple exact class/offset scenarios that share one typed transformation
grammar. Its grid builder forms a bounded Cartesian scan across source classes,
target classes, and source/target offsets. It generates candidate programs by
degree-shift group, interleaves those groups so one offset cannot starve the
others, and evaluates each candidate against every scenario. Results rank
programs by how many scenarios they match, show per-scenario failures, and
identify candidates that pass every listed finite window.

The family spec has explicit scenario, enumeration, class-object, candidate,
and total map-evaluation limits. The SQLite worker route checkpoints candidate
progress and ranked results, can resume deterministically, and uses the same
class generator, offsets, transformation grammar, and finite-map evaluator as
single-question search.

Validation completed on 2026-10-08:

- Three targeted N8 cases passed: class/offset grid serialization, discovery
  of the identity map across ordinary and modified avoidance classes while
  exposing its failure at degree offset +1, deterministic checkpoint resume,
  and persistent worker dispatch through SQLite.
- The full direct repository compatibility harness passed **200 cases, 0
  failed** after N1–N8. It is not pytest; pytest is unavailable.
- `python -m compileall -q ac tests experiments` and `git diff --check` passed.
  No package was built.

This checks a user-selected finite matrix of avoidance classes and offsets; it
does not infer an infinite family of pattern classes or prove a map beyond the
listed bounds. General pattern-family inference remains an open extension.

## Gate record: N9

**Status: passed; safe to begin N10.** Completed transformation and
family-search worker jobs now write their result, provenance, normalized
program keys, and candidate observations to a separate durable SQLite research
memory. Candidate keys include the transformation grammar version and
normalized program representation. Exact candidates also carry a deterministic
fingerprint of their objectwise map on the tested source sets, allowing memory
to distinguish a repeated finite map from a different map that merely passes
the same test. Failed candidates can be grouped by matching failure
signatures.

Novelty labels distinguish a new transformation, a new application of an
already-seen transformation to a different question, a repeated program, a
repeated finite map, and a repeated finite failure signature. Run IDs are
idempotent, and the store exposes run history and candidate history. Worker
results include the memory write status; a memory-store error is visible while
the completed mathematical result remains available. Runs default to an
`unclassified_bounded_run` provenance label; the system does not infer whether
a candidate was independently discovered, reconstructed, or supplied by a
researcher.

The finite-map fingerprint and failure signatures describe only the recorded
finite computation. They do not establish semantic equivalence or a theorem.
Transformation normal forms are grammar-level canonical forms; two distinct
normal forms may still represent the same mathematical map.

Validation completed on 2026-10-08:

- Two targeted N9 cases passed, covering new/existing program classification,
  same finite-map detection, new-application detection, idempotent run IDs,
  candidate history, and repeatable finite-map fingerprints.
- The N8 persistent-worker test confirmed that a completed family search is
  automatically recorded in research memory. The full direct repository
  compatibility harness passed **202 cases, 0 failed** after N1–N9.
- The N6 reconstruction benchmark still exhausted all 7,360 recipes and found
  the same 17 finite candidates. `python -m compileall -q ac tests experiments`
  and `git diff --check` passed. No package was built.

## Gate record: N10

**Status: passed; safe to begin N11.** The desktop's primary navigation now
names the broader workflow “Discover” and links the existing quick Wilf count
scan to a persistent transformation-family campaign window. Researchers can
enter separate source and target pattern lists (including the unrestricted
class), select avoid/contain semantics, compare several degree offsets, and
bound generated program cost, composition depth, and candidate count. Each
campaign is stored through the SQLite job queue, runs in the persistent worker,
and can be paused, resumed, cancelled, refreshed, and inspected after restart.

The campaign view shows candidate coverage across scenarios, each scenario's
first failure, bounded sample applications and position/value maps, the
research-memory novelty summary, and durable checkpoint data. Sample previews
open in the existing transformation graph. Closing the desktop asks the worker
to stop at a checkpoint; if it cannot stop within the timeout, job recovery
marks the last run interrupted for later resumption.

Validation completed on 2026-10-08:

- Three targeted N10 cases passed for separate pattern/offset grids, invalid
  form input, and stored candidate map previews. All three N8 class/offset
  tests passed after restoring the generator exhaustion flag.
- The full direct repository compatibility harness passed **205 cases, 0
  failed** after N1–N10. It is a compatibility harness, not pytest; pytest is
  unavailable. `python -m compileall -q ac tests experiments`, the desktop
  `--startup-check`, and `git diff --check` passed.
- The environment has no display server, so interactive layout, click paths,
  and preview rendering still need visual review on a desktop. No package was
  built.

N10 connects the bounded search engine to the desktop. It does not broaden the
mathematical grammar beyond N5–N8, establish that a candidate is a theorem, or
remove the manual visual review required for release readiness.

## Gate record: N11

**Status: passed; safe to begin N12.** A versioned JSON dossier now exports
the exact canonical research question and its fingerprint, the explicit
ascent-sequence and pattern semantics, engine version and source revision,
runtime environment, planned and tested degree windows, grammar and budgets,
full finite result, proof status and obligations, durable worker checkpoint
and progress, and the job event history. This includes ranked candidates,
first failures, example transformation traces, and the research-memory record
when available. Dossiers can be exported while a campaign is paused or
interrupted, preserving its current checkpoint.

The reader validates the dossier schema, exact specification serialization,
question fingerprint, semantic-definition fingerprint, and registered search
specification format. File export writes a temporary sibling and atomically
replaces the destination after validation. The desktop Discover window exposes
the export action for a selected campaign.

Validation completed on 2026-10-08:

- Four targeted N11 cases passed for completed and interrupted jobs, saved
  checkpoints and events, atomic JSON round trip, changed-question and changed
  semantics rejection, and all four registered question formats.
- The full direct repository compatibility harness passed **209 cases, 0
  failed** after N1–N11. It is a compatibility harness, not pytest; pytest is
  unavailable. `python -m compileall -q ac tests experiments`, the desktop
  `--startup-check`, and `git diff --check` passed.
- Display-level export interaction and packaged application checks remain
  open because this environment has no display server or packager. No package
  was built.

N11 makes a bounded experiment portable and auditable. It does not turn finite
matches into theorems or verify a dossier's proof obligations automatically.

## Gate record: N12a–N12d

N12 is tracked as four smaller gates in
[`AM_N12_VALIDATION.md`](AM_N12_VALIDATION.md). N12a passed: a generated
selector-sweep search, without the named Hat map atom, found one ordinary to
modified finite map through degree 5. The separate all-tuples validator in
N12b confirmed it through held-out degree 7. The earlier `+2` modified/revised
block search is now correctly labeled a reconstruction from seeded operations:
its recipe catalogue includes the target map's block ingredients. Its
independent held-out audit retained three of twelve candidates at degrees 5
and 6.

The worker's real crash/restart test, desktop `--startup-check`, and worker
CLI help check passed in N12c. The full direct compatibility harness passed
**211 cases, 0 failed** after N12 changes. It is a compatibility harness, not
a pytest run; pytest is unavailable. `python -m compileall -q ac tests
experiments` and `git diff --check` passed.

N12d is complete as a release decision: **not release ready**. There is no
display server for interactive desktop review and no PyInstaller for a local
package build; packaged launch and multiprocessing still need platform checks.
No release is claimed. This closes the validation report while leaving those
release checks explicitly open.
