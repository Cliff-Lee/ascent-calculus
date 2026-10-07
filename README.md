# Ascent Calculus (AC)

**Alpha research software for exploring ascent sequences and their transformations.**

AC is a Python calculus and a visual workbench for ordinary, modified, and revised
ascent sequences. It lets a researcher inspect a word, follow engine-generated
transformations, and test conjectures on finite ranges. It is experimental software:
finite verification is evidence, not a proof of a general theorem.

> **Alpha status:** the GUI is a research prototype, the API and interface may change,
> and the current `2122` to `2212` bijection candidate is not proved for arbitrary
> length. E11c (the reachable-state provenance invariant) and E11d (the symbolic
> inverse proof) remain open. The workbench labels bounded success as
> **VERIFIED THROUGH `n=k`**, never **PROVED**.

## What you can do

- **Inspect a sequence:** view positions, values, stable occurrence IDs, first
  occurrences, ascent tops and bottoms, defects, runs, multiplicities, fibre gaps,
  and `2122`/`2212` orientation. Select a position to see why it has each role.
- **Trace a transformation:** run the engine-backed
  `ExtremeGapSwap → CanonicalRepair` construction, step through its states, and inspect
  the selected defects, pivot value, blocks `A` and `B`, repair interval, potential,
  and local certificate.
- **Try bounded conjectures:** choose one of the supported source/target classes and
  transformations, then run an exhaustive finite check. A counterexample is reported
  when found. A successful check reports the tested degree range only.
- **Review proof status:** see which local claims have proof arguments, which results
  are finite computations, and which obligations remain open.
- **Use the Python engine:** import the same definitions and transformations in Python
  scripts and experiments.

The GUI is a view over the AC engine. The standalone HTML review page is a curated
clickable demonstration; the live workbench supports arbitrary inputs and executes the
Python engine.

## Download an alpha app

Installers and the importable Python wheel are attached to the GitHub
[**Releases**](https://github.com/Cliff-Lee/ascent-calculus/releases) page. The desktop
app bundles the AC engine and starts its local API inside the application; users do not
manage a Python server.

| Platform | Release download | Notes |
| --- | --- | --- |
| macOS Apple silicon | `.dmg` or `.zip` | Unsigned and not notarized; macOS may show a security prompt. |
| Windows 10/11, x64 | `*-windows-x64-setup.exe` | Requires the Microsoft Edge WebView2 Runtime. |
| Ubuntu 24.04, x86_64 | `*_amd64.deb` | Install with `sudo apt install ./ascent-calculus_*.deb`; Ubuntu resolves GTK and WebKit dependencies. |

The Windows installer is per-user and offers a Start menu shortcut. On Ubuntu, launch
**Ascent Calculus** from the Applications menu after installing the `.deb`. These are
alpha builds; the platform release jobs build and run focused regression tests, but the
installers have not yet been manually exercised on every end-user machine.

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

The workbench currently focuses on the proposed map between modified `2122`-avoiding
and modified `2212`-avoiding ascent sequences.

- E11a and E11b contain local structural arguments about fibre orientation and defect
  rotation.
- E11c is open: the proof needs a provenance invariant for states reachable from the
  extreme gap swap, including the no-heavy-crossing condition.
- E11d is open: the parameter-swapped construction still needs a symbolic inverse
  proof.
- The GUI's finite checks do not prove claims beyond the checked range. The recorded
  degree-10 bijection benchmark and the incomplete degree-11 run remain finite evidence.
- The general exhaustively searchable degree is limited by combinatorial growth and
  available memory and time. Large runs can take a long time.

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
