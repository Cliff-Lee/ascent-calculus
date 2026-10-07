# Desktop Launch Reliability Campaign

## Goal

A downloaded installer must open a real desktop window, render the Ascent Calculus workbench, remain usable, and close cleanly. A successful package build or API health check alone does not meet this gate.

## Current release work

The a8 frozen entrypoint used a relative import. The a9 launcher changed it to an absolute package import and added an API/static-resource check. That check does not instantiate the native webview, which is why it did not catch the reported Mac close-on-launch.

The a10 branch adds persistent lifecycle records and a native-window smoke mode. Its log records process start, import, local server readiness, window shown, page load/readiness, exceptions, and process exit. On macOS the log is:

`~/Library/Logs/AscentCalculus/startup.log`

The first Ubuntu smoke attempt exposed a problem in the smoke harness: waiting inside pywebview startup delayed GTK event processing. The monitor now runs on a separate thread while the GUI loop runs on the main thread. The Ubuntu gate must pass with this corrected harness before a10 can be released.

## Campaign

### DL-1 — Explain every launch exit

- Keep startup logging available in windowed builds.
- Record normal return as well as Python exceptions.
- Enable fault-handler output while the log file remains open.
- Print runner logs when a native launch check fails.

**Gate:** every early exit yields a stage and a useful error record.

### DL-2 — Verify the native window

- Run `--startup-check` against the installed app to check imports, API, and packaged assets.
- Run `--window-smoke-check` against the installed app.
- Require a native window and a ready document; close it automatically after the check.
- Run the checks on macOS arm64, Windows x64, and Ubuntu 24.04 under Xvfb.

**Gate:** all three packaged installers pass both checks before release assets are uploaded.

### DL-3 — Review the first-run experience

- Set a window size that fits a 13-inch MacBook display.
- Inspect loading, first-run, and error states at real desktop sizes.
- Ensure the guided definitions can be reached by hover and keyboard focus.
- Check that the newcomer learning path and researcher tools remain easy to find.

**Gate:** a newcomer can reach a definition/example and a researcher can reach an experiment without a blank or clipped view.

### DL-4 — Release and device acceptance

- Keep the release blocked on any platform smoke failure.
- Install the Mac DMG on the M1 MacBook Air.
- Confirm first launch, visible workbench, sequence inspection, and clean quit.
- If that device still exits, use its startup log to locate the last successful stage and fix that failure before publishing.

**Gate:** the exact downloadable artifact is tested, not just the source tree or a separately launched Python module.

## Relevant code

- `ac/gui/desktop.py`: launcher, local server lifecycle, log, native-window smoke mode.
- `ac/gui/server.py`: local API and packaged static-resource routing.
- `ac/gui/static/`: workbench screens and visual states.
- `scripts/build_macos.sh`, `scripts/build_windows.ps1`, `scripts/build_ubuntu.sh`: platform packaging and native checks.
- `.github/workflows/release.yml`: PR/release gates and asset-upload gate.

The app remains alpha until the M1 device acceptance gate passes.
