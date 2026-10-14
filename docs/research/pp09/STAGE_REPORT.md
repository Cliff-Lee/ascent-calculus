# PP-RI-09 stage report — 2026-10-14

Repository: public `Cliff-Lee/ascent-calculus`, branch `codex/pp-ri-09`, starting commit `a5797331c67510f491378015df024df0dd487866`. Private `Cliff-Lee/ascent-calculus-research` remains clean at `f398f092ab1822a3bb8d0348d2363d671aa64be2`. This report is committed with the implementation; its containing commit identifies the delivered source.

## Delivered changes

Research Library and Benchmark / Method Explorer extend the existing Tk and browser workbenches. The shared model presents searchable records, exact citations, original imported annotations, source versions/hypotheses, method cards and mapped public capabilities. Eleven reviewed works are available without an import; the supplied 140-record ZIP is imported explicitly using the PP01 security/idempotence contract. Unreviewed metadata does not become a theorem.

Six fixed small references expose counts, recursive specifications, generating trees, pattern transport, recursive bijection and language/grammar equations. They retain exact finite coverage, independently implemented checks, generated structures, refuted attempts and proof obligations. Counterexamples navigate to the existing inspector with explicit alphabet conversion. Source claims, conjectures, bounded verification and formal status remain separate. No all-length proof or new theorem is claimed.

Added `ac/gui/research_library_model.py`, `research_jobs.py`, `research_panel.py`, `research_http.py`, `research_smoke.py`, browser `research.js`, resource adapter `ac/research_resources.py`, reproducible payload script, generated public-only `ac/research_data`, 16 acceptance tests and this documentation/evidence. Existing desktop/server/HTML/CSS, focused CI and three packaging scripts are extended. Seven mathematical integration modules change only resource resolution/source hashing to work outside a repository checkout. Original mathematical definitions and the 2122/2212 algorithm are unchanged.

## Architecture and operational choices

One widget-independent model and bounded job API serve both UIs. Optional mathematics loads only when a method is run. Spawned workers provide responsive cancellation and a 30-second limit; one active job and eight retained results bound workbench memory. Existing state remains separate from the new literature database. No runtime dependency was added, provider enabled, external data transmitted or private strategy code copied into public source.

The installed wheel/native bundle includes 37 allowlisted public reference/source records (263,056 bytes), with exact hashes and tests against canonical source. This solves the former repository-relative data requirement. Raw `.py` source records require explicit PyInstaller inclusion because its ordinary data collector omits Python files. They preserve implementation provenance and are not imported as an alternative engine.

## Validation actually executed

- Python 3.14.7: targeted GUI/model/job/resource tests **16 passed**, 1.09s; `evidence/targeted-pytest.txt`.
- Same environment: full suite **369 passed, 1 skipped, 1 expected duplicate-ZIP-fixture warning**, 52.28s; `evidence/full-pytest.txt`. Skip remains the existing opt-in deep benchmark.
- Tk-enabled Python 3.13.15/Tk 9.0: real mapped desktop journey with actual ZIP **passed**. Lazy initialization, 140 records, exact C-PP-129-6 citation, bijection degrees 1–4, zero-to-positive counterexample navigation and cancellation verified; `evidence/native-journey.json`.
- Local macOS arm64 development build, PyInstaller 6.22.3: existing startup check, existing window smoke and full research journey **passed**. Cancellation 0.0111s; complete research journey 0.569s; `evidence/native-build.txt`, `frozen-native-journey.json` and `packaging-summary.json`. Timings are local smoke observations, not performance guarantees.
- Wheel built and installed into an isolated target. Python isolated-mode check uses packaged resources rather than repository docs: eleven reviewed works and all six method results **finite_verified**; `evidence/wheel-build.txt`, `wheel-install.txt`, `installed-wheel.json`.
- Browser UI: actual work → citation → bounded bijection → generated derivation → faulty-inverse counterexample → existing positive inspector journey **passed**. Visible source `0,0` becomes `1,1`; `evidence/browser-inspector.png`. JavaScript syntax check passed.
- Original six external worktree heads/statuses, installed advanced executable hash and private checkout unchanged; `evidence/preservation.json`. Existing public core mathematical files unchanged.

Build-only tools were installed in a new ignored `public/.local-imports/pp09/build-env`, not existing research environments. The development app has its own name/bundle identifier and remains in ignored build output. No installed application or user data was replaced. No push, merge, release or private pin update occurred.

## Resolved failures and limitations

The first frozen worker journey failed because the desktop entry point lacked `multiprocessing.freeze_support()`. Source tests alone did not catch this. The guard and nonmodal smoke-error handling were added, the app rebuilt, and all three packaged checks passed. The first packaging attempt also exposed omitted source records; explicit inclusion fixes this and installed-resource checks cover it.

Only local macOS native packaging was executed. Windows/Linux scripts were updated but not run; hosted CI, signing/notarization, installers, clean-machine launch and the broader ADP full-application restoration/parity gates remain unverified. Wheel build emits setuptools namespace/data-directory warnings, although the installed payload and methods were validated. The existing Python 3.14 test environment lacks Tk; native checks use a separate available Tk-enabled interpreter. No new formal proof backend is introduced. Reference jobs are fixed bounded examples, not autonomous original-discovery campaigns; history is not durable. The broader installed private Workbench preservation gate remains distinct from this additive public interface gate.

## Gate and stop

**PP09 gate passed for the supported local macOS workflow:** complete native literature/citation/benchmark/structure/result/inspector journey, independent finite evidence, responsive cancellation, existing startup/window smoke and isolated wheel/frozen-resource checks. Platform/release limitations remain explicit.

**STOP. PP-RI-10 has not begun.** Next recommended slice is the private original-discovery/proof-assistance pipeline, pinned to this reviewed public commit and scoped to its reproducible altered-conjecture demonstration. PP-RI-12 cumulative discovery remains deferred until existing campaign gates and design review. No strategy-learning or major refactor was begun here.
