# AM-AI — Optional AI Assistance for Ascent Research

AM-AI adds an optional assistant for proposing experiments, organizing
computational evidence, and explaining results. It does not replace the
deterministic Ascent Calculus engine: class membership, transformations,
collisions, coverage, statistics, counterexamples, and tested bounds remain
engine-checked. Model output is always labeled unverified, and AI is disabled
when no provider is configured.

The first integration target is the user's Ollama API at `http://localhost:11434`.
The app connects only to a loopback endpoint, but Ollama can offload selected
cloud models; the UI must make that data path clear. Offline use remains a
complete supported mode. No candidate code from a model is executed.

## Subcampaigns

| Stage | Scope | Gate |
|---|---|---|
| AI1 | Provider-neutral interface, capability model, structured requests, cancellation, timeouts, safe errors, disconnected mode | Passed: ten offline fake-provider tests; no third-party dependency; all outputs unverified |
| AI2 | Ollama discovery and chat adapter | Offline adapter gate passed; live Ollama check on the target Linux machine remains |
| AI3 | Desktop settings and contextual assistant actions | In progress: explicit opt-in; endpoint/model status; explanations attached to selected experiment results |
| AI4 | Evidence-aware dossiers | Passed: exact request, model, response, and evidence hashes persist with the campaign and export separately from mathematical results |
| AI5 | Significance review | Passed: deterministic, explainable candidate triage with explicit score inputs, uncertainty, and dossier reproducibility |
| AI6 | Experiment designer | Passed offline gate: convert a research question into bounded, typed transformation-family search specs for deterministic evaluation |
| AI7 | Closed-loop refinement | Offline implementation gate passed: exact engine failures can guide a linked, bounded follow-up plan; never self-certify a claim |
| AI8 | Proof assistance | Organize proof obligations and candidate lemmas; preserve human review and separate proof text from machine verification |
| AI9 | Overnight research | In progress: resumable AI-assisted search/refinement loop, global candidate/time budgets, cancellation, exact round provenance; broader soak and target-machine validation remain |
| AI10 | Benchmarking, privacy, and release gate | In progress: AI10a offline paired-benchmark protocol and data-flow audit passed; live model comparison, target-Linux checks, and packaged release gate remain |

## AI1 — Provider architecture

**Status: passed.** The `ac.ai` package
defines provider descriptors and capabilities, model discovery and chat
contracts, text and JSON request modes, a thread-safe cancellation token,
normalized timeout/failure/response errors, a lazy in-memory registry, and an
`AIService` that works with no provider configured. Structured output is parsed
as JSON but is not thereby validated as mathematics or as a theorem. The
service labels every response `unverified`.

AI1 deliberately added no Ollama network calls and no desktop settings. AI2
provides that adapter, defaulting to the loopback endpoint. The adapter enforces
the request's timeout, cooperates with cancellation, and avoids exposing raw
transport details in user-facing errors.

Validation completed on 2026-10-08:

- Ten offline `unittest` cases passed. They cover disconnected mode, explicit
  registry selection, capability gating, JSON parsing, cancellation, timeout
  normalization, safe error text, and request bounds.
- `python -m compileall -q ac tests` and `git diff --check` passed.
- The environment has no `pytest`; no pytest run is claimed. AI1 makes no
  mathematical-engine or desktop changes, and no real provider was contacted.

## AI2 — Ollama loopback adapter

The adapter talks to Ollama's local `GET /api/tags` model-list endpoint and
streaming `POST /api/chat` endpoint. Streaming is consumed internally so a
cancel signal can close the active response. Structured requests pass a JSON
schema through Ollama's `format` field; Ascent Calculus still only verifies the
returned text's JSON syntax at this layer. The endpoint is restricted to
localhost/loopback, with `http://localhost:11434` as its default. The provider
does not start Ollama, pull models, or execute tool calls. Ollama Cloud models
can send prompts to remote inference even though the app connects to the local
API; model discovery reports remote metadata when Ollama supplies it.

Official references: [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md),
[structured outputs](https://ollama.com/blog/structured-outputs), and
[Ollama Cloud models](https://github.com/ollama/ollama/blob/main/docs/cloud.mdx).

**Status: offline adapter gate passed; target-machine check pending.** Six
mocked-transport tests cover `/api/tags`, streaming `/api/chat`, model selection
and absence, structured output, cancellation, and loopback-only transport
restrictions. The transport bypasses proxy settings and refuses redirects, so
the adapter itself stays loopback-only. The tests use no network because this build
environment blocks local socket binding. A real request to the user's Ollama
process still needs to be checked from the Ubuntu machine.

Validation completed on 2026-10-08:

- Six AI2 adapter tests passed; AI1 plus AI2 total **16 passing tests**.
- `python -m compileall -q ac tests experiments`, `git diff --check`, and the
  desktop `--startup-check` passed.
- `pytest` is not installed, and the live Ollama process is not available in
  this container. These limitations are not represented as passing checks.

## AI3 — Desktop settings and contextual review

The Discover window now exposes an **Ollama · Off** settings control and a
candidate-specific **Ask Ollama** action. Settings are opt-in and saved locally
without credentials. Model discovery runs only after the user clicks its
button; requests run in a worker thread with a cancel action. The assistant
receives the exact search specification plus a bounded candidate summary and
selected counterexample data. Its response is shown as unverified and does not
change the saved conjecture or campaign.

The endpoint is loopback-only, but a local API does not guarantee local
inference: Ollama Cloud models can offload prompts. The model selector shows
remote metadata when Ollama provides it and warns when the selected model is
cloud or its inference location is unknown.

**Status: implementation added; desktop visual review pending.** Settings
round-trip, disabled defaults, local endpoint validation, protected file
permissions, and bounded evidence packets have focused offline tests. The
window cannot be visually exercised in this headless container. The target
Linux desktop should confirm the layout and make one request using a local
model such as the user's `qwen3.5:9b` before AM-AI3 is marked fully passed.

Validation completed on 2026-10-08:

- Four AI3 settings/context tests passed; AI1–AI3 total **20 offline tests**.
- `python -m compileall -q ac tests experiments`, `git diff --check`, desktop
  `--startup-check`, and worker `--help` passed.
- Ubuntu 24.04 amd64 package `0.1.0a28` built. Its metadata and dependencies
  were checked, packaged startup self-check passed after extraction, and the
  launcher and desktop entry were present.
- The package has not received a visual window review or a live Ollama request
  in this headless environment. The Ubuntu machine's UI and local model check
  are the remaining AI3 gate.

## AI4 — Evidence-aware assistant dossiers

**Status: offline data and dossier gate passed.** Each successful assistant
review is saved in the local research-jobs database for its campaign. The
record includes the exact system and user messages, bounded evidence packet,
provider and endpoint, requested and reported model, known inference locality,
request parameters, timestamps, response text, and separate SHA-256
fingerprints for the request and evidence. The response remains explicitly
`unverified` and is stored separately from the deterministic finite result.

Version-2 dossiers introduced saved assistant reviews beside the ordinary
mathematical result. Version-1 dossiers remain readable. Review records are
written only after a successful, explicit Ask action; failed and cancelled
requests are not recorded. The settings screen and review dialog state that
successful reviews are retained locally and included in dossier exports.

Validation completed on 2026-10-08:

- Two AI4 tests passed for durable local storage, dossier round-trip, legacy
  version-1 reading, request/evidence integrity, and the unverified status.
- The combined AI1–AI4 suite has **22 passing offline tests**; four existing
  AM-N11 dossier tests also passed when invoked directly.
- `compileall`, desktop `--startup-check`, worker `--help`, and
  `git diff --check` passed.
- Ubuntu 24.04 amd64 package `0.1.0a29` built; metadata and dependencies
  were checked, and packaged startup self-check, worker help, launcher, and
  desktop-entry checks passed after extraction.
- The live Linux window and Ollama request are still untested here; AI3's
  target-machine visual and provider check remains open.

## AI5 — Explainable research-priority review

**Status: deterministic ranking and dossier gate passed.** Discover now sorts
candidate transformations by an explicit priority rubric and shows the score,
component breakdown, reasons, and missing evidence for the selected candidate.
The optional Ollama explanation receives this review as context. It cannot
change the score or mathematical result.

| Component | Weight | Rule |
|---|---:|---|
| Finite match coverage | 40 | Matched selected scenarios divided by all selected scenarios |
| Family and offset breadth | 20 | Ten points for coverage of distinct source/target family pairs and ten for distinct offset pairs |
| Tested degree coverage | 15 | Average fraction of each planned degree window checked |
| Program simplicity | 15 | Linear preference for lower transformation cost within the configured maximum |
| Research-memory novelty | 10 | New transformation 10; new application 8; same finite map 4; same failure signature 2; exact duplicate 0 |

The sum is out of 100. Missing components are marked unavailable and not
renormalized; the score reports signal completeness separately. Candidate
ordering breaks ties by lower cost and then program text. “Confidence” describes
completeness of score inputs only. The UI and dossier state that this is triage,
not a probability of truth, proof, or publication value. The rubric version and
recomputed candidate scores are stored in version-3 dossiers; versions 1 and 2
remain readable.

Validation completed on 2026-10-08:

- Four AI5 tests passed for deterministic ordering, finite evidence reasons,
  novelty contribution, missing-signal uncertainty, and tamper-checked dossier
  reproduction.
- The combined AI1–AI5 suite has **26 passing offline tests**; four existing
  AM-N11 dossier tests also passed when invoked directly.
- `compileall`, desktop `--startup-check`, worker `--help`, and
  `git diff --check` passed.
- Ubuntu 24.04 amd64 package `0.1.0a30` built. Package metadata, extracted
  startup, worker help, launcher, desktop entry, and six AI4/AI5 tests against
  the extracted package passed.
- The live Linux window and real Ollama request remain the open AI3 gate.

## AI6 — Bounded experiment designer

**Status: implementation and offline validation passed; target-desktop review
pending.** Discover now offers **Design experiment…**. After explicit Ollama
opt-in, a researcher can describe a question and request a typed proposal for
the current transformation-family workflow. The scope is intentionally
specific: ordinary/modified/revised source and target families, avoidance or
containment classes, source/target degree offsets, base-degree window, and
finite transformation-search budgets. Each listed pattern represents a
separate class choice; classes and offsets make a Cartesian scenario grid.
Questions outside this scope are identified without applying a plan.

The response must match a closed JSON schema. Local validation then checks the
families, pattern syntax, distinct offsets, supported degree and grammar
bounds, and the 32-scenario maximum before constructing a
`TransformationFamilySearchSpec`. The model cannot supply a transformation
program or execute code. **Use this design** only fills the existing controls;
the researcher reviews or edits them and presses **Start campaign** separately
to run the deterministic worker. A finite match remains evidence through the
tested bound, not a proof.

When the researcher starts a campaign from an accepted proposal, job options
retain the research question, endpoint, model and known inference locality,
request prompts and parameters, exact structured response, normalized typed
specification, and both proposed/applied fingerprints. The dossier records
whether the controls were used as proposed or edited after proposal. These
fields remain separate from the worker's deterministic mathematical result.

Validation completed on 2026-10-08:

- Six AM-AI6 tests passed for grid construction, exact prefilled-spec
  reconstruction, out-of-scope behavior,
  strict schema and budget rejection, persisted job/dossier provenance, and
  edited-after-proposal labeling. The combined AM-AI1–AI6 suite has **32
  passing offline tests**.
- `python -m compileall -q ac tests experiments`, `git diff --check`, and the
  packaged desktop `--startup-check` and worker `--help` passed using the
  available Python runtime with Tk. The extracted package's AM-AI1–AI6 tests
  also passed against the packaged application code.
- Ubuntu 24.04 amd64 package `0.1.0a31` built; package metadata, launcher and
  desktop entry were inspected. The container's `/usr/bin/python3` lacks
  `python3-tk`, so the actual Debian launcher could not run here; the package
  correctly declares `python3-tk` as a dependency. Full unittest discovery
  also cannot import eight existing pytest-based modules because pytest is not
  installed in this environment.
- No live Ollama request or visual Linux desktop review was possible here.
  The target Linux machine still needs to verify the layout and a proposal
  using a local Ollama model. This remains the open AI3 desktop/provider gate
  and the AI6 acceptance check.

## AI7 — Counterexample-guided follow-up experiments

**Status: implementation and offline validation passed; target-desktop and
live-model review pending.** A selected candidate with recorded engine failure
evidence now offers **Refine from failure…**. The assistant receives the exact
parent search specification, selected candidate program, and a bounded set of
engine-generated failure records. It must cite existing failed scenario
indices and propose a different typed search specification. Local validation
checks the citations, evidence fingerprints, closed response shape, supported
class/pattern/offset controls, and existing degree and budget limits.

The researcher reviews the returned interpretation, cited failures, and
proposed control change. **Use this design** only fills the existing form; the
researcher can edit it and must press **Start campaign** separately. The
follow-up dossier retains the parent job, parent specification and candidate
fingerprints, exact witness packet, model request and response, cited scenario
indices, and proposed/applied specification fingerprints. A follow-up result
therefore remains linked to the evidence that motivated it.

This stage proposes another bounded search. It does not modify or repair the
candidate map, automatically run the next campaign, turn a failure explanation
into a theorem, or certify a conjecture. AI analysis and every proposed
control change are explicitly unverified; only the deterministic engine
produces the next finite result.

Validation completed on 2026-10-08:

- Four AI7 tests passed for exact witness capture and hashing, valid failure
  references, rejection of nonexistent or duplicate references, no-op plan
  rejection, tamper detection, and dossier lineage with edited-after-proposal
  status. The combined AM-AI1–AI7 suite has **36 passing offline tests**.
- `python -m compileall -q ac tests` and `git diff --check` passed.
- Ubuntu 24.04 amd64 package `0.1.0a32` built; metadata, extracted packaged
  desktop `--startup-check`, worker help, and inclusion of the new refinement
  module passed. The actual Debian launcher remains untested because the
  container's `/usr/bin/python3` has no `python3-tk`.
- AM-N pytest-based modules could not be executed because pytest is not
  installed in this environment. No live Ollama request or visual Linux
  desktop review was possible; those remain target-machine checks.

## AI8 — Proof-plan assistance

**Status: implementation and offline validation passed; target-desktop and
live-model review pending.** The Discover candidate panel now offers **Build
proof plan…** for a selected generated map. The request contains the exact
bounded candidate record and the deterministic engine's proof obligations.
The assistant can organize them into proposed main claims, intermediate
lemmas, case splits, inverse formulas, and induction hypotheses. Every step
must cite one or more supplied obligation IDs, and every obligation must be
covered.

Local checks bind the response to a fingerprint of the exact candidate
evidence, reject unknown obligation references, and check that the proposed
step dependencies form an acyclic graph. These checks do not validate the
mathematics. The interface labels the full outline **AI-proposed · unverified**
and keeps the candidate's proof status `not_proved`. The plan is not saved
automatically: the researcher reviews it and selects **Save plan to dossier**.
The saved assistant review includes the exact prompt, context, schema text,
model response, and provenance, and dossier validation still prevents it from
changing the mathematical result or proof status.

Validation completed on 2026-10-08:

- Four AM-AI8 tests passed for obligation coverage, rejection of unknown
  references, dependency-cycle detection, evidence-fingerprint integrity,
  explicit unverified labeling, and JSON-mode review persistence. The combined
  AM-AI1–AI8 suite has **40 passing offline tests**.
- `python3 -m compileall -q ac tests experiments`, desktop `--startup-check`,
  worker `--help`, and `git diff --check` passed.
- `pytest` is not installed in this environment; pytest-based suite modules were
  not run. AM-AI8 does not change the mathematical engine.
- Ubuntu 24.04 amd64 package `0.1.0a33` built; the package metadata and
  extracted startup checks are recorded with this campaign. A live Ollama
  request and visual desktop review on the target Linux machine remain pending.

## AI9a — Resumable overnight search/refinement loop

**Status: implementation and offline validation passed; AM-AI9 remains open.**
The Discover workflow adds **Run overnight with AI…**. It starts from the
currently selected class, pattern, offset, degree, and grammar controls, then
runs the same deterministic transformation-family worker used by ordinary
campaigns. When a completed round contains an exact engine failure, the worker
can ask the configured Ollama model for a bounded follow-up class/offset/degree
experiment. The response must pass the existing typed experiment and failure
reference validators before the next deterministic round is launched.

Each job is resumable from SQLite. It checkpoints the active search, completed
rounds, pending refinement request, and any structured model response before
applying it. A response already saved before a pause or process restart is
reused without another model call. Pause and cancel are checked while Ollama
is streaming; the provider request is interrupted promptly. The UI exposes
limits for refinement rounds, total candidate programs, and elapsed hours. The
elapsed limit includes paused time. Per-round finite results are stored in
research memory under the exact round specification, not misattributed to the
root question.

The dossier indexes every applied round specification and preserves each
search result, the exact prompt, structured response, failure context,
validation result, and applied-spec fingerprint. Invalid, unsupported, or
out-of-budget proposals stop the campaign with an interpretable reason. Every
result remains `not_proved`; AI output is recorded as unverified. The supported
refinement grammar changes class patterns, degree offsets, tested degree
windows, and finite budgets. It does not yet synthesize new transformation
program operations or block schemas.

Validation completed on 2026-10-09:

- Nine offline AM-AI9 tests passed, covering strict budgets and loopback-only
  endpoints, two-round search/refinement, persisted-response reuse after pause,
  interruption of an in-flight model request, exact-match early exit, rejected
  proposal handling, partial-budget checkpoints, SQLite crash recovery without
  a duplicate model request, and dossier preservation of every round's
  specification.
- All **49 AM-AI1–AI9a offline tests** and all **52 repository unittest tests**
  passed. `compileall`, desktop `--startup-check`, worker `--help`, and
  `git diff --check` passed.
- Ubuntu 24.04 amd64 `.deb` and wheel `0.1.0a34` built. The extracted package
  passed the desktop startup check, worker help check, and overnight-handler
  import check. The `.deb` SHA-256 is
  `11eedf6ca3ad0492c8c5c53b098ccdaf08685705af5c3e8c4c7b223227082aec`.
- This container has no display server or `xvfb-run`, so the desktop window
  could not be visually reviewed here. Live Ollama operation and visual review
  on the target Linux machine remain untested. AM-AI9 still needs overnight
  soak/recovery testing and AM-AI10's independent benchmark, privacy, and
  release gate.

## AI10a — Paired benchmark protocol and privacy inventory

**Status: offline implementation gate passed; AM-AI10 remains open.** The new
`experiments/am_ai10_benchmark.py` accepts an exact transformation-family spec,
an overnight campaign report, or an exported research dossier. It always runs
a deterministic baseline first. The default path is offline and does not
construct an Ollama provider. `--with-ai` is an explicit opt-in that runs the
same root question through the bounded overnight workflow using a named model.

Both arms have the same total candidate cap. The baseline may spend the full cap
on the original specification; the guided arm starts at the specification's
own candidate budget and may spend the remainder on locally validated follow-up
specifications. The report separates candidate counts and wall time, records
both complete finite results and model locality, and compares exact map/scenario
matches using a scenario fingerprint that omits operational budget fields but
retains the classes, offsets, degree window, and transformation grammar. It
compares retained exact-candidate records and reports total exact-candidate
counts separately. It does not collapse results into a claim that the assistant
found the “best” transformation. Every record says `proof_status: not_proved`.

The data-flow inventory is in `docs/AM_AI_DATA_FLOW.md`. The runner stores no
credentials, validates loopback-only routing through the existing Ollama
adapter, and exports prompts/responses as part of the paired report when AI is
enabled. A loopback API can still use a cloud model; locality must be selected
or recorded as unknown.

Offline validation completed on 2026-10-09:

- Six AM-AI10 tests passed for exact spec/dossier loading, offline provider
  isolation, explicit model selection, candidate-cap comparison, stable
  scenario matches across different compute budgets, and paired-result
  classification.
- The AM-AI1–AM-AI10a suite passed **55 tests**. The supported repository
  `unittest` suite passed **58 tests**; eight existing pytest-dependent modules
  were excluded because pytest is unavailable in this environment.
- `experiments/results/am_ai10_identity_control.json` records a positive
  identity-map control: 8 candidates tested, 3 exact finite maps, through the
  two same-class windows at offsets `(0,0)` and `(1,1)`. This is a harness
  control, not a new mathematical discovery.
- `experiments/results/am_ai10_refinement_challenge_baseline.json` records the
  deterministic arm for modified `111`-avoiders versus revised `111`-avoiders,
  with offsets `(0,0)` and `(0,+2)`: 24 candidates tested, no exact map, and
  candidate space not exhausted. Its root spec cap is 12, leaving the paired
  AI arm up to 12 candidates for a validated follow-up under the same total
  cap of 24.
- `compileall`, benchmark `--help`, JSON parsing for both recorded results, and
  `git diff --check` passed. A raw `unittest discover` still cannot import the
  eight pytest-dependent modules here; they are not counted as passing.

Linux package check on 2026-10-09:

- `scripts/build_ubuntu.sh` built the Ubuntu amd64 `.deb` and wheel as version
  `0.1.0a34`. The package metadata includes `python3-tk`.
- After extraction, the packaged desktop `--startup-check` and worker `--help`
  passed with the available runtime Python, and the launcher and desktop entry
  were present. The container's `/usr/bin/python3` lacks `tkinter`, so the
  system-interpreter launcher could not be exercised here; an installed target
  should receive Tk through the declared package dependency.
- This checks package construction and payload, not a visible desktop launch on
  the target Ubuntu machine.

To run the paired challenge on the Ubuntu machine, after confirming the model
is local in Ollama, use:

```bash
python3 experiments/am_ai10_benchmark.py \
  --spec experiments/benchmarks/am_ai10_refinement_challenge.json \
  --candidate-budget 24 --with-ai --model qwen3.5:9b --model-locality local \
  --max-refinements 1 --max-wall-seconds 3600 \
  --output experiments/results/am_ai10_refinement_challenge_paired.json
```

That live paired result, an overnight soak on the target Linux machine, the
visual desktop review, and the packaged-launch gate remain pending. The
identity control stops before an AI call by design; use the challenge fixture
for a refinement comparison.
