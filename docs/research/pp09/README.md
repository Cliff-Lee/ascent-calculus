# PP-RI-09 Research Library and Method Explorer

The existing desktop and browser workbenches now connect reviewed literature to the public reference mathematics of PP03–08. No model provider or external retrieval is needed.

## Research journey

1. Start `python -m ac.gui.desktop` with a Tk-enabled Python, or `python -m ac.gui.server --port 8799` and open the local browser workbench.
2. Open **Research Library**. Eleven reviewed works are available offline. Import the supplied conference ZIP explicitly to search all 140 annotations; ingestion uses the existing secure, idempotent importer.
3. Search by method/family/relevance, author, year or priority. Select PP-129 and review its exact citations, source versions, hypotheses and mapped capabilities.
4. Choose **Recursive bijection to tilings** and run the small reference. The output shows complete tested degrees 1–4, independent checks, a recursive derivation, a faulty-inverse counterexample and remaining all-length obligations.
5. Open the counterexample in the existing inspector. Source word `0,0` becomes positive engine word `1,1`; the conversion is displayed explicitly.

Native controls support keyboard focus, Return search and Escape cancellation. Runs occur in a spawned process with a 30-second limit, one active job and an eight-job in-memory history. Cancel terminates the worker. History is deliberately not a persistent autonomous campaign store.

## Contracts and extension points

- `research_library_model`: read-only catalogue access, reviewed source details, fixed method cards and precise status rendering shared by both interfaces.
- `research_jobs`: bounded deterministic reference dispatch and detached results; mathematical modules stay independent of widgets.
- `research_panel` / `static/research.js`: presentation and navigation into existing inspectors.
- `research_http`: validated local JSON commands. Research POSTs reject mismatched browser origins; ZIP imports retain the existing member/schema/size checks.
- `research_resources`: repository or packaged reference-resource resolution. `scripts/prepare_research_data.py` records the exact public definitions, source reviews and implementation hashes needed by installed builds.

The SQLite library is a new `pp-research-library.sqlite` beside the existing research state file. `ASCENT_ENGINE_DATA_DIR` chooses an isolated directory; existing saved state is not migrated. Import is user-directed. Citation links open only when selected by the researcher.

Published/source-reviewed claims are separate from local conjectures and finite verification. Unreviewed imported annotations remain `CATALOGUED_UNVERIFIED`. `PROVED_EXTERNAL` describes the inspected source claim, not formal verification of our implementation. No reference job produces a formal-kernel proof flag. The model defines separate descriptions for `PROOF_ATTEMPT` and formal proof; no placeholder proof attempt is invented.

## Reproducible native acceptance

Use Tk-enabled Python 3.13, a supplied pack and disposable directories:

```sh
ASCENT_ENGINE_DATA_DIR=.local-imports/pp09/example-state ASCENT_ENGINE_LOG_DIR=.local-imports/pp09/example-logs python -m ac.gui.desktop --research-smoke-check --research-pack .local-imports/pp-ri/source-pack.zip --research-smoke-output .local-imports/pp09/example-journey.json
```

The mapped-window check imports the actual 140-record ZIP, selects a citation and method, waits for independent finite evidence, opens the counterexample and checks cancellation. It exits after validation. Ordinary launch does not run these checks.

Prepare the allowlisted payload before building a wheel/native bundle. Source snapshots in `ac.research_data` are provenance records, not a second implementation; tests require byte-for-byte agreement with canonical public source. The conference ZIP and private artifacts are excluded. This stage builds a local macOS development app only; it does not install or release it.
