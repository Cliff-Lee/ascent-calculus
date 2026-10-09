# Ascent Calculus (AC)

**Alpha research software for exploring ascent sequences and their transformations.**

AC is a Python calculus and a research engine for ordinary, modified, and revised
ascent sequences. Its default screen is a conjecture tester; specialist views let a
researcher inspect a word, follow engine-generated
transformations, and test conjectures on finite ranges. It is experimental software:
finite verification is evidence, not a proof of a general theorem.

> **Alpha status:** the GUI is a research prototype and the API and interface may change.
> The original one-pass `GapSwapRepair(2,1)` candidate is refuted at degree 11. The
> newer alternating M/O construction is exhaustively verified through degree 11, but
> its general termination, target-preservation, and bijection proof remain open. The
> workbench labels bounded success as
> **VERIFIED THROUGH `n=k`**, never **PROVED**.

## What you can do

- **Inspect a sequence:** view positions, values, stable occurrence IDs, first
  occurrences, ascent tops and bottoms, defects, runs, multiplicities, fibre gaps,
  and `2122`/`2212` orientation. Select a position to see why it has each role.
- **Learn the vocabulary:** start with a guided introduction to ordinary ascent
  sequences, ascent tops and bottoms, and the engine's modified/revised definitions.
  Hover or keyboard-focus underlined terms for definitions; try a word to get live
  classifications from the Python engine.
- **Trace a transformation:** step through the original engine-backed
  `ExtremeGapSwap → CanonicalRepair` construction and inspect its states, defects,
  blocks `A` and `B`, repair interval, potential, and local certificate. The trace is
  explicitly marked as the historical one-pass rule; the alternating M/O candidate is
  not yet wired into this screen.
- **Build a bounded experiment:** drag a sequence family, an Avoid/Contain rule, and
  Cayley patterns into either comparison lane; or use the ordinary controls and edit the
  pattern list directly. The sentence below the builder restates the exact question
  before it runs. Count one class or compare two, choose a degree range, then optionally
  compare a statistic or apply a structural filter.
- **Start with a conjecture:** the app opens directly in the experiment builder. Drag a
  pattern chip into either family, or drop a `.txt`, `.csv`, or `.json` file containing
  patterns (one per line, or a JSON array / `{ "patterns": [...] }`). Inspect, trace, and
  evidence views stay available from the compact tool bar.
- **Reproduce pattern comparisons:** the builder can express questions such as modified
  `2122`-avoiders versus modified `2212`-avoiders, or revised `3121`-avoiders at degree
  `n+1` versus ordinary `221`-avoiders at degree `n`, without dedicated GUI commands.
- **Scan for Wilf matches:** search all Cayley avoidance patterns of a selected length
  between two families, including degree shifts from `−2` to `+2`. The catalogue reports
  the full tested count vectors and first divergence, then opens any selected pair in the
  conjecture tester. Pattern length and degree bounds keep the scan finite and responsive;
  a count match is not a bijection.
- **Queue a bounded class-count discovery:** the Python engine can generate and compare
  all selected Cayley pattern avoidance and containment classes across sequence families
  and offsets, rank exact/prefix count matches, and retain first count counterexamples.
  `docs/AM_NEXT_CONJECTURE_SEARCH.md` documents the current search grammar and worker API;
  this search is not exposed in the desktop interface yet and does not synthesize maps.
- **Compare structural invariants:** profile the distributions of `new`, `asctop`,
  `ascbot`, ascent runs, multiplicities, and fibre gaps across two exact classes and
  offsets. The report includes example words for changed feature values. Equal profiles
  are finite equidistribution evidence, not an objectwise bijection. See
  `docs/AM_NEXT_STRUCTURAL_ANALYSIS.md`.
- **Search for a plausible map:** from a class comparison, choose **Find a map** to test
  reverse, complement, standardization, compression, hat and inverse hat, fixed prefix
  lifts, selector-driven sweep lifts, generated block recipes, and compositions. Block
  recipes vary their segmentation, repeated-value parent rule, safe
  ordering, block reversal or reverse-complement, and (for `n → n+1`) a new maximum or
  (for `n → n+2`) a new-maximum pair.
  The paper's modified/revised `111` map and its inverse are included as reference
  candidates. Each result shows its recipe, tested bound, and first counterexample when
  it fails. One-step searches are bounded to source degree 8 and two-step searches to
  degree 6, subject to the family and pattern limits. Export a JSON record with the exact
  class specification, search grammar, candidates, failures, and finite evidence. Class
  count tests accept any valid degree offsets; the current map grammar covers net shifts
  `0`, `+1`, `+2`, and the registered paper inverse at `−2`. A selected statistic is not
  currently an extra map constraint. Every finite pass is evidence, not proof.
- **Refine a search from a failure:** in Discover, select a candidate with an exact
  engine failure and ask the optional assistant for a linked follow-up experiment.
  It must cite supplied failure scenarios and change a bounded search control. Review
  or edit the suggested classes, offsets, range, and budgets, then start the next
  deterministic campaign yourself. The exact parent evidence and proposal are kept
  in the dossier; the assistant does not repair maps or prove conjectures.
- **Test degree offsets:** either class can use a degree `n+d`, so count questions can
  compare shifted classes and the map search can test maps whose lengths differ. A preset
  loads the paper's `M_n(111) → R_{n+2}(111)` conjecture, with the reverse map available
  when the classes are swapped.
- **Inspect transformation roles:** the before/after diagrams label first occurrences
  (`N`), ascent tops (`T`), ascent bottoms (`B`), changed or inserted entries, and the
  sequence-family classifications. The inspector also lists increasing blocks and the
  position and value maps, making structural rules easier to recognize.
- **Investigate results:** browse members of a selected class and degree, refine a
  comparison by ascents, ascent runs, their lengths and start positions, maximum, multiplicity
  profile, or first/last-occurrence positions,
  inspect statistic buckets side-by-side, and open any selected word in the structural
  inspector. Filter members by an exact statistic value or an additional pattern
  condition. At a shared-degree count divergence, ask the engine to find exact words
  belonging to only one side and compare their occurrence roles and fibre orientations
  side-by-side, including run blocks and first/last occurrence positions.
- **Keep research work:** the current draft autosaves; save named-by-content tests on this
  device, reload and rerun them, or export/import a JSON record with the exact experiment
  specification and finite result. The desktop app stores this in the operating system's
  normal per-user application-data folder.
- **Run legacy transformation checks:** the earlier bounded map checker remains under a
  disclosure for reproducing prior one-pass experiments. It reports counterexamples or
  the tested degree range only.
- **Audit a class-wide transformation:** test `reverse`, `complement`, `hat`,
  `inverse_hat`, `prefix_lift`, `inverse_prefix_lift`, position insertion, or
  single-position deletion on a bounded source class. Prefix lifts and restrictions
  take explicit positions; insertion also takes a cut and value. The audit handles the
  `n → n+1` and `n → n−1` degree shifts, and deletion retains unused ambient value
  levels. Review target membership, collisions, coverage, inverse recovery, and an
  optional statistic, with concrete witnesses for failed checks. Results are finite
  computations, not all-degree proofs.
- **Review proof status:** see which local claims have proof arguments, which results
  are finite computations, and which obligations remain open.
- **Compare with existing discovery research:** `docs/AM_N0_EXISTING_SYSTEMS.md` reviews
  FindStat, Combinatorial Exploration, the Bijectionist’s Toolkit, and evolutionary
  bijection synthesis, with runnable baselines that separate equal counts from a searched
  and finitely verified transformation.
- **Follow AM-Next:** `docs/AM_NEXT_CAMPAIGN.md` records the 12 gated research-engineering
  stages and current status; `docs/AM_NEXT_SPECIFICATION.md` defines the versioned N1
  finite-search question format and its bounded independent validation;
  `docs/AM_NEXT_WORKER.md` covers the N2 job queue and checkpoints; and
  `docs/AM_NEXT_CONJECTURE_SEARCH.md` describes N3's generated class-count search; and
  `docs/AM_NEXT_STRUCTURAL_ANALYSIS.md` documents N4's fingerprints and profiles.
- **Use the Python engine:** import the same definitions and transformations in Python
  scripts and experiments.

The primary user experience is the installable desktop app. It uses native Tk controls
and calls the Python engine directly in the application process. Researchers can drag
Avoid/Contain pattern rules into two class lanes, see the conjecture restated before
running, compare degree-by-degree counts, and keep saved tests on their device. The
browser workbench remains available for the sequence inspector and specialist views.

## Download an alpha app

Installers and the importable Python wheel are attached to the GitHub
[**Releases**](https://github.com/Cliff-Lee/ascent-calculus/releases) page. Windows and
macOS packages bundle the Python runtime and AC engine. The Ubuntu `.deb` installs a
menu-launchable app and engine code using Ubuntu's Python and Tk package.

| Platform | Release download | Notes |
| --- | --- | --- |
| macOS Apple silicon | `.dmg` or `.zip` | Unsigned and not notarized; macOS may show a security prompt. |
| Windows 10/11, x64 | `*-windows-x64-setup.exe` | Installs a native desktop workbench. |
| Ubuntu 24.04, x86_64 | `*_amd64.deb` | Install with `sudo apt install ./ascent-calculus_*.deb`; requires `python3-tk`. |

The Windows installer is per-user and offers a Start menu shortcut. On Ubuntu, launch
**Ascent Calculus** from the Applications menu after installing the `.deb`. Each
platform job builds and smoke-tests the packaged native window before uploading a
short-lived Actions artifact for device testing. The Mac launcher writes startup details
to `~/Library/Logs/AscentCalculus/startup.log`.

## Run from source

Requires Python 3.11 or newer.

```bash
git clone https://github.com/cliff-lee/ascent-calculus.git
cd ascent-calculus
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

### Browser workbench

```bash
python -m ac.gui.server
```

Open <http://127.0.0.1:8765>. Stop the server with `Ctrl+C`.
The page opens on **Test a conjecture**; choose a preset or compose a count/comparison.

### Desktop workbench

```bash
python -m pip install -e ".[desktop]"
ac-workbench-desktop
```

The app uses Python's Tk desktop toolkit and the engine runs in-process. On Linux,
install the system Tk package if your Python build does not include it (for example,
`python3-tk` on Ubuntu).

### Build a macOS installer

Run this script on a Mac. It packages the Python interpreter, engine, and GUI into a
`.app`, then creates a compressed `.dmg` and `.zip` in `dist/`.

```bash
./scripts/build_macos.sh
```

The build follows the architecture of the Python used to run it (`arm64` on Apple
silicon or `x86_64` on Intel). The automated release currently builds the Apple silicon
version.

### Build Windows and Ubuntu installers

The Windows installer is built on Windows with PyInstaller and Inno Setup:

```powershell
.\scripts\build_windows.ps1
```

It creates a per-user setup executable and Python wheel in `dist/`.

The Ubuntu `.deb` is built on Ubuntu 24.04 x86_64 and depends on Ubuntu's Tk package:

```bash
./scripts/build_ubuntu.sh
```

It creates the `.deb` and Python wheel in `dist/`. The current Ubuntu installer targets
Ubuntu 24.04 on x86_64.

## Use the Python package

For development, install the package from the repository as shown above. For example,
the core API can be used directly:

```python
from ac import Avoid, Modified, verify_on
from ac.generate.universes import cayley_words

result = verify_on(
    Modified() & Avoid("2122"),
    universe=cayley_words,
    through=6,
)
print(result)
```

AC is not yet published to PyPI. When it is, the importable package will remain
`ascent-calculus`; the desktop app is an additional distribution format.

## Research status and limits

The project records the attempted map between modified `2122`-avoiding and modified
`2212`-avoiding ascent sequences. The original one-pass repair fails at degree 11; the
frozen alternating M/O candidate passed an exhaustive degree-11 check but has no
all-degree proof.

- E11a and E11b contain local structural arguments about fibre orientation and defect
  rotation.
- E11c.1b0 proved base defect admissibility after the complete gap phase.
- E11c.1b1 refuted the first-repair no-heavy-crossing lemma for the one-pass rule. This
  explains why that old repair cannot be treated as the current map.
- E11c.2a1 froze an alternating M/O repair algorithm and checked all 1,248,595 modified
  `2122`-avoiders at degree 11. Every source terminated in the modified `2212`-avoiding
  class with a distinct image; there were no cycles, stalls, unpaired defects, target
  failures, collisions, or missing targets.
- These are finite checks, not an all-degree theorem. The next proof work is the
  alternating-state taxonomy and a termination/preservation argument.
- The experiment builder currently caps ordinary and modified generation at degree 11
  and revised generation at degree 7. General pattern searches have additional
  pattern-length limits; the recognized repeated-sandwich family uses a faster exact
  fibre test. The builder reports these bounds before a costly run.

The project includes the E4–E11 experiments, proof-extraction notes, test suite, GUI
interface contract, and [`standalone clickable prototype`](docs/AC-GUI1-clickable-prototype.html).
See [`STATUS.md`](STATUS.md), [`docs/`](docs/), and [`experiments/`](experiments/) for
details.

## Development and tests

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

Optional Z3 support:

```bash
python -m pip install -e ".[solver]"
```

## Project layout

- `ac/` — Python calculus, transformations, generation, discovery, logic, and GUI API.
- `ac/gui/static/` — browser interface assets.
- `docs/` — semantics, transformation laws, pattern language, and proof extraction.
- `experiments/` — reproducible campaign scripts and recorded outputs.
- `tests/` — regression and semantic tests.
- `docs/AC-GUI1-clickable-prototype.html` — standalone curated prototype.

## License and contributions

No open-source license has been selected for this alpha. The public repository is
available for inspection; no permission to redistribute or publish modified builds is
granted unless a license is added. Please contact the author before contributing.
