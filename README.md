# Ascent Calculus (AC)

**Alpha research software for exploring ascent sequences and their transformations.**

AC is a Python calculus and a visual workbench for ordinary, modified, and revised
ascent sequences. It lets a researcher inspect a word, follow engine-generated
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
- **Build a bounded experiment:** compose a count or comparison from ordinary, modified,
  or revised sequences; add one or more classical Cayley-pattern restrictions; choose a
  degree range; and optionally compare a statistic or apply a structural filter. The
  result states the interpreted question, first count divergence, and finite range.
- **Reproduce pattern comparisons:** the builder can express questions such as modified
  `2122`-avoiders versus modified `2212`-avoiders, or revised `3121`-avoiders at degree
  `n+1` versus ordinary `221`-avoiders at degree `n`, without dedicated GUI commands.
- **Investigate results:** browse members of a selected class and degree, refine a
  comparison by ascents, ascent runs, their lengths and start positions, maximum, multiplicity
  profile, or first/last-occurrence positions,
  inspect statistic buckets side-by-side, and open any selected word in the structural
  inspector. Filter members by an exact statistic value or an additional pattern
  condition. At a shared-degree count divergence, ask the engine to find exact words
  belonging to only one side and compare their occurrence roles and fibre orientations
  side-by-side, including run blocks and first/last occurrence positions.
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
- **Use the Python engine:** import the same definitions and transformations in Python
  scripts and experiments.

The primary user experience is the installable desktop app. Its HTML/CSS interface is
packaged inside a native app window, with the Python engine running alongside it; users
launch the app from their operating system and do not open a browser page or start a
server. The separate standalone HTML review page is only a curated clickable preview.

## Download an alpha app

Installers and the importable Python wheel are attached to the GitHub
[**Releases**](https://github.com/Cliff-Lee/ascent-calculus/releases) page. The app
starts its private local API inside the desktop process. Windows and macOS packages
bundle the Python runtime and AC engine. The Ubuntu `.deb` installs a menu-launchable app
and engine code, using Ubuntu's Python and GTK/WebKit system components; users still do
not need to manage a server.

| Platform | Release download | Notes |
| --- | --- | --- |
| macOS Apple silicon | `.dmg` or `.zip` | Unsigned and not notarized; macOS may show a security prompt. |
| Windows 10/11, x64 | `*-windows-x64-setup.exe` | Requires the Microsoft Edge WebView2 Runtime. |
| Ubuntu 24.04, x86_64 | `*_amd64.deb` | Install with `sudo apt install ./ascent-calculus_*.deb`; Ubuntu resolves GTK and WebKit dependencies. |

The Windows installer is per-user and offers a Start menu shortcut. On Ubuntu, launch
**Ascent Calculus** from the Applications menu after installing the `.deb`. These are alpha builds. The release workflow now installs and exercises the packaged
native window on each platform runner before attaching installers. The Mac launcher
writes startup stages and failures to
`~/Library/Logs/AscentCalculus/startup.log`; this log is useful if the app exits early.
Hosted checks do not replace testing on every user's device.

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

### Native desktop window

```bash
python -m pip install -e ".[desktop]"
ac-workbench-desktop
```

The desktop extra uses the platform's native webview. macOS builds use Cocoa; Linux
may need the GTK or Qt system libraries required by pywebview.

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

It creates a per-user setup executable and Python wheel in `dist/`. Windows needs the
WebView2 Runtime for the native app window.

The Ubuntu `.deb` is built on Ubuntu 24.04 x86_64. Its dependencies use Ubuntu's GTK 3
and WebKit2GTK 4.1 packages, while the installer vendors pywebview and the AC code:

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
