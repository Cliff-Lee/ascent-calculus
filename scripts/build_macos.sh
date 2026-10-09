#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Build the macOS app on a Mac so Python and native frameworks match the target." >&2
  exit 2
fi

ARCH="$(uname -m)"
if [[ "$ARCH" != "arm64" && "$ARCH" != "x86_64" ]]; then
  echo "Unsupported macOS architecture: $ARCH" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 -m pip install --upgrade '.[desktop-build]'
python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --onedir \
  --name AscentCalculus \
  --osx-bundle-identifier org.cliffpackman.ascentcalculus \
  --collect-submodules tkinter \
  ac/gui/desktop.py

APP_BIN="dist/AscentCalculus.app/Contents/MacOS/AscentCalculus"
if [[ ! -x "$APP_BIN" ]]; then
  echo "Packaged macOS executable is missing or not executable: $APP_BIN" >&2
  exit 1
fi
"$APP_BIN" --startup-check
"$APP_BIN" --window-smoke-check

OUT="dist/AscentCalculus-macos-${ARCH}"
mkdir -p "$OUT"
python3 -m pip wheel --no-deps . --wheel-dir "$OUT"
hdiutil create \
  -volname "Ascent Calculus Alpha" \
  -srcfolder dist/AscentCalculus.app \
  -ov -format UDZO \
  "$OUT/AscentCalculus-0.1.0a34-macos-${ARCH}.dmg"
ditto -c -k --sequesterRsrc --keepParent \
  dist/AscentCalculus.app \
  "$OUT/AscentCalculus-0.1.0a34-macos-${ARCH}.zip"

DMG_PATH="$OUT/AscentCalculus-0.1.0a34-macos-${ARCH}.dmg"
hdiutil verify "$DMG_PATH"

STARTUP_LOG="$HOME/Library/Logs/AscentCalculus/startup.log"
launch_services_smoke() {
  local app_path="$1"
  local open_pid
  local smoke_passed=0

  rm -f "$STARTUP_LOG"
  /usr/bin/open -n -W "$app_path" --args --launch-smoke-check &
  open_pid=$!
  for ((attempt=0; attempt<120; attempt++)); do
    if grep -Fq '"event": "launch_smoke_passed"' "$STARTUP_LOG" 2>/dev/null; then
      smoke_passed=1
      break
    fi
    if ! kill -0 "$open_pid" 2>/dev/null; then
      break
    fi
    sleep 0.25
  done

  if [[ "$smoke_passed" != 1 ]]; then
    if kill -0 "$open_pid" 2>/dev/null; then
      echo "LaunchServices smoke test timed out for: $app_path" >&2
      kill "$open_pid" 2>/dev/null || true
      pkill -x AscentCalculus 2>/dev/null || true
      wait "$open_pid" 2>/dev/null || true
    else
      wait "$open_pid" 2>/dev/null || true
      echo "LaunchServices smoke test exited before the window stayed open: $app_path" >&2
    fi
    [[ ! -f "$STARTUP_LOG" ]] || cat "$STARTUP_LOG" >&2
    return 1
  fi

  if ! wait "$open_pid"; then
    echo "LaunchServices returned an error for: $app_path" >&2
    [[ ! -f "$STARTUP_LOG" ]] || cat "$STARTUP_LOG" >&2
    return 1
  fi
  cat "$STARTUP_LOG"
}

MOUNT_POINT="$(mktemp -d "${TMPDIR:-/tmp}/ascent-dmg.XXXXXX")"
DISK_DEVICE=""
cleanup_dmg_mount() {
  if [[ -n "$DISK_DEVICE" ]]; then
    hdiutil detach "$DISK_DEVICE" >/dev/null 2>&1 || true
  fi
  if [[ -n "$MOUNT_POINT" && -d "$MOUNT_POINT" ]]; then
    rmdir "$MOUNT_POINT" >/dev/null 2>&1 || true
  fi
}
trap cleanup_dmg_mount EXIT
ATTACH_OUTPUT="$(hdiutil attach -nobrowse -readonly -mountpoint "$MOUNT_POINT" "$DMG_PATH")"
DISK_DEVICE="$(printf '%s\n' "$ATTACH_OUTPUT" | awk '$1 ~ /^\/dev\/disk/ { print $1; exit }')"
if [[ -z "$DISK_DEVICE" || ! -d "$MOUNT_POINT/AscentCalculus.app" ]]; then
  echo "Could not find AscentCalculus.app in the mounted DMG." >&2
  printf '%s\n' "$ATTACH_OUTPUT" >&2
  exit 1
fi
launch_services_smoke "$MOUNT_POINT/AscentCalculus.app"
hdiutil detach "$DISK_DEVICE"
DISK_DEVICE=""
rmdir "$MOUNT_POINT"
MOUNT_POINT=""
trap - EXIT
echo "Created release artifacts in $OUT"
