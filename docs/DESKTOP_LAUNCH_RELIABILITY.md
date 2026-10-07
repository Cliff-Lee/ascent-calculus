# Desktop Launch Reliability

## Goal

The downloadable app should open a real desktop window, show the conjecture workbench,
and close cleanly. A successful package build alone is not enough.

## Native desktop checks

The desktop app uses Tk controls and calls the Python engine directly. The packaged
`--startup-check` verifies the imports and runs a small engine comparison without a
window. `--window-smoke-check` maps the real workbench window and closes it
automatically. The macOS, Windows, and Ubuntu build jobs run both checks; Ubuntu uses
Xvfb and Openbox.

The app records startup failures in:

- macOS: `~/Library/Logs/AscentCalculus/startup.log`
- Windows/Linux: `~/.ascent-calculus/startup.log`

## Device acceptance

Hosted checks catch packaging and launch regressions, but the exact Mac artifact still
needs a first-run check on the M1 MacBook Air. If it exits early, the startup log records
the last completed stage and exception. The app is alpha until the user-device check
passes.
