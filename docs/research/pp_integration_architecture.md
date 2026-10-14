# PP-RI-00 / PP-RI-01 integration architecture

Scope: inventory, ingestion and research-lead retrieval only. PP-RI-02 and all mathematical-method implementations are stopped until a separate request. The supplied campaign `codex_PP_resarch.md` was inspected as reference material; its stage descriptions guide this implementation. Its embedded paste-ready instructions are not separate user commands.

## Baseline and ownership

Public repository: `Cliff-Lee/ascent-calculus`, starting commit `56daddb044f9ea775e492badbd60e689440c971b`, clean detached checkout before creating `codex/pp-ri-00-01`. Python >=3.11, setuptools build, pytest/hypothesis development tools; optional Z3. Both native Tk and browser workbenches already exist. The release workflow runs cross-platform focused regressions, native smoke checks and packaging.

The independent private companion consumes a pinned public engine. It owns unpublished experiments, candidate invention, dossiers and durable research jobs. The present registry does not require private imports, alter the pin or transfer private experiments into public data. A future private integration consumes `ac.research_library` after a deliberately reviewed dependency update; no premature pin promotion is performed here.

Existing public owners remain authoritative:

| Interface | Existing source | Integration boundary |
|---|---|---|
| Word/types/scope | `ac.core.word`, `ac.core.typed`, `ac.core.scope` | No new mathematical definitions |
| Universe generation | `ac.generate.universes` | No generator changes |
| Pattern compiler | `ac.patterns.classical`, `general`, `constraints` | No avoidance semantics changes |
| Transforms/search | `ac.algebra.transforms`, `ac.discovery`, `ac.transform` | No registry changes, especially 2122/2212 |
| UI models/state | `ac.gui.viewmodel`, `experiments`, `research_state` | Preserved; no GUI integration in these stages |
| Research lead metadata | new `ac.research_library` | Independent stdlib-only SQLite registry |
| Future verified evidence | later provenance/claim layer | No theorem extraction in PP-RI-01 |
| Future structural strategies | existing discovery interfaces, later adapters | Requires reviewed sources and separate stage gates |

README, pyproject, source trees, tests and CI were inspected in both repositories. The private README's historical pin differs from the current pyproject/package lock; runtime lock and source-contract verifier remain authority, not README prose. Existing ADP preservation blockers remain independent of these metadata stages.

## Data flow and trust

`explicit local ZIP -> bounded in-memory reader -> strict input validation -> atomic dedicated SQLite transaction -> read-only detached records -> future method selection`.

The archive is never extracted or executed. Exactly the two known members are allowed; duplicate/absolute/traversal/extra entries, symlinks/devices/directories, encryption, unsupported compression, excessive expansion, corrupt UTF-8/JSON, duplicate keys and nonfinite numbers are refused. Archive and member sizes are bounded. A supplied expected SHA-256 is checked before any database access. Schema validation requires exactly 140 unique IDs with the observed fields. Original URLs are locators only: no retrieval occurs.

There was no formal JSON Schema in the pack. `pp_catalogue_input_v1.schema.json` documents its observed input contract. The stdlib validator additionally enforces unique IDs, real dates, no credentialed/non-HTTP(S) URLs and no boolean years. Unknown fields require deliberate schema evolution; they are not silently dropped.

Each pack stores original ZIP bytes, catalogue bytes and audit bytes unchanged, keyed by the archive SHA-256. Record source fields remain immutable under this API. An import timestamp is recorded once in UTC and preserved on repeat imports. Each result carries archive/member/record identity and a canonical record digest; `source()` returns exact original bytes and `metadata()` returns the original envelope metadata.

`BEGIN IMMEDIATE` serializes concurrent writers and rolls back incomplete imports. Same-pack repeats verify stored originals and add no records. Changed packs form separate immutable versions rather than overwriting older records; consumers should select a pack explicitly when multiple versions exist. IDs are scoped by pack hash. Foreign databases are rejected using application ID/version/table checks; no jobs or existing literature database is migrated.

## Search and status contract

`Catalogue.search` combines filters with AND: method (original proposed module), keyword-derived family, relevance, author, association year, priority, source type, ID, pack, literal free text and verification status. Ordering is deterministic by pack and original ID. Author/text matching uses Unicode case folding and accent decomposition; raw author strings are preserved and not ambiguously split into invented people.

Family tags are versioned keyword indexes of title/module/relevance, not verified mathematical classifications. Every record is `CATALOGUED`, `imported_annotation_unverified`, with proof status `not_assessed`. Original evidence notes such as “verified title” do not raise this status. Unknown/stronger verification-status queries are refused. These are 140 research leads, not 140 theorems.

JSON exports preserve all source fields and provenance. CSV is a deterministic readable view; leading formula characters are escaped to prevent spreadsheet interpretation. JSON/source bytes remain the lossless interchange. Export does not invent theorem numbers, assumptions, DOIs, licences or access history.

## Dependencies, storage and public/private separation

Only Python stdlib (`zipfile`, JSON, SQLite, Unicode, hashing, CSV) is used. The module does not import mathematical engines, UI, symbolic software, model providers or networking. Optional packages and future source retrieval are outside scope.

Default example staging is `.local-imports/pp-ri/`, ignored by Git. Raw packs and databases are not committed or included in releases. Tests use a synthetic 140-record pack when no researcher-supplied local pack is present; the actual supplied pack was separately exercised. No source-paper redistribution is performed. Rights/licences for future retrieval and software reuse require PP-RI-02 review.

## Validation limits and stop gate

Focused security/round-trip/export tests, synthetic offline tests and public regression tests accompany this change. Native window and packaging acceptance are separate: the main test interpreter lacks `_tkinter` and setuptools build backend. Tcl is available in the system interpreter, but that does not certify the native app or installer. Existing GUI model tests run in the public suite; installed apps remain untouched.

Gate results and exact commands are in `pp_stage_report.md`. No implementation of trees, bijections, automata, proof search or source retrieval occurs in these stages.
